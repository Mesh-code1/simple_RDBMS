from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from .auth import Authenticator
from .errors import AuthError, SchemaError
from .parser import parse
from .storage import Catalog, Column


class MiniDB:
    def __init__(self, persistence_dir: str = "./minidb_data", enable_auth: bool = True):
        self.persistence_dir = persistence_dir
        self.enable_auth = enable_auth
        self.catalog = Catalog(persistence_dir=persistence_dir)
        self.catalog.load_existing()
        self.auth = Authenticator()
        if enable_auth:
            self._ensure_users_table()

    def _ensure_users_table(self) -> None:
        if self.catalog.has_table("users"):
            return
        self.catalog.create_table(
            "users",
            [
                Column("id", "INT", primary=True, unique=True),
                Column("username", "STRING", unique=True),
                Column("password_hash", "STRING"),
                Column("email", "STRING"),
                Column("is_admin", "INT"),
            ],
        )

    def _next_int_id(self, table: str) -> int:
        t = self.catalog.get_table(table)
        rows = t.select(["id"], None)
        max_id = 0
        for r in rows:
            v = r.get("id")
            if isinstance(v, int) and v > max_id:
                max_id = v
        return max_id + 1

    def register_user(self, username: str, password: str, email: str = "", is_admin: int = 0) -> int:
        if not self.enable_auth:
            raise AuthError("Auth disabled")
        users = self.catalog.get_table("users")
        uid = self._next_int_id("users")
        users.insert(
            {
                "id": uid,
                "username": username,
                "password_hash": self.auth.hash_password(password),
                "email": email,
                "is_admin": int(is_admin),
            }
        )
        users.persist()
        return uid

    def login(self, username: str, password: str) -> str:
        if not self.enable_auth:
            raise AuthError("Auth disabled")
        users = self.catalog.get_table("users")
        rows = users.select(["id", "username", "password_hash"], ("username", "=", username))
        if not rows:
            raise AuthError("Invalid credentials")
        row = rows[0]
        if row.get("password_hash") != self.auth.hash_password(password):
            raise AuthError("Invalid credentials")
        return self.auth.create_session(int(row["id"]), str(row["username"]))

    def validate(self, token: Optional[str]) -> Tuple[int, str]:
        s = self.auth.validate(token)
        return s.user_id, s.username

    def close(self) -> None:
        for name in self.catalog.list_tables():
            self.catalog.get_table(name).persist()

    def execute(self, sql: str, session_token: Optional[str] = None) -> Any:
        session = None
        if self.enable_auth:
            session = self.auth.validate(session_token)

        ast = parse(sql)
        t = ast["type"]

        if t == "CREATE_TABLE":
            cols = [
                Column(
                    name=c["name"],
                    dtype=c["dtype"],
                    primary=bool(c.get("primary")),
                    unique=bool(c.get("unique")),
                )
                for c in ast["columns"]
            ]
            self.catalog.create_table(ast["table"], cols)
            return 1

        if t == "INSERT":
            table = self.catalog.get_table(ast["table"])
            row = dict(ast["row"])
            if self.enable_auth and "user_id" in table.schema and "user_id" not in row:
                row["user_id"] = session.user_id
            table.insert(row)
            table.persist()
            return 1

        if t == "SELECT":
            if ast.get("join") is None:
                table = self.catalog.get_table(ast["table"])
                where = ast.get("where")
                if self.enable_auth and "user_id" in table.schema and not self._is_admin(session.user_id):
                    where = self._and_where(where, ("user_id", "=", session.user_id))
                return table.select(ast.get("columns"), where)

            left = self.catalog.get_table(ast["table"])
            join = ast["join"]
            right = self.catalog.get_table(join["table"])

            where_left = ast.get("where")
            if self.enable_auth and "user_id" in left.schema and not self._is_admin(session.user_id):
                where_left = self._and_where(where_left, ("user_id", "=", session.user_id))

            left_rows = left.select(["*"], where_left)
            results: List[Dict[str, Any]] = []
            for lr in left_rows:
                lv = lr.get(join["left"])
                rr = right.select(["*"], (join["right"], "=", lv))
                for rrow in rr:
                    merged = {**{f"{left.name}.{k}": v for k, v in lr.items()}, **{f"{right.name}.{k}": v for k, v in rrow.items()}}
                    results.append(merged)

            cols = ast.get("columns")
            if cols == ["*"]:
                return results
            projected: List[Dict[str, Any]] = []
            for row in results:
                projected.append({c: row.get(c) for c in cols})
            return projected

        if t == "UPDATE":
            table = self.catalog.get_table(ast["table"])
            where = ast.get("where")
            if self.enable_auth and "user_id" in table.schema and not self._is_admin(session.user_id):
                where = self._and_where(where, ("user_id", "=", session.user_id))
            n = table.update(ast["updates"], where)
            table.persist()
            return n

        if t == "DELETE":
            table = self.catalog.get_table(ast["table"])
            where = ast.get("where")
            if self.enable_auth and "user_id" in table.schema and not self._is_admin(session.user_id):
                where = self._and_where(where, ("user_id", "=", session.user_id))
            n = table.delete(where)
            table.persist()
            return n

        raise SchemaError("Unsupported AST")

    def _and_where(self, a: Optional[Tuple[str, str, Any]], b: Tuple[str, str, Any]) -> Tuple[str, str, Any]:
        if a is None:
            return b
        if a[0] == b[0] and a[1] == "=" and b[1] == "=":
            return a
        raise SchemaError("Only one WHERE condition supported")

    def _is_admin(self, user_id: int) -> bool:
        if not self.enable_auth:
            return True
        users = self.catalog.get_table("users")
        r = users.select(["is_admin"], ("id", "=", user_id))
        if not r:
            return False
        v = r[0].get("is_admin")
        return bool(v) and int(v) != 0
