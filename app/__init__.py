from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os, sys

# Inicializar SQLAlchemy
db = SQLAlchemy()
login_manager = LoginManager()
def create_app():
    app = Flask(__name__)
    from app.config import Config
    app.config.from_object(Config)
    
    # Inicializar la base de datos
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
 # Configurar ruta estática basada en si la app está congelada o no
    if getattr(sys, 'frozen', False):
        # Si está instalada, usar la ruta del ejecutable
        base_dir = os.path.dirname(sys.executable)
        app.static_folder = os.path.join(base_dir,'app', 'static')
        app.template_folder = os.path.join(base_dir, 'app', 'templates')
    else:
        # En desarrollo, usar rutas relativas
        app.static_folder = 'static'
        app.template_folder = 'templates'
    
    # Verificar y crear la base de datos si es necesario
    with app.app_context():
        from app.database import verificar_base_datos
        from app.models.modelos import Usuario, crear_admin
        
        mensaje = verificar_base_datos()
        print(mensaje)
        
        # Crear las tablas
        db.create_all()
        
        # Verificar si existe el usuario admin
        admin = Usuario.query.filter_by(usuario="admin").first()
        if not admin:
            crear_admin()
    
    # Registrar los blueprints
    from app.main import main_bp
    app.register_blueprint(main_bp)
    
    return app

# Mover el user_loader aquí
@login_manager.user_loader
def load_user(user_id):
    from app.models.modelos import Usuario
    return Usuario.query.get(int(user_id))