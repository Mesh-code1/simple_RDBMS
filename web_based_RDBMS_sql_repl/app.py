from __future__ import annotations

import os
import sys
import json
import re
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template_string, request, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from minidb import MiniDB
from minidb.errors import MiniDBError, ParseError


app = Flask(__name__)
app.secret_key = "dev"

_DEFAULT_DB_NAME = "default"
_DB_ROOT_DIR = "./web_based_RDBMS_sql_repl_databases"


def _normalize_db_name(name: str) -> str:
    s = (name or "").strip()
    while s.endswith(";"):
        s = s[:-1].rstrip()
    if len(s) >= 2 and ((s[0] == "'" and s[-1] == "'") or (s[0] == '"' and s[-1] == '"')):
        s = s[1:-1].strip()
    if len(s) >= 2 and s[0] == "`" and s[-1] == "`":
        s = s[1:-1].strip()
    return s


def _safe_db_name(name: str) -> str:
    s = _normalize_db_name(name)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s):
        raise ValueError("Invalid database name")
    return s


def _db_dir(name: str) -> str:
    if name == _DEFAULT_DB_NAME:
        return "./web_based_RDBMS_sql_repl_data"
    return os.path.join(_DB_ROOT_DIR, name)


def _current_db_name() -> str:
    v = session.get("current_db")
    if isinstance(v, str) and v.strip():
        return v
    return _DEFAULT_DB_NAME


def _set_current_db(name: str) -> None:
    session["current_db"] = name


def _list_databases() -> List[str]:
    out = [_DEFAULT_DB_NAME]
    if os.path.isdir(_DB_ROOT_DIR):
        for fn in os.listdir(_DB_ROOT_DIR):
            p = os.path.join(_DB_ROOT_DIR, fn)
            if os.path.isdir(p) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", fn):
                out.append(fn)
    return sorted(set(out))


def _require_login_for_db(name: str) -> None:
    if name == _DEFAULT_DB_NAME:
        return
    if not session.get("session_token"):
        raise MiniDBError("Login required for non-default databases")


def _get_db() -> MiniDB:
    name = _current_db_name()
    return MiniDB(_db_dir(name), enable_auth=False)


_auth_db = MiniDB("./web_based_RDBMS_sql_repl_auth", enable_auth=True)


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
      .terminal {
        display: grid;
        gap: 10px;
        padding: 12px 14px;
      }
      .terminal-row {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 10px;
        align-items: center;
      }
      .terminal-input {
        width: 100%;
        padding: 11px 12px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.06);
        color: var(--text);
        outline: none;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 13px;
      }
      .help-body {
        padding: 12px 14px;
        color: var(--text);
        font-size: 13px;
        line-height: 1.5;
      }
      .help-body code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="topbar">
        <div class="brand">
          <strong>Web-based MiniDB SQL REPL</strong>
          <span>Run SQL scripts (CREATE/INSERT/SELECT/JOIN/UPDATE/DELETE) with JSON persistence</span>
        </div>
        <div class="actions">
          <span class="pill" id="dbPill">DB: default</span>
          <span class="pill" id="userPill">User: anonymous</span>
          <span class="pill" id="statusPill">Idle</span>
          <button class="btn" id="btnHelp" type="button">User Guide</button>
          <button class="btn" id="btnFindReplace" type="button">Find & Replace</button>
          <button class="btn" id="btnRefresh" type="button">Refresh Data</button>
          <button class="btn btn-primary" id="btnRun" type="button">Run</button>
        </div>
      </div>

      <div class="grid">
        <div class="split">
          <div class="panel">
            <div class="panel-header">
              <h2>SQL Script</h2>
              <div class="muted">Supports multiple statements separated by <code>;</code></div>
            </div>
            <textarea id="sql">-- MiniDB SQL Workshop (run step-by-step)
-- Supported: CREATE TABLE, INSERT, SELECT, SELECT JOIN, UPDATE, DELETE
-- Types: INT, STRING, FLOAT
-- Constraints: PRIMARY, UNIQUE

-- Database commands (SQL-style)
-- CREATE DATABASE mydb;
-- USE mydb;

-- 1) CREATE TABLES (run once)
CREATE TABLE customers (id INT PRIMARY UNIQUE, name STRING, email STRING UNIQUE);
CREATE TABLE products (id INT PRIMARY UNIQUE, name STRING UNIQUE, price FLOAT);
CREATE TABLE orders (id INT PRIMARY UNIQUE, customer_id INT, product_id INT, qty INT, total FLOAT);
CREATE TABLE employees (id INT PRIMARY UNIQUE, email STRING UNIQUE, dept STRING, salary FLOAT);

-- 2) SEED DATA (INSERT)
INSERT INTO customers (id, name, email) VALUES (1, 'Amina', 'amina@example.com');
INSERT INTO customers (id, name, email) VALUES (2, 'Omar', 'omar@example.com');

INSERT INTO products (id, name, price) VALUES (10, 'Keyboard', 45.50);
INSERT INTO products (id, name, price) VALUES (11, 'Mouse', 18.00);
INSERT INTO products (id, name, price) VALUES (12, 'Monitor', 150.00);

-- Indexing demo dataset (more rows):
-- MiniDB maintains an internal index for PRIMARY/UNIQUE columns.
-- Here: employees.id (PRIMARY/UNIQUE) and employees.email (UNIQUE) are indexed.
INSERT INTO employees (id, email, dept, salary) VALUES (1, 'e1@corp.com', 'ENG', 120.0);
INSERT INTO employees (id, email, dept, salary) VALUES (2, 'e2@corp.com', 'ENG', 121.0);
INSERT INTO employees (id, email, dept, salary) VALUES (3, 'e3@corp.com', 'ENG', 122.0);
INSERT INTO employees (id, email, dept, salary) VALUES (4, 'e4@corp.com', 'HR', 90.0);
INSERT INTO employees (id, email, dept, salary) VALUES (5, 'e5@corp.com', 'HR', 91.0);
INSERT INTO employees (id, email, dept, salary) VALUES (6, 'e6@corp.com', 'SALES', 80.0);
INSERT INTO employees (id, email, dept, salary) VALUES (7, 'e7@corp.com', 'SALES', 82.5);
INSERT INTO employees (id, email, dept, salary) VALUES (8, 'e8@corp.com', 'OPS', 95.0);
INSERT INTO employees (id, email, dept, salary) VALUES (9, 'e9@corp.com', 'OPS', 96.0);
INSERT INTO employees (id, email, dept, salary) VALUES (10, 'e10@corp.com', 'ENG', 130.0);
INSERT INTO employees (id, email, dept, salary) VALUES (11, 'e11@corp.com', 'ENG', 131.0);
INSERT INTO employees (id, email, dept, salary) VALUES (12, 'e12@corp.com', 'HR', 92.0);

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

-- 9) BASIC "INDEX" behavior demo
-- Indexed lookups (PRIMARY/UNIQUE):
SELECT * FROM customers WHERE email = 'amina@example.com';
SELECT * FROM products WHERE name = 'Keyboard';
SELECT * FROM employees WHERE id = 10;
SELECT * FROM employees WHERE email = 'e7@corp.com';
-- Non-indexed lookup (dept is NOT UNIQUE): this requires scanning matching rows.
SELECT * FROM employees WHERE dept = 'ENG';

-- 10) CLEANUP (remove the seeded data + tables)
-- You can either DELETE rows or DROP TABLE. Here we DROP TABLE.
DROP TABLE employees;
DROP TABLE orders;
DROP TABLE products;
DROP TABLE customers;

-- 11) Verify tables are gone (these should ERROR with "Table not found")
SELECT * FROM customers;
SELECT * FROM products;
SELECT * FROM orders;
SELECT * FROM employees;
</textarea>
          </div>

          <div class="panel">
            <div class="panel-header">
              <h2>Live Data</h2>
              <div class="muted">Tables + sample rows</div>
            </div>
            <div class="output" id="live">Loading…</div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <h2>Terminal</h2>
            <div class="muted">Commands: <code>:help</code>, <code>:register</code>, <code>:login</code>, <code>:createdb</code>, <code>:use</code></div>
          </div>
          <div class="terminal">
            <div class="terminal-row">
              <input class="terminal-input" id="term" placeholder=":help" />
              <button class="btn btn-primary" id="btnTerm" type="button">Run</button>
            </div>
            <div class="output" id="termOut">Type :help to see commands.</div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <h2>Output</h2>
            <div class="muted">Results / errors</div>
          </div>
          <div class="output" id="out">Run a query to see results.</div>
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

    <div class=\"modal\" id=\"helpModal\">
      <div class=\"modal-card\">
        <div class=\"panel-header\" style=\"border-bottom:none; padding: 0 0 10px\">
          <h2>User Guide</h2>
          <div class=\"actions\">
            <button class=\"btn\" id=\"btnHelpClose\" type=\"button\">Close</button>
          </div>
        </div>
        <div class=\"help-body\">
          <div class=\"pill\" style=\"display:inline-block; margin-bottom:10px\">SQL Subset</div>
          <div>
            <div><code>CREATE TABLE t (id INT PRIMARY UNIQUE, name STRING, price FLOAT);</code></div>
            <div><code>INSERT INTO t (id, name, price) VALUES (1, 'A', 9.99);</code></div>
            <div><code>SELECT * FROM t;</code></div>
            <div><code>SELECT * FROM t WHERE id = 1;</code></div>
            <div><code>UPDATE t SET price=10.5 WHERE id=1;</code></div>
            <div><code>DELETE FROM t WHERE id=1;</code></div>
            <div><code>DROP TABLE t;</code></div>
            <div style=\"margin-top:10px\"><code>SELECT * FROM a JOIN b ON a_id = id;</code></div>
          </div>

          <div class=\"pill\" style=\"display:inline-block; margin:14px 0 10px\">Database (SQL-style)</div>
          <div>
            <div><code>CREATE DATABASE mydb;</code></div>
            <div><code>USE mydb;</code></div>
          </div>

          <div class=\"pill\" style=\"display:inline-block; margin:14px 0 10px\">Terminal Commands</div>
          <div>
            <div><code>:help</code> show this guide</div>
            <div><code>:register username password [email]</code> create user</div>
            <div><code>:login username password</code> login</div>
            <div><code>:logout</code> logout</div>
            <div><code>:whoami</code> show current user</div>
            <div><code>:dbs</code> list databases</div>
            <div><code>:createdb name</code> create database (requires login)</div>
            <div><code>:use name</code> switch database (requires login for non-default)</div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const elSql = document.getElementById('sql');
      const elOut = document.getElementById('out');
      const elLive = document.getElementById('live');
      const pill = document.getElementById('statusPill');
      const dbPill = document.getElementById('dbPill');
      const userPill = document.getElementById('userPill');
      const elTerm = document.getElementById('term');
      const elTermOut = document.getElementById('termOut');

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
        dbPill.textContent = `DB: ${data.current_db || 'default'}`;
        userPill.textContent = `User: ${data.username || 'anonymous'}`;
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

      async function runTerminal() {
        const cmd = (elTerm.value || '').trim();
        if (!cmd) return;
        setStatus('Running…');
        const resp = await fetch('/api/terminal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cmd })
        });
        const data = await resp.json();
        if (data && data.message) {
          elTermOut.textContent = data.message;
        } else {
          elTermOut.textContent = 'OK';
        }
        elTerm.value = '';
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

      document.getElementById('btnTerm').addEventListener('click', runTerminal);
      elTerm.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          runTerminal();
        }
      });

      // Help
      const helpModal = document.getElementById('helpModal');
      const btnHelp = document.getElementById('btnHelp');
      const btnHelpClose = document.getElementById('btnHelpClose');
      function openHelp() { helpModal.classList.add('open'); }
      function closeHelp() { helpModal.classList.remove('open'); }
      btnHelp.addEventListener('click', openHelp);
      btnHelpClose.addEventListener('click', closeHelp);
      helpModal.addEventListener('click', (e) => { if (e.target === helpModal) closeHelp(); });

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


def _handle_sql_db_statement(stmt: str) -> Any:
    s = stmt.strip().rstrip(";")
    upper = s.upper()
    if upper.startswith("CREATE DATABASE "):
        raw = s[len("CREATE DATABASE ") :].strip()
        name = _safe_db_name(raw)
        _require_login_for_db(name)
        os.makedirs(_db_dir(name), exist_ok=True)
        return 1
    if upper.startswith("USE "):
        raw = s[len("USE ") :].strip()
        name = _safe_db_name(raw)
        _require_login_for_db(name)
        os.makedirs(_db_dir(name), exist_ok=True)
        _set_current_db(name)
        return 1
    return None


def _terminal_help() -> str:
    return "\n".join(
        [
            "Terminal commands:",
            ":help",
            ":register <username> <password> [email]",
            ":login <username> <password>",
            ":logout",
            ":whoami",
            ":dbs",
            ":createdb <name>",
            ":use <name>",
            "SQL-style database commands (in SQL editor): CREATE DATABASE <name>;  USE <name>;",
        ]
    )


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
            maybe = _handle_sql_db_statement(stmt)
            if maybe is not None:
                results.append(_result_payload(maybe))
                continue

            db = _get_db()
            res = db.execute(stmt)
            results.append(_result_payload(res))
        except (MiniDBError, ParseError) as e:
            results.append({"kind": "error", "message": str(e)})
        except Exception as e:
            results.append({"kind": "error", "message": str(e)})

    return jsonify({"results": results})


@app.get("/api/state")
def api_state():
    db = _get_db()
    tables = []
    for name in db.catalog.list_tables():
        t = db.catalog.get_table(name)
        try:
            all_rows = t.select(["*"])
        except Exception:
            all_rows = []
        sample = all_rows[:25]
        tables.append({"name": name, "row_count": len(all_rows), "sample": sample})
    username = session.get("username") if isinstance(session.get("username"), str) else None
    return jsonify({"tables": tables, "current_db": _current_db_name(), "username": username})


@app.post("/api/terminal")
def api_terminal():
    data = request.get_json(silent=True) or {}
    cmd = str(data.get("cmd") or "").strip()
    if cmd == "":
        return jsonify({"message": ""})

    if not cmd.startswith(":"):
        return jsonify({"message": "Terminal commands must start with ':' (try :help)"})

    parts = cmd[1:].split()
    op = (parts[0] if parts else "").lower()

    try:
        if op in ("h", "help"):
            return jsonify({"message": _terminal_help()})

        if op == "register":
            if len(parts) < 3:
                return jsonify({"message": "Usage: :register <username> <password> [email]"})
            username = parts[1]
            password = parts[2]
            email = parts[3] if len(parts) >= 4 else ""
            uid = _auth_db.register_user(username=username, password=password, email=email, is_admin=0)
            return jsonify({"message": f"User created (id={uid}). You can now :login {username} <password>"})

        if op == "login":
            if len(parts) < 3:
                return jsonify({"message": "Usage: :login <username> <password>"})
            username = parts[1]
            password = parts[2]
            token = _auth_db.login(username=username, password=password)
            session["session_token"] = token
            session["username"] = username
            return jsonify({"message": f"Logged in as {username}"})

        if op == "logout":
            token = session.get("session_token")
            try:
                _auth_db.auth.logout(token if isinstance(token, str) else None)
            finally:
                session.pop("session_token", None)
                session.pop("username", None)
                session.pop("current_db", None)
            return jsonify({"message": "Logged out"})

        if op == "whoami":
            username = session.get("username") if isinstance(session.get("username"), str) else None
            if username:
                return jsonify({"message": f"User: {username}"})
            return jsonify({"message": "User: anonymous"})

        if op == "dbs":
            return jsonify({"message": "\n".join(_list_databases())})

        if op == "createdb":
            if len(parts) < 2:
                return jsonify({"message": "Usage: :createdb <name>"})
            name = _safe_db_name(parts[1])
            _require_login_for_db(name)
            os.makedirs(_db_dir(name), exist_ok=True)
            return jsonify({"message": f"Database created: {name}"})

        if op == "use":
            if len(parts) < 2:
                return jsonify({"message": "Usage: :use <name>"})
            name = _safe_db_name(parts[1])
            _require_login_for_db(name)
            os.makedirs(_db_dir(name), exist_ok=True)
            _set_current_db(name)
            return jsonify({"message": f"Using database: {name}"})

        return jsonify({"message": "Unknown command (try :help)"})
    except (MiniDBError, ValueError) as e:
        return jsonify({"message": str(e)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
