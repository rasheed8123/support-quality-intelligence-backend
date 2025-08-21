from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Get the appropriate database URL
database_url = settings.database_url

# Determine connect_args based on database type
connect_args = {}
if "sqlite" in database_url.lower():
    # SQLite-specific configuration
    connect_args = {"check_same_thread": False}
elif "mysql" in database_url.lower():
    # MySQL-specific configuration
    connect_args = {
        "charset": "utf8mb4",
        "autocommit": False,
    }

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
