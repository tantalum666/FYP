"""Additive local prototype migrations; existing runs and audit rows are retained."""

from sqlalchemy import inspect, text

from .models import Base


def prepare_database(engine):
    Base.metadata.create_all(engine)
    columns = {
        table: {c["name"] for c in inspect(engine).get_columns(table)}
        for table in ["events", "users", "workspaces", "runs", "menu_items"]
    }
    with engine.begin() as connection:
        if "sequence" not in columns["events"]:
            connection.execute(text("ALTER TABLE events ADD COLUMN sequence INTEGER"))
            connection.execute(
                text("""UPDATE events AS e SET sequence = ranked.n FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY at, ctid) AS n
                FROM events) AS ranked WHERE e.id = ranked.id""")
            )
            connection.execute(text("ALTER TABLE events ALTER COLUMN sequence SET NOT NULL"))
            connection.execute(
                text("CREATE UNIQUE INDEX ux_events_run_sequence ON events(run_id, sequence)")
            )
            connection.execute(
                text("""UPDATE runs r SET snapshot_version = GREATEST(r.snapshot_version, latest.n)
                FROM (SELECT run_id, MAX(sequence) AS n FROM events GROUP BY run_id) latest
                WHERE r.id = latest.run_id""")
            )
        additions = [
            ("runs", "service_version", "INTEGER NOT NULL DEFAULT 1"),
            ("menu_items", "quote_version", "INTEGER NOT NULL DEFAULT 1"),
            ("users", "activity_version", "INTEGER NOT NULL DEFAULT 0"),
            ("runs", "service_type", "VARCHAR(30) NOT NULL DEFAULT 'buffet_self_service'"),
            ("runs", "order_counter", "INTEGER NOT NULL DEFAULT 0"),
            ("workspaces", "menu_code", "VARCHAR(32)"),
        ]
        for table, column, definition in additions:
            if column not in columns[table]:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        if "menu_code" not in columns["workspaces"]:
            connection.execute(
                text(
                    "UPDATE workspaces SET menu_code = 'SP-' || UPPER(SUBSTR(REPLACE(id, '-', ''), 1, 10))"
                )
            )
            connection.execute(text("ALTER TABLE workspaces ALTER COLUMN menu_code SET NOT NULL"))
            connection.execute(
                text("CREATE UNIQUE INDEX ux_workspace_menu_code ON workspaces(menu_code)")
            )
