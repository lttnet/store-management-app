# cloud_sync_manager.py
import sqlite3
import hashlib
from datetime import datetime

# Lazy import to avoid circular references
def get_firebase_api():
    try:
        from firebase_client import firebase_api
        return firebase_api
    except ImportError:
        return None

class CloudSyncManager:
    
    # ============================================================
    # MATERIAL SYNC METHODS
    # ============================================================
    
    @staticmethod
    def sync_materials_to_cloud(company_id):
        """Sync ALL materials to cloud - DELETES cloud materials not in local"""
        try:
            conn = sqlite3.connect("store_management.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE company_id = ?", (company_id,))
            local_materials = cursor.fetchall()
            conn.close()
            
            local_ids = {m['id'] for m in local_materials}
            print(f"📊 Local materials: {len(local_ids)}")
            
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            # Get cloud materials
            cloud_materials = firebase_api.get_materials(company_id)
            cloud_ids = {m['id'] for m in cloud_materials}
            print(f"📊 Cloud materials: {len(cloud_ids)}")
            
            # DELETE from cloud what's not in local
            deleted_count = 0
            for mat_id in cloud_ids - local_ids:
                if firebase_api.delete_material(company_id, mat_id):
                    deleted_count += 1
                    print(f"  🗑️ Deleted material {mat_id} from cloud")
            
            # UPLOAD local materials to cloud
            uploaded_count = 0
            for material in local_materials:
                material_dict = dict(material)
                if firebase_api.sync_material(company_id, material_dict):
                    uploaded_count += 1
            
            print(f"✅ Materials synced: {uploaded_count} uploaded, {deleted_count} deleted from cloud")
            return True
            
        except Exception as e:
            print(f"❌ Sync materials error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def sync_single_material_to_cloud(company_id, material_id):
        """Sync a single material to cloud"""
        try:
            conn = sqlite3.connect("store_management.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ? AND company_id = ?", (material_id, company_id))
            material = cursor.fetchone()
            conn.close()
            
            if not material:
                print(f"❌ Material {material_id} not found in local database")
                return False
            
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            return firebase_api.sync_material(company_id, dict(material))
            
        except Exception as e:
            print(f"Sync single material error: {e}")
            return False
    
    @staticmethod
    def delete_material_from_cloud(company_id, material_id):
        """Delete a single material from cloud"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            return firebase_api.delete_material(company_id, material_id)
            
        except Exception as e:
            print(f"Delete material from cloud error: {e}")
            return False
    
    @staticmethod
    def download_materials_from_cloud(company_id):
        """Download materials from cloud - UPDATES local with cloud"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                return False
            
            cloud_materials = firebase_api.get_materials(company_id)
            if not cloud_materials:
                print("📦 No materials in cloud")
                return True
            
            print(f"📥 Downloading {len(cloud_materials)} materials from cloud...")
            
            conn = sqlite3.connect("store_management.db")
            cursor = conn.cursor()
            
            # Get local IDs
            cursor.execute("SELECT id FROM materials WHERE company_id = ?", (company_id,))
            local_ids = {row[0] for row in cursor.fetchall()}
            
            inserted_count = 0
            updated_count = 0
            deleted_count = 0
            
            # DELETE local materials not in cloud
            for mat_id in local_ids - {m['id'] for m in cloud_materials}:
                cursor.execute("DELETE FROM materials WHERE id = ? AND company_id = ?", (mat_id, company_id))
                deleted_count += 1
                print(f"  🗑️ Deleted material {mat_id} from local (not in cloud)")
            
            # INSERT or UPDATE cloud materials
            for material in cloud_materials:
                material_id = material.get('id')
                
                if material_id in local_ids:
                    # UPDATE existing
                    cursor.execute('''UPDATE materials SET 
                        name = ?, category_id = ?, quantity = ?, quality = ?, location_ids = ?,
                        size = ?, length = ?, colors = ?, notes = ?, barcode_value = ?,
                        image_path = ?, updated_at = ?
                        WHERE id = ? AND company_id = ?''',
                        (material.get('name'), material.get('category_id', 0),
                         material.get('quantity', 0), material.get('quality', 'New'),
                         material.get('location_ids', ''), material.get('size', ''),
                         material.get('length', 0), material.get('colors', ''),
                         material.get('notes', ''), material.get('barcode_value', ''),
                         material.get('image_path', ''), datetime.now().isoformat(),
                         material_id, company_id))
                    updated_count += 1
                else:
                    # INSERT new
                    cursor.execute('''INSERT INTO materials 
                        (id, name, category_id, quantity, quality, location_ids,
                         size, length, colors, notes, barcode_value, image_path, company_id,
                         created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (material_id, material.get('name'), material.get('category_id', 0),
                         material.get('quantity', 0), material.get('quality', 'New'),
                         material.get('location_ids', ''), material.get('size', ''),
                         material.get('length', 0), material.get('colors', ''),
                         material.get('notes', ''), material.get('barcode_value', ''),
                         material.get('image_path', ''), company_id,
                         material.get('created_at', datetime.now().isoformat()),
                         material.get('updated_at', datetime.now().isoformat())))
                    inserted_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ Materials downloaded: {inserted_count} inserted, {updated_count} updated, {deleted_count} deleted locally")
            return True
            
        except Exception as e:
            print(f"❌ Download materials error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # ACCESSORY SYNC METHODS
    # ============================================================
    
    @staticmethod
    def sync_accessories_to_cloud(company_id):
        """Sync ALL accessories to cloud - DELETES cloud accessories not in local"""
        try:
            conn = sqlite3.connect("store_management.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE company_id = ?", (company_id,))
            local_accessories = cursor.fetchall()
            conn.close()
            
            local_ids = {a['id'] for a in local_accessories}
            print(f"📊 Local accessories: {len(local_ids)}")
            
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            # Get cloud accessories
            cloud_accessories = firebase_api.get_accessories(company_id)
            cloud_ids = {a['id'] for a in cloud_accessories}
            print(f"📊 Cloud accessories: {len(cloud_ids)}")
            
            # DELETE from cloud what's not in local
            deleted_count = 0
            for acc_id in cloud_ids - local_ids:
                if firebase_api.delete_accessory(company_id, acc_id):
                    deleted_count += 1
                    print(f"  🗑️ Deleted accessory {acc_id} from cloud")
            
            # UPLOAD local accessories to cloud
            uploaded_count = 0
            for accessory in local_accessories:
                accessory_dict = dict(accessory)
                if firebase_api.sync_accessory(company_id, accessory_dict):
                    uploaded_count += 1
            
            print(f"✅ Accessories synced: {uploaded_count} uploaded, {deleted_count} deleted from cloud")
            return True
            
        except Exception as e:
            print(f"❌ Sync accessories error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def sync_single_accessory_to_cloud(company_id, accessory_id):
        """Sync a single accessory to cloud"""
        try:
            conn = sqlite3.connect("store_management.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE id = ? AND company_id = ?", (accessory_id, company_id))
            accessory = cursor.fetchone()
            conn.close()
            
            if not accessory:
                print(f"❌ Accessory {accessory_id} not found in local database")
                return False
            
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            return firebase_api.sync_accessory(company_id, dict(accessory))
            
        except Exception as e:
            print(f"Sync single accessory error: {e}")
            return False
    
    @staticmethod
    def delete_accessory_from_cloud(company_id, accessory_id):
        """Delete a single accessory from cloud"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            return firebase_api.delete_accessory(company_id, accessory_id)
            
        except Exception as e:
            print(f"Delete accessory from cloud error: {e}")
            return False
    
    @staticmethod
    def download_accessories_from_cloud(company_id):
        """Download accessories from cloud - UPDATES local with cloud"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                return False
            
            cloud_accessories = firebase_api.get_accessories(company_id)
            if not cloud_accessories:
                print("📦 No accessories in cloud")
                return True
            
            print(f"📥 Downloading {len(cloud_accessories)} accessories from cloud...")
            
            conn = sqlite3.connect("store_management.db")
            cursor = conn.cursor()
            
            # Get local IDs
            cursor.execute("SELECT id FROM accessories WHERE company_id = ?", (company_id,))
            local_ids = {row[0] for row in cursor.fetchall()}
            
            inserted_count = 0
            updated_count = 0
            deleted_count = 0
            
            # DELETE local accessories not in cloud
            for acc_id in local_ids - {a['id'] for a in cloud_accessories}:
                cursor.execute("DELETE FROM accessories WHERE id = ? AND company_id = ?", (acc_id, company_id))
                deleted_count += 1
                print(f"  🗑️ Deleted accessory {acc_id} from local (not in cloud)")
            
            # INSERT or UPDATE cloud accessories
            for accessory in cloud_accessories:
                accessory_id = accessory.get('id')
                
                if accessory_id in local_ids:
                    # UPDATE existing
                    cursor.execute('''UPDATE accessories SET 
                        name = ?, category_id = ?, quantity = ?, price = ?, quality = ?,
                        location = ?, notes = ?, barcode_value = ?, image_path = ?, updated_at = ?
                        WHERE id = ? AND company_id = ?''',
                        (accessory.get('name'), accessory.get('category_id', 0),
                         accessory.get('quantity', 0), accessory.get('price', 0),
                         accessory.get('quality', 'New'), accessory.get('location', ''),
                         accessory.get('notes', ''), accessory.get('barcode_value', ''),
                         accessory.get('image_path', ''), datetime.now().isoformat(),
                         accessory_id, company_id))
                    updated_count += 1
                else:
                    # INSERT new
                    cursor.execute('''INSERT INTO accessories 
                        (id, name, category_id, quantity, price, quality, location,
                         notes, barcode_value, image_path, company_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (accessory_id, accessory.get('name'), accessory.get('category_id', 0),
                         accessory.get('quantity', 0), accessory.get('price', 0),
                         accessory.get('quality', 'New'), accessory.get('location', ''),
                         accessory.get('notes', ''), accessory.get('barcode_value', ''),
                         accessory.get('image_path', ''), company_id,
                         accessory.get('created_at', datetime.now().isoformat()),
                         accessory.get('updated_at', datetime.now().isoformat())))
                    inserted_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ Accessories downloaded: {inserted_count} inserted, {updated_count} updated, {deleted_count} deleted locally")
            return True
            
        except Exception as e:
            print(f"❌ Download accessories error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # USER SYNC METHODS
    # ============================================================
    
    @staticmethod
    def sync_users_to_cloud(company_id):
        """Sync users to cloud - UPLOAD with deletion"""
        try:
            conn = sqlite3.connect("store_management.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, password_hash, role, company_id FROM users WHERE company_id = ?", (company_id,))
            local_users = cursor.fetchall()
            conn.close()
            
            local_ids = {u['id'] for u in local_users}
            print(f"📊 Local users: {len(local_ids)}")
            
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            # Get cloud users
            cloud_users = firebase_api.get_users(company_id)
            cloud_ids = {u['id'] for u in cloud_users}
            print(f"📊 Cloud users: {len(cloud_ids)}")
            
            # DELETE from cloud what's not in local
            deleted_count = 0
            for user_id in cloud_ids - local_ids:
                if firebase_api.delete_user(company_id, user_id):
                    deleted_count += 1
                    print(f"  🗑️ Deleted user {user_id} from cloud")
            
            # UPLOAD local users to cloud
            uploaded_count = 0
            for user in local_users:
                user_dict = dict(user)
                if firebase_api.sync_user(company_id, user_dict):
                    uploaded_count += 1
            
            print(f"✅ Users synced: {uploaded_count} uploaded, {deleted_count} deleted from cloud")
            return True
            
        except Exception as e:
            print(f"❌ Sync users error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def download_users_from_cloud(company_id):
        """Download users from cloud - UPDATES local with cloud"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                return False
            
            cloud_users = firebase_api.get_users(company_id)
            if not cloud_users:
                print("👤 No users in cloud")
                return True
            
            print(f"📥 Downloading {len(cloud_users)} users from cloud...")
            
            conn = sqlite3.connect("store_management.db")
            cursor = conn.cursor()
            
            # Get local IDs
            cursor.execute("SELECT id FROM users WHERE company_id = ?", (company_id,))
            local_ids = {row[0] for row in cursor.fetchall()}
            
            DEFAULT_PASSWORD_HASH = hashlib.sha256("changeme".encode()).hexdigest()
            
            # Get existing passwords to preserve them
            cursor.execute("SELECT id, password_hash FROM users")
            existing = {row[0]: row[1] for row in cursor.fetchall()}
            
            inserted_count = 0
            updated_count = 0
            deleted_count = 0
            
            # DELETE local users not in cloud
            for user_id in local_ids - {u['id'] for u in cloud_users}:
                cursor.execute("DELETE FROM users WHERE id = ? AND company_id = ?", (user_id, company_id))
                deleted_count += 1
                print(f"  🗑️ Deleted user {user_id} from local (not in cloud)")
            
            # INSERT or UPDATE cloud users
            for user in cloud_users:
                user_id = user.get('id')
                password_hash = existing.get(user_id, DEFAULT_PASSWORD_HASH)
                
                if user_id in local_ids:
                    # UPDATE existing
                    cursor.execute('''UPDATE users SET 
                        name = ?, email = ?, password_hash = ?, role = ?
                        WHERE id = ? AND company_id = ?''',
                        (user.get('name'), user.get('email'), password_hash,
                         user.get('role'), user_id, company_id))
                    updated_count += 1
                else:
                    # INSERT new
                    cursor.execute('''INSERT INTO users 
                        (id, name, email, password_hash, role, company_id)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                        (user_id, user.get('name'), user.get('email'),
                         password_hash, user.get('role'), company_id))
                    inserted_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ Users downloaded: {inserted_count} inserted, {updated_count} updated, {deleted_count} deleted locally")
            return True
            
        except Exception as e:
            print(f"❌ Download users error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # ACTIVATION CODE SYNC METHODS
    # ============================================================
    
    @staticmethod
    def sync_activation_codes_to_cloud(company_id):
        """Sync all activation codes to cloud"""
        try:
            conn = sqlite3.connect("store_management.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activation_codes ORDER BY created_at DESC")
            codes = cursor.fetchall()
            conn.close()
            
            codes_list = [dict(code) for code in codes]
            
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            return firebase_api.sync_activation_codes(company_id, codes_list)
            
        except Exception as e:
            print(f"Sync activation codes error: {e}")
            return False
    
    @staticmethod
    def delete_activation_code_from_cloud(company_id, activation_code):
        """Delete a single activation code from cloud"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            # Get existing codes from cloud
            existing_codes = firebase_api.get_activation_codes(company_id)
            
            if not existing_codes:
                print("📦 No codes in cloud to delete")
                return True
            
            # Filter out the code to delete
            original_count = len(existing_codes)
            updated_codes = [code for code in existing_codes if code.get('code') != activation_code]
            
            # If no change, code wasn't found
            if len(updated_codes) == original_count:
                print(f"⚠️ Code {activation_code} not found in cloud")
                return True
            
            print(f"📤 Removing code {activation_code} from cloud (was {original_count}, now {len(updated_codes)})")
            
            # Sync updated list back to cloud
            return firebase_api.sync_activation_codes(company_id, updated_codes)
            
        except Exception as e:
            print(f"Delete activation code from cloud error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    @staticmethod
    def sync_single_activation_code_to_cloud(company_id, code_data):
        """Sync a single activation code to cloud - FIXED"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                print("❌ Firebase not ready")
                return False
            
            # Ensure code_data is a dictionary
            if not isinstance(code_data, dict):
                print(f"⚠️ code_data is not a dict: {type(code_data)}")
                return False
            
            # Get existing codes from cloud
            existing_codes = firebase_api.get_activation_codes(company_id)
            
            # If no existing codes, create new list
            if not existing_codes:
                existing_codes = []
            
            # Create a clean copy of the code data
            clean_code = {
                'code': str(code_data.get('code', '')),
                'customer_name': str(code_data.get('customer_name', '')),
                'customer_email': str(code_data.get('customer_email', '')),
                'company_name': str(code_data.get('company_name', '')),
                'is_used': int(code_data.get('is_used', 0)),
                'device_id': str(code_data.get('device_id', '')),
                'activated_at': str(code_data.get('activated_at', '')),
                'created_at': str(code_data.get('created_at', ''))
            }
            
            # Update or add the code
            code_found = False
            for i, code in enumerate(existing_codes):
                if code.get('code') == clean_code.get('code'):
                    existing_codes[i] = clean_code
                    code_found = True
                    break
            
            if not code_found:
                existing_codes.append(clean_code)
            
            # Sync all codes back to cloud
            return firebase_api.sync_activation_codes(company_id, existing_codes)
            
        except Exception as e:
            print(f"Sync single activation code error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # FULL SYNC METHODS
    # ============================================================
    
    @staticmethod
    def full_sync_to_cloud(company_id):
        """Sync ALL data to cloud - UPLOAD with deletion"""
        try:
            print(f"🔄 Syncing ALL data to cloud for company {company_id}")
            
            material_result = CloudSyncManager.sync_materials_to_cloud(company_id)
            accessory_result = CloudSyncManager.sync_accessories_to_cloud(company_id)
            user_result = CloudSyncManager.sync_users_to_cloud(company_id)
            activation_result = CloudSyncManager.sync_activation_codes_to_cloud(company_id)
            
            print(f"✅ Full sync complete: Materials={material_result}, Accessories={accessory_result}, Users={user_result}, Activation={activation_result}")
            return material_result and accessory_result and user_result and activation_result
        except Exception as e:
            print(f"Full sync error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    @staticmethod
    def download_activation_codes_from_cloud(company_id):
        """Download activation codes from cloud"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                return False
            
            cloud_codes = firebase_api.get_activation_codes(company_id)
            if not cloud_codes:
                print(f"📦 No activation codes in cloud for company {company_id}")
                return True
            
            print(f"📥 Downloading {len(cloud_codes)} activation codes from cloud...")
            
            conn = sqlite3.connect("store_management.db")
            cursor = conn.cursor()
            
            # Clear existing codes
            cursor.execute("DELETE FROM activation_codes")
            
            # Insert cloud codes
            inserted_count = 0
            for code in cloud_codes:
                cursor.execute('''
                    INSERT OR REPLACE INTO activation_codes 
                    (code, customer_name, customer_email, company_name, is_used, device_id, activated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code.get('code'),
                    code.get('customer_name', ''),
                    code.get('customer_email', ''),
                    code.get('company_name', ''),
                    code.get('is_used', 0),
                    code.get('device_id', ''),
                    code.get('activated_at', ''),
                    code.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                ))
                inserted_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ Downloaded {inserted_count} activation codes from cloud")
            return True
            
        except Exception as e:
            print(f"Download activation codes error: {e}")
            return False
        
    @staticmethod
    def full_sync_from_cloud(company_id):
        """Download ALL data from cloud - DOWNLOAD with deletion"""
        try:
            print(f"🔄 Downloading ALL data from cloud for company {company_id}")
            
            material_result = CloudSyncManager.download_materials_from_cloud(company_id)
            accessory_result = CloudSyncManager.download_accessories_from_cloud(company_id)
            user_result = CloudSyncManager.download_users_from_cloud(company_id)
            activation_result = CloudSyncManager.download_activation_codes_from_cloud(company_id)
            
            print(f"✅ Full download complete: Materials={material_result}, Accessories={accessory_result}, Users={user_result}, Activation={activation_result}")
            return material_result and accessory_result and user_result and activation_result
        except Exception as e:
            print(f"Full download error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================
    # SYNC STATUS
    # ============================================================
    
    @staticmethod
    def get_sync_status(company_id):
        """Get sync status"""
        try:
            firebase_api = get_firebase_api()
            if not firebase_api or not firebase_api.is_ready():
                return {'status': 'offline', 'last_sync': 'Never'}
            
            conn = sqlite3.connect("store_management.db")
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(updated_at) FROM materials WHERE company_id = ?", (company_id,))
            result = cursor.fetchone()
            conn.close()
            
            last_sync = result[0] if result and result[0] else 'Never'
            
            return {
                'status': 'connected' if firebase_api.is_ready() else 'offline',
                'last_sync': last_sync
            }
        except Exception as e:
            print(f"Get sync status error: {e}")
            return {'status': 'error', 'last_sync': 'Error'}
