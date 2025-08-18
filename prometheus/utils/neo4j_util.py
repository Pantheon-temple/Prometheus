from typing import Any, Iterator, Mapping, Optional, Sequence, Tuple

import neo4j

from prometheus.models.context import Context
from prometheus.utils.str_util import truncate_text

EMPTY_DATA_MESSAGE = "Your query returned empty result, please try a different query!"


def format_neo4j_data(data: Sequence[Mapping[str, Any]], max_token_per_result: int) -> str:
    """Format a Neo4j result into a string.

    Args:
      data: The result from a Neo4j query.
      max_token_per_result: Maximum number of tokens per result.

    Returns:
      A string representation of the result.
    """
    if not data:
        return EMPTY_DATA_MESSAGE

    output = ""
    for index, row_result in enumerate(data):
        output += f"Result {index + 1}:\n"
        for key in sorted(row_result.keys()):
            output += f"{key}: {str(row_result[key])}\n"
        output += "\n\n"
    return truncate_text(output.strip(), max_token_per_result)


def neo4j_data_for_context_generator(
    data: Optional[Sequence[Mapping[str, Any]]],
) -> Iterator[Context]:
    if data is None:
        return

    for search_result in data:
        search_result_keys = search_result.keys()
        # Skip if the result has no keys or only contains the "FileNode" key
        if len(search_result_keys) == 1:
            continue

        context = Context(
            relative_path=search_result["FileNode"]["relative_path"],
            content=(
                search_result.get("ASTNode", {}).get("text")
                or search_result.get("TextNode", {}).get("text")
                or search_result.get("preview", {}).get("text")
                or search_result.get("SelectedLines", {}).get("text")
            ),
            start_line_number=(
                search_result.get("ASTNode", {}).get("start_line")
                or search_result.get("SelectedLines", {}).get("start_line")
                or search_result.get("preview", {}).get("start_line")
            ),
            end_line_number=search_result.get("ASTNode", {}).get("end_line")
            or search_result.get("SelectedLines", {}).get("end_line")
            or search_result.get("preview", {}).get("end_line"),
        )

        yield context


def run_neo4j_query(
    query: str, driver: neo4j.GraphDatabase.driver, max_token_per_result: int
) -> Tuple[str, Sequence[Mapping[str, Any]]]:
    """Run a read-only Neo4j query and format the result into a string.

    Args:
      query: The query to run.
      driver: The Neo4j driver to use.
      max_token_per_result: Maximum number of tokens per result.

    Returns:
      A string representation of the result.
    """

    def query_transaction(tx):
        result = tx.run(query)
        data = result.data()
        return format_neo4j_data(data, max_token_per_result), data

    with driver.session() as session:
        return session.execute_read(query_transaction)


def run_neo4j_query_without_formatting(
    query: str, driver: neo4j.GraphDatabase.driver
) -> Sequence[Mapping[str, Any]]:
    """Run a read-only Neo4j query and return the result.

    Args:
      query: The query to run.
      driver: The Neo4j driver to use.

    Returns:
      result
    """

    def query_transaction(tx):
        result = tx.run(query)
        data = result.data()
        return data

    with driver.session() as session:
        return session.execute_read(query_transaction)
