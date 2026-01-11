from __future__ import annotations

from getpass import getpass

from minidb import MiniDB
from minidb.errors import MiniDBError


def main() -> None:
    db = MiniDB("./minidb_data", enable_auth=True)
    username = input("Username: ").strip()
    password = getpass("Password: ")

    try:
        token = db.login(username, password)
    except Exception:
        create = input("User not found or bad password. Create user? (y/n): ").strip().lower() == "y"
        if not create:
            return
        email = input("Email (optional): ").strip()
        is_admin = 1 if input("Admin? (y/n): ").strip().lower() == "y" else 0
        db.register_user(username=username, password=password, email=email, is_admin=is_admin)
        token = db.login(username, password)

    print(f"Logged in as {username}")
    while True:
        sql = input("> ").strip()
        if sql.lower() in {"exit", "quit"}:
            db.close()
            return
        if sql == "":
            continue
        try:
            res = db.execute(sql, token)
            print(res)
        except MiniDBError as e:
            print(f"ERROR: {e}")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
