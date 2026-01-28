from sqlmodel import SQLModel, create_engine, Session
from config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.DB_PATH else {}
engine = create_engine(settings.DB_PATH, connect_args=connect_args, pool_pre_ping=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
