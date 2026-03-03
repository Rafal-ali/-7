import os
import sqlite3
import socket
from datetime import datetime, timedelta

import bcrypt
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smart-parking-secret-key")

BASE_DIR = os.path.dirname(__file__)
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "instance", "parking.db")
DB_PATH = os.environ.get("DB_PATH", DEFAULT_DB_PATH)
SCHEMA_PATH = os.path.join(BASE_DIR, "instance", "schema.sql")
HOURLY_RATE = 1000
CANCELLATION_TAX_RATE = 0.10
MIN_CANCELLATION_TAX = 500
SERVER_PORT = 5000


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_connection() as connection:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            connection.executescript(schema_file.read())

        admin_username = "admin"
        admin_password = "admin123"
        existing_admin = connection.execute(
            "SELECT id FROM users WHERE username = ?", (admin_username,)
        ).fetchone()
        if not existing_admin:
            hashed_password = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            connection.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (admin_username, hashed_password, "admin"),
            )

        slots_count = connection.execute("SELECT COUNT(*) AS total FROM slots").fetchone()["total"]
        if slots_count == 0:
            connection.executemany(
                "INSERT INTO slots (status, car_number, user_id) VALUES ('free', NULL, NULL)",
                [() for _ in range(6)],
            )


init_db()


def require_login():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return None


def require_admin():
    if session.get("role") != "admin":
        flash("هذه الصفحة متاحة فقط للمشرف", "danger")
        return redirect(url_for("dashboard"))
    return None


def notify(message: str, category: str = "info") -> None:
    flash(message, category)
    notifications = session.get("notifications", [])
    notifications.insert(
        0,
        {
            "message": message,
            "category": category,
            "time": datetime.now().strftime("%H:%M"),
        },
    )
    session["notifications"] = notifications[:10]


def get_local_ip() -> str:
    try:
        host_name = socket.gethostname()
        return socket.gethostbyname(host_name)
    except OSError:
        return "127.0.0.1"


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db_connection() as connection:
            user = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("تم تسجيل الدخول بنجاح!", "success")
            return redirect(url_for("dashboard"))

        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT s.id, s.status, s.car_number, s.user_id, u.username AS owner_name
            FROM slots s
            LEFT JOIN users u ON u.id = s.user_id
            ORDER BY s.id
            """
        ).fetchall()

    slots = [
        (row["id"], row["status"], row["car_number"], row["user_id"], row["owner_name"])
        for row in rows
    ]

    if session.get("role") == "customer":
        return render_template("customer_dashboard.html", slots=slots, role="customer")

    return render_template("dashboard.html", slots=slots, role=session.get("role", "operator"))


@app.route("/slot/<int:slot_id>/toggle", methods=["POST"])
def slot_toggle(slot_id: int):
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    role = session.get("role", "operator")
    current_user_id = session.get("user_id")

    with get_db_connection() as connection:
        slot = connection.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
        if not slot:
            notify("الموقف غير موجود", "danger")
            return redirect(url_for("dashboard"))

        if slot["status"] == "free":
            car_number = request.form.get("car_number", "").strip()
            hours_raw = request.form.get("hours", "1")
            try:
                hours = max(1, int(hours_raw))
            except ValueError:
                hours = 1

            if not car_number:
                notify("يرجى إدخال رقم السيارة", "danger")
                return redirect(url_for("dashboard"))

            if role == "customer":
                existing = connection.execute(
                    "SELECT id FROM slots WHERE status = 'occupied' AND user_id = ?",
                    (current_user_id,),
                ).fetchone()
                if existing:
                    notify(f"لا يمكنك حجز أكثر من موقف واحد. ألغِ موقف رقم {existing['id']} أولاً", "danger")
                    return redirect(url_for("dashboard"))

                connection.execute(
                    "UPDATE slots SET status = 'occupied', car_number = ?, user_id = ? WHERE id = ?",
                    (car_number, current_user_id, slot_id),
                )
            else:
                connection.execute(
                    "UPDATE slots SET status = 'occupied', car_number = ?, user_id = NULL WHERE id = ?",
                    (car_number, slot_id),
                )

            entry_time = datetime.now()
            exit_time = entry_time + timedelta(hours=hours)
            total_price = hours * HOURLY_RATE

            connection.execute(
                "INSERT INTO revenue (date, amount) VALUES (?, ?)",
                (entry_time.strftime("%Y-%m-%d"), total_price),
            )

            session["entry_time"] = entry_time.strftime("%Y-%m-%d %H:%M")
            session["exit_time"] = exit_time.strftime("%Y-%m-%d %H:%M")
            session["slot_id"] = slot_id
            session["total_price"] = total_price
            session["late_fee_added"] = False

            notify(f"تم الحجز بنجاح. المجموع: {total_price} دينار", "success")
        else:
            if role == "customer" and slot["user_id"] != current_user_id:
                notify("لا يمكنك إلغاء حجز لا يخصك", "danger")
                return redirect(url_for("dashboard"))

            cancellation_tax = 0
            if role == "customer" and slot["user_id"] == current_user_id:
                booking_total = 0
                if session.get("slot_id") == slot_id:
                    try:
                        booking_total = int(session.get("total_price", 0))
                    except (TypeError, ValueError):
                        booking_total = 0

                if booking_total <= 0:
                    booking_total = HOURLY_RATE

                cancellation_tax = max(int(booking_total * CANCELLATION_TAX_RATE), MIN_CANCELLATION_TAX)
                connection.execute(
                    "INSERT INTO revenue (date, amount) VALUES (?, ?)",
                    (datetime.now().strftime("%Y-%m-%d"), cancellation_tax),
                )

            connection.execute(
                "UPDATE slots SET status = 'free', car_number = NULL, user_id = NULL WHERE id = ?",
                (slot_id,),
            )

            if session.get("slot_id") == slot_id:
                session.pop("entry_time", None)
                session.pop("exit_time", None)
                session.pop("slot_id", None)
                session.pop("total_price", None)
                session.pop("late_fee", None)
                session.pop("late_fee_added", None)

            if cancellation_tax > 0:
                notify(f"تم إلغاء الحجز وتم احتساب ضريبة إلغاء: {cancellation_tax} دينار", "warning")
            else:
                notify("تم إلغاء/إنهاء الحجز", "success")

        connection.commit()

    return redirect(url_for("dashboard"))


@app.route("/admin/reset_slots", methods=["POST"])
def reset_slots():
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    with get_db_connection() as connection:
        connection.execute("UPDATE slots SET status = 'free', car_number = NULL, user_id = NULL")
        connection.commit()

    flash("تم إعادة تعيين جميع المواقف", "success")
    return redirect(url_for("slots"))


@app.route("/slots", methods=["GET", "POST"])
def slots():
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    with get_db_connection() as connection:
        if request.method == "POST":
            slot_id = request.form.get("slot_id", "").strip()
            try:
                if slot_id:
                    connection.execute(
                        "INSERT INTO slots (id, status, car_number, user_id) VALUES (?, 'free', NULL, NULL)",
                        (int(slot_id),),
                    )
                else:
                    connection.execute("INSERT INTO slots (status, car_number, user_id) VALUES ('free', NULL, NULL)")
                connection.commit()
                flash("تم إضافة الموقف بنجاح", "success")
            except sqlite3.IntegrityError:
                flash("رقم الموقف موجود مسبقاً", "danger")

        rows = connection.execute("SELECT id, status, car_number FROM slots ORDER BY id").fetchall()

    slots_data = [(row["id"], row["status"], row["car_number"]) for row in rows]
    return render_template("slots.html", slots=slots_data)


@app.route("/slots/toggle/<int:slot_id>", methods=["POST"])
def slots_toggle(slot_id: int):
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    with get_db_connection() as connection:
        row = connection.execute("SELECT status FROM slots WHERE id = ?", (slot_id,)).fetchone()
        if not row:
            flash("الموقف غير موجود", "danger")
            return redirect(url_for("slots"))

        new_status = "occupied" if row["status"] == "free" else "free"
        if new_status == "free":
            connection.execute("UPDATE slots SET status = 'free', car_number = NULL, user_id = NULL WHERE id = ?", (slot_id,))
        else:
            connection.execute("UPDATE slots SET status = 'occupied' WHERE id = ?", (slot_id,))
        connection.commit()

    flash("تم تحديث حالة الموقف", "success")
    return redirect(url_for("slots"))


@app.route("/slots/delete/<int:slot_id>", methods=["POST"])
def slots_delete(slot_id: int):
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    with get_db_connection() as connection:
        connection.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
        connection.commit()

    flash("تم حذف الموقف", "success")
    return redirect(url_for("slots"))


@app.route("/users", methods=["GET", "POST"])
def users():
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    with get_db_connection() as connection:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            role = request.form.get("role", "operator").strip()

            if username and password and role:
                hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                try:
                    connection.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        (username, hashed_password, role),
                    )
                    connection.commit()
                    flash("تم إضافة المستخدم", "success")
                except sqlite3.IntegrityError:
                    flash("اسم المستخدم موجود مسبقاً", "danger")

        rows = connection.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()

    users_data = [(row["id"], row["username"], "", row["role"]) for row in rows]
    return render_template("users.html", users=users_data)


@app.route("/users/delete/<int:user_id>", methods=["POST"])
def users_delete(user_id: int):
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    with get_db_connection() as connection:
        row = connection.execute("SELECT username, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            flash("المستخدم غير موجود", "danger")
            return redirect(url_for("users"))

        if row["username"] == "admin" or row["role"] == "admin":
            flash("لا يمكن حذف المشرف", "danger")
            return redirect(url_for("users"))

        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()

    flash("تم حذف المستخدم", "success")
    return redirect(url_for("users"))


@app.route("/account", methods=["GET", "POST"])
def account():
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    username = session.get("username", "")

    if request.method == "POST":
        new_password = request.form.get("new_password", "").strip()
        if new_password:
            hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            with get_db_connection() as connection:
                connection.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
                connection.commit()
            flash("تم تحديث كلمة المرور", "success")

    return render_template("account.html", username=username)


@app.route("/analytics")
def analytics():
    auth_redirect = require_login()
    if auth_redirect:
        return auth_redirect

    admin_redirect = require_admin()
    if admin_redirect:
        return admin_redirect

    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT date, SUM(amount) AS total FROM revenue GROUP BY date ORDER BY date"
        ).fetchall()

    labels = [row["date"] for row in rows]
    values = [row["total"] for row in rows]
    return render_template("analytics.html", labels=labels, values=values)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("يرجى إدخال جميع الحقول", "danger")
            return render_template("signup.html")

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        with get_db_connection() as connection:
            existing = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                flash("اسم المستخدم موجود مسبقاً.", "danger")
            else:
                connection.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, 'customer')",
                    (username, hashed_password),
                )
                connection.commit()
                flash("تم إنشاء الحساب بنجاح! سجل دخولك الآن.", "success")
                return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    return signup()


if __name__ == "__main__":
    runtime_port = int(os.environ.get("PORT", SERVER_PORT))
    local_ip = get_local_ip()
    print(f"Local Network URL: http://{local_ip}:{runtime_port}")
    app.run(host="0.0.0.0", port=runtime_port,debug=False)
