# managers/user_manager.py

import sqlite3
import hashlib
import sys
import os
from datetime import datetime

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from database import DB_PATH
except ImportError:
    DB_PATH = os.path.join(parent_dir, "store_management.db")

class UserManager:
    
    @staticmethod
    def _auto_sync(company_id):
        """Auto-sync users to cloud"""
        try:
            import threading
            try:
                from main import CloudSyncManager
                threading.Thread(
                    target=CloudSyncManager.sync_users_to_cloud,
                    args=(company_id,),
                    daemon=True
                ).start()
                print(f"🔄 Auto-sync triggered for users (company: {company_id})")
            except ImportError:
                print("⚠️ CloudSyncManager not available")
        except Exception as e:
            print(f"Auto-sync error: {e}")
    
    @staticmethod
    def create(name, email, password, role='user', company_id=1):
        """Create user with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return False
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, hashed_password, role, company_id, current_time))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ User created: {name} ({email})")
            
            # ===== AUTO-SYNC TO CLOUD =====
            UserManager._auto_sync(company_id)
            
            return user_id
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
# managers/user_manager.py

    @staticmethod
    def delete(user_id):
        """Delete user with auto-sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
            name_result = cursor.fetchone()
            user_name = name_result[0] if name_result else "Unknown"
            
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            
            print(f"✅ User deleted locally: ID={user_id}, Name={user_name}")
            
            # ===== FORCE AUTO-SYNC TO CLOUD =====
            def sync_deletion():
                try:
                    import threading
                    from main import CloudSyncManager
                    CloudSyncManager.sync_users_to_cloud(company_id)
                    print(f"🔄 Deletion synced to cloud for user {user_id}")
                except Exception as e:
                    print(f"⚠️ Sync error: {e}")
            
            import threading
            threading.Thread(target=sync_deletion, daemon=True).start()
            # =========================================
            
            return True
            
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
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
            
            if user:
                print(f"✅ User authenticated: {email}")
                return user
            else:
                print(f"❌ Authentication failed: {email}")
                return None
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    # managers/user_manager.py - Add this method

    @staticmethod
    def get_all(company_id=None):
        """Get all users, optionally filtered by company_id"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if company_id:
                cursor.execute("SELECT * FROM users WHERE company_id = ? ORDER BY name", (company_id,))
            else:
                cursor.execute("SELECT * FROM users ORDER BY name")
            
            users = cursor.fetchall()
            conn.close()
            return users
            
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
