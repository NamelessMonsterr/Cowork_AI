"""
System Strategy - Handles OS-level actions: launch apps, run shell commands, open URLs.

This is the bridge between high-level tools (open_app, run_shell, open_url) and
the low-level WindowsComputer methods. Unlike UI strategies (UIA, Vision, Coords),
this strategy doesn't interact with UI elements - it executes system commands directly.

Priority: 5 (highest - checked before UI strategies)
"""

import logging
import webbrowser
from typing import Optional

from assistant.ui_contracts.schemas import ActionStep, UISelector
from .base import Strategy, StrategyResult

logger = logging.getLogger(__name__)


class SystemStrategy(Strategy):
    """
    Strategy for executing system-level actions that don't require UI automation.

    Supported tools:
    - open_app: Launch an application by name
    - run_shell / shell: Execute a shell command
    - open_url: Open a URL in the default browser
    """

    def __init__(self, computer=None):
        """
        Initialize SystemStrategy.

        Args:
            computer: WindowsComputer instance for executing OS commands.
                     If None, will be set later via set_computer().
        """
        self._computer = computer

    def set_computer(self, computer):
        """Set the computer instance (for lazy initialization)."""
        self._computer = computer

    @property
    def name(self) -> str:
        return "system"

    @property
    def priority(self) -> int:
        # Highest priority - check system commands first before trying UI automation
        return 5

    def can_handle(self, step: ActionStep) -> bool:
        """Check if this strategy can handle the given step."""
        return step.tool in [
            "open_app",
            "run_shell",
            "shell",
            "open_url",
            "restricted_shell",
        ]

    def execute(self, step: ActionStep) -> StrategyResult:
        """
        Execute the system action.

        Args:
            step: ActionStep containing the tool and args

        Returns:
            StrategyResult indicating success/failure
        """
        if not self._computer:
            return StrategyResult(
                success=False, error="SystemStrategy: No computer instance configured"
            )

        try:
            tool = step.tool
            args = step.parameters or {}

            if tool == "open_app":
                app_name = args.get("app_name") or args.get("name")
                if not app_name:
                    return StrategyResult(
                        success=False, error="open_app: Missing 'app_name' argument"
                    )

                logger.info(f"[SystemStrategy] Opening app: {app_name}")
                success = self._computer.launch_app(app_name)

                if success:
                    return StrategyResult(
                        success=True,
                        details={"action": "open_app", "app_name": app_name},
                    )
                else:
                    return StrategyResult(
                        success=False, error=f"Failed to launch app: {app_name}"
                    )

            elif tool in ["run_shell", "shell"]:
                command = args.get("command") or args.get("cmd")
                if not command:
                    return StrategyResult(
                        success=False, error="run_shell: Missing 'command' argument"
                    )

                logger.info(f"[SystemStrategy] Running shell: {command}")
                success = self._computer.run_shell(command)

                if success:
                    return StrategyResult(
                        success=True,
                        details={"action": "run_shell", "command": command},
                    )
                else:
                    return StrategyResult(
                        success=False, error=f"Shell command failed: {command}"
                    )

            elif tool == "open_url":
                url = args.get("url") or args.get("link")
                if not url:
                    return StrategyResult(
                        success=False, error="open_url: Missing 'url' argument"
                    )

                logger.info(f"[SystemStrategy] Opening URL: {url}")
                webbrowser.open(url)
                return StrategyResult(
                    success=True, output=f"Opened {url}", action_type="open_url"
                )

            elif tool == "restricted_shell":
                # Execute safe shell command via RestrictedShellTool
                try:
                    from assistant.tools.restricted_shell import RestrictedShellTool

                    engine = args.get("engine", "cmd")
                    command = args.get("command", "")
                    run_as_admin = args.get("run_as_admin", False)

                    tool_instance = RestrictedShellTool()
                    result = tool_instance.execute(
                        engine, command, run_as_admin, supervised=True
                    )

                    logger.info(
                        f"[SystemStrategy] Shell: {command[:50]}... exit={result.exit_code}"
                    )

                    output = result.stdout if result.stdout else result.stderr
                    if result.redacted:
                        output += "\n[Some output redacted for security]"

                    return StrategyResult(
                        success=(result.exit_code == 0),
                        output=output[:1000] if output else "",
                        error=result.stderr if result.exit_code != 0 else None,
                        action_type="restricted_shell",
                    )
                except Exception as e:
                    logger.error(f"[SystemStrategy] Shell failed: {e}")
                    return StrategyResult(
                        success=False,
                        error=f"Shell execution failed: {str(e)}",
                        action_type="restricted_shell",
                    )

            else:
                return StrategyResult(
                    success=False, error=f"Unknown system tool: {tool}"
                )

        except Exception as e:
            logger.exception(f"[SystemStrategy] Error executing {tool}")
            return StrategyResult(success=False, error=str(e))

    def find_element(self, step: ActionStep) -> Optional[UISelector]:
        """System strategy doesn't find UI elements."""
        return None

    def validate_element(self, selector: UISelector) -> bool:
        """System strategy doesn't validate UI elements."""
        return False
