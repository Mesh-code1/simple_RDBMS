from __future__ import annotations

from datetime import date

from flask import Flask, redirect, render_template_string, request, session, url_for

from minidb import MiniDB
from minidb.errors import MiniDBError


app = Flask(__name__)
app.secret_key = "dev"

db = MiniDB("./minidb_data", enable_auth=True)


BASE_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{{ title }}</title>
    <style>
      :root {
        --bg: #0b1220;
        --card: rgba(255, 255, 255, 0.06);
        --card-2: rgba(255, 255, 255, 0.08);
        --text: rgba(255, 255, 255, 0.92);
        --muted: rgba(255, 255, 255, 0.66);
        --border: rgba(255, 255, 255, 0.12);
        --primary: #7c3aed;
        --primary-2: #a78bfa;
        --danger: #ef4444;
        --success: #22c55e;
        --warning: #f59e0b;
        --shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
        --radius: 16px;
        --radius-sm: 12px;
        --font: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji",
          "Segoe UI Emoji";
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: var(--font);
        color: var(--text);
        background:
          radial-gradient(1200px 600px at 20% -10%, rgba(124, 58, 237, 0.35), transparent 60%),
          radial-gradient(900px 500px at 90% 10%, rgba(59, 130, 246, 0.22), transparent 55%),
          radial-gradient(900px 500px at 70% 110%, rgba(34, 197, 94, 0.12), transparent 55%),
          var(--bg);
        min-height: 100vh;
      }
      a { color: var(--primary-2); text-decoration: none; }
      a:hover { text-decoration: underline; }
      .container { max-width: 1100px; margin: 0 auto; padding: 28px 18px 60px; }
      .nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 14px 16px;
        border: 1px solid var(--border);
        background: rgba(11, 18, 32, 0.55);
        backdrop-filter: blur(10px);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
      }
      .brand { display: flex; flex-direction: column; line-height: 1.1; }
      .brand strong { font-size: 16px; letter-spacing: 0.2px; }
      .brand span { font-size: 12px; color: var(--muted); }
      .nav-actions { display: flex; gap: 10px; align-items: center; }
      .pill {
        padding: 7px 10px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.05);
        border-radius: 999px;
        color: var(--muted);
        font-size: 12px;
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
        margin-top: 18px;
      }
      @media (min-width: 900px) {
        .grid.grid-2 { grid-template-columns: 1fr 1.4fr; }
      }
      .card {
        border: 1px solid var(--border);
        background: var(--card);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 18px;
      }
      .card h1, .card h2, .card h3 { margin: 0 0 12px 0; }
      .subtle { color: var(--muted); font-size: 13px; margin-top: -4px; }
      .alert {
        border: 1px solid rgba(239, 68, 68, 0.35);
        background: rgba(239, 68, 68, 0.10);
        color: rgba(255, 255, 255, 0.92);
        padding: 10px 12px;
        border-radius: var(--radius-sm);
        margin: 10px 0 0;
      }
      form { margin: 0; }
      .form {
        display: grid;
        gap: 12px;
      }
      .row { display: grid; gap: 10px; grid-template-columns: 1fr; }
      @media (min-width: 700px) {
        .row.row-3 { grid-template-columns: 1.4fr 1fr 1fr; }
        .row.row-2 { grid-template-columns: 1fr 1fr; }
      }
      label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
      input {
        width: 100%;
        padding: 11px 12px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.06);
        color: var(--text);
        outline: none;
      }
      input::placeholder { color: rgba(255, 255, 255, 0.45); }
      input:focus {
        border-color: rgba(167, 139, 250, 0.65);
        box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.18);
      }
      .btn {
        appearance: none;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.06);
        color: var(--text);
        padding: 10px 12px;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 600;
      }
      .btn:hover { background: rgba(255, 255, 255, 0.09); }
      .btn-primary {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.95), rgba(59, 130, 246, 0.85));
        border-color: rgba(167, 139, 250, 0.45);
      }
      .btn-primary:hover { filter: brightness(1.06); }
      .btn-danger {
        background: rgba(239, 68, 68, 0.12);
        border-color: rgba(239, 68, 68, 0.35);
      }
      .btn-success {
        background: rgba(34, 197, 94, 0.12);
        border-color: rgba(34, 197, 94, 0.35);
      }
      .btn-sm { padding: 8px 10px; border-radius: 10px; font-size: 13px; }
      .table {
        width: 100%;
        border-collapse: collapse;
        overflow: hidden;
        border-radius: var(--radius);
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.04);
      }
      .table th, .table td { padding: 12px 12px; border-bottom: 1px solid var(--border); text-align: left; }
      .table th { color: var(--muted); font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
      .table tr:last-child td { border-bottom: none; }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 12px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.06);
      }
      .badge-success { border-color: rgba(34, 197, 94, 0.35); background: rgba(34, 197, 94, 0.12); }
      .badge-warning { border-color: rgba(245, 158, 11, 0.35); background: rgba(245, 158, 11, 0.14); }
      .badge-danger { border-color: rgba(239, 68, 68, 0.35); background: rgba(239, 68, 68, 0.12); }
      .actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
      .muted { color: var(--muted); }
      .footer-note { margin-top: 14px; color: var(--muted); font-size: 12px; }
    </style>
  </head>
  <body>
    <div class=\"container\">
      <div class=\"nav\">
        <div class=\"brand\">
          <strong>Bills Admin</strong>
          <span>MiniDB demo</span>
        </div>
        <div class=\"nav-actions\">
          {% if username %}<span class=\"pill\">Signed in as <strong>{{ username }}</strong></span>{% endif %}
          {% if show_logout %}
            <form method=\"post\" action=\"{{ url_for('logout') }}\">
              <button class=\"btn btn-sm\" type=\"submit\">Logout</button>
            </form>
          {% endif %}
        </div>
      </div>

      <div class=\"grid\">{{ body|safe }}</div>
    </div>
  </body>
</html>
"""


def _render_page(*, title: str, body: str, username: str = "", show_logout: bool = False):
    return render_template_string(
        BASE_TEMPLATE,
        title=title,
        body=body,
        username=username,
        show_logout=show_logout,
    )


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


def _sum_payments_for_bill(token: str, bill_id: int) -> float:
    if not token:
        return 0.0
    try:
        payments = db.execute(f"SELECT * FROM payments WHERE bill_id={bill_id};", token)
    except MiniDBError:
        return 0.0
    total = 0.0
    for p in payments:
        try:
            total += float(p.get("amount") or 0)
        except Exception:
            total += 0.0
    return total


def _recompute_bill_status(token: str, bill_id: int) -> None:
    if not token:
        return
    bills = db.execute(f"SELECT * FROM bills WHERE id={bill_id};", token)
    if not bills:
        return
    bill = bills[0]
    try:
        bill_amount = float(bill.get("amount") or 0)
    except Exception:
        bill_amount = 0.0
    paid_total = _sum_payments_for_bill(token, int(bill.get("id") or bill_id))
    new_status = "paid" if paid_total >= bill_amount and bill_amount > 0 else "unpaid"
    db.execute(f"UPDATE bills SET status='{new_status}' WHERE id={bill_id};", token)


@app.get("/")
def home():
    if _require_auth() is None:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.get("/login")
def login():
    body = """
      <div class=\"card\" style=\"max-width: 520px; margin: 18px auto 0;\">
        <h2>Welcome back</h2>
        <div class=\"subtle\">Sign in to manage your bills.</div>
        <div style=\"height: 14px\"></div>
        <form method=\"post\" class=\"form\">
          <div>
            <label>Username</label>
            <input name=\"username\" placeholder=\"e.g. admin\" required />
          </div>
          <div>
            <label>Password</label>
            <input name=\"password\" placeholder=\"••••••••\" type=\"password\" required />
          </div>
          <button class=\"btn btn-primary\" type=\"submit\">Login</button>
        </form>
        <div class=\"footer-note\">No account? <a href=\"{{ url_for('register') }}\">Create one</a>.</div>
      </div>
    """
    return _render_page(title="Login", body=render_template_string(body))


@app.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    try:
        token = db.login(username, password)
        session["token"] = token
        return redirect(url_for("dashboard"))
    except Exception as e:
        body = """
          <div class=\"card\" style=\"max-width: 520px; margin: 18px auto 0;\">
            <h2>Login</h2>
            <div class=\"alert\">Login failed: {{ e }}</div>
            <div style=\"height: 14px\"></div>
            <a class=\"btn\" href=\"{{ url_for('login') }}\">Back</a>
          </div>
        """
        return _render_page(title="Login", body=render_template_string(body, e=str(e)))


@app.get("/register")
def register():
    body = """
      <div class=\"card\" style=\"max-width: 560px; margin: 18px auto 0;\">
        <h2>Create your account</h2>
        <div class=\"subtle\">This demo stores users in <span class=\"muted\">minidb_data/users.rows.json</span>.</div>
        <div style=\"height: 14px\"></div>
        <form method=\"post\" class=\"form\">
          <div class=\"row row-2\">
            <div>
              <label>Username</label>
              <input name=\"username\" placeholder=\"choose a username\" required />
            </div>
            <div>
              <label>Email (optional)</label>
              <input name=\"email\" placeholder=\"you@example.com\" />
            </div>
          </div>
          <div>
            <label>Password</label>
            <input name=\"password\" placeholder=\"create a password\" type=\"password\" required />
          </div>
          <button class=\"btn btn-primary\" type=\"submit\">Create account</button>
        </form>
        <div class=\"footer-note\"><a href=\"{{ url_for('login') }}\">Back to login</a></div>
      </div>
    """
    return _render_page(title="Register", body=render_template_string(body))


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
        body = """
          <div class=\"card\" style=\"max-width: 560px; margin: 18px auto 0;\">
            <h2>Register</h2>
            <div class=\"alert\">Register failed: {{ e }}</div>
            <div style=\"height: 14px\"></div>
            <a class=\"btn\" href=\"{{ url_for('register') }}\">Back</a>
          </div>
        """
        return _render_page(title="Register", body=render_template_string(body, e=str(e)))


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

    view = request.args.get("view", "bills").strip().lower()
    if view not in {"add", "bills", "payments"}:
        view = "bills"

    try:
        bills = db.execute("SELECT * FROM bills;", session.get("token"))
    except MiniDBError as e:
        bills = []
        err = str(e)
    else:
        err = ""

    try:
        payments = db.execute("SELECT * FROM payments;", session.get("token"))
    except MiniDBError:
        payments = []

    bill_desc_by_id = {int(b.get("id")): str(b.get("description") or "") for b in bills if b.get("id") is not None}

    last_err = session.pop("last_error", "")
    if err == "" and last_err:
        err = last_err

    token = session.get("token")
    username = ""
    try:
        _uid, uname = db.validate(token)
        username = uname
    except Exception:
        username = ""

    today = date.today().isoformat()

    body = """
      <style>
        .shell { display: grid; grid-template-columns: 1fr; gap: 16px; }
        @media (min-width: 980px) { .shell { grid-template-columns: 280px 1fr; } }
        .sidebar { position: sticky; top: 18px; height: fit-content; }
        .navlist { display: grid; gap: 8px; margin-top: 12px; }
        .navitem {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: rgba(255, 255, 255, 0.04);
          color: var(--text);
          text-decoration: none;
        }
        .navitem:hover { background: rgba(255, 255, 255, 0.07); }
        .navitem.active { border-color: rgba(167, 139, 250, 0.55); background: rgba(124, 58, 237, 0.12); }
        .content-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
        .small { font-size: 12px; color: var(--muted); }
      </style>

      <div class=\"shell\">
        <div class=\"card sidebar\">
          <h2 style=\"margin-bottom: 6px\">Dashboard</h2>
          <div class=\"subtle\">Manage bills and payments.</div>
          <div class=\"navlist\">
            <a class=\"navitem {{ 'active' if view=='add' else '' }}\" href=\"{{ url_for('dashboard', view='add') }}\">Add bill<span class=\"small\">+</span></a>
            <a class=\"navitem {{ 'active' if view=='bills' else '' }}\" href=\"{{ url_for('dashboard', view='bills') }}\">Manage bills<span class=\"small\">{{ bills|length }}</span></a>
            <a class=\"navitem {{ 'active' if view=='payments' else '' }}\" href=\"{{ url_for('dashboard', view='payments') }}\">Payments<span class=\"small\">{{ payments|length }}</span></a>
          </div>
          <div class=\"footer-note\">Today: <strong>{{ today }}</strong></div>
        </div>

        <div class=\"grid\">
          {% if err %}<div class=\"alert\">{{ err }}</div>{% endif %}

          {% if view == 'add' %}
            <div class=\"card\">
              <div class=\"content-header\">
                <div>
                  <h2 style=\"margin-bottom: 6px\">Add bill</h2>
                  <div class=\"subtle\">Create a bill record (ownership enforced by <span class=\"muted\">user_id</span>).</div>
                </div>
              </div>
              <div style=\"height: 12px\"></div>
              <form method=\"post\" action=\"{{ url_for('add_bill') }}\" class=\"form\">
                <div>
                  <label>Description</label>
                  <input name=\"description\" placeholder=\"e.g. Rent\" required />
                </div>
                <div class=\"row row-2\">
                  <div>
                    <label>Amount</label>
                    <input name=\"amount\" placeholder=\"e.g. 1200.00\" required />
                  </div>
                  <div>
                    <label>Due date</label>
                    <input name=\"due_date\" type=\"date\" required />
                  </div>
                </div>
                <button class=\"btn btn-primary\" type=\"submit\">Add bill</button>
              </form>
              <div class=\"footer-note\">Tip: Payments are tracked separately; the bill becomes paid only when total payments cover the bill amount.</div>
            </div>
          {% endif %}

          {% if view == 'bills' %}
            <div class=\"card\">
              <div class=\"content-header\">
                <div>
                  <h2 style=\"margin-bottom: 6px\">Manage bills</h2>
                  <div class=\"subtle\">Edit, set status, pay, or delete.</div>
                </div>
              </div>
              <div style=\"height: 12px\"></div>
              <table class=\"table\">
                <tr>
                  <th>ID</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Paid total</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
                {% for b in bills %}
                  {% set overdue = b['due_date'] < today and b['status'] != 'paid' %}
                  {% set paid_total = 0.0 %}
                  {% for p in payments %}
                    {% if (p['bill_id']|int) == (b['id']|int) %}
                      {% set paid_total = paid_total + ((p['amount'] or 0)|float) %}
                    {% endif %}
                  {% endfor %}
                  {% set form_id = 'billform' ~ b['id'] %}
                  <tr style=\"background: {{ 'rgba(239, 68, 68, 0.08)' if overdue else 'transparent' }}\">
                    <td>{{ b['id'] }}</td>
                    <td>
                      <input form=\"{{ form_id }}\" name=\"description\" value=\"{{ b['description'] }}\" required style=\"max-width: 220px\" />
                    </td>
                    <td>
                      <input form=\"{{ form_id }}\" name=\"amount\" value=\"{{ b['amount'] }}\" required style=\"max-width: 120px\" />
                    </td>
                    <td>{{ paid_total }}</td>
                    <td>
                      <input form=\"{{ form_id }}\" name=\"due_date\" type=\"date\" value=\"{{ b['due_date'] }}\" required style=\"max-width: 160px\" />
                    </td>
                    <td>
                      <select form=\"{{ form_id }}\" name=\"status\" class=\"btn btn-sm\" style=\"padding: 10px 12px\">
                        <option value=\"paid\" {{ 'selected' if b['status']=='paid' else '' }}>paid</option>
                        <option value=\"unpaid\" {{ 'selected' if b['status']=='unpaid' else '' }}>unpaid</option>
                        <option value=\"pending\" {{ 'selected' if b['status']=='pending' else '' }}>pending</option>
                      </select>
                    </td>
                    <td>
                      <div class=\"actions\">
                        <form id=\"{{ form_id }}\" method=\"post\" action=\"{{ url_for('update_bill', bill_id=b['id']) }}\"></form>
                        <button form=\"{{ form_id }}\" class=\"btn btn-sm\" type=\"submit\">Save</button>
                        <form method=\"post\" action=\"{{ url_for('pay_bill', bill_id=b['id']) }}\">
                          <input name=\"amount\" placeholder=\"payment amount\" required style=\"max-width: 160px\" />
                          <button class=\"btn btn-sm btn-success\" type=\"submit\">Pay</button>
                        </form>
                        <form method=\"post\" action=\"{{ url_for('delete_bill', bill_id=b['id']) }}\">
                          <button class=\"btn btn-sm btn-danger\" type=\"submit\">Delete</button>
                        </form>
                      </div>
                    </td>
                  </tr>
                {% endfor %}
              </table>
              {% if bills|length == 0 %}
                <div class=\"footer-note\">No bills yet. Use “Add bill” from the sidebar.</div>
              {% endif %}
            </div>
          {% endif %}

          {% if view == 'payments' %}
            <div class=\"card\">
              <div class=\"content-header\">
                <div>
                  <h2 style=\"margin-bottom: 6px\">Payments</h2>
                  <div class=\"subtle\">Record payments and review history.</div>
                </div>
              </div>
              <div style=\"height: 12px\"></div>
              <form method=\"post\" action=\"{{ url_for('make_payment') }}\" class=\"form\">
                <div class=\"row row-3\">
                  <div>
                    <label>Bill</label>
                    <select name=\"bill_id\" class=\"btn\" style=\"padding: 11px 12px\" required>
                      {% for b in bills %}
                        <option value=\"{{ b['id'] }}\">#{{ b['id'] }} - {{ b['description'] }} (amount {{ b['amount'] }})</option>
                      {% endfor %}
                    </select>
                  </div>
                  <div>
                    <label>Amount</label>
                    <input name=\"amount\" placeholder=\"e.g. 500.00\" required />
                  </div>
                  <div>
                    <label>&nbsp;</label>
                    <button class=\"btn btn-primary\" type=\"submit\">Make payment</button>
                  </div>
                </div>
              </form>

              <div style=\"height: 12px\"></div>
              <table class=\"table\">
                <tr>
                  <th>ID</th>
                  <th>Bill ID</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Date</th>
                </tr>
                {% for p in payments %}
                  <tr>
                    <td>{{ p['id'] }}</td>
                    <td>{{ p['bill_id'] }}</td>
                    <td>{{ bill_desc_by_id.get(p['bill_id']|int, '') }}</td>
                    <td>{{ p['amount'] }}</td>
                    <td>{{ p['payment_date'] }}</td>
                  </tr>
                {% endfor %}
              </table>
              {% if payments|length == 0 %}
                <div class=\"footer-note\">No payments yet.</div>
              {% endif %}
            </div>
          {% endif %}
        </div>
      </div>
    """
    return _render_page(
        title="Dashboard",
        body=render_template_string(
            body,
            bills=bills,
            payments=payments,
            today=today,
            err=err,
            view=view,
            bill_desc_by_id=bill_desc_by_id,
        ),
        username=username,
        show_logout=True,
    )


@app.post("/add_bill")
def add_bill():
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))

    description = request.form.get("description", "").strip()
    amount = request.form.get("amount", "").strip()
    due_date = request.form.get("due_date", "").strip()
    if due_date == "":
        due_month = request.form.get("due_month", "").strip()
        if due_month != "":
            due_date = f"{due_month}-01"

    description_sql = description.replace("'", "''")
    due_date_sql = due_date.replace("'", "''")
    amount_sql = amount.replace(",", "").strip()

    bill_id = db._next_int_id("bills")
    try:
        db.execute(
            f"INSERT INTO bills (id, description, amount, due_date, status) VALUES ({bill_id}, '{description_sql}', {amount_sql}, '{due_date_sql}', 'pending');",
            session.get("token"),
        )
    except MiniDBError as e:
        session["last_error"] = str(e)
    except Exception as e:
        session["last_error"] = str(e)
    return redirect(url_for("dashboard"))


@app.post("/pay_bill/<int:bill_id>")
def pay_bill(bill_id: int):
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))

    token = session.get("token")
    try:
        owned = db.execute(f"SELECT * FROM bills WHERE id={bill_id};", token)
    except MiniDBError as e:
        session["last_error"] = str(e)
        return redirect(url_for("dashboard", view="bills"))
    if not owned:
        session["last_error"] = "Bill not found"
        return redirect(url_for("dashboard", view="bills"))

    amt = request.form.get("amount", "").strip()
    payment_id = db._next_int_id("payments")
    today = date.today().isoformat()

    amt_sql = amt.replace(",", "").strip()

    db.execute(
        f"INSERT INTO payments (id, bill_id, amount, payment_date) VALUES ({payment_id}, {bill_id}, {amt_sql}, '{today}');",
        token,
    )
    _recompute_bill_status(token, bill_id)
    return redirect(url_for("dashboard"))


@app.post("/make_payment")
def make_payment():
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))

    token = session.get("token")
    bill_id = request.form.get("bill_id", "").strip()
    amt = request.form.get("amount", "").strip()
    try:
        bid = int(bill_id)
    except Exception:
        session["last_error"] = "Invalid bill id"
        return redirect(url_for("dashboard", view="payments"))
    payment_id = db._next_int_id("payments")
    today = date.today().isoformat()
    amt_sql = amt.replace(",", "").strip()
    try:
        owned = db.execute(f"SELECT * FROM bills WHERE id={bid};", token)
        if not owned:
            session["last_error"] = "Bill not found"
            return redirect(url_for("dashboard", view="payments"))
        db.execute(
            f"INSERT INTO payments (id, bill_id, amount, payment_date) VALUES ({payment_id}, {bid}, {amt_sql}, '{today}');",
            token,
        )
        _recompute_bill_status(token, bid)
    except MiniDBError as e:
        session["last_error"] = str(e)
    except Exception as e:
        session["last_error"] = str(e)
    return redirect(url_for("dashboard", view="payments"))


@app.post("/update_bill/<int:bill_id>")
def update_bill(bill_id: int):
    uid = _require_auth()
    if uid is None:
        return redirect(url_for("login"))

    description = request.form.get("description", "").strip()
    amount = request.form.get("amount", "").strip()
    due_date = request.form.get("due_date", "").strip()
    status = request.form.get("status", "").strip().lower()
    if status not in {"paid", "unpaid", "pending"}:
        status = "pending"

    description_sql = description.replace("'", "''")
    due_date_sql = due_date.replace("'", "''")
    amount_sql = amount.replace(",", "").strip()

    try:
        db.execute(
            f"UPDATE bills SET description='{description_sql}', amount={amount_sql}, due_date='{due_date_sql}', status='{status}' WHERE id={bill_id};",
            session.get("token"),
        )
    except MiniDBError as e:
        session["last_error"] = str(e)
    except Exception as e:
        session["last_error"] = str(e)
    return redirect(url_for("dashboard", view="bills"))


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
