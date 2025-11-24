# cellar_tracker

A lightweight Flask application for tracking your wine cellar. Add bottles, search and filter your collection, mark wines as enjoyed, and restock as you go.

## Setup

1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Start the development server (auto-reload is disabled by default to prevent a
   `SystemExit` some Windows IDEs trigger when Flask's reloader restarts the
   parent process):
   ```bash
   python app.py
   ```
   If you prefer live reloads, pass `use_reloader=True` in `app.run`.
3. Open your browser to [http://localhost:5000](http://localhost:5000).

## Features

- Add wines with varietal, region, vintage, quantity, and notes.
- Filter and search by text or status (in cellar vs. enjoyed).
- Track bottle quantities and mark bottles as enjoyed or restocked.
- Remove bottles you no longer want to track.

SQLite persistence is handled automatically via SQLAlchemy; the app creates `cellar.db` in the project root on first run.
