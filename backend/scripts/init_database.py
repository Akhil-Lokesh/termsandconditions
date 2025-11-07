#!/usr/bin/env python3
"""
Initialize or reset database with Alembic migrations.

Usage:
    python scripts/init_database.py           # Run migrations
    python scripts/init_database.py --reset   # Drop all tables and rerun migrations
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a shell command and handle errors."""
    print(f"\n{description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if check and result.returncode != 0:
        print(f"✗ Failed: {result.stderr}")
        if result.stdout:
            print(result.stdout)
        sys.exit(1)
    else:
        print(f"✓ Success")
        if result.stdout:
            print(result.stdout)

    return result


def check_database_connection():
    """Check if database is accessible."""
    print("\nChecking database connection...")
    backend_dir = Path(__file__).parent.parent

    result = run_command(
        f"cd {backend_dir} && python3 -m alembic current",
        "Testing database connection",
        check=False,
    )

    if result.returncode != 0:
        print("\n❌ Database connection failed!")
        print("\nPossible issues:")
        print("  1. PostgreSQL is not running")
        print("     → Start with: docker-compose up -d postgres")
        print("  2. Database credentials are incorrect")
        print("     → Check DATABASE_URL in .env")
        print("  3. Database does not exist")
        print("     → Create with: docker-compose exec postgres createdb <dbname>")
        sys.exit(1)

    print("✓ Database connection successful")


def main():
    """Initialize database."""
    parser = argparse.ArgumentParser(description="Initialize T&C Analysis database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables and rerun migrations (DESTRUCTIVE!)",
    )
    parser.add_argument(
        "--check-only", action="store_true", help="Only check database connection"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("T&C Analysis - Database Initialization")
    print("=" * 60)

    backend_dir = Path(__file__).parent.parent

    # Check database connection first
    check_database_connection()

    if args.check_only:
        print("\n✓ Database connection check passed!")
        return

    if args.reset:
        print("\n⚠️  WARNING: --reset will drop all tables and data!")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() != "yes":
            print("Aborting.")
            sys.exit(0)

        # Drop all tables by downgrading to base
        run_command(
            f"cd {backend_dir} && python3 -m alembic downgrade base",
            "Dropping all tables",
        )

    # Run migrations
    run_command(
        f"cd {backend_dir} && python3 -m alembic upgrade head",
        "Applying migrations",
    )

    # Show current migration status
    run_command(
        f"cd {backend_dir} && python3 -m alembic current",
        "Current migration status",
    )

    print("\n" + "=" * 60)
    print("✓ Database initialized successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Start the backend: uvicorn app.main:app --reload")
    print("  2. Check health: curl http://localhost:8000/health")
    print("  3. View API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
