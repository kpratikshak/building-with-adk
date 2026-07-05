#  Native Processing agent
# allows passing the PDF directly as an input content file.

from google.adk.agents import Agent
from tools.prompts import pdf_extraction_prompt

# Switch to the stable production model
MODEL_NAME = "gemini-2.5-flash" 

pdf_agent = Agent(
    model=MODEL_NAME,
    name="PDFTextExtractor",
    description="Analyzes and extracts information directly from PDF documents.",
    instruction=pdf_extraction_prompt,
)
