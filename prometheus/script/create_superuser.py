import argparse
import re

from prometheus.app.services.database_service import DatabaseService
from prometheus.app.services.user_service import UserService
from prometheus.configuration.config import settings

database_service: DatabaseService = DatabaseService(settings.DATABASE_URL)
user_service: UserService = UserService(database_service)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a superuser account.")
    parser.add_argument("--username", required=True, help="Superuser username")
    parser.add_argument("--email", required=True, help="Superuser email")
    parser.add_argument("--password", required=True, help="Superuser password")
    parser.add_argument("--github_token", required=False, help="Optional GitHub token")

    args = parser.parse_args()

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(pattern, args.email):
        raise ValueError("Invalid email format")

    user_service.create_superuser(
        username=args.username,
        email=args.email,
        password=args.password,
        github_token=args.github_token,
    )
    print("Superuser account created!")
