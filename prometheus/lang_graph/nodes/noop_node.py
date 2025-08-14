"""No-operation router node for workflow routing.

This module provides a simple pass-through node that can be used for routing in
workflows without performing any operations. It acts as a structural element in
node graphs where a connection is needed but no processing is required.
"""

from prometheus.utils.logger_manager import get_logger
from typing import Dict


class NoopNode:
    """No-operation node that routes workflow without processing.

    This class implements a pass-through node that accepts any input and returns
    None without performing any operations. It serves as a routing element in
    node graphs where a connection point is needed but no actual processing
    should occur.
    """

    def __init__(self):
        self._logger = get_logger(__name__)

    def __call__(self, state: Dict) -> None:
        """Routes the workflow without performing any operations.

        Accepts any input and returns None, serving as a pass-through point
        in the workflow.

        Args:
          _: Any state - not used by this node.

        Returns:
          None always, as this node performs no operations.
        """
        for key, value in state.items():
            if isinstance(value, bool) or isinstance(value, int):
                self._logger.debug(f"State {key}: {value}")
        return
