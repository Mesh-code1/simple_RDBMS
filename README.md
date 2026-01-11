# simple_RDBMS (MiniDB)

## Live Demos

- <a href="https://simple-rdbms-sql-repl.onrender.com" target="_blank" rel="noopener noreferrer">Live RDBMS (SQL REPL)</a>
- <a href="https://simple-rdbms-bills-demo.onrender.com" target="_blank" rel="noopener noreferrer">Billing Web App Demo</a>



A lightweight, educational Relational Database Management System (RDBMS) implemented in **pure Python (standard library)**, with:

- A small **SQL subset** (regex-based parser)
- **Persistent storage** to JSON files
- **Primary/Unique key constraints**
- **Basic indexing** on PRIMARY/UNIQUE columns
- **Simple INNER JOIN** support
- A console **REPL**
- A Flask **Bills Management Admin Panel** demo (`web_demo`)
- A modern, web-based **SQL REPL** (`web_based_RDBMS_sql_repl`) including:
  - A split SQL editor + output + live data explorer
  - A terminal for user/session + database management
  - Multi-database persistence

This project is intentionally small and readable. It is not a production database.

---

## Repository layout

- `minidb/`
  - Core database engine
  - SQL parsing (`parser.py`)
  - Storage engine + persistence (`storage.py`)
  - Auth + sessions (`auth.py`, `db.py`)
- `repl.py`
  - Console REPL for MiniDB
- `web_demo/`
  - Flask Bills Management Admin Panel demo
- `web_based_RDBMS_sql_repl/`
  - Flask web-based SQL REPL (modern UI)
- `requirements.txt`
  - Python dependencies for the Flask apps (core MiniDB uses stdlib)
- `setup.md`
  - Quick run commands

---

## Features

### SQL subset

MiniDB supports the following statements:

- `CREATE TABLE`
- `INSERT INTO ... VALUES ...`
- `SELECT ... FROM ...`
  - Optional: `WHERE col (=|<|>) value`
  - Optional: `JOIN table2 ON left_col = right_col` (single JOIN)
- `UPDATE ... SET ... [WHERE ...]`
- `DELETE FROM ... [WHERE ...]`
- `DROP TABLE <name>`

#### Column types

Supported column types:

- `INT`
- `FLOAT`
- `STRING`

#### Constraints

- `PRIMARY` (one per table)
- `UNIQUE` (per column)

PRIMARY is also treated as UNIQUE internally.

---

## MiniDB architecture (high level)

MiniDB is composed of a few small components:

### 1) Parser (`minidb/parser.py`)

- Regex-based parsing into a small AST (Python dict)
- Supported statement types map to AST node types like:
  - `CREATE_TABLE`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`, `DROP_TABLE`

### 2) Storage engine (`minidb/storage.py`)

#### Table representation

- Schema: `Dict[column_name -> dtype]`
- Rows: `List[Dict[str, Any]]`
- Persistence:
  - `<table>.meta.json` stores schema + constraints
  - `<table>.rows.json` stores row data

#### Indexing

- MiniDB maintains in-memory hash indexes for **PRIMARY/UNIQUE** columns:
  - `_indexes[col][value] -> row_index`
- `SELECT` with an equality predicate on an indexed column can return in O(1) average time.
- Non-indexed predicates and inequality predicates fall back to a full scan.

### 3) Executor / Orchestrator (`minidb/db.py`)

- `MiniDB.execute(sql, session_token=None)`:
  - validates sessions when `enable_auth=True`
  - parses SQL to AST
  - dispatches to table operations
  - persists on mutations

### 4) Authenticator (`minidb/auth.py` + `minidb/db.py`)

When `enable_auth=True`:

- A `users` table is auto-created in the DB persistence directory
- Passwords are stored as `sha256` hashes
- Sessions are UUID tokens stored in-memory with TTL

> Note: Sessions are not persisted across process restarts.

---

## Persistence model

MiniDB persists tables to JSON:

- `*.meta.json` (schema + constraints)
- `*.rows.json` (data)

Each app uses its own persistence directory to keep data separate:

- Bills demo: `./minidb_data/` (or the configured folder)
- Web SQL REPL default DB: `./web_based_RDBMS_sql_repl_data/`
- Web SQL REPL auth DB: `./web_based_RDBMS_sql_repl_auth/`
- Web SQL REPL non-default DBs: `./web_based_RDBMS_sql_repl_databases/<db_name>/`

---

## How to run

### Requirements

- Python 3.x
- Flask for the web apps:
  - `py -m pip install -r requirements.txt`

### Quick sanity compile

From repo root:

```bash
py -m compileall minidb repl.py web_demo\app.py
```

### 1) Console REPL

```bash
py repl.py
```

Depending on how you configure the REPL, it may ask for username/password (MiniDB auth is enabled by default when used directly).

### 2) Bills Management Admin Panel (`web_demo`)

```bash
py -m web_demo.app
```

Then open:

- `http://127.0.0.1:5000/`

Features:

- Register/Login
- Add bills (amount + due date)
- Manage bills (edit, delete, change status)
- Record payments
- Correct bill status recomputation based on total payments

### 3) Web-based SQL REPL (`web_based_RDBMS_sql_repl`)

```bash
py -m web_based_RDBMS_sql_repl.app
```

Then open:

- `http://127.0.0.1:5001/`

---

## Web SQL REPL: databases, terminal, and auth

The web SQL REPL offers two ways to manage databases:

### A) SQL-style DB commands (in the SQL editor)

```sql
CREATE DATABASE mydb;
USE mydb;
```

### B) Terminal-style commands (in the Terminal panel)

- `:help`
- `:register <username> <password> [email]`
- `:login <username> <password>`
- `:logout`
- `:whoami`
- `:dbs`
- `:createdb <name>;`
- `:use <name>;`

#### Auth rules

- The **default database** (`default`) is usable without login (keeps the “demo mode” working).
- Creating/using **non-default databases** requires login.

---

## Example SQL (supported)

### Create tables

```sql
CREATE TABLE customers (id INT PRIMARY UNIQUE, name STRING, email STRING UNIQUE);
CREATE TABLE orders (id INT PRIMARY UNIQUE, customer_id INT, total FLOAT);
```

### Insert

```sql
INSERT INTO customers (id, name, email) VALUES (1, 'Amina', 'amina@example.com');
INSERT INTO orders (id, customer_id, total) VALUES (100, 1, 91.00);
```

### Select + Where

```sql
SELECT * FROM customers WHERE email = 'amina@example.com';
SELECT * FROM orders WHERE total > 50;
```

### Join

```sql
SELECT * FROM orders JOIN customers ON customer_id = id;
```

### Update

```sql
UPDATE customers SET name='Amina M.' WHERE id=1;
```

### Delete

```sql
DELETE FROM orders WHERE id=100;
```

### Drop table

```sql
DROP TABLE orders;
```

---

## Notes, limitations, and non-goals

- No transactions, locking, or concurrent writers.
- JOINs are nested-loop joins (fine for small datasets).
- Only one JOIN per SELECT.
- SQL grammar is intentionally strict and small.
- Sessions are in-memory only.

---

## Troubleshooting

- If you see `Unsupported SQL`, check:
  - You’re using the supported SQL subset
  - Statements are separated by semicolons
  - String values use single quotes: `'text'`

- If you see `Invalid database name`:
  - Database names must match: `[A-Za-z_][A-Za-z0-9_]*`

---

## License

Educational / demo project. 