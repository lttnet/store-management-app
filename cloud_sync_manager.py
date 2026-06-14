# cloud_sync_manager.py - Updated to use Firestore
import sqlite3
from database import DB_PATH
from datetime import datetime
import json
import os

# Import Firestore sync
try:
    from firestore_sync import firestore_sync
    USE_FIRESTORE = firestore_sync.is_ready()
except:
    USE_FIRESTORE = False
    print("⚠️ Firestore not available, using local files")

class CloudSyncManager:
    
    @staticmethod
    def _get_cloud_data_file(company_id):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cloud_dir = os.path.join(base_dir, "cloud_data")
        if not os.path.exists(cloud_dir):
            os.makedirs(cloud_dir)
        return os.path.join(cloud_dir, f"company_{company_id}.json")
    
    @staticmethod
    def sync_users_to_cloud(company_id):
        """Sync users to REAL Firestore cloud"""
        try:
            # Get local users
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, password_hash, role, company_id, created_at FROM users WHERE company_id = ?", (company_id,))
            local_users = cursor.fetchall()
            conn.close()
            
            users_list = [dict(u) for u in local_users]
            print(f"📤 Uploading {len(users_list)} users to cloud...")
            
            # Use Firestore (real cloud)
            if USE_FIRESTORE:
                result = firestore_sync.sync_users_to_firestore(company_id, users_list)
                if result:
                    print(f"✅ Synced {len(users_list)} users to Firestore Cloud!")
                return result
            else:
                # Fallback to local JSON
                cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
                if os.path.exists(cloud_file):
                    with open(cloud_file, 'r') as f:
                        cloud_data = json.load(f)
                else:
                    cloud_data = {'company_id': company_id, 'materials': [], 'accessories': [], 'users': []}
                
                cloud_data['users'] = users_list
                cloud_data['last_sync'] = datetime.now().isoformat()
                
                with open(cloud_file, 'w') as f:
                    json.dump(cloud_data, f, indent=2)
                
                print(f"✅ Synced {len(users_list)} users to local cloud file")
                return True
        except Exception as e:
            print(f"Sync users error: {e}")
            return False
    
    @staticmethod
    def download_users_from_cloud(company_id):
        """Download users from REAL Firestore cloud"""
        try:
            if USE_FIRESTORE:
                # Get from Firestore
                cloud_users = firestore_sync.get_users_from_firestore(company_id)
            else:
                # Fallback to local JSON
                cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
                if not os.path.exists(cloud_file):
                    return False
                with open(cloud_file, 'r') as f:
                    cloud_data = json.load(f)
                cloud_users = cloud_data.get('users', [])
            
            if not cloud_users:
                return False
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get existing local user IDs
            cursor.execute("SELECT id FROM users WHERE company_id = ?", (company_id,))
            local_ids = {row[0] for row in cursor.fetchall()}
            
            cloud_ids = {u.get('id') for u in cloud_users}
            
            # Delete users that are not in cloud (local-only users)
            to_delete = local_ids - cloud_ids
            deleted_count = 0
            for user_id in to_delete:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                deleted_count += 1
            
            # Add or update users
            added = 0
            updated = 0
            
            for user in cloud_users:
                user_id = user.get('id')
                
                if user_id in local_ids:
                    # Update existing user
                    cursor.execute('''
                        UPDATE users SET name = ?, email = ?, role = ?, company_id = ?
                        WHERE id = ?
                    ''', (user.get('name'), user.get('email'), user.get('role'), company_id, user_id))
                    updated += 1
                else:
                    # Insert new user
                    import hashlib
                    default_password = hashlib.sha256("temp123".encode()).hexdigest()
                    cursor.execute('''
                        INSERT INTO users (id, name, email, password_hash, role, company_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, user.get('name'), user.get('email'), default_password, 
                          user.get('role', 'user'), company_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    added += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ Downloaded {len(cloud_users)} users from Firestore Cloud")
            if added:
                print(f"   + Added: {added} users")
            if updated:
                print(f"   ~ Updated: {updated} users")
            if deleted_count:
                print(f"   - Deleted: {deleted_count} users")
            
            return True
        except Exception as e:
            print(f"Download users error: {e}")
            return False
    
    @staticmethod
    def full_sync_to_cloud(company_id):
        """Full upload to cloud"""
        return CloudSyncManager.sync_users_to_cloud(company_id)
    
    @staticmethod
    def full_sync_from_cloud(company_id):
        """Full download from cloud"""
        return CloudSyncManager.download_users_from_cloud(company_id)