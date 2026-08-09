import sqlite3
import os 
from flask import Flask, render_template, request, redirect, url_for, session
from urllib.parse import quote
from datetime import datetime
from functools import wraps

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

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
        quantity = int(request.form.get("quantity", 1))
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
        # Customer gets every second item free.
        # Example:
        # quantity 1 -> pay for 1
        # quantity 2 -> pay for 1
        # quantity 3 -> pay for 2
        # quantity 4 -> pay for 2

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
        # ONLINE PAYMENT
        # -------------------------

        # Replace this with your restaurant's actual UPI ID.
        upi_id = os.environ.get("UPI_ID")

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