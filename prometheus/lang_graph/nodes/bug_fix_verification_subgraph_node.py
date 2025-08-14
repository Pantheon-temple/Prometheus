
from langchain_core.language_models.chat_models import BaseChatModel

from prometheus.docker.base_container import BaseContainer
from prometheus.lang_graph.subgraphs.bug_fix_verification_subgraph import BugFixVerificationSubgraph
from prometheus.lang_graph.subgraphs.issue_bug_state import IssueBugState
from prometheus.utils.logger_manager import get_logger


class BugFixVerificationSubgraphNode:
    def __init__(
        self,
        model: BaseChatModel,
        container: BaseContainer,
    ):
        self._logger = get_logger(__name__)
        self.subgraph = BugFixVerificationSubgraph(
            model=model,
            container=container,
        )

    def __call__(self, state: IssueBugState):
        self._logger.info("Enter bug_fix_verification_subgraph_node")
        self._logger.debug(f"reproduced_bug_file: {state['reproduced_bug_file']}")
        self._logger.debug(f"reproduced_bug_commands: {state['reproduced_bug_commands']}")

        output_state = self.subgraph.invoke(
            reproduced_bug_file=state["reproduced_bug_file"],
            reproduced_bug_commands=state["reproduced_bug_commands"],
        )

        self._logger.info(
            f"Passing bug reproducing test: {not bool(output_state['reproducing_test_fail_log'])}"
        )
        self._logger.debug(
            f"reproducing_test_fail_log: {output_state['reproducing_test_fail_log']}"
        )

        return {
            "reproducing_test_fail_log": output_state["reproducing_test_fail_log"],
        }
