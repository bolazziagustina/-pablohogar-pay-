from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from functools import wraps
import json
import uuid
import os
from datetime import datetime

app = Flask(__name__)

app.secret_key = "pablohogar-secret-key-2024"

ADMIN_USERNAME = "pablo"
ADMIN_PASSWORD = "pablohogar2024"

DB_FILE = os.path.join(os.path.dirname(__file__), "payments.json")


def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"links": [], "payments": []}


def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("admin"))
        else:
            error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def admin():
    db = load_db()
    return render_template("admin.html", links=db["links"], payments=db["payments"])


@app.route("/admin/create-link", methods=["POST"])
@login_required
def create_link():
    db = load_db()
    link_id = str(uuid.uuid4())[:8]
    new_link = {
        "id": link_id,
        "title": request.form.get("title", "Pago"),
        "description": request.form.get("description", ""),
        "amount": float(request.form.get("amount", 0)),
        "currency": request.form.get("currency", "UYU"),
        "client_name": request.form.get("client_name", ""),
        "client_email": request.form.get("client_email", ""),
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "single_use": request.form.get("single_use") == "on",
    }
    db["links"].append(new_link)
    save_db(db)
    return redirect(url_for("admin"))


@app.route("/admin/delete-link/<link_id>", methods=["POST"])
@login_required
def delete_link(link_id):
    db = load_db()
    db["links"] = [l for l in db["links"] if l["id"] != link_id]
    save_db(db)
    return redirect(url_for("admin"))


@app.route("/pay/<link_id>")
def checkout(link_id):
    db = load_db()
    link = next((l for l in db["links"] if l["id"] == link_id), None)
    if not link or link["status"] != "active":
        return render_template("expired.html"), 404
    return render_template("checkout.html", link=link)


@app.route("/pay/<link_id>/process", methods=["POST"])
def process_payment(link_id):
    db = load_db()
    link = next((l for l in db["links"] if l["id"] == link_id), None)
    if not link or link["status"] != "active":
        return jsonify({"error": "Link no válido"}), 404

    payment = {
        "id": str(uuid.uuid4())[:8],
        "link_id": link_id,
        "link_title": link["title"],
        "amount": link["amount"],
        "currency": link["currency"],
        "payer_name": request.form.get("name", ""),
        "payer_email": request.form.get("email", ""),
        "payer_phone": request.form.get("phone", ""),
        "card_last4": request.form.get("card_number", "")[-4:],
        "status": "approved",
        "paid_at": datetime.now().isoformat(),
    }
    db["payments"].append(payment)

    if link["single_use"]:
        for l in db["links"]:
            if l["id"] == link_id:
                l["status"] = "used"

    save_db(db)
    return redirect(url_for("confirmation", payment_id=payment["id"]))


@app.route("/confirmation/<payment_id>")
def confirmation(payment_id):
    db = load_db()
    payment = next((p for p in db["payments"] if p["id"] == payment_id), None)
    if not payment:
        return "Pago no encontrado", 404
    return render_template("confirmation.html", payment=payment)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
