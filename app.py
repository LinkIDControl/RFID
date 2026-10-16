from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    
    # Tabla para guardar a los usuarios y su tarjeta asignada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            uid_tarjeta TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Tabla para guardar cada vez que se pase la tarjeta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marcaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha_hora TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

init_db()


# --- RUTAS DE LA PÁGINA WEB ---

@app.route('/')
def inicio():
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    
    # Obtener lista de usuarios
    cursor.execute('SELECT * FROM usuarios')
    usuarios = cursor.fetchall()
    
    # Obtener historial de lecturas uniendo el nombre del usuario
    cursor.execute('''
        SELECT marcaciones.id, usuarios.nombre, usuarios.uid_tarjeta, marcaciones.fecha_hora 
        FROM marcaciones 
        JOIN usuarios ON marcaciones.usuario_id = usuarios.id 
        ORDER BY marcaciones.id DESC
    ''')
    marcaciones = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', usuarios=usuarios, marcaciones=marcaciones)


@app.route('/agregar_usuario', methods=['POST'])
def agregar_usuario():
    nombre = request.form['nombre'].strip()
    uid = request.form['uid_tarjeta'].strip()

    if nombre and uid:
        try:
            conn = sqlite3.connect('asistencia.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (nombre, uid_tarjeta) VALUES (?, ?)', (nombre, uid))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            print("Error: El UID de la tarjeta ya está registrado.")
            
    return redirect(url_for('inicio'))


@app.route('/eliminar_usuario/<int:id>', methods=['POST'])
def eliminar_usuario(id):
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    
    # Primero eliminamos sus marcaciones asociadas
    cursor.execute('DELETE FROM marcaciones WHERE usuario_id = ?', (id,))
    # Luego eliminamos al usuario
    cursor.execute('DELETE FROM usuarios WHERE id = ?', (id,))
    
    conn.commit()
    conn.close()
    return redirect(url_for('inicio'))


@app.route('/registrar_lectura', methods=['POST'])
def registrar_lectura():
    uid = request.form['uid_tarjeta'].strip()
    
    if uid:
        conn = sqlite3.connect('asistencia.db')
        cursor = conn.cursor()
        
        # Buscar el usuario correspondiente a la tarjeta
        cursor.execute('SELECT id, nombre FROM usuarios WHERE uid_tarjeta = ?', (uid,))
        usuario = cursor.fetchone()
        
        if usuario:
            usuario_id = usuario[0]
            nombre_usuario = usuario[1]
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar la lectura en el historial
            cursor.execute('INSERT INTO marcaciones (usuario_id, fecha_hora) VALUES (?, ?)', (usuario_id, fecha_actual))
            conn.commit()
            print(f"Marcación registrada: {nombre_usuario} ({fecha_actual})")
        else:
            print(f"Tarjeta no registrada: {uid}")
            
        conn.close()
        
    return redirect(url_for('inicio'))


if __name__ == '__main__':
    app.run(debug=True)
#pip install flask