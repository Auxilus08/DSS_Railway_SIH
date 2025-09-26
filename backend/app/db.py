import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Load environment variables from .env file
load_dotenv()


def get_engine():
    """Create and configure database engine for Railway Traffic Management System"""
    # Prefer DATABASE_URL if present
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "railway_db")
        db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    
    # Configure engine with optimizations for railway system
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        poolclass=QueuePool,
        pool_size=20,  # Increased for high-frequency position updates
        max_overflow=30,
        pool_recycle=3600,  # Recycle connections every hour
        echo=False,  # Set to True for SQL debugging
        connect_args={
            "options": "-c timezone=utc",  # Ensure UTC timezone
            "application_name": "railway_traffic_mgmt"
        }
    )
    return engine


def get_session():
    """Get a database session"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_database():
    """Initialize database with extensions and basic setup"""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Enable required extensions
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
            print("✅ TimescaleDB extension enabled")
        except Exception as e:
            print(f"⚠️ TimescaleDB extension warning: {e}")
        
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            print("✅ PostGIS extension enabled")
        except Exception as e:
            print(f"⚠️ PostGIS extension not available: {e}")
            print("   Geographic features will be limited")
        
        conn.commit()
    
    print("Database initialized with required extensions")
