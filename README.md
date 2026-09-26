# BookMySpot 📅

A full-stack resource booking web application built with Flask, SQLAlchemy, and vanilla JavaScript. Users can book shared resources (like conference rooms) while the system automatically prevents double-bookings and suggests alternative time slots when conflicts occur.

## Features

- **Conflict-free booking** — interval-overlap detection ensures no resource is double-booked for overlapping time ranges
- **Smart slot suggestions** — when a requested time is unavailable, the app automatically finds and suggests the nearest free slots on that resource
- **Natural language booking** — type a request like *"Conference Room A tomorrow at 3pm for 2 hours"* and the app parses it into a booking automatically
- **Dynamic users** — no fixed user list; anyone can book under their name, and the system finds or creates that user automatically

## Tech Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript (vanilla, no framework)
- **NLP parsing:** `dateparser` library for extracting dates/times from plain text

## How It Works

The core logic lives in two functions in `app.py`:

- `has_conflict()` — checks whether a new booking's time range overlaps any existing booking on the same resource, using the interval condition `start1 < end2 AND start2 < end1`
- `find_available_slots()` — walks through a resource's existing bookings in time order and identifies gaps large enough for the requested duration, to power the "suggested slots" feature

## Running Locally

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install flask flask-sqlalchemy dateparser
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Project Structure

```
room-booking-system/
├── app.py              # Flask routes, booking logic, conflict detection, slot suggestions, NL parsing
├── models.py            # Database models (User, Resource, Booking)
├── templates/
│   └── index.html       # Frontend UI
└── requirements.txt     # Python dependencies
```