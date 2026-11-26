
from database.database import db
from werkzeug.security import generate_password_hash, check_password_hash


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="cliente")
    activo = db.Column(db.Boolean, default=True)

    def establecer_password(self, contrasena):
        self.password = generate_password_hash(contrasena)

    def verificar_password(self, contrasena):
        return check_password_hash(self.password, contrasena)

    def __repr__(self):
        return f"<Usuario {self.nombre}>"
