import hashlib
import secrets
import time
from typing import Dict, Tuple, Optional
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.config import settings

# Password Hashing via Argon2
pwd_context = PasswordHash((Argon2Hasher(),))

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, None

# CSRF Protection
csrf_serializer = URLSafeTimedSerializer(settings.CSRF_SECRET, salt="allergraph-csrf")

def generate_csrf_token(session_id: str) -> str:
    return csrf_serializer.dumps({"sid": session_id, "t": time.time()})

def verify_csrf_token(token: str, session_id: str, max_age: int = 7200) -> bool:
    if not token or not session_id:
        return False
    try:
        data = csrf_serializer.loads(token, max_age=max_age)
        return data.get("sid") == session_id
    except (BadSignature, SignatureExpired):
        return False

# In-Memory Rate Limiter for Login Protection
class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 900):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        # key -> (attempt_count, last_attempt_time, locked_until)
        self.attempts: Dict[str, Tuple[int, float, float]] = {}

    def is_locked(self, identifier: str) -> Tuple[bool, int]:
        now = time.time()
        record = self.attempts.get(identifier)
        if not record:
            return False, 0
        count, last_time, locked_until = record
        if locked_until > now:
            remaining = int(locked_until - now)
            return True, remaining
        # If lockout period expired, reset
        if now - last_time > self.lockout_seconds:
            self.attempts.pop(identifier, None)
        return False, 0

    def record_failure(self, identifier: str) -> Tuple[bool, int]:
        now = time.time()
        record = self.attempts.get(identifier)
        if not record:
            self.attempts[identifier] = (1, now, 0)
            return False, 0
        count, _, locked_until = record
        if locked_until > now:
            return True, int(locked_until - now)
        
        count += 1
        if count >= self.max_attempts:
            locked_until = now + self.lockout_seconds
            self.attempts[identifier] = (count, now, locked_until)
            return True, self.lockout_seconds
        else:
            self.attempts[identifier] = (count, now, 0)
            return False, 0

    def record_success(self, identifier: str):
        self.attempts.pop(identifier, None)

login_rate_limiter = LoginRateLimiter()

# Password Reset Token Helpers
reset_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET, salt="allergraph-pwd-reset")

def generate_reset_token(email: str) -> str:
    raw_token = secrets.token_urlsafe(32)
    # Store token signature that includes email and timestamp
    signed = reset_serializer.dumps({"email": email.lower(), "raw": raw_token})
    return signed

def verify_reset_token(token: str, max_age: int = 3600) -> Optional[str]:
    try:
        data = reset_serializer.loads(token, max_age=max_age)
        return data.get("email")
    except (BadSignature, SignatureExpired):
        return None

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
