from database.database import db


class Reserva(db.Model):

    __tablename__ = "reservas"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id"),
        nullable=False
    )

    barbero_id = db.Column(
        db.Integer,
        db.ForeignKey("barberos.id"),
        nullable=False
    )

    servicio_id = db.Column(
        db.Integer,
        db.ForeignKey("servicios.id"),
        nullable=False
    )

    fecha = db.Column(
        db.Date,
        nullable=False
    )

    hora = db.Column(
        db.Time,
        nullable=False
    )

    estado = db.Column(
        db.String(20),
        default="pendiente",
        nullable=False
    )

    cliente = db.relationship(
        "Cliente",
        backref="reservas"
    )

    barbero = db.relationship(
        "Barbero",
        backref="reservas"
    )

    servicio = db.relationship(
        "Servicio",
        backref="reservas"
    )