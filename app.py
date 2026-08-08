import sqlite3
from flask import request
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/menu")
def menu():
    return render_template("menu.html")

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/reviews")
def reviews():
    return render_template("reviews.html")

@app.route("/order", methods=["GET", "POST"])
def order():

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        food = request.form["food"]
        quantity = request.form["quantity"]
        address = request.form["address"]
        message = request.form["message"]

        conn = sqlite3.connect("orders.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO orders(name,phone,food,quantity,address,message)
        VALUES(?,?,?,?,?,?)
        """, (name, phone, food, quantity, address, message))

        conn.commit()
        conn.close()

        return render_template(
    "success.html",
    name=name,
    phone=phone,
    food=food,
    quantity=quantity,
    address=address
)

    return render_template("order.html")
@app.route("/admin")
def admin():

    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders")

    orders = cursor.fetchall()

    conn.close()

    return render_template("admin.html", orders=orders)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)