"""
Add password authentication and create demo users
"""
import sys
import bcrypt
from sqlalchemy import text
from app.db import get_engine

def hash_password(password: str) -> str:
    """Hash a password using bcrypt directly"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def setup_auth():
    """Add password column and create demo users"""
    engine = get_engine()
    
    print("🔐 Setting up authentication...")
    
    with engine.connect() as conn:
        # Add password_hash column if it doesn't exist
        try:
            conn.execute(text("""
                ALTER TABLE controllers 
                ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)
            """))
            conn.commit()
            print("✅ Password column added to controllers table")
        except Exception as e:
            print(f"⚠️  Column may already exist: {e}")
        
        # Update existing users with demo passwords
        demo_users = [
            ('CTR001', 'Alice Johnson', 'admin123'),  # SUPERVISOR
            ('CTR002', 'Bob Smith', 'operator123'),   # OPERATOR
            ('CTR003', 'Carol Davis', 'manager123'),  # MANAGER
            ('CTR004', 'David Wilson', 'operator123'), # OPERATOR
            ('CTR005', 'Eva Martinez', 'admin123'),   # ADMIN
        ]
        
        for employee_id, name, password in demo_users:
            try:
                # Check if user exists
                result = conn.execute(
                    text("SELECT id FROM controllers WHERE employee_id = :emp_id"),
                    {"emp_id": employee_id}
                )
                user = result.fetchone()
                
                if user:
                    # Update password
                    hashed = hash_password(password)
                    conn.execute(
                        text("""
                            UPDATE controllers 
                            SET password_hash = :pwd_hash 
                            WHERE employee_id = :emp_id
                        """),
                        {"pwd_hash": hashed, "emp_id": employee_id}
                    )
                    conn.commit()
                    print(f"✅ Updated password for {employee_id} ({name})")
                else:
                    print(f"⚠️  User {employee_id} not found")
            except Exception as e:
                print(f"❌ Error updating {employee_id}: {e}")
        
        # Create a special demo user
        try:
            result = conn.execute(
                text("SELECT id FROM controllers WHERE employee_id = 'DEMO001'")
            )
            if not result.fetchone():
                hashed = hash_password('demo123')
                conn.execute(text("""
                    INSERT INTO controllers 
                    (name, employee_id, password_hash, auth_level, active, section_responsibility, created_at, updated_at)
                    VALUES 
                    (:name, :emp_id, :pwd_hash, :auth_level, :active, :sections, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """), {
                    "name": "Demo User",
                    "emp_id": "DEMO001",
                    "pwd_hash": hashed,
                    "auth_level": "ADMIN",
                    "active": True,
                    "sections": []
                })
                conn.commit()
                print("✅ Created demo user: DEMO001 / demo123")
        except Exception as e:
            print(f"⚠️  Demo user creation: {e}")
    
    print("\n" + "="*60)
    print("🎉 Authentication setup complete!")
    print("="*60)
    print("\n📝 Demo Login Credentials:\n")
    print("  Employee ID: DEMO001")
    print("  Password:    demo123")
    print("  Role:        ADMIN\n")
    print("  OR\n")
    print("  Employee ID: CTR005")
    print("  Password:    admin123")
    print("  Role:        ADMIN (Eva Martinez)\n")
    print("  Employee ID: CTR003")
    print("  Password:    manager123")
    print("  Role:        MANAGER (Carol Davis)\n")
    print("  Employee ID: CTR002")
    print("  Password:    operator123")
    print("  Role:        OPERATOR (Bob Smith)\n")
    print("="*60)

if __name__ == "__main__":
    try:
        setup_auth()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
