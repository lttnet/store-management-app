# cloud_sync_manager.py
import sqlite3
import json
import os
from datetime import datetime
from database import DB_PATH

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
        """Sync users to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, password_hash, role, company_id, created_at FROM users WHERE company_id = ?", (company_id,))
            users = cursor.fetchall()
            conn.close()
            
            users_list = [dict(u) for u in users]
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
            
            print(f"✅ Company {company_id}: Synced {len(users_list)} users to cloud")
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
            
            with open(cloud_file, 'r') as f:
                cloud_data = json.load(f)
            
            users = cloud_data.get('users', [])
            if not users:
                return False
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get existing local user IDs
            cursor.execute("SELECT id FROM users WHERE company_id = ?", (company_id,))
            local_ids = {row[0] for row in cursor.fetchall()}
            
            cloud_ids = {u.get('id') for u in users}
            
            # Delete users not in cloud
            for user_id in (local_ids - cloud_ids):
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            for user in users:
                user_id = user.get('id')
                if user_id in local_ids:
                    cursor.execute('''UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?''',
                                 (user.get('name'), user.get('email'), user.get('role'), user_id))
                else:
                    import hashlib
                    default_password = hashlib.sha256("temp123".encode()).hexdigest()
                    cursor.execute('''INSERT INTO users (id, name, email, password_hash, role, company_id, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                 (user_id, user.get('name'), user.get('email'), default_password,
                                  user.get('role', 'user'), company_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            print(f"✅ Company {company_id}: Downloaded {len(users)} users from cloud")
            return True
        except Exception as e:
            print(f"Download users error: {e}")
            return False
    
    @staticmethod
    def sync_materials_to_cloud(company_id):
        """Sync materials to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE company_id = ? OR company_id IS NULL", (company_id,))
            materials = cursor.fetchall()
            conn.close()
            
            materials_list = [dict(m) for m in materials]
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            
            if os.path.exists(cloud_file):
                with open(cloud_file, 'r') as f:
                    cloud_data = json.load(f)
            else:
                cloud_data = {'company_id': company_id, 'materials': [], 'accessories': [], 'users': []}
            
            cloud_data['materials'] = materials_list
            cloud_data['last_sync'] = datetime.now().isoformat()
            
            with open(cloud_file, 'w') as f:
                json.dump(cloud_data, f, indent=2)
            
            print(f"✅ Company {company_id}: Synced {len(materials_list)} materials to cloud")
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
            
            with open(cloud_file, 'r') as f:
                cloud_data = json.load(f)
            
            materials = cloud_data.get('materials', [])
            if not materials:
                return False
            
            conn = sqlite3.connect(DB_PATH)
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
            print(f"✅ Company {company_id}: Downloaded {len(materials)} materials from cloud")
            return True
        except Exception as e:
            print(f"Download materials error: {e}")
            return False
    
    @staticmethod
    def sync_accessories_to_cloud(company_id):
        """Sync accessories to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE company_id = ? OR company_id IS NULL", (company_id,))
            accessories = cursor.fetchall()
            conn.close()
            
            accessories_list = [dict(a) for a in accessories]
            cloud_file = CloudSyncManager._get_cloud_data_file(company_id)
            
            if os.path.exists(cloud_file):
                with open(cloud_file, 'r') as f:
                    cloud_data = json.load(f)
            else:
                cloud_data = {'company_id': company_id, 'materials': [], 'accessories': [], 'users': []}
            
            cloud_data['accessories'] = accessories_list
            cloud_data['last_sync'] = datetime.now().isoformat()
            
            with open(cloud_file, 'w') as f:
                json.dump(cloud_data, f, indent=2)
            
            print(f"✅ Company {company_id}: Synced {len(accessories_list)} accessories to cloud")
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
            
            with open(cloud_file, 'r') as f:
                cloud_data = json.load(f)
            
            accessories = cloud_data.get('accessories', [])
            if not accessories:
                return False
            
            conn = sqlite3.connect(DB_PATH)
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
            print(f"✅ Company {company_id}: Downloaded {len(accessories)} accessories from cloud")
            return True
        except Exception as e:
            print(f"Download accessories error: {e}")
            return False
    
    @staticmethod
    def full_sync_to_cloud(company_id):
        """Full upload to cloud"""
        success1 = CloudSyncManager.sync_users_to_cloud(company_id)
        success2 = CloudSyncManager.sync_materials_to_cloud(company_id)
        success3 = CloudSyncManager.sync_accessories_to_cloud(company_id)
        return success1 or success2 or success3
    
    @staticmethod
    def full_sync_from_cloud(company_id):
        """Full download from cloud"""
        success1 = CloudSyncManager.download_users_from_cloud(company_id)
        success2 = CloudSyncManager.download_materials_from_cloud(company_id)
        success3 = CloudSyncManager.download_accessories_from_cloud(company_id)
        return success1 or success2 or success3
