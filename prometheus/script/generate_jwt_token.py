import base64
import secrets


def generate_jwt_secret_token(length: int = 64) -> str:
    """
    Generate a secure JWT secret token.
    """
    token_bytes = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(token_bytes).decode("utf-8")


if __name__ == "__main__":
    secret = generate_jwt_secret_token()
    print(f"JWT_SECRET_TOKEN={secret}")
