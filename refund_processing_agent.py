"""
Multi-LLM Refund Processing System
Reference:
https://google.github.io/adk-docs/agents/multi-agents/#coordinatordispatcher-pattern
"""

from __future__ import annotations

import logging

from google.adk.agents import Agent

from tools.prompts import (
    top_level_prompt,
    purchase_history_subagent_prompt,
    check_eligibility_subagent_prompt,
    process_refund_subagent_prompt,
)

from tools.tools import (
    get_purchase_history,
    check_refund_eligibility,
    process_refund,
)

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

MODEL_NAME = "gemini-2.5-flash-preview-05-20"

ROOT_AGENT_NAME = "RefundMultiAgent"

ROOT_AGENT_DESCRIPTION = (
    "Customer refund multi-agent system for Crabby's Taffy."
)

ROOT_AGENT_INSTRUCTION = f"""
You are a coordinator agent responsible for orchestrating
specialized refund workflow agents.

Your objectives are:

- Execute the complete refund workflow.
- Delegate tasks to specialized agents.
- Minimize the number of conversation turns.
- Ask the customer questions only when absolutely necessary.
- Never perform tool actions yourself when a specialist agent exists.

{top_level_prompt}
"""

# ----------------------------------------------------------------------
# Helper Function
# ----------------------------------------------------------------------

def create_agent(
    *,
    name: str,
    description: str,
    instruction: str,
    tools: list,
    output_key: str | None = None,
) -> Agent:
    """
    Factory function to create ADK agents with shared configuration.
    """

    return Agent(
        model=MODEL_NAME,
        name=name,
        description=description,
        instruction=instruction,
        tools=tools,
        output_key=output_key,
    )

# ----------------------------------------------------------------------
# Specialist Agents
# ----------------------------------------------------------------------

purchase_history_agent = create_agent(
    name="PurchaseHistoryAgent",
    description="Retrieves and validates purchase history.",
    instruction=purchase_history_subagent_prompt,
    tools=[get_purchase_history],
    output_key="purchase_history",
)

eligibility_agent = create_agent(
    name="EligibilityAgent",
    description="Evaluates refund eligibility using company policies.",
    instruction=check_eligibility_subagent_prompt,
    tools=[check_refund_eligibility],
    output_key="is_refund_eligible",
)

process_refund_agent = create_agent(
    name="ProcessRefundAgent",
    description="Processes approved customer refunds.",
    instruction=process_refund_subagent_prompt,
    tools=[process_refund],
)

# ----------------------------------------------------------------------
# Root Coordinator Agent
# ----------------------------------------------------------------------

root_agent = Agent(
    model=MODEL_NAME,
    name=ROOT_AGENT_NAME,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=ROOT_AGENT_INSTRUCTION,
    sub_agents=[
        purchase_history_agent,
        eligibility_agent,
        process_refund_agent,
    ],
)

logger.info("Refund multi-agent system initialized successfully.")
