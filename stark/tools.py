"""
STARK — Tool Manager
Wraps MuktiVerse's ToolRegistry with STARK's security ToolPolicy.
Ensures every tool call is authorized, sandboxed, and verified.
"""
from __future__ import annotations

from typing import Any
from muktiverse.tools.registry import initialize_tools, get_tool, get_all_tools
from muktiverse.tools.base import ToolOutput
from muktiverse.logging import get_logger

from stark.policies.tool_policy import ToolPolicy

logger = get_logger(__name__)


class STARKToolManager:
    """
    Manages available tools, policy enforcement, and execution for STARK.
    """

    def __init__(self, policy: ToolPolicy | None = None) -> None:
        self.policy = policy or ToolPolicy()
        self._initialized = False

    def startup(self) -> None:
        """Initialize all MuktiVerse tools."""
        if not self._initialized:
            initialize_tools()
            self._initialized = True
            logger.info("stark.tools.initialized", available=[t.name for t in get_all_tools()])

    async def execute(
        self,
        tool_name: str,
        agent_name: str = "direct",
        **kwargs: Any,
    ) -> ToolOutput:
        """
        Execute a tool after passing policy validation.

        Args:
            tool_name:  Tool identifier (e.g. "python_executor").
            agent_name: Requesting agent or "direct".
            kwargs:     Tool arguments.

        Returns:
            ToolOutput with success status and result/error.
        """
        self.startup()

        # Step 1: Policy validation
        check = self.policy.check_permission(tool_name, agent_name=agent_name, args=kwargs)
        if not check.allowed:
            logger.warning("stark.tools.blocked", tool=tool_name, reason=check.reason)
            return ToolOutput(success=False, result=None, error=check.reason)

        # Step 2: Tool lookup
        try:
            tool = get_tool(tool_name)
        except Exception as e:
            return ToolOutput(success=False, result=None, error=str(e))

        # Step 3: Sandboxed safe execution
        args = check.sanitized_args or kwargs
        logger.info("stark.tools.executing", tool=tool_name, agent=agent_name)
        return await tool.safe_execute(**args)
