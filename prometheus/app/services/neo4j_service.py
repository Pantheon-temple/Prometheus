"""Service for managing Neo4j database driver."""

import logging

from neo4j import GraphDatabase

from prometheus.app.services.base_service import BaseService


class Neo4jService(BaseService):
    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str):
        self._logger = logging.getLogger("prometheus.app.services.neo4j_service")
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_username, neo4j_password),
            connection_timeout=1200,
            max_transaction_retry_time=1200,
            keep_alive=True,
        )

    def close(self):
        self.neo4j_driver.close()
        self._logger.info("Neo4j driver connection closed.")
