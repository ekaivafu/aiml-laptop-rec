import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models import Base

# By default, we use SQLite for local development. 
# This can easily be changed to a PostgreSQL URI later.
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "scraper.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
