#!/usr/bin/env python3
"""
AllerGraph - Administrator Creation Script
Safely creates or upgrades an administrator account with secure Argon2 password hashing.
Usage:
    python allergraph/scripts/create_admin.py [email] [full_name] [password]
Or run without arguments for interactive prompts.
"""
import sys
import getpass
from pathlib import Path
from datetime import datetime, timezone
import uuid

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import db
from app.security import hash_password, validate_password_strength

def main():
    print("=" * 60)
    print("AllerGraph: Safe Administrator Account Creator")
    print("=" * 60)

    if len(sys.argv) >= 4:
        email = sys.argv[1].strip()
        full_name = sys.argv[2].strip()
        password = sys.argv[3]
    else:
        email = input("Enter Admin Email (e.g. admin@allergraph.local): ").strip()
        if not email or "@" not in email:
            print("[ERROR] Valid email address is required.")
            sys.exit(1)

        full_name = input("Enter Full Name (e.g. Platform Administrator): ").strip()
        if not full_name:
            full_name = "Platform Administrator"

        password = getpass.getpass("Enter Admin Password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit): ")
        confirm_password = getpass.getpass("Confirm Admin Password: ")

        if password != confirm_password:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    # Validate password strength
    valid, err_msg = validate_password_strength(password)
    if not valid:
        print(f"[ERROR] {err_msg}")
        sys.exit(1)

    hashed = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(uuid.uuid4())

    query = """
    MERGE (u:User {email: toLower($email)})
    ON CREATE SET
        u.id = $id,
        u.full_name = $full_name,
        u.password_hash = $hashed,
        u.role = 'ADMIN',
        u.is_active = true,
        u.created_at = $now,
        u.updated_at = $now
    ON MATCH SET
        u.id = coalesce(u.id, $id),
        u.full_name = $full_name,
        u.password_hash = $hashed,
        u.role = 'ADMIN',
        u.is_active = true,
        u.updated_at = $now
    RETURN u
    """

    try:
        db.verify_connectivity()
        record = db.execute_single(query, {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "hashed": hashed,
            "now": now
        })
        user = record["u"]
        print(f"\n[SUCCESS] Administrator account successfully configured!")
        print(f"  User ID:   {user.get('id')}")
        print(f"  Name:      {user.get('full_name')}")
        print(f"  Email:     {user.get('email')}")
        print(f"  Role:      {user.get('role')}")
        print(f"  Active:    {user.get('is_active')}")
        print("\nYou can now sign in at http://localhost:8000/login")
    except Exception as e:
        print(f"\n[ERROR] Failed to create administrator: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
