# managers/user_manager.py
import sqlite3
import hashlib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DB_PATH

class UserManager:
    
    @classmethod
    def get_connection(cls):
        """Get database connection with row_factory"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @classmethod
    def _row_to_dict(cls, row):
        """Convert sqlite3.Row to dictionary"""
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}
    
    @classmethod
    def authenticate(cls, email, password):
        """Authenticate user by email and password"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password_hash = ?", (email, password_hash))
        row = cursor.fetchone()
        conn.close()
        
        return cls._row_to_dict(row)
    
    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return cls._row_to_dict(row)
    
    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        return cls._row_to_dict(row)
    
    @classmethod
    def get_all(cls):
        """Get all users"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append(cls._row_to_dict(row))
        return users
    
    @classmethod
    def create(cls, name, email, password, role='user'):
        """Create a new user"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (name, email, password_hash, role))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    @classmethod
    def update(cls, user_id, data):
        """Update user information"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        try:
            set_clause = []
            values = []
            
            allowed_fields = ['name', 'email', 'role', 'is_premium', 'premium_plan', 
                             'license_key', 'license_expiry', 'trial_mode', 'trial_end_date', 'avatar_path']
            
            for field in allowed_fields:
                if field in data:
                    set_clause.append(f"{field} = ?")
                    values.append(data[field])
            
            if not set_clause:
                return False
            
            set_clause.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(set_clause)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
        finally:
            conn.close()
    
    @classmethod
    def delete(cls, email):
        """Delete user by email"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success