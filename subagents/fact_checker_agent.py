from google.adk import Agent
from google.adk.tools import google_search

fact_checker_agent = Agent(
    model="gemini-2.5-flash",
    name="FactChecker",
    description="Cross-references extracted document claims against live web data.",
    instruction=(
        "Analyze the provided text block. Identify any concrete data points, "
        "historical facts, or statistical claims. Use the google_search tool to "
        "verify if they match trusted live public records. Output a structured "
        "report labeling claims as Verified, Contradicted, or Unverifiable."
    ),
    tools=[google_search], # Leverages ADK's built-in web search tool
)
