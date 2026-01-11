from __future__ import annotations

from datetime import date

from flask import Flask, redirect, render_template_string, request, session, url_for

from minidb import MiniDB
from minidb.errors import MiniDBError


app = Flask(__name__)
app.secret_key = "dev"

db = MiniDB("./minidb_data", enable_auth=True)


def _init_schema() -> None:
    try:
        db.execute(
            "CREATE TABLE bills (id INT PRIMARY, user_id INT, description STRING, amount FLOAT, due_date STRING, status STRING);",
            session.get("token"),
        )
    except Exception:
        pass

    try:
        db.execute(
            "CREATE TABLE payments (id INT PRIMARY, user_id INT, bill_id INT, amount FLOAT, payment_date STRING);",
            session.get("token"),
        )
    except Exception:
        pass


def _require_auth():
    token = session.get("token")
    if not token:
        return None
    try:
        uid, _ = db.validate(token)
        return uid
    except Exception:
        session.pop("token", None)
        return None


@app.get("/")
def home():
    if _require_auth() is None:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.get("/login")
def login():
    return render_template_string(
        """
        <h2>Login</h2>
        <form method="post">
          <div><input name="username" placeholder="username" required></div>
          <div><input name="password" placeholder="password" type="password" required></div>
          <button type="submit">Login</button>
        </form>
        <p>No user yet? <a href="{{ url_for('register') }}">Register</a></p>
        """
    )


@app.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        token = db.login(username, password)
        session["token"] = token
        return redirect(url_for("dashboard"))
    except Exception as e:
        return render_template_string("<p>Login failed: {{e}}</p><a href='{{url_for('login')}}'>Back</a>", e=str(e))


@app.get("/register")
def register():
    return render_template_string(
        """
        <h2>Register</h2>
        <form method="post">
          <div><input name="username" placeholder="username" required></div>
          <div><input name="email" placeholder="email"></div>
          <div><input name="password" placeholder="password" type="password" required></div>
          <button type="submit">Create account</button>
        </form>
        <a href="{{ url_for('login') }}">Back to login</a>
        """
    )


@app.post("/register")
def register_post():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    try:
        db.register_user(username=username, password=password, email=email, is_admin=0)
        session["token"] = db.login(username, password)
        return redirect(url_for("dashboard"))
    except Exception as e:
        return render_template_string("<p>Register failed: {{e}}</p><a href='{{url_for('register')}}'>Back</a>", e=str(e))


@app.post("/logout")
def logout():
    session.pop("token", None)
    return redirect(url_for("login"))


@app.get("/dashboard")
def dashboard():
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))
    _init_schema()
    try:
        bills = db.execute("SELECT * FROM bills;", session.get("token"))
    except MiniDBError as e:
        bills = []
        err = str(e)
    else:
        err = ""

    today = date.today().isoformat()
    return render_template_string(
        """
        <h2>Bills Dashboard</h2>
        <form method="post" action="{{ url_for('logout') }}"><button type="submit">Logout</button></form>
        {% if err %}<p style="color:red">{{err}}</p>{% endif %}

        <h3>Add bill</h3>
        <form method="post" action="{{ url_for('add_bill') }}">
          <input name="description" placeholder="description" required>
          <input name="amount" placeholder="amount" required>
          <input name="due_date" placeholder="YYYY-MM-DD" required>
          <button type="submit">Add</button>
        </form>

        <h3>Your bills</h3>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>ID</th><th>Description</th><th>Amount</th><th>Due</th><th>Status</th><th>Actions</th></tr>
          {% for b in bills %}
            {% set overdue = b['due_date'] < today and b['status'] != 'paid' %}
            <tr style="background: {{ 'mistyrose' if overdue else 'white' }}">
              <td>{{ b['id'] }}</td>
              <td>{{ b['description'] }}</td>
              <td>{{ b['amount'] }}</td>
              <td>{{ b['due_date'] }}</td>
              <td>{{ b['status'] }}</td>
              <td>
                <form method="post" action="{{ url_for('pay_bill', bill_id=b['id']) }}" style="display:inline">
                  <input name="amount" placeholder="payment amount" required>
                  <button type="submit">Pay</button>
                </form>
                <form method="post" action="{{ url_for('delete_bill', bill_id=b['id']) }}" style="display:inline">
                  <button type="submit">Delete</button>
                </form>
              </td>
            </tr>
          {% endfor %}
        </table>
        """,
        bills=bills,
        today=today,
        err=err,
    )


@app.post("/add_bill")
def add_bill():
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))

    description = request.form.get("description", "").strip()
    amount = request.form.get("amount", "").strip()
    due_date = request.form.get("due_date", "").strip()

    bill_id = db._next_int_id("bills")
    db.execute(
        f"INSERT INTO bills (id, description, amount, due_date, status) VALUES ({bill_id}, '{description}', {amount}, '{due_date}', 'pending');",
        session.get("token"),
    )
    return redirect(url_for("dashboard"))


@app.post("/pay_bill/<int:bill_id>")
def pay_bill(bill_id: int):
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))

    amt = request.form.get("amount", "").strip()
    payment_id = db._next_int_id("payments")
    today = date.today().isoformat()

    db.execute(
        f"INSERT INTO payments (id, bill_id, amount, payment_date) VALUES ({payment_id}, {bill_id}, {amt}, '{today}');",
        session.get("token"),
    )
    db.execute(
        f"UPDATE bills SET status='paid' WHERE id={bill_id};",
        session.get("token"),
    )
    return redirect(url_for("dashboard"))


@app.post("/delete_bill/<int:bill_id>")
def delete_bill(bill_id: int):
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))

    db.execute(f"DELETE FROM payments WHERE bill_id={bill_id};", session.get("token"))
    db.execute(f"DELETE FROM bills WHERE id={bill_id};", session.get("token"))
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
