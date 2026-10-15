import pytest
from app.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    generate_csrf_token,
    verify_csrf_token,
    generate_reset_token,
    verify_reset_token,
    LoginRateLimiter,
)

def test_password_hashing():
    pw = "SuperSecret123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_password_strength():
    # Too short
    ok, msg = validate_password_strength("Short1!")
    assert ok is False
    assert "8 characters" in msg

    # Missing uppercase
    ok, msg = validate_password_strength("lowercase1!")
    assert ok is False
    assert "uppercase" in msg

    # Missing lowercase
    ok, msg = validate_password_strength("UPPERCASE1!")
    assert ok is False
    assert "lowercase" in msg

    # Missing digit
    ok, msg = validate_password_strength("NoDigitsHere!")
    assert ok is False
    assert "number" in msg

    # Valid
    ok, msg = validate_password_strength("ValidPassword123!")
    assert ok is True
    assert msg is None

def test_csrf_tokens():
    session_id = "test-session-123"
    token = generate_csrf_token(session_id)
    assert token is not None
    assert len(token) > 20

    # Verification success
    assert verify_csrf_token(token, session_id) is True

    # Verification failure on mismatched session
    assert verify_csrf_token(token, "different-session") is False

    # Verification failure on tampered token
    assert verify_csrf_token(token + "tampered", session_id) is False

def test_reset_token():
    email = "test@allergraph.local"
    token = generate_reset_token(email)
    assert token is not None

    extracted = verify_reset_token(token, max_age=60)
    assert extracted == email

    # Invalid token verification
    assert verify_reset_token("invalid-token") is None

def test_login_rate_limiter():
    limiter = LoginRateLimiter(max_attempts=3, lockout_seconds=60)
    ip = "192.168.1.100"

    locked, _ = limiter.is_locked(ip)
    assert locked is False

    # 1st failure
    locked, _ = limiter.record_failure(ip)
    assert locked is False

    # 2nd failure
    locked, _ = limiter.record_failure(ip)
    assert locked is False

    # 3rd failure triggers lockout
    locked, remaining = limiter.record_failure(ip)
    assert locked is True
    assert remaining > 0

    locked, remaining = limiter.is_locked(ip)
    assert locked is True

    # Success resets lockout
    limiter.record_success(ip)
    locked, _ = limiter.is_locked(ip)
    assert locked is False
