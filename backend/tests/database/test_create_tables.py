"""
Database setup script for Railway Traffic Management System
Creates all tables using SQLAlchemy models
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models import Base

def create_tables():
    """Create all database tables"""
    # Database connection
    database_url = "postgresql+psycopg2://postgres:1234@localhost:5432/railway_db"
    
    print("🔗 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to: {version}")
            
        print("📋 Creating all tables...")
        Base.metadata.create_all(engine)
        print("✅ All tables created successfully!")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema='public' ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
        print(f"📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = create_tables()
    exit(0 if success else 1)