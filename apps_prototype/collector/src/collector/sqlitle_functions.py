import sqlite3



def create_historic_table(cursor: sqlite3.Cursor, connection: sqlite3.Connection) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historic_delays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            edad INTEGER NOT NULL
        )                              
    """)

    connection.commit()