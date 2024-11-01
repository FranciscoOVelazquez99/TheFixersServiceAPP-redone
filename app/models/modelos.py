from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, DECIMAL, Boolean
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, UTC
from app import db
from flask_bcrypt import Bcrypt
from flask_login import UserMixin

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario = Column(String(120), unique=True, nullable=False)
    contraseña = Column(String(100), nullable=False)
    rol = Column(String(100), nullable=False)
    avatar = db.Column(db.String(255), default='img/profile.jpg')
    fecha_registro = Column(DateTime, default=datetime.now(UTC))
    
    # Relación con reparaciones
    reparaciones = relationship('Reparacion', back_populates='tecnico_rel')
    
    def __repr__(self):
        return f"<Usuario(usuario='{self.usuario}', rol='{self.rol}')>"

class Reparacion(db.Model):
    __tablename__ = 'reparaciones'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente = Column(String(200), nullable=False)
    dni_cuil = Column(String(11), nullable=False)
    telefono = Column(String(15), nullable=False)
    email = Column(String(120), nullable=False)
    descripcion = Column(Text)
    fecha_ingreso = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime)
    estado = Column(String(100), nullable=False)
    tecnico = Column(String(120), ForeignKey('usuarios.usuario'))
    
    # Relaciones
    tecnico_rel = relationship('Usuario', back_populates='reparaciones')
    equipos = relationship('Equipo', back_populates='reparacion')
    presupuestos = relationship('Presupuesto', back_populates='reparacion')
    
    def __repr__(self):
        return f"<Reparacion(cliente='{self.cliente}', estado='{self.estado}')>"

class Equipo(db.Model):
    __tablename__ = 'equipos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reparacion_id = Column(Integer, ForeignKey('reparaciones.id'))
    equipo = Column(String(100), nullable=False)
    detalle = Column(Text)
    img_equipo = Column(String(200))
    
    # Relación
    reparacion = relationship('Reparacion', back_populates='equipos')
    
    def __repr__(self):
        return f"<Equipo(equipo='{self.equipo}')>"

class Presupuesto(db.Model):
    __tablename__ = 'presupuestos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reparacion_id = Column(Integer, ForeignKey('reparaciones.id'))
    tipo_reparacion = Column(String(100), nullable=False)
    descripcion = Column(Text)
    unidades = Column(Integer, nullable=False)
    precio_unitario = Column(DECIMAL(10, 2), nullable=False)
    total = Column(DECIMAL(10, 2), nullable=False)
    aprobado = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # Relación
    reparacion = relationship('Reparacion', back_populates='presupuestos')
    
    def __repr__(self):
        return f"<Presupuesto(tipo_reparacion='{self.tipo_reparacion}', total={self.total})>"

# Crear una sesión
Session = sessionmaker(bind=db.engine)
session = Session()
bcrypt = Bcrypt()
# Función para probar la conexión
def crear_admin():
    try:
        # Crear un usuario de prueba
        nuevo_usuario = Usuario(
            usuario="admin",
            contraseña=bcrypt.generate_password_hash("admin").decode('utf-8'),  # Usar la instancia bcrypt
            rol="admin",
            fecha_registro=datetime.now(UTC)
        )
        session.add(nuevo_usuario)
        session.commit()
        print("Usuario admin creado exitosamente")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

