#!/usr/bin/env python3
"""
Add password support to controllers table and create test admin user
"""
import sys
from sqlalchemy import text
from app.auth import get_password_hash
from app.models import Controller
from app.db import get_db, get_engine

def add_password_column():
    """Add password_hash column to controllers table if it doesn't exist"""
    print("🔧 Adding password_hash column to controllers table...")
    
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='controllers' AND column_name='password_hash'
            """))
            
            if result.fetchone() is None:
                # Add column
                conn.execute(text("""
                    ALTER TABLE controllers 
                    ADD COLUMN password_hash VARCHAR(255)
                """))
                print("✅ password_hash column added successfully")
            else:
                print("ℹ️  password_hash column already exists")
                
    except Exception as e:
        print(f"⚠️  Error adding column: {e}")
        return False
    
    return True

def create_test_users():
    """Create test users with passwords"""
    print("\n👤 Creating test users with passwords...")
    
    db = next(get_db())
    
    test_users = [
        {
            "employee_id": "ADMIN001",
            "name": "Test Admin",
            "auth_level": "ADMIN",
            "password": "admin123"
        },
        {
            "employee_id": "MANAGER001", 
            "name": "Test Manager",
            "auth_level": "MANAGER",
            "password": "manager123"
        },
        {
            "employee_id": "OPERATOR001",
            "name": "Test Operator", 
            "auth_level": "OPERATOR",
            "password": "operator123"
        }
    ]
    
    for user_data in test_users:
        try:
            # Check if user already exists
            existing = db.query(Controller).filter(
                Controller.employee_id == user_data["employee_id"]
            ).first()
            
            password_hash = get_password_hash(user_data["password"])
            
            if existing:
                # Update password using raw SQL since model may not have the field yet
                db.execute(text("""
                    UPDATE controllers 
                    SET password_hash = :password_hash 
                    WHERE employee_id = :employee_id
                """), {"password_hash": password_hash, "employee_id": user_data["employee_id"]})
                db.commit()
                print(f"✅ Updated password for {user_data['employee_id']} ({user_data['auth_level']})")
            else:
                # Create new user using raw SQL
                db.execute(text("""
                    INSERT INTO controllers (employee_id, name, auth_level, active, section_responsibility, password_hash)
                    VALUES (:employee_id, :name, :auth_level, true, '{}', :password_hash)
                """), {
                    "employee_id": user_data["employee_id"],
                    "name": user_data["name"],
                    "auth_level": user_data["auth_level"],
                    "password_hash": password_hash
                })
                db.commit()
                print(f"✅ Created user {user_data['employee_id']} ({user_data['auth_level']})")
                
        except Exception as e:
            print(f"⚠️  Error creating user {user_data['employee_id']}: {e}")
            db.rollback()
    
    db.close()

def update_existing_users():
    """Update existing users with default password"""
    print("\n🔄 Updating existing users with default passwords...")
    
    db = next(get_db())
    default_password = "railway123"
    
    try:
        # Get all users without password using raw SQL
        result = db.execute(text("""
            SELECT employee_id, name 
            FROM controllers 
            WHERE password_hash IS NULL OR password_hash = ''
        """))
        
        users = result.fetchall()
        password_hash = get_password_hash(default_password)
        
        for user in users:
            db.execute(text("""
                UPDATE controllers 
                SET password_hash = :password_hash 
                WHERE employee_id = :employee_id
            """), {"password_hash": password_hash, "employee_id": user[0]})
            print(f"✅ Set default password for {user[0]} ({user[1]})")
        
        db.commit()
        
        if users:
            print(f"\nℹ️  Default password for existing users: '{default_password}'")
        else:
            print("ℹ️  No users needed password updates")
            
    except Exception as e:
        print(f"⚠️  Error updating users: {e}")
        db.rollback()
    finally:
        db.close()

def print_credentials():
    """Print all credentials"""
    print("\n" + "="*60)
    print("🔐 LOGIN CREDENTIALS")
    print("="*60)
    print("\nTest Users:")
    print("  📱 Employee ID: ADMIN001")
    print("     Password:    admin123")
    print("     Role:        ADMIN")
    print()
    print("  📱 Employee ID: MANAGER001")
    print("     Password:    manager123")
    print("     Role:        MANAGER")
    print()
    print("  📱 Employee ID: OPERATOR001")
    print("     Password:    operator123")
    print("     Role:        OPERATOR")
    print()
    print("Existing Users (from database):")
    print("  📱 Employee ID: CTR001, CTR002, CTR003, CTR004, CTR005")
    print("     Password:    railway123")
    print("     Roles:       Various")
    print()
    print("="*60)
    print("🌐 Login at: http://localhost:5173/login")
    print("="*60)

if __name__ == "__main__":
    print("🚀 Setting up authentication for Railway Traffic Management System\n")
    
    # Step 1: Add password column
    if not add_password_column():
        print("❌ Failed to add password column")
        sys.exit(1)
    
    # Step 2: Create test users
    create_test_users()
    
    # Step 3: Update existing users
    update_existing_users()
    
    # Step 4: Print credentials
    print_credentials()
    
    print("\n✅ Authentication setup complete!")
