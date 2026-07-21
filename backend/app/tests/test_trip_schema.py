"""Migration contract tests for durable Trip storage."""

from pathlib import Path


def test_trip_schema_contains_revision_contract():
    sql = (Path(__file__).parents[1] / "migrations" / "init.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS trips" in sql
    assert "current_revision INTEGER NOT NULL" in sql
    assert "snapshot JSONB NOT NULL" in sql
    assert "CREATE TABLE IF NOT EXISTS trip_revisions" in sql
    assert "UNIQUE (trip_id, revision)" in sql
