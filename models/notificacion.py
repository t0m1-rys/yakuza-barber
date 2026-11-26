from datetime import datetime

from database.database import db


class Notificacion(db.Model):
    """Mensaje dirigido a un barbero cuando se le agenda una cita."""

    __tablename__ = "notificaciones"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    barbero_id = db.Column(
        db.Integer,
        db.ForeignKey("barberos.id"),
        nullable=False
    )

    reserva_id = db.Column(
        db.Integer,
        db.ForeignKey("reservas.id"),
        nullable=True
    )

    mensaje = db.Column(
        db.Text,
        nullable=False
    )

    leida = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    creada_en = db.Column(
        db.DateTime,
        default=datetime.now,
        nullable=False
    )

    barbero = db.relationship(
        "Barbero",
        backref="notificaciones"
    )

    reserva = db.relationship(
        "Reserva",
        backref="notificaciones"
    )

    def __repr__(self):
        return f"<Notificacion {self.id} barbero={self.barbero_id}>"