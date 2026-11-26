from database.database import db


class Barbero(db.Model):
    __tablename__ = "barberos"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    especialidad = db.Column(
        db.String(100),
        nullable=True
    )

    foto = db.Column(
        db.String(255),
        nullable=True
    )

    descripcion = db.Column(
        db.Text,
        nullable=True
    )

    # Teléfono con código de país y sin "+" (ej: 56912345678).
    # Se usa para el botón de WhatsApp con el aviso de la cita.
    telefono = db.Column(
        db.String(20),
        nullable=True
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    def __repr__(self):
        return f"<Barbero {self.nombre}>"