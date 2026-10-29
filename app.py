
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from functools import wraps
from datetime import date
import sqlite3

app = Flask(__name__)
app.secret_key = "smartlab-dev-key-change-before-deployment"


# ==================================================
# DEMO ACCOUNTS
# ==================================================

DEMO_USERS = {
    "student": {
        "password": "student123",
        "role": "student"
    },
    "admin": {
        "password": "admin123",
        "role": "admin"
    }
}


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_db_connection():
    connection = sqlite3.connect("smartlab.db")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

def initialize_database():
    """
    Verify required tables and add missing ownership columns.
    Existing database records are preserved.
    """

    connection = get_db_connection()

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        table_names = {row["name"] for row in tables}

        required_tables = {
            "equipment",
            "bookings",
            "maintenance"
        }

        missing_tables = required_tables - table_names

        if missing_tables:
            raise RuntimeError(
                "Missing database tables: "
                + ", ".join(sorted(missing_tables))
                + ". Run init_db.py first."
            )

        # Add missing booking columns.
        booking_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(bookings)"
            ).fetchall()
        }

        if "owner_username" not in booking_columns:
            connection.execute(
                """
                ALTER TABLE bookings
                ADD COLUMN owner_username TEXT
                """
            )

        if "roll_number" not in booking_columns:
            connection.execute(
                """
                ALTER TABLE bookings
                ADD COLUMN roll_number TEXT
                """
            )

        # Add missing maintenance columns.
        maintenance_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(maintenance)"
            ).fetchall()
        }

        if "roll_number" not in maintenance_columns:
            connection.execute(
                """
                ALTER TABLE maintenance
                ADD COLUMN roll_number TEXT
                """
            )

        if "owner_username" not in maintenance_columns:
            connection.execute(
                """
                ALTER TABLE maintenance
                ADD COLUMN owner_username TEXT
                """
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==================================================
# ACCESS CONTROL
# ==================================================

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "username" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


def role_required(required_role):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):

            if "username" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))

            if session.get("role") != required_role:

                if session.get("role") == "admin":
                    return redirect(url_for("admin_dashboard"))

                return redirect(url_for("student_dashboard"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


# ==================================================
# LOGIN
# ==================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if "username" in session:

        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("student_dashboard"))

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get("password", "")

        selected_role = request.form.get(
            "role", ""
        ).strip()

        user = DEMO_USERS.get(username)

        if (
            user
            and user["password"] == password
            and user["role"] == selected_role
        ):

            session.clear()
            session["username"] = username
            session["role"] = user["role"]

            flash("Login successful!", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("student_dashboard"))

        flash(
            "Invalid username, password, or selected role.",
            "error"
        )

    return render_template("login.html")


# ==================================================
# HOME
# ==================================================

@app.route("/home")
@login_required
def home():

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    return redirect(url_for("student_dashboard"))


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have logged out successfully.", "success")

    return redirect(url_for("login"))


# ==================================================
# STUDENT DASHBOARD
# ==================================================

@app.route("/student-dashboard")
@role_required("student")
def student_dashboard():

    connection = get_db_connection()

    try:
        booking_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE owner_username = ?
            """,
            (session["username"],)
        ).fetchone()[0]

        pending_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE owner_username = ?
              AND status = 'Pending'
            """,
            (session["username"],)
        ).fetchone()[0]

        maintenance_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM maintenance
            WHERE owner_username = ?
            """,
            (session["username"],)
        ).fetchone()[0]

        return render_template(
            "student_dashboard.html",
            username=session["username"],
            booking_count=booking_count,
            pending_count=pending_count,
            maintenance_count=maintenance_count
        )

    finally:
        connection.close()


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route("/admin-dashboard")
@role_required("admin")
def admin_dashboard():

    connection = get_db_connection()

    try:
        equipment_count = connection.execute(
            "SELECT COUNT(*) FROM equipment"
        ).fetchone()[0]

        booking_count = connection.execute(
            "SELECT COUNT(*) FROM bookings"
        ).fetchone()[0]

        maintenance_count = connection.execute(
            "SELECT COUNT(*) FROM maintenance"
        ).fetchone()[0]

        pending_bookings = connection.execute(
            """
            SELECT COUNT(*)
            FROM bookings
            WHERE status = 'Pending'
            """
        ).fetchone()[0]

        return render_template(
            "admin_dashboard.html",
            username=session["username"],
            equipment_count=equipment_count,
            booking_count=booking_count,
            maintenance_count=maintenance_count,
            pending_bookings=pending_bookings
        )

    finally:
        connection.close()


# ==================================================
# VIEW EQUIPMENT
# ==================================================

@app.route("/equipment")
@login_required
def equipment():

    connection = get_db_connection()

    try:
        items = connection.execute(
            """
            SELECT *
            FROM equipment
            ORDER BY name
            """
        ).fetchall()

        return render_template(
            "equipment.html",
            equipment=items,
            role=session.get("role")
        )

    finally:
        connection.close()


# ==================================================
# ADD EQUIPMENT - ADMIN ONLY
# ==================================================

@app.route("/add-equipment", methods=["GET", "POST"])
@role_required("admin")
def add_equipment():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        quantity_text = request.form.get(
            "quantity", ""
        ).strip()

        if not name or not quantity_text:
            flash(
                "Enter the equipment name and quantity.",
                "error"
            )
            return redirect(url_for("add_equipment"))

        try:
            quantity = int(quantity_text)

            if quantity < 1:
                raise ValueError

        except ValueError:
            flash(
                "Quantity must be a positive whole number.",
                "error"
            )
            return redirect(url_for("add_equipment"))

        connection = get_db_connection()

        try:
            existing = connection.execute(
                """
                SELECT id
                FROM equipment
                WHERE LOWER(name) = LOWER(?)
                """,
                (name,)
            ).fetchone()

            if existing:
                flash(
                    "This equipment already exists.",
                    "error"
                )
                return redirect(url_for("add_equipment"))

            connection.execute(
                """
                INSERT INTO equipment (name, quantity, available)
                VALUES (?, ?, ?)
                """,
                (name, quantity, quantity)
            )

            connection.commit()

            flash(
                "Equipment added successfully!",
                "success"
            )

            return redirect(url_for("equipment"))

        except sqlite3.Error:
            connection.rollback()

            flash(
                "Could not add equipment. Please try again.",
                "error"
            )

        finally:
            connection.close()

        return redirect(url_for("add_equipment"))

    return render_template("add_equipment.html")


# ==================================================
# BOOK EQUIPMENT - BOTH LOGGED-IN ROLES
# ==================================================

@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking():

    if request.method == "POST":

        student_name = request.form.get(
            "student_name", ""
        ).strip()

        roll_number = request.form.get(
            "roll_number", ""
        ).strip()

        equipment_name = request.form.get(
            "equipment_name", ""
        ).strip()

        booking_date = request.form.get(
            "booking_date", ""
        ).strip()

        time_slot = request.form.get(
            "time_slot", ""
        ).strip()

        purpose = request.form.get(
            "purpose", ""
        ).strip()

        if not all([
            student_name,
            roll_number,
            equipment_name,
            booking_date,
            time_slot
        ]):
            flash(
                "Please fill in all required booking fields.",
                "error"
            )
            return redirect(url_for("booking"))

        try:
            selected_date = date.fromisoformat(booking_date)

            if selected_date < date.today():
                flash(
                    "You cannot book equipment for a past date.",
                    "error"
                )
                return redirect(url_for("booking"))

        except ValueError:
            flash(
                "Please select a valid booking date.",
                "error"
            )
            return redirect(url_for("booking"))

        connection = get_db_connection()

        try:
            item = connection.execute(
                """
                SELECT name
                FROM equipment
                WHERE name = ?
                """,
                (equipment_name,)
            ).fetchone()

            if item is None:
                flash(
                    "Please select valid equipment.",
                    "error"
                )
                return redirect(url_for("booking"))

            connection.execute(
                """
                INSERT INTO bookings (
                    student_name,
                    roll_number,
                    equipment_name,
                    booking_date,
                    time_slot,
                    purpose,
                    owner_username
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_name,
                    roll_number,
                    equipment_name,
                    booking_date,
                    time_slot,
                    purpose,
                    session["username"]
                )
            )

            connection.commit()

            flash(
                "Booking submitted successfully! "
                "Await administrator approval.",
                "success"
            )

            if session.get("role") == "admin":
                return redirect(url_for("view_bookings"))

            return redirect(url_for("my_bookings"))

        except sqlite3.Error:
            connection.rollback()

            flash(
                "Booking could not be saved. Please try again.",
                "error"
            )

        finally:
            connection.close()

        return redirect(url_for("booking"))

    # Pass equipment to the dropdown in booking.html.
    connection = get_db_connection()

    try:
        equipment_items = connection.execute(
            "SELECT * FROM equipment ORDER BY name"
        ).fetchall()

        return render_template(
            "booking.html",
            equipment=equipment_items
        )

    finally:
        connection.close()


# ==================================================
# STUDENT - VIEW OWN BOOKINGS
# ==================================================

@app.route("/my-bookings")
@role_required("student")
def my_bookings():

    connection = get_db_connection()

    try:
        bookings = connection.execute(
            """
            SELECT *
            FROM bookings
            WHERE owner_username = ?
            ORDER BY id DESC
            """,
            (session["username"],)
        ).fetchall()

        return render_template(
            "bookings.html",
            bookings=bookings,
            my_bookings=True
        )

    finally:
        connection.close()


# ==================================================
# ADMIN - VIEW ALL BOOKINGS
# ==================================================

@app.route("/bookings")
@role_required("admin")
def view_bookings():

    connection = get_db_connection()

    try:
        bookings = connection.execute(
            """
            SELECT *
            FROM bookings
            ORDER BY id DESC
            """
        ).fetchall()

        return render_template(
            "bookings.html",
            bookings=bookings,
            my_bookings=False
        )

    finally:
        connection.close()


# ==================================================
# ADMIN - APPROVE OR REJECT BOOKINGS
# ==================================================

@app.route(
    "/update-booking/<int:booking_id>",
    methods=["POST"]
)
@role_required("admin")
def update_booking(booking_id):

    action = request.form.get("action", "")

    if action not in ["Approved", "Rejected"]:
        flash("Invalid booking action.", "error")
        return redirect(url_for("view_bookings"))

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        booking_record = connection.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = ?
            """,
            (booking_id,)
        ).fetchone()

        if booking_record is None:
            connection.rollback()
            flash("Booking not found.", "error")
            return redirect(url_for("view_bookings"))

        old_status = booking_record["status"]
        equipment_name = booking_record["equipment_name"]

        if old_status == action:
            connection.commit()
            flash(
                f"Booking is already {action.lower()}.",
                "error"
            )
            return redirect(url_for("view_bookings"))

        if action == "Approved":

            item = connection.execute(
                """
                SELECT quantity, available
                FROM equipment
                WHERE name = ?
                """,
                (equipment_name,)
            ).fetchone()

            if item is None:
                connection.rollback()
                flash("Equipment not found.", "error")
                return redirect(url_for("view_bookings"))

            approved_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM bookings
                WHERE equipment_name = ?
                  AND booking_date = ?
                  AND time_slot = ?
                  AND status = 'Approved'
                  AND id != ?
                """,
                (
                    equipment_name,
                    booking_record["booking_date"],
                    booking_record["time_slot"],
                    booking_id
                )
            ).fetchone()[0]

            if approved_count >= item["quantity"]:
                connection.rollback()
                flash(
                    "No more units are available for this time slot.",
                    "error"
                )
                return redirect(url_for("view_bookings"))

            # Restore stock if this booking was previously rejected.
            if old_status != "Approved":

                if item["available"] <= 0:
                    connection.rollback()
                    flash(
                        "No equipment units are currently available.",
                        "error"
                    )
                    return redirect(url_for("view_bookings"))

                connection.execute(
                    """
                    UPDATE equipment
                    SET available = available - 1
                    WHERE name = ?
                      AND available > 0
                    """,
                    (equipment_name,)
                )

        elif old_status == "Approved" and action == "Rejected":

            connection.execute(
                """
                UPDATE equipment
                SET available = MIN(quantity, available + 1)
                WHERE name = ?
                """,
                (equipment_name,)
            )

        connection.execute(
            """
            UPDATE bookings
            SET status = ?
            WHERE id = ?
            """,
            (action, booking_id)
        )

        connection.commit()

        flash(
            f"Booking successfully {action.lower()}.",
            "success"
        )

    except sqlite3.Error:
        connection.rollback()
        flash(
            "A database error occurred while updating the booking.",
            "error"
        )

    finally:
        connection.close()

    return redirect(url_for("view_bookings"))


# ==================================================
# REPORT MAINTENANCE - BOTH ROLES
# ==================================================

@app.route("/maintenance", methods=["GET", "POST"])
@login_required
def maintenance():

    if request.method == "POST":

        student_name = request.form.get(
            "student_name", ""
        ).strip()

        roll_number = request.form.get(
            "roll_number", ""
        ).strip()

        equipment_name = request.form.get(
            "equipment_name", ""
        ).strip()

        issue_type = request.form.get(
            "issue_type", ""
        ).strip()

        description = request.form.get(
            "description", ""
        ).strip()

        if not all([
            student_name,
            roll_number,
            equipment_name,
            issue_type,
            description
        ]):
            flash(
                "Please complete all required maintenance fields.",
                "error"
            )
            return redirect(url_for("maintenance"))

        connection = get_db_connection()

        try:
            item = connection.execute(
                """
                SELECT name
                FROM equipment
                WHERE name = ?
                """,
                (equipment_name,)
            ).fetchone()

            if item is None:
                flash(
                    "Please select valid equipment.",
                    "error"
                )
                return redirect(url_for("maintenance"))

            connection.execute(
                """
                INSERT INTO maintenance (
                    student_name,
                    equipment_name,
                    issue_type,
                    description,
                    roll_number,
                    owner_username
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    student_name,
                    equipment_name,
                    issue_type,
                    description,
                    roll_number,
                    session["username"]
                )
            )

            connection.commit()

            flash(
                "Maintenance report submitted successfully!",
                "success"
            )

            if session.get("role") == "admin":
                return redirect(url_for("maintenance_requests"))

            return redirect(url_for("my_maintenance"))

        except sqlite3.Error:
            connection.rollback()

            flash(
                "Maintenance report could not be saved. Please try again.",
                "error"
            )

        finally:
            connection.close()

        return redirect(url_for("maintenance"))

    # Pass equipment to the dropdown in maintenance.html.
    connection = get_db_connection()

    try:
        equipment_items = connection.execute(
            "SELECT * FROM equipment ORDER BY name"
        ).fetchall()

        return render_template(
            "maintenance.html",
            equipment=equipment_items
        )

    finally:
        connection.close()


# ==================================================
# STUDENT - VIEW OWN MAINTENANCE REPORTS
# ==================================================

@app.route("/my-maintenance")
@role_required("student")
def my_maintenance():

    connection = get_db_connection()

    try:
        reports = connection.execute(
            """
            SELECT *
            FROM maintenance
            WHERE owner_username = ?
            ORDER BY id DESC
            """,
            (session["username"],)
        ).fetchall()

        return render_template(
            "maintenance_requests.html",
            reports=reports,
            my_reports=True
        )

    finally:
        connection.close()


# ==================================================
# ADMIN - VIEW ALL MAINTENANCE REPORTS
# ==================================================

@app.route("/maintenance-requests")
@role_required("admin")
def maintenance_requests():

    connection = get_db_connection()

    try:
        reports = connection.execute(
            """
            SELECT *
            FROM maintenance
            ORDER BY id DESC
            """
        ).fetchall()

        return render_template(
            "maintenance_requests.html",
            reports=reports,
            my_reports=False
        )

    finally:
        connection.close()


# ==================================================
# ADMIN - MARK MAINTENANCE AS RESOLVED
# ==================================================

@app.route(
    "/update-maintenance/<int:report_id>",
    methods=["POST"]
)
@role_required("admin")
def update_maintenance(report_id):

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE maintenance
            SET status = ?
            WHERE id = ?
            """,
            ("Resolved", report_id)
        )

        connection.commit()

        if cursor.rowcount > 0:
            flash(
                "Maintenance request marked as resolved!",
                "success"
            )
        else:
            flash(
                "Maintenance request not found.",
                "error"
            )

    except sqlite3.Error:
        connection.rollback()
        flash(
            "Could not update the maintenance request.",
            "error"
        )

    finally:
        connection.close()

    return redirect(url_for("maintenance_requests"))


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
