# migrate_google_uid.py
import sqlite3
from database import DB_PATH

def migrate_add_google_uid():
    """Add google_uid column to users table for Google Sign-In"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("❌ Users table doesn't exist!")
            conn.close()
            return False
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Existing columns: {columns}")
        
        # Add google_uid column
        if 'google_uid' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN google_uid TEXT")
            print("✅ Added google_uid column")
        else:
            print("✅ google_uid column already exists")
        
        conn.commit()
        conn.close()
        print("✅ Migration complete!")
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    migrate_add_google_uid()