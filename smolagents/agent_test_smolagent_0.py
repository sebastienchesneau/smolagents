from smolagents import CodeAgent, DuckDuckGoSearchTool

# --- bootstrap : racine du dépôt importable (base.py / base_tools.py y restent) ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from base import build_model

# Let's pretend we have a function that fetches the highest-rated catering services.
agent = CodeAgent(tools=[DuckDuckGoSearchTool()], model=build_model())

# Run the agent to find the best catering service
result = agent.run(
    "Search for the best music recommendations for a party at the Wayne's mansion."
)

print(result)   # Output: Gotham Catering Co.
