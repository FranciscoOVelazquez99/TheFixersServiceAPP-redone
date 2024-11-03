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
    
    def tiene_notificaciones_sin_leer(self):
        return any(not notif.leida for notif in self.notificaciones)

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

class Tarea(db.Model):
    __tablename__ = 'tareas'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='pendiente')
    prioridad = db.Column(db.String(20), default='media')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    
    asignado_a_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    creado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    asignado_a = db.relationship('Usuario', foreign_keys=[asignado_a_id])
    creado_por = db.relationship('Usuario', foreign_keys=[creado_por_id])

    def __init__(self, **kwargs):
        super(Tarea, self).__init__(**kwargs)
        if not self.estado:
            self.estado = 'pendiente'


class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo = db.Column(db.String(50), nullable=False)  # 'reparacion', 'tarea', etc.
    mensaje = db.Column(db.Text, nullable=False)
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    referencia_id = db.Column(db.Integer)  # ID de la reparación o tarea relacionada
    
    # Relación con el usuario
    usuario = db.relationship('Usuario', backref=db.backref('notificaciones', lazy=True))

class Documento(db.Model):
    __tablename__ = 'documentos'
    
    id = Column(Integer, primary_key=True)
    reparacion_id = Column(Integer, ForeignKey('reparaciones.id'))
    filename = Column(String(255), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    total = Column(DECIMAL(10, 2))
    estado = Column(String(50), default='generado')  # generado, firmado, cancelado
    
    # Relaciones
    reparacion = relationship('Reparacion', backref='documentos')
    
    @property
    def estado_color(self):
        colores = {
            'generado': 'warning',
            'firmado': 'success',
            'cancelado': 'danger'
        }
        return colores.get(self.estado.lower(), 'secondary')
    
    @property
    def pdf_url(self):
        return f'/static/pdfs/{self.filename}'



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
            rol="ADMIN",
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

