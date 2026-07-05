#If custom pdf pre-processing is mandatory)
# Cleaned up and updated to the stable model checkpoint.

from google.adk.agents import Agent
from tools.pdf_tools import extract_pdf_text
from tools.prompts import pdf_extraction_prompt

MODEL_NAME = "gemini-2.5-flash"

pdf_agent = Agent(
    model=MODEL_NAME,
    name="PDFTextExtractor",
    description="Extracts and structures text from PDF documents using localized tools.",
    instruction=pdf_extraction_prompt,
    tools=[extract_pdf_text],
)
