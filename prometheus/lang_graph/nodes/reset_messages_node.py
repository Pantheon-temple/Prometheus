"""Message state reset handler for workflow loops.

This module provides functionality to reset message states in workflow loops,
allowing the same state attribute to be reused across multiple iterations. It
supports clearing both list-type message collections and string-type message
states.

The module is specifically designed for workflows where:
- Message history needs to be cleared between loop iterations
- The same state attribute name is reused
"""

import logging
import threading
from typing import Dict


class ResetMessagesNode:
    """Resets message states for workflow loop iterations.

    This class provides functionality to clear or reset message states between
    workflow loop iterations. It handles both list-type message collections
    (by clearing the list) and string-type messages (by returning an empty
    string state).

    The node is typically used in loops where:
    - Message history needs to be cleared for the next iteration
    - The same state key is reused throughout the loop
    """

    def __init__(self, message_state_key: str):
        """Initializes the ResetMessagesNode with a target state key.

        Args:
          message_state_key: String identifying which state attribute should
            be reset during node execution.
        """
        self.message_state_key = message_state_key
        self._logger = logging.getLogger(
            f"thread-{threading.get_ident()}.prometheus.lang_graph.nodes.reset_messages_node"
        )

    def __call__(self, state: Dict):
        """Resets the specified message state for the next iteration.

        Handles two types of message states:
        1. List-type: Clears the list in place
        2. String-type: Returns a new state with empty string

        Args:
          state: Current workflow state containing the message attribute to be reset.

        Returns:
          For string-type messages: Dictionary with empty string state
          For list-type messages: None (list is cleared in place)
        """
        self._logger.debug(f"Resetting {self.message_state_key} in state.")
        if isinstance(state[self.message_state_key], list):
            state[self.message_state_key].clear()
        elif isinstance(state[self.message_state_key], str):
            return {self.message_state_key: ""}
