#!/usr/bin/env python3
import os
import sys
sys.path.append('.')

from app.db import get_engine
from sqlalchemy import text

try:
    engine = get_engine()
    print("Database engine created successfully!")
    
    with engine.connect() as conn:
        result = conn.execute(text('SELECT current_database()'))
        db_name = result.scalar()
        print(f"Connected to database: {db_name}")
        
        # Check if we can see tables
        result = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"))
        table_count = result.scalar()
        print(f"Number of public tables: {table_count}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()