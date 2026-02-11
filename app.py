from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "carpool.db"

app = Flask(__name__)


CREATE_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK(role IN ('driver', 'passenger')),
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    city TEXT NOT NULL,
    home_area TEXT NOT NULL,
    destination_area TEXT NOT NULL,
    commute_days TEXT NOT NULL,
    depart_time TEXT NOT NULL,
    return_time TEXT NOT NULL,
    car_make TEXT,
    car_model TEXT,
    car_color TEXT,
    plate_number TEXT,
    seats_available INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    proposed_fuel_share REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sender_id) REFERENCES profiles(id),
    FOREIGN KEY(receiver_id) REFERENCES profiles(id)
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_PROFILES_TABLE)
    conn.execute(CREATE_MESSAGES_TABLE)
    conn.commit()
    conn.close()


def validate_profile(payload: dict[str, Any]) -> tuple[bool, str]:
    required_fields = [
        "role",
        "full_name",
        "phone",
        "email",
        "home_area",
        "destination_area",
        "commute_days",
        "depart_time",
        "return_time",
    ]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    if payload["role"] not in {"driver", "passenger"}:
        return False, "Role must be either driver or passenger"

    if not isinstance(payload["commute_days"], list) or not payload["commute_days"]:
        return False, "Commute days must be a non-empty list"

    return True, ""


def row_to_profile(row: sqlite3.Row) -> dict[str, Any]:
    profile = dict(row)
    profile["commute_days"] = json.loads(profile["commute_days"])
    return profile


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/profiles", methods=["GET"])
def get_profiles() -> tuple[Any, int]:
    role = request.args.get("role")
    db = get_db()
    if role in {"driver", "passenger"}:
        rows = db.execute(
            "SELECT * FROM profiles WHERE city = 'Islamabad' AND role = ? ORDER BY created_at DESC",
            (role,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM profiles WHERE city = 'Islamabad' ORDER BY created_at DESC"
        ).fetchall()

    profiles = [row_to_profile(row) for row in rows]
    return jsonify(profiles), 200


@app.route("/api/profiles", methods=["POST"])
def create_profile() -> tuple[Any, int]:
    payload = request.get_json(silent=True) or {}
    is_valid, message = validate_profile(payload)
    if not is_valid:
        return jsonify({"error": message}), 400

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO profiles (
            role, full_name, phone, email, city, home_area, destination_area,
            commute_days, depart_time, return_time, car_make, car_model,
            car_color, plate_number, seats_available, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["role"],
            payload["full_name"],
            payload["phone"],
            payload["email"],
            "Islamabad",
            payload["home_area"],
            payload["destination_area"],
            json.dumps(payload["commute_days"]),
            payload["depart_time"],
            payload["return_time"],
            payload.get("car_make") or None,
            payload.get("car_model") or None,
            payload.get("car_color") or None,
            payload.get("plate_number") or None,
            payload.get("seats_available") or None,
            payload.get("notes") or None,
        ),
    )
    db.commit()

    new_profile = db.execute("SELECT * FROM profiles WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(row_to_profile(new_profile)), 201


@app.route("/api/messages", methods=["GET"])
def list_messages() -> tuple[Any, int]:
    profile_id = request.args.get("profile_id", type=int)
    if not profile_id:
        return jsonify({"error": "profile_id is required"}), 400

    db = get_db()
    rows = db.execute(
        """
        SELECT m.*, s.full_name AS sender_name, r.full_name AS receiver_name
        FROM messages m
        JOIN profiles s ON s.id = m.sender_id
        JOIN profiles r ON r.id = m.receiver_id
        WHERE sender_id = ? OR receiver_id = ?
        ORDER BY m.created_at DESC
        """,
        (profile_id, profile_id),
    ).fetchall()

    return jsonify([dict(row) for row in rows]), 200


@app.route("/api/messages", methods=["POST"])
def send_message() -> tuple[Any, int]:
    payload = request.get_json(silent=True) or {}
    required_fields = ["sender_id", "receiver_id", "message"]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    db = get_db()
    sender = db.execute("SELECT id FROM profiles WHERE id = ?", (payload["sender_id"],)).fetchone()
    receiver = db.execute("SELECT id FROM profiles WHERE id = ?", (payload["receiver_id"],)).fetchone()
    if not sender or not receiver:
        return jsonify({"error": "Sender or receiver profile does not exist"}), 404

    cursor = db.execute(
        """
        INSERT INTO messages (sender_id, receiver_id, message, proposed_fuel_share)
        VALUES (?, ?, ?, ?)
        """,
        (
            payload["sender_id"],
            payload["receiver_id"],
            payload["message"],
            payload.get("proposed_fuel_share") or None,
        ),
    )
    db.commit()

    sent = db.execute(
        """
        SELECT m.*, s.full_name AS sender_name, r.full_name AS receiver_name
        FROM messages m
        JOIN profiles s ON s.id = m.sender_id
        JOIN profiles r ON r.id = m.receiver_id
        WHERE m.id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()

    return jsonify(dict(sent)), 201


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
