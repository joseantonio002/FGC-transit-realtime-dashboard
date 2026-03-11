import sqlite3

# Conectar a la base de datos (se crea si no existe)
conn = sqlite3.connect("datos.db")

# Crear cursor para ejecutar SQL
cursor = conn.cursor()

# Crear tabla
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    edad INTEGER NOT NULL
)
""")

# Insertar datos
cursor.execute(
    "INSERT INTO usuarios (nombre, edad) VALUES (?, ?)",
    ("Ana", 28)
)

cursor.execute(
    "INSERT INTO usuarios (nombre, edad) VALUES (?, ?)",
    ("Luis", 34)
)

# Guardar cambios
conn.commit()

# Leer datos
cursor.execute("SELECT id, nombre, edad FROM usuarios")
filas = cursor.fetchall()

for fila in filas:
    print(fila)

# Cerrar conexión
conn.close()