# update_database.py
import sqlite3
from database import DB_PATH

def update_database():
    """Update database schema to add missing columns"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing columns in materials table
    cursor.execute("PRAGMA table_info(materials)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print("Current columns in materials:", columns)
    
    # Add missing columns to materials table (without DEFAULT)
    if 'created_at' not in columns:
        cursor.execute("ALTER TABLE materials ADD COLUMN created_at TIMESTAMP")
        # Update existing rows
        cursor.execute("UPDATE materials SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        print("✅ Added created_at column to materials")
    
    if 'updated_at' not in columns:
        cursor.execute("ALTER TABLE materials ADD COLUMN updated_at TIMESTAMP")
        cursor.execute("UPDATE materials SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        print("✅ Added updated_at column to materials")
    
    # Check existing columns in accessories table
    cursor.execute("PRAGMA table_info(accessories)")
    acc_columns = [col[1] for col in cursor.fetchall()]
    
    print("Current columns in accessories:", acc_columns)
    
    # Add missing columns to accessories table
    if 'created_at' not in acc_columns:
        cursor.execute("ALTER TABLE accessories ADD COLUMN created_at TIMESTAMP")
        cursor.execute("UPDATE accessories SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        print("✅ Added created_at column to accessories")
    
    if 'updated_at' not in acc_columns:
        cursor.execute("ALTER TABLE accessories ADD COLUMN updated_at TIMESTAMP")
        cursor.execute("UPDATE accessories SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        print("✅ Added updated_at column to accessories")
    
    # Check users table
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cursor.fetchall()]
    
    print("Current columns in users:", user_columns)
    
    # Add missing columns to users table
    premium_columns = ['is_premium', 'premium_plan', 'stripe_customer_id', 'license_key', 'license_expiry', 'trial_mode', 'trial_end_date', 'avatar_path']
    
    for col in premium_columns:
        if col not in user_columns:
            if col in ['is_premium', 'trial_mode']:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
            else:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            print(f"✅ Added {col} column to users")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 50)
    print("Database update completed successfully!")
    print("=" * 50)

if __name__ == "__main__":
    update_database()