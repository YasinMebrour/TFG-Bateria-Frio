"""Database connection utilities."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=10, max_overflow=20)


# Creación de la clase base y del objeto SessionLocal
SessionLocal = sessionmaker(

    autocommit=False,
    autoflush=False,
    bind=engine
)
Base = declarative_base()

# Dependencia para inyectar sesión de BD en routes
def get_db():
    """Yield a SQLAlchemy session and close it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
