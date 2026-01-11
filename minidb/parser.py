from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .errors import ParseError


_kw = re.compile(r"\s+")


def _strip_semicolon(sql: str) -> str:
    s = sql.strip()
    if s.endswith(";"):
        s = s[:-1].rstrip()
    return s


def _parse_identifier(s: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s):
        raise ParseError(f"Invalid identifier: {s}")
    return s


def _split_csv(content: str) -> List[str]:
    items: List[str] = []
    buf = ""
    in_str = False
    i = 0
    while i < len(content):
        ch = content[i]
        if ch == "'":
            in_str = not in_str
            buf += ch
            i += 1
            continue
        if ch == "," and not in_str:
            items.append(buf.strip())
            buf = ""
            i += 1
            continue
        buf += ch
        i += 1
    if buf.strip() != "":
        items.append(buf.strip())
    return items


def _parse_value(token: str) -> Any:
    t = token.strip()
    if t.upper() == "NULL":
        return None
    if len(t) >= 2 and t[0] == "'" and t[-1] == "'":
        return t[1:-1]
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def parse(sql: str) -> Dict[str, Any]:
    sql = _strip_semicolon(sql)
    if sql == "":
        raise ParseError("Empty SQL")

    upper = sql.upper()
    if upper.startswith("DROP TABLE "):
        m = re.match(r"(?is)^DROP\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)$", sql)
        if not m:
            raise ParseError("Invalid DROP TABLE")
        table = _parse_identifier(m.group(1))
        return {"type": "DROP_TABLE", "table": table}

    if upper.startswith("CREATE TABLE "):
        m = re.match(r"(?is)^CREATE\s+TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)$", sql)
        if not m:
            raise ParseError("Invalid CREATE TABLE")
        table = _parse_identifier(m.group(1))
        cols_raw = _split_csv(m.group(2))
        cols: List[Dict[str, Any]] = []
        for cdef in cols_raw:
            parts = _kw.split(cdef.strip())
            if len(parts) < 2:
                raise ParseError("Invalid column definition")
            name = _parse_identifier(parts[0])
            dtype = parts[1].upper()
            primary = any(p.upper() == "PRIMARY" for p in parts[2:])
            unique = any(p.upper() == "UNIQUE" for p in parts[2:])
            cols.append({"name": name, "dtype": dtype, "primary": primary, "unique": unique})
        return {"type": "CREATE_TABLE", "table": table, "columns": cols}

    if upper.startswith("INSERT INTO "):
        m = re.match(
            r"(?is)^INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s+VALUES\s*\(([^)]*)\)$",
            sql,
        )
        if not m:
            raise ParseError("Invalid INSERT")
        table = _parse_identifier(m.group(1))
        cols = [_parse_identifier(x.strip()) for x in _split_csv(m.group(2))]
        vals = [_parse_value(x) for x in _split_csv(m.group(3))]
        if len(cols) != len(vals):
            raise ParseError("INSERT columns/values mismatch")
        return {"type": "INSERT", "table": table, "row": dict(zip(cols, vals))}

    if upper.startswith("SELECT "):
        m = re.match(
            r"(?is)^SELECT\s+(.*?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+JOIN\s+([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*))?(?:\s+WHERE\s+([A-Za-z_][A-Za-z0-9_]*)\s*(=|<|>)\s*(.*))?$",
            sql,
        )
        if not m:
            raise ParseError("Invalid SELECT")
        cols_raw = m.group(1).strip()
        cols = ["*"] if cols_raw == "*" else [_parse_identifier(x.strip()) for x in _split_csv(cols_raw)]
        table = _parse_identifier(m.group(2))
        join_table = m.group(3)
        join = None
        if join_table:
            join = {
                "table": _parse_identifier(join_table),
                "left": _parse_identifier(m.group(4)),
                "right": _parse_identifier(m.group(5)),
            }
        where = None
        if m.group(6):
            where = (_parse_identifier(m.group(6)), m.group(7), _parse_value(m.group(8).strip()))
        return {"type": "SELECT", "table": table, "columns": cols, "join": join, "where": where}

    if upper.startswith("UPDATE "):
        m = re.match(
            r"(?is)^UPDATE\s+([A-Za-z_][A-Za-z0-9_]*)\s+SET\s+(.*?)(?:\s+WHERE\s+([A-Za-z_][A-Za-z0-9_]*)\s*(=|<|>)\s*(.*))?$",
            sql,
        )
        if not m:
            raise ParseError("Invalid UPDATE")
        table = _parse_identifier(m.group(1))
        updates_raw = _split_csv(m.group(2))
        updates: Dict[str, Any] = {}
        for assign in updates_raw:
            if "=" not in assign:
                raise ParseError("Invalid SET assignment")
            col, val = assign.split("=", 1)
            updates[_parse_identifier(col.strip())] = _parse_value(val.strip())
        where = None
        if m.group(3):
            where = (_parse_identifier(m.group(3)), m.group(4), _parse_value(m.group(5).strip()))
        return {"type": "UPDATE", "table": table, "updates": updates, "where": where}

    if upper.startswith("DELETE FROM "):
        m = re.match(
            r"(?is)^DELETE\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+WHERE\s+([A-Za-z_][A-Za-z0-9_]*)\s*(=|<|>)\s*(.*))?$",
            sql,
        )
        if not m:
            raise ParseError("Invalid DELETE")
        table = _parse_identifier(m.group(1))
        where = None
        if m.group(2):
            where = (_parse_identifier(m.group(2)), m.group(3), _parse_value(m.group(4).strip()))
        return {"type": "DELETE", "table": table, "where": where}

    raise ParseError("Unsupported SQL")
