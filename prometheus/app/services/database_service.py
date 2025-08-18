import logging

from sqlmodel import SQLModel, create_engine

from prometheus.app.services.base_service import BaseService


class DatabaseService(BaseService):
    def __init__(self, DATABASE_URL: str):
        self.engine = create_engine(DATABASE_URL, echo=True)
        self._logger = logging.getLogger("prometheus.app.services.database_service")

    # Create the database and tables
    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def start(self):
        """
        Start the database service by creating the database and tables.
        This method is called when the service is initialized.
        """
        self.create_db_and_tables()
        self._logger.info("Database and tables created successfully.")

    def close(self):
        """
        Close the database connection and release any resources.
        """
        self.engine.dispose()
        self._logger.info("Database connection closed.")
