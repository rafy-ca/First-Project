# Islamabad Intracity Carpool App

A fresh Flask + SQLite application for managing an Islamabad-only intracity carpool network for drivers and passengers.

## Features
- Register **drivers** and **passengers** with personal details.
- Capture car details (especially for drivers).
- Store regular commute route (A → B and B → A), days, and timings.
- List all available drivers and passengers so people can find route overlap.
- In-app contact endpoint to exchange pickup/drop details and propose fuel cost sharing.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:5000`

## API endpoints
- `POST /api/profiles`
- `GET /api/profiles?role=driver|passenger`
- `POST /api/messages`
- `GET /api/messages?profile_id=<id>`
