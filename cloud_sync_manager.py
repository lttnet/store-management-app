# cloud_sync_manager.py
import sqlite3
import json
import os
from datetime import datetime

# Get database path
def get_db_path():
    """Get database path that works on both desktop and mobile"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "store_management.db")

class CloudSyncManager:
    
    @staticmethod
    def _get_cloud_data_file(company_id):
        """Get cloud data file path"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cloud_dir = os.path.join(base_dir, "cloud_data")
        if not os.path.exists(cloud_dir):
            os.makedirs(cloud_dir, exist_ok=True)
        return os.path.join(cloud_dir, f"company_{company_id}.json")
    
    @staticmethod
    def _get_connection():
        """Get database connection"""
        db_path = get_db_path()
        return sqlite3.connect(db_path)
    
    # ============ USERS SYNC ============
    @staticmethod
    def sync_users_to_cloud(company_id):
        """Sync users to cloud"""
        try:
            conn = CloudSyncManager._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get users for this company
            cursor.execute("SELECT id, name, email, password_hash, role, company_id, created_at FROM users WHERE company_id = ?", (company_id,))
            users = cursor.fetchall()
            conn.close()
            
            users_list = [dict(u) for u in users]
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            
            # Load existing cloud data or create new
            if os.path.exists(cloud_file):
                with open(cloud_file, 'r', encoding='utf-8') as f:
                    cloud_data = json.load(f)
            else:
                cloud_data = {'company_id': company_id, 'materials': [], 'accessories': [], 'users': []}
            
            cloud_data['users'] = users_list
            cloud_data['last_sync'] = datetime.now().isoformat()
            
            with open(cloud_file, 'w', encoding='utf-8') as f:
                json.dump(cloud_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Synced {len(users_list)} users to cloud")
            return True
        except Exception as e:
            print(f"Sync users error: {e}")
            return False
    
    @staticmethod
    def download_users_from_cloud(company_id):
        """Download users from cloud"""
        try:
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            if not os.path.exists(cloud_file):
                return False
            
            with open(cloud_file, 'r', encoding='utf-8') as f:
                cloud_data = json.load(f)
            
            users = cloud_data.get('users', [])
            if not users:
                return False
            
            conn = CloudSyncManager._get_connection()
            cursor = conn.cursor()
            
            # Get existing users
            cursor.execute("SELECT id FROM users")
            existing_ids = {row[0] for row in cursor.fetchall()}
            
            for user in users:
                user_id = user.get('id')
                if user_id in existing_ids:
                    # Update existing
                    cursor.execute('''UPDATE users SET name=?, email=?, role=?, company_id=? WHERE id=?''',
                                 (user.get('name'), user.get('email'), user.get('role'), company_id, user_id))
                else:
                    # Insert new
                    import hashlib
                    default_password = hashlib.sha256("temp123".encode()).hexdigest()
                    cursor.execute('''INSERT INTO users (id, name, email, password_hash, role, company_id, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                 (user_id, user.get('name'), user.get('email'), default_password,
                                  user.get('role', 'user'), company_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            print(f"✅ Downloaded {len(users)} users from cloud")
            return True
        except Exception as e:
            print(f"Download users error: {e}")
            return False
    
    # ============ MATERIALS SYNC ============
    @staticmethod
    def sync_materials_to_cloud(company_id):
        """Sync materials to cloud"""
        try:
            conn = CloudSyncManager._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM materials WHERE company_id = ? OR company_id IS NULL", (company_id,))
            materials = cursor.fetchall()
            conn.close()
            
            materials_list = [dict(m) for m in materials]
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            
            if os.path.exists(cloud_file):
                with open(cloud_file, 'r', encoding='utf-8') as f:
                    cloud_data = json.load(f)
            else:
                cloud_data = {'company_id': company_id, 'materials': [], 'accessories': [], 'users': []}
            
            cloud_data['materials'] = materials_list
            cloud_data['last_sync'] = datetime.now().isoformat()
            
            with open(cloud_file, 'w', encoding='utf-8') as f:
                json.dump(cloud_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Synced {len(materials_list)} materials to cloud")
            return True
        except Exception as e:
            print(f"Sync materials error: {e}")
            return False
    
    @staticmethod
    def download_materials_from_cloud(company_id):
        """Download materials from cloud"""
        try:
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            if not os.path.exists(cloud_file):
                return False
            
            with open(cloud_file, 'r', encoding='utf-8') as f:
                cloud_data = json.load(f)
            
            materials = cloud_data.get('materials', [])
            if not materials:
                return False
            
            conn = CloudSyncManager._get_connection()
            cursor = conn.cursor()
            
            for material in materials:
                cursor.execute('''INSERT OR REPLACE INTO materials 
                    (id, name, category_id, quantity, quality, location_ids, size, length, colors, notes, image_path, barcode_value, company_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (material.get('id'), material.get('name'), material.get('category_id'),
                     material.get('quantity'), material.get('quality'), material.get('location_ids'),
                     material.get('size'), material.get('length'), material.get('colors'),
                     material.get('notes'), material.get('image_path'), material.get('barcode_value'),
                     company_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            print(f"✅ Downloaded {len(materials)} materials from cloud")
            return True
        except Exception as e:
            print(f"Download materials error: {e}")
            return False
    
    # ============ ACCESSORIES SYNC ============
    @staticmethod
    def sync_accessories_to_cloud(company_id):
        """Sync accessories to cloud"""
        try:
            conn = CloudSyncManager._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM accessories WHERE company_id = ? OR company_id IS NULL", (company_id,))
            accessories = cursor.fetchall()
            conn.close()
            
            accessories_list = [dict(a) for a in accessories]
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            
            if os.path.exists(cloud_file):
                with open(cloud_file, 'r', encoding='utf-8') as f:
                    cloud_data = json.load(f)
            else:
                cloud_data = {'company_id': company_id, 'materials': [], 'accessories': [], 'users': []}
            
            cloud_data['accessories'] = accessories_list
            cloud_data['last_sync'] = datetime.now().isoformat()
            
            with open(cloud_file, 'w', encoding='utf-8') as f:
                json.dump(cloud_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Synced {len(accessories_list)} accessories to cloud")
            return True
        except Exception as e:
            print(f"Sync accessories error: {e}")
            return False
    
    @staticmethod
    def download_accessories_from_cloud(company_id):
        """Download accessories from cloud"""
        try:
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            if not os.path.exists(cloud_file):
                return False
            
            with open(cloud_file, 'r', encoding='utf-8') as f:
                cloud_data = json.load(f)
            
            accessories = cloud_data.get('accessories', [])
            if not accessories:
                return False
            
            conn = CloudSyncManager._get_connection()
            cursor = conn.cursor()
            
            for accessory in accessories:
                cursor.execute('''INSERT OR REPLACE INTO accessories 
                    (id, name, category_id, quantity, price, quality, location, notes, image_path, barcode_value, company_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (accessory.get('id'), accessory.get('name'), accessory.get('category_id'),
                     accessory.get('quantity'), accessory.get('price'), accessory.get('quality'),
                     accessory.get('location'), accessory.get('notes'), accessory.get('image_path'),
                     accessory.get('barcode_value'), company_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            print(f"✅ Downloaded {len(accessories)} accessories from cloud")
            return True
        except Exception as e:
            print(f"Download accessories error: {e}")
            return False
    
    # ============ FULL SYNC ============
    @staticmethod
    def full_sync_to_cloud(company_id):
        """Full upload to cloud"""
        print(f"🔄 Uploading data for company {company_id}...")
        success1 = CloudSyncManager.sync_users_to_cloud(company_id)
        success2 = CloudSyncManager.sync_materials_to_cloud(company_id)
        success3 = CloudSyncManager.sync_accessories_to_cloud(company_id)
        return success1 or success2 or success3
    
    @staticmethod
    def full_sync_from_cloud(company_id):
        """Full download from cloud"""
        print(f"🔄 Downloading data for company {company_id}...")
        success1 = CloudSyncManager.download_users_from_cloud(company_id)
        success2 = CloudSyncManager.download_materials_from_cloud(company_id)
        success3 = CloudSyncManager.download_accessories_from_cloud(company_id)
        return success1 or success2 or success3
    
    @staticmethod
    def get_sync_status(company_id):
        """Get sync status"""
        cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
        if os.path.exists(cloud_file):
            with open(cloud_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                'last_sync': data.get('last_sync', 'Never'),
                'materials_count': len(data.get('materials', [])),
                'accessories_count': len(data.get('accessories', [])),
                'users_count': len(data.get('users', []))
            }
        return {
            'last_sync': 'Never',
            'materials_count': 0,
            'accessories_count': 0,
            'users_count': 0
        }

# Test on import
print("✅ CloudSyncManager loaded successfully")
