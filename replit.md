# Running on Replit

This is a Python command-line quantitative research project, not a web app. Click **Run** to execute the sample in `main.py`; its output appears in the console. The Run command sets `PYTHONPATH=src` so imports resolve from the existing `src/` layout. The command exits when the sample finishes; no server or web preview is expected.

Dependencies are declared in `pyproject.toml` and installed in Replit. To run the automated checks from the Shell, use `python -m pytest -q`. No secrets or external services are needed for the current demo and tests.

The sample uses a fixed example date and prices. It does not process a real trading session yet; the next research milestone requires a complete WIN tick-data session and validation against the manual backtest.