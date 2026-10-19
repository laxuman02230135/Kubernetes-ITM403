"""A small user management REST API for the Kubernetes assignment."""
import re

import psycopg
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from db import connect

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@app.errorhandler(psycopg.errors.UniqueViolation)
def duplicate_email(error):
    return jsonify(error="Email already exists."), 409


@app.errorhandler(psycopg.Error)
def database_error(error):
    # Never return connection details or credentials to clients.
    return jsonify(error="Database temporarily unavailable."), 503


def user_input():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(error="Provide a JSON object with name and email."), 400)
    name, email = data.get("name"), data.get("email")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        return None, (jsonify(error="Name must contain 1 to 100 characters."), 400)
    if not isinstance(email, str):
        return None, (jsonify(error="A valid email is required."), 400)
    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return None, (jsonify(error="A valid email is required."), 400)
    return (name.strip(), email), None


@app.get("/healthz")
def health():
    # Liveness does not depend on PostgreSQL.
    return jsonify(status="alive")


@app.get("/ready")
def ready():
    with connect() as connection:
        connection.execute("SELECT 1")
    return jsonify(status="ready")


@app.get("/users")
def list_users():
    with connect() as connection:
        users = connection.execute("SELECT id, name, email FROM users ORDER BY id").fetchall()
    return jsonify(users)


@app.post("/users")
def create_user():
    values, error = user_input()
    if error:
        return error
    with connect() as connection:
        user = connection.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id, name, email",
            values,
        ).fetchone()
    return jsonify(user), 201, {"Location": f"/users/{user['id']}"}


@app.get("/users/<int:user_id>")
def get_user(user_id):
    with connect() as connection:
        user = connection.execute(
            "SELECT id, name, email FROM users WHERE id = %s", (user_id,)
        ).fetchone()
    if user is None:
        return jsonify(error="User not found."), 404
    return jsonify(user)


@app.put("/users/<int:user_id>")
def update_user(user_id):
    values, error = user_input()
    if error:
        return error
    with connect() as connection:
        user = connection.execute(
            "UPDATE users SET name = %s, email = %s WHERE id = %s RETURNING id, name, email",
            (*values, user_id),
        ).fetchone()
    if user is None:
        return jsonify(error="User not found."), 404
    return jsonify(user)


@app.delete("/users/<int:user_id>")
def delete_user(user_id):
    with connect() as connection:
        user = connection.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,)).fetchone()
    if user is None:
        return jsonify(error="User not found."), 404
    return "", 204
