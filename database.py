"""
Database module for Store Management System
"""
import sqlite3
import os

# Get the absolute path to the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "store_management.db")

def init_database():
    """Initialize the database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table with all columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            avatar_path TEXT,
            is_premium INTEGER DEFAULT 0,
            premium_plan TEXT,
            license_key TEXT,
            license_expiry TEXT,
            trial_mode INTEGER DEFAULT 0,
            trial_end_date TEXT,
            guest_mode INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create materials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            category_id INTEGER,
            item_code TEXT UNIQUE,
            quantity INTEGER DEFAULT 0,
            size TEXT,
            length REAL,
            quality TEXT DEFAULT 'New',
            location_ids TEXT,
            colors TEXT,
            notes TEXT,
            barcode_value TEXT UNIQUE,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create accessories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accessories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            category_id INTEGER,
            item_code TEXT UNIQUE,
            quantity INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            quality TEXT DEFAULT 'New',
            location TEXT,
            notes TEXT,
            barcode_value TEXT UNIQUE,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create custom_categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT DEFAULT '📁',
            color TEXT DEFAULT '#1976D2',
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin user if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        import hashlib
        admin_password = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ("Administrator", "admin@store.com", admin_password, "admin"))
        print("✅ Default admin user created: admin@store.com / admin123")
    
    # Add any missing columns to existing users table
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    columns_to_add = {
        'guest_mode': 'INTEGER DEFAULT 0',
        'avatar_path': 'TEXT',
        'trial_mode': 'INTEGER DEFAULT 0',
        'trial_end_date': 'TEXT',
        'is_premium': 'INTEGER DEFAULT 0',
        'premium_plan': 'TEXT',
        'license_key': 'TEXT',
        'license_expiry': 'TEXT'
    }
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"✅ Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")
