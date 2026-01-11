python -m compileall minidb repl.py web_demo\app.py

How to run the RDBMS
--
Start the app from repo root:
py web_based_RDBMS_sql_repl\app.py


1) REPL
py repl.py

2) Web demo (Bills Management Admin Panel)
Install Flask:
py -m pip install -r requirements.txt

Run web app:
py -m web_demo.app

After code updates
Run:
py -m py_compile web_demo\app.py