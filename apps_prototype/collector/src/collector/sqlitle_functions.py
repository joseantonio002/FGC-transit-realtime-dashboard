import sqlite3


HISTORIC_DELAY_COLUMNS: tuple[str, ...] = (
  "trip_id",
  "route_id",
  "stop_id",
  "stop_sequence",
  "arrival_planned",
  "arrival_real",
  "arrival_delay_total_seconds",
  "arrival_delay_formatted",
  "execution_timestamp",
)



def create_historic_table(cursor: sqlite3.Cursor, connection: sqlite3.Connection) -> None:
  """Create historic_delays table if it does not exist."""
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS historic_delays (
      trip_id TEXT NOT NULL,
      route_id TEXT NOT NULL,
      stop_id TEXT NOT NULL,
      stop_sequence INTEGER NOT NULL,
      arrival_planned INTEGER NOT NULL,
      arrival_real INTEGER NOT NULL,
      arrival_delay_total_seconds INTEGER NOT NULL,
      arrival_delay_formatted TEXT NOT NULL,
      execution_timestamp INTEGER NOT NULL
    )
  """)

  connection.commit()


def insert_historic_delay_row(
  cursor: sqlite3.Cursor,
  connection: sqlite3.Connection,
  row: dict[str, str | int],
) -> None:
  """Insert one historic delay row after validating required fields."""
  missing_fields: list[str] = [column for column in HISTORIC_DELAY_COLUMNS if column not in row]
  if missing_fields:
    raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

  cursor.execute(
    """
    INSERT INTO historic_delays (
      trip_id,
      route_id,
      stop_id,
      stop_sequence,
      arrival_planned,
      arrival_real,
      arrival_delay_total_seconds,
      arrival_delay_formatted,
      execution_timestamp
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
      row["trip_id"],
      row["route_id"],
      row["stop_id"],
      row["stop_sequence"],
      row["arrival_planned"],
      row["arrival_real"],
      row["arrival_delay_total_seconds"],
      row["arrival_delay_formatted"],
      row["execution_timestamp"],
    ),
  )

  connection.commit()
