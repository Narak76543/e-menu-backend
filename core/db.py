from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import config

Base = declarative_base()

engine = create_engine(
    config.DATABASE_URL,
    pool_timeout=30,
    echo=True
)

Session = sessionmaker(bind=engine)
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()