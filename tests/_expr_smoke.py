import sys
sys.path.insert(0, ".")
from ssis2dbt.convert.expression import translate
from ssis2dbt.dialects.base import get_dialect
d = get_dialect("snowflake")
cases = [
    ("(DT_DBTIMESTAMP)(@[System::StartTime])", "cast({{ var('StartTime') }} as timestamp)"),
    ("(DT_WSTR,50)[Col]",                       "cast(col as varchar(50))"),
    ("(DT_UI1)1",                               "cast(1 as tinyint)"),
    ("(DT_I1)1",                                "cast(1 as tinyint)"),
]
ok = True
for expr, expected in cases:
    r = translate(expr, d)
    status = "OK" if r.sql == expected else "FAIL"
    if status == "FAIL":
        ok = False
    print(f"[{status}] {expr!r}")
    print(f"       got: {r.sql!r}")
    if status == "FAIL":
        print(f"  expected: {expected!r}")
sys.exit(0 if ok else 1)
