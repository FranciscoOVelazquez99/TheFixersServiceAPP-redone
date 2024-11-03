from flask import Blueprint, jsonify, send_from_directory,render_template, url_for, redirect, flash,request

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField , SubmitField

from wtforms.validators import DataRequired

from flask_login import login_required, logout_user, LoginManager, current_user, login_user

from app.models.modelos import Usuario, Reparacion, Equipo, Presupuesto, Tarea, Notificacion, Documento, db
from flask_bcrypt import Bcrypt

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from werkzeug.utils import secure_filename

from datetime import datetime, timedelta

PDF_PATH = 'static/PDFs'
UPLOAD_FOLDER_AVATARS = 'app/static/uploads/avatars'
UPLOAD_FOLDER_EQUIPOS = 'app/static/uploads/equipos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'jfif'}


main_bp = Blueprint('main', __name__,
                   template_folder='./templates', 
                   static_folder='./static')

bcrypt = Bcrypt() 

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar sesión')

class RegisterForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    rol = SelectField('Rol', choices=[('ADMIN', 'Administrador'), ('ADMINISTRACION', 'Administración'), ('SUPERVISOR', 'Supervisor'), ('OPERADOR', 'Operador')])
    submit = SubmitField('Registrar')

def validate_username(username):
    existing_user_username = Usuario.query.filter_by(
        usuario=username.data).first()
    if existing_user_username:
        return True

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def crear_notificacion(usuario_id, tipo, mensaje, referencia_id=None):
    try:
        notificacion = Notificacion(
            usuario_id=usuario_id,
            tipo=tipo,
            mensaje=mensaje,
            referencia_id=referencia_id
        )
        db.session.add(notificacion)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error al crear notificación: {e}")
        db.session.rollback()
        return False


@main_bp.route('/')
def index():
    return redirect(url_for('main.login'))


@main_bp.route('/login', methods=['GET', 'POST']) 
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(usuario=form.username.data).first()
        if user and bcrypt.check_password_hash(user.contraseña, form.password.data):
            login_user(user)
            flash('Bienvenido', 'success')
            return jsonify({
                'success': True, 
                'redirect': url_for('main.home')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Usuario o contraseña incorrectos'
            })
    return render_template('login.html', form=form) if request.method == 'GET' else jsonify({
        'success': False,
        'message': 'Datos de formulario inválidos'
    })

@main_bp.route('/home')
@login_required
def home():
    # Obtener estadísticas de reparaciones
    reparaciones_pendientes = Reparacion.query.filter_by(estado='Pendiente').count()
    reparaciones_proceso = Reparacion.query.filter_by(estado='En proceso').count()
    
    # Obtener estadísticas de tareas del usuario actual
    tareas_pendientes = Tarea.query.filter_by(
        asignado_a_id=current_user.id,
        estado='pendiente'
    ).count()
    
    # Tareas vencidas
    tareas_vencidas = Tarea.query.filter(
        Tarea.asignado_a_id == current_user.id,
        Tarea.fecha_vencimiento < datetime.now(),
        Tarea.estado != 'completada'
    ).count()
    
    # Estadísticas de presupuestos
    fecha_inicio = datetime.now() - timedelta(days=30)
    presupuestos = Presupuesto.query.filter(
        Presupuesto.fecha_creacion >= fecha_inicio
    ).all()
    presupuestos_total = len(presupuestos)
    facturacion_mes = sum(p.total for p in presupuestos if p.aprobado)
    
    # Estadísticas de usuarios
    usuarios_total = Usuario.query.count()
    tecnicos_activos = Usuario.query.filter(
        Usuario.rol.in_(['SUPERVISOR', 'OPERADOR'])
    ).count()
    
    return render_template('home.html',
        reparaciones_pendientes=reparaciones_pendientes,
        reparaciones_proceso=reparaciones_proceso,
        tareas_pendientes=tareas_pendientes,
        tareas_vencidas=tareas_vencidas,
        presupuestos_total=presupuestos_total,
        facturacion_mes="{:,.2f}".format(facturacion_mes),
        usuarios_total=usuarios_total,
        tecnicos_activos=tecnicos_activos
    )

@main_bp.route('/api/estadisticas/reparaciones')
@login_required
def get_estadisticas_reparaciones():
    try:
        estados = ['Pendiente', 'En proceso', 'Completada', 'Cancelada']
        datos = []
        for estado in estados:
            count = Reparacion.query.filter_by(estado=estado).count()
            datos.append(count)
            
        return jsonify({
            'labels': estados,
            'datos': datos
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/estadisticas/facturacion')
@login_required
def get_estadisticas_facturacion():
    try:
        # Obtener los últimos 6 meses
        hoy = datetime.now()
        meses = []
        datos = []
        
        for i in range(5, -1, -1):
            fecha_inicio = (hoy - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0)
            if i > 0:
                fecha_fin = (hoy - timedelta(days=30*(i-1))).replace(day=1, hour=0, minute=0, second=0)
            else:
                fecha_fin = hoy
                
            # Obtener facturación del mes
            facturacion = db.session.query(
                db.func.sum(Presupuesto.total)
            ).filter(
                Presupuesto.fecha_creacion >= fecha_inicio,
                Presupuesto.fecha_creacion < fecha_fin,
                Presupuesto.aprobado == True
            ).scalar() or 0
            
            meses.append(fecha_inicio.strftime('%B %Y'))
            datos.append(float(facturacion))
            
        return jsonify({
            'labels': meses,
            'datos': datos
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/static/')
def serve_static(path):
    return send_from_directory(
        main_bp.static_folder,path, as_attachment=True
  )

@main_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            if validate_username(form.username):
                flash('El nombre de usuario ya existe', 'danger')
                return render_template('nuevo_usuario.html', form=form)
            
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            
            avatar_path = 'img/profile.jpg'  # Default avatar
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    if not os.path.exists(UPLOAD_FOLDER_AVATARS):
                        os.makedirs(UPLOAD_FOLDER_AVATARS)
                    file.save(os.path.join(UPLOAD_FOLDER_AVATARS, filename))
                    avatar_path = f'uploads/avatars/{filename}'
            
            new_user = Usuario(
                usuario=form.username.data,
                contraseña=hashed_password,
                rol=form.rol.data,
                avatar=avatar_path
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('main.register'))
            
    return render_template('usuarios/nuevo_usuario.html', form=form)


@main_bp.route('/listar_usuarios')
@login_required
def listar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios/listar_usuarios.html', usuarios=usuarios)

@main_bp.route('/editar_usuario/<int:id>', methods=['POST'])
@login_required
def editar_usuario(id):
    if not current_user.rol == 'ADMIN':
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('main.listar_usuarios'))
        
    usuario = Usuario.query.get_or_404(id)
    
    if 'username' in request.form:
        usuario.usuario = request.form['username']
    
    if request.form.get('password'):
        usuario.contraseña = bcrypt.generate_password_hash(
            request.form['password']
        ).decode('utf-8')
    
    if 'rol' in request.form:
        usuario.rol = request.form['rol']
    
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and allowed_file(file.filename):
            # Borrar avatar anterior si no es el default
            if usuario.avatar and 'img/profile.jpg' not in usuario.avatar:
                avatar_path = os.path.join('app/static', usuario.avatar)
                if os.path.exists(avatar_path):
                    os.remove(avatar_path)
                    
            filename = secure_filename(file.filename)
            if not os.path.exists(UPLOAD_FOLDER_AVATARS):
                os.makedirs(UPLOAD_FOLDER_AVATARS)
            file.save(os.path.join(UPLOAD_FOLDER_AVATARS, filename))
            usuario.avatar = f'uploads/avatars/{filename}'
    
    db.session.commit()
    flash('Usuario actualizado exitosamente', 'success')
    return redirect(url_for('main.listar_usuarios'))

@main_bp.route('/eliminar_usuario/<int:id>', methods=['DELETE'])
@login_required
def eliminar_usuario(id):
    if not current_user.rol == 'ADMIN':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        return jsonify({'success': False, 'message': 'No puedes eliminarte a ti mismo'}), 400
        
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({'success': True})




@main_bp.route('/reparaciones')
@login_required
def reparaciones():
    reparaciones = Reparacion.query.all()
    tecnicos = Usuario.query.filter(Usuario.rol.in_(['ADMIN', 'SUPERVISOR', 'OPERADOR'])).all()
    return render_template('reparaciones/reparaciones.html', 
                         reparaciones=reparaciones, 
                         tecnicos=tecnicos)

@main_bp.route('/nueva_reparacion', methods=['POST'])
@login_required
def nueva_reparacion():
    try:
        nueva_reparacion = Reparacion(
            cliente=request.form['cliente'],
            dni_cuil=request.form['dni_cuil'],
            telefono=request.form['telefono'],
            email=request.form['email'],
            descripcion=request.form['descripcion'],
            tecnico=request.form['tecnico'] if request.form['tecnico'] else None,
            estado='Pendiente'
        )

        # Crear notificación para el técnico asignado
        if nueva_reparacion.tecnico:
            usuario = Usuario.query.filter_by(usuario=nueva_reparacion.tecnico).first()
            if usuario:
                crear_notificacion(
                    usuario_id=usuario.id,
                    tipo='reparacion',
                    mensaje=f'Se te ha asignado una nueva reparación: {nueva_reparacion.descripcion}',
                    referencia_id=nueva_reparacion.id
                )

        db.session.add(nueva_reparacion)
        db.session.commit()
        flash('Reparación creada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al crear la reparación: {str(e)}', 'danger')
    return redirect(url_for('main.reparaciones'))

@main_bp.route('/editar_reparacion/<int:id>', methods=['POST', 'GET'])
@login_required
def editar_reparacion(id):
    try:
        reparacion = Reparacion.query.get_or_404(id)
        reparacion.cliente = request.form['cliente']
        reparacion.dni_cuil = request.form['dni_cuil']
        reparacion.telefono = request.form['telefono']
        reparacion.email = request.form['email']
        reparacion.descripcion = request.form['descripcion']
        reparacion.tecnico = request.form['tecnico'] if request.form['tecnico'] else None
        reparacion.estado = request.form['estado']
        
        # Crear notificación para el técnico asignado
        print(reparacion.id)
        if reparacion.tecnico:
            usuario = Usuario.query.filter_by(usuario=reparacion.tecnico).first()
            if usuario:
                crear_notificacion(
                    usuario_id=usuario.id,
                    tipo='reparacion',
                    mensaje=f'Se te ha asignado una nueva reparación: {reparacion.descripcion}',
                    referencia_id=reparacion.id
                )
        
        db.session.commit()
        flash('Reparación actualizada exitosamente', 'success')
    except Exception as e:
        flash(f'Error al actualizar la reparación: {str(e)}', 'danger')
    return redirect(url_for('main.reparaciones'))

@main_bp.route('/eliminar_reparacion/<int:id>', methods=['DELETE'])
@login_required
def eliminar_reparacion(id):
    try:
        reparacion = Reparacion.query.get_or_404(id)
        
        # Eliminar equipos asociados
        for equipo in reparacion.equipos:
            # Eliminar imagen del equipo si existe
            if equipo.img_equipo and equipo.img_equipo != 'img/noimage.jfif':
                try:
                    os.remove(os.path.join('app/static', equipo.img_equipo))
                except:
                    pass
            db.session.delete(equipo)
            
        # Eliminar presupuestos asociados
        for presupuesto in reparacion.presupuestos:
            db.session.delete(presupuesto)
            
        # Eliminar la reparación
        db.session.delete(reparacion)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/reclamar_reparacion/<int:id>', methods=['POST'])
@login_required
def reclamar_reparacion(id):
    try:
        reparacion = Reparacion.query.get_or_404(id)
        
        # Si ya está reclamada por otro usuario
        if reparacion.reclamado_por_id and reparacion.reclamado_por_id != current_user.id:
            return jsonify({
                'success': False, 
                'message': f'Esta reparación ya está siendo trabajada por {reparacion.reclamado_por.usuario}'
            }), 400
            
        # Si el usuario actual la reclama, la libera
        if reparacion.reclamado_por_id == current_user.id:
            reparacion.reclamado_por_id = None
            reparacion.fecha_reclamado = None
            mensaje = 'Reparación liberada'
        else:
            # Reclamar la reparación
            reparacion.reclamado_por_id = current_user.id
            reparacion.fecha_reclamado = datetime.now()
            mensaje = 'Reparación reclamada exitosamente'
            
            # Crear notificación para otros técnicos
            tecnicos = Usuario.query.filter(
                Usuario.rol.in_(['ADMIN', 'SUPERVISOR', 'OPERADOR']),
                Usuario.id != current_user.id
            ).all()
            
            for tecnico in tecnicos:
                crear_notificacion(
                    usuario_id=tecnico.id,
                    tipo='reparacion',
                    mensaje=f'{current_user.usuario} está trabajando en la reparación de {reparacion.cliente}',
                    referencia_id=reparacion.id
                )
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': mensaje,
            'reclamado_por': current_user.usuario if reparacion.reclamado_por_id else None,
            'fecha_reclamado': reparacion.fecha_reclamado.strftime('%Y-%m-%d %H:%M') if reparacion.fecha_reclamado else None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# Rutas para Equipos
@main_bp.route('/agregar_equipo', methods=['POST'])
@login_required
def agregar_equipo():
    try:
        reparacion_id = request.form['reparacion_id']
        
        imagen_path = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                if not os.path.exists(UPLOAD_FOLDER_EQUIPOS):
                    os.makedirs(UPLOAD_FOLDER_EQUIPOS)
                file.save(os.path.join(UPLOAD_FOLDER_EQUIPOS, filename))
                imagen_path = f'uploads/equipos/{filename}'
            else:
                imagen_path = 'img/noimage.jfif'

        
        nuevo_equipo = Equipo(
            reparacion_id=reparacion_id,
            equipo=request.form['equipo'],
            detalle=request.form['detalle'],
            img_equipo=imagen_path
        )
        db.session.add(nuevo_equipo)
        db.session.commit()
        flash('Equipo agregado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al agregar el equipo: {str(e)}', 'danger')
    return redirect(url_for('main.reparaciones'))

@main_bp.route('/editar_equipo/<int:id>', methods=['POST'])
@login_required
def editar_equipo(id):
    try:
        equipo = Equipo.query.get_or_404(id)
        equipo.equipo = request.form['equipo']
        equipo.detalle = request.form['detalle']
        
        # Manejar nueva imagen si se proporciona
        if 'imagen' in request.files and request.files['imagen'].filename:
            file = request.files['imagen']
            if allowed_file(file.filename):
                # Eliminar imagen anterior si existe
                if equipo.img_equipo and equipo.img_equipo != 'img/noimage.jfif':
                    try:
                        os.remove(os.path.join('app/static', equipo.img_equipo))
                    except:
                        pass
                
                filename = secure_filename(file.filename)
                if not os.path.exists(UPLOAD_FOLDER_EQUIPOS):
                    os.makedirs(UPLOAD_FOLDER_EQUIPOS)
                file.save(os.path.join(UPLOAD_FOLDER_EQUIPOS, filename))
                equipo.img_equipo = f'uploads/equipos/{filename}'
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@main_bp.route('/eliminar_equipo/<int:id>', methods=['DELETE'])
@login_required
def eliminar_equipo(id):
    try:
        equipo = Equipo.query.get_or_404(id)
        
        # Si hay una imagen, eliminarla del sistema de archivos
        if equipo.img_equipo and equipo.img_equipo != 'img/noimage.jfif':
            try:
                os.remove(os.path.join('app/static', equipo.img_equipo))
            except:
                pass
  
        db.session.delete(equipo)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Rutas para Presupuestos
@main_bp.route('/presupuestos/<int:reparacion_id>')
@login_required
def presupuestos(reparacion_id):
    reparacion = Reparacion.query.get_or_404(reparacion_id)
    return render_template('presupuestos/presupuestos.html', reparacion=reparacion)

@main_bp.route('/nuevo_presupuesto/<int:reparacion_id>', methods=['POST'])
@login_required
def nuevo_presupuesto(reparacion_id):
    try:
        # Validar y convertir unidades
        unidades_str = request.form.get('unidades', '0').strip()
        unidades = int(unidades_str) if unidades_str else 0

        # Validar y convertir precio unitario
        precio_str = request.form.get('precio_unitario', '0').strip()
        precio_unitario = float(precio_str) if precio_str else 0.0

        # Calcular total
        total = unidades * precio_unitario
        
        nuevo_presupuesto = Presupuesto(
            reparacion_id=reparacion_id,
            tipo_reparacion=request.form.get('tipo_reparacion', ''),
            descripcion=request.form.get('descripcion', ''),
            unidades=unidades,
            precio_unitario=precio_unitario,
            total=total
        )
        db.session.add(nuevo_presupuesto)
        db.session.commit()
        flash('Presupuesto creado exitosamente', 'success')
    except ValueError as e:
        flash('Error: Los valores de unidades y precio deben ser números válidos', 'danger')
    except Exception as e:
        flash(f'Error al crear el presupuesto: {str(e)}', 'danger')
    return redirect(url_for('main.presupuestos', reparacion_id=reparacion_id))

@main_bp.route('/editar_presupuesto/<int:id>', methods=['POST'])
@login_required
def editar_presupuesto(id):
    try:
        presupuesto = Presupuesto.query.get_or_404(id)
        
        # Validar y convertir unidades
        unidades_str = request.form.get('unidades', '0').strip()
        unidades = int(unidades_str) if unidades_str else 0

        # Validar y convertir precio unitario
        precio_str = request.form.get('precio_unitario', '0').strip()
        precio_unitario = float(precio_str) if precio_str else 0.0

        # Actualizar datos
        presupuesto.tipo_reparacion = request.form.get('tipo_reparacion', '')
        presupuesto.descripcion = request.form.get('descripcion', '')
        presupuesto.unidades = unidades
        presupuesto.precio_unitario = precio_unitario
        presupuesto.total = unidades * precio_unitario
        presupuesto.aprobado = 'aprobado' in request.form
        
        db.session.commit()
        flash('Presupuesto actualizado exitosamente', 'success')
    except ValueError as e:
        flash('Error: Los valores de unidades y precio deben ser números válidos', 'danger')
    except Exception as e:
        flash(f'Error al actualizar el presupuesto: {str(e)}', 'danger')
    return redirect(url_for('main.presupuestos', reparacion_id=presupuesto.reparacion_id))

@main_bp.route('/eliminar_presupuesto/<int:id>', methods=['DELETE'])
@login_required
def eliminar_presupuesto(id):
    try:
        presupuesto = Presupuesto.query.get_or_404(id)
        reparacion_id = presupuesto.reparacion_id
        db.session.delete(presupuesto)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Template filter para colores de estado
@main_bp.app_template_filter('estado_color')
def estado_color(estado):
    colores = {
        'pendiente': 'warning',
        'en proceso': 'primary',
        'completado': 'success',
        'cancelado': 'danger'
    }
    return colores.get(estado.lower(), 'secondary')



@main_bp.route('/presupuestosResumen')
@login_required
def presupuestosResumen():
    return render_template('presupuestos/presupuestosResumen.html')



@main_bp.route('/presupuesto/<int:id>')
@login_required
def ver_presupuesto(id):
    try:
        presupuesto = Presupuesto.query.get_or_404(id)
        return jsonify({
            'success': True,
            'presupuesto': {
                'id': presupuesto.id,
                'cliente': presupuesto.reparacion.cliente,
                'tipo_reparacion': presupuesto.tipo_reparacion,
                'descripcion': presupuesto.descripcion,
                'unidades': presupuesto.unidades,
                'precio_unitario': float(presupuesto.precio_unitario),
                'total': float(presupuesto.total),
                'fecha': presupuesto.fecha_creacion.strftime('%Y-%m-%d'),
                'estado': 'Aprobado' if presupuesto.aprobado else 'Pendiente',
                'reparacion_id': presupuesto.reparacion_id
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/presupuestos/resumen')
@login_required
def get_presupuestos_resumen():
    try:
        # Obtener todos los presupuestos
        presupuestos = Presupuesto.query.join(Reparacion).all()
        
        # Preparar datos para el frontend
        presupuestos_data = [{
            'id': p.id,
            'reparacion_id': p.reparacion_id,
            'cliente': p.reparacion.cliente,
            'tipo_reparacion': p.tipo_reparacion,
            'fecha': p.fecha_creacion.strftime('%Y-%m-%d'),
            'total': float(p.total),
            'estado': 'Aprobado' if p.aprobado else 'Pendiente'
        } for p in presupuestos]
        
        # Calcular estadísticas
        total_presupuestos = len(presupuestos_data)
        presupuestos_aprobados = sum(1 for p in presupuestos_data if p['estado'] == 'Aprobado')
        presupuestos_pendientes = total_presupuestos - presupuestos_aprobados
        total_facturado = sum(p['total'] for p in presupuestos_data if p['estado'] == 'Aprobado')
        
        return jsonify({
            'success': True,
            'presupuestos': presupuestos_data,
            'estadisticas': {
                'total': total_presupuestos,
                'aprobados': presupuestos_aprobados,
                'pendientes': presupuestos_pendientes,
                'facturado': total_facturado
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/facturacion')
@login_required
def get_facturacion():
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        query = Presupuesto.query.filter_by(aprobado=True)
        
        if fecha_inicio and fecha_fin:
            fecha_inicio = datetime.fromisoformat(fecha_inicio.split('T')[0])
            fecha_fin = datetime.fromisoformat(fecha_fin.split('T')[0])
            query = query.filter(
                Presupuesto.fecha_creacion >= fecha_inicio,
                Presupuesto.fecha_creacion <= fecha_fin
            )
        
        total_facturado = sum(p.total for p in query.all())
        
        return jsonify({
            'success': True,
            'facturacion': float(total_facturado)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main_bp.route('/tablero')
@login_required
def tablero():
    usuarios = Usuario.query.all()
    return render_template('tareas/tablero.html', usuarios=usuarios)

@main_bp.route('/api/tareas', methods=['GET'])
@login_required
def get_tareas():
    tareas = Tarea.query.filter(Tarea.estado != 'archivada').all()
    return jsonify([{
        'id': t.id,
        'titulo': t.titulo,
        'descripcion': t.descripcion,
        'estado': t.estado,
        'prioridad': t.prioridad,
        'asignado_a': t.asignado_a.usuario if t.asignado_a else 'Sin asignar',
        'fecha_vencimiento': t.fecha_vencimiento.strftime('%Y-%m-%d') if t.fecha_vencimiento else None
    } for t in tareas])

@main_bp.route('/api/tareas', methods=['POST'])
@login_required
def crear_tarea():
    try:

        fecha_vencimiento = None
        if request.form.get('fecha_vencimiento'):
            try:
                fecha_vencimiento = datetime.strptime(request.form['fecha_vencimiento'], '%Y-%m-%d')
            except ValueError as e:
                print("Error al parsear la fecha:", e)
        
        nueva_tarea = Tarea(
            titulo=request.form['titulo'],
            descripcion=request.form['descripcion'],
            estado='pendiente',  # Agregar estado inicial
            prioridad=request.form['prioridad'],
            asignado_a_id=request.form['asignado_a_id'],
            creado_por_id=current_user.id,
            fecha_vencimiento=fecha_vencimiento
        )
                # Crear notificación para el usuario asignado
        if nueva_tarea.asignado_a_id:
            crear_notificacion(
                usuario_id=nueva_tarea.asignado_a_id,
                tipo='tarea',
                mensaje=f'Se te ha asignado una nueva tarea: {nueva_tarea.titulo}',
                referencia_id=nueva_tarea.id
            )
        
        db.session.add(nueva_tarea)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear la tarea: {str(e)}', 'danger')
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/tareas/<int:id>/estado', methods=['PUT'])
@login_required
def actualizar_estado_tarea(id):
    try:
        tarea = Tarea.query.get_or_404(id)
        data = request.get_json()
        
        tarea.estado = data['estado']
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/tareas/<int:id>', methods=['GET'])
@login_required
def obtener_tarea(id):
    try:
        tarea = Tarea.query.get_or_404(id)
        return jsonify({
            'id': tarea.id,
            'titulo': tarea.titulo,
            'descripcion': tarea.descripcion,
            'estado': tarea.estado,
            'prioridad': tarea.prioridad,
            'asignado_a_id': tarea.asignado_a_id,
            'fecha_vencimiento': tarea.fecha_vencimiento.strftime('%Y-%m-%d') if tarea.fecha_vencimiento else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/tareas/<int:id>', methods=['PUT'])
@login_required
def actualizar_tarea(id):
    try:
        tarea = Tarea.query.get_or_404(id)
        form_data = request.form

        # Actualizar los campos de la tarea
        tarea.titulo = form_data.get('titulo', tarea.titulo)
        tarea.descripcion = form_data.get('descripcion', tarea.descripcion)
        tarea.prioridad = form_data.get('prioridad', tarea.prioridad)
        tarea.asignado_a_id = form_data.get('asignado_a_id', tarea.asignado_a_id)
        
        # Manejar la fecha de vencimiento
        if form_data.get('fecha_vencimiento'):
            try:
                tarea.fecha_vencimiento = datetime.strptime(form_data['fecha_vencimiento'], '%Y-%m-%d')
            except ValueError:
                return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400


        # Actualizar notificación
        if tarea.asignado_a_id:
            crear_notificacion(
                usuario_id=tarea.asignado_a_id,
                tipo='tarea',
                mensaje=f'Se te ha asignado a la tarea: {tarea.titulo}',
                referencia_id=tarea.id
            )

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/tareas/<int:id>', methods=['DELETE'])
@login_required
def eliminar_tarea(id):
    try:
        tarea = Tarea.query.get_or_404(id)
        db.session.delete(tarea)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/tareas/archivadas', methods=['GET'])
@login_required
def get_tareas_archivadas():
    tareas = Tarea.query.filter_by(estado='archivada').all()
    return jsonify([{
        'id': t.id,
        'titulo': t.titulo,
        'descripcion': t.descripcion,
        'prioridad': t.prioridad,
        'asignado_a': t.asignado_a.usuario if t.asignado_a else 'Sin asignar',
        'fecha_vencimiento': t.fecha_vencimiento.strftime('%Y-%m-%d') if t.fecha_vencimiento else None
    } for t in tareas])

@main_bp.route('/api/tareas/<int:id>/archivar', methods=['PUT'])
@login_required
def archivar_tarea(id):
    try:
        tarea = Tarea.query.get_or_404(id)
        tarea.estado = 'archivada'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/tareas/<int:id>/restaurar', methods=['PUT'])
@login_required
def restaurar_tarea(id):
    try:
        tarea = Tarea.query.get_or_404(id)
        tarea.estado = 'pendiente'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500



@main_bp.route('/api/notificaciones', methods=['GET'])
@login_required
def get_notificaciones():
    notificaciones = Notificacion.query.filter_by(
        usuario_id=current_user.id
    ).order_by(Notificacion.fecha_creacion.desc()).all()
    
    return jsonify([{
        'id': n.id,
        'tipo': n.tipo,
        'mensaje': n.mensaje,
        'leida': n.leida,
        'fecha': n.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
        'referencia_id': n.referencia_id
    } for n in notificaciones])

@main_bp.route('/api/notificaciones/marcar-leida/<int:id>', methods=['PUT'])
@login_required
def marcar_notificacion_leida(id):
    try:
        notificacion = Notificacion.query.get_or_404(id)
        notificacion.leida = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/notificaciones')
@login_required
def notificaciones():
    return render_template('notificaciones/notificaciones.html')


@main_bp.route('/generar_pdf_presupuesto/<int:reparacion_id>', methods=['POST'])
@login_required
def generar_pdf_presupuesto(reparacion_id):
    try:
        reparacion = Reparacion.query.get_or_404(reparacion_id)
        
        # Obtener datos del formulario
        marca_modelo = request.form.get('marca_modelo', '')
        numero_serie = request.form.get('numero_serie', '')
        descripcion_problema = request.form.get('descripcion_problema', '')
        impuestos = float(request.form.get('impuestos', 21))
        tiempo_estimado = request.form.get('tiempo_estimado', '')
        garantia = request.form.get('garantia', '')
        terminos_pago = request.form.get('terminos_pago', '')
        validez = request.form.get('validez', '')
        
        # Obtener presupuestos seleccionados
        presupuestos_ids = request.form.getlist('presupuestos[]')
        presupuestos = Presupuesto.query.filter(Presupuesto.id.in_(presupuestos_ids)).all()
        
        # Crear PDF
        pdf_filename = f'presupuesto_{reparacion.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        pdf_path = os.path.join('app', 'static', 'pdfs', pdf_filename)
        
        # Asegurarse de que el directorio existe
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Crear el documento con márgenes personalizados
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a237e'),  # Azul oscuro
            alignment=1  # Centrado
        ))
        
        styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1565c0'),  # Azul medio
            spaceBefore=15,
            spaceAfter=10
        ))
        
        styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=16
        ))
        styles.add(ParagraphStyle(
            name='CustomDescription',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            spaceBefore=6,
            spaceAfter=6,
            wordWrap='CJK' 
        ))
        
        # Encabezado con logo y título
        header_data = [
            [Image('app/static/img/FixLogo.png', width=1.5*inch, height=1.2*inch),
             Paragraph("Presupuesto de Servicio Técnico", styles['CustomTitle'])]
        ]
        header_table = Table(header_data, colWidths=[2*inch, 4*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 20))
        
        # Información del presupuesto
        elements.append(Paragraph(f"Presupuesto #{reparacion.id}", styles['CustomHeading']))
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", styles['CustomNormal']))
        elements.append(Spacer(1, 20))
        
        # Información del cliente en tabla
        cliente_data = [
            ['INFORMACIÓN DEL CLIENTE', ''],
            ['Cliente:', reparacion.cliente],
            ['Teléfono:', reparacion.telefono],
            ['Email:', reparacion.email]
        ]
        cliente_table = Table(cliente_data, colWidths=[100, 400])
        cliente_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#e3f2fd')),  # Azul muy claro
            ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#1565c0')),
            ('SPAN', (0, 0), (1, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(cliente_table)
        elements.append(Spacer(1, 20))
        
        # Información del equipo en tabla
        equipo_data = [
            ['DETALLES DEL EQUIPO', ''],
            ['Marca/Modelo:', marca_modelo if marca_modelo else 'No especificado'],
            ['Número de Serie:', numero_serie if numero_serie else 'No especificado'],
            ['Descripción:', Paragraph(descripcion_problema, styles['CustomDescription'])]
        ]
        equipo_table = Table(equipo_data, colWidths=[100, 400])
        equipo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#e3f2fd')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#1565c0')),
            ('SPAN', (0, 0), (1, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alinear al tope para descripción larga
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
            # Ajustar el espacio de la celda de descripción
            ('TOPPADDING', (1, -1), (1, -1), 12),
            ('BOTTOMPADDING', (1, -1), (1, -1), 12),
        ]))

        # Ajustar el tamaño de la tabla dinámicamente
        equipo_table._argW[1] = 400  # Ancho fijo para la segunda columna
        equipo_table._argH[3] = None  # Altura automática para la fila de descripción


        elements.append(equipo_table)
        elements.append(Spacer(1, 20))
        
        # Tabla de presupuestos
        elements.append(Paragraph("DETALLE DE SERVICIOS", styles['CustomHeading']))
        data = [['Servicio', 'Unidades', 'Precio Unit.', 'Total']]
        subtotal = 0
        for p in presupuestos:
            data.append([
                p.tipo_reparacion,
                str(p.unidades),
                f"${p.precio_unitario:.2f}",
                f"${p.total:.2f}"
            ])
            subtotal += float(p.total)
            
        # Calcular totales
        impuesto = subtotal * (impuestos/100)
        total = subtotal + impuesto
        
        # Agregar totales
        data.extend([
            ['', '', 'Subtotal:', f"${subtotal:.2f}"],
            ['', '', f'IVA ({impuestos}%):', f"${impuesto:.2f}"],
            ['', '', 'TOTAL:', f"${total:.2f}"]
        ])
        
        # Crear y estilizar la tabla
        table = Table(data, colWidths=[250, 75, 100, 75])
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Contenido
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -4), 1, colors.grey),
            # Totales
            ('SPAN', (0, -3), (2, -3)),
            ('SPAN', (0, -2), (2, -2)),
            ('SPAN', (0, -1), (2, -1)),
            ('ALIGN', (-2, -3), (-1, -1), 'RIGHT'),
            ('FONTNAME', (-2, -3), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e3f2fd')),
            ('LINEABOVE', (-2, -3), (-1, -3), 1, colors.black),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        # Términos y condiciones en tabla
        elements.append(Paragraph("TÉRMINOS Y CONDICIONES", styles['CustomHeading']))
        terminos_data = [
            ['Tiempo Estimado:', tiempo_estimado],
            ['Garantía:', garantia],
            ['Términos de Pago:', terminos_pago],
            ['Validez:', validez]
        ]
        terminos_table = Table(terminos_data, colWidths=[150, 350])
        terminos_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(terminos_table)
        elements.append(Spacer(1, 40))
        
        # Firmas
        firma_data = [
            ['_'*30, '_'*30],
            ['Cliente', 'Técnico'],
            [reparacion.cliente, reparacion.tecnico if reparacion.tecnico else 'No asignado']
        ]
        firma_table = Table(firma_data, colWidths=[250, 250])
        firma_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 1), (-1, 1), 20),
        ]))
        elements.append(firma_table)
        
        # Generar PDF
        doc.build(elements)

        documento = Documento(
            reparacion_id=reparacion.id,
            filename=pdf_filename,
            total=total
        )
        db.session.add(documento)
        db.session.commit()
        
        # Devolver la URL del PDF generado
        pdf_url = url_for('static', filename=f'pdfs/{pdf_filename}')
        return jsonify({'success': True, 'pdf_url': pdf_url})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/documentos')
@login_required
def documentos():
    documentos = Documento.query.order_by(Documento.fecha_creacion.desc()).all()
    return render_template('presupuestos/documentos.html', documentos=documentos)

@main_bp.route('/api/documentos')
@login_required
def get_documentos():
    cliente = request.args.get('cliente', '')
    mes = request.args.get('mes', '')
    year = request.args.get('year', '')
    
    query = Documento.query.join(Reparacion)
    
    if cliente:
        query = query.filter(Reparacion.cliente.ilike(f'%{cliente}%'))
    if mes:
        query = query.filter(extract('month', Documento.fecha_creacion) == int(mes))
    if year:
        query = query.filter(extract('year', Documento.fecha_creacion) == int(year))
    
    documentos = query.order_by(Documento.fecha_creacion.desc()).all()
    
    return jsonify([{
        'id': doc.id,
        'fecha': doc.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
        'cliente': doc.reparacion.cliente,
        'reparacion_id': doc.reparacion_id,
        'total': float(doc.total),
        'estado': doc.estado,
        'estado_color': doc.estado_color,
        'pdf_url': doc.pdf_url,
        'filename': doc.filename
    } for doc in documentos])

@main_bp.route('/api/documentos/<int:id>', methods=['DELETE'])
@login_required
def eliminar_documento(id):
    try:
        documento = Documento.query.get_or_404(id)
        # Eliminar archivo físico
        pdf_path = os.path.join('app', 'static', 'pdfs', documento.filename)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        db.session.delete(documento)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/descargar-pdf/<path:filename>')
@login_required
def descargar_pdf(filename):
    try:
        return send_from_directory('static/pdfs', filename, as_attachment=True)
    except Exception as e:
        flash('Error al descargar el archivo', 'danger')
        return redirect(url_for('main.documentos'))

@main_bp.route('/api/documentos/<int:id>/estado', methods=['PUT'])
@login_required
def cambiar_estado_documento(id):
    try:
        documento = Documento.query.get_or_404(id)
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in ['generado', 'firmado', 'cancelado']:
            return jsonify({'success': False, 'error': 'Estado no válido'}), 400
        
        documento.estado = nuevo_estado
        db.session.commit()
        
        # Crear notificación
        mensaje = f'Documento #{documento.id} cambió a estado {nuevo_estado}'
        crear_notificacion(
            usuario_id=current_user.id,
            tipo='documento',
            mensaje=mensaje,
            referencia_id=documento.id
        )
        
        return jsonify({
            'success': True,
            'estado': documento.estado,
            'estado_color': documento.estado_color
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/usuarios')
@login_required
def usuarios():
    return render_template('base.html')






@main_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))











@main_bp.route('/usuarios')
def get_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([{
        'id': u.id,
        'usuario': u.usuario,
        'rol': u.rol,
        'fecha_registro': u.fecha_registro.strftime('%Y-%m-%d %H:%M:%S')
    } for u in usuarios])