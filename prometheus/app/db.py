from typing import Optional

from passlib.hash import bcrypt
from sqlmodel import Session, SQLModel, create_engine

from prometheus.app.entity.user import User
from prometheus.configuration.config import settings
from prometheus.utils.logger_manager import get_logger

engine = create_engine(settings.DATABASE_URL, echo=True)
_logger = get_logger(__name__)


# Create the database and tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Create a superuser and commit it to the database
def create_superuser(
    username: str,
    email: str,
    password: str,
    github_token: Optional[str] = None,
) -> None:
    """
    Create a new superuser and commit it to the database.

    Args:
        username (str): Desired username.
        email (str): Email address.
        password (str): Plaintext password (will be hashed).
        github_token (Optional[str]): Optional GitHub token.

    Returns:
        User: The created superuser instance.
    """
    with Session(engine) as session:
        if session.query(User).filter(User.username == username).first():
            raise ValueError(f"Username '{username}' already exists")
        if session.query(User).filter(User.email == email).first():
            raise ValueError(f"Email '{email}' already exists")

        hashed_password = bcrypt.hash(password)

        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            github_token=github_token,
            issue_credit=999999,
            is_superuser=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    _logger.info(f"Superuser '{username}' created successfully.")
