from flask import Blueprint, jsonify, send_from_directory,render_template, url_for, redirect, flash,request

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField , SubmitField

from wtforms.validators import DataRequired

from flask_login import login_required, logout_user, LoginManager, current_user, login_user

from app.models.modelos import Usuario, Reparacion, Equipo, Presupuesto, db
from flask_bcrypt import Bcrypt

import os
from werkzeug.utils import secure_filename

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
            return render_template('home.html')
        else:
            return render_template('login.html', form=form)
    return render_template('login.html', form=form)

@main_bp.route('/home')
@login_required
def home():
    return render_template('home.html')

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


@main_bp.route('/notificaciones')
@login_required
def notificaciones():
    return render_template('base.html')


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