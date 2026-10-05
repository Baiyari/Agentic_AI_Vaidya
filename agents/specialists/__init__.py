from typing import Dict
from agents.base import BaseSpecialistAgent
from agents.specialists.cardiology import CardiologyAgent
from agents.specialists.pulmonology import PulmonologyAgent
from agents.specialists.neurology import NeurologyAgent
from agents.specialists.gastroenterology import GastroenterologyAgent
from agents.specialists.dermatology import DermatologyAgent
from agents.specialists.general import GeneralMedicineAgent

SPECIALIST_REGISTRY: Dict[str, BaseSpecialistAgent] = {
    "Cardiology": CardiologyAgent(),
    "Pulmonology": PulmonologyAgent(),
    "Neurology": NeurologyAgent(),
    "Gastroenterology": GastroenterologyAgent(),
    "Dermatology": DermatologyAgent(),
    "General Medicine": GeneralMedicineAgent(),
}


def get_specialist_agent(specialty_name: str) -> BaseSpecialistAgent:
    """
    Retrieves the specialist agent instance for a given specialty name,
    defaulting to General Medicine if not found.
    """
    return SPECIALIST_REGISTRY.get(specialty_name, SPECIALIST_REGISTRY["General Medicine"])
