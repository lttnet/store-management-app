import sqlite3
import os
from datetime import datetime

DB_PATH = "store_management.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create materials table with category
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            quantity INTEGER DEFAULT 0,
            quality TEXT DEFAULT 'New',
            location_ids TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # IMPORTANT: Force add category column if missing
    try:
        cursor.execute("ALTER TABLE materials ADD COLUMN category TEXT DEFAULT 'Uncategorized'")
    except:
        pass  # Column already exists
    
    # Create admin user
    import hashlib
    admin_password = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (id, name, email, password_hash, role)
        VALUES (1, 'Administrator', 'admin@store.com', ?, 'admin')
    ''', (admin_password,))
    
    conn.commit()
    conn.close()

class MaterialManager:
    @staticmethod
    def create(data):
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Ensure category column exists
        try:
            cursor.execute("ALTER TABLE materials ADD COLUMN category TEXT DEFAULT 'Uncategorized'")
        except:
            pass
        
        cursor.execute('''
            INSERT INTO materials (name, category, quantity, quality, location_ids, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name', ''),
            data.get('category', 'Uncategorized'),
            data.get('quantity', 0),
            data.get('quality', 'New'),
            data.get('location_ids', ''),
            current_time,
            current_time
        ))
        conn.commit()
        material_id = cursor.lastrowid
        conn.close()
        return {'id': material_id}
    
    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials ORDER BY id DESC")
        results = cursor.fetchall()
        conn.close()
        return results
    
    @staticmethod
    def get_by_id(material_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def update(material_id, data):
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            UPDATE materials 
            SET name = ?, category = ?, quantity = ?, quality = ?, location_ids = ?, updated_at = ?
            WHERE id = ?
        ''', (
            data.get('name', ''),
            data.get('category', 'Uncategorized'),
            data.get('quantity', 0),
            data.get('quality', 'New'),
            data.get('location_ids', ''),
            current_time,
            material_id
        ))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    @staticmethod
    def delete(material_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

class UserManager:
    @staticmethod
    def authenticate(email, password):
        import hashlib
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password_hash = ?",
            (email, password_hash)
        )
        result = cursor.fetchone()
        conn.close()
        return result
