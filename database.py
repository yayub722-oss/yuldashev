from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os 
 
 
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///shop.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import User, Category, Product, Order, OrderItem
    Base.metadata.create_all(bind=engine)

#postgresql://uzharidor_db_user:zH5I2mJ5E4eZ4kCBCKjGxrKbj3iKalt3@dpg-dahbhg1594qs73811ul0-a/uzharidor_db