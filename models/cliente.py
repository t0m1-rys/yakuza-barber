from database.database import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    telefono = db.Column(
        db.String(20),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        nullable=True
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    def __repr__(self):
        return f"<Cliente {self.nombre}>"