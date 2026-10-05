import logging
from fastmcp import FastMCP
from typing import List, Dict, Any, Optional

from core.models import TriageRequest
from core.triage import assess_severity
from core.icd_lookup import lookup_condition_category, get_specialist_for_symptoms
from config.settings import settings

logger = logging.getLogger(__name__)

mcp = FastMCP("Vaidya Triage MCP")

@mcp.tool()
def check_severity(
    symptoms: List[str], 
    age: int, 
    duration_days: float = 1.0, 
    duration_hours: Optional[float] = None
) -> Dict[str, Any]:
    """
    Checks the severity of a patient's symptoms based on a deterministic rules engine.
    Use this tool to determine how urgent a patient's condition is.
    
    Args:
        symptoms: A list of symptoms (e.g. ["chest_pain", "fever"])
        age: The patient's age in years
        duration_days: How long the symptoms have been present in days (can be fractional)
        duration_hours: Optional duration in hours
        
    Returns:
        A dictionary containing severity level, reason, and an integer score.
    """
    logger.info(f"MCP check_severity called for symptoms: {symptoms}, age: {age}, days: {duration_days}, hours: {duration_hours}")
    if duration_hours is not None and duration_days == 1.0:
        duration_days = round(duration_hours / 24.0, 3)
    elif duration_hours is None and duration_days > 0:
        duration_hours = duration_days * 24.0

    request = TriageRequest(
        symptoms=symptoms, 
        age=age, 
        duration_days=duration_days,
        duration_hours=duration_hours
    )
    result = assess_severity(request)
    
    return {
        "severity": result.severity.value,
        "reason": result.reason,
        "score": result.score
    }

@mcp.tool()
def lookup_condition(symptom: str) -> str:
    """
    Looks up the ICD-style category for a given symptom.
    
    Args:
        symptom: A single symptom string.
        
    Returns:
        The ICD category description or a message saying it's unknown.
    """
    logger.info(f"MCP lookup_condition called for symptom: {symptom}")
    category = lookup_condition_category(symptom)
    return category if category else "Unknown category"

@mcp.tool()
def lookup_conditions(symptom: str) -> str:
    """
    Looks up the ICD-style category for a given symptom (plural alias).
    
    Args:
        symptom: A single symptom string.
        
    Returns:
        The ICD category description or a message saying it's unknown.
    """
    return lookup_condition(symptom)

@mcp.tool()
def suggest_specialist(symptoms: List[str]) -> str:
    """
    Suggests the appropriate medical specialist based on a list of symptoms.
    
    Args:
        symptoms: A list of symptom strings.
        
    Returns:
        The specialist type.
    """
    logger.info(f"MCP suggest_specialist called for symptoms: {symptoms}")
    suggestion = get_specialist_for_symptoms(symptoms)
    if suggestion:
        return suggestion.specialist
    return "General Practitioner"

def run_mcp_server():
    """Starts the FastMCP server using streamable-http transport."""
    logger.info(f"Starting MCP server with streamable-http on port {settings.MCP_PORT}")
    mcp.run(transport="streamable-http", port=settings.MCP_PORT, host=settings.MCP_HOST)

if __name__ == "__main__":
    run_mcp_server()
