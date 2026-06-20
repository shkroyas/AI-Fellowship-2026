# Task 4: Mini SQL Agent (Agentic System Task)

## Assignment Expectation
The objective is to build a simple agentic system that thinks, acts, and corrects itself. It must follow a required flow: Understand Query, Generate SQL, Execute Query, Error Handling (with up to 3 retries), and Final Output (including a natural language summary). The implementation should expose a FastAPI endpoint and follow a clean system design.

## What Has Been Done
As detailed in the `REPORT.md`:
- **State-Based Workflow**: Implemented a robust state-driven workflow routing through Planner, SQL Generator, Validator, Executor, and Summarizer agents.
- **Hybrid Execution Strategy**: Designed the system to use LLMs (OpenAI/Gemini) when available, but included deterministic heuristic fallbacks so the application remains fully functional locally even without API keys.
- **Dual Interfaces**: Exposed the workflow via a FastAPI backend (`main.py`) for programmatic access and a Streamlit chat interface (`streamlit_app.py`) for interactive use.
- **Safety & Robustness**: Included comprehensive safety rules to block destructive SQL, limit retries to 3, and safely execute queries against the ClassicModels PostgreSQL database.
