# database.py
import sqlite3
import os

# Database path
DB_PATH = "store_management.db"

def init_database():
    """Initialize the database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_premium INTEGER DEFAULT 0,
            premium_plan TEXT,
            stripe_customer_id TEXT,
            license_key TEXT,
            license_expiry TEXT,
            trial_mode INTEGER DEFAULT 0,
            trial_end_date TEXT,
            avatar_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create materials table (no image_path)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            item_code TEXT UNIQUE,
            quantity INTEGER DEFAULT 0,
            size TEXT,
            length REAL,
            quality TEXT,
            location_ids TEXT,
            colors TEXT,
            notes TEXT,
            barcode_value TEXT UNIQUE,
            barcode_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create accessories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accessories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            item_code TEXT UNIQUE,
            quantity INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            quality TEXT,
            location TEXT,
            notes TEXT,
            barcode_value TEXT UNIQUE,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create activity logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            item_type TEXT,
            item_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create backups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            file_size TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin user if not exists
    cursor.execute("SELECT * FROM users WHERE email = ?", ("admin@store.com",))
    if not cursor.fetchone():
        import hashlib
        default_password = "admin123"
        password_hash = hashlib.sha256(default_password.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, is_premium)
            VALUES (?, ?, ?, ?, ?)
        ''', ("Administrator", "admin@store.com", password_hash, "admin", 1))
        print("Default admin user created: admin@store.com / admin123")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

def backup_database():
    """Create a backup of the database"""
    import shutil
    from datetime import datetime
    
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)
    
    shutil.copy2(DB_PATH, backup_path)
    
    # Log the backup
    conn = get_db_connection()
    cursor = conn.cursor()
    file_size = os.path.getsize(backup_path)
    
    if file_size < 1024:
        size_str = f"{file_size} B"
    elif file_size < 1024 * 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / (1024 * 1024):.1f} MB"
    
    cursor.execute("INSERT INTO backups (filename, file_size) VALUES (?, ?)", (backup_name, size_str))
    conn.commit()
    conn.close()
    
    return backup_path

def restore_database(backup_file):
    """Restore database from backup"""
    import shutil
    
    backup_path = os.path.join("backups", backup_file)
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, DB_PATH)
        return True
    return False

def get_database_size():
    """Get database file size"""
    if os.path.exists(DB_PATH):
        size = os.path.getsize(DB_PATH)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    return "N/A"

def get_backup_list():
    """Get list of backups"""
    import os
    from datetime import datetime
    
    backups = []
    backup_dir = "backups"
    
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.endswith('.db'):
                file_path = os.path.join(backup_dir, file)
                file_size = os.path.getsize(file_path)
                file_time = os.path.getmtime(file_path)
                
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                date_str = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
                
                backups.append({
                    'filename': file,
                    'size': size_str,
                    'date': date_str,
                    'path': file_path
                })
    
    backups.sort(key=lambda x: x['date'], reverse=True)
    return backups

def delete_backup(backup_file):
    """Delete a backup file"""
    import os
    backup_path = os.path.join("backups", backup_file)
    if os.path.exists(backup_path):
        os.remove(backup_path)
        
        # Remove from database log
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM backups WHERE filename = ?", (backup_file,))
        conn.commit()
        conn.close()
        
        return True
    return False

def reset_database():
    """Reset database (delete all data)"""
    import os
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        init_database()
        return True
    return False

def execute_query(query, params=None):
    """Execute a query and return results"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            conn.close()
            return results
        else:
            conn.commit()
            last_id = cursor.lastrowid
            conn.close()
            return last_id
    except Exception as e:
        print(f"Database error: {e}")
        conn.close()
        return None

# Run initialization when module is imported
if __name__ == "__main__":
    init_database()