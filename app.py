from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURACIÓN E INICIALIZACIÓN DE LA BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    
    # Tabla de usuarios (estudiantes y maestros)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            curso_materia TEXT NOT NULL,
            uid_tarjeta TEXT UNIQUE NOT NULL,
            foto TEXT
        )
    ''')
    
    # Tabla de marcaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marcaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha_hora TEXT NOT NULL,
            estado TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- RUTAS PRINCIPALES Y API ---

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/api/usuarios', methods=['GET'])
def obtener_usuarios():
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, tipo, nombre, curso_materia, uid_tarjeta, foto FROM usuarios')
    filas = cursor.fetchall()
    
    # Consultar las marcaciones de hoy
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        SELECT usuario_id, strftime('%H:%M', fecha_hora) as hora, estado 
        FROM marcaciones 
        WHERE fecha_hora LIKE ?
    ''', (f"{fecha_hoy}%",))
    marcaciones_hoy = {row[0]: {'hora': row[1], 'estado': row[2]} for row in cursor.fetchall()}
    
    conn.close()
    
    usuarios = []
    for f in filas:
        u_id = f[0]
        m = marcaciones_hoy.get(u_id, {'hora': '', 'estado': 'n'})
        usuarios.append({
            'id': u_id,
            'tipo': f[1],
            'n': f[2],
            'c': f[3],
            'k': f[4],
            'f': f[5] or '',
            's': m['estado'],
            'h': m['hora']
        })
        
    return jsonify(usuarios)

@app.route('/api/marcaciones', methods=['GET'])
def obtener_marcaciones():
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        SELECT marcaciones.usuario_id 
        FROM marcaciones 
        WHERE fecha_hora LIKE ? 
        ORDER BY marcaciones.id DESC
    ''', (f"{fecha_hoy}%",))
    log = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(log)

@app.route('/api/registrar_lectura', methods=['POST'])
def registrar_lectura():
    data = request.get_json()
    uid = data.get('uid', '').strip()
    
    if not uid:
        return jsonify({'status': 'error', 'msg': 'código de tarjeta vacío'}), 400
        
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, tipo, nombre, curso_materia, foto FROM usuarios WHERE uid_tarjeta = ?', (uid,))
    usuario = cursor.fetchone()
    
    if not usuario:
        conn.close()
        return jsonify({'status': 'no_registrado', 'uid': uid})
        
    u_id, tipo, nombre, curso, foto = usuario
    
    # Comprobar si ya marcó hoy
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('SELECT hora FROM (SELECT strftime("%Y-%m-%d", fecha_hora) as f, strftime("%H:%M", fecha_hora) as hora FROM marcaciones WHERE usuario_id = ?) WHERE f = ?', (u_id, fecha_hoy))
    marcacion_existente = cursor.fetchone()
    
    ahora_dt = datetime.now()
    hora_str = ahora_dt.strftime("%H:%M")
    fecha_hora_str = ahora_dt.strftime("%Y-%m-%d %H:%M:%S")
    limite = "07:15"
    
    if not marcacion_existente:
        estado = "t" if hora_str > limite else "p"
        cursor.execute('INSERT INTO marcaciones (usuario_id, fecha_hora, estado) VALUES (?, ?, ?)', (u_id, fecha_hora_str, estado))
        conn.commit()
    else:
        # Recuperar estado previo
        cursor.execute('SELECT estado FROM marcaciones WHERE usuario_id = ? AND fecha_hora LIKE ?', (u_id, f"{fecha_hoy}%"))
        estado = cursor.fetchone()[0]
        
    conn.close()
    
    return jsonify({
        'status': 'ok',
        'usuario': {
            'id': u_id,
            'tipo': tipo,
            'n': nombre,
            'c': curso,
            'k': uid,
            'f': foto or '',
            's': estado,
            'h': hora_str
        }
    })

@app.route('/api/agregar_usuario', methods=['POST'])
def agregar_usuario():
    data = request.get_json()
    tipo = data.get('tipo')
    nombre = data.get('nombre', '').strip()
    curso = data.get('curso', '').strip()
    tarjeta = data.get('tarjeta', '').strip()
    foto = data.get('foto', '')
    
    if not nombre or not curso or not tarjeta:
        return jsonify({'status': 'error', 'msg': 'campos incompletos'}), 400
        
    try:
        conn = sqlite3.connect('asistencia.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO usuarios (tipo, nombre, curso_materia, uid_tarjeta, foto) VALUES (?, ?, ?, ?, ?)',
                       (tipo, nombre, curso, tarjeta, foto))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'msg': 'esa tarjeta ya está asignada a otra persona'}), 400

@app.route('/api/eliminar_usuario/<int:user_id>', methods=['DELETE'])
def eliminar_usuario(user_id):
    conn = sqlite3.connect('asistencia.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM marcaciones WHERE usuario_id = ?', (user_id,))
    cursor.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True)
#pip install flask