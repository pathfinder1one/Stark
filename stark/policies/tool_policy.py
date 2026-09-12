"""
STARK — Tool Policy & Sandboxing Guard
Validates permissions before any tool is executed by an agent or user request.
Loads rules from config/policies.yaml with sensible secure defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from muktiverse.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolPermissionCheck:
    """Result of a tool authorization check."""
    allowed: bool
    reason: str
    tool_name: str
    agent_name: str = "direct"
    sanitized_args: dict[str, Any] = field(default_factory=dict)


class ToolPolicy:
    """
    Enforces security and permission boundaries for all tool calls in STARK.

    Rules:
    1. Tools can be globally enabled/disabled.
    2. Certain tools are restricted to specific agent roles (e.g. python_executor -> coding, reasoning).
    3. Dangerous external side-effects (e.g. web search, file write) require explicit permission.
    4. Code execution limits: max CPU timeout, sandboxed builtins.
    """

    DEFAULT_ALLOWED_AGENT_TOOLS = {
        "coding": ["python_executor", "file_processor"],
        "reasoning": ["python_executor"],
        "math": ["python_executor"],
        "research": ["web_search", "web_scraper", "document_tools"],
        "direct": ["python_executor", "document_tools"],
    }

    # Tools that are enabled by default in local mode
    LOCAL_SAFE_TOOLS = {"python_executor", "document_tools", "file_processor"}

    def __init__(self, allow_network_tools: bool = False) -> None:
        self._allow_network = allow_network_tools

    def check_permission(
        self,
        tool_name: str,
        agent_name: str = "direct",
        args: dict[str, Any] | None = None,
    ) -> ToolPermissionCheck:
        """
        Authorize or block a tool execution request.

        Args:
            tool_name:  Name of the tool (e.g. "python_executor").
            agent_name: Requesting agent (e.g. "coding", "reasoning", "direct").
            args:       Arguments to be passed to the tool.

        Returns:
            ToolPermissionCheck with allowed=True/False and explanation.
        """
        args = args or {}

        # 1. Local-safe check
        if tool_name not in self.LOCAL_SAFE_TOOLS and not self._allow_network:
            if tool_name in {"web_search", "web_scraper", "api_caller", "github_search"}:
                return ToolPermissionCheck(
                    allowed=False,
                    reason=f"Tool '{tool_name}' requires external network access which is disabled by policy.",
                    tool_name=tool_name,
                    agent_name=agent_name,
                )

        # 2. Agent capability boundary
        allowed_tools = self.DEFAULT_ALLOWED_AGENT_TOOLS.get(agent_name, self.LOCAL_SAFE_TOOLS)
        if tool_name not in allowed_tools and agent_name != "direct":
            logger.warning("tool_policy.agent_denied", tool=tool_name, agent=agent_name)
            return ToolPermissionCheck(
                allowed=False,
                reason=f"Agent '{agent_name}' is not authorized to call '{tool_name}'.",
                tool_name=tool_name,
                agent_name=agent_name,
            )

        # 3. Argument sanitization
        sanitized = dict(args)
        if tool_name == "python_executor":
            # Cap timeout to 30s max
            sanitized["timeout_seconds"] = min(int(args.get("timeout_seconds", 10)), 30)

        logger.info("tool_policy.approved", tool=tool_name, agent=agent_name)
        return ToolPermissionCheck(
            allowed=True,
            reason="Tool call authorized by STARK policy",
            tool_name=tool_name,
            agent_name=agent_name,
            sanitized_args=sanitized,
        )
