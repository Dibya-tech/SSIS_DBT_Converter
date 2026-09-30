"""Dialect emitters translate dialect-neutral concerns into target SQL.

Adding a new warehouse target means adding a Dialect subclass and registering
it -- no changes to the converters (PRD sections 6, 11 extensibility).
"""
from __future__ import annotations


class Dialect:
    name = "generic"

    # function name -> template using {args} placeholders by position {0},{1}
    def current_timestamp(self) -> str:
        return "current_timestamp()"

    def coalesce(self, a: str, b: str) -> str:
        return f"coalesce({a}, {b})"

    def length(self, x: str) -> str:
        return f"length({x})"

    def try_cast(self, expr: str, sqltype: str) -> str:
        return f"try_cast({expr} as {sqltype})"

    def cast(self, expr: str, sqltype: str) -> str:
        return f"cast({expr} as {sqltype})"

    def limit(self, n: int) -> str:
        return f"limit {n}"

    def concat(self, a: str, b: str) -> str:
        return f"{a} || {b}"

    def quote_ident(self, ident: str) -> str:
        return f'"{ident}"'


_REGISTRY: dict[str, Dialect] = {}


def register(dialect: Dialect) -> None:
    _REGISTRY[dialect.name] = dialect


def get_dialect(name: str) -> Dialect:
    key = (name or "snowflake").lower()
    if key not in _REGISTRY:
        raise KeyError(f"Unknown dialect '{name}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[key]


def available() -> list[str]:
    return sorted(_REGISTRY)
