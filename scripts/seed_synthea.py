import csv
import os
import sys
import logging
from typing import Set, List, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.dialects.postgresql import insert
from config.settings import settings
from data.database import SessionLocal, engine
from data.models import Patient, Condition, Encounter, User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_synthea")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "synthea")
PATIENTS_CSV = os.path.join(DATA_DIR, "patients.csv")
CONDITIONS_CSV = os.path.join(DATA_DIR, "conditions.csv")
ENCOUNTERS_CSV = os.path.join(DATA_DIR, "encounters.csv")

BATCH_SIZE = 1000
PATIENT_LIMIT = 500


def seed_admin_user(session) -> None:
    """Seeds the default admin/clinician user if not present."""
    admin_user = session.query(User).filter_by(username=settings.DASHBOARD_ADMIN_USER).first()
    if not admin_user:
        user = User(
            username=settings.DASHBOARD_ADMIN_USER,
            full_name="Dr. Vaidya (Chief Clinician)",
            role="clinician"
        )
        user.set_password(settings.DASHBOARD_ADMIN_PASSWORD)
        session.add(user)
        session.commit()
        logger.info(f"Seeded default clinician user: '{settings.DASHBOARD_ADMIN_USER}'")
    else:
        logger.info(f"Clinician user '{settings.DASHBOARD_ADMIN_USER}' already exists.")


def seed_patients(session) -> Set[str]:
    """
    Seeds patients up to PATIENT_LIMIT. Returns set of seeded patient IDs.
    """
    if not os.path.exists(PATIENTS_CSV):
        logger.error(f"Patients CSV not found at {PATIENTS_CSV}")
        return set()

    patient_ids: Set[str] = set()
    records_to_insert: List[Dict[str, Any]] = []

    with open(PATIENTS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if count >= PATIENT_LIMIT:
                break
            patient_id = row.get("Id", "").strip()
            if not patient_id:
                continue

            patient_ids.add(patient_id)
            records_to_insert.append({
                "id": patient_id,
                "birthdate": row.get("BIRTHDATE"),
                "deathdate": row.get("DEATHDATE"),
                "first_name": row.get("FIRST"),
                "last_name": row.get("LAST"),
                "gender": row.get("GENDER"),
                "race": row.get("RACE"),
                "ethnicity": row.get("ETHNICITY"),
                "city": row.get("CITY"),
                "state": row.get("STATE"),
                "zip": row.get("ZIP")
            })
            count += 1

    if records_to_insert:
        stmt = insert(Patient).values(records_to_insert).on_conflict_do_nothing(index_elements=["id"])
        session.execute(stmt)
        session.commit()

    total_in_db = session.query(Patient).count()
    logger.info(f"Patients seeded: {len(records_to_insert)} read from CSV, {total_in_db} total currently in database.")
    return patient_ids


def seed_encounters(session, valid_patient_ids: Set[str]) -> None:
    """Seeds encounters corresponding to valid_patient_ids."""
    if not os.path.exists(ENCOUNTERS_CSV):
        logger.warning(f"Encounters CSV not found at {ENCOUNTERS_CSV}")
        return

    records: List[Dict[str, Any]] = []
    total_processed = 0

    with open(ENCOUNTERS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("PATIENT", "").strip()
            if pid not in valid_patient_ids:
                continue

            enc_id = row.get("Id", "").strip()
            if not enc_id:
                continue

            records.append({
                "id": enc_id,
                "patient_id": pid,
                "start_date": row.get("START"),
                "stop_date": row.get("STOP"),
                "encounter_class": row.get("ENCOUNTERCLASS"),
                "code": row.get("CODE"),
                "description": row.get("DESCRIPTION")
            })

            if len(records) >= BATCH_SIZE:
                stmt = insert(Encounter).values(records).on_conflict_do_nothing(index_elements=["id"])
                session.execute(stmt)
                session.commit()
                total_processed += len(records)
                records = []

    if records:
        stmt = insert(Encounter).values(records).on_conflict_do_nothing(index_elements=["id"])
        session.execute(stmt)
        session.commit()
        total_processed += len(records)

    total_in_db = session.query(Encounter).count()
    logger.info(f"Encounters seeded: {total_processed} processed, {total_in_db} total in database.")


def seed_conditions(session, valid_patient_ids: Set[str]) -> None:
    """Seeds conditions corresponding to valid_patient_ids."""
    if not os.path.exists(CONDITIONS_CSV):
        logger.warning(f"Conditions CSV not found at {CONDITIONS_CSV}")
        return

    existing_count = session.query(Condition).count()
    if existing_count > 0:
        logger.info(f"Conditions table already contains {existing_count} records. Skipping duplicate seeding.")
        return

    records: List[Dict[str, Any]] = []
    total_processed = 0

    with open(CONDITIONS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("PATIENT", "").strip()
            if pid not in valid_patient_ids:
                continue

            desc = row.get("DESCRIPTION", "").strip()
            if not desc:
                continue

            records.append({
                "patient_id": pid,
                "encounter_id": row.get("ENCOUNTER"),
                "code": row.get("CODE"),
                "description": desc,
                "start_date": row.get("START"),
                "stop_date": row.get("STOP")
            })

            if len(records) >= BATCH_SIZE:
                # Fast bulk insert for conditions
                session.bulk_insert_mappings(Condition, records)
                session.commit()
                total_processed += len(records)
                records = []

    if records:
        session.bulk_insert_mappings(Condition, records)
        session.commit()
        total_processed += len(records)

    total_in_db = session.query(Condition).count()
    logger.info(f"Conditions seeded: {total_processed} processed, {total_in_db} total in database.")


def main():
    logger.info("Starting Synthea dataset seeding into PostgreSQL...")
    session = SessionLocal()
    try:
        seed_admin_user(session)
        patient_ids = seed_patients(session)
        if patient_ids:
            seed_encounters(session, patient_ids)
            seed_conditions(session, patient_ids)
        logger.info("Synthea seeding completed successfully.")
    except Exception as e:
        session.rollback()
        logger.exception(f"Error during seeding: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
