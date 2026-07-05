# main.py
import asyncio
from google.adk import Runner # Core execution layer for ADK applications
from readme_agent import readme_agent

async def main():
    # Initialize the runner with your agent
    runner = Runner(agent=readme_agent)
    
    # Target your local workspace directory
    target_repo = "." 
    prompt_message = f"Please scan the repository at path '{target_repo}' and generate its README.md file."
    
    print("🤖 Agent is analyzing your workspace directory...")
    
    # Run the agent session
    result = await runner.run_async(prompt_message)
    
    # Save the output directly into your workspace
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(result.text)
        
    print("✅ README.md successfully created and written to root directory!")

if __name__ == "__main__":
    asyncio.run(main())
