"""Reconcile the live database schema with the current models — RUN MANUALLY.

This is the standalone counterpart to the Alembic migration
``f1a2b3c4d5e6_reconcile_schema_drift``. Use it when the live DB's
``alembic_version`` is out of sync (so ``alembic upgrade head`` can't apply
cleanly) — it inspects the actual tables and reconciles them directly.

What it does:
  1. CREATE ``feedback_events`` if missing (needed by the feedback + performance
     endpoints; without it they 500).
  2. With ``--drop-vestigial``: DROP the orphaned tables from the deleted
     two-stage / advanced-detection pipeline (analysis_logs, compound_risks,
     calibration_feedback, active_learning_queue). Off by default — destructive.
  3. With ``--clean-test-rows``: delete leftover ``bugfix_probe_*`` test users
     created during the bug-sweep verification.

Usage (from backend/, venv active):
    python -m scripts.reconcile_db_schema                 # create feedback_events only (safe)
    python -m scripts.reconcile_db_schema --drop-vestigial --clean-test-rows
"""

import argparse

from sqlalchemy import inspect, text

import app.models  # noqa: F401 — register all models on Base.metadata
from app.db.base import Base
from app.db.session import engine

VESTIGIAL_TABLES = [
    "analysis_logs",
    "compound_risks",
    "calibration_feedback",
    "active_learning_queue",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile DB schema with models.")
    parser.add_argument("--drop-vestigial", action="store_true",
                        help="Drop orphaned tables from the deleted pipeline (destructive).")
    parser.add_argument("--clean-test-rows", action="store_true",
                        help="Delete leftover bugfix_probe_* test users.")
    args = parser.parse_args()

    before = set(inspect(engine).get_table_names())
    print("Tables present:", sorted(before))

    # 1. Create feedback_events (and any other missing modeled table). create_all
    #    only issues CREATE for tables that don't exist; it never alters/drops.
    Base.metadata.create_all(bind=engine)
    after_create = set(inspect(engine).get_table_names())
    created = sorted(after_create - before)
    print("Created:", created or "(nothing — all modeled tables already present)")

    # 2. Drop vestigial tables.
    if args.drop_vestigial:
        with engine.begin() as conn:
            for table in VESTIGIAL_TABLES:
                if table in after_create:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    print(f"Dropped vestigial table: {table}")
    else:
        still_present = [t for t in VESTIGIAL_TABLES if t in after_create]
        if still_present:
            print(f"Vestigial tables still present (pass --drop-vestigial to remove): {still_present}")

    # 3. Clean up bug-sweep test rows.
    if args.clean_test_rows:
        with engine.begin() as conn:
            conn.execute(text(
                "DELETE FROM feedback_events WHERE user_id IN "
                "(SELECT id FROM users WHERE email LIKE 'bugfix_probe_%')"
            ))
            conn.execute(text(
                "DELETE FROM anomalies WHERE document_id IN (SELECT id FROM documents "
                "WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'bugfix_probe_%'))"
            ))
            conn.execute(text(
                "DELETE FROM documents WHERE user_id IN "
                "(SELECT id FROM users WHERE email LIKE 'bugfix_probe_%')"
            ))
            result = conn.execute(text("DELETE FROM users WHERE email LIKE 'bugfix_probe_%'"))
            print(f"Cleaned {result.rowcount} bugfix_probe test user(s)")

    print("Done.")


if __name__ == "__main__":
    main()
