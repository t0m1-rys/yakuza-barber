from database.database import db


class Servicio(db.Model):
    __tablename__ = "servicios"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    descripcion = db.Column(
        db.Text,
        nullable=True
    )

    precio = db.Column(
        db.Integer,
        nullable=False
    )

    duracion = db.Column(
        db.Integer,
        nullable=False
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    def __repr__(self):
        return f"<Servicio {self.nombre}>"