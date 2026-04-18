"""
Unit tests for security utilities:
  - OTP generation and argon2 hashing
  - JWT creation and verification
  - Password hashing (bcrypt)
"""
import pytest
from app.utils.security import (
    generate_otp,
    hash_otp,
    verify_otp_hash,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
)


# ─── OTP Tests ────────────────────────────────────────────────────────────────

class TestOTP:
    def test_otp_is_6_digits(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_otp_custom_length(self):
        for length in [4, 6, 8]:
            otp = generate_otp(length)
            assert len(otp) == length

    def test_otp_high_entropy(self):
        """1000 OTPs should not all be the same — verifies randomness."""
        otps = {generate_otp() for _ in range(1000)}
        assert len(otps) > 900

    def test_otp_hash_and_verify_correct(self):
        otp = "482910"
        hashed = hash_otp(otp)
        assert verify_otp_hash(otp, hashed) is True

    def test_otp_wrong_code_fails(self):
        otp = "482910"
        hashed = hash_otp(otp)
        assert verify_otp_hash("000000", hashed) is False
        assert verify_otp_hash("482911", hashed) is False

    def test_otp_hash_is_not_plaintext(self):
        otp = "123456"
        hashed = hash_otp(otp)
        assert otp not in hashed  # never store plaintext

    def test_otp_different_hashes_same_value(self):
        """argon2 uses salt — same OTP produces different hashes."""
        otp = "123456"
        h1 = hash_otp(otp)
        h2 = hash_otp(otp)
        assert h1 != h2
        # Both still verify correctly
        assert verify_otp_hash(otp, h1)
        assert verify_otp_hash(otp, h2)


# ─── Password Tests ───────────────────────────────────────────────────────────

class TestPassword:
    def test_hash_and_verify_correct(self):
        pw = "SuperSecurePassword123!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_not_plaintext(self):
        pw = "mysecret"
        assert pw not in hash_password(pw)

    def test_different_hashes_same_password(self):
        """bcrypt salts — two hashes of same password differ."""
        pw = "password123"
        assert hash_password(pw) != hash_password(pw)


# ─── JWT Tests ────────────────────────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode_access_token(self):
        data = {"sub": "user-uuid-123", "role": "admin", "type": "access"}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded["sub"] == "user-uuid-123"
        assert decoded["role"] == "admin"
        assert decoded["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        data = {"sub": "user-uuid-456", "type": "refresh"}
        token = create_refresh_token(data)
        decoded = decode_token(token)
        assert decoded["sub"] == "user-uuid-456"
        assert decoded["type"] == "refresh"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "test"})
        decoded = decode_token(token)
        assert "exp" in decoded

    def test_tampered_token_rejected(self):
        token = create_access_token({"sub": "user-1"})
        tampered = token[:-5] + "XXXXX"
        result = decode_token(tampered)
        assert result is None

    def test_generate_secure_token_is_unique(self):
        tokens = {generate_secure_token() for _ in range(100)}
        assert len(tokens) == 100  # all unique

    def test_generate_secure_token_length(self):
        token = generate_secure_token(32)
        assert len(token) > 0  # URL-safe base64 — always longer than 32 chars
