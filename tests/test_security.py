from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hashing_and_verification() -> None:
    password_hash = hash_password("secure-pass-123")

    assert password_hash != "secure-pass-123"
    assert verify_password("secure-pass-123", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_access_token_signature_and_payload_validation() -> None:
    token = create_access_token({"sub": 1, "role": "student"}, "test-secret")

    assert decode_access_token(token, "test-secret") == {"sub": 1, "role": "student", "iat": decode_access_token(token, "test-secret")["iat"], "exp": decode_access_token(token, "test-secret")["exp"]}
    assert decode_access_token(token, "wrong-secret") is None
