# managers/user_manager.py
import sqlite3
import hashlib
import sys
import os
from datetime import datetime

# Fix import paths - go up one level to parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from parent directory (NO circular imports)
from database import DB_PATH
from firebase_client import firebase_api
from cloud_sync_manager import CloudSyncManager

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
            
            if firebase_api.is_ready():
                import threading
                def sync():
                    try:
                        CloudSyncManager.sync_users_to_cloud(company_id)
                        print(f"✅ User {user_id} synced to cloud")
                    except Exception as e:
                        print(f"Background sync error: {e}")
                threading.Thread(target=sync, daemon=True).start()
            
            return {'id': user_id, 'name': kwargs.get('name'), 'email': kwargs.get('email')}
            
        except sqlite3.IntegrityError:
            print(f"User with email {kwargs.get('email')} already exists")
            return None
        except Exception as e:
            print(f"Create user error: {e}")
            return None
    
# managers/user_manager.py

    @staticmethod
    def update(user_id, data):
        """Update user and sync to cloud - FIXED"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get company_id first
            cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            company_id = result[0]
            
            # Build update query
            set_clause = []
            values = []
            
            for key, value in data.items():
                if key != 'id':
                    set_clause.append(f"{key} = ?")
                    values.append(value)
            
            # Add updated_at timestamp
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
                # Sync to cloud with the updated data
                if firebase_api.is_ready():
                    import threading
                    def sync():
                        try:
                            # Convert to dict and sync
                            user_dict = dict(updated_user)
                            success = firebase_api.sync_user(company_id, user_dict)
                            if success:
                                print(f"✅ User {user_id} updated and synced to cloud")
                            else:
                                print(f"⚠️ User {user_id} updated locally but failed to sync to cloud")
                        except Exception as e:
                            print(f"Background sync error: {e}")
                    threading.Thread(target=sync, daemon=True).start()
                
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
            
            if firebase_api.is_ready():
                import threading
                def sync():
                    try:
                        CloudSyncManager.sync_users_to_cloud(company_id)
                        print(f"✅ User {user_id} deleted from cloud")
                    except Exception as e:
                        print(f"Background sync error: {e}")
                threading.Thread(target=sync, daemon=True).start()
            
            return True
            
        except Exception as e:
            print(f"Delete user error: {e}")
            return False
