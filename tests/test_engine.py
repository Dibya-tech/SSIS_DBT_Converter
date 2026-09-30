"""End-to-end and unit tests for the migration engine."""
from pathlib import Path

import pytest

from ssis2dbt.convert.expression import translate
from ssis2dbt.dialects.base import get_dialect
from ssis2dbt.engine import convert_file
from ssis2dbt.export.project import build_project_files
from ssis2dbt.ir.model import Grade, sanitize_identifier
from ssis2dbt.parser import dtsx
from ssis2dbt.parser.redact import redact_properties

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "LoadSales.dtsx"


def test_parse_sample():
    pkg = dtsx.parse_file(SAMPLE)
    assert pkg.name == "LoadSales"
    assert len(pkg.data_flows) == 1
    df = pkg.data_flows[0]
    assert len(df.components) == 4
    assert len(df.paths) == 3


def test_credentials_redacted_at_parser():
    pkg = dtsx.parse_file(SAMPLE)
    blob = str([cm.properties for cm in pkg.connections])
    assert "SuperSecret123" not in blob
    assert "REDACTED" in blob


def test_convert_produces_model_and_grades():
    run = convert_file(SAMPLE, dialect="snowflake")
    assert len(run.models) == 1
    model = run.models[0]
    assert "with" in model.sql
    assert "{{ source(" in model.sql
    assert "{{ ref(" in model.sql
    # SendMail control-flow task must be surfaced as critical/manual
    assert any(e.severity == "CRITICAL" for e in run.log)


def test_no_secret_in_any_generated_file():
    run = convert_file(SAMPLE)
    for content in build_project_files(run).values():
        if isinstance(content, bytes):
            continue  # binary files (PNGs) can't contain text secrets
        assert "SuperSecret123" not in content


@pytest.mark.parametrize("expr,expected_fragment", [
    ('[Col] == "X"', "col = 'x'"),
    ('[Col] != "X"', "col <> 'x'"),
    ('cond ? [a] : [b]', "case when cond then a else b end"),
    ('ISNULL([Col])', "col is null"),
    ('UPPER([Col])', "upper(col)"),
    ('(DT_WSTR,50)[Col]', "cast(col as varchar(50))"),
])
def test_expression_translation(expr, expected_fragment):
    res = translate(expr, get_dialect("snowflake"))
    assert expected_fragment in res.sql.lower()


def test_variable_maps_to_jinja_var():
    res = translate("@[User::LoadDate]", get_dialect("snowflake"))
    assert "{{ var('LoadDate') }}" in res.sql


def test_unmapped_function_flagged():
    res = translate("WEIRDFUNC([Col])", get_dialect("snowflake"))
    assert res.confident is False


def test_sanitize_identifier():
    assert sanitize_identifier("Derived Column 1!") == "derived_column_1"
    assert sanitize_identifier("123abc").startswith("_")


def test_redact_properties():
    out = redact_properties({"Password": "abc", "ConnectionString": "Server=x;Pwd=secret;"})
    assert out["Password"] == "***REDACTED***"
    assert "secret" not in out["ConnectionString"]


def test_dialect_differences():
    assert get_dialect("tsql").coalesce("a", "b") == "isnull(a, b)"
    assert get_dialect("snowflake").coalesce("a", "b") == "coalesce(a, b)"
    assert get_dialect("databricks").concat("a", "b") == "concat(a, b)"
