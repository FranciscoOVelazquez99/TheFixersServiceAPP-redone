from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

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
    
        # Configurar ruta estática para uploads
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    
    # Si la app está congelada (instalada), ajustar la ruta estática
    if getattr(sys, 'frozen', False):
        app.static_folder = os.path.join(os.path.dirname(sys.executable), 'static')
    

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