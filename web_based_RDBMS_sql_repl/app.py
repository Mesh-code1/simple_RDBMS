from __future__ import annotations

import os
import sys
import json
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template_string, request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from minidb import MiniDB
from minidb.errors import MiniDBError, ParseError


app = Flask(__name__)

db = MiniDB("./web_based_RDBMS_sql_repl_data", enable_auth=False)


INDEX_HTML = """
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Web SQL REPL</title>
    <style>
      :root {
        --bg: #0b1220;
        --panel: rgba(255, 255, 255, 0.06);
        --panel2: rgba(255, 255, 255, 0.08);
        --text: rgba(255, 255, 255, 0.92);
        --muted: rgba(255, 255, 255, 0.66);
        --border: rgba(255, 255, 255, 0.12);
        --primary: #7c3aed;
        --primary2: #a78bfa;
        --danger: #ef4444;
        --success: #22c55e;
        --shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
        --radius: 16px;
        --font: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: var(--font);
        color: var(--text);
        background:
          radial-gradient(1200px 600px at 20% -10%, rgba(124, 58, 237, 0.35), transparent 60%),
          radial-gradient(900px 500px at 90% 10%, rgba(59, 130, 246, 0.22), transparent 55%),
          var(--bg);
        min-height: 100vh;
      }
      .container { max-width: 1200px; margin: 0 auto; padding: 22px 16px 44px; }
      .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 14px 16px;
        border: 1px solid var(--border);
        background: rgba(11, 18, 32, 0.55);
        backdrop-filter: blur(10px);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
      }
      .brand { display: flex; flex-direction: column; line-height: 1.15; }
      .brand strong { font-size: 16px; letter-spacing: 0.2px; }
      .brand span { font-size: 12px; color: var(--muted); }
      .actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
      .btn {
        appearance: none;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.06);
        color: var(--text);
        padding: 10px 12px;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 700;
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
        margin-top: 16px;
      }
      .panel {
        border: 1px solid var(--border);
        background: var(--panel);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        overflow: hidden;
      }
      .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        padding: 12px 14px;
        border-bottom: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.03);
      }
      .panel-header h2 { margin: 0; font-size: 14px; letter-spacing: 0.2px; }
      .muted { color: var(--muted); font-size: 12px; }
      textarea {
        width: 100%;
        min-height: 260px;
        resize: vertical;
        padding: 14px;
        border: none;
        outline: none;
        background: rgba(0, 0, 0, 0.20);
        color: var(--text);
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 13px;
        line-height: 1.5;
      }
      .split {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
      }
      @media (min-width: 1000px) {
        .split { grid-template-columns: 1.4fr 1fr; }
      }
      .output {
        padding: 12px 14px;
        white-space: pre-wrap;
        word-break: break-word;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 12px;
      }
      .alert {
        border: 1px solid rgba(239, 68, 68, 0.35);
        background: rgba(239, 68, 68, 0.10);
        padding: 10px 12px;
        border-radius: 12px;
      }
      .ok {
        border: 1px solid rgba(34, 197, 94, 0.35);
        background: rgba(34, 197, 94, 0.12);
        padding: 10px 12px;
        border-radius: 12px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.04);
      }
      th, td { padding: 10px 10px; border-bottom: 1px solid var(--border); text-align: left; }
      th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
      tr:last-child td { border-bottom: none; }
      .modal {
        position: fixed;
        inset: 0;
        display: none;
        align-items: center;
        justify-content: center;
        background: rgba(0, 0, 0, 0.55);
        padding: 16px;
      }
      .modal.open { display: flex; }
      .modal-card {
        width: min(640px, 100%);
        border: 1px solid var(--border);
        background: rgba(11, 18, 32, 0.90);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 14px;
      }
      .form { display: grid; gap: 10px; }
      label { font-size: 12px; color: var(--muted); }
      input {
        width: 100%;
        padding: 11px 12px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.06);
        color: var(--text);
        outline: none;
      }
    </style>
  </head>
  <body>
    <div class=\"container\">
      <div class=\"topbar\">
        <div class=\"brand\">
          <strong>Web-based MiniDB SQL REPL</strong>
          <span>Run SQL scripts (CREATE/INSERT/SELECT/JOIN/UPDATE/DELETE) with JSON persistence</span>
        </div>
        <div class=\"actions\">
          <span class=\"pill\" id=\"statusPill\">Idle</span>
          <button class=\"btn\" id=\"btnFindReplace\" type=\"button\">Find & Replace</button>
          <button class=\"btn\" id=\"btnRefresh\" type=\"button\">Refresh Data</button>
          <button class=\"btn btn-primary\" id=\"btnRun\" type=\"button\">Run</button>
        </div>
      </div>

      <div class=\"grid\">
        <div class=\"split\">
          <div class=\"panel\">
            <div class=\"panel-header\">
              <h2>SQL Script</h2>
              <div class=\"muted\">Supports multiple statements separated by <code>;</code></div>
            </div>
            <textarea id=\"sql\">-- MiniDB SQL Workshop (run step-by-step)
-- Supported: CREATE TABLE, INSERT, SELECT, SELECT JOIN, UPDATE, DELETE
-- Types: INT, STRING, FLOAT
-- Constraints: PRIMARY, UNIQUE

-- 1) CREATE TABLES (run once)
CREATE TABLE customers (id INT PRIMARY UNIQUE, name STRING, email STRING UNIQUE);
CREATE TABLE products (id INT PRIMARY UNIQUE, name STRING UNIQUE, price FLOAT);
CREATE TABLE orders (id INT PRIMARY UNIQUE, customer_id INT, product_id INT, qty INT, total FLOAT);

-- 2) SEED DATA (INSERT)
INSERT INTO customers (id, name, email) VALUES (1, 'Amina', 'amina@example.com');
INSERT INTO customers (id, name, email) VALUES (2, 'Omar', 'omar@example.com');

INSERT INTO products (id, name, price) VALUES (10, 'Keyboard', 45.50);
INSERT INTO products (id, name, price) VALUES (11, 'Mouse', 18.00);
INSERT INTO products (id, name, price) VALUES (12, 'Monitor', 150.00);

-- Orders (total is precomputed here; MiniDB doesn't support expressions)
INSERT INTO orders (id, customer_id, product_id, qty, total) VALUES (100, 1, 10, 2, 91.00);
INSERT INTO orders (id, customer_id, product_id, qty, total) VALUES (101, 1, 11, 1, 18.00);
INSERT INTO orders (id, customer_id, product_id, qty, total) VALUES (102, 2, 12, 1, 150.00);

-- 3) BASIC SELECTS
SELECT * FROM customers;
SELECT * FROM products;
SELECT * FROM orders;

-- 4) WHERE filters (=, >, <)
SELECT * FROM products WHERE price > 20;
SELECT * FROM orders WHERE qty = 1;
SELECT * FROM orders WHERE total < 100;

-- 5) UNIQUE constraint demo (this should ERROR: duplicate email)
-- Run this statement alone to see the constraint enforcement.
INSERT INTO customers (id, name, email) VALUES (3, 'DuplicateEmail', 'omar@example.com');

-- 6) JOIN demo (only one JOIN supported per SELECT)
-- Join orders with customers
SELECT * FROM orders JOIN customers ON customer_id = id;
-- Join orders with products
SELECT * FROM orders JOIN products ON product_id = id;

-- 7) UPDATE (CRUD)
UPDATE customers SET name='Amina M.' WHERE id=1;
UPDATE products SET price=49.99 WHERE id=10;
UPDATE orders SET qty=3, total=136.50 WHERE id=100;

-- 8) DELETE (CRUD)
DELETE FROM orders WHERE id=101;
SELECT * FROM orders;

-- 9) BASIC "INDEX" behavior demo (MiniDB uses UNIQUE columns as indexes)
-- These queries use equality on UNIQUE columns.
SELECT * FROM customers WHERE email = 'amina@example.com';
SELECT * FROM products WHERE name = 'Keyboard';

-- 10) CLEANUP (remove the seeded data)
-- Note: DROP TABLE is not supported; we delete rows instead.
DELETE FROM orders;
DELETE FROM products;
DELETE FROM customers;

-- 11) Verify empty
SELECT * FROM customers;
SELECT * FROM products;
SELECT * FROM orders;
</textarea>
          </div>

          <div class=\"panel\">
            <div class=\"panel-header\">
              <h2>Live Data</h2>
              <div class=\"muted\">Tables + sample rows</div>
            </div>
            <div class=\"output\" id=\"live\">Loading…</div>
          </div>
        </div>

        <div class=\"panel\">
          <div class=\"panel-header\">
            <h2>Output</h2>
            <div class=\"muted\">Results / errors</div>
          </div>
          <div class=\"output\" id=\"out\">Run a query to see results.</div>
        </div>
      </div>
    </div>

    <div class=\"modal\" id=\"modal\">
      <div class=\"modal-card\">
        <div class=\"panel-header\" style=\"border-bottom:none; padding: 0 0 10px\">
          <h2>Find & Replace</h2>
          <div class=\"actions\">
            <button class=\"btn\" id=\"btnClose\" type=\"button\">Close</button>
          </div>
        </div>
        <div class=\"form\">
          <div>
            <label>Find</label>
            <input id=\"find\" placeholder=\"text to find\" />
          </div>
          <div>
            <label>Replace with</label>
            <input id=\"replace\" placeholder=\"replacement\" />
          </div>
          <div class=\"actions\">
            <button class=\"btn\" id=\"btnFindNext\" type=\"button\">Find next</button>
            <button class=\"btn btn-primary\" id=\"btnReplaceAll\" type=\"button\">Replace all</button>
            <button class=\"btn btn-danger\" id=\"btnClear\" type=\"button\">Clear</button>
          </div>
          <div class=\"muted\">Replace-all is literal (no regex). Find-next selects the next match.</div>
        </div>
      </div>
    </div>

    <script>
      const elSql = document.getElementById('sql');
      const elOut = document.getElementById('out');
      const elLive = document.getElementById('live');
      const pill = document.getElementById('statusPill');

      function setStatus(text) {
        pill.textContent = text;
      }

      function escapeHtml(s) {
        return String(s)
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('"', '&quot;')
          .replaceAll("'", '&#39;');
      }

      function renderResult(r) {
        if (r.kind === 'error') {
          return `<div class="alert">${escapeHtml(r.message)}</div>`;
        }
        if (r.kind === 'message') {
          return `<div class="ok">${escapeHtml(r.message)}</div>`;
        }
        if (r.kind === 'rows') {
          const rows = r.rows || [];
          if (rows.length === 0) {
            return `<div class="ok">0 rows</div>`;
          }
          const cols = Object.keys(rows[0]);
          const head = cols.map(c => `<th>${escapeHtml(c)}</th>`).join('');
          const body = rows.map(row => `<tr>${cols.map(c => `<td>${escapeHtml(row[c])}</td>`).join('')}</tr>`).join('');
          return `<table><tr>${head}</tr>${body}</table>`;
        }
        return `<div class="ok">OK</div>`;
      }

      async function refreshState() {
        const resp = await fetch('/api/state');
        const data = await resp.json();
        const tables = data.tables || [];
        if (tables.length === 0) {
          elLive.textContent = 'No tables yet.';
          return;
        }
        let html = '';
        for (const t of tables) {
          html += `<div style="margin-bottom:12px"><div class="pill" style="display:inline-block">${escapeHtml(t.name)} (${t.row_count} rows)</div></div>`;
          if (!t.sample || t.sample.length === 0) {
            html += `<div class="muted" style="margin-bottom:16px">No rows</div>`;
            continue;
          }
          const cols = Object.keys(t.sample[0] || {});
          const head = cols.map(c => `<th>${escapeHtml(c)}</th>`).join('');
          const body = t.sample.map(row => `<tr>${cols.map(c => `<td>${escapeHtml(row[c])}</td>`).join('')}</tr>`).join('');
          html += `<table style="margin-bottom:16px"><tr>${head}</tr>${body}</table>`;
        }
        elLive.innerHTML = html;
      }

      async function runSql() {
        setStatus('Running…');
        elOut.textContent = 'Running…';
        const resp = await fetch('/api/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql: elSql.value })
        });
        const data = await resp.json();
        const results = data.results || [];
        const combined = results.map((r, idx) => `<div style="margin-bottom:12px"><div class="muted" style="margin-bottom:6px">Statement ${idx+1}</div>${renderResult(r)}</div>`).join('');
        elOut.innerHTML = combined || '<div class="muted">No output</div>';
        await refreshState();
        setStatus('Done');
      }

      // Find / Replace
      const modal = document.getElementById('modal');
      const btnFR = document.getElementById('btnFindReplace');
      const btnClose = document.getElementById('btnClose');
      const btnFindNext = document.getElementById('btnFindNext');
      const btnReplaceAll = document.getElementById('btnReplaceAll');
      const btnClear = document.getElementById('btnClear');
      const elFind = document.getElementById('find');
      const elReplace = document.getElementById('replace');

      function openModal() { modal.classList.add('open'); elFind.focus(); }
      function closeModal() { modal.classList.remove('open'); }

      function findNext() {
        const needle = elFind.value;
        if (!needle) return;
        const hay = elSql.value;
        const start = elSql.selectionEnd || 0;
        const idx = hay.indexOf(needle, start);
        const idx2 = idx === -1 ? hay.indexOf(needle, 0) : idx;
        if (idx2 === -1) return;
        elSql.focus();
        elSql.setSelectionRange(idx2, idx2 + needle.length);
      }

      function replaceAll() {
        const needle = elFind.value;
        if (!needle) return;
        const rep = elReplace.value;
        elSql.value = elSql.value.split(needle).join(rep);
      }

      btnFR.addEventListener('click', openModal);
      btnClose.addEventListener('click', closeModal);
      modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
      btnFindNext.addEventListener('click', findNext);
      btnReplaceAll.addEventListener('click', replaceAll);
      btnClear.addEventListener('click', () => { elFind.value=''; elReplace.value=''; });

      document.getElementById('btnRun').addEventListener('click', runSql);
      document.getElementById('btnRefresh').addEventListener('click', refreshState);

      refreshState().then(() => setStatus('Ready'));
    </script>
  </body>
</html>
"""


def _split_statements(sql: str) -> List[str]:
    out: List[str] = []
    buf: List[str] = []
    in_str = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'":
            in_str = not in_str
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_str:
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _strip_line_comments(sql: str) -> str:
    lines = sql.splitlines()
    kept: List[str] = []
    for ln in lines:
        s = ln.lstrip()
        if s.startswith("--"):
            continue
        kept.append(ln)
    return "\n".join(kept)


def _result_payload(res: Any) -> Dict[str, Any]:
    if isinstance(res, list):
        return {"kind": "rows", "rows": res}
    if isinstance(res, int):
        return {"kind": "message", "message": f"OK ({res})"}
    return {"kind": "message", "message": str(res)}


@app.get("/")
def index():
    return render_template_string(INDEX_HTML)


@app.post("/api/execute")
def api_execute():
    data = request.get_json(silent=True) or {}
    sql = str(data.get("sql") or "")
    sql = _strip_line_comments(sql)
    statements = _split_statements(sql)
    results: List[Dict[str, Any]] = []

    for stmt in statements:
        try:
            res = db.execute(stmt)
            results.append(_result_payload(res))
        except (MiniDBError, ParseError) as e:
            results.append({"kind": "error", "message": str(e)})
        except Exception as e:
            results.append({"kind": "error", "message": str(e)})

    return jsonify({"results": results})


@app.get("/api/state")
def api_state():
    tables = []
    for name in db.catalog.list_tables():
        t = db.catalog.get_table(name)
        try:
            all_rows = t.select(["*"])
        except Exception:
            all_rows = []
        sample = all_rows[:25]
        tables.append({"name": name, "row_count": len(all_rows), "sample": sample})
    return jsonify({"tables": tables})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
