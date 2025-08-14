from typing import Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.docker.base_container import BaseContainer
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.subgraphs.build_and_test_subgraph import BuildAndTestSubgraph
from prometheus.lang_graph.subgraphs.issue_bug_state import IssueBugState
from prometheus.utils.logger_manager import get_logger


class BuildAndTestSubgraphNode:
    def __init__(
        self,
        container: BaseContainer,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        build_commands: Optional[Sequence[str]] = None,
        test_commands: Optional[Sequence[str]] = None,
    ):
        self.build_and_test_subgraph = BuildAndTestSubgraph(
            container=container,
            model=model,
            kg=kg,
            build_commands=build_commands,
            test_commands=test_commands,
        )
        self._logger = get_logger(__name__)

    def __call__(self, state: IssueBugState):
        exist_build = None
        build_command_summary = None
        build_fail_log = None
        exist_test = None
        test_command_summary = None
        existing_test_fail_log = None

        if "build_command_summary" in state and state["build_command_summary"]:
            exist_build = state["exist_build"]
            build_command_summary = state["build_command_summary"]
            build_fail_log = state["build_fail_log"]

        if "test_command_summary" in state and state["test_command_summary"]:
            exist_test = state["exist_test"]
            test_command_summary = state["test_command_summary"]
            existing_test_fail_log = state["existing_test_fail_log"]

        self._logger.info("Enters BuildAndTestSubgraphNode")

        output_state = self.build_and_test_subgraph.invoke(
            run_build=state["run_build"],
            run_existing_test=state["run_existing_test"],
            exist_build=exist_build,
            build_command_summary=build_command_summary,
            build_fail_log=build_fail_log,
            exist_test=exist_test,
            test_command_summary=test_command_summary,
            existing_test_fail_log=existing_test_fail_log,
        )

        self._logger.info(f"exist_build: {output_state['exist_build']}")
        self._logger.info(f"build_command_summary:\n{output_state['build_command_summary']}")
        self._logger.info(f"build_fail_log:\n{output_state['build_fail_log']}")
        self._logger.info(f"exist_test: {output_state['exist_test']}")
        self._logger.info(f"test_command_summary:\n{output_state['test_command_summary']}")
        self._logger.info(f"existing_test_fail_log:\n{output_state['existing_test_fail_log']}")

        return {
            "exist_build": output_state["exist_build"],
            "build_command_summary": output_state["build_command_summary"],
            "build_fail_log": output_state["build_fail_log"],
            "exist_test": output_state["exist_test"],
            "test_command_summary": output_state["test_command_summary"],
            "existing_test_fail_log": output_state["existing_test_fail_log"],
        }
