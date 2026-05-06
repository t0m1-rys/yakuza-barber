# =============================
# YAKUZA BARBER PRO - SISTEMA REAL PARA PYMES (WEB FUNCIONAL)
# =============================
# FIX ERROR 500:
# - Ruta absoluta para templates
# - Manejo de errores en rutas
# =============================

from flask import Flask, render_template, request, redirect
import sqlite3
import os

# Ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# -----------------------------
# BASE DE DATOS
# -----------------------------

def init_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'barberia.db'))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barberos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            hora TEXT,
            barbero_id INTEGER
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM barberos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO barberos (nombre) VALUES ('Vale')")
        cursor.execute("INSERT INTO barberos (nombre) VALUES ('Bruno')")
        cursor.execute("INSERT INTO barberos (nombre) VALUES ('Angel')")
        cursor.execute("INSERT INTO barberos (nombre) VALUES ('Vicente')")

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# ASEGURAR TEMPLATE
# -----------------------------

if not os.path.exists(TEMPLATE_DIR):
    os.makedirs(TEMPLATE_DIR)

html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Yakuza Barber</title>
</head>
<body style="background:black;color:white;text-align:center;font-family:Arial;">

<h1 style="color:red;">YAKUZA BARBER</h1>

<form method="POST" action="/agendar">
    <input name="cliente" placeholder="Cliente" required>
    <input type="time" name="hora" required>

    <select name="barbero">
    {% for b in barberos %}
        <option value="{{ b[0] }}">{{ b[1] }}</option>
    {% endfor %}
    </select>

    <button>Agendar</button>
</form>

<h2>Citas</h2>
<table border="1" style="margin:auto;">
<tr><th>ID</th><th>Cliente</th><th>Hora</th><th>Barbero</th><th></th></tr>

{% for c in citas %}
<tr>
<td>{{ c[0] }}</td>
<td>{{ c[1] }}</td>
<td>{{ c[2] }}</td>
<td>{{ c[3] }}</td>
<td><a href="/eliminar/{{ c[0] }}">Eliminar</a></td>
</tr>
{% endfor %}

</table>

</body>
</html>
"""

with open(os.path.join(TEMPLATE_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(html_content)

# -----------------------------
# ROUTES
# -----------------------------

@app.route('/')
def index():
    try:
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'barberia.db'))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM barberos")
        barberos = cursor.fetchall()

        cursor.execute('''
            SELECT citas.id, citas.cliente, citas.hora, barberos.nombre
            FROM citas
            JOIN barberos ON citas.barbero_id = barberos.id
        ''')
        citas = cursor.fetchall()

        conn.close()

        return render_template("index.html", citas=citas, barberos=barberos)

    except Exception as e:
        return f"Error interno: {e}"

@app.route('/agendar', methods=['POST'])
def agendar():
    try:
        cliente = request.form['cliente']
        hora = request.form['hora']
        barbero_id = request.form['barbero']

        conn = sqlite3.connect(os.path.join(BASE_DIR, 'barberia.db'))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM citas WHERE hora=? AND barbero_id=?", (hora, barbero_id))

        if not cursor.fetchone():
            cursor.execute("INSERT INTO citas (cliente, hora, barbero_id) VALUES (?, ?, ?)",
                           (cliente, hora, barbero_id))
            conn.commit()

        conn.close()
        return redirect('/')

    except Exception as e:
        return f"Error al agendar: {e}"

@app.route('/eliminar/<int:id>')
def eliminar(id):
    try:
        conn = sqlite3.connect(os.path.join(BASE_DIR, 'barberia.db'))
        cursor = conn.cursor()

        cursor.execute("DELETE FROM citas WHERE id=?", (id,))
        conn.commit()
        conn.close()

        return redirect('/')

    except Exception as e:
        return f"Error al eliminar: {e}"

# -----------------------------
# TEST
# -----------------------------

def test_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'barberia.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()

    assert 'barberos' in tables
    assert 'citas' in tables

# -----------------------------
# RUN
# -----------------------------

if __name__ == '__main__':
    test_db()

    print("SERVIDOR INICIADO")
    print("http://127.0.0.1:5000")

    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=False)
