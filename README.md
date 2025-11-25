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

Existing SQLite databases are updated automatically at startup to add the
`price_paid`, `purchase_location`, `tasting_notes`, `experience_notes`, and
`rating` columns, so you can safely run the latest code without manual
migrations. New consumption history entries are stored in their own table and
created automatically on first run.

## Features

- Add wines with varietal, region, vintage, quantity, notes, price paid, and purchase location.
- Edit existing entries after they've been added.
- Filter and search by text or status (in cellar vs. enjoyed).
- Track bottle quantities and mark bottles as enjoyed or restocked with tasting and experience notes prompts.
- Remove bottles you no longer want to track.
- Switch between card and data-table views to see all details at a glance (use
  the Cards/Table toggle above the list).
- Capture tasting/experience notes and a 0–5 rating (0.1 increments) whenever
  you mark a bottle as enjoyed.
- Browse a dedicated Consumption History view to review past enjoyed bottles,
  including ratings and notes, and edit logged notes/ratings directly from that view.

SQLite persistence is handled automatically via SQLAlchemy; the app creates `cellar.db` in the project root on first run.
