"""
Database module for Store Management System
"""
import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store_management.db")

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with all required tables"""
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create materials table with all columns including category
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            item_code TEXT UNIQUE,
            quantity INTEGER DEFAULT 0,
            size TEXT,
            length REAL,
            quality TEXT DEFAULT 'New',
            location_ids TEXT,
            colors TEXT,
            notes TEXT,
            barcode_value TEXT UNIQUE,
            barcode_path TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create accessories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accessories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Uncategorized',
            item_code TEXT UNIQUE,
            quantity INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            quality TEXT DEFAULT 'New',
            location TEXT,
            notes TEXT,
            barcode_value TEXT UNIQUE,
            barcode_path TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create backups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if category column exists, if not add it
    cursor.execute("PRAGMA table_info(materials)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'category' not in columns:
        print("Adding category column to materials table...")
        cursor.execute("ALTER TABLE materials ADD COLUMN category TEXT DEFAULT 'Uncategorized'")
    
    # Check if colors column exists
    if 'colors' not in columns:
        print("Adding colors column to materials table...")
        cursor.execute("ALTER TABLE materials ADD COLUMN colors TEXT")
    
    # Check if notes column exists
    if 'notes' not in columns:
        print("Adding notes column to materials table...")
        cursor.execute("ALTER TABLE materials ADD COLUMN notes TEXT")
    
    # Create default admin user if not exists
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
    """Manager for material operations"""
    
    @staticmethod
    def create(data):
        """Create a new material with category support"""
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Ensure category column exists
            cursor.execute("PRAGMA table_info(materials)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'category' not in columns:
                cursor.execute("ALTER TABLE materials ADD COLUMN category TEXT DEFAULT 'Uncategorized'")
                conn.commit()
            
            # Prepare insert data
            insert_data = {
                'name': data.get('name', ''),
                'category': data.get('category', 'Uncategorized'),
                'quantity': data.get('quantity', 0),
                'quality': data.get('quality', 'New'),
                'location_ids': data.get('location_ids', ''),
                'barcode_value': data.get('barcode_value', ''),
                'created_at': current_time,
                'updated_at': current_time
            }
            
            # Add optional fields if they exist in data
            optional_fields = ['size', 'length', 'colors', 'notes', 'image_path', 'item_code']
            for field in optional_fields:
                if field in data and data.get(field):
                    insert_data[field] = data[field]
            
            # Build INSERT query
            fields = list(insert_data.keys())
            placeholders = ','.join(['?' for _ in fields])
            values = [insert_data[field] for field in fields]
            
            query = f"INSERT INTO materials ({','.join(fields)}) VALUES ({placeholders})"
            
            print(f"DEBUG MaterialManager.create: {query}")
            print(f"DEBUG Values: {values}")
            
            cursor.execute(query, values)
            conn.commit()
            material_id = cursor.lastrowid
            
            conn.close()
            print(f"DEBUG Material created with ID: {material_id}, Category: {insert_data['category']}")
            return {'id': material_id}
            
        except Exception as e:
            print(f"ERROR in MaterialManager.create: {e}")
            import traceback
            traceback.print_exc()
            conn.close()
            return None
    
    @staticmethod
    def get_by_id(material_id):
        """Get material by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def get_all():
        """Get all materials"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials ORDER BY id DESC")
        results = cursor.fetchall()
        conn.close()
        return results
    
    @staticmethod
    def update(material_id, data, user_id=None):
        """Update material"""
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Build update query
            update_fields = []
            values = []
            
            allowed_fields = ['name', 'category', 'quantity', 'size', 'length', 
                            'quality', 'location_ids', 'colors', 'notes', 
                            'barcode_value', 'image_path']
            
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    values.append(data[field])
            
            update_fields.append("updated_at = ?")
            values.append(current_time)
            values.append(material_id)
            
            query = f"UPDATE materials SET {','.join(update_fields)} WHERE id = ?"
            
            print(f"DEBUG MaterialManager.update: {query}")
            print(f"DEBUG Values: {values}")
            
            cursor.execute(query, values)
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            
            print(f"DEBUG Update success: {success}")
            return success
            
        except Exception as e:
            print(f"ERROR in MaterialManager.update: {e}")
            conn.close()
            return False
    
    @staticmethod
    def delete(material_id):
        """Delete material"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    @staticmethod
    def get_by_barcode(barcode):
        """Get material by barcode"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE barcode_value = ?", (barcode,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def search(query):
        """Search materials by name or code"""
        conn = get_db_connection()
        cursor = conn.cursor()
        search_term = f"%{query}%"
        cursor.execute(
            "SELECT * FROM materials WHERE name LIKE ? OR item_code LIKE ? OR barcode_value LIKE ?",
            (search_term, search_term, search_term)
        )
        results = cursor.fetchall()
        conn.close()
        return results

class AccessoryManager:
    """Manager for accessory operations"""
    
    @staticmethod
    def create(data):
        """Create a new accessory"""
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT INTO accessories (name, category, item_code, quantity, price, quality, location, notes, barcode_value, image_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name', ''),
                data.get('category', 'Uncategorized'),
                data.get('item_code', ''),
                data.get('quantity', 0),
                data.get('price', 0),
                data.get('quality', 'New'),
                data.get('location', ''),
                data.get('notes', ''),
                data.get('barcode_value', ''),
                data.get('image_path', ''),
                current_time,
                current_time
            ))
            conn.commit()
            accessory_id = cursor.lastrowid
            conn.close()
            return {'id': accessory_id}
        except Exception as e:
            print(f"ERROR in AccessoryManager.create: {e}")
            conn.close()
            return None
    
    @staticmethod
    def get_by_id(accessory_id):
        """Get accessory by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def get_all():
        """Get all accessories"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories ORDER BY id DESC")
        results = cursor.fetchall()
        conn.close()
        return results
    
    @staticmethod
    def update(accessory_id, data):
        """Update accessory"""
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            update_fields = []
            values = []
            
            allowed_fields = ['name', 'category', 'quantity', 'price', 'quality', 
                            'location', 'notes', 'barcode_value', 'image_path']
            
            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    values.append(data[field])
            
            update_fields.append("updated_at = ?")
            values.append(current_time)
            values.append(accessory_id)
            
            query = f"UPDATE accessories SET {','.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            print(f"ERROR in AccessoryManager.update: {e}")
            conn.close()
            return False
    
    @staticmethod
    def delete(accessory_id):
        """Delete accessory"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accessories WHERE id = ?", (accessory_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    @staticmethod
    def get_by_barcode(barcode):
        """Get accessory by barcode"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE barcode_value = ?", (barcode,))
        result = cursor.fetchone()
        conn.close()
        return result

class UserManager:
    """Manager for user operations"""
    
    @staticmethod
    def create(name, email, password, role='user'):
        """Create a new user"""
        import hashlib
        
        conn = get_db_connection()
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, password_hash, role, current_time, current_time))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return {'id': user_id}
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    @staticmethod
    def authenticate(email, password):
        """Authenticate user"""
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
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role, created_at FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def get_all():
        """Get all users"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id")
        results = cursor.fetchall()
        conn.close()
        return results
    
    @staticmethod
    def update(user_id, data):
        """Update user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            update_fields = []
            values = []
            
            if 'name' in data:
                update_fields.append("name = ?")
                values.append(data['name'])
            if 'role' in data:
                update_fields.append("role = ?")
                values.append(data['role'])
            
            update_fields.append("updated_at = ?")
            values.append(current_time)
            values.append(user_id)
            
            query = f"UPDATE users SET {','.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            print(f"ERROR in UserManager.update: {e}")
            conn.close()
            return False
    
    @staticmethod
    def delete(user_id):
        """Delete user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

# Initialize database when module is imported
if __name__ == "__main__":
    init_database()
    print("Database initialized successfully")
