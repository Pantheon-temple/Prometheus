from typing import Mapping, Optional, Sequence

import neo4j
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph

from prometheus.docker.base_container import BaseContainer
from prometheus.git.git_repository import GitRepository
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.lang_graph.nodes.bug_get_regression_tests_subgraph_node import (
    BugGetRegressionTestsSubgraphNode,
)
from prometheus.lang_graph.nodes.bug_reproduction_subgraph_node import BugReproductionSubgraphNode
from prometheus.lang_graph.nodes.issue_bug_responder_node import IssueBugResponderNode
from prometheus.lang_graph.nodes.issue_not_verified_bug_subgraph_node import (
    IssueNotVerifiedBugSubgraphNode,
)
from prometheus.lang_graph.nodes.issue_verified_bug_subgraph_node import (
    IssueVerifiedBugSubgraphNode,
)
from prometheus.lang_graph.subgraphs.issue_bug_state import IssueBugState


class IssueBugSubgraph:
    def __init__(
        self,
        advanced_model: BaseChatModel,
        base_model: BaseChatModel,
        container: BaseContainer,
        kg: KnowledgeGraph,
        git_repo: GitRepository,
        neo4j_driver: neo4j.Driver,
        max_token_per_neo4j_result: int,
        build_commands: Optional[Sequence[str]] = None,
        test_commands: Optional[Sequence[str]] = None,
    ):
        # Construct bug reproduction node
        bug_reproduction_subgraph_node = BugReproductionSubgraphNode(
            advanced_model=advanced_model,
            base_model=base_model,
            container=container,
            kg=kg,
            git_repo=git_repo,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            test_commands=test_commands,
        )
        # Construct bug regression tests subgraph node
        bug_get_regression_tests_subgraph_node = BugGetRegressionTestsSubgraphNode(
            advanced_model=advanced_model,
            base_model=base_model,
            container=container,
            kg=kg,
            git_repo=git_repo,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
        )

        # Construct issue bug verified subgraph nodes
        issue_verified_bug_subgraph_node = IssueVerifiedBugSubgraphNode(
            advanced_model=advanced_model,
            base_model=base_model,
            container=container,
            kg=kg,
            git_repo=git_repo,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
            build_commands=build_commands,
            test_commands=test_commands,
        )
        # Construct issue not verified bug subgraph node
        issue_not_verified_bug_subgraph_node = IssueNotVerifiedBugSubgraphNode(
            advanced_model=advanced_model,
            base_model=base_model,
            kg=kg,
            git_repo=git_repo,
            container=container,
            neo4j_driver=neo4j_driver,
            max_token_per_neo4j_result=max_token_per_neo4j_result,
        )
        # Construct issue bug responder node
        issue_bug_responder_node = IssueBugResponderNode(base_model)

        # Create the state graph for the issue bug subgraph
        workflow = StateGraph(IssueBugState)
        # Add nodes to the workflow
        workflow.add_node("bug_reproduction_subgraph_node", bug_reproduction_subgraph_node)
        workflow.add_node(
            "bug_get_regression_tests_subgraph_node", bug_get_regression_tests_subgraph_node
        )

        workflow.add_node("issue_verified_bug_subgraph_node", issue_verified_bug_subgraph_node)
        workflow.add_node(
            "issue_not_verified_bug_subgraph_node", issue_not_verified_bug_subgraph_node
        )

        workflow.add_node("issue_bug_responder_node", issue_bug_responder_node)

        # Start with bug_get_regression_tests_subgraph_node if regression tests are to be run,
        # otherwise start with bug_reproduction_subgraph_node if reproduce tests are to be run,
        # otherwise start with issue_not_verified_bug_subgraph_node
        workflow.set_conditional_entry_point(
            lambda state: "bug_get_regression_tests_subgraph_node"
            if state["run_regression_test"]
            else "bug_reproduction_subgraph_node"
            if state["run_reproduce_test"]
            else "issue_not_verified_bug_subgraph_node",
            {
                "bug_get_regression_tests_subgraph_node": "bug_get_regression_tests_subgraph_node",
                "bug_reproduction_subgraph_node": "bug_reproduction_subgraph_node",
                "issue_not_verified_bug_subgraph_node": "issue_not_verified_bug_subgraph_node",
            },
        )
        # Add edges for the bug_get_regression_tests_subgraph_node
        workflow.add_conditional_edges(
            "bug_get_regression_tests_subgraph_node",
            lambda state: state["run_reproduce_test"],
            {True: "bug_reproduction_subgraph_node", False: "issue_not_verified_bug_subgraph_node"},
        )

        # Go to verified bug subgraph if the bug is verified, otherwise go to not verified bug subgraph
        workflow.add_conditional_edges(
            "bug_reproduction_subgraph_node",
            lambda state: state["reproduced_bug"]
            or state["run_build"]
            or state["run_existing_test"],
            {
                True: "issue_verified_bug_subgraph_node",
                False: "issue_not_verified_bug_subgraph_node",
            },
        )
        # Go to issue bug responder node if the bug is solved, otherwise go to not verified bug subgraph
        workflow.add_conditional_edges(
            "issue_verified_bug_subgraph_node",
            lambda state: bool(state["edit_patch"]),
            {True: "issue_bug_responder_node", False: "issue_not_verified_bug_subgraph_node"},
        )
        # Add edges for the issue bug responder node
        workflow.add_edge("issue_not_verified_bug_subgraph_node", "issue_bug_responder_node")
        workflow.add_edge("issue_bug_responder_node", END)

        self.subgraph = workflow.compile()

    def invoke(
        self,
        issue_title: str,
        issue_body: str,
        issue_comments: Sequence[Mapping[str, str]],
        run_build: bool,
        run_existing_test: bool,
        run_regression_test: bool,
        run_reproduce_test: bool,
        number_of_candidate_patch: int,
        recursion_limit: int = 30,
    ):
        config = {"recursion_limit": recursion_limit}

        input_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "issue_comments": issue_comments,
            "run_build": run_build,
            "run_existing_test": run_existing_test,
            "run_regression_test": run_regression_test,
            "run_reproduce_test": run_reproduce_test,
            "number_of_candidate_patch": number_of_candidate_patch,
        }

        output_state = self.subgraph.invoke(input_state, config)
        return {
            "edit_patch": output_state["edit_patch"],
            "passed_reproducing_test": output_state["passed_reproducing_test"],
            "passed_build": output_state["passed_build"],
            "passed_existing_test": output_state["passed_existing_test"],
            "passed_regression_test": bool(output_state.get("selected_regression_tests", []))
            and bool(output_state["edit_patch"]),
            "issue_response": output_state["issue_response"],
        }
