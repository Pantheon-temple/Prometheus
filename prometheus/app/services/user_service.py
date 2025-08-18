import logging
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlmodel import Session, or_, select

from prometheus.app.entity.user import User
from prometheus.app.services.base_service import BaseService
from prometheus.app.services.database_service import DatabaseService
from prometheus.exceptions.server_exception import ServerException
from prometheus.utils.jwt_utils import JWTUtils


class UserService(BaseService):
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.engine = database_service.engine
        self._logger = logging.getLogger("prometheus.app.services.user_service")
        self.ph = PasswordHasher()
        self.jwt_utils = JWTUtils()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        github_token: Optional[str] = None,
        issue_credit: int = 0,
        is_superuser: bool = False,
    ) -> None:
        """
        Create a new superuser and commit it to the database.

        Args:
            username (str): Desired username.
            email (str): Email address.
            password (str): Plaintext password (will be hashed).
            github_token (Optional[str]): Optional GitHub token.
            issue_credit (int): Optional issue credit.
            is_superuser (bool): Whether the user is a superuser.
        Returns:
            User: The created superuser instance.
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.username == username)
            if session.exec(statement).first():
                raise ValueError(f"Username '{username}' already exists")
            statement = select(User).where(User.email == email)
            if session.exec(statement).first():
                raise ValueError(f"Email '{email}' already exists")

            hashed_password = self.ph.hash(password)

            user = User(
                username=username,
                email=email,
                password_hash=hashed_password,
                github_token=github_token,
                issue_credit=issue_credit,
                is_superuser=is_superuser,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

    def login(self, username: str, email: str, password: str) -> str:
        """
        Log in a user by verifying their credentials and return an access token.

        Args:
            username (str): Username of the user.
            email (str): Email address of the user.
            password (str): Plaintext password.
        """
        with Session(self.engine) as session:
            statement = select(User).where(or_(User.username == username, User.email == email))
            user = session.exec(statement).first()

            if not user:
                raise ServerException(code=400, message="Invalid username or email")

            try:
                self.ph.verify(user.password_hash, password)
            except VerifyMismatchError:
                raise ServerException(code=400, message="Invalid password")

            # Generate and return a JWT token for the user
            token = self.jwt_utils.generate_token({"user_id": user.id})
            return token

    # Create a superuser and commit it to the database
    def create_superuser(
        self,
        username: str,
        email: str,
        password: str,
        github_token: Optional[str] = None,
    ) -> None:
        """
        Create a new superuser in the database.

        This method creates a superuser with the provided credentials and commits it to the database.
        """
        self.create_user(
            username, email, password, github_token, is_superuser=True, issue_credit=999999
        )
        self._logger.info(f"Superuser '{username}' created successfully.")

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieve a user by their ID.

        Args:
            user_id (int): The ID of the user to retrieve.

        Returns:
            User: The user instance if found, otherwise None.
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.id == user_id)
            return session.exec(statement).first()

    def get_issue_credit(self, user_id: int) -> int:
        """
        Retrieve the issue credit of a user by their ID.

        Args:
            user_id (int): The ID of the user.

        Returns:
            int: The issue credit of the user.
        """
        with Session(self.engine) as session:
            statement = select(User.issue_credit).where(User.id == user_id)
            result = session.exec(statement).first()
            return result

    def update_issue_credit(self, user_id: int, new_issue_credit) -> None:
        """
        Update the issue credit of a user by their ID.

        Args:
            user_id (int): The ID of the user.
            new_issue_credit (int): The new issue credit.
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.id == user_id)
            user = session.exec(statement).first()
            user.issue_credit = new_issue_credit
            session.add(user)
            session.commit()
