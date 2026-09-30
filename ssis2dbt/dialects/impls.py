"""Concrete dialect implementations (PRD section 6.1)."""
from __future__ import annotations

from .base import Dialect, register


class Snowflake(Dialect):
    name = "snowflake"

    def current_timestamp(self) -> str:
        return "current_timestamp()"

    def limit(self, n: int) -> str:
        return f"limit {n}"


class TSQL(Dialect):
    name = "tsql"

    def current_timestamp(self) -> str:
        return "getdate()"

    def coalesce(self, a: str, b: str) -> str:
        return f"isnull({a}, {b})"

    def length(self, x: str) -> str:
        return f"len({x})"

    def limit(self, n: int) -> str:
        # T-SQL uses TOP; callers handle placement. Return marker.
        return f"top ({n})"

    def concat(self, a: str, b: str) -> str:
        return f"{a} + {b}"

    def quote_ident(self, ident: str) -> str:
        return f"[{ident}]"


class Databricks(Dialect):
    name = "databricks"

    def current_timestamp(self) -> str:
        return "current_timestamp()"

    def concat(self, a: str, b: str) -> str:
        return f"concat({a}, {b})"

    def quote_ident(self, ident: str) -> str:
        return f"`{ident}`"


register(Snowflake())
register(TSQL())
register(Databricks())
