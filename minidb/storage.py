from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .errors import ConstraintViolation, SchemaError


SUPPORTED_TYPES = {"INT", "STRING", "FLOAT"}


def _atomic_write_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _coerce_value(value: Any, dtype: str) -> Any:
    if value is None:
        return None
    if dtype == "INT":
        if isinstance(value, bool):
            raise SchemaError("Invalid INT")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str) and value.strip() != "":
            return int(value)
        raise SchemaError("Invalid INT")
    if dtype == "FLOAT":
        if isinstance(value, bool):
            raise SchemaError("Invalid FLOAT")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip() != "":
            return float(value)
        raise SchemaError("Invalid FLOAT")
    if dtype == "STRING":
        if isinstance(value, str):
            return value
        return str(value)
    raise SchemaError(f"Unsupported type: {dtype}")


@dataclass
class Column:
    name: str
    dtype: str
    primary: bool = False
    unique: bool = False


class Table:
    def __init__(
        self,
        name: str,
        columns: List[Column],
        persistence_dir: str,
        existing_rows: Optional[List[Dict[str, Any]]] = None,
    ):
        self.name = name
        self.columns = columns
        self.schema: Dict[str, str] = {c.name: c.dtype for c in columns}
        self.primary_key: Optional[str] = next((c.name for c in columns if c.primary), None)
        self.unique_cols: List[str] = [c.name for c in columns if c.unique or c.primary]
        if len([c for c in columns if c.primary]) > 1:
            raise SchemaError("Only one PRIMARY KEY supported")
        for c in columns:
            if c.dtype not in SUPPORTED_TYPES:
                raise SchemaError(f"Unsupported type: {c.dtype}")
        self._rows: List[Dict[str, Any]] = []
        self._indexes: Dict[str, Dict[Any, int]] = {}
        self._persistence_dir = persistence_dir
        self._data_path = os.path.join(persistence_dir, f"{name}.rows.json")
        self._meta_path = os.path.join(persistence_dir, f"{name}.meta.json")

        if existing_rows is not None:
            self._rows = existing_rows
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        self._indexes = {col: {} for col in self.unique_cols}
        for i, row in enumerate(self._rows):
            for col in self.unique_cols:
                v = row.get(col)
                if v is None:
                    if col == self.primary_key:
                        raise ConstraintViolation("PRIMARY KEY cannot be NULL")
                    continue
                if v in self._indexes[col]:
                    raise ConstraintViolation(f"Duplicate value for UNIQUE column {col}")
                self._indexes[col][v] = i

    def to_meta(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": [
                {"name": c.name, "dtype": c.dtype, "primary": c.primary, "unique": c.unique}
                for c in self.columns
            ],
        }

    @classmethod
    def load(cls, name: str, persistence_dir: str) -> "Table":
        meta_path = os.path.join(persistence_dir, f"{name}.meta.json")
        data_path = os.path.join(persistence_dir, f"{name}.rows.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        cols = [
            Column(
                name=c["name"],
                dtype=c["dtype"],
                primary=bool(c.get("primary")),
                unique=bool(c.get("unique")),
            )
            for c in meta["columns"]
        ]
        rows: List[Dict[str, Any]] = []
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        return cls(name=name, columns=cols, persistence_dir=persistence_dir, existing_rows=rows)

    def persist(self) -> None:
        os.makedirs(self._persistence_dir, exist_ok=True)
        _atomic_write_json(self._meta_path, self.to_meta())
        _atomic_write_json(self._data_path, self._rows)

    def _validate_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for col, dtype in self.schema.items():
            out[col] = _coerce_value(row.get(col), dtype)
        if self.primary_key:
            if out.get(self.primary_key) is None:
                raise ConstraintViolation("PRIMARY KEY cannot be NULL")
        return out

    def insert(self, row: Dict[str, Any]) -> None:
        new_row = self._validate_row(row)
        for col in self.unique_cols:
            v = new_row.get(col)
            if v is None:
                continue
            if v in self._indexes[col]:
                raise ConstraintViolation(f"Duplicate value for UNIQUE column {col}")
        idx = len(self._rows)
        self._rows.append(new_row)
        for col in self.unique_cols:
            v = new_row.get(col)
            if v is None:
                continue
            self._indexes[col][v] = idx

    def _match_where(self, row: Dict[str, Any], where: Optional[Tuple[str, str, Any]]) -> bool:
        if where is None:
            return True
        col, op, val = where
        if col not in self.schema:
            raise SchemaError(f"Unknown column: {col}")
        left = row.get(col)
        right = _coerce_value(val, self.schema[col])
        if op == "=":
            return left == right
        if op == ">":
            return left is not None and right is not None and left > right
        if op == "<":
            return left is not None and right is not None and left < right
        raise SchemaError(f"Unsupported operator: {op}")

    def select(self, columns: Optional[List[str]] = None, where: Optional[Tuple[str, str, Any]] = None) -> List[Dict[str, Any]]:
        if columns is None:
            columns = list(self.schema.keys())
        for c in columns:
            if c != "*" and c not in self.schema:
                raise SchemaError(f"Unknown column: {c}")
        if columns == ["*"]:
            columns = list(self.schema.keys())

        if where and where[1] == "=" and where[0] in self._indexes:
            col, _, val = where
            v = _coerce_value(val, self.schema[col])
            if v in self._indexes[col]:
                row = self._rows[self._indexes[col][v]]
                return [{c: row.get(c) for c in columns}]
            return []

        out: List[Dict[str, Any]] = []
        for row in self._rows:
            if self._match_where(row, where):
                out.append({c: row.get(c) for c in columns})
        return out

    def update(self, updates: Dict[str, Any], where: Optional[Tuple[str, str, Any]] = None) -> int:
        for col in updates:
            if col not in self.schema:
                raise SchemaError(f"Unknown column: {col}")

        count = 0
        new_rows = list(self._rows)
        for i, row in enumerate(self._rows):
            if not self._match_where(row, where):
                continue
            candidate = dict(row)
            for col, val in updates.items():
                candidate[col] = _coerce_value(val, self.schema[col])
            if self.primary_key and candidate.get(self.primary_key) is None:
                raise ConstraintViolation("PRIMARY KEY cannot be NULL")
            new_rows[i] = candidate
            count += 1

        self._rows = new_rows
        self._rebuild_indexes()
        return count

    def delete(self, where: Optional[Tuple[str, str, Any]] = None) -> int:
        kept: List[Dict[str, Any]] = []
        removed = 0
        for row in self._rows:
            if self._match_where(row, where):
                removed += 1
            else:
                kept.append(row)
        self._rows = kept
        self._rebuild_indexes()
        return removed


class Catalog:
    def __init__(self, persistence_dir: str):
        self.persistence_dir = persistence_dir
        self._tables: Dict[str, Table] = {}

    def list_tables(self) -> List[str]:
        return sorted(self._tables.keys())

    def has_table(self, name: str) -> bool:
        return name in self._tables

    def get_table(self, name: str) -> Table:
        if name not in self._tables:
            raise SchemaError(f"Table not found: {name}")
        return self._tables[name]

    def load_existing(self) -> None:
        if not os.path.exists(self.persistence_dir):
            return
        for fn in os.listdir(self.persistence_dir):
            if fn.endswith(".meta.json"):
                name = fn[: -len(".meta.json")]
                if name not in self._tables:
                    self._tables[name] = Table.load(name, self.persistence_dir)

    def create_table(self, name: str, columns: List[Column]) -> Table:
        if name in self._tables:
            raise SchemaError(f"Table already exists: {name}")
        t = Table(name=name, columns=columns, persistence_dir=self.persistence_dir)
        self._tables[name] = t
        t.persist()
        return t
