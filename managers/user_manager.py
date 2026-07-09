# managers/user_manager.py
import sqlite3
import hashlib
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH

# Lazy imports to avoid circular references
def get_firebase_api():
    from firebase_client import firebase_api
    return firebase_api

def get_cloud_sync_manager():
    from cloud_sync_manager import CloudSyncManager
    return CloudSyncManager

class UserManager:
    
    @staticmethod
    def get_all():
        """Get all users"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY id DESC")
            users = cursor.fetchall()
            conn.close()
            
            result = []
            for u in users:
                user_dict = dict(u)
                if 'password_hash' in user_dict:
                    del user_dict['password_hash']
                result.append(user_dict)
            return result
        except Exception as e:
            print(f"Get all users error: {e}")
            return []
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                user_dict = dict(user)
                if 'password_hash' in user_dict:
                    del user_dict['password_hash']
                return user_dict
            return None
        except Exception as e:
            print(f"Get user by ID error: {e}")
            return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return dict(user)
            return None
        except Exception as e:
            print(f"Get user by email error: {e}")
            return None
    
    @staticmethod
    def authenticate(email, password):
        """Authenticate user by email and password"""
        try:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE email = ? AND password_hash = ?",
                (email, hashed_password)
            )
            user = cursor.fetchone()
            conn.close()
            
            if user:
                user_dict = dict(user)
                if 'password_hash' in user_dict:
                    del user_dict['password_hash']
                return user_dict
            return None
        except Exception as e:
            print(f"Authenticate error: {e}")
            return None
    
    @staticmethod
    def create(**kwargs):
        """Create user and sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            company_id = kwargs.get('company_id', 1)
            password = kwargs.get('password', 'changeme')
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                kwargs.get('name'),
                kwargs.get('email'),
                hashed_password,
                kwargs.get('role', 'user'),
                company_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # AUTO-SYNC: Sync immediately in background
            try:
                firebase_api = get_firebase_api()
                if firebase_api.is_ready():
                    import threading
                    def sync():
                        try:
                            CloudSyncManager = get_cloud_sync_manager()
                            CloudSyncManager.sync_users_to_cloud(company_id)
                        except Exception as e:
                            print(f"[AUTO-SYNC] Error: {e}")
                    threading.Thread(target=sync, daemon=True).start()
            except Exception as e:
                print(f"Auto-sync setup error: {e}")
            
            return {'id': user_id, 'name': kwargs.get('name'), 'email': kwargs.get('email')}
            
        except sqlite3.IntegrityError:
            print(f"User with email {kwargs.get('email')} already exists")
            return None
        except Exception as e:
            print(f"Create user error: {e}")
            return None
    
    @staticmethod
    def update(user_id, data):
        """Update user and sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            company_id = result[0]
            
            set_clause = []
            values = []
            
            for key, value in data.items():
                if key != 'id':
                    set_clause.append(f"{key} = ?")
                    values.append(value)
            
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(set_clause)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            
            # Get the updated user data
            cursor.execute("SELECT id, name, email, role, company_id FROM users WHERE id = ?", (user_id,))
            updated_user = cursor.fetchone()
            conn.close()
            
            if updated_user:
                # AUTO-SYNC: Sync immediately in background
                try:
                    firebase_api = get_firebase_api()
                    if firebase_api.is_ready():
                        import threading
                        def sync():
                            try:
                                CloudSyncManager = get_cloud_sync_manager()
                                CloudSyncManager.sync_users_to_cloud(company_id)
                            except Exception as e:
                                print(f"[AUTO-SYNC] Error: {e}")
                        threading.Thread(target=sync, daemon=True).start()
                except Exception as e:
                    print(f"Auto-sync setup error: {e}")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Update user error: {e}")
            return False
    
    @staticmethod
    def delete(user_id):
        """Delete user and sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            company_id = result[0]
            
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            
            # AUTO-SYNC: Delete from cloud
            try:
                firebase_api = get_firebase_api()
                if firebase_api.is_ready():
                    import threading
                    def sync():
                        try:
                            CloudSyncManager = get_cloud_sync_manager()
                            CloudSyncManager.sync_users_to_cloud(company_id)
                        except Exception as e:
                            print(f"[AUTO-SYNC] Error: {e}")
                    threading.Thread(target=sync, daemon=True).start()
            except Exception as e:
                print(f"Auto-sync setup error: {e}")
            
            return True
            
        except Exception as e:
            print(f"Delete user error: {e}")
            return False
