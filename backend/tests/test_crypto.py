from app.core.crypto import decrypt_secret, encrypt_secret


def test_roundtrip():
    secret = "ya29.fake-access-token-value"
    ciphertext = encrypt_secret(secret)
    assert ciphertext != secret
    assert decrypt_secret(ciphertext) == secret


def test_none_passthrough():
    assert encrypt_secret(None) is None
    assert decrypt_secret(None) is None


def test_garbage_fails_closed():
    assert decrypt_secret("not-a-real-token") is None
