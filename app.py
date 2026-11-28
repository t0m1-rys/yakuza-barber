import os
from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask,
    render_template,
    redirect,
    request,
    jsonify,
    flash,
    session
)

from werkzeug.utils import secure_filename

from datetime import (
    date,
    datetime,
    time,
    timedelta
)

from database.database import db

from models.usuario import Usuario
from models.cliente import Cliente
from models.barbero import Barbero
from models.servicio import Servicio
from models.Reserva import Reserva
from models.notificacion import Notificacion

from urllib.parse import quote


# ==========================================================
# CONFIGURACIÓN DE FLASK
# ==========================================================


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("Falta configurar SECRET_KEY")

# ==========================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==========================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Compatibilidad con las direcciones de Render
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    database_uri = DATABASE_URL

else:
    DATABASE_PATH = os.environ.get("DATABASE_PATH")

    if DATABASE_PATH:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        database_uri = "sqlite:///" + DATABASE_PATH
    else:
        database_uri = "sqlite:///yakuza.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)



# ==========================================================
# PÁGINA PRINCIPAL
# ==========================================================

@app.route("/")
def inicio():

    barberos = Barbero.query.filter_by(
        activo=True
    ).all()

    return render_template(
        "index.html",
        barberos=barberos
    )


# ==========================================================
# PÁGINA DE BARBEROS
# ==========================================================


@app.route("/barberos")
def mostrar_barberos():

    try:
        barberos = (
            Barbero.query
            .order_by(Barbero.id.asc())
            .all()
        )

        return render_template(
            "barberos.html",
            barberos=barberos
        )

    except Exception as e:
        app.logger.exception("Error al cargar los barberos")
        return "Error al cargar los barberos", 500
# ==========================================================
# RESERVAR HORA
# ==========================================================

@app.route(
    "/reservar/<int:barbero_id>",
    methods=["GET", "POST"]
)
def reservar(barbero_id):

    barbero = Barbero.query.get_or_404(barbero_id)

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        telefono = request.form.get(
            "telefono",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        servicio_id = request.form.get(
            "servicio_id"
        )

        fecha_texto = request.form.get(
            "fecha"
        )

        hora_texto = request.form.get(
            "hora"
        )

        # --------------------------------------------------
        # VALIDACIONES
        # --------------------------------------------------

        if not nombre:

            flash(
                "Debes ingresar tu nombre.",
                "danger"
            )

            return redirect(request.url)

        if not telefono:

            flash(
                "Debes ingresar tu teléfono.",
                "danger"
            )

            return redirect(request.url)

        if not servicio_id:

            flash(
                "Debes seleccionar un servicio.",
                "danger"
            )

            return redirect(request.url)

        if not fecha_texto:

            flash(
                "Debes seleccionar una fecha.",
                "danger"
            )

            return redirect(request.url)

        if not hora_texto:

            flash(
                "Debes seleccionar una hora.",
                "danger"
            )

            return redirect(request.url)

        # --------------------------------------------------
        # SERVICIO
        # --------------------------------------------------

        try:

            servicio = Servicio.query.get(
                int(servicio_id)
            )

        except (ValueError, TypeError):

            servicio = None

        if not servicio:

            flash(
                "El servicio seleccionado no existe.",
                "danger"
            )

            return redirect(request.url)

        if not servicio.activo:

            flash(
                "El servicio seleccionado no está disponible.",
                "danger"
            )

            return redirect(request.url)

        # --------------------------------------------------
        # FECHA
        # --------------------------------------------------

        try:

            fecha_reserva = datetime.strptime(
                fecha_texto,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "La fecha seleccionada no es válida.",
                "danger"
            )

            return redirect(request.url)

        if fecha_reserva < date.today():

            flash(
                "No puedes reservar una fecha pasada.",
                "danger"
            )

            return redirect(request.url)

        # --------------------------------------------------
        # HORA
        # --------------------------------------------------

        try:

            hora_reserva = datetime.strptime(
                hora_texto,
                "%H:%M"
            ).time()

        except ValueError:

            flash(
                "La hora seleccionada no es válida.",
                "danger"
            )

            return redirect(request.url)

        # --------------------------------------------------
        # HORARIO DE ATENCIÓN
        # --------------------------------------------------

        if fecha_reserva.weekday() == 6:

            flash(
                "La barbería no atiende los domingos.",
                "danger"
            )

            return redirect(request.url)

        if fecha_reserva.weekday() < 5:

            bloques = [
                (time(11, 0), time(13, 0)),
                (time(15, 0), time(19, 0))
            ]

        else:

            bloques = [
                (time(10, 0), time(13, 0)),
                (time(15, 0), time(18, 0))
            ]

        # --------------------------------------------------
        # CALCULAR DURACIÓN
        # --------------------------------------------------

        inicio_nuevo = datetime.combine(
            fecha_reserva,
            hora_reserva
        )

        fin_nuevo = (
            inicio_nuevo
            + timedelta(
                minutes=servicio.duracion
            )
        )

        # --------------------------------------------------
        # COMPROBAR HORARIO
        # --------------------------------------------------

        dentro_horario = False

        for inicio_bloque, fin_bloque in bloques:

            inicio_bloque_dt = datetime.combine(
                fecha_reserva,
                inicio_bloque
            )

            fin_bloque_dt = datetime.combine(
                fecha_reserva,
                fin_bloque
            )

            if (
                inicio_nuevo >= inicio_bloque_dt
                and
                fin_nuevo <= fin_bloque_dt
            ):

                dentro_horario = True

                break

        if not dentro_horario:

            flash(
                "La hora seleccionada está fuera del horario de atención.",
                "danger"
            )

            return redirect(request.url)

        # --------------------------------------------------
        # COMPROBAR RESERVAS EXISTENTES
        # --------------------------------------------------

        reservas_existentes = (
            Reserva.query
            .filter_by(
                barbero_id=barbero.id,
                fecha=fecha_reserva
            )
            .filter(
                Reserva.estado != "cancelada"
            )
            .all()
        )

        for reserva_existente in reservas_existentes:

            inicio_existente = datetime.combine(
                fecha_reserva,
                reserva_existente.hora
            )

            fin_existente = (
                inicio_existente
                + timedelta(
                    minutes=reserva_existente.servicio.duracion
                )
            )

            if (
                inicio_nuevo < fin_existente
                and
                fin_nuevo > inicio_existente
            ):

                flash(
                    "La hora seleccionada ya está ocupada.",
                    "danger"
                )

                return redirect(request.url)

        # --------------------------------------------------
        # CREAR / ACTUALIZAR CLIENTE
        # --------------------------------------------------

        cliente = Cliente.query.filter_by(
            telefono=telefono
        ).first()

        if cliente:

            cliente.nombre = nombre
            cliente.email = email
            cliente.activo = True

        else:

            cliente = Cliente(
                nombre=nombre,
                telefono=telefono,
                email=email,
                activo=True
            )

            db.session.add(cliente)

            db.session.flush()

        # --------------------------------------------------
        # CREAR RESERVA
        # --------------------------------------------------

        nueva_reserva = Reserva(
            cliente_id=cliente.id,
            barbero_id=barbero.id,
            servicio_id=servicio.id,
            fecha=fecha_reserva,
            hora=hora_reserva,
            estado="pendiente"
        )

        db.session.add(
            nueva_reserva
        )

        db.session.flush()

        # --------------------------------------------------
        # AVISAR AL BARBERO DE LA NUEVA CITA
        # --------------------------------------------------

        db.session.add(
            Notificacion(
                barbero_id=barbero.id,
                reserva_id=nueva_reserva.id,
                mensaje=(
                    f"Nueva cita: {cliente.nombre} "
                    f"(tel. {cliente.telefono}) - "
                    f"{servicio.nombre} - "
                    f"{fecha_reserva.strftime('%d/%m/%Y')} "
                    f"a las {hora_reserva.strftime('%H:%M')}."
                )
            )
        )

        db.session.commit()

        return render_template(
            "reserva_confirmada.html",
            reserva=nueva_reserva
        )

    # ------------------------------------------------------
    # SERVICIOS DISPONIBLES
    # ------------------------------------------------------

    servicios = Servicio.query.filter_by(
        activo=True
    ).all()

    return render_template(
        "reservar.html",
        barbero=barbero,
        servicios=servicios
    )


# ==========================================================
# HORARIOS DISPONIBLES
# ==========================================================

@app.route(
    "/horarios-disponibles/<int:barbero_id>"
)
def horarios_disponibles(barbero_id):

    barbero = Barbero.query.get_or_404(
        barbero_id
    )

    fecha_texto = request.args.get(
        "fecha"
    )

    servicio_id = request.args.get(
        "servicio_id"
    )

    if not fecha_texto or not servicio_id:

        return jsonify({
            "horarios": []
        })

    # --------------------------------------------------
    # FECHA
    # --------------------------------------------------

    try:

        fecha_seleccionada = datetime.strptime(
            fecha_texto,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return jsonify({
            "horarios": []
        })

    # --------------------------------------------------
    # SERVICIO
    # --------------------------------------------------

    try:

        servicio = Servicio.query.get(
            int(servicio_id)
        )

    except (ValueError, TypeError):

        servicio = None

    if not servicio or not servicio.activo:

        return jsonify({
            "horarios": []
        })

    # --------------------------------------------------
    # DOMINGO
    # --------------------------------------------------

    if fecha_seleccionada.weekday() == 6:

        return jsonify({
            "horarios": []
        })

    # --------------------------------------------------
    # HORARIOS
    # --------------------------------------------------

    if fecha_seleccionada.weekday() < 5:

        bloques = [
            (time(11, 0), time(13, 0)),
            (time(15, 0), time(19, 0))
        ]

    else:

        bloques = [
            (time(10, 0), time(13, 0)),
            (time(15, 0), time(18, 0))
        ]

    # --------------------------------------------------
    # RESERVAS EXISTENTES
    # --------------------------------------------------

    reservas = (
        Reserva.query
        .filter_by(
            barbero_id=barbero.id,
            fecha=fecha_seleccionada
        )
        .filter(
            Reserva.estado != "cancelada"
        )
        .all()
    )

    horarios_disponibles = []

    duracion = servicio.duracion

    # --------------------------------------------------
    # GENERAR HORARIOS
    # --------------------------------------------------

    for inicio, fin in bloques:

        hora_actual = datetime.combine(
            fecha_seleccionada,
            inicio
        )

        hora_final = datetime.combine(
            fecha_seleccionada,
            fin
        )

        while (
            hora_actual
            + timedelta(minutes=duracion)
            <= hora_final
        ):

            inicio_nuevo = hora_actual

            fin_nuevo = (
                hora_actual
                + timedelta(
                    minutes=duracion
                )
            )

            ocupado = False

            # --------------------------------------------------
            # COMPROBAR CRUCE
            # --------------------------------------------------

            for reserva in reservas:

                inicio_reserva = datetime.combine(
                    fecha_seleccionada,
                    reserva.hora
                )

                fin_reserva = (
                    inicio_reserva
                    + timedelta(
                        minutes=reserva.servicio.duracion
                    )
                )

                if (
                    inicio_nuevo < fin_reserva
                    and
                    fin_nuevo > inicio_reserva
                ):

                    ocupado = True

                    break

            if not ocupado:

                horarios_disponibles.append(
                    hora_actual.strftime("%H:%M")
                )

            # Intervalos de 15 minutos
            hora_actual += timedelta(
                minutes=15
            )

    return jsonify({
        "horarios": horarios_disponibles
    })


# ==========================================================
# LOGIN
# ==========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "usuario",
            ""
        ).strip()

        contrasena = request.form.get(
            "contrasena",
            ""
        )

        # --------------------------------------------------
        # BUSCAR USUARIO
        # --------------------------------------------------

        usuario = Usuario.query.filter_by(
            email=email
        ).first()

        # --------------------------------------------------
        # VALIDAR
        # --------------------------------------------------

        if (
            usuario
            and usuario.password == contrasena
            and usuario.activo
            and usuario.rol == "admin"
        ):

            session["admin"] = True
            session["usuario_id"] = usuario.id
            session["usuario_nombre"] = usuario.nombre

            return redirect(
                "/admin"
            )

        flash(
            "Correo o contraseña incorrectos.",
            "danger"
        )

    return render_template(
        "login.html"
    )


# ==========================================================
# CERRAR SESIÓN
# ==========================================================

@app.route("/logout")
def logout():

    session.pop(
        "admin",
        None
    )

    session.pop(
        "usuario_id",
        None
    )

    session.pop(
        "usuario_nombre",
        None
    )

    return redirect(
        "/login"
    )


# ==========================================================
# DASHBOARD
# ==========================================================

@app.route("/admin")
def admin():

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    hoy = date.today()

    total_clientes = Cliente.query.filter_by(
        activo=True
    ).count()

    total_barberos = Barbero.query.filter_by(
        activo=True
    ).count()

    total_servicios = Servicio.query.filter_by(
        activo=True
    ).count()

    reservas_pendientes = Reserva.query.filter_by(
        estado="pendiente"
    ).count()

    reservas_hoy = (
        Reserva.query
        .filter_by(
            fecha=hoy
        )
        .filter(
            Reserva.estado != "cancelada"
        )
        .count()
    )

    proximas_reservas = (
        Reserva.query
        .filter(
            Reserva.fecha >= hoy,
            Reserva.estado != "cancelada"
        )
        .order_by(
            Reserva.fecha.asc(),
            Reserva.hora.asc()
        )
        .limit(10)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_clientes=total_clientes,
        total_barberos=total_barberos,
        total_servicios=total_servicios,
        reservas_pendientes=reservas_pendientes,
        reservas_hoy=reservas_hoy,
        proximas_reservas=proximas_reservas
    )


# ==========================================================
# ADMINISTRACIÓN DE RESERVAS
# ==========================================================

@app.route("/admin/reservas")
def admin_reservas():

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    reservas = (
        Reserva.query
        .order_by(
            Reserva.fecha.asc(),
            Reserva.hora.asc()
        )
        .all()
    )

    return render_template(
        "admin/reservas.html",
        reservas=reservas
    )


# ==========================================================
# DETALLE DE RESERVA
# ==========================================================

@app.route(
    "/admin/reserva/<int:reserva_id>"
)
def detalle_reserva(reserva_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    reserva = Reserva.query.get_or_404(
        reserva_id
    )

    return render_template(
        "admin/detalle_reserva.html",
        reserva=reserva
    )


# ==========================================================
# CAMBIAR ESTADO DE RESERVA
# ==========================================================

@app.route(
    "/admin/reserva/<int:reserva_id>/estado/<string:nuevo_estado>"
)
def cambiar_estado_reserva(
    reserva_id,
    nuevo_estado
):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    reserva = Reserva.query.get_or_404(
        reserva_id
    )

    estados_validos = [
        "pendiente",
        "confirmada",
        "completada",
        "cancelada"
    ]

    if nuevo_estado not in estados_validos:

        return "Estado no válido", 400

    estado_anterior = reserva.estado

    reserva.estado = nuevo_estado

    if nuevo_estado == "cancelada" and estado_anterior != "cancelada":

        db.session.add(
            Notificacion(
                barbero_id=reserva.barbero_id,
                reserva_id=reserva.id,
                mensaje=(
                    f"Cita CANCELADA: {reserva.cliente.nombre} - "
                    f"{reserva.servicio.nombre} - "
                    f"{reserva.fecha.strftime('%d/%m/%Y')} "
                    f"a las {reserva.hora.strftime('%H:%M')}."
                )
            )
        )

    db.session.commit()

    return redirect(
        "/admin/reservas"
    )


# ==========================================================
# CLIENTES
# ==========================================================

@app.route("/admin/clientes")
def admin_clientes():

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    clientes = (
        Cliente.query
        .order_by(
            Cliente.nombre.asc()
        )
        .all()
    )

    return render_template(
        "admin/clientes.html",
        clientes=clientes
    )


# ==========================================================
# DETALLE / HISTORIAL DE CLIENTE
# ==========================================================

@app.route(
    "/admin/cliente/<int:cliente_id>"
)
def detalle_cliente(cliente_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    cliente = Cliente.query.get_or_404(
        cliente_id
    )

    reservas = (
        Reserva.query
        .filter_by(
            cliente_id=cliente.id
        )
        .order_by(
            Reserva.fecha.desc(),
            Reserva.hora.desc()
        )
        .all()
    )

    return render_template(
        "admin/detalle_cliente.html",
        cliente=cliente,
        reservas=reservas
    )


# ==========================================================
# SERVICIOS
# ==========================================================

@app.route("/admin/servicios")
def admin_servicios():

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    servicios = (
        Servicio.query
        .order_by(
            Servicio.nombre.asc()
        )
        .all()
    )

    return render_template(
        "admin/servicios.html",
        servicios=servicios
    )


# ==========================================================
# CREAR SERVICIO
# ==========================================================

@app.route(
    "/admin/servicio/nuevo",
    methods=["GET", "POST"]
)
def nuevo_servicio():

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        descripcion = request.form.get(
            "descripcion",
            ""
        ).strip()

        precio_texto = request.form.get(
            "precio",
            ""
        ).strip()

        duracion_texto = request.form.get(
            "duracion",
            ""
        ).strip()

        if not nombre:

            flash(
                "Debes ingresar el nombre del servicio.",
                "danger"
            )

            return redirect(
                request.url
            )

        try:

            precio = int(
                precio_texto
            )

        except (ValueError, TypeError):

            flash(
                "El precio debe ser un número.",
                "danger"
            )

            return redirect(
                request.url
            )

        if precio <= 0:

            flash(
                "El precio debe ser mayor que 0.",
                "danger"
            )

            return redirect(
                request.url
            )

        try:

            duracion = int(
                duracion_texto
            )

        except (ValueError, TypeError):

            flash(
                "La duración debe ser un número.",
                "danger"
            )

            return redirect(
                request.url
            )

        if duracion <= 0:

            flash(
                "La duración debe ser mayor que 0.",
                "danger"
            )

            return redirect(
                request.url
            )

        nuevo = Servicio(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            duracion=duracion,
            activo=True
        )

        db.session.add(
            nuevo
        )

        db.session.commit()

        flash(
            "Servicio creado correctamente.",
            "success"
        )

        return redirect(
            "/admin/servicios"
        )

    return render_template(
        "admin/nuevo_servicio.html"
    )


# ==========================================================
# EDITAR SERVICIO
# ==========================================================

@app.route(
    "/admin/servicio/<int:servicio_id>/editar",
    methods=["GET", "POST"]
)
def editar_servicio(servicio_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    servicio = Servicio.query.get_or_404(
        servicio_id
    )

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        descripcion = request.form.get(
            "descripcion",
            ""
        ).strip()

        precio_texto = request.form.get(
            "precio",
            ""
        ).strip()

        duracion_texto = request.form.get(
            "duracion",
            ""
        ).strip()

        if not nombre:

            flash(
                "Debes ingresar el nombre del servicio.",
                "danger"
            )

            return redirect(
                request.url
            )

        try:

            precio = int(
                precio_texto
            )

        except (ValueError, TypeError):

            flash(
                "El precio debe ser un número.",
                "danger"
            )

            return redirect(
                request.url
            )

        if precio <= 0:

            flash(
                "El precio debe ser mayor que 0.",
                "danger"
            )

            return redirect(
                request.url
            )

        try:

            duracion = int(
                duracion_texto
            )

        except (ValueError, TypeError):

            flash(
                "La duración debe ser un número.",
                "danger"
            )

            return redirect(
                request.url
            )

        if duracion <= 0:

            flash(
                "La duración debe ser mayor que 0.",
                "danger"
            )

            return redirect(
                request.url
            )

        servicio.nombre = nombre
        servicio.descripcion = descripcion
        servicio.precio = precio
        servicio.duracion = duracion

        db.session.commit()

        flash(
            "Servicio actualizado correctamente.",
            "success"
        )

        return redirect(
            "/admin/servicios"
        )

    return render_template(
        "admin/editar_servicio.html",
        servicio=servicio
    )


# ==========================================================
# ACTIVAR / DESACTIVAR SERVICIO
# ==========================================================

@app.route(
    "/admin/servicio/<int:servicio_id>/toggle"
)
def toggle_servicio(servicio_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    servicio = Servicio.query.get_or_404(
        servicio_id
    )

    servicio.activo = not servicio.activo

    db.session.commit()

    return redirect(
        "/admin/servicios"
    )


# ==========================================================
# ADMINISTRACIÓN DE BARBEROS
# ==========================================================

@app.route("/admin/barberos")
def admin_barberos():

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    barberos = (
        Barbero.query
        .order_by(
            Barbero.nombre.asc()
        )
        .all()
    )

    return render_template(
        "admin/barberos.html",
        barberos=barberos
    )


# ==========================================================
# ACTIVAR / DESACTIVAR BARBERO
# ==========================================================

@app.route(
    "/admin/barbero/<int:barbero_id>/toggle"
)
def toggle_barbero(barbero_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    barbero = Barbero.query.get_or_404(
        barbero_id
    )

    barbero.activo = not barbero.activo

    db.session.commit()

    return redirect(
        "/admin/barberos"
    )


# ==========================================================
# AGREGAR BARBERO
# ==========================================================

@app.route(
    "/admin/barbero/nuevo",
    methods=["GET", "POST"]
)
def nuevo_barbero():

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        especialidad = request.form.get(
            "especialidad",
            ""
        ).strip()

        descripcion = request.form.get(
            "descripcion",
            ""
        ).strip()

        telefono = request.form.get(
            "telefono",
            ""
        ).strip()

        foto = request.files.get(
            "foto"
        )

        nombre_foto = None

        # --------------------------------------------------
        # GUARDAR FOTO
        # --------------------------------------------------

        if foto and foto.filename:

            nombre_foto = secure_filename(
                foto.filename
            )

            carpeta = os.path.join(
                app.static_folder,
                "img",
                "barberos"
            )

            os.makedirs(
                carpeta,
                exist_ok=True
            )

            ruta_foto = os.path.join(
                carpeta,
                nombre_foto
            )

            foto.save(
                ruta_foto
            )

        # --------------------------------------------------
        # CREAR BARBERO
        # --------------------------------------------------

        nuevo = Barbero(
            nombre=nombre,
            especialidad=especialidad,
            descripcion=descripcion,
            foto=nombre_foto,
            telefono=telefono or None,
            activo=True
        )

        db.session.add(
            nuevo
        )

        db.session.commit()

        flash(
            "Barbero creado correctamente.",
            "success"
        )

        return redirect(
            "/admin/barberos"
        )

    return render_template(
        "admin/nuevo_barbero.html"
    )


# ==========================================================
# EDITAR BARBERO
# ==========================================================

@app.route(
    "/admin/barbero/<int:barbero_id>/editar",
    methods=["GET", "POST"]
)
def editar_barbero(barbero_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    barbero = Barbero.query.get_or_404(
        barbero_id
    )

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        especialidad = request.form.get(
            "especialidad",
            ""
        ).strip()

        descripcion = request.form.get(
            "descripcion",
            ""
        ).strip()

        if not nombre:

            flash(
                "El nombre del barbero es obligatorio.",
                "danger"
            )

            return redirect(
                request.url
            )

        barbero.nombre = nombre
        barbero.especialidad = especialidad
        barbero.descripcion = descripcion

        barbero.telefono = request.form.get(
            "telefono",
            ""
        ).strip() or None

        # --------------------------------------------------
        # CAMBIAR FOTOGRAFÍA
        # --------------------------------------------------

        foto = request.files.get(
            "foto"
        )

        if foto and foto.filename:

            nombre_foto = secure_filename(
                foto.filename
            )

            carpeta = os.path.join(
                app.static_folder,
                "img",
                "barberos"
            )

            os.makedirs(
                carpeta,
                exist_ok=True
            )

            ruta_foto = os.path.join(
                carpeta,
                nombre_foto
            )

            foto.save(
                ruta_foto
            )

            barbero.foto = nombre_foto

        db.session.commit()

        flash(
            "Barbero actualizado correctamente.",
            "success"
        )

        return redirect(
            "/admin/barberos"
        )

    return render_template(
        "admin/editar_barbero.html",
        barbero=barbero
    )


# ==========================================================
# ELIMINAR BARBERO
# ==========================================================

@app.route(
    "/admin/barbero/<int:barbero_id>/eliminar",
    methods=["POST"]
)
def eliminar_barbero(barbero_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    barbero = Barbero.query.get_or_404(
        barbero_id
    )

    # No se puede borrar si tiene citas futuras activas
    citas_futuras = (
        Reserva.query
        .filter_by(
            barbero_id=barbero.id
        )
        .filter(
            Reserva.fecha >= date.today(),
            Reserva.estado.in_(
                ["pendiente", "confirmada"]
            )
        )
        .count()
    )

    if citas_futuras:

        flash(
            f"{barbero.nombre} tiene {citas_futuras} cita(s) "
            "pendientes. Cancélalas o reasígnalas antes de eliminarlo.",
            "danger"
        )

        return redirect(
            "/admin/barberos"
        )

    nombre = barbero.nombre

    # Se borra el historial que depende de él (claves foráneas)
    Notificacion.query.filter_by(
        barbero_id=barbero.id
    ).delete()

    Reserva.query.filter_by(
        barbero_id=barbero.id
    ).delete()

    db.session.delete(
        barbero
    )

    db.session.commit()

    flash(
        f"Barbero {nombre} eliminado correctamente.",
        "success"
    )

    return redirect(
        "/admin/barberos"
    )


# ==========================================================
# MENSAJES / CITAS DE UN BARBERO
# ==========================================================

@app.route(
    "/admin/barbero/<int:barbero_id>/mensajes"
)
def mensajes_barbero(barbero_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    barbero = Barbero.query.get_or_404(
        barbero_id
    )

    notificaciones = (
        Notificacion.query
        .filter_by(
            barbero_id=barbero.id
        )
        .order_by(
            Notificacion.creada_en.desc()
        )
        .limit(50)
        .all()
    )

    proximas = (
        Reserva.query
        .filter(
            Reserva.barbero_id == barbero.id,
            Reserva.fecha >= date.today(),
            Reserva.estado != "cancelada"
        )
        .order_by(
            Reserva.fecha.asc(),
            Reserva.hora.asc()
        )
        .all()
    )

    # Resumen de la agenda para enviar por WhatsApp
    if proximas:

        lineas = [
            f"Hola {barbero.nombre}, tus próximas citas:"
        ]

        for r in proximas:

            lineas.append(
                f"- {r.fecha.strftime('%d/%m')} "
                f"{r.hora.strftime('%H:%M')} "
                f"{r.cliente.nombre} ({r.servicio.nombre})"
            )

        resumen = "\n".join(lineas)

    else:

        resumen = (
            f"Hola {barbero.nombre}, no tienes citas próximas."
        )

    enlace_whatsapp = None

    if barbero.telefono:

        enlace_whatsapp = (
            f"https://wa.me/{barbero.telefono}?text="
            + quote(resumen)
        )

    return render_template(
        "admin/mensajes_barbero.html",
        barbero=barbero,
        notificaciones=notificaciones,
        proximas=proximas,
        enlace_whatsapp=enlace_whatsapp
    )


# ==========================================================
# MARCAR MENSAJES COMO LEÍDOS
# ==========================================================

@app.route(
    "/admin/barbero/<int:barbero_id>/mensajes/leer",
    methods=["POST"]
)
def marcar_mensajes_leidos(barbero_id):

    if not session.get("admin"):

        return redirect(
            "/login"
        )

    Notificacion.query.filter_by(
        barbero_id=barbero_id,
        leida=False
    ).update({"leida": True})

    db.session.commit()

    return redirect(
        f"/admin/barbero/{barbero_id}/mensajes"
    )


# ==========================================================
# INICIALIZAR BASE DE DATOS
# ==========================================================

with app.app_context():
    db.create_all()

# ==========================================================
# INICIAR APLICACIÓN LOCAL
# ==========================================================

if __name__ == "__main__":
    print("==========================================")
    print("         YAKUZA BARBER INICIADO")
    print("==========================================")
    print("PC: http://127.0.0.1:5000")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )