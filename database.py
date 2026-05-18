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
    
    # Users table
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
    
    # Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT '📦',
            color TEXT DEFAULT '#1976D2',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Materials table with full fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER DEFAULT 8,
            quantity INTEGER DEFAULT 0,
            quality TEXT DEFAULT 'New',
            location_ids TEXT,
            size TEXT,
            length REAL,
            colors TEXT,
            notes TEXT,
            barcode_value TEXT UNIQUE,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')
    
    # Insert default categories
    default_categories = [
        (1, "Raw Material", "📦", "#1976D2"),
        (2, "Hardware", "🔩", "#757575"),
        (3, "Tools", "🔧", "#FF9800"),
        (4, "Electrical", "⚡", "#FFC107"),
        (5, "Plumbing", "💧", "#00BCD4"),
        (6, "Wood", "🪵", "#8D6E63"),
        (7, "Metal", "⚙️", "#9E9E9E"),
        (8, "Other", "📁", "#607D8B"),
    ]
    
    for cat_id, name, icon, color in default_categories:
        cursor.execute('''
            INSERT OR IGNORE INTO categories (id, name, icon, color)
            VALUES (?, ?, ?, ?)
        ''', (cat_id, name, icon, color))
    
    # Create admin user
    import hashlib
    admin_password = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (id, name, email, password_hash, role)
        VALUES (1, 'Administrator', 'admin@store.com', ?, 'admin')
    ''', (admin_password,))
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

class MaterialManager:
    @staticmethod
    def create(data):
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO materials (
                name, category_id, quantity, quality, location_ids, 
                size, length, colors, notes, barcode_value, image_path, 
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name', ''),
            data.get('category_id', 8),
            data.get('quantity', 0),
            data.get('quality', 'New'),
            data.get('location_ids', ''),
            data.get('size', ''),
            data.get('length', None),
            data.get('colors', ''),
            data.get('notes', ''),
            data.get('barcode_value', ''),
            data.get('image_path', ''),
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
        cursor.execute('''
            SELECT m.*, c.name as category_name, c.icon as category_icon
            FROM materials m
            LEFT JOIN categories c ON m.category_id = c.id
            ORDER BY m.id DESC
        ''')
        results = cursor.fetchall()
        conn.close()
        return results
    
    @staticmethod
    def get_by_id(material_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.*, c.name as category_name, c.icon as category_icon
            FROM materials m
            LEFT JOIN categories c ON m.category_id = c.id
            WHERE m.id = ?
        ''', (material_id,))
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
            SET name = ?, category_id = ?, quantity = ?, quality = ?, location_ids = ?,
                size = ?, length = ?, colors = ?, notes = ?, barcode_value = ?,
                image_path = ?, updated_at = ?
            WHERE id = ?
        ''', (
            data.get('name', ''),
            data.get('category_id', 8),
            data.get('quantity', 0),
            data.get('quality', 'New'),
            data.get('location_ids', ''),
            data.get('size', ''),
            data.get('length', None),
            data.get('colors', ''),
            data.get('notes', ''),
            data.get('barcode_value', ''),
            data.get('image_path', ''),
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
    
    @staticmethod
    def get_all_categories():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        results = cursor.fetchall()
        conn.close()
        return results
    
    @staticmethod
    def add_category(name, icon):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO categories (name, icon)
                VALUES (?, ?)
            ''', (name, icon))
            conn.commit()
            category_id = cursor.lastrowid
            conn.close()
            return category_id
        except sqlite3.IntegrityError:
            conn.close()
            return None

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
