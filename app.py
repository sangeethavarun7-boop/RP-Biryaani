import sqlite3
import os 
import smtplib

from email.message import EmailMessage
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from datetime import datetime, date

from urllib.parse import quote
from functools import wraps

app = Flask(
    __name__,
    template_folder=os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates"
    )
)

app.secret_key = os.environ.get("SECRET_KEY")

def send_order_email(order_details):
    sender_email = os.environ.get("MAIL_USERNAME")
    sender_password = os.environ.get("MAIL_PASSWORD")

    recipients = [
        os.environ.get("ORDER_EMAIL_1"),
        os.environ.get("ORDER_EMAIL_2")
    ]

    # Remove empty email addresses
    recipients = [email for email in recipients if email]

    if not sender_email or not sender_password or not recipients:
        print("Email settings are missing.")
        return False

    message = EmailMessage()

    message["Subject"] = "🔔 New RP Biryaani Order"
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)

    message.set_content(f"""
NEW RP BIRYAANI ORDER

Customer Name: {order_details.get("name", "")}
Phone: {order_details.get("phone", "")}

Food: {order_details.get("food", "")}
Quantity: {order_details.get("quantity", "")}

Address:
{order_details.get("address", "")}

Message:
{order_details.get("message", "")}

Payment Method:
{order_details.get("payment_method", "")}

Total Amount:
₹{order_details.get("total", "")}

Please check the RP Biryaani Admin Panel.

This is an automatic notification from the RP Biryaani website.
""")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)

        print("Order notification email sent successfully.")
        return True

    except Exception as e:
        print("Email sending failed:", e)
        return False

# ADMIN LOGIN DETAILS
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return f(*args, **kwargs)

    return decorated_function

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

            session["admin_logged_in"] = True

            return redirect(url_for("admin"))

        return render_template(
            "admin_login.html",
            error="Invalid username or password"
        )

    return render_template("admin_login.html")

# =========================
# DATABASE
# =========================

DATABASE = "rp_biryaani.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            food TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            address TEXT NOT NULL,
            message TEXT,
            subtotal REAL NOT NULL,
            discount REAL NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Order Confirmed',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()

def init_bulk_orders_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bulk_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            event_type TEXT NOT NULL,
            food_type TEXT NOT NULL,
            guests INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            food_items TEXT NOT NULL,
            budget REAL,
            event_address TEXT NOT NULL,
            service_type TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_bulk_orders_table()

# =========================
# FOOD PRICES
# =========================

FOOD_PRICES = {
    "Chicken Biryani": 140,
    "Fish Fry": 150,
    "Chicken Kabab": 160,
    "Kaima Unde Saaru": 200,
    "Egg Rice": 60
}


@app.route("/bulk-order", methods=["GET", "POST"])
def bulk_order():
    if request.method == "POST":
        try:
            customer_name = request.form.get("customer_name", "").strip()
            phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip()
            event_type = request.form.get("event_type", "").strip()
            food_type = request.form.get("food_type", "").strip()
            food_items = request.form.get("food_items", "").strip()
            event_address = request.form.get("event_address", "").strip()
            event_date = request.form.get("event_date", "").strip()
            event_time = request.form.get("event_time", "").strip()
            service_type = request.form.get("service_type", "").strip()
            notes = request.form.get("notes", "").strip()

            if not all([
                customer_name, phone, event_type, food_type,
                food_items, event_address, event_date, event_time
            ]):
                flash("Please fill in all required fields.", "danger")
                return redirect(url_for("bulk_order"))

            if not phone.isdigit() or len(phone) != 10:
                flash("Enter a valid 10-digit mobile number.", "danger")
                return redirect(url_for("bulk_order"))

            guests = int(request.form.get("guests", "0"))
            if not 1 <= guests <= 100000:
                flash("Enter a valid guest count.", "danger")
                return redirect(url_for("bulk_order"))

            parsed_date = date.fromisoformat(event_date)
            if parsed_date < date.today():
                flash("Event date cannot be in the past.", "danger")
                return redirect(url_for("bulk_order"))

            budget_text = request.form.get("budget", "").strip()
            budget = float(budget_text) if budget_text else None

            if budget is not None and (
                budget < 0 or budget > 1000000000
            ):
                flash("Enter a valid budget.", "danger")
                return redirect(url_for("bulk_order"))

            conn = get_db()
            try:
                conn.execute("""
                    INSERT INTO bulk_orders (
                        customer_name, phone, email, event_type,
                        food_type, guests, event_date, event_time,
                        food_items, budget, event_address,
                        service_type, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    customer_name, phone, email, event_type,
                    food_type, guests, event_date, event_time,
                    food_items, budget, event_address,
                    service_type, notes,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
            finally:
                conn.close()

            flash("Your bulk order request was submitted successfully!", "success")
            return redirect(url_for("bulk_order"))

        except (ValueError, OverflowError):
            flash("Please check your guest count, date and budget.", "danger")
            return redirect(url_for("bulk_order"))

        except sqlite3.Error:
            app.logger.exception("Unable to save bulk order")
            flash("Unable to save your request. Please try again.", "danger")
            return redirect(url_for("bulk_order"))

    return render_template(
        "bulk_order.html",
        today=date.today().isoformat()
    )


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# ABOUT
# =========================

@app.route("/about")
def about():
    return render_template("about.html")


# =========================
# MENU
# =========================

@app.route("/menu")
def menu():
    return render_template("menu.html")


# =========================
# GALLERY
# =========================

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


# =========================
# CONTACT
# =========================

@app.route("/contact")
def contact():
    return render_template("contact.html")


# =========================
# REVIEWS
# =========================

@app.route("/reviews")
def reviews():
    return render_template("reviews.html")


# =========================
# ORDER
# =========================

@app.route("/order", methods=["GET", "POST"])
def order():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        food = request.form.get("food", "").strip()

        try:
            quantity = int(request.form.get("quantity", 1))
        except ValueError:
            return "Invalid quantity", 400

        address = request.form.get("address", "").strip()
        message = request.form.get("message", "").strip()

        payment_method = request.form.get(
            "payment_method",
            "Cash on Delivery"
        )

        offer = request.form.get("offer", "none")

        # -------------------------
        # BASIC VALIDATION
        # -------------------------

        if food not in FOOD_PRICES:
            return "Invalid food item", 400

        if quantity < 1:
            return "Invalid quantity", 400

        if not name or not phone or not address:
            return "Please fill all required fields.", 400

        # -------------------------
        # PRICE CALCULATION
        # -------------------------

        price = FOOD_PRICES[food]

        subtotal = price * quantity

        discount = 0

        # -------------------------
        # FIRST ORDER CHECK
        # -------------------------

        conn = get_db()

        previous_order = conn.execute(
            "SELECT id FROM orders WHERE phone = ? LIMIT 1",
            (phone,)
        ).fetchone()

        is_first_order = previous_order is None

        # -------------------------
        # FIRST ORDER 10% OFFER
        # -------------------------

        if offer == "first10" and is_first_order:
            discount = round(subtotal * 0.10, 2)

        # -------------------------
        # BUY 1 GET 1
        # -------------------------

        elif offer == "bogo":

            paid_quantity = (quantity + 1) // 2

            discount = round(
                subtotal - (price * paid_quantity),
                2
            )

        # -------------------------
        # FINAL TOTAL
        # -------------------------

        total = round(subtotal - discount, 2)

        # -------------------------
        # ORDER ID
        # -------------------------

        next_id = conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
        ).fetchone()[0]

        order_id = f"RP{next_id:05d}"

        created_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # -------------------------
        # SAVE ORDER
        # -------------------------

        conn.execute("""
            INSERT INTO orders (
                order_id,
                name,
                phone,
                food,
                quantity,
                address,
                message,
                subtotal,
                discount,
                total,
                payment_method,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            name,
            phone,
            food,
            quantity,
            address,
            message,
            subtotal,
            discount,
            total,
            payment_method,
            "Order Confirmed",
            created_at
        ))

        conn.commit()
        conn.close()

        # -------------------------
        # SEND ORDER EMAIL
        # -------------------------

        order_details = {
            "name": name,
            "phone": phone,
            "food": food,
            "quantity": quantity,
            "address": address,
            "message": message,
            "payment_method": payment_method,
            "total": total
        }

        send_order_email(order_details)

        # -------------------------
        # ONLINE PAYMENT
        # -------------------------

        if payment_method == "Online Payment":

            upi_id = os.environ.get("UPI_ID")

            if not upi_id:
                return "Online payment is currently unavailable.", 500

            upi_link = (
                "upi://pay?"
                f"pa={quote(upi_id)}"
                f"&pn={quote('RP Biryaani')}"
                f"&am={total:.2f}"
                "&cu=INR"
                f"&tn={quote(order_id)}"
            )

            return render_template(
                "success.html",
                order_id=order_id,
                name=name,
                food=food,
                quantity=quantity,
                subtotal=subtotal,
                discount=discount,
                total=total,
                payment_method=payment_method,
                upi_link=upi_link
            )

        # -------------------------
        # CASH ON DELIVERY
        # -------------------------

        return render_template(
            "success.html",
            order_id=order_id,
            name=name,
            food=food,
            quantity=quantity,
            subtotal=subtotal,
            discount=discount,
            total=total,
            payment_method=payment_method
        )

    # -------------------------
    # SHOW ORDER PAGE
    # -------------------------

    return render_template(
        "order.html",
        prices=FOOD_PRICES
    )

# =========================
# TRACK ORDER
# =========================

@app.route("/track", methods=["GET", "POST"])
def track():

    order = None

    if request.method == "POST":

        order_id = request.form.get(
            "order_id", ""
        ).strip().upper()

        phone = request.form.get(
            "phone", ""
        ).strip()

        conn = get_db()

        order = conn.execute("""
            SELECT *
            FROM orders
            WHERE order_id = ?
            AND phone = ?
        """, (order_id, phone)).fetchone()

        conn.close()

    return render_template(
        "track.html",
        order=order
    )

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("admin_login"))

# =========================
# ADMIN
# =========================

@app.route("/admin")
@admin_required
def admin():

    conn = get_db()

    orders = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        orders=orders
    )


# =========================
# ADMIN UPDATE ORDER STATUS
# =========================

@app.route("/admin/update/<int:order_id>", methods=["POST"])
@admin_required
def update_order(order_id):

    status = request.form.get("status")

    allowed_statuses = [
        "Order Confirmed",
        "Preparing",
        "Out for Delivery",
        "Delivered",
        "Cancelled"
    ]

    if status not in allowed_statuses:
        return "Invalid status", 400

    conn = get_db()

    conn.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (status, order_id))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )