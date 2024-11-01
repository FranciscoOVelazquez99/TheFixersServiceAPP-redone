import mysql.connector
from mysql.connector import Error
from app.models.crear_db import crear_base_datos

def verificar_base_datos():
    try:
        # Intentar conectar al servidor MySQL
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password=""
        )
        
        if conexion.is_connected():
            cursor = conexion.cursor()
            
            # Verificar si existe la base de datos
            cursor.execute("SHOW DATABASES LIKE 'fixers'")
            resultado = cursor.fetchone()
            
            if not resultado:
                # Si no existe, crear la base de datos y las tablas
                crear_base_datos()
                return "Base de datos y tablas creadas exitosamente"
            return "Base de datos ya existe"
            
    except Error as e:
        return f"Error: {e}"
    
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()