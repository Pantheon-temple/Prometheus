import pytest

from prometheus.tools import graph_traversal
from tests.test_utils import test_project_paths
from tests.test_utils.fixtures import neo4j_container_with_kg_fixture  # noqa: F401


@pytest.mark.slow
async def test_find_file_node_with_basename(neo4j_container_with_kg_fixture):  # noqa: F811
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_file_node_with_basename(
            test_project_paths.PYTHON_FILE.name, driver, 1000, 0
        )

        basename = test_project_paths.PYTHON_FILE.name
        relative_path = str(
            test_project_paths.PYTHON_FILE.relative_to(
                test_project_paths.TEST_PROJECT_PATH
            ).as_posix()
        )

        result_data = result[1]
        assert len(result_data) == 1
        assert "FileNode" in result_data[0]
        assert result_data[0]["FileNode"].get("basename", "") == basename
        assert result_data[0]["FileNode"].get("relative_path", "") == relative_path


@pytest.mark.slow
async def test_find_file_node_with_relative_path(neo4j_container_with_kg_fixture):  # noqa: F811
    relative_path = str(
        test_project_paths.MD_FILE.relative_to(test_project_paths.TEST_PROJECT_PATH).as_posix()
    )
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_file_node_with_relative_path(relative_path, driver, 1000, 0)

        basename = test_project_paths.MD_FILE.name

        result_data = result[1]
        assert len(result_data) == 1
        assert "FileNode" in result_data[0]
        assert result_data[0]["FileNode"].get("basename", "") == basename
        assert result_data[0]["FileNode"].get("relative_path", "") == relative_path


@pytest.mark.slow
async def test_find_ast_node_with_text_in_file_with_basename(neo4j_container_with_kg_fixture):  # noqa: F811
    basename = test_project_paths.PYTHON_FILE.name
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_ast_node_with_text_in_file_with_basename(
            "Hello world!", basename, driver, 1000, 0
        )

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "ASTNode" in result_row
            assert "Hello world!" in result_row["ASTNode"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("basename", "") == basename


@pytest.mark.slow
async def test_find_ast_node_with_text_in_file_with_relative_path(neo4j_container_with_kg_fixture):  # noqa: F811
    relative_path = str(
        test_project_paths.C_FILE.relative_to(test_project_paths.TEST_PROJECT_PATH).as_posix()
    )
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_ast_node_with_text_in_file_with_relative_path(
            "Hello world!", relative_path, driver, 1000, 0
        )

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "ASTNode" in result_row
            assert "Hello world!" in result_row["ASTNode"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("relative_path", "") == relative_path


@pytest.mark.slow
async def test_find_ast_node_with_type_in_file_with_basename(neo4j_container_with_kg_fixture):  # noqa: F811
    basename = test_project_paths.C_FILE.name
    node_type = "function_definition"
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_ast_node_with_type_in_file_with_basename(
            node_type, basename, driver, 1000, 0
        )

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "ASTNode" in result_row
            assert result_row["ASTNode"].get("type", "") == node_type
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("basename", "") == basename


@pytest.mark.slow
async def test_find_ast_node_with_type_in_file_with_relative_path(neo4j_container_with_kg_fixture):  # noqa: F811
    relative_path = str(
        test_project_paths.JAVA_FILE.relative_to(test_project_paths.TEST_PROJECT_PATH).as_posix()
    )
    node_type = "string_literal"
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_ast_node_with_type_in_file_with_relative_path(
            node_type, relative_path, driver, 1000, 0
        )

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "ASTNode" in result_row
            assert result_row["ASTNode"].get("type", "") == node_type
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("relative_path", "") == relative_path


@pytest.mark.slow
async def test_find_text_node_with_text(neo4j_container_with_kg_fixture):  # noqa: F811
    text = "Text under header C"
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_text_node_with_text(text, driver, 1000, 0)

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "TextNode" in result_row
            assert text in result_row["TextNode"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("relative_path", "") == "foo/test.md"


@pytest.mark.slow
async def test_find_text_node_with_text_in_file(neo4j_container_with_kg_fixture):  # noqa: F811
    basename = test_project_paths.MD_FILE.name
    text = "Text under header B"
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.find_text_node_with_text_in_file(text, basename, driver, 1000, 0)

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "TextNode" in result_row
            assert text in result_row["TextNode"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("basename", "") == basename


@pytest.mark.slow
async def test_get_next_text_node_with_node_id(neo4j_container_with_kg_fixture):  # noqa: F811
    node_id = 34
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.get_next_text_node_with_node_id(node_id, driver, 1000, 0)

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "TextNode" in result_row
            assert "Text under header D" in result_row["TextNode"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("relative_path", "") == "foo/test.md"


@pytest.mark.slow
async def test_preview_file_content_with_basename(neo4j_container_with_kg_fixture):  # noqa: F811
    basename = test_project_paths.PYTHON_FILE.name
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.preview_file_content_with_basename(basename, driver, 1000, 0)

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "preview" in result_row
            assert 'print("Hello world!")' in result_row["preview"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("basename", "") == basename

    basename = test_project_paths.MD_FILE.name
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.preview_file_content_with_basename(basename, driver, 1000, 0)

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "preview" in result_row
            assert "Text under header A" in result_row["preview"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("basename", "") == basename


@pytest.mark.slow
async def test_preview_file_content_with_relative_path(neo4j_container_with_kg_fixture):  # noqa: F811
    relative_path = str(
        test_project_paths.PYTHON_FILE.relative_to(test_project_paths.TEST_PROJECT_PATH).as_posix()
    )
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.preview_file_content_with_relative_path(
            relative_path, driver, 1000, 0
        )

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "preview" in result_row
            assert 'print("Hello world!")' in result_row["preview"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("relative_path", "") == relative_path

    relative_path = str(
        test_project_paths.MD_FILE.relative_to(test_project_paths.TEST_PROJECT_PATH).as_posix()
    )
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.preview_file_content_with_relative_path(
            relative_path, driver, 1000, 0
        )

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "preview" in result_row
            assert "Text under header A" in result_row["preview"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("relative_path", "") == relative_path


@pytest.mark.slow
async def test_read_code_with_basename(neo4j_container_with_kg_fixture):  # noqa: F811
    basename = test_project_paths.JAVA_FILE.name
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.read_code_with_basename(basename, 2, 3, driver, 1000, 0)

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "SelectedLines" in result_row
            assert "public static void main(String[] args) {" in result_row["SelectedLines"].get(
                "text", ""
            )
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("basename", "") == basename


@pytest.mark.slow
async def test_read_code_with_relative_path(neo4j_container_with_kg_fixture):  # noqa: F811
    relative_path = str(
        test_project_paths.C_FILE.relative_to(test_project_paths.TEST_PROJECT_PATH).as_posix()
    )
    neo4j_container, kg = neo4j_container_with_kg_fixture
    with neo4j_container.get_driver() as driver:
        result = graph_traversal.read_code_with_relative_path(relative_path, 5, 6, driver, 1000, 0)

        result_data = result[1]
        assert len(result_data) > 0
        for result_row in result_data:
            assert "SelectedLines" in result_row
            assert "return 0;" in result_row["SelectedLines"].get("text", "")
            assert "FileNode" in result_row
            assert result_row["FileNode"].get("relative_path", "") == relative_path
