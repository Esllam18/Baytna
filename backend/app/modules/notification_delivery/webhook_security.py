import hashlib, hmac

def sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

def verify_payload(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature: return False
    return hmac.compare_digest(sign_payload(payload, secret), signature.strip())
