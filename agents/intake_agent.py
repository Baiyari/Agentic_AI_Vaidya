import re
import json
import logging
from typing import List, Tuple, Optional

from core.models import TriageRequest
from core.icd_lookup import get_all_symptoms, SYMPTOM_MAP
from agents.llm_client import llm_client

logger = logging.getLogger(__name__)


# Common conversational aliases mapped to normalized taxonomy keys
SYMPTOM_SYNONYMS = {
    "chest pain": "chest_pain",
    "crushing chest pain": "chest_pain",
    "pain in chest": "chest_pain",
    "angina": "chest_pain",
    "shortness of breath": "shortness_of_breath",
    "short of breath": "shortness_of_breath",
    "breathless": "shortness_of_breath",
    "severe breathlessness": "difficulty_breathing",
    "severe shortness of breath": "difficulty_breathing",
    "trouble breathing": "difficulty_breathing",
    "hard to breathe": "difficulty_breathing",
    "difficulty breathing": "difficulty_breathing",
    "cannot breathe": "difficulty_breathing",
    "can't breathe": "difficulty_breathing",
    "gasping for air": "difficulty_breathing",
    "wheezing": "wheezing",
    "severe headache": "sudden_severe_headache",
    "worst headache": "sudden_severe_headache",
    "headache": "headache",
    "migraine": "migraine",
    "vision loss": "vision_loss",
    "can't see": "vision_loss",
    "double vision": "double_vision",
    "bleeding heavily": "severe_bleeding",
    "severe bleeding": "severe_bleeding",
    "slurred speech": "slurred_speech",
    "slurring": "slurred_speech",
    "facial drooping": "facial_drooping",
    "face drooping": "facial_drooping",
    "face swelling": "swelling_face",
    "swollen face": "swelling_face",
    "stiff neck": "stiff_neck",
    "confusion": "confusion",
    "confused": "confusion",
    "coughing up blood": "coughing_blood",
    "coughing blood": "coughing_blood",
    "numbness": "numbness",
    "weakness on one side": "weakness_one_side",
    "one sided weakness": "weakness_one_side",
    "stroke symptoms": "slurred_speech",
    "stroke": "slurred_speech",
    "loss of consciousness": "syncope",
    "passed out": "syncope",
    "blackout": "syncope",
    "fainted": "syncope",
    "fainting": "syncope",
    "suicidal thoughts": "suicidal_thoughts",
    "suicidal": "suicidal_thoughts",
    "thoughts of suicide": "suicidal_thoughts",
    "seizures": "seizures",
    "fit": "seizures",
    "fever": "fever",
    "high temperature": "fever",
    "cough": "cough",
    "coughing": "cough",
    "nausea": "nausea",
    "throwing up": "vomiting",
    "vomiting": "vomiting",
    "stomach pain": "abdominal_pain",
    "belly pain": "abdominal_pain",
    "abdominal pain": "abdominal_pain",
    "rash": "skin_rash",
    "skin rash": "skin_rash",
    "itching": "itching",
    "itchy": "itching",
    "hives": "hives",
    "dizziness": "dizziness",
    "dizzy": "dizziness",
    "lightheaded": "dizziness",
    "palpitations": "palpitations",
    "racing heart": "palpitations",
    "joint pain": "joint_pain",
    "back pain": "back_pain",
    "fatigue": "fatigue",
    "tiredness": "fatigue",
    "exhaustion": "fatigue",
}

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "a": 1, "an": 1, "couple": 2, "few": 3, "half": 0.5
}


class IntakeAgent:
    """
    Parses unstructured, conversational patient prose into a structured TriageRequest.
    Uses optional LLM extraction with deterministic regex/synonym fallback.
    """

    def __init__(self):
        self.known_symptoms = set(get_all_symptoms())

    def parse(self, text: str) -> TriageRequest:
        """
        Converts conversational text to structured TriageRequest.
        """
        # 1. Try LLM extraction if enabled
        if llm_client.is_available():
            llm_result = self._parse_with_llm(text)
            if llm_result:
                return llm_result

        # 2. Fall back to deterministic rule/regex extractor
        return self._parse_with_rules(text)

    def _parse_with_llm(self, text: str) -> Optional[TriageRequest]:
        system_prompt = (
            "You are a clinical intake assistant. Extract the patient's symptoms, age, duration in days or hours from the text. "
            "Return ONLY a valid JSON object with keys: 'symptoms' (list of strings using lowercase snake_case), "
            "'age' (integer, default 40 if unknown), 'duration_days' (float or int, default 1.0 if unknown), "
            "and 'duration_hours' (float or int, optional). "
            "Do not include code markdown formatting or explanation."
        )
        response = llm_client.generate(text, system_instruction=system_prompt)
        if not response:
            return None

        try:
            # Clean markdown codeblocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
                cleaned = re.sub(r"```$", "", cleaned).strip()

            data = json.loads(cleaned)
            symptoms = data.get("symptoms", [])
            age = int(data.get("age", 40))
            duration_days = float(data.get("duration_days", 1.0))
            duration_hours = float(data.get("duration_hours", duration_days * 24.0))

            # Validate symptoms against known taxonomy or fallback normalization
            valid_symptoms = []
            for s in symptoms:
                norm = s.lower().replace("-", "_").replace(" ", "_")
                if norm in self.known_symptoms:
                    valid_symptoms.append(norm)
                elif norm in SYMPTOM_SYNONYMS:
                    valid_symptoms.append(SYMPTOM_SYNONYMS[norm])

            if valid_symptoms:
                return TriageRequest(
                    symptoms=valid_symptoms, 
                    age=age, 
                    duration_days=duration_days,
                    duration_hours=duration_hours
                )
        except Exception as e:
            logger.warning(f"Failed to parse LLM intake response as JSON: {e}")

        return None

    def _parse_duration(self, lower: str) -> Tuple[float, float]:
        """
        Extracts duration from natural language prose.
        Returns tuple of (duration_days, duration_hours).
        Never drops sub-day durations to 0 days.
        """
        # Specific conversational time anchor checks
        if "half an hour" in lower or "half hour" in lower:
            return 0.021, 0.5
        if "since this morning" in lower or "this morning" in lower:
            return 0.25, 6.0
        if "since last night" in lower or "last night" in lower:
            return 0.5, 12.0
        if "since yesterday" in lower or "yesterday" in lower:
            return 1.0, 24.0
        if "today" in lower:
            return 0.25, 6.0

        # Remove age indicators from text so "60 years old" does not match "60 years" duration
        clean_text = re.sub(r"\b\d{1,3}\s*(?:years?\s*old|yo|y/o|-year-old|-years-old)\b", " ", lower)
        clean_text = re.sub(r"\b(?:age|aged)\s*[:=\s]\s*\d{1,3}\b", " ", clean_text)
        clean_text = re.sub(r"\b(?:i am|i'm)\s*\d{1,3}\b", " ", clean_text)

        # Regex to capture numeric and written durations
        pattern = r"\b(?:for|since|past|last|over|about|around|lasting|during)?\s*(\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|a|an|couple|few|half)\s*(minute|min|hour|hr|day|week|month|year)s?\b"
        matches = re.finditer(pattern, clean_text)
        for match in matches:
            raw_qty = match.group(1).strip()
            unit = match.group(2).strip()

            try:
                if raw_qty in WORD_TO_NUM:
                    qty = float(WORD_TO_NUM[raw_qty])
                else:
                    qty = float(raw_qty)
            except ValueError:
                continue

            if qty <= 0:
                continue

            if unit.startswith("min"):
                hours = round(qty / 60.0, 3)
                days = round(hours / 24.0, 3)
                return max(days, 0.001), hours
            elif unit.startswith("hour") or unit.startswith("hr"):
                hours = qty
                days = round(hours / 24.0, 3)
                return max(days, 0.001), hours
            elif unit.startswith("day"):
                days = qty
                hours = qty * 24.0
                return days, hours
            elif unit.startswith("week"):
                days = qty * 7.0
                hours = days * 24.0
                return days, hours
            elif unit.startswith("month"):
                days = qty * 30.0
                hours = days * 24.0
                return days, hours
            elif unit.startswith("year"):
                days = qty * 365.0
                hours = days * 24.0
                return days, hours

        # Default fallback: 1 day (24 hours)
        return 1.0, 24.0

    def _parse_with_rules(self, text: str) -> TriageRequest:
        lower = text.lower()

        # Extract Age (e.g. "45 year old", "age: 45", "45yo", "45 y/o", "45-year-old")
        age = 40  # Default adult age
        age_patterns = [
            r"(\d{1,3})\s*(?:years?\s*old|yo|y/o|-year-old)",
            r"age\s*[:=\s]\s*(\d{1,3})",
            r"i am\s*(\d{1,3})",
            r"i'm\s*(\d{1,3})"
        ]
        for pattern in age_patterns:
            match = re.search(pattern, lower)
            if match:
                try:
                    parsed_age = int(match.group(1))
                    if 0 <= parsed_age <= 120:
                        age = parsed_age
                        break
                except ValueError:
                    pass

        # Extract Duration (store hours and fractional days, never 0 days)
        duration_days, duration_hours = self._parse_duration(lower)

        # Extract Symptoms using synonym map and direct taxonomy search
        matched_symptoms = []

        # 1. Check multi-word synonyms first (longer phrases matched first)
        sorted_synonyms = sorted(SYMPTOM_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True)
        for phrase, symptom_key in sorted_synonyms:
            if re.search(r"\b" + re.escape(phrase) + r"\b", lower):
                if symptom_key not in matched_symptoms:
                    matched_symptoms.append(symptom_key)

        # 2. Check direct matches with normalized taxonomy keys (replace _ with space)
        for symptom_key in self.known_symptoms:
            spaced = symptom_key.replace("_", " ")
            if re.search(r"\b" + re.escape(spaced) + r"\b", lower):
                if symptom_key not in matched_symptoms:
                    matched_symptoms.append(symptom_key)

        # Fallback if no symptoms matched
        if not matched_symptoms:
            matched_symptoms = ["fever"]  # Safe default presenting complaint

        return TriageRequest(
            symptoms=matched_symptoms,
            age=age,
            duration_days=duration_days,
            duration_hours=duration_hours
        )
