#!/usr/bin/env python3
"""
AllerGraph - Database Schema Initialization Script
Creates idempotent uniqueness constraints and search indexes in Neo4j.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import db

def main():
    print("=" * 60)
    print("AllerGraph: Initializing Neo4j Schema Constraints & Indexes")
    print("=" * 60)

    try:
        db.verify_connectivity()
        applied = db.initialize_schema()
        print(f"\nSuccessfully executed/verified {len(applied)} schema statements.")
        for stmt in applied:
            print(f"  ✓ {stmt}")
        print("\nSchema initialization complete.")
    except Exception as e:
        print(f"\n[ERROR] Schema initialization failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
