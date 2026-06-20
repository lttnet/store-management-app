# managers/user_manager.py

import sqlite3
import hashlib
from database import DB_PATH
from datetime import datetime

class UserManager:
    
    @staticmethod
    def create(name, email, password, role='user', company_id=1):
        """Create a new user with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return False
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, hashed_password, role, company_id,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            
            # ===== AUTO-SYNC AFTER CREATE =====
            UserManager._auto_sync_users(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    @staticmethod
    def update(user_id, data):
        """Update a user with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get company_id before update
            cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            # Build update query
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id' and key != 'company_id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            # ===== AUTO-SYNC AFTER UPDATE =====
            UserManager._auto_sync_users(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    @staticmethod
    def delete(user_id):
        """Delete a user with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get company_id before delete
            cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            
            # ===== AUTO-SYNC AFTER DELETE =====
            UserManager._auto_sync_users(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    @staticmethod
    def _auto_sync_users(company_id):
        """Internal method to auto-sync users to cloud"""
        try:
            from main import CloudSyncManager
            import threading
            threading.Thread(
                target=CloudSyncManager.sync_users_full_to_cloud,
                args=(company_id,),
                daemon=True
            ).start()
            print(f"🔄 Auto-sync triggered for users (company: {company_id})")
        except Exception as e:
            print(f"Auto-sync error: {e}")
    
    @staticmethod
    def authenticate(email, password):
        """Authenticate a user"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute(
                "SELECT * FROM users WHERE email = ? AND password_hash = ?",
                (email, hashed_password)
            )
            user = cursor.fetchone()
            conn.close()
            
            return user
            
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    @staticmethod
    def get_all():
        """Get all users"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY name")
            users = cursor.fetchall()
            conn.close()
            return users
            
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    @staticmethod
    def get_by_id(user_id):
        """Get a user by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            conn.close()
            return user
            
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
        
