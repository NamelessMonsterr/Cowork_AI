"""
Planner Module - Orchestrates high-level reasoning and plan generation.

1. Receives user request
2. Gets computer state (Screenshot + Window info)
3. Consults LLM
4. Generates Execution Plan (ActionSteps)

Note: Execution is handled by the ReliableExecutor, not this class.
"""

import logging
from typing import Any

from assistant.agent.llm import AgentResponse, LLMClient
from assistant.computer.windows import WindowsComputer
from assistant.recovery.context import RecoveryContext
from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan

logger = logging.getLogger("Planner")


class Planner:
    def __init__(self, computer: WindowsComputer = None):
        """
        Initialize Planner.

        Args:
            computer: WindowsComputer instance for OBSERVATION only.
                      Execution is done by ReliableExecutor.
        """
        self.computer = computer or WindowsComputer()
        self.computer = computer or WindowsComputer()
        self.llm = LLMClient()
        # W12.6: Plugin Integration placeholder
        # In full implementation, we would inject:
        # self.tool_registry = ToolRegistry()
        # self.tool_router = ToolRouter(...)

    async def create_plan(self, user_task: str) -> list[dict[str, Any]]:
        """
        Generate a plan for the user task based on current state.

        Returns:
            List of step dictionaries (compatible with ActionStep schema)
        """
        logger.info(f"Planning for task: {user_task}")

        # 1. Observe
        # We use strict observation methods (no side effects)
        screenshot_path = self.computer.take_screenshot()
        active_window = self.computer.get_active_window()

        context = f"Active APP: {active_window.title if active_window else 'None'}"

        # 2. Think (LLM)
        # Fetch Skill Prompts
        skill_prompts = ""
        try:
            from assistant.main import state

            if state.skill_loader:
                skill_prompts = state.skill_loader.get_active_system_prompts()
        except ImportError:
            pass  # Circular import or test mode

        response: AgentResponse = self.llm.analyze_screen_and_plan(
            task=user_task,
            screenshot_path=screenshot_path,
            context=context,
            system_append=skill_prompts,
        )

        logger.info(f"LLM Thought: {response.thought}")

        plan = response.plan

        # 3. Handle Voice Reply
        if response.reply_text:
            speak_step = {
                "id": "voice_reply",
                "tool": "speak",
                "args": {"text": response.reply_text},
                "description": "Reply to user",
            }
            plan.insert(0, speak_step)

        # 4. Cleanup
        # (Optional cleanup of screenshot file if needed to save space)

        return plan

    async def generate_repair_plan(self, context: RecoveryContext) -> ExecutionPlan:
        """
        Generate a short, safe Repair Plan (W9.3).

        Constraints:
        - Max 5 steps
        - Safe tools only (focus, scroll, ocr)
        """
        logger.info(f"Generating Repair Plan for {context.failure_type.value}...")

        # 1. Observe (Fresh state)
        screenshot_path = self.computer.take_screenshot()

        # 2. Ask LLM
        # We construct a specific prompt for repair
        prompt_context = context.to_prompt_context()

        # NOTE: In a real implementation, we'd add specific LLM method or modify existing.
        # For this phase, we reuse analyze_screen_and_plan but with "REPAIR MODE" prefix.

        repair_task = f"""
        [REPAIR MODE]
        The previous step failed.
        Context: {prompt_context}

        Goal: Fix the state so we can retry the failed step.
        Rules:
        1. Max 5 steps.
        2. Use safe tools: focus_window, scroll, click (if safe), ocr.
        3. Do NOT assume the element is visible. Find it.
        """

        response: AgentResponse = self.llm.analyze_screen_and_plan(
            task=repair_task,
            screenshot_path=screenshot_path,
            context=f"REPAIRING: {context.failed_step.tool}",
        )

        steps = []
        for s in response.plan:
            steps.append(ActionStep(**s))

        # Hard constraint enforcement (W9 Safety)
        if len(steps) > 5:
            logger.warning("Repair plan too long, truncating to 5 steps.")
            steps = steps[:5]

        return ExecutionPlan(
            id=f"repair_{context.step_id}",
            task=f"Repair {context.failure_type.value}",
            steps=steps,
        )
