from flask import Flask, request, jsonify, render_template
from models import db, User, Resource, Booking
from datetime import datetime, timedelta
import re
from dateparser.search import search_dates

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
db.init_app(app)

with app.app_context():
    db.create_all()
    if not Resource.query.first():
        db.session.add_all([
            Resource(name="Conference Room A", resource_type="room"),
            Resource(name="Conference Room B", resource_type="room"),
        ])
        db.session.commit()

def parse_booking_text(text):
    """Rule-based parser: pulls out a resource name, a date/time, and a duration from plain English."""
    resources = Resource.query.all()
    matched_resource = None
    for r in resources:
        if r.name.lower() in text.lower():
            matched_resource = r
            break

    duration_minutes = 60
    duration_match = re.search(r'for\s+(\d+)\s*(hour|hr|minute|min)', text, re.IGNORECASE)
    if duration_match:
        num = int(duration_match.group(1))
        unit = duration_match.group(2).lower()
        duration_minutes = num * 60 if 'hour' in unit or 'hr' in unit else num

    found = search_dates(text, settings={'PREFER_DATES_FROM': 'future'})
    if not found:
        return None
    matched_text, parsed_start = found[0]

    if ':' not in matched_text:
        parsed_start = parsed_start.replace(minute=0, second=0, microsecond=0)
    else:
        parsed_start = parsed_start.replace(second=0, microsecond=0)

    parsed_end = parsed_start + timedelta(minutes=duration_minutes)

    return {
        "resource_id": matched_resource.id if matched_resource else None,
        "resource_name": matched_resource.name if matched_resource else None,
        "start": parsed_start.isoformat(),
        "end": parsed_end.isoformat()
    }

def find_available_slots(resource_id, date, duration_minutes=60, day_start_hour=9, day_end_hour=18):
    """Finds free time slots of the given duration on a resource for a given day."""
    day_start = datetime.combine(date, datetime.min.time()).replace(hour=day_start_hour)
    day_end = datetime.combine(date, datetime.min.time()).replace(hour=day_end_hour)

    existing = Booking.query.filter(
        Booking.resource_id == resource_id,
        Booking.start_time < day_end,
        Booking.end_time > day_start
    ).order_by(Booking.start_time).all()

    free_slots = []
    cursor = day_start
    duration = timedelta(minutes=duration_minutes)

    for b in existing:
        gap = (b.start_time - cursor).total_seconds() / 60
        if gap >= duration_minutes:
            free_slots.append((cursor, cursor + duration))
        cursor = max(cursor, b.end_time)

    if (day_end - cursor).total_seconds() / 60 >= duration_minutes:
        free_slots.append((cursor, cursor + duration))

    return free_slots[:3]

def has_conflict(resource_id, start, end, exclude_booking_id=None):
    query = Booking.query.filter(
        Booking.resource_id == resource_id,
        Booking.start_time < end,
        Booking.end_time > start
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.first() is not None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/resources', methods=['GET'])
def list_resources():
    resources = Resource.query.all()
    return jsonify([{"id": r.id, "name": r.name, "type": r.resource_type} for r in resources])

@app.route('/bookings', methods=['POST'])
def create_booking():
    data = request.json
    start = datetime.fromisoformat(data['start_time'])
    end = datetime.fromisoformat(data['end_time'])
    user_name = data.get('user_name', '').strip()

    if not user_name:
        return jsonify({"error": "Please enter your name"}), 400

    if start >= end:
        return jsonify({"error": "start_time must be before end_time"}), 400

    if has_conflict(data['resource_id'], start, end):
        return jsonify({"error": "This resource is already booked for that time slot"}), 409

    user = User.query.filter(db.func.lower(User.name) == user_name.lower()).first()
    if not user:
        user = User(name=user_name)
        db.session.add(user)
        db.session.commit()

    booking = Booking(
        resource_id=data['resource_id'],
        user_id=user.id,
        start_time=start,
        end_time=end
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"message": "Booking confirmed", "booking_id": booking.id}), 201

@app.route('/bookings/<int:resource_id>', methods=['GET'])
def get_bookings(resource_id):
    bookings = Booking.query.filter_by(resource_id=resource_id).order_by(Booking.start_time).all()
    return jsonify([{
        "id": b.id, "user": b.user.name,
        "start": b.start_time.isoformat(), "end": b.end_time.isoformat()
    } for b in bookings])

@app.route('/suggest/<int:resource_id>', methods=['GET'])
def suggest_slots(resource_id):
    date_str = request.args.get('date')
    duration = int(request.args.get('duration', 60))
    date = datetime.fromisoformat(date_str).date()

    slots = find_available_slots(resource_id, date, duration)
    return jsonify([
        {"start": s.isoformat(), "end": e.isoformat()} for s, e in slots
    ])

@app.route('/parse', methods=['POST'])
def parse_text():
    data = request.json
    text = data.get('text', '')
    result = parse_booking_text(text)

    if not result or not result.get('start'):
        return jsonify({"error": "Couldn't understand that. Try mentioning a room and a time, like 'Conference Room A tomorrow at 3pm'."}), 400
    if not result['resource_id']:
        return jsonify({"error": "Couldn't figure out which room. Please mention the room name exactly."}), 400

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)