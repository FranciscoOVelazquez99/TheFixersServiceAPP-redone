import mysql.connector
from mysql.connector import Error

def crear_base_datos():
    try:
        # Establecer conexión
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
        )
        
        if conexion.is_connected():
            cursor = conexion.cursor()
            
            # Crear la base de datos
            cursor.execute("CREATE DATABASE IF NOT EXISTS fixers")
            print("Base de datos creada exitosamente")
            
            # Usar la base de datos
            cursor.execute("USE fixers")
            
            # Crear tablas
            tablas = {
                'usuarios': """
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        usuario VARCHAR(120) UNIQUE NOT NULL,
                        contraseña VARCHAR(100) NOT NULL,
                        rol VARCHAR(100) NOT NULL,
                        avatar VARCHAR(255),
                        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                'reparaciones': """
                    CREATE TABLE IF NOT EXISTS reparaciones (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        cliente VARCHAR(200) NOT NULL,
                        dni_cuil VARCHAR(11) NOT NULL,
                        telefono VARCHAR(15) NOT NULL,
                        email VARCHAR(120) NOT NULL,
                        descripcion TEXT,
                        fecha_ingreso DATETIME DEFAULT CURRENT_TIMESTAMP,
                        fecha_fin DATETIME,
                        estado VARCHAR(100) NOT NULL,
                        tecnico VARCHAR(120),
                        FOREIGN KEY (tecnico) REFERENCES usuarios(usuario)
                    )
                """,
                'equipos': """
                    CREATE TABLE IF NOT EXISTS equipos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        reparacion_id INT,
                        equipo VARCHAR(100) NOT NULL,
                        detalle TEXT,
                        img_equipo VARCHAR(200),
                        FOREIGN KEY (reparacion_id) REFERENCES reparaciones(id)
                    )
                """,
                'presupuestos': """
                    CREATE TABLE IF NOT EXISTS presupuestos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        reparacion_id INT,
                        tipo_reparacion VARCHAR(100) NOT NULL,
                        descripcion TEXT,
                        unidades INT NOT NULL,
                        precio_unitario DECIMAL(10, 2) NOT NULL,
                        total DECIMAL(10, 2) NOT NULL,
                        aprobado BOOLEAN DEFAULT FALSE,
                        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (reparacion_id) REFERENCES reparaciones(id)
                    )
                """,
                'tareas': """
                    CREATE TABLE IF NOT EXISTS tareas (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        titulo VARCHAR(100) NOT NULL,
                        descripcion TEXT,
                        estado VARCHAR(20) DEFAULT 'pendiente',
                        prioridad VARCHAR(20) DEFAULT 'media',
                        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        fecha_vencimiento DATETIME,

                        creado_por_id INT,
                        asignado_a_id INT,
                        FOREIGN KEY (creado_por_id) REFERENCES usuarios(id),
                        FOREIGN KEY (asignado_a_id) REFERENCES usuarios(id)
                    )
                """,
                'notificaciones': """
                    CREATE TABLE IF NOT EXISTS notificaciones (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        usuario_id INT,
                        tipo VARCHAR(50) NOT NULL,
                        mensaje TEXT NOT NULL,
                        leida BOOLEAN DEFAULT FALSE,
                        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        referencia_id INT,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                    )
                """,
                'documentos': """
                    CREATE TABLE IF NOT EXISTS documentos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        reparacion_id INT,
                        filename VARCHAR(255) NOT NULL,
                        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                        total DECIMAL(10, 2),
                        estado VARCHAR(50) DEFAULT 'generado',
                        FOREIGN KEY (reparacion_id) REFERENCES reparaciones(id)
                    )
                """ 
            }
            
            # Crear cada tabla
            for nombre_tabla, query in tablas.items():
                cursor.execute(query)
                print(f"Tabla {nombre_tabla} creada exitosamente")
            
            conexion.commit()
            
    except Error as e:
        print(f"Error: {e}")
    
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("Conexión cerrada")

if __name__ == "__main__":
    crear_base_datos()