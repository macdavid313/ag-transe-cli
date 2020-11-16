"""
File: connection.py
Created Date: Monday, 16th November 2020 7:12:09 pm
Author: Tianyu Gu (macdavid313@gmail.com)
"""

import logging
import os
from typing import Dict

from franz.openrdf.repository.repository import Repository, RepositoryConnection
from franz.openrdf.sail.allegrographserver import AllegroGraphServer

logging.basicConfig(
    format="%(levelname)s - %(asctime)s: %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)


def load_ag_env() -> Dict[str, str]:
    return {
        "host": os.getenv("AGRAPH_HOST"),
        "port": os.getenv("AGRAPH_PORT"),
        "user": os.getenv("AGRAPH_USER"),
        "password": os.getenv("AGRAPH_PASSWORD"),
    }


class AG_CONN:
    _conn: RepositoryConnection

    def __init__(self, repo_name: str):
        self._ag_conn_credential = load_ag_env()
        _ag_server = AllegroGraphServer(**self._ag_conn_credential)
        _ag_catalog = _ag_server.openCatalog(os.getenv("AGRAPH_CATALOG"))
        self._repo = _ag_catalog.getRepository(repo_name, Repository.OPEN)
        self._conn = self._repo.getConnection()
        logging.info(
            "Connecting to AllegroGraph Server: '%s:%s', Catalog: '%s', Repository: '%s'",
            self._ag_conn_credential["host"],
            self._ag_conn_credential["port"],
            os.getenv("AGRAPH_CATALOG"),
            repo_name,
        )

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._conn.close()
        self._repo.shutDown()

    @staticmethod
    def renew_or_create(repo_name: str) -> None:
        _ag_server = AllegroGraphServer(**load_ag_env())
        _ag_catalog = _ag_server.openCatalog(os.getenv("AGRAPH_CATALOG"))
        try:
            if repo_name in _ag_catalog.listRepositories():
                logging.info(f"Existing '%s' found", repo_name)
                repo = _ag_catalog.getRepository(repo_name, Repository.RENEW)
            else:
                logging.info(f"Repo '%s' does not exist, creating ...", repo_name)
                repo = _ag_catalog.createRepository(repo_name)
            repo.initialize()
            logging.info(f"'%s' has been successfully initialized", repo_name)
            repo.shutDown()
        except BaseException as exception:
            logging.info(
                f"Cannot initialize repository due to error: %s",
                exception,
            )
