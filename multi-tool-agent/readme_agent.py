# readme_agent.py
from google.adk import Agent
from tools.repo_tools import analyze_workspace

MODEL_NAME = "gemini-2.5-flash"

# High-fidelity prompt targeting professional open-source standards
README_INSTRUCTION = """
You are a Staff Technical Writer and Open Source Developer. 
Your job is to generate a comprehensive, visually appealing, and highly professional README.md file for a GitHub repository.

CRITICAL INSTRUCTIONS:
1. Use the `analyze_workspace` tool to inspect the codebase structure, directory patterns, and dependency files first.
2. Based on the files found (e.g., Python, Node.js, Go), determine the exact language, build systems, and stack dependencies.
3. Write a production-grade README.md. Do NOT use generic placeholders like "Insert description here". Infer descriptions from the directory names and config contents.

The README must contain the following structural layout:
- # Project Title (Clear, engaging, and brief)
- Short project description & core value proposition.
- 🚀 Features (Bulleted list of core capabilities).
- 🛠️ Tech Stack & Dependencies.
- 📦 Installation & Setup instructions (Tailored exactly to the package managers found, e.g., npm install, pip install, uv, etc.).
- 💻 Usage Examples (Include code blocks showing how to import/run the project).
- 🤝 Contributing guidelines and License framework.

Output ONLY valid, un-encapsulated Markdown code.
"""

readme_agent = Agent(
    model=MODEL_NAME,
    name="ReadmeGenerator",
    description="Analyzes code repository assets and auto-generates professional GitHub documentation.",
    instruction=README_INSTRUCTION,
    tools=[analyze_workspace]
)
