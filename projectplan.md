Implementation Strategy for MiniDB: A Persistent, Secure, General-Purpose RDBMS
The strategy outlines the design and implementation of MiniDB, a lightweight RDBMS in Python using only the standard library for the core (with optional Flask for the web demo). It supports declaring tables with column data types (INT, STRING, FLOAT), CRUD operations, basic indexing on primary/unique keys, and inner joins on equality conditions. The interface is a SQL subset parsed via regex-based tokenization, with a real interactive REPL using input(). Storage is in-memory for performance but persists to JSON files for durability across sessions/restarts. Basic security enforces username/password authentication with hashed credentials, restricting access to owned data (e.g., via user_id filtering).
MiniDB is general-purpose: The MiniDB class is importable, with execute(sql, session_token=None) for programmatic use in any web app. Auth is enabled by default but toggleable; persistence is automatic. The demo is a Flask-based bills management admin panel, showcasing CRUD on a relational schema (users, bills, payments) with joins (e.g., user-bill-payment) and security (ownership checks).
1. High-Level Architecture

Core Components:
Parser: Tokenizes SQL into an AST for the supported subset.
Executor: Validates auth, interprets AST, performs operations on storage.
Storage Engine: Manages tables, rows, schemas, indexes, constraints, and persistence.
Authenticator: Handles login/validation for security.
REPL: Secure interactive shell with credential prompts.

Data Flow:
Credentials → Authenticator → Session token.
SQL + token → Parser → AST → Auth validation → Executor → Storage ops.
Mutations → Persistence sync.
Results → Raw dicts for apps; pretty-printed for REPL.

Modularity: Pluggable layers (e.g., auth via enable_auth=True, persistence via persistence_dir='./data').
Assumptions: Case-insensitive keywords; quoted strings for values; no transactions/concurrency (add locks later). Files in configurable dir (e.g., ./minidb_data/).

2. Detailed Component Strategies
2.1 Storage Engine (Table Class)

Schema Representation: Dict {column_name: data_type} (types: 'INT', 'STRING', 'FLOAT'). Metadata (schema, constraints) in separate JSON.
Data Storage: List of row dicts ({'col': value}); loaded from table_name.json on init.
Constraints:
Primary Key: One per table; non-null + unique, via dedicated index set.
Unique Key: Per-column (or composite via tuple hashes).
Enforcement: Validate on INSERT/UPDATE before commit; raise ConstraintViolation.

Indexing:
Hash sets {column: set(values)} for PK/UK columns.
Auto-maintain: Add on INSERT, discard/add on UPDATE, discard on DELETE.
Usage: O(1) equality lookups in WHERE; full scan for inequalities/joins.

Row Validation: Strict type checks/coercion; nulls ok except PK.
Persistence:
Load: On startup/Table init: json.load() data; rebuild indexes from rows.
Dump: Post-mutation: Atomic json.dump() to temp file then rename. Batch (e.g., every 10 ops); full dump on MiniDB.close().
Special: users table (users.json) for auth: {id INT PRIMARY, username STRING UNIQUE, password_hash STRING, email STRING}.
Hooks: For bills app, persist bills.json, payments.json; app-level FK checks via joins.


2.2 SQL Parser

Approach: Regex tokenization (split on spaces/commas/parens); build AST as nested dicts.
Supported Grammar:
CREATE TABLE table (col1 TYPE [PRIMARY|UNIQUE], ...);
INSERT INTO table (cols) VALUES (vals);
SELECT [cols|*] FROM table [JOIN table2 ON col1=col2] [WHERE col op val]; (op: =, >, <)
UPDATE table SET col1=val1,... [WHERE ...];
DELETE FROM table [WHERE ...];

Parsing Steps:
Uppercase keywords; extract clauses (e.g., FROM (\w+), WHERE (\w+\s*[=<>]\s*'[^']*')).
Infer types for vals (e.g., '42.5' → float if FLOAT col).
AST: e.g., {'type': 'SELECT', 'from': 'bills', 'join': {'table': 'payments', 'on': ('id', 'bill_id')}, 'where': {'user_id': {'op': '=', 'val': 1}}}.

Security: Validate tokens (reject DROP); escape vals (strip ;, limit len); auto-inject user_id = ? for ownership.

2.3 Query Executor (MiniDB.execute(sql, session_token=None))

Orchestration:
Auth check: Raise AuthError if invalid/expired.
Parse → Schema validate (table exists, types match).
Execute → Persist if mutation.
Return: List[dict] for SELECT; int for counts.

CRUD Execution (Tuned for Bills):
CREATE: Parse/build Table; persist schema/constraints JSON. E.g., bills (id INT PRIMARY, user_id INT, description STRING, amount FLOAT, due_date STRING, status STRING UNIQUE); index due_date.
INSERT: Validate row; append/update indexes; e.g., auto-set user_id from token.
SELECT: Filter via index (equality); JOIN: Loop left rows, filter right on on_col (O(n*m), optimized if indexed); project cols. E.g., SELECT b.description, p.amount FROM bills b JOIN payments p ON b.id = p.bill_id WHERE b.user_id = ?.
UPDATE: Select matches; update fields (re-validate/constrain); e.g., set status='paid' only if owned.
DELETE: Select/remove; e.g., delete bill only if user_id = ? (app cascades payments).

WHERE Handling: {'col': {'op': op, 'val': value}}; type-safe eval (numeric for >/<).

2.4 Authenticator (Class)

Approach: Session tokens (UUID + expiry, 24h); in-memory dict {token: {'user_id': int, 'expiry': datetime}}.
Operations:
login(username, password) → token: Load users table; hash check (hashlib.sha256(password.encode()).hexdigest()); generate/return token.
validate(token) → user_id: Check expiry; refresh if <1h left.
logout(token): Remove from sessions.

Security: Hashed pw (no salt for basic); expiry anti-replay. For bills: Inject user_id into WHERE for ownership. REPL/web: Token in session/cookie.
Errors: AuthError (InvalidCreds, Expired); 401 for web.

2.5 REPL Implementation

Interactivity: __main__: db = MiniDB('./data', enable_auth=True); Prompt "Username: ", mask "Password: " (getpass); token = db.login(); if valid: loop sql = input('> '); if 'exit': db.close(); break; db.execute(sql, token).
Features: Print "Logged in as {username}"; re-prompt on expiry. Mutations auto-persist; results as markdown tables.

3. Execution Flow Example

Startup: Load users.json → other tables → rebuild indexes.
Login: Hash verify → token.
INSERT INTO bills (id, user_id, description, amount, due_date, status) VALUES (1, 1, 'Rent', 1200.0, '2026-02-01', 'pending'); → Auth ok → Parse → Insert (user_id=1) → Persist.
Restart: Load bills → SELECT * FROM bills WHERE user_id=1; shows data.
Unauthorized: Invalid token → AuthError.

4. Integration for Web Apps – Bills Management Admin Panel

Generality: Import from minidb import MiniDB; db = MiniDB('./app_data', enable_auth=True); Use db.login in auth route; pass token to execute.
Demo (bills_panel.py with Flask; pip install flask):
Schema Init: On startup/load: Create/load users, bills (PK id, FK-like user_id, description STRING, amount FLOAT, due_date STRING indexed, status STRING UNIQUE), payments (PK id, bill_id INT, amount FLOAT, payment_date STRING).
Auth Routes: /login (POST: form → session['token'] = db.login(); redirect); /logout (del session['token']; redirect).
Protected Routes (Decorator @requires_auth: validate token, get user_id):
/dashboard (GET: SELECT b.*, u.username FROM bills b JOIN users u ON b.user_id = u.id WHERE b.user_id = ? ORDER BY due_date; render Bootstrap table: desc, amount, due (highlight overdue via current date), status; filter via form-submitted WHERE).
/add_bill (POST: form → INSERT INTO bills (..., user_id=?) VALUES (...); redirect dashboard).
/pay_bill/<int:bill_id> (POST: If SELECT * FROM bills WHERE id=? AND user_id=? exists: INSERT INTO payments ...; UPDATE bills SET status='paid' WHERE id=? AND user_id=?;).
/delete_bill/<int:bill_id> (POST: If owned: DELETE FROM payments WHERE bill_id=?; DELETE FROM bills WHERE id=? AND user_id=?;).

UI: Login form; dashboard table with actions (pay/delete buttons); forms for add/pay. Use Jinja2 for raw results; flash errors (e.g., AuthError → login).
Security/Persistence: All ops bind user_id; data survives logout/restart. Demo: Admin user views all (bypass via superuser flag).


5. Extensibility and Edge Cases

Future-Proofing: AST for adding aggregates; persistence to DB adapter; auth to JWT. Transactions: Wrap in try/finally.
Edge Cases:
Persistence: File locks (fcntl) for concurrency; corrupt load → empty + backup.
Security: Rate-limit logins (counter); bills dates → parse/validate in app.
Scale: Warn scans >1k rows; more indexes (e.g., status).

Testing: Parser (valid SQL), executor (persistence roundtrip), auth (ownership), bills flows (join queries).
Credit/Originality: Concepts from DB principles (e.g., indexing like PostgreSQL basics); fully original implementation.