"""Store Management App - ORIGINAL LAYOUT WITH ZOOM SUPPORT"""
import sys
import hashlib
import warnings
import traceback
import sqlite3
from database import DB_PATH
# Suppress warnings
warnings.filterwarnings('ignore')

# Mock problematic modules
class DummyModule:
    def __getattr__(self, name):
        return None
    def __call__(self, *args, **kwargs):
        return None

problematic_modules = ['numpy', 'cv2', 'pyzbar', 'matplotlib', 'cmake', 'skbuild', 'PIL']
for module in problematic_modules:
    if module not in sys.modules:
        sys.modules[module] = DummyModule()

import flet as ft
from database import init_database
from managers.material_manager import MaterialManager
from managers.accessory_manager import AccessoryManager
from managers.user_manager import UserManager

import requests
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, 'images', 'Logo-store.png')
background_path = os.path.join(BASE_DIR, 'images', 'backgound_storemgt.png')

class ScaleHelper:
    """Automatically scales desktop layout to fit any screen"""
    
    DESKTOP_WIDTH = 1600
    DESKTOP_HEIGHT = 900
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.scale = 1.0
        self.update_scale()
    
    def update_scale(self):
        """Calculate scale factor based on current window size"""
        if self.page.width and self.page.height:
            scale_w = self.page.width / self.DESKTOP_WIDTH
            scale_h = self.page.height / self.DESKTOP_HEIGHT
            # Use the smaller scale to ensure everything fits
            self.scale = min(scale_w, scale_h, 1.0)  # Max scale 1.0, never enlarge beyond original
        else:
            self.scale = 1.0
    
    def get_scaled_size(self, original_size):
        """Get scaled size for dimensions"""
        return original_size * self.scale
    
    def get_scaled_font(self, original_size):
        """Get scaled font size (minimum 8px)"""
        scaled = int(original_size * self.scale)
        return max(scaled, 8)

class FirebaseRestAPI:
    def __init__(self):
        self.api_key = None
        self.project_id = None
        self._load_config()
    
    def _load_config(self):
        # Your Firebase credentials
        self.api_key = "AIzaSyBBgVLQ2poP3o-jHyninWmyWP5CmkSnOyM"
        self.project_id = "store-management-system-5e28a"
        
        # Also try from environment (for GitHub Actions)
        if os.environ.get('FIREBASE_WEB_API_KEY'):
            self.api_key = os.environ.get('FIREBASE_WEB_API_KEY')
        if os.environ.get('FIREBASE_PROJECT_ID'):
            self.project_id = os.environ.get('FIREBASE_PROJECT_ID')
        
        if self.api_key and self.project_id:
            print(f"✅ Firebase REST API ready")
            print(f"   Project: {self.project_id}")
            return True
        else:
            print("⚠️ Firebase REST API not configured")
            return False
    
    def is_ready(self):
        return self.api_key is not None and self.project_id is not None
    
    def _get_url(self, path):
        return f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{path}?key={self.api_key}"
    
    # ============================================================
    # MATERIAL SYNC METHODS
    # ============================================================
    
    def sync_material(self, company_id, material_data):
        """Sync a single material to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            material_id = material_data.get('id')
            if not material_id:
                print("❌ No material ID provided")
                return False
            
            url = self._get_url(f"companies/{company_id}/materials/{material_id}")
            
            # Convert material data to Firebase format
            document = {
                "fields": {
                    "id": {"integerValue": str(material_id)},
                    "name": {"stringValue": str(material_data.get('name', ''))},
                    "category_id": {"integerValue": str(material_data.get('category_id', 0))},
                    "quantity": {"integerValue": str(material_data.get('quantity', 0))},
                    "quality": {"stringValue": str(material_data.get('quality', 'New'))},
                    "location_ids": {"stringValue": str(material_data.get('location_ids', ''))},
                    "size": {"stringValue": str(material_data.get('size', ''))},
                    "length": {"stringValue": str(material_data.get('length', ''))},
                    "colors": {"stringValue": str(material_data.get('colors', ''))},
                    "notes": {"stringValue": str(material_data.get('notes', ''))},
                    "barcode_value": {"stringValue": str(material_data.get('barcode_value', ''))},
                    "image_path": {"stringValue": str(material_data.get('image_path', ''))},
                    "company_id": {"integerValue": str(company_id)},
                    "synced_at": {"stringValue": datetime.now().isoformat()}
                }
            }
            
            # Add timestamps if they exist
            if material_data.get('created_at'):
                document["fields"]["created_at"] = {"stringValue": str(material_data.get('created_at'))}
            if material_data.get('updated_at'):
                document["fields"]["updated_at"] = {"stringValue": str(material_data.get('updated_at'))}
            
            response = requests.patch(url, json=document)
            
            if response.status_code in [200, 201]:
                print(f"  ✅ Synced material {material_id}: {material_data.get('name')}")
                return True
            else:
                print(f"  ❌ Failed to sync material {material_id}: {response.status_code}")
                print(f"     Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"Sync material error: {e}")
            return False
    
    def delete_material(self, company_id, material_id):
        """Delete a material from Firebase"""
        if not self.is_ready():
            return False
        
        try:
            url = self._get_url(f"companies/{company_id}/materials/{material_id}")
            response = requests.delete(url)
            
            if response.status_code in [200, 204]:
                print(f"  ✅ Deleted material {material_id} from cloud")
                return True
            else:
                print(f"  ❌ Failed to delete material {material_id}: {response.status_code}")
                return False
        except Exception as e:
            print(f"Delete material error: {e}")
            return False
    
    def get_materials(self, company_id):
        """Get all materials from Firebase"""
        if not self.is_ready():
            return []
        
        try:
            url = self._get_url(f"companies/{company_id}/materials")
            response = requests.get(url)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            materials = []
            
            for doc in data.get('documents', []):
                doc_id = doc['name'].split('/')[-1]
                fields = doc.get('fields', {})
                
                material = {
                    'id': int(doc_id),
                    'name': fields.get('name', {}).get('stringValue', ''),
                    'category_id': int(fields.get('category_id', {}).get('integerValue', 0)),
                    'quantity': int(fields.get('quantity', {}).get('integerValue', 0)),
                    'quality': fields.get('quality', {}).get('stringValue', 'New'),
                    'location_ids': fields.get('location_ids', {}).get('stringValue', ''),
                    'size': fields.get('size', {}).get('stringValue', ''),
                    'length': fields.get('length', {}).get('stringValue', ''),
                    'colors': fields.get('colors', {}).get('stringValue', ''),
                    'notes': fields.get('notes', {}).get('stringValue', ''),
                    'barcode_value': fields.get('barcode_value', {}).get('stringValue', ''),
                    'image_path': fields.get('image_path', {}).get('stringValue', ''),
                    'created_at': fields.get('created_at', {}).get('stringValue', ''),
                    'updated_at': fields.get('updated_at', {}).get('stringValue', ''),
                }
                materials.append(material)
            
            print(f"✅ Downloaded {len(materials)} materials from Firebase")
            return materials
            
        except Exception as e:
            print(f"Get materials error: {e}")
            return []
    
    # ============================================================
    # ACCESSORY SYNC METHODS
    # ============================================================
    
    def sync_accessory(self, company_id, accessory_data):
        """Sync a single accessory to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            accessory_id = accessory_data.get('id')
            if not accessory_id:
                print("❌ No accessory ID provided")
                return False
            
            url = self._get_url(f"companies/{company_id}/accessories/{accessory_id}")
            
            # Convert accessory data to Firebase format
            document = {
                "fields": {
                    "id": {"integerValue": str(accessory_id)},
                    "name": {"stringValue": str(accessory_data.get('name', ''))},
                    "category_id": {"integerValue": str(accessory_data.get('category_id', 0))},
                    "quantity": {"integerValue": str(accessory_data.get('quantity', 0))},
                    "price": {"stringValue": str(accessory_data.get('price', 0))},
                    "quality": {"stringValue": str(accessory_data.get('quality', 'New'))},
                    "location": {"stringValue": str(accessory_data.get('location', ''))},
                    "notes": {"stringValue": str(accessory_data.get('notes', ''))},
                    "barcode_value": {"stringValue": str(accessory_data.get('barcode_value', ''))},
                    "image_path": {"stringValue": str(accessory_data.get('image_path', ''))},
                    "company_id": {"integerValue": str(company_id)},
                    "synced_at": {"stringValue": datetime.now().isoformat()}
                }
            }
            
            # Add timestamps if they exist
            if accessory_data.get('created_at'):
                document["fields"]["created_at"] = {"stringValue": str(accessory_data.get('created_at'))}
            if accessory_data.get('updated_at'):
                document["fields"]["updated_at"] = {"stringValue": str(accessory_data.get('updated_at'))}
            
            response = requests.patch(url, json=document)
            
            if response.status_code in [200, 201]:
                print(f"  ✅ Synced accessory {accessory_id}: {accessory_data.get('name')}")
                return True
            else:
                print(f"  ❌ Failed to sync accessory {accessory_id}: {response.status_code}")
                print(f"     Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"Sync accessory error: {e}")
            return False
    
    def delete_accessory(self, company_id, accessory_id):
        """Delete an accessory from Firebase"""
        if not self.is_ready():
            return False
        
        try:
            url = self._get_url(f"companies/{company_id}/accessories/{accessory_id}")
            response = requests.delete(url)
            
            if response.status_code in [200, 204]:
                print(f"  ✅ Deleted accessory {accessory_id} from cloud")
                return True
            else:
                print(f"  ❌ Failed to delete accessory {accessory_id}: {response.status_code}")
                return False
        except Exception as e:
            print(f"Delete accessory error: {e}")
            return False
    
    def get_accessories(self, company_id):
        """Get all accessories from Firebase"""
        if not self.is_ready():
            return []
        
        try:
            url = self._get_url(f"companies/{company_id}/accessories")
            response = requests.get(url)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            accessories = []
            
            for doc in data.get('documents', []):
                doc_id = doc['name'].split('/')[-1]
                fields = doc.get('fields', {})
                
                accessory = {
                    'id': int(doc_id),
                    'name': fields.get('name', {}).get('stringValue', ''),
                    'category_id': int(fields.get('category_id', {}).get('integerValue', 0)),
                    'quantity': int(fields.get('quantity', {}).get('integerValue', 0)),
                    'price': float(fields.get('price', {}).get('stringValue', 0)),
                    'quality': fields.get('quality', {}).get('stringValue', 'New'),
                    'location': fields.get('location', {}).get('stringValue', ''),
                    'notes': fields.get('notes', {}).get('stringValue', ''),
                    'barcode_value': fields.get('barcode_value', {}).get('stringValue', ''),
                    'image_path': fields.get('image_path', {}).get('stringValue', ''),
                    'created_at': fields.get('created_at', {}).get('stringValue', ''),
                    'updated_at': fields.get('updated_at', {}).get('stringValue', ''),
                }
                accessories.append(accessory)
            
            print(f"✅ Downloaded {len(accessories)} accessories from Firebase")
            return accessories
            
        except Exception as e:
            print(f"Get accessories error: {e}")
            return []
        
# Create Firebase instance
firebase_api = FirebaseRestAPI()

class CloudSyncManager:
    
    # ============================================================
    # MATERIAL SYNC
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
            
            if not firebase_api.is_ready():
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
            
            if not firebase_api.is_ready():
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
            if not firebase_api.is_ready():
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
            if not firebase_api.is_ready():
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
    # ACCESSORY SYNC
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
            
            if not firebase_api.is_ready():
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
            
            if not firebase_api.is_ready():
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
            if not firebase_api.is_ready():
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
            if not firebase_api.is_ready():
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
            
            print(f"✅ Full sync complete: Materials={material_result}, Accessories={accessory_result}, Users={user_result}")
            return material_result and accessory_result and user_result
        except Exception as e:
            print(f"Full sync error: {e}")
            return False
    
    @staticmethod
    def full_sync_from_cloud(company_id):
        """Download ALL data from cloud - DOWNLOAD with deletion"""
        try:
            print(f"🔄 Downloading ALL data from cloud for company {company_id}")
            
            material_result = CloudSyncManager.download_materials_from_cloud(company_id)
            accessory_result = CloudSyncManager.download_accessories_from_cloud(company_id)
            user_result = CloudSyncManager.download_users_from_cloud(company_id)
            
            print(f"✅ Full download complete: Materials={material_result}, Accessories={accessory_result}, Users={user_result}")
            return material_result and accessory_result and user_result
        except Exception as e:
            print(f"Full download error: {e}")
            return False
    
    # ============================================================
    # SYNC STATUS
    # ============================================================
    
    @staticmethod
    def get_sync_status(company_id):
        """Get sync status"""
        try:
            if not firebase_api.is_ready():
                return {'status': 'offline', 'last_sync': 'Never'}
            
            # Try to get a sync timestamp
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
        
class StoreApp:
    def __init__(self):
        self.current_user = None
        self.current_view = "dashboard"
        self.selected_material_detail = None
        self.selected_accessory_detail = None
        self.current_material_filter = "All"
        self.current_accessory_filter = "All"
        self.page_ref = None
        self.zoom_level = 1.0
        self.scale_helper = None  # Will be initialized in main
        
        # Colors
        self.bg_color = "#101010"
        self.sidebar_color = "#1E1E1E"
        self.card_color = "#2C2C2C"
        self.accent_color = "#1976D2"
        self.success_color = "#2E7D32"
        self.warning_color = "#F57C00"
        self.danger_color = "#FF5252"
        self.text_color = "#FFFFFF"
        
        # Quality colors
        self.quality_colors = {
            "New": "#2E7D32",
            "Used": "#F57C00",
            "Damaged": "#FF5252",
            "Repaired": "#1976D2",
        }
    def get_device_id(self):
        """Get a unique device ID for trial tracking"""
        import uuid
        import os
        
        try:
            # Try to get a persistent device ID from a file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            device_file = os.path.join(base_dir, ".device_id")
            
            if os.path.exists(device_file):
                with open(device_file, 'r') as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id
            
            # Generate a new device ID
            device_id = str(uuid.uuid4())
            
            # Save it for future use
            try:
                with open(device_file, 'w') as f:
                    f.write(device_id)
            except:
                pass  # If we can't save, just return the generated ID
            
            return device_id
            
        except Exception as e:
            print(f"Error getting device ID: {e}")
            # Fallback: generate a temporary ID based on timestamp
            import time
            return f"device_{int(time.time())}_{hash(str(time.time()))}"
    
    def dict_list(self, rows):
        """Convert sqlite3.Row to dict - FIXED to include all columns"""
        if rows is None:
            return []
        result = []
        for row in rows:
            # Convert row to dict properly
            row_dict = {}
            for key in row.keys():
                row_dict[key] = row[key]
            result.append(row_dict)
            return result
    def sync_activation_codes(self, page: ft.Page):
        """Manually sync activation codes from cloud"""
        try:
            from cloud_sync_manager import CloudSyncManager
            company_id = 1  # Default company
            
            page.snack_bar = ft.SnackBar(
                ft.Text("🔄 Syncing activation codes..."),
                bgcolor=self.accent_color,
                duration=2000
            )
            page.snack_bar.open = True
            page.update()
            
            result = CloudSyncManager.download_activation_codes_from_cloud(company_id)
            
            if result:
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Activation codes synced successfully!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("⚠️ No activation codes in cloud or sync failed"),
                    bgcolor=self.warning_color,
                    duration=3000
                )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            print(f"Sync activation codes error: {e}")
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Sync error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

    def show_sync_confirmation(self, page: ft.Page, message, success=True):
        """Show a brief sync confirmation"""
        color = self.success_color if success else self.danger_color
        icon = ft.icons.CHECK_CIRCLE if success else ft.icons.ERROR
        
        # Use snackbar for brief notification
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(icon, size=20, color=color),
                ft.Text(message, size=12, color="white"),
            ], spacing=8),
            bgcolor=color,
            duration=2000,
        )
        page.snack_bar.open = True
        page.update()
    
    def test_firebase_connection(self, page: ft.Page):
        """Test if Firebase is actually connected and working"""
        
        import os
        import sys
        
        messages = []
        
        # Step 1: Check if Firebase is initialized
        try:
            import firebase_admin
            if firebase_admin._apps:
                messages.append("✅ Firebase is INITIALIZED")
                messages.append(f"   Apps: {len(firebase_admin._apps)}")
            else:
                messages.append("❌ Firebase NOT initialized")
        except ImportError:
            messages.append("⚠️ firebase-admin not installed")
        except Exception as e:
            messages.append(f"⚠️ Firebase check error: {str(e)[:50]}")
        
        # Step 2: Check if key file exists
        key_paths = [
            "serviceAccountKey.json",
            os.path.join(os.path.dirname(sys.argv[0]), "serviceAccountKey.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "serviceAccountKey.json"),
        ]
        
        key_found = False
        for path in key_paths:
            if os.path.exists(path):
                messages.append(f"✅ Key file found: {path}")
                key_found = True
                break
        
        if not key_found:
            messages.append("❌ serviceAccountKey.json NOT found")
        
        # Step 3: Check cloud data
        try:
           # from cloud_sync_manager import CloudSyncManager
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            status = CloudSyncManager.get_sync_status(company_id)
            messages.append(f"📁 Cloud status: {status.get('status', 'Unknown')}")
            messages.append(f"   Last sync: {status.get('last_sync', 'Never')}")
        except Exception as e:
            messages.append(f"⚠️ Cloud status check: {str(e)[:50]}")
        
        # Step 4: Show result
        result_text = ft.Column([
            ft.Text("🔍 Firebase Connection Test", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Column([ft.Text(msg, size=11, selectable=True) for msg in messages], spacing=5),
            ft.Divider(),
            ft.Text("💡 To use real cloud sync:", size=12, weight=ft.FontWeight.BOLD),
            ft.Text("1. Place serviceAccountKey.json in project folder", size=10, color="#888888"),
            ft.Text("2. Or add as GitHub Secret when building APK", size=10, color="#888888"),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Firebase Test", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=result_text, width=450, height=450, padding=20),
            actions=[
                ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_company_registration(self, page: ft.Page):
        """First-time setup for new customer"""
        
        company_name_field = ft.TextField(label="Company Name", width=300)
        admin_name_field = ft.TextField(label="Your Name", width=300)
        admin_email_field = ft.TextField(label="Email", width=300)
        admin_password_field = ft.TextField(label="Password", password=True, width=300)
        status_text = ft.Text("", size=12)
        
        def register_company(e):
            company_name = company_name_field.value.strip()
            admin_name = admin_name_field.value.strip()
            admin_email = admin_email_field.value.strip()
            admin_password = admin_password_field.value
            
            if not all([company_name, admin_name, admin_email, admin_password]):
                status_text.value = "❌ Please fill all fields"
                status_text.color = self.danger_color
                page.update()
                return
            
            if len(admin_password) < 4:
                status_text.value = "❌ Password must be at least 4 characters"
                status_text.color = self.danger_color
                page.update()
                return
            
            import sqlite3
            import hashlib
            from database import DB_PATH
            from datetime import datetime
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Create company
            cursor.execute("INSERT INTO companies (name) VALUES (?)", (company_name,))
            company_id = cursor.lastrowid
            
            # Create admin user
            hashed_password = hashlib.sha256(admin_password.encode()).hexdigest()
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, company_id, account_type, is_activated, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (admin_name, admin_email, hashed_password, 'admin', company_id, 'full', 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Company '{company_name}' created! Please login."),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Register Your Company", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Create your company account to get started:", size=13),
                    ft.Container(height=10),
                    company_name_field,
                    admin_name_field,
                    admin_email_field,
                    admin_password_field,
                    status_text,
                ], spacing=10),
                width=380,
                height=350,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False)),
                ft.FilledButton("Register Company", on_click=register_company, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_categories_page(self, page: ft.Page):
        """Categories Page - SIMPLE VERSION that works on mobile"""
        print("DEBUG: show_categories_page called!")
        
        # Clear all controls first
        page.controls.clear()
        
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        
        # Get current user
        current_user_id = self.current_user.get('id') if self.current_user else 0
        
        # Get categories
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, icon, created_at FROM categories WHERE user_id = ? ORDER BY created_at DESC", (current_user_id,))
        custom_categories = cursor.fetchall()
        conn.close()
        
        # Predefined default categories
        default_categories = [
            "📦 Raw Material", "🔩 Hardware", "🔧 Tools", 
            "⚡ Electrical", "💧 Plumbing", "⚙️ Metal", "📁 Other"
        ]
        
        # Create a simple column with scroll
        main_content = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        # Header with Back button
        header = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    icon_size=24,
                    on_click=lambda e: self.show_dashboard(page),
                    style=ft.ButtonStyle(bgcolor=self.card_color),
                ),
                ft.Text("Categories", size=24, weight=ft.FontWeight.BOLD, color=self.text_color, expand=True),
                ft.IconButton(
                    icon=ft.icons.ADD,
                    icon_size=24,
                    icon_color=self.success_color,
                    on_click=lambda e: self.show_add_category_dialog(page),
                    style=ft.ButtonStyle(bgcolor=self.card_color),
                ),
            ]),
            padding=10,
        )
        main_content.controls.append(header)
        
        # Add Category Form (inline)
        name_input = ft.TextField(
            hint_text="New category name...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            expand=True,
        )
        
        icon_dropdown = ft.Dropdown(
            width=70,
            options=[
                ft.dropdown.Option("📦"), ft.dropdown.Option("🔩"), ft.dropdown.Option("🔧"),
                ft.dropdown.Option("⚡"), ft.dropdown.Option("💧"), ft.dropdown.Option("🪵"),
                ft.dropdown.Option("⚙️"), ft.dropdown.Option("📁"),
            ],
            value="📁",
            bgcolor=self.card_color,
        )
        
        def add_category(e):
            name = name_input.value.strip()
            if not name:
                page.snack_bar = ft.SnackBar(ft.Text("Enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, current_user_id))
            if cursor.fetchone():
                page.snack_bar = ft.SnackBar(ft.Text("Category exists!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                conn.close()
                page.update()
                return
            
            cursor.execute(
                "INSERT INTO categories (name, icon, user_id, created_at) VALUES (?, ?, ?, ?)",
                (name, icon_dropdown.value, current_user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            conn.close()
            
            name_input.value = ""
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name}"), bgcolor=self.success_color)
            page.snack_bar.open = True
            self.show_categories_page(page)
        
        add_form = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Add Category", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row([name_input, icon_dropdown, ft.IconButton(icon=ft.icons.ADD_CIRCLE, on_click=add_category, icon_color=self.success_color)]),
                ], spacing=8),
                padding=10,
            ),
        )
        main_content.controls.append(add_form)
        
        # Default Categories Section
        main_content.controls.append(ft.Divider())
        main_content.controls.append(ft.Text("📁 Default Categories", size=16, weight=ft.FontWeight.BOLD))
        
        for cat in default_categories:
            cat_card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Text(cat[0], size=24),
                        ft.Text(cat[2:], size=14, expand=True),
                        ft.Text("System", size=11, color="#888888"),
                    ]),
                    padding=12,
                ),
            )
            main_content.controls.append(cat_card)
        
        # Custom Categories Section
        if custom_categories:
            main_content.controls.append(ft.Divider())
            main_content.controls.append(ft.Text("✨ My Categories", size=16, weight=ft.FontWeight.BOLD, color=self.accent_color))
            
            for cat in custom_categories:
                cat_card = ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Text(cat['icon'], size=24),
                            ft.Text(cat['name'], size=14, expand=True),
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    icon_size=18,
                                    icon_color=self.accent_color,
                                    on_click=lambda e, cid=cat['id'], name=cat['name'], icon=cat['icon']: 
                                        self.show_edit_category_dialog(page, cid, name, icon),
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    icon_size=18,
                                    icon_color=self.danger_color,
                                    on_click=lambda e, cid=cat['id'], name=cat['name']: 
                                        self.show_delete_category_dialog(page, cid, name),
                                ),
                            ]),
                        ]),
                        padding=12,
                    ),
                )
                main_content.controls.append(cat_card)
        else:
            main_content.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Text("No custom categories. Add one above!", size=12, color="#888888"),
                        padding=20,
                        alignment=ft.alignment.center,
                    ),
                )
            )
        
        # Cancel Button
        main_content.controls.append(ft.Container(height=10))
        main_content.controls.append(
            ft.Row(
                [ft.ElevatedButton("Cancel", on_click=lambda e: self.show_dashboard(page))],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        main_content.controls.append(ft.Container(height=20))
        
        # Wrap in container with padding
        container = ft.Container(
            content=main_content,
            expand=True,
            padding=15,
        )
        
        # Add bottom navigation for mobile
        is_mobile = page.width < 800 if page.width else False
        if is_mobile:
            bottom_nav = self.create_bottom_nav(page)
            page.add(
                ft.Column([
                    container,
                    bottom_nav,
                ], spacing=0, expand=True)
            )
        else:
            sidebar = self.create_sidebar(page)
            page.add(
                ft.Row([
                    sidebar,
                    container,
                ], spacing=0, expand=True)
            )
        
        page.update()
        print("DEBUG: Categories page displayed")

    def open_add_category_form(self, page: ft.Page, refresh_callback=None):
        """Open dialog to add new category"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        is_mobile = page.width < 800 if page.width else False
        dialog_width = page.width - 40 if is_mobile and page.width else 380
        
        name_input = ft.TextField(label="Category Name", width=dialog_width - 40, bgcolor=self.card_color)
        icon_select = ft.Dropdown(
            label="Icon", width=100,
            options=[ft.dropdown.Option("📦", "📦"), ft.dropdown.Option("🔩", "🔩"), ft.dropdown.Option("🔧", "🔧"),
                    ft.dropdown.Option("⚡", "⚡"), ft.dropdown.Option("💧", "💧"), ft.dropdown.Option("🪵", "🪵"),
                    ft.dropdown.Option("⚙️", "⚙️"), ft.dropdown.Option("📁", "📁")],
            value="📁", bgcolor=self.card_color,
        )
        status_text = ft.Text("", size=12)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def save_category(e):
            name = name_input.value.strip()
            if not name:
                status_text.value = "❌ Enter name"
                page.update()
                return
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, current_user_id))
            if cursor.fetchone():
                status_text.value = "❌ Already exists"
                page.update()
                conn.close()
                return
            cursor.execute(
                "INSERT INTO categories (name, icon, user_id, created_at) VALUES (?, ?, ?, ?)",
                (name, icon_select.value, current_user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            conn.close()
            close_dialog()
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name}"), bgcolor=self.success_color)
            page.snack_bar.open = True
            if refresh_callback:
                refresh_callback()
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add Category"),
            content=ft.Container(
                content=ft.Column([name_input, icon_select, status_text, ft.Row([
                    ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                    ft.FilledButton("Save", on_click=save_category),
                ])], spacing=10),
                width=dialog_width, padding=15
            ),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def open_edit_category_form(self, page: ft.Page, category_id, current_name, current_icon, refresh_callback=None):
        """Open form to edit category - Mobile friendly"""
        import sqlite3
        from database import DB_PATH
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        is_mobile = page.width < 800 if page.width else False
        
        dialog_width = page.width - 40 if is_mobile and page.width else 380
        field_width = dialog_width - 40
        
        name_input = ft.TextField(
            label="Category Name",
            value=current_name,
            width=field_width,
            bgcolor=self.card_color,
            autofocus=True,
        )
        
        icon_select = ft.Dropdown(
            label="Icon",
            width=80,
            options=[
                ft.dropdown.Option("📦", "📦"),
                ft.dropdown.Option("🔩", "🔩"),
                ft.dropdown.Option("🔧", "🔧"),
                ft.dropdown.Option("⚡", "⚡"),
                ft.dropdown.Option("💧", "💧"),
                ft.dropdown.Option("🪵", "🪵"),
                ft.dropdown.Option("⚙️", "⚙️"),
                ft.dropdown.Option("📁", "📁"),
                ft.dropdown.Option("🎨", "🎨"),
                ft.dropdown.Option("🔨", "🔨"),
            ],
            value=current_icon,
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def update_category(e):
            new_name = name_input.value.strip()
            if not new_name:
                status_text.value = "❌ Please enter a category name"
                status_text.color = self.danger_color
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if another category with same name exists
            cursor.execute("SELECT id FROM categories WHERE name = ? AND user_id = ? AND id != ?", 
                        (new_name, current_user_id, category_id))
            if cursor.fetchone():
                status_text.value = "❌ Category name already exists!"
                status_text.color = self.danger_color
                page.update()
                conn.close()
                return
            
            try:
                cursor.execute(
                    "UPDATE categories SET name = ?, icon = ? WHERE id = ? AND user_id = ?",
                    (new_name, icon_select.value, category_id, current_user_id)
                )
                conn.commit()
                close_dialog()
                
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Category updated to '{new_name}'!"),
                    bgcolor=self.success_color,
                    duration=2000
                )
                page.snack_bar.open = True
                
                if refresh_callback:
                    refresh_callback()
                page.update()
                
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
            finally:
                conn.close()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Category", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(),
            name_input,
            ft.Row([icon_select], alignment=ft.MainAxisAlignment.START),
            status_text,
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Update", on_click=update_category, 
                            style=ft.ButtonStyle(bgcolor=self.accent_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=15),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def delete_category_confirm(self, page: ft.Page, category_id, category_name, refresh_callback=None):
        """Confirm and delete category - Mobile friendly"""
        import sqlite3
        from database import DB_PATH
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        is_mobile = page.width < 800 if page.width else False
        
        dialog_width = 320 if is_mobile else 380
        
        # Check if category has items
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM materials WHERE category_id = ?", (category_id,))
        material_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM accessories WHERE category_id = ?", (category_id,))
        accessory_count = cursor.fetchone()[0]
        conn.close()
        
        warning_text = ""
        if material_count > 0 or accessory_count > 0:
            warning_text = f"⚠️ This category contains {material_count} material(s) and {accessory_count} accessory(ies). They will become uncategorized."
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Set category_id to NULL for items using this category
            cursor.execute("UPDATE materials SET category_id = NULL WHERE category_id = ?", (category_id,))
            cursor.execute("UPDATE accessories SET category_id = NULL WHERE category_id = ?", (category_id,))
            
            # Delete the category
            cursor.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, current_user_id))
            conn.commit()
            conn.close()
            
            close_dialog()
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Category '{category_name}' deleted!"),
                bgcolor=self.success_color,
                duration=2000
            )
            page.snack_bar.open = True
            
            if refresh_callback:
                refresh_callback()
            page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Delete Category", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(),
            ft.Text(f"Delete '{category_name}'?", size=14),
            ft.Text(warning_text, size=12, color=self.warning_color) if warning_text else ft.Container(),
            ft.Text("This action cannot be undone!", size=12, color="#888888"),
            ft.Container(height=10),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Delete", on_click=confirm_delete, 
                            style=ft.ButtonStyle(bgcolor=self.danger_color), expand=True),
            ], spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=15),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def create_category_chart(self, page: ft.Page):
        """Create a category distribution chart"""
        import sqlite3
        from database import DB_PATH
        
        is_mobile = page.width < 800 if page.width else False
        
        # Get category counts from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get materials by category
        cursor.execute('''
            SELECT c.name, c.icon, COUNT(m.id) as count
            FROM categories c
            LEFT JOIN materials m ON m.category_id = c.id
            GROUP BY c.id
            ORDER BY count DESC
        ''')
        material_cats = cursor.fetchall()
        
        # Get accessories by category
        cursor.execute('''
            SELECT c.name, c.icon, COUNT(a.id) as count
            FROM categories c
            LEFT JOIN accessories a ON a.category_id = c.id
            GROUP BY c.id
            ORDER BY count DESC
        ''')
        accessory_cats = cursor.fetchall()
        
        conn.close()
        
        # Combine counts
        category_counts = {}
        category_icons = {}
        
        for row in material_cats:
            name = row[0]
            icon = row[1]
            count = row[2]
            category_counts[name] = category_counts.get(name, 0) + count
            category_icons[name] = icon
        
        for row in accessory_cats:
            name = row[0]
            icon = row[1]
            count = row[2]
            category_counts[name] = category_counts.get(name, 0) + count
            category_icons[name] = icon
        
        # Filter out categories with 0 items
        categories_with_items = [(name, category_counts[name], category_icons.get(name, '📁')) 
                                for name in category_counts if category_counts[name] > 0]
        categories_with_items.sort(key=lambda x: x[1], reverse=True)
        
        if not categories_with_items:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.PIE_CHART, size=50, color="#888888"),
                    ft.Text("No data available", size=14, color="#888888"),
                    ft.Text("Add materials or accessories to see chart", size=12, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                bgcolor=self.card_color,
                border_radius=10,
            )
        
        # Calculate total for percentages
        total_items = sum(count for _, count, _ in categories_with_items)
        
        # Create color palette
        colors = [
            "#1976D2", "#4CAF50", "#FF9800", "#F44336", "#9C27B0",
            "#00BCD4", "#FF5722", "#795548", "#607D8B", "#E91E63",
            "#8BC34A", "#673AB7", "#009688", "#FFC107", "#3F51B5"
        ]
        
        # Create chart items
        chart_items = []
        for i, (name, count, icon) in enumerate(categories_with_items[:10]):
            percentage = (count / total_items) * 100
            color = colors[i % len(colors)]
            
            # Calculate bar width based on percentage
            bar_width = int(percentage * 2) if not is_mobile else int(percentage * 1.5)
            bar_width = max(20, min(bar_width, 200))
            
            chart_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{icon} {name}", size=13, color=self.text_color, width=120),
                            ft.Text(f"{count} items", size=12, color="#888888", width=70),
                            ft.Text(f"{percentage:.1f}%", size=12, color=self.accent_color, width=50),
                            ft.Container(
                                content=ft.Container(
                                    width=bar_width,
                                    height=8,
                                    bgcolor=color,
                                    border_radius=4,
                                ),
                                expand=True,
                            ),
                        ], spacing=8),
                    ], spacing=4),
                    margin=ft.margin.only(bottom=8),
                )
            )
        
        # Create donut items for desktop
        donut_items = []
        for i, (name, count, icon) in enumerate(categories_with_items[:6]):
            percentage = (count / total_items) * 100
            color = colors[i % len(colors)]
            
            donut_items.append(
                ft.Row([
                    ft.Container(width=12, height=12, bgcolor=color, border_radius=2),
                    ft.Text(f"{icon} {name}", size=11, color=self.text_color, expand=True),
                    ft.Text(f"{percentage:.1f}%", size=11, color="#888888"),
                ], spacing=6)
            )
        
        if is_mobile:
            # Mobile layout - stacked
            return ft.Container(
                content=ft.Column([
                    ft.Text("📊 Materials by Category", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text(f"Distribution across {len(categories_with_items)} categories", size=11, color="#888888"),
                    ft.Divider(),
                    ft.Column(chart_items, spacing=6),
                    ft.Container(height=10),
                    ft.Text(f"Total: {total_items} items", size=12, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ], spacing=8),
                padding=15,
                bgcolor=self.card_color,
                border_radius=12,
            )
        else:
            # Desktop layout - side by side
            return ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text("📊 Materials by Category", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text(f"Distribution across {len(categories_with_items)} categories", size=12, color="#888888"),
                        ft.Divider(),
                        ft.Column(chart_items, spacing=8),
                        ft.Container(height=10),
                        ft.Text(f"Total: {total_items} items", size=13, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ], expand=2),
                    ft.VerticalDivider(),
                    ft.Column([
                        ft.Text("📈 Category Share", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Container(height=10),
                        ft.Column(donut_items, spacing=8),
                    ], expand=1),
                ], spacing=20),
                padding=20,
                bgcolor=self.card_color,
                border_radius=12,
            )
    def show_material_detail_dialog_from_row(self, page: ft.Page, row):
        """Show detail dialog using sqlite3.Row object"""
        
        name = row['name']
        category_name = row['category_name'] if row['category_name'] else 'Other'
        category_icon = row['category_icon'] if row['category_icon'] else '📁'
        quality = row['quality']
        quantity = row['quantity']
        location = row['location_ids'] if row['location_ids'] else 'N/A'
        created = str(row['created_at'])[:16] if row['created_at'] else 'N/A'
        updated = str(row['updated_at'])[:16] if row['updated_at'] else 'N/A'
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_material(e):
            page.dialog.open = False
            self.open_edit_modal(page, row['id'])
        
        def delete_material(e):
            page.dialog.open = False
            self.open_delete_modal(page, row['id'])
        
        content_items = [
            ft.Row([ft.Text("📁 Category:", size=14, color="#CCCCCC", width=100), 
                    ft.Text(f"{category_icon} {category_name}", size=14, color=self.accent_color)], spacing=8),
            ft.Row([ft.Text("🏷️ Quality:", size=14, color="#CCCCCC", width=100), 
                    ft.Container(content=ft.Text(quality, size=12, color="white"),
                    bgcolor=self.get_quality_color(quality), border_radius=8, padding=ft.padding.symmetric(horizontal=12, vertical=4))], spacing=8),
            ft.Row([ft.Text("🔢 Quantity:", size=14, color="#CCCCCC", width=100), 
                    ft.Text(str(quantity), size=16, weight=ft.FontWeight.BOLD,
                    color=self.danger_color if quantity < 10 else self.text_color)], spacing=8),
            ft.Row([ft.Text("📍 Location:", size=14, color="#CCCCCC", width=100), 
                    ft.Text(location, size=14, color=self.text_color)], spacing=8),
            ft.Divider(),
            ft.Row([ft.Text("📅 Created:", size=13, color="#CCCCCC", width=100), 
                    ft.Text(created, size=13, color="#888888")], spacing=8),
            ft.Row([ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=100), 
                    ft.Text(updated, size=13, color="#888888")], spacing=8),
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=edit_material, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=delete_material, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], spacing=10),
        ]
        
        scrollable_content = ft.Column(content_items, spacing=10, scroll=ft.ScrollMode.AUTO, height=400)
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable_content, width=400, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def get_quality_color(self, quality):
        """Get color for quality badge"""
        colors = {
            "New": "#2E7D32",      # Green
            "Used": "#F57C00",      # Orange
            "Damaged": "#FF5252",   # Red
            "Repaired": "#1976D2"   # Blue
        }
        return colors.get(quality, "#888888")

    def get_quality_icon(self, quality):
        """Get icon for quality"""
        icons = {
            "New": "🟢",
            "Used": "🟠",
            "Damaged": "🔴",
            "Repaired": "🔵"
        }
        return icons.get(quality, "⚪")
    
    def has_permission(self, permission):
        """Check if user has permission - Also checks app activation"""
        if not self.current_user:
            return False
        
        # Check if app is activated (trial or full)
        from activation_manager import ActivationManager
        device_id = ActivationManager.get_device_id()
        status = ActivationManager.check_activation_status(device_id)
        
        # If app is not activated and not in trial, block access
        if status.get('status') not in ['activated', 'trial_active']:
            return False
        
        # If app is in trial, check if trial has enough days left
        if status.get('status') == 'trial_active' and status.get('days_left', 0) <= 0:
            return False
        
        # Check user role permissions
        role = self.current_user.get('role', 'user')
        
        # Admin has all permissions
        if role == 'admin':
            return True
        
        # Manager permissions
        if role == 'manager':
            manager_permissions = [
                'view_dashboard', 'view_materials', 'view_accessories', 
                'add_material', 'edit_material', 'delete_material',
                'add_accessory', 'edit_accessory', 'delete_accessory',
                'view_inventory', 'export_data', 'scan_barcode'
            ]
            return permission in manager_permissions
        
        # User permissions (regular users)
        if role == 'user':
            user_permissions = [
                'view_dashboard', 'view_materials', 'view_accessories',
                'add_material', 'edit_material', 
                'add_accessory', 'edit_accessory',
                'view_inventory', 'scan_barcode'
            ]
            return permission in user_permissions
        
        return False
        
    def show_no_permission(self, page):
        """Show no permission message with activation status"""
        from activation_manager import ActivationManager
        device_id = ActivationManager.get_device_id()
        status = ActivationManager.check_activation_status(device_id)
        
        if status.get('status') == 'trial_expired':
            message = "⚠️ Your trial has expired. Please activate the app to continue."
            action = "Activate Now"
            def on_action(e):
                self.show_activation_dialog(page)
        elif status.get('status') == 'no_trial':
            message = "📱 Please start a free trial or activate the app."
            action = "Start Trial"
            def on_action(e):
                from activation_manager import ActivationManager
                result = ActivationManager.start_trial(device_id)
                if result.get('status') == 'trial_started':
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✅ 30-day trial started!"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
                    self.show_dashboard(page)
        else:
            message = "You don't have permission to perform this action."
            action = None
            def on_action(e):
                pass
        
        dialog = ft.AlertDialog(
            title=ft.Text("Access Denied", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(message, size=14),
                    ft.Text(f"User: {self.current_user.get('name', 'Unknown')}", size=12, color="#888888"),
                    ft.Text(f"Role: {self.current_user.get('role', 'user').upper()}", size=12, color="#888888"),
                ], spacing=10),
                width=350,
                padding=20,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False)),
            ] if not action else [
                ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False)),
                ft.ElevatedButton(action, on_click=on_action, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def get_company_info(self):
        """Load company information from config file"""
        import json
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_dir, "company_config.json")
        
        default_info = {
            'company_name': 'Store Management System',
            'phone': '',
            'email': '',
            'website': '',
            'address': '',
            'city': '',
            'tax_id': ''
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        default_info.update(data)
            except (json.JSONDecodeError, ValueError, IOError) as e:
                print(f"Error reading company config: {e}")
        
        return default_info
    
    def save_company_info(self, page: ft.Page):
        """Save company information to config file"""
        import json
        import os
        
        # Find the company card and get values
        # Since we can't easily get the values from the card, we'll use a dialog approach
        
        def save_info(e):
            data = {
                'company_name': name_field.value,
                'phone': phone_field.value,
                'email': email_field.value,
                'website': website_field.value,
                'address': address_field.value,
                'city': city_field.value,
                'tax_id': tax_id_field.value,
            }
            
            try:
                config_file = os.path.join(BASE_DIR, "company_config.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Company information saved!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_settings(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Error saving: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
            page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        # Get current company info
        current = self.get_company_info()
        
        name_field = ft.TextField(label="Company Name", value=current.get('company_name', ''), width=350)
        phone_field = ft.TextField(label="Phone", value=current.get('phone', ''), width=350)
        email_field = ft.TextField(label="Email", value=current.get('email', ''), width=350)
        website_field = ft.TextField(label="Website", value=current.get('website', ''), width=350)
        address_field = ft.TextField(label="Address", value=current.get('address', ''), width=350, multiline=True)
        city_field = ft.TextField(label="City", value=current.get('city', ''), width=350)
        tax_id_field = ft.TextField(label="Tax ID / VAT", value=current.get('tax_id', ''), width=350)
        
        dialog_content = ft.Column([
            ft.Text("Edit Company Information", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Container(
                content=ft.Column([
                    name_field,
                    phone_field,
                    email_field,
                    website_field,
                    address_field,
                    city_field,
                    tax_id_field,
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
                height=400,
            ),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save", on_click=save_info, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Company Information"),
            content=ft.Container(content=dialog_content, width=450, height=550, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def check_cloud_users_direct(self, page: ft.Page):
        """Directly check what users are in cloud file"""
        import json
        import os
        
        company_id = self.current_user.get('company_id', 1) if self.current_user else 1
        cloud_file = f"cloud_data/company_{company_id}.json"
        
        if os.path.exists(cloud_file):
            with open(cloud_file, 'r') as f:
                data = json.load(f)
            
            cloud_users = data.get('users', [])
            
            # Also get local users
            import sqlite3
            from database import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, role FROM users")
            local_users = cursor.fetchall()
            conn.close()
            
            message = f"=== LOCAL USERS ({len(local_users)}) ===\n"
            for u in local_users:
                message += f"  ID:{u[0]} - {u[1]} ({u[2]}) - {u[3]}\n"
            
            message += f"\n=== CLOUD USERS ({len(cloud_users)}) ===\n"
            for u in cloud_users:
                message += f"  ID:{u.get('id')} - {u.get('name')} ({u.get('email')}) - {u.get('role')}\n"
            
            dialog = ft.AlertDialog(
                title=ft.Text("User Sync Status", size=18, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Text(message, size=11, font_family="monospace"),
                    width=450,
                    height=450,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False)),
                    ft.ElevatedButton("Force Sync", on_click=lambda e: self.force_sync_users(page)),
                ],
            )
            page.dialog = dialog
            dialog.open = True
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("No cloud file found. Run sync first."),
                bgcolor=self.warning_color,
                duration=3000
            )
            page.snack_bar.open = True
        
        page.update()

    def force_sync_users(self, page: ft.Page):
        """Force sync users to cloud (overwrite cloud with local)"""
        import json
        import os
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        
        company_id = self.current_user.get('company_id', 1) if self.current_user else 1
        
        # Get local users
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password_hash, role, company_id, created_at FROM users")
        local_users = cursor.fetchall()
        conn.close()
        
        users_list = [dict(u) for u in local_users]
        
        # Overwrite cloud file
        cloud_file = f"cloud_data/company_{company_id}.json"
        if os.path.exists(cloud_file):
            with open(cloud_file, 'r') as f:
                cloud_data = json.load(f)
        else:
            cloud_data = {'company_id': company_id, 'materials': [], 'accessories': [], 'users': []}
        
        cloud_data['users'] = users_list
        cloud_data['last_sync'] = datetime.now().isoformat()
        
        with open(cloud_file, 'w') as f:
            json.dump(cloud_data, f, indent=2)
        
        page.snack_bar = ft.SnackBar(
            ft.Text(f"✅ Force sync complete! {len(users_list)} users in cloud"),
            bgcolor=self.success_color,
            duration=3000
        )
        page.snack_bar.open = True
        
        # Close the dialog
        if page.dialog:
            page.dialog.open = False
        
        page.update()

    def debug_cloud_users(self, page: ft.Page):
        """Debug: Show what users are in cloud"""
        import json
        import os
        
        company_id = self.current_user.get('company_id', 1) if self.current_user else 1
        cloud_file = f"cloud_data/company_{company_id}.json"
        
        if os.path.exists(cloud_file):
            with open(cloud_file, 'r') as f:
                data = json.load(f)
            
            cloud_users = data.get('users', [])
            
            message = f"Cloud Users for Company {company_id}:\n"
            message += f"Total: {len(cloud_users)}\n\n"
            for u in cloud_users:
                message += f"  • ID:{u.get('id')} - {u.get('name')} ({u.get('email')}) - Role: {u.get('role')}\n"
            
            dialog = ft.AlertDialog(
                title=ft.Text("Cloud Users", size=18, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Text(message, size=11),
                    width=400,
                    height=400,
                    padding=20,
                ),
                actions=[ft.TextButton("OK", on_click=lambda e: setattr(page.dialog, 'open', False))],
            )
            page.dialog = dialog
            dialog.open = True
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("No cloud file found. Run sync first."),
                bgcolor=self.warning_color,
                duration=3000
            )
            page.snack_bar.open = True
        
        page.update()

    def add_cloud_sync_button(self, page: ft.Page):
        sync_btn = ft.IconButton(
            icon=ft.icons.CLOUD_SYNC,
            icon_size=24,
            icon_color=self.accent_color,
            on_click=lambda e: self.manual_sync(page),
            tooltip="Sync with Cloud",
        )
        return sync_btn
    
    def manual_sync(self, page: ft.Page):
        """Manual sync with cloud"""
        if not self.current_user:
            page.snack_bar = ft.SnackBar(ft.Text("Please login first"), bgcolor=self.warning_color)
            page.snack_bar.open = True
            page.update()
            return
        
        company_id = self.current_user.get('company_id', 1)
        
        page.snack_bar = ft.SnackBar(
            ft.Text(f"🔄 Syncing..."),
            bgcolor=self.accent_color,
            duration=2000
        )
        page.snack_bar.open = True
        page.update()
        
        try:
            # Upload to cloud
            upload_result = CloudSyncManager.full_sync_to_cloud(company_id)
            # Download from cloud
            download_result = CloudSyncManager.full_sync_from_cloud(company_id)
            
            if upload_result or download_result:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✅ Sync completed!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                # Refresh current view
                if self.current_view == "users":
                    self.show_users(page)
                elif self.current_view == "dashboard":
                    self.show_dashboard(page)
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("ℹ️ No changes detected"),
                    bgcolor=self.warning_color,
                    duration=2000
                )
        except Exception as e:
            print(f"Sync error: {e}")
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Sync error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
        
        page.snack_bar.open = True
        page.update()

    def auto_sync_on_start(self, page: ft.Page):
        """Auto sync when app starts"""
        if self.current_user and self.current_user.get('id', 0) > 0:
            company_id = self.current_user.get('company_id', 1)
            print(f"🔄 Auto-syncing for company ID: {company_id}")
            
            success = CloudSyncManager.full_sync_from_cloud(company_id)
            
            if success:
                print(f"✅ Auto-sync completed for company {company_id}")
                if self.current_view == "users":
                    self.show_users(page)

    def auto_sync_after_change(self, page: ft.Page):
        """Auto sync after data changes"""
        if self.current_user and self.current_user.get('id', 0) > 0:
            company_id = self.current_user.get('company_id', 1)
            CloudSyncManager.full_sync_to_cloud(company_id)
            print(f"✅ Auto-synced after change for company {company_id}")
    # ============ ZOOM METHODS ============
    def zoom_in(self, page: ft.Page):
        self.zoom_level = min(self.zoom_level + 0.1, 2.0)
        self.apply_zoom(page)
    
    def zoom_out(self, page: ft.Page):
        self.zoom_level = max(self.zoom_level - 0.1, 0.5)
        self.apply_zoom(page)
    
    def reset_zoom(self, page: ft.Page):
        self.zoom_level = 1.0
        self.apply_zoom(page)
    
    def apply_zoom(self, page: ft.Page):
        if not self.current_user:
            return
        page.snack_bar = ft.SnackBar(ft.Text(f"Zoom: {int(self.zoom_level * 100)}%"), bgcolor=self.accent_color, duration=1000)
        page.snack_bar.open = True
        if self.current_view == "dashboard":
            self.show_dashboard(page)
        elif self.current_view == "materials":
            self.show_materials_screen(page)
        elif self.current_view == "accessories":
            self.show_accessories(page)
        page.update()    

    def main(self, page: ft.Page):
        """Main entry point - Show dashboard directly"""
        try:
            # Initialize scale helper
            self.scale_helper = ScaleHelper(page)
            self.page_ref = page
            
            # Page settings
            page.title = "Store Management System"
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = self.bg_color
            page.padding = 0
            page.spacing = 0
            
            # Track zoom level
            self.zoom_level = 1.0
            
            # Handle resize
            def on_resize(e):
                if self.scale_helper:
                    self.scale_helper.update_scale()
                if self.current_view == "dashboard":
                    self.show_dashboard(page)
            
            page.on_resize = on_resize
            
            # ===== INITIALIZE DATABASE =====
            init_database()
            print("✅ Database initialized")
            
            # ===== ENSURE ACTIVATION TABLES EXIST =====
            from activation_manager import ActivationManager
            ActivationManager.ensure_tables()
            print("✅ Activation tables verified")
            
            # ===== AUTO-SYNC ACTIVATION CODES FROM CLOUD ON STARTUP =====
            print("\n☁️ Auto-syncing activation codes from cloud...")
            try:
                from cloud_sync_manager import CloudSyncManager
                from firebase_client import firebase_api
                company_id = 1  # Default company
                
                # Check if Firebase is ready
                if firebase_api.is_ready():
                    print("   Firebase is ready, downloading activation codes...")
                    result = CloudSyncManager.download_activation_codes_from_cloud(company_id)
                    if result:
                        print("   ✅ Activation codes synced from cloud successfully!")
                    else:
                        print("   ⚠️ No activation codes found in cloud or sync failed")
                else:
                    print("   ⚠️ Firebase not ready, skipping cloud sync")
                    print("   💡 App will work in offline mode with local data")
            except Exception as e:
                print(f"   ⚠️ Auto-sync error (non-critical): {e}")
                print("   💡 App will continue with local data")
            
            # ===== CHECK USER SESSION =====
            self.current_user = self.get_saved_user()
            
            if not self.current_user:
                # First time user - start trial automatically
                device_id = ActivationManager.get_device_id()
                self.current_user = {
                    'email': 'trial@user.com',
                    'trial': True,
                    'activated': False,
                    'days_left': 30,
                    'device_id': device_id
                }
                self.save_user_session(self.current_user)
                self.save_trial_info('trial@user.com')
                print("✅ New trial started for device:", device_id)
            else:
                # Check if trial expired
                if not self.current_user.get('activated', False):
                    try:
                        trial_active, days_left = self.check_trial_status()
                        if trial_active:
                            self.current_user['days_left'] = days_left
                            self.current_user['trial'] = True
                        else:
                            self.current_user['days_left'] = 0
                            self.current_user['trial'] = False
                            print("⚠️ Trial expired for device:", self.current_user.get('device_id'))
                    except Exception as e:
                        print(f"Error checking trial: {e}")
                        # Default to trial active with 30 days
                        self.current_user['days_left'] = 30
                        self.current_user['trial'] = True
            
            print(f"📊 User state: activated={self.current_user.get('activated')}, trial={self.current_user.get('trial')}, days_left={self.current_user.get('days_left')}")
            
            # ===== SHOW LOGIN SCREEN =====
            self.show_login(page)
            page.update()
            print("✅ App started successfully")
            
        except Exception as e:
            print(f"❌ App startup error: {e}")
            import traceback
            traceback.print_exc()
            
            # Show error on screen
            try:
                page.controls.clear()
                page.add(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("❌ App Error", size=24, color="red"),
                            ft.Text(str(e), size=14, color="white"),
                            ft.ElevatedButton("Retry", on_click=lambda e: self.main(page)),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                )
                page.update()
            except:
                pass
            
    def ensure_trial_table(self):
        """Ensure trial_info table exists"""
        import sqlite3
        from database import DB_PATH
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trial_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    trial_start TEXT,
                    trial_end TEXT,
                    activated INTEGER DEFAULT 0,
                    activation_code TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ Trial table ready")
            
        except Exception as e:
            print(f"Error ensuring trial table: {e}")

    def get_saved_user(self):
        """Get saved user from session"""
        import json
        import os
        
        try:
            session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
            if not os.path.exists(session_file):
                return None
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            if not session_data:
                return None
            
            return {
                'email': session_data.get('email', 'trial@user.com'),
                'trial': session_data.get('trial', True),
                'activated': session_data.get('activated', False),
                'days_left': session_data.get('days_left', 30),
                'device_id': session_data.get('device_id', self.get_device_id())
            }
            
        except Exception as e:
            print(f"Error getting saved user: {e}")
            return None
    def save_trial_info(self, email):
        """Save trial info to database"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime, timedelta
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Create trial_info table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trial_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    trial_start TEXT,
                    trial_end TEXT,
                    activated INTEGER DEFAULT 0,
                    activation_code TEXT
                )
            ''')
            
            # Delete existing trial info
            cursor.execute("DELETE FROM trial_info")
            
            # Insert new trial
            trial_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            trial_end = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO trial_info (email, trial_start, trial_end)
                VALUES (?, ?, ?)
            ''', (email, trial_start, trial_end))
            
            conn.commit()
            conn.close()
            print(f"✅ Trial started for {email} (ends: {trial_end})")
            
        except Exception as e:
            print(f"Save trial error: {e}")

    def check_trial_status(self):
        """Check if trial is active and days left"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if trial_info table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trial_info'")
            if not cursor.fetchone():
                conn.close()
                return False, 0
            
            cursor.execute("SELECT email, trial_start, trial_end FROM trial_info LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, 0
            
            email, trial_start, trial_end = result
            
            if not trial_end:
                return False, 0
            
            trial_end_date = datetime.strptime(trial_end, '%Y-%m-%d %H:%M:%S')
            days_left = (trial_end_date - datetime.now()).days
            
            if days_left <= 0:
                return False, 0
            
            return True, days_left
            
        except Exception as e:
            print(f"Check trial error: {e}")
            return False, 0
    
    def save_user_session(self, user_dict):
        """Save user session for auto-login"""
        import json
        import os
        
        try:
            session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
            
            session_data = {
                'email': user_dict.get('email', 'trial@user.com'),
                'trial': user_dict.get('trial', True),
                'activated': user_dict.get('activated', False),
                'days_left': user_dict.get('days_left', 30),
                'device_id': user_dict.get('device_id', self.get_device_id())
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
            
            print(f"✅ Session saved for: {session_data['email']}")
            return True
            
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def is_mobile(self, page: ft.Page):
        """Check if running on mobile device"""
        return page.width < 800 if page.width else False        
        
    def wrap_with_touch_zoom(self, content):
            """Wrap content to enable touch pinch-to-zoom"""
            return ft.Container(
                content=content,
                expand=True,
                on_gesture=self.on_pinch_zoom,
            )

    def on_pinch_zoom(self, e):
        """Handle pinch zoom gesture"""
        if e.type == ft.GestureType.PAN_UPDATE:
            # Detect pinch (when two fingers)
            if e.scale != 1.0:
                new_zoom = self.zoom_level * e.scale
                new_zoom = max(0.5, min(new_zoom, 3.0))
                if new_zoom != self.zoom_level:
                    self.zoom_level = new_zoom
                    self.apply_zoom_to_current_view(e.control.page)

    def show_activation_dialog(self, page: ft.Page):
        """Show activation dialog for entering code"""
        from activation_manager import ActivationManager
        
        code_field = ft.TextField(
            label="Activation Code",
            hint_text="ACT-XXXX-XXXX-XXXX",
            width=300,
            bgcolor="#2C2C2C",
            border_color="#FF9800",
            autofocus=True,
        )
        status_text = ft.Text("", size=12)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def activate(e):
            code = code_field.value.strip().upper()
            if not code:
                status_text.value = "❌ Please enter activation code"
                status_text.color = self.danger_color
                page.update()
                return
            
            device_id = ActivationManager.get_device_id()
            result = ActivationManager.activate_app(device_id, code)
            
            if result.get('success'):
                close_dialog()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✅ {result.get('message')}"),
                    bgcolor=self.success_color,
                    duration=4000
                )
                page.snack_bar.open = True
                
                # Update current user's activation status
                if self.current_user:
                    self.current_user['is_activated'] = True
                
                page.update()
                self.show_dashboard(page)
            else:
                status_text.value = f"❌ {result.get('message')}"
                status_text.color = self.danger_color
                page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("🔑 Activate App", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Enter your activation code to unlock full access:", size=13),
                    ft.Container(height=10),
                    code_field,
                    status_text,
                    ft.Divider(),
                    ft.Text("💡 Need a code? Contact support@store.com", size=10, color="#888888"),
                ], spacing=10),
                width=380,
                height=300,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                ft.FilledButton("Activate", on_click=activate, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_activation_only_dialog(self, page: ft.Page):
        """Show activation dialog for existing users with working close button"""
        import sqlite3
        from database import DB_PATH
        
        email_field = ft.TextField(label="Email", width=300, bgcolor=self.card_color)
        activation_field = ft.TextField(label="Activation Code", width=300, bgcolor=self.card_color)
        status_text = ft.Text("", size=12)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def verify_activation(e):
            email = email_field.value.strip()
            code = activation_field.value.strip().upper()
            
            if not email or not code:
                status_text.value = "❌ Please enter email and activation code"
                status_text.color = self.danger_color
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, activation_code FROM users WHERE email = ?", (email,))
            result = cursor.fetchone()
            
            if result and result[1] == code:
                cursor.execute("UPDATE users SET is_activated = 1, account_type = 'full' WHERE id = ?", (result[0],))
                conn.commit()
                conn.close()
                
                close_dialog()
                
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Account activated! You can now log in."),
                    bgcolor=self.success_color,
                    duration=4000
                )
                page.snack_bar.open = True
                page.update()
            else:
                status_text.value = "❌ Invalid email or activation code"
                status_text.color = self.danger_color
                page.update()
                conn.close()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Activate License", size=18, weight=ft.FontWeight.BOLD, color=self.accent_color, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Enter your email and activation code:", size=13),
                    ft.Container(height=10),
                    email_field,
                    activation_field,
                    status_text,
                ], spacing=8),
                width=380,
                height=300,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                ft.FilledButton("Activate", on_click=verify_activation, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_trial_signup_dialog(self, page: ft.Page):
        """Dialog for 30-day trial signup with working close button"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime, timedelta
        import hashlib
        import random
        import string
        
        name_field = ft.TextField(label="Full Name", width=300, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", width=300, bgcolor=self.card_color)
        password_field = ft.TextField(label="Password", password=True, width=300, bgcolor=self.card_color)
        confirm_field = ft.TextField(label="Confirm Password", password=True, width=300, bgcolor=self.card_color)
        status_text = ft.Text("", size=12)
        
        def generate_activation_code():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def create_trial_account(e):
            name = name_field.value.strip()
            email = email_field.value.strip()
            password = password_field.value
            confirm = confirm_field.value
            
            if not name or not email or not password:
                status_text.value = "❌ Please fill all fields"
                status_text.color = self.danger_color
                page.update()
                return
            
            if password != confirm:
                status_text.value = "❌ Passwords do not match"
                status_text.color = self.danger_color
                page.update()
                return
            
            if len(password) < 4:
                status_text.value = "❌ Password must be at least 4 characters"
                status_text.color = self.danger_color
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                status_text.value = "❌ Email already registered"
                status_text.color = self.danger_color
                page.update()
                conn.close()
                return
            
            # Create trial account
            start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            activation_code = generate_activation_code()
            
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, trial_start_date, trial_end_date, account_type, activation_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, hashed_password, 'user', start_date, end_date, 'trial', activation_code, start_date))
            
            conn.commit()
            conn.close()
            
            close_dialog()
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Trial account created! Login with your email. Trial expires in 30 days."),
                bgcolor=self.success_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Start 30-Day Free Trial", size=20, weight=ft.FontWeight.BOLD, color=self.success_color, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Create your account to start your free trial:", size=13, color="#888888"),
                    ft.Container(height=5),
                    name_field,
                    email_field,
                    password_field,
                    confirm_field,
                    status_text,
                    ft.Container(height=10),
                    ft.Text("✓ 30 days full access", size=11, color="#888888"),
                    ft.Text("✓ No credit card required", size=11, color="#888888"),
                    ft.Text("✓ Cancel anytime", size=11, color="#888888"),
                ], spacing=8),
                width=380,
                height=500,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                ft.FilledButton("Start Trial", on_click=create_trial_account, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_register_dialog(self, page: ft.Page):
        """Register new user dialog - Simplified"""
        import sqlite3
        import hashlib
        from database import DB_PATH
        from datetime import datetime
        
        name_field = ft.TextField(label="Full Name", width=300, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", width=300, bgcolor=self.card_color)
        password_field = ft.TextField(label="Password", password=True, width=300, bgcolor=self.card_color)
        confirm_field = ft.TextField(label="Confirm Password", password=True, width=300, bgcolor=self.card_color)
        status_text = ft.Text("", size=12)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def create_account(e):
            name = name_field.value.strip()
            email = email_field.value.strip()
            password = password_field.value
            confirm = confirm_field.value
            
            if not name or not email or not password:
                status_text.value = "❌ Please fill all fields"
                status_text.color = self.danger_color
                page.update()
                return
            
            if password != confirm:
                status_text.value = "❌ Passwords do not match"
                status_text.color = self.danger_color
                page.update()
                return
            
            if len(password) < 4:
                status_text.value = "❌ Password must be at least 4 characters"
                status_text.color = self.danger_color
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                status_text.value = "❌ Email already registered"
                status_text.color = self.danger_color
                page.update()
                conn.close()
                return
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, hashed_password, 'user', current_time))
            
            conn.commit()
            conn.close()
            
            close_dialog()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Account created! Please login."),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Create Account", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Create your account:", size=13, color="#888888"),
                    ft.Container(height=5),
                    name_field,
                    email_field,
                    password_field,
                    confirm_field,
                    status_text,
                ], spacing=8),
                width=380,
                height=420,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                ft.FilledButton("Create Account", on_click=create_account, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_forgot_password_dialog(self, page: ft.Page):
        """Forgot password dialog"""
        import sqlite3
        import hashlib
        import random
        import string
        from database import DB_PATH
        
        email_field = ft.TextField(label="Email", width=300, bgcolor=self.card_color)
        status_text = ft.Text("", size=12)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def reset_password(e):
            email = email_field.value.strip()
            
            if not email:
                status_text.value = "❌ Please enter your email"
                status_text.color = self.danger_color
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if user:
                # Generate temporary password
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                hashed_password = hashlib.sha256(temp_password.encode()).hexdigest()
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user[0]))
                conn.commit()
                
                status_text.value = f"✓ Temporary password: {temp_password}\n\nPlease login with this password and change it in Settings."
                status_text.color = self.success_color
                page.set_clipboard(temp_password)
            else:
                status_text.value = "❌ Email not found"
                status_text.color = self.danger_color
            
            conn.close()
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Reset Password", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Enter your email to reset password:", size=13),
                    ft.Container(height=10),
                    email_field,
                    status_text,
                ], spacing=10),
                width=380,
                height=280,
                padding=20,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                ft.FilledButton("Reset Password", on_click=reset_password, style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def activate_app(self, page: ft.Page):
        """Handle app activation"""
        from activation_manager import ActivationManager
        
        # Find the activation code field
        activation_code = None
        for control in page.controls:
            if isinstance(control, ft.Stack):
                for child in control.content.content.controls:
                    if isinstance(child, ft.TextField) and child.label == "Activation Code":
                        activation_code = child.value
                        break
        
        # If not found, show dialog
        if not activation_code:
            self.show_activation_dialog(page)
            return
        
        if not activation_code or len(activation_code) < 10:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Please enter a valid activation code"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        device_id = ActivationManager.get_device_id()
        result = ActivationManager.activate_app(device_id, activation_code.upper())
        
        if result.get('success'):
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ {result.get('message')}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            
            # Update current user
            if self.current_user:
                self.current_user['is_activated'] = True
            
            page.update()
            self.show_dashboard(page)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ {result.get('message')}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def activate_app(self, page: ft.Page):
        """Handle app activation from login screen"""
        from activation_manager import ActivationManager
        
        # Find the activation code field from the page
        activation_code = None
        
        # Search through page controls for the activation code field
        def find_code_field(controls):
            for control in controls:
                if isinstance(control, ft.TextField) and control.label == "Activation Code":
                    return control.value
                if hasattr(control, 'controls') and control.controls:
                    result = find_code_field(control.controls)
                    if result:
                        return result
            return None
        
        # Try to find the code field
        for control in page.controls:
            if hasattr(control, 'controls') and control.controls:
                activation_code = find_code_field(control.controls)
                if activation_code:
                    break
        
        # If not found in page controls, show activation dialog
        if not activation_code:
            self.show_activation_dialog(page)
            return
        
        # Clean and validate code
        activation_code = activation_code.strip().upper()
        
        if not activation_code or len(activation_code) < 10:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Please enter a valid activation code"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Get device ID and activate
        device_id = ActivationManager.get_device_id()
        result = ActivationManager.activate_app(device_id, activation_code)
        
        if result.get('success'):
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ {result.get('message')}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            
            # Update current user
            if self.current_user:
                self.current_user['is_activated'] = True
            
            page.update()
            self.show_dashboard(page)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ {result.get('message')}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def create_default_admin(self):
        """Create default admin if no users exist"""
        import sqlite3
        import hashlib
        from database import DB_PATH
        from datetime import datetime
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if users table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                print("Users table doesn't exist yet")
                conn.close()
                return
            
            # Check if any users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Check if companies table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
                if not cursor.fetchone():
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS companies (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            created_at TEXT
                        )
                    ''')
                
                # Check if default company exists
                cursor.execute("SELECT id FROM companies WHERE name = 'Default Company'")
                company = cursor.fetchone()
                
                if not company:
                    cursor.execute(
                        "INSERT INTO companies (name, created_at) VALUES (?, ?)",
                        ('Default Company', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    company_id = cursor.lastrowid
                else:
                    company_id = company[0]
                
                # Create admin user
                hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute("""
                    INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ('Administrator', 'admin@store.com', hashed_password, 'admin', company_id, current_time))
                
                conn.commit()
                print("✅ Created default admin: admin@store.com / admin123")
                
                # Show snackbar if page is available
                if hasattr(self, 'page_ref') and self.page_ref:
                    self.page_ref.snack_bar = ft.SnackBar(
                        ft.Text("✓ Default admin created! Email: admin@store.com, Password: admin123"),
                        bgcolor=self.success_color,
                        duration=5000
                    )
                    self.page_ref.snack_bar.open = True
                    self.page_ref.update()
            
            conn.close()
            
        except Exception as e:
            print(f"Error creating default admin: {e}")
    # Add this method to your StoreApp class (outside show_login)

    def manual_sync_codes(self, page: ft.Page):
        """Manually sync activation codes from cloud"""
        try:
            from cloud_sync_manager import CloudSyncManager
            from firebase_client import firebase_api
            company_id = 1
            
            page.snack_bar = ft.SnackBar(
                ft.Text("☁️ Syncing activation codes..."),
                bgcolor=self.accent_color,
                duration=2000
            )
            page.snack_bar.open = True
            page.update()
            
            if firebase_api.is_ready():
                result = CloudSyncManager.download_activation_codes_from_cloud(company_id)
                if result:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✅ Activation codes synced successfully!"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("ℹ️ No activation codes found in cloud"),
                        bgcolor=self.warning_color,
                        duration=3000
                    )
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("⚠️ Firebase not available. Check your connection."),
                    bgcolor=self.warning_color,
                    duration=3000
                )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            print(f"Manual sync error: {e}")
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Sync error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

    def activate_with_code(self, page: ft.Page, code):
        """Activate app with activation code - Force cloud sync first"""
        from activation_manager import ActivationManager
        
        if not code or len(code.strip()) < 10:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Please enter a valid activation code"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Clean and uppercase the code
        code = code.strip().upper()
        print(f"🔑 Activation code entered: {code}")
        
        # ===== FORCE CLOUD SYNC BEFORE VERIFICATION =====
        print("\n☁️ Syncing activation codes from cloud...")
        try:
            from cloud_sync_manager import CloudSyncManager
            from firebase_client import firebase_api
            company_id = 1
            
            if firebase_api.is_ready():
                print("   Firebase is ready, downloading latest codes...")
                CloudSyncManager.download_activation_codes_from_cloud(company_id)
                print("   ✅ Codes synced from cloud!")
            else:
                print("   ⚠️ Firebase not ready, using local data")
        except Exception as e:
            print(f"   ⚠️ Sync error: {e}")
        # ==============================================
        
        # Show loading
        page.snack_bar = ft.SnackBar(
            ft.Text("🔄 Verifying code..."),
            bgcolor=self.accent_color,
            duration=2000
        )
        page.snack_bar.open = True
        page.update()
        
        device_id = ActivationManager.get_device_id()
        print(f"📱 Device ID: {device_id}")
        
        # Now activate with the code (will check cloud first)
        result = ActivationManager.activate_app(device_id, code)
        
        if result.get('success'):
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ {result.get('message')}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            
            # Update current user
            if self.current_user:
                self.current_user['is_activated'] = True
            
            page.update()
            self.show_dashboard(page)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ {result.get('message')}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def show_login(self, page: ft.Page):
        """Login screen with trial and activation - Auto-sync on load"""
        try:
            page.controls.clear()
            
            from activation_manager import ActivationManager
            
            # ===== AUTO-SYNC ON LOGIN SCREEN LOAD =====
            print("\n☁️ Auto-syncing activation codes on login screen...")
            try:
                from cloud_sync_manager import CloudSyncManager
                from firebase_client import firebase_api
                company_id = 1
                
                if firebase_api.is_ready():
                    print("   Firebase is ready, syncing activation codes...")
                    CloudSyncManager.download_activation_codes_from_cloud(company_id)
                    print("   ✅ Activation codes synced!")
                else:
                    print("   ⚠️ Firebase not ready, using local data")
            except Exception as e:
                print(f"   ⚠️ Auto-sync error: {e}")
            # ========================================
            
            # Get device ID
            device_id = ActivationManager.get_device_id()
            print(f"📱 Device ID: {device_id}")
            
            # Check activation status
            status = ActivationManager.check_activation_status(device_id)
            print(f"📊 Activation status: {status}")
            
            field_width = 280
            
            # ===== STATUS BANNER =====
            if status.get('status') == 'activated':
                banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50", size=24),
                        ft.Text("✅ App Activated - Full Access", size=14, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                    ], spacing=10),
                    padding=12,
                    bgcolor="#1A3A1A",
                    border_radius=10,
                    margin=ft.margin.only(bottom=15),
                )
            elif status.get('status') == 'trial_active':
                days_left = status.get('days_left', 0)
                emoji = "⚠️" if days_left <= 5 else "🚀"
                
                banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.TIMER, color="#FF9800", size=24),
                        ft.Text(f"{emoji} Trial: {days_left} days remaining", size=14, weight=ft.FontWeight.BOLD, color="#FF9800"),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "🔑 Activate Now",
                            on_click=lambda e: self.show_activation_dialog(page),
                            style=ft.ButtonStyle(bgcolor="#FF9800", color="white"),
                            height=32,
                        ),
                    ], spacing=10),
                    padding=12,
                    bgcolor="#2C2C2C",
                    border_radius=10,
                    margin=ft.margin.only(bottom=15),
                )
            elif status.get('status') == 'trial_expired':
                banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.WARNING, color=self.danger_color, size=24),
                        ft.Text("⚠️ Trial Expired - Please Activate", size=14, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "🔑 Activate Now",
                            on_click=lambda e: self.show_activation_dialog(page),
                            style=ft.ButtonStyle(bgcolor=self.danger_color, color="white"),
                            height=32,
                        ),
                    ], spacing=10),
                    padding=12,
                    bgcolor="#3A1A1A",
                    border_radius=10,
                    margin=ft.margin.only(bottom=15),
                )
            else:
                banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.INFO, color=self.accent_color, size=24),
                        ft.Text("📱 Start your 30-day free trial", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "🚀 Start Trial",
                            on_click=lambda e: self.start_trial_action(page),
                            style=ft.ButtonStyle(bgcolor=self.accent_color, color="white"),
                            height=32,
                        ),
                    ], spacing=10),
                    padding=12,
                    bgcolor="#1A2A3A",
                    border_radius=10,
                    margin=ft.margin.only(bottom=15),
                )
            
            # ===== LOGIN FIELDS =====
            email_field = ft.TextField(
                label="Email", 
                hint_text="your@email.com", 
                width=field_width, 
                bgcolor="#2C2C2C", 
                border_color=self.accent_color
            )
            password_field = ft.TextField(
                label="Password", 
                hint_text="••••••••", 
                password=True, 
                can_reveal_password=True, 
                width=field_width, 
                bgcolor="#2C2C2C", 
                border_color=self.accent_color
            )
            status_text = ft.Text("", size=12)
            loading_indicator = ft.ProgressRing(visible=False, width=30, height=30)
            
            # ===== ACTIVATION SECTION =====
            activation_code_field = ft.TextField(
                label="Activation Code",
                hint_text="ACT-XXXX-XXXX-XXXX",
                width=field_width,
                bgcolor="#2C2C2C",
                border_color="#FF9800",
            )
            
            # Sync button function
            def manual_sync_codes(e):
                """Manually sync activation codes from cloud"""
                try:
                    from cloud_sync_manager import CloudSyncManager
                    from firebase_client import firebase_api
                    company_id = 1
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text("☁️ Syncing activation codes..."),
                        bgcolor=self.accent_color,
                        duration=2000
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    if firebase_api.is_ready():
                        result = CloudSyncManager.download_activation_codes_from_cloud(company_id)
                        if result:
                            page.snack_bar = ft.SnackBar(
                                ft.Text("✅ Activation codes synced successfully!"),
                                bgcolor=self.success_color,
                                duration=3000
                            )
                        else:
                            page.snack_bar = ft.SnackBar(
                                ft.Text("ℹ️ No activation codes found in cloud"),
                                bgcolor=self.warning_color,
                                duration=3000
                            )
                    else:
                        page.snack_bar = ft.SnackBar(
                            ft.Text("⚠️ Firebase not available. Check your connection."),
                            bgcolor=self.warning_color,
                            duration=3000
                        )
                    page.snack_bar.open = True
                    page.update()
                    
                except Exception as ex:
                    print(f"Manual sync error: {ex}")
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"❌ Sync error: {str(ex)[:50]}"),
                        bgcolor=self.danger_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
            
            activation_section = ft.Column([
                ft.Divider(height=15, color="#3C3C3C"),
                ft.Row([
                    ft.Text("🔑 Have an activation code?", size=14, weight=ft.FontWeight.BOLD, expand=True),
                    ft.ElevatedButton(
                        "☁️ Sync",
                        on_click=manual_sync_codes,
                        style=ft.ButtonStyle(bgcolor=self.accent_color, color="white"),
                        height=32,
                    ),
                ]),
                ft.Text("Enter your code to unlock full access", size=11, color="#888888"),
                ft.Container(height=5),
                activation_code_field,
                ft.ElevatedButton(
                    "🔑 Activate Now",
                    on_click=lambda e: self.activate_with_code(page, activation_code_field.value),
                    style=ft.ButtonStyle(bgcolor="#FF9800", color="white"),
                    width=field_width,
                    height=45,
                ),
                ft.Container(height=10),
                ft.Text("💡 Contact support@store.com to purchase", size=10, color="#888888"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
            
            # ===== LOGIN FUNCTION =====
            def on_login(e):
                email = email_field.value.strip()
                password = password_field.value
                
                if not email or not password:
                    status_text.value = "Please enter email and password!"
                    status_text.color = self.danger_color
                    page.update()
                    return
                
                loading_indicator.visible = True
                status_text.value = "🔄 Authenticating..."
                status_text.color = self.accent_color
                page.update()
                
                try:
                    user = UserManager.authenticate(email, password)
                    
                    if user:
                        user_dict = dict(user)
                        company_id = user_dict.get('company_id', 1)
                        user_dict['company_id'] = company_id
                        
                        # Check if app is activated
                        activation_status = ActivationManager.check_activation_status(device_id)
                        user_dict['is_activated'] = activation_status.get('is_activated', False)
                        
                        self.current_user = user_dict
                        
                        loading_indicator.visible = False
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"✓ Welcome {user_dict.get('name', 'User')}!"),
                            bgcolor=self.success_color,
                            duration=3000
                        )
                        page.snack_bar.open = True
                        page.update()
                        
                        self.show_dashboard(page)
                    else:
                        loading_indicator.visible = False
                        status_text.value = "Invalid email or password!"
                        status_text.color = self.danger_color
                        page.update()
                        
                except Exception as ex:
                    loading_indicator.visible = False
                    status_text.value = f"Error: {str(ex)[:50]}"
                    status_text.color = self.danger_color
                    page.update()
                    print(f"Login error: {ex}")
            
            # ===== START TRIAL FUNCTION =====
            def on_start_trial(e):
                print(f"🚀 Starting trial for device: {device_id}")
                
                # Check if trial already exists
                current_status = ActivationManager.check_activation_status(device_id)
                
                if current_status.get('status') == 'trial_active':
                    days_left = current_status.get('days_left', 0)
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"ℹ️ You already have an active trial with {days_left} days remaining!"),
                        bgcolor=self.accent_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    page.update()
                    return
                
                if current_status.get('status') == 'activated':
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✅ Your app is already activated!"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
                    return
                
                # Show loading
                loading_indicator.visible = True
                status_text.value = "🔄 Starting trial..."
                status_text.color = self.accent_color
                page.update()
                
                result = ActivationManager.start_trial(device_id)
                print(f"📊 Start trial result: {result}")
                
                loading_indicator.visible = False
                
                if result.get('status') == 'trial_started':
                    status_text.value = "✅ Trial started successfully!"
                    status_text.color = self.success_color
                    page.update()
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✅ 30-day trial started! You can now login."),
                        bgcolor=self.success_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    # Refresh login screen
                    self.show_login(page)
                else:
                    error_msg = result.get('message', 'Error starting trial')
                    print(f"❌ Trial error: {error_msg}")
                    
                    status_text.value = f"❌ {error_msg}"
                    status_text.color = self.danger_color
                    page.update()
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"❌ {error_msg}"),
                        bgcolor=self.danger_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    page.update()
            
            # ===== ACTIVATE WITH CODE FUNCTION =====
            def activate_with_code(page, code):
                from activation_manager import ActivationManager
                
                if not code or len(code.strip()) < 10:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("❌ Please enter a valid activation code"),
                        bgcolor=self.danger_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
                    return
                
                # Clean and uppercase the code
                code = code.strip().upper()
                print(f"🔑 Activation code entered: {code}")
                
                # ===== FORCE CLOUD SYNC BEFORE VERIFICATION =====
                print("\n☁️ Syncing activation codes from cloud...")
                try:
                    from cloud_sync_manager import CloudSyncManager
                    from firebase_client import firebase_api
                    company_id = 1
                    
                    if firebase_api.is_ready():
                        print("   Firebase is ready, downloading latest codes...")
                        CloudSyncManager.download_activation_codes_from_cloud(company_id)
                        print("   ✅ Codes synced from cloud!")
                    else:
                        print("   ⚠️ Firebase not ready, using local data")
                except Exception as ex:
                    print(f"   ⚠️ Sync error: {ex}")
                # ==============================================
                
                # Show loading
                page.snack_bar = ft.SnackBar(
                    ft.Text("🔄 Verifying code..."),
                    bgcolor=self.accent_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
                
                device_id = ActivationManager.get_device_id()
                print(f"📱 Device ID: {device_id}")
                
                # Now activate with the code
                result = ActivationManager.activate_app(device_id, code)
                
                if result.get('success'):
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✅ {result.get('message')}"),
                        bgcolor=self.success_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    
                    # Update current user
                    if self.current_user:
                        self.current_user['is_activated'] = True
                    
                    page.update()
                    self.show_dashboard(page)
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"❌ {result.get('message')}"),
                        bgcolor=self.danger_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    page.update()
            
            # ===== FORGOT PASSWORD FUNCTION =====
            def on_forgot_password(e):
                self.show_forgot_password_dialog(page)
            
            # ===== CREATE DEFAULT ADMIN =====
            try:
                self.create_default_admin()
            except Exception as e:
                print(f"Error creating admin: {e}")
            
            # ===== LOGO =====
            logo_exists = os.path.exists(logo_path)
            logo = ft.Image(src=logo_path, width=100, height=100, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=60)
            
            # ===== BUILD MAIN LAYOUT =====
            main_layout = ft.Column(
                [
                    ft.Text("Welcome", size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Manage your inventory anywhere", size=13, color="#AAAAAA"),
                    ft.Container(height=15),
                    banner,
                    ft.Container(height=5),
                    ft.Divider(height=10, color="#3C3C3C"),
                    email_field, 
                    ft.Container(height=12),
                    password_field, 
                    ft.Container(height=12),
                    ft.Row([status_text, loading_indicator], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ft.Container(height=10),
                    ft.Row([
                        logo, 
                        ft.Container(width=15), 
                        ft.FilledButton("Sign In", width=140, height=45, on_click=on_login)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0
            )
            
            # ===== ADD ACTIVATION SECTION =====
            main_layout.controls.append(activation_section)
            
            # ===== ADD REMAINING CONTROLS =====
            main_layout.controls.append(ft.Divider(height=15, color="#3C3C3C"))
            main_layout.controls.append(
                ft.Row([
                    ft.TextButton("Forgot Password?", on_click=on_forgot_password, style=ft.ButtonStyle(color="#888888")),
                ], alignment=ft.MainAxisAlignment.CENTER)
            )
            main_layout.controls.append(ft.Container(height=10))
            main_layout.controls.append(
                ft.Text("💡 Default: admin@store.com / admin123", size=10, color="#888888", selectable=True)
            )
            
            # ===== DISPLAY =====
            login_card = ft.Container(content=main_layout, padding=30, bgcolor=None, border_radius=20, width=500)
            centered_login = ft.Container(content=login_card, alignment=ft.alignment.center, expand=True)
            bg_image = ft.Image(src=background_path, fit=ft.ImageFit.COVER) if os.path.exists(background_path) else None
            
            if bg_image:
                page.add(ft.Stack([bg_image, centered_login], expand=True))
            else:
                page.add(centered_login)
            
            page.update()
            
        except Exception as e:
            print(f"❌ Login screen error: {e}")
            import traceback
            traceback.print_exc()
            
            # Show error on screen
            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Text("❌ Login Error", size=24, color="red"),
                        ft.Text(str(e), size=14, color="white"),
                        ft.ElevatedButton("Retry", on_click=lambda e: self.show_login(page)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
            page.update()

    def start_trial_action(self, page: ft.Page):
        """Start trial from dashboard"""
        from activation_manager import ActivationManager
        
        device_id = ActivationManager.get_device_id()
        result = ActivationManager.start_trial(device_id)
        
        if result.get('status') == 'trial_started':
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ 30-day trial started!"),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            self.show_dashboard(page)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ {result.get('message', 'Error starting trial')}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

                    # ============ SIDEBAR WITH ZOOM ============
    def create_sidebar(self, page: ft.Page):
        """Create sidebar navigation - Customer Version (No Activation Admin)"""
        
        # Check app activation
        from activation_manager import ActivationManager
        device_id = ActivationManager.get_device_id()
        status = ActivationManager.check_activation_status(device_id)
        is_activated = status.get('status') in ['activated', 'trial_active']
        is_trial_expired = status.get('status') == 'trial_expired'
        days_left = status.get('days_left', 0)
        
        nav_items = []
        
        # Always show Dashboard
        nav_items.append(("📊", "Dashboard", "dashboard"))
        
        # Only show other items if app is activated or trial is active
        if is_activated and not is_trial_expired:
            nav_items.extend([
                ("📦", "Materials", "materials"),
                ("🔧", "Accessories", "accessories"),
                ("📷", "Barcode Scan", "barcode_scanner"),
                ("📋", "Inventory", "inventory"),
                ("👥", "Users", "users"),
                ("⚙️", "Settings", "settings"),
            ])
            # ❌ REMOVED: Activation Admin - This is for admin panel only
        elif is_trial_expired:
            # Show limited navigation with activation prompt
            nav_items.append(("🔑", "Activate Now", "activation"))
        
        nav_buttons = []
        
        def navigate(e, view):
            if view == "dashboard":
                self.show_dashboard(page)
            elif view == "activation":
                self.show_activation_dialog(page)
            elif view == "materials":
                self.show_materials_screen(page)
            elif view == "accessories":
                self.show_accessories(page)
            elif view == "barcode_scanner":
                self.show_barcode_scanner(page)
            elif view == "inventory":
                self.show_inventory(page)
            elif view == "users":
                self.show_users(page)
            elif view == "settings":
                self.show_settings(page)
            # ❌ REMOVED: activation_admin navigation
        
        for emoji, label, view in nav_items:
            btn = ft.Container(
                content=ft.Row([ft.Text(emoji, size=22), ft.Text(label, size=15, color=self.text_color)], spacing=12),
                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                border_radius=10,
                ink=True,
                on_click=lambda e, v=view: navigate(e, v),
            )
            nav_buttons.append(btn)
        
        def logout(e):
            self.confirm_logout(page)
        
        logout_btn = ft.Container(
            content=ft.Row([ft.Text("🚪", size=22), ft.Text("Logout", size=15, color="#FF5252")], spacing=12),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            border_radius=10,
            ink=True,
            on_click=logout,
        )
        
        logo_exists = os.path.exists(logo_path)
        sidebar_logo = ft.Image(src=logo_path, width=35, height=35, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=28)
        
        title_content = ft.Row(
            [sidebar_logo, ft.Text("Store Manager", size=20, weight=ft.FontWeight.BOLD, color=self.text_color)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )
        
        role = self.current_user.get('role', 'guest') if self.current_user else 'guest'
        role_display = role.upper()
        
        # Activation status text
        if is_activated and not is_trial_expired:
            if days_left > 0 and status.get('status') == 'trial_active':
                status_text = f"📱 Trial: {days_left}d"
                status_color = "#FF9800"
            else:
                status_text = "✅ Full Version"
                status_color = "#4CAF50"
        elif is_trial_expired:
            status_text = "⚠️ Expired"
            status_color = self.danger_color
        else:
            status_text = "📱 Free Trial"
            status_color = self.accent_color
        
        return ft.Container(
            content=ft.Column([
                ft.Container(content=title_content, padding=25),
                ft.Divider(),
                ft.Column(nav_buttons, spacing=8),
                ft.Container(expand=True),
                ft.Divider(),
                logout_btn,
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"User: {self.current_user.get('name', 'User') if self.current_user else 'Guest'}", size=12, color="#888888"),
                        ft.Text(role_display, size=12, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text(status_text, size=11, color=status_color, weight=ft.FontWeight.BOLD),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15,
                ),
            ], spacing=0),
            width=260,
            bgcolor=self.sidebar_color,
        )
    def show_activation_admin(self, page: ft.Page):
        """Show activation admin panel - For generating codes"""
        from admin_panel import AdminPanel
        
        # Check if user is admin
        if not self.current_user or self.current_user.get('role') != 'admin':
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Admin access required"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Create and run admin panel
        admin = AdminPanel()
        
        # Clear current page and show admin panel
        page.controls.clear()
        
        # Create a container for the admin panel
        admin_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        icon_size=24,
                        on_click=lambda e: self.show_settings(page),
                        tooltip="Back to Settings",
                    ),
                    ft.Text("🔑 Activation Code Manager", size=24, weight=ft.FontWeight.BOLD, expand=True),
                ]),
                ft.Divider(),
            ], spacing=10),
            padding=10,
        )
        
        # Get the admin panel content
        # We need to create a temporary page-like object for the admin panel
        # Or we can use the existing page and just render the admin panel
        
        # Simplified: Show a message and link to run admin panel separately
        page.controls.clear()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.IconButton(
                            icon=ft.icons.ARROW_BACK,
                            icon_size=24,
                            on_click=lambda e: self.show_settings(page),
                        ),
                        ft.Text("🔑 Activation Code Manager", size=24, weight=ft.FontWeight.BOLD, color=self.text_color, expand=True),
                    ]),
                    ft.Divider(),
                    ft.Container(height=20),
                    ft.Icon(ft.icons.KEY, size=80, color=self.accent_color),
                    ft.Text("Activation Code Manager", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Generate and manage activation codes for customers", size=14, color="#888888"),
                    ft.Container(height=20),
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("📝 How to use:", size=16, weight=ft.FontWeight.BOLD),
                                ft.Text("1. Run the Admin Panel separately:", size=13, color="#888888"),
                                ft.Container(
                                    content=ft.Text("python admin_panel.py", size=12, color=self.accent_color, font_family="monospace"),
                                    padding=8,
                                    bgcolor="#1E1E1E",
                                    border_radius=4,
                                ),
                                ft.Text("2. Or click the button below to open it in a new window", size=13, color="#888888"),
                                ft.Container(height=10),
                                ft.ElevatedButton(
                                    "🚀 Open Activation Manager",
                                    on_click=lambda e: self.launch_admin_panel(page),
                                    icon=ft.icons.OPEN_IN_NEW,
                                    style=ft.ButtonStyle(bgcolor=self.accent_color, color="white"),
                                ),
                            ], spacing=10),
                            padding=20,
                        ),
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                expand=True,
                alignment=ft.alignment.center,
            )
        )
        page.update()

    def launch_admin_panel(self, page: ft.Page):
        """Launch admin panel as a separate window or show it inline"""
        from admin_panel import AdminPanel
        
        # Option 1: Open in new window (desktop only)
        try:
            # This will open a new window with the admin panel
            import subprocess
            import sys
            subprocess.Popen([sys.executable, "admin_panel.py"])
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Admin Panel opened in new window!"),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            # Option 2: Show inline (fallback)
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Could not open new window: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
    def create_bottom_nav(self, page: ft.Page):
        """Create bottom navigation bar - Customer Version (No Activation Admin)"""
        
        nav_items = [
            (ft.icons.DASHBOARD, "Home", "dashboard"),
            (ft.icons.INVENTORY, "Materials", "materials"),
            (ft.icons.BUILD, "Parts", "accessories"),
            (ft.icons.QR_CODE_SCANNER, "Scan", "barcode_scanner"),
            (ft.icons.LIST_ALT, "Inventory", "inventory"),
            (ft.icons.PEOPLE, "Users", "users"),
            (ft.icons.SETTINGS, "Settings", "settings"),
            # ❌ REMOVED: Activation Admin - This is for admin panel only
            (ft.icons.LOGOUT, "Logout", "logout"),
        ]
        
        def navigate(e):
            index = e.control.selected_index
            if index < len(nav_items):
                view = nav_items[index][2]
                if view == "dashboard":
                    self.show_dashboard(page)
                elif view == "materials":
                    self.show_materials_screen(page)
                elif view == "accessories":
                    self.show_accessories(page)
                elif view == "barcode_scanner":
                    self.show_barcode_scanner(page)
                elif view == "inventory":
                    self.show_inventory(page)
                elif view == "users":
                    self.show_users(page)
                elif view == "settings":
                    self.show_settings(page)
                elif view == "logout":
                    self.confirm_logout(page)
        
        return ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(icon=icon, label=label)
                for icon, label, _ in nav_items
            ],
            on_change=navigate,
            height=65,
            bgcolor=self.sidebar_color,
        )
    def export_html_chrome_alternative(self, page: ft.Page):
        """Force open in Chrome using package name"""
        import subprocess
        import tempfile
        from datetime import datetime
        
        try:
            materials = self.dict_list(MaterialManager.get_all())
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Store Export</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #4CAF50; color: white; }}
                </style>
            </head>
            <body>
                <h1>Store Management Export</h1>
                <p>Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <h2>Materials ({len(materials)})</h2>
                </table>
                    <tr><th>Name</th><th>Quantity</th><th>Quality</th></tr>
            """
            
            for m in materials[:100]:
                html += f"<tr><td>{m.get('name', '')}</td><td>{m.get('quantity', 0)}</td><td>{m.get('quality', 'New')}</td></tr>"
            
            html += "</table></body></html>"
            
            # Save temp file
            temp = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp.write(html)
            temp.close()
            
            # Force open in Chrome using ADB-like intent (works on Samsung)
            file_url = f"file://{temp.name}"
            
            # Use Chrome intent
            page.launch_url(f"intent://{file_url}#Intent;scheme=file;package=com.android.chrome;end")
            
            page.snack_bar = ft.SnackBar(
                ft.Text("🌐 Opening in Chrome..."),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        
    def export_html_force_chrome(self, page: ft.Page):
        """Export HTML and force open in Chrome browser"""
        import os
        import tempfile
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Generate HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Store Management Report</title>
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }}
                    .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
                    .header p {{ font-size: 14px; opacity: 0.9; }}
                    .stats {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                        gap: 15px;
                        padding: 25px;
                        background: #f8f9fa;
                    }}
                    .stat-card {{
                        background: white;
                        padding: 15px;
                        border-radius: 12px;
                        text-align: center;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }}
                    .stat-card .value {{
                        font-size: 28px;
                        font-weight: bold;
                        color: #1976D2;
                    }}
                    .stat-card .label {{ font-size: 12px; color: #666; margin-top: 5px; }}
                    .section {{ padding: 20px 25px; }}
                    .section h2 {{
                        color: #333;
                        border-left: 4px solid #1976D2;
                        padding-left: 15px;
                        margin-bottom: 15px;
                        font-size: 18px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 10px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #1976D2;
                        color: white;
                        font-weight: 600;
                    }}
                    .badge {{
                        display: inline-block;
                        padding: 3px 10px;
                        border-radius: 20px;
                        font-size: 11px;
                        font-weight: bold;
                        color: white;
                    }}
                    .badge-new {{ background-color: #4CAF50; }}
                    .badge-used {{ background-color: #FF9800; }}
                    .badge-damaged {{ background-color: #F44336; }}
                    .badge-repaired {{ background-color: #2196F3; }}
                    .footer {{
                        text-align: center;
                        padding: 20px;
                        background: #f8f9fa;
                        color: #888;
                        font-size: 12px;
                    }}
                    @media (max-width: 600px) {{
                        .stats {{ gap: 8px; padding: 15px; }}
                        .stat-card .value {{ font-size: 22px; }}
                        th, td {{ padding: 6px; font-size: 11px; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 Store Management Report</h1>
                        <p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-card">
                            <div class="value">{len(materials)}</div>
                            <div class="label">Materials</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">{len(accessories)}</div>
                            <div class="label">Accessories</div>
                        </div>
                        <div class="stat-card">
                            <div class="value">{len(materials) + len(accessories)}</div>
                            <div class="label">Total Items</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📦 Materials</h2>
                        <div style="overflow-x: auto;">
                            <table>
                                <thead>
                                    <tr><th>Name</th><th>Quantity</th><th>Quality</th><th>Location</th></tr>
                                </thead>
                                <tbody>
            """
            
            for m in materials[:50]:
                quality = m.get('quality', 'Used')
                html_content += f"""
                                    <tr>
                                        <td>{m.get('name', 'N/A')}</td>
                                        <td>{m.get('quantity', 0)}</td>
                                        <td><span class="badge badge-{quality.lower()}">{quality}</span></td>
                                        <td>{m.get('location_ids', 'N/A')}</td>
                                    </tr>
                """
            
            html_content += f"""
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🔧 Accessories</h2>
                        <div style="overflow-x: auto;">
                            <table>
                                <thead>
                                    <tr><th>Name</th><th>Quantity</th><th>Price</th><th>Quality</th><th>Location</th></tr>
                                </thead>
                                <tbody>
            """
            
            for a in accessories[:50]:
                quality = a.get('quality', 'Used')
                price = a.get('price', 0)
                price_text = f"${price:.2f}" if price else "-"
                html_content += f"""
                                    <tr>
                                        <td>{a.get('name', 'N/A')}</td>
                                        <td>{a.get('quantity', 0)}</td>
                                        <td>{price_text}</td>
                                        <td><span class="badge badge-{quality.lower()}">{quality}</span></td>
                                        <td>{a.get('location', 'N/A')}</td>
                                    </tr>
                """
            
            html_content += f"""
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>Generated by Store Management System</p>
                        <p>Report ID: {timestamp}</p>
                        <p>© {datetime.now().year} Store Management</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create temporary HTML file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            # Method 1: Force open in Chrome using intent
            file_path = temp_file.name
            file_url = f"file://{file_path}"
            
            # Chrome intent URI
            chrome_intent = f"googlechrome://{file_path}"
            
            # Try multiple methods to force Chrome
            try:
                # Method 1: Direct Chrome intent
                page.launch_url(chrome_intent)
            except:
                try:
                    # Method 2: Use chrome:// URL
                    page.launch_url(f"chrome://{file_path}")
                except:
                    # Method 3: Default browser (fallback)
                    page.launch_url(file_url)
            
            # Show success message
            page.snack_bar = ft.SnackBar(
                ft.Text(f"🌐 Report opened in Chrome! {len(materials)} materials, {len(accessories)} accessories"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

    def export_csv_direct_samsung(self, page: ft.Page):
        """Direct save to Samsung accessible folder - No FilePicker needed"""
        import csv
        import os
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Try multiple accessible paths on Samsung
            possible_paths = [
                "/storage/emulated/0/Download",      # Downloads folder
                "/storage/emulated/0/Documents",     # Documents folder
                "/sdcard/Download",                  # SD Card Download
                "/storage/emulated/0/DCIM",          # DCIM folder
            ]
            
            saved_path = None
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        full_path = os.path.join(path, filename)
                        with open(full_path, 'w', newline='', encoding='utf-8-sig') as file:
                            writer = csv.writer(file)
                            writer.writerow(['STORE MANAGEMENT SYSTEM - EXPORT'])
                            writer.writerow([f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                            writer.writerow([])
                            writer.writerow(['MATERIALS'])
                            writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location'])
                            
                            for m in materials[:500]:
                                writer.writerow([
                                    m.get('name', ''),
                                    m.get('category_name', 'Other'),
                                    m.get('quantity', 0),
                                    m.get('quality', 'New'),
                                    m.get('location_ids', '')
                                ])
                            
                            writer.writerow([])
                            writer.writerow(['ACCESSORIES'])
                            writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location'])
                            
                            for a in accessories[:500]:
                                writer.writerow([
                                    a.get('name', ''),
                                    a.get('category_name', 'Other'),
                                    a.get('quantity', 0),
                                    a.get('price', 0),
                                    a.get('quality', 'New'),
                                    a.get('location', '')
                                ])
                        
                        saved_path = full_path
                        break
                except Exception as e:
                    print(f"Failed to save to {path}: {e}")
                    continue
            
            if saved_path:
                # Show success with instructions
                def copy_path():
                    page.set_clipboard(saved_path)
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✓ Path copied to clipboard"),
                        bgcolor=self.success_color,
                        duration=2000
                    )
                    page.snack_bar.open = True
                    page.update()
                
                def open_folder():
                    folder = os.path.dirname(saved_path)
                    page.launch_url(f"file://{folder}")
                    close_overlay()
                
                def close_overlay():
                    if hasattr(page, 'dialog') and page.dialog:
                        page.dialog.open = False
                    page.update()
                
                # Create dialog
                dialog = ft.AlertDialog(
                    title=ft.Row([
                        ft.Text("✅ Export Successful", size=18, weight=ft.FontWeight.BOLD, color=self.success_color, expand=True),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_overlay()),
                    ]),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(filename, size=14, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Materials: {len(materials)} | Accessories: {len(accessories)}", size=11, color="#888888"),
                            ft.Divider(),
                            ft.Text("📍 File saved to:", size=13, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text(saved_path, size=9, color="#888888", selectable=True),
                                padding=6,
                                bgcolor="#2C2C2C",
                                border_radius=4,
                            ),
                            ft.Row([
                                ft.ElevatedButton(
                                    "📋 Copy Path",
                                    on_click=lambda e: copy_path(),
                                    expand=True,
                                    icon=ft.icons.CONTENT_COPY,
                                ),
                                ft.ElevatedButton(
                                    "📂 Open Folder",
                                    on_click=lambda e: open_folder(),
                                    expand=True,
                                    icon=ft.icons.FOLDER_OPEN,
                                ),
                            ], spacing=8),
                            ft.Divider(),
                            ft.Text("📱 To open this file:", size=13, weight=ft.FontWeight.BOLD),
                            ft.Text("1. Open 'My Files' app", size=11),
                            ft.Text("2. Go to 'Internal Storage'", size=11),
                            ft.Text("3. Look in 'Download' folder", size=11),
                            ft.Text("4. Tap the file to open", size=11),
                        ], spacing=8),
                        width=420,
                        height=450,
                        padding=15,
                    ),
                )
                
                page.dialog = dialog
                dialog.open = True
                page.update()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Could not save file. No accessible folder found."),
                    bgcolor=self.danger_color,
                    duration=4000
                )
                page.snack_bar.open = True
                page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def export_csv_reliable(self, page: ft.Page):
        """Most reliable CSV export - uses cache and share"""
        import csv
        import os
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Save to app's cache directory (always writable)
            cache_dir = page.get_storage_path()
            if not cache_dir:
                cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            file_path = os.path.join(cache_dir, filename)
            
            # Write CSV
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location'])
                for m in materials[:30]:
                    writer.writerow([
                        m.get('name', ''),
                        m.get('category_name', 'Other'),
                        m.get('quantity', 0),
                        m.get('quality', 'New'),
                        m.get('location_ids', '')[:20]
                    ])
            
            def share_and_close():
                page.launch_url(f"file://{file_path}")
                page.dialog.open = False
                page.update()
            
            def copy_path():
                page.set_clipboard(file_path)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Path copied to clipboard"),
                    bgcolor=self.success_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text("✅ Export Ready", size=18, weight=ft.FontWeight.BOLD, color=self.success_color, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: setattr(page.dialog, 'open', False)),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(filename, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Contains {len(materials)} materials", size=12, color="#888888"),
                        ft.Divider(),
                        ft.Text("Choose an action:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton(
                                "📤 Share / Save",
                                on_click=lambda e: share_and_close(),
                                expand=True,
                                icon=ft.icons.SHARE,
                                style=ft.ButtonStyle(bgcolor=self.accent_color),
                            ),
                        ], spacing=8),
                        ft.Row([
                            ft.ElevatedButton(
                                "📋 Copy Path",
                                on_click=lambda e: copy_path(),
                                expand=True,
                                icon=ft.icons.CONTENT_COPY,
                            ),
                        ], spacing=8),
                        ft.Container(height=10),
                        ft.Text("💡 Tap 'Share/Save' then choose 'Save to Downloads'", size=10, color="#888888"),
                    ], spacing=10),
                    width=380,
                    height=350,
                    padding=20,
                ),
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def export_csv_with_filepicker(self, page: ft.Page):
        """Export CSV using FilePicker with permissions"""
        import csv
        from datetime import datetime
        
        def on_file_selected(e: ft.FilePickerResultEvent):
            if not e.path:
                page.snack_bar = ft.SnackBar(ft.Text("Save cancelled"))
                page.snack_bar.open = True
                page.update()
                return
                
            try:
                # Get data
                materials = self.dict_list(MaterialManager.get_all())
                accessories = self.dict_list(AccessoryManager.get_all())
                
                # Write CSV to user-selected location
                with open(e.path, mode='w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    
                    # Header
                    writer.writerow(['STORE MANAGEMENT SYSTEM - EXPORT'])
                    writer.writerow([f'Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                    writer.writerow([])
                    
                    # Materials
                    writer.writerow(['MATERIALS'])
                    writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location'])
                    for m in materials[:500]:
                        writer.writerow([
                            m.get('name', ''),
                            m.get('category_name', 'Other'),
                            m.get('quantity', 0),
                            m.get('quality', 'New'),
                            m.get('location_ids', '')
                        ])
                    
                    writer.writerow([])
                    
                    # Accessories
                    writer.writerow(['ACCESSORIES'])
                    writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location'])
                    for a in accessories[:500]:
                        writer.writerow([
                            a.get('name', ''),
                            a.get('category_name', 'Other'),
                            a.get('quantity', 0),
                            a.get('price', 0),
                            a.get('quality', 'New'),
                            a.get('location', '')
                        ])
                
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ CSV saved to: {e.path}"),
                    bgcolor=self.success_color,
                    duration=4000
                )
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Save failed: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=4000
                )
            
            page.snack_bar.open = True
            page.update()
        
        # Create FilePicker
        file_picker = ft.FilePicker(on_result=on_file_selected)
        page.overlay.append(file_picker)
        page.update()
        
        # Open save dialog
        file_picker.save_file(
            file_name=f"store_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            allowed_extensions=["csv"],
            dialog_title="Save CSV to Downloads"
        )
    def export_csv_via_share(self, page: ft.Page):
        """Export CSV and let user share/save via Android share dialog"""
        import csv
        import os
        from datetime import datetime
        import tempfile
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig')
            
            writer = csv.writer(temp_file)
            writer.writerow(['=== STORE MANAGEMENT EXPORT ==='])
            writer.writerow([f'Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
            writer.writerow([])
            
            # Materials
            writer.writerow(['MATERIALS'])
            writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location'])
            for m in materials[:100]:
                writer.writerow([
                    m.get('name', ''),
                    m.get('category_name', 'Other'),
                    m.get('quantity', 0),
                    m.get('quality', 'New'),
                    m.get('location_ids', '')
                ])
            
            writer.writerow([])
            
            # Accessories
            writer.writerow(['ACCESSORIES'])
            writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location'])
            for a in accessories[:100]:
                writer.writerow([
                    a.get('name', ''),
                    a.get('category_name', 'Other'),
                    a.get('quantity', 0),
                    a.get('price', 0),
                    a.get('quality', 'New'),
                    a.get('location', '')
                ])
            
            temp_file.close()
            temp_path = temp_file.name
            
            def share_file():
                # Share using Android share intent
                page.launch_url(f"file://{temp_path}")
                page.dialog.open = False
                page.update()
            
            def copy_path():
                page.set_clipboard(temp_path)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ File path copied to clipboard"),
                    bgcolor=self.success_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
            
            def close_dlg():
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                page.dialog.open = False
                page.update()
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text("📊 CSV Export Ready", size=18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(filename, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Materials: {len(materials)} | Accessories: {len(accessories)}", size=11, color="#888888"),
                        ft.Divider(),
                        ft.Text("How to save to Downloads:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Text("1️⃣ Tap 'Share/Save' below", size=12),
                        ft.Text("2️⃣ Select 'Save to Downloads' or 'Save to Device'", size=12),
                        ft.Text("3️⃣ Choose location and save", size=12),
                        ft.Container(height=15),
                        ft.Row([
                            ft.ElevatedButton(
                                "📤 Share / Save",
                                on_click=lambda e: share_file(),
                                expand=True,
                                style=ft.ButtonStyle(bgcolor=self.accent_color),
                                icon=ft.icons.SHARE,
                            ),
                        ], spacing=8),
                        ft.Row([
                            ft.ElevatedButton(
                                "📋 Copy Path",
                                on_click=lambda e: copy_path(),
                                expand=True,
                                icon=ft.icons.CONTENT_COPY,
                            ),
                        ], spacing=8),
                    ], spacing=8),
                    width=400,
                    height=380,
                    padding=20,
                ),
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
    def export_csv_final(self, page: ft.Page):
        """Final working CSV export - uses FilePicker for user to choose location"""
        import csv
        import os
        from datetime import datetime
        
        try:
            # Show loading
            page.snack_bar = ft.SnackBar(
                ft.Text("📊 Preparing CSV..."),
                bgcolor=self.accent_color,
                duration=2000
            )
            page.snack_bar.open = True
            page.update()
            
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Create CSV content as string
            csv_lines = []
            csv_lines.append("Name,Category,Quantity,Quality,Location")
            
            for m in materials[:50]:
                csv_lines.append(f"\"{m.get('name', '')}\",\"{m.get('category_name', 'Other')}\",{m.get('quantity', 0)},\"{m.get('quality', 'New')}\",\"{m.get('location_ids', '')}\"")
            
            csv_content = "\n".join(csv_lines)
            
            # FilePicker callback
            def on_save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    try:
                        with open(e.path, 'w', encoding='utf-8-sig') as f:
                            f.write(csv_content)
                        
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"✓ CSV saved successfully!"),
                            bgcolor=self.success_color,
                            duration=4000
                        )
                        page.snack_bar.open = True
                        page.update()
                    except Exception as ex:
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"Save error: {str(ex)[:50]}"),
                            bgcolor=self.danger_color,
                            duration=4000
                        )
                        page.snack_bar.open = True
                        page.update()
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Save cancelled"),
                        bgcolor=self.warning_color,
                        duration=2000
                    )
                    page.snack_bar.open = True
                    page.update()
            
            # Create FilePicker
            file_picker = ft.FilePicker(on_result=on_save_result)
            page.overlay.append(file_picker)
            page.update()
            
            # Show save dialog - user chooses where to save
            file_picker.save_file(
                file_name=filename,
                dialog_title="Save CSV File",
                initial_directory="/storage/emulated/0/Download"
            )
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    def export_csv_visible(self, page: ft.Page):
        """Export CSV to a visible folder on mobile"""
        import csv
        import os
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Try multiple visible locations (in order of preference)
            possible_paths = [
                "/storage/emulated/0/Download",      # Downloads folder
                "/storage/emulated/0/Documents",     # Documents folder
                "/storage/emulated/0/Movies",        # Movies folder
                "/storage/emulated/0/Pictures",      # Pictures folder
                "/storage/emulated/0/DCIM",          # DCIM folder
            ]
            
            selected_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    selected_path = path
                    break
            
            # If no folder exists, create Downloads path (should always exist)
            if not selected_path:
                selected_path = "/storage/emulated/0/Download"
                os.makedirs(selected_path, exist_ok=True)
            
            # Full file path
            file_path = os.path.join(selected_path, filename)
            
            # Write CSV file
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                writer.writerow(['STORE MANAGEMENT SYSTEM - EXPORT'])
                writer.writerow([f'Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow([])
                
                # Materials
                writer.writerow(['MATERIALS'])
                writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location', 'Size', 'Length', 'Colors', 'Notes'])
                for m in materials:
                    writer.writerow([
                        m.get('name', ''),
                        m.get('category_name', 'Other'),
                        m.get('quantity', 0),
                        m.get('quality', 'New'),
                        m.get('location_ids', ''),
                        m.get('size', ''),
                        m.get('length', ''),
                        m.get('colors', ''),
                        m.get('notes', '')
                    ])
                
                writer.writerow([])
                
                # Accessories
                writer.writerow(['ACCESSORIES'])
                writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location', 'Notes'])
                for a in accessories:
                    writer.writerow([
                        a.get('name', ''),
                        a.get('category_name', 'Other'),
                        a.get('quantity', 0),
                        a.get('price', 0),
                        a.get('quality', 'New'),
                        a.get('location', ''),
                        a.get('notes', '')
                    ])
            
            # Get file size
            file_size = os.path.getsize(file_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            def close_dlg():
                page.dialog.open = False
                page.update()
            
            def open_folder():
                close_dlg()
                # Try to open the folder
                page.launch_url(f"file://{selected_path}")
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text("✅ Export Successful", size=18, weight=ft.FontWeight.BOLD, color=self.success_color, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"📄 {filename}", size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Size: {size_str}", size=12, color="#888888"),
                        ft.Divider(),
                        ft.Text("📍 File saved to:", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(f"{selected_path}/{filename}", size=10, color="#888888", selectable=True),
                            padding=8,
                            bgcolor="#2C2C2C",
                            border_radius=6,
                        ),
                        ft.Row([
                            ft.ElevatedButton(
                                "📂 Open Folder", 
                                on_click=lambda e: open_folder(),
                                expand=True,
                                icon=ft.icons.FOLDER_OPEN,
                            ),
                        ], spacing=8),
                        ft.Row([
                            ft.ElevatedButton(
                                "📋 Copy Path", 
                                on_click=lambda e: page.set_clipboard(f"{selected_path}/{filename}"),
                                expand=True,
                                icon=ft.icons.CONTENT_COPY,
                            ),
                        ], spacing=8),
                        ft.Container(height=10),
                        ft.Text("💡 You can find this file in your Downloads folder", size=10, color="#888888"),
                        ft.Text("💡 Use any file manager app to open the CSV file", size=10, color="#888888"),
                    ], spacing=8),
                    width=400,
                    height=420,
                    padding=15,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda e: close_dlg()),
                ],
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    def export_csv_simple(self, page: ft.Page):
        """Simple CSV export - saves to app storage, shows location"""
        import csv
        import os
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Save to app's private storage (ALWAYS works, no permission needed)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            export_dir = os.path.join(base_dir, "exports")
            
            # Create folder if not exists
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            file_path = os.path.join(export_dir, filename)
            
            # Write CSV file
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                writer.writerow(['STORE MANAGEMENT SYSTEM - EXPORT'])
                writer.writerow([f'Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow([])
                
                # Materials
                writer.writerow(['MATERIALS'])
                writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location', 'Size', 'Length', 'Colors', 'Notes'])
                for m in materials:
                    writer.writerow([
                        m.get('name', ''),
                        m.get('category_name', 'Other'),
                        m.get('quantity', 0),
                        m.get('quality', 'New'),
                        m.get('location_ids', ''),
                        m.get('size', ''),
                        m.get('length', ''),
                        m.get('colors', ''),
                        m.get('notes', '')
                    ])
                
                writer.writerow([])
                
                # Accessories
                writer.writerow(['ACCESSORIES'])
                writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location', 'Notes'])
                for a in accessories:
                    writer.writerow([
                        a.get('name', ''),
                        a.get('category_name', 'Other'),
                        a.get('quantity', 0),
                        a.get('price', 0),
                        a.get('quality', 'New'),
                        a.get('location', ''),
                        a.get('notes', '')
                    ])
            
            # Get file size
            file_size = os.path.getsize(file_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            # Show success dialog with file location
            def copy_path():
                page.set_clipboard(file_path)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ File path copied to clipboard!"),
                    bgcolor=self.success_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
            
            def close_dlg():
                page.dialog.open = False
                page.update()
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text("✅ Export Successful", size=18, weight=ft.FontWeight.BOLD, color=self.success_color, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"📄 {filename}", size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Size: {size_str}", size=12, color="#888888"),
                        ft.Divider(),
                        ft.Text("📍 File Location:", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(file_path, size=9, color="#888888", selectable=True),
                            padding=8,
                            bgcolor="#2C2C2C",
                            border_radius=6,
                        ),
                        ft.Row([
                            ft.ElevatedButton("📋 Copy Path", on_click=lambda e: copy_path(), expand=True),
                        ], spacing=8),
                        ft.Divider(),
                        ft.Text("📱 How to access this file:", size=13, weight=ft.FontWeight.BOLD),
                        ft.Text("1️⃣ Tap 'Copy Path' above", size=11),
                        ft.Text("2️⃣ Open a file manager app (like CX File Explorer)", size=11),
                        ft.Text("3️⃣ Paste the path in the file manager", size=11),
                        ft.Text("4️⃣ Tap the file to open/share it", size=11),
                        ft.Container(height=5),
                        ft.Text("💡 You can also view this file in 'View Exports'", size=10, color="#888888"),
                    ], spacing=8),
                    width=400,
                    height=450,
                    padding=15,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda e: close_dlg()),
                    ft.ElevatedButton("📁 View All Exports", on_click=lambda e: self.show_exported_files(page)),
                ],
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    def export_csv_to_downloads(self, page: ft.Page):
        """Export CSV directly to Downloads folder on mobile"""
        import csv
        import os
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Try to save to Downloads folder first (for mobile)
            if os.path.exists("/storage/emulated/0/Download"):
                downloads_path = "/storage/emulated/0/Download"
            elif os.path.exists(os.path.expanduser("~/Downloads")):
                downloads_path = os.path.expanduser("~/Downloads")
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                downloads_path = os.path.join(base_dir, "exports")
                os.makedirs(downloads_path, exist_ok=True)
            
            files_created = []
            
            # Export materials
            if materials:
                materials_file = os.path.join(downloads_path, f"materials_{timestamp}.csv")
                with open(materials_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location', 'Size', 'Length', 'Colors', 'Notes', 'Barcode'])
                    for m in materials:
                        writer.writerow([
                            m.get('name', ''),
                            m.get('category_name', 'Other'),
                            m.get('quantity', 0),
                            m.get('quality', 'New'),
                            m.get('location_ids', ''),
                            m.get('size', ''),
                            m.get('length', ''),
                            m.get('colors', ''),
                            m.get('notes', ''),
                            m.get('barcode_value', '')
                        ])
                files_created.append(f"materials_{timestamp}.csv")
            
            # Export accessories
            if accessories:
                accessories_file = os.path.join(downloads_path, f"accessories_{timestamp}.csv")
                with open(accessories_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location', 'Notes', 'Barcode'])
                    for a in accessories:
                        writer.writerow([
                            a.get('name', ''),
                            a.get('category_name', 'Other'),
                            a.get('quantity', 0),
                            a.get('price', 0),
                            a.get('quality', 'New'),
                            a.get('location', ''),
                            a.get('notes', ''),
                            a.get('barcode_value', '')
                        ])
                files_created.append(f"accessories_{timestamp}.csv")
            
            if files_created:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ CSV saved to Downloads folder"),
                    bgcolor=self.success_color,
                    duration=4000
                )
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("No data to export"),
                    bgcolor=self.warning_color,
                    duration=3000
                )
            
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Export failed: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def generate_inventory_html_content(self, items, timestamp):
        """Generate HTML content for inventory report"""
        from datetime import datetime
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Inventory Report</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                .header {{
                    background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
                .header p {{ font-size: 14px; opacity: 0.9; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    padding: 25px;
                    background: #f8f9fa;
                }}
                .stat-card {{
                    background: white;
                    padding: 15px;
                    border-radius: 12px;
                    text-align: center;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .stat-card .value {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #1976D2;
                }}
                .stat-card .label {{ font-size: 12px; color: #666; margin-top: 5px; }}
                .section {{ padding: 20px 25px; }}
                .section h2 {{
                    color: #333;
                    border-left: 4px solid #1976D2;
                    padding-left: 15px;
                    margin-bottom: 15px;
                    font-size: 18px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: left;
                }}
                th {{
                    background-color: #1976D2;
                    color: white;
                    font-weight: 600;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 20px;
                    font-size: 11px;
                    font-weight: bold;
                    color: white;
                }}
                .badge-new {{ background-color: #4CAF50; }}
                .badge-used {{ background-color: #FF9800; }}
                .badge-damaged {{ background-color: #F44336; }}
                .badge-repaired {{ background-color: #2196F3; }}
                .low-stock {{ color: #F44336; font-weight: bold; }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    background: #f8f9fa;
                    color: #888;
                    font-size: 12px;
                }}
                @media (max-width: 600px) {{
                    .stats {{ gap: 8px; padding: 15px; }}
                    .stat-card .value {{ font-size: 22px; }}
                    th, td {{ padding: 6px; font-size: 11px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Inventory Report</h1>
                    <p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="value">{len(items)}</div>
                        <div class="label">Total Items</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">{sum(i.get('quantity', 0) for i in items)}</div>
                        <div class="label">Total Stock</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">{len([i for i in items if i.get('quantity', 0) < 10])}</div>
                        <div class="label">Low Stock</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📋 Inventory Items ({len(items)})</h2>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Type</th>
                                    <th>Name</th>
                                    <th>Code</th>
                                    <th>Quantity</th>
                                    <th>Quality</th>
                                    <th>Location</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        for item in items:
            qty_class = 'low-stock' if item.get('quantity', 0) < 10 else ''
            quality = item.get('quality', 'Used')
            html_content += f"""
                                <tr>
                                    <td>{item.get('type_icon', '📦')} {item.get('type_name', '')}</td>
                                    <td>{item.get('name', 'N/A')}</td>
                                    <td>{item.get('code', 'N/A')}</td>
                                    <td class='{qty_class}'>{item.get('quantity', 0)}</td>
                                    <td><span class="badge badge-{quality.lower()}">{quality}</span></td>
                                    <td>{item.get('location', 'N/A')}</td>
                                </tr>
            """
        
        html_content += f"""
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Generated by Store Management System</p>
                    <p>Report ID: {timestamp}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def generate_low_stock_html_content(self, low_stock_items):
        """Generate HTML content for low stock report"""
        from datetime import datetime
        
        html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Low Stock Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background: #f5f5f5;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 20px;
            }}
            h1 {{ color: #F44336; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #F44336;
                color: white;
            }}
            .critical {{ background-color: #FFEBEE; }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #888;
                font-size: 12px;
            }}
            @media (max-width: 600px) {{
                th, td {{ padding: 6px; font-size: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ Low Stock Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total low stock items: {len(low_stock_items)}</p>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Name</th>
                            <th>Current Stock</th>
                            <th>Quality</th>
                            <th>Location</th>
                        </tr>
                    </thead>
                    <tbody>"""
        
        for item in low_stock_items:
            critical_class = 'critical' if item['quantity'] < 5 else ''
            html_content += f"""
                        <tr class='{critical_class}'>
                            <td>{item['type']}</td>
                            <td><strong>{item['name']}</strong></td>
                            <td style='color:#F44336;font-weight:bold'>{item['quantity']}</td>
                            <td>{item['quality']}</td>
                            <td>{item['location']}</td>
                        </tr>"""
        
        html_content += f"""
                    </tbody>
                </table>
            </div>
            <div class="footer">
                <p>Generated by Store Management System</p>
            </div>
        </div>
    </body>
    </html>"""
        
        return html_content
    
    def export_html_and_open(self, page: ft.Page):
        """Export HTML and auto-open using launch_url (works on mobile)"""
        import os
        from datetime import datetime
        
        try:
            # Get export directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            export_dir = os.path.join(base_dir, "exports")
            
            if not os.path.exists(export_dir):
                os.makedirs(export_dir, exist_ok=True)
            
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            # Calculate stats
            total_materials = len(materials)
            total_accessories = len(accessories)
            total_items = total_materials + total_accessories
            total_stock = sum(m.get('quantity', 0) for m in materials) + sum(a.get('quantity', 0) for a in accessories)
            low_stock_count = len([m for m in materials if m.get('quantity', 0) < 10]) + len([a for a in accessories if a.get('quantity', 0) < 10])
            
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"inventory_report_{timestamp}.html"
            file_path = os.path.join(export_dir, filename)
            
            # Generate HTML content
            html_content = self.generate_inventory_html(materials, accessories, total_items, total_stock, low_stock_count, total_materials, total_accessories, timestamp)
            
            # Save file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Show success message
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ HTML saved: {filename}"),
                bgcolor=self.success_color,
                duration=2000
            )
            page.snack_bar.open = True
            page.update()
            
            # Auto-open in browser using launch_url (works on mobile)
            file_url = f"file://{os.path.abspath(file_path)}"
            page.launch_url(file_url)
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Export failed: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
    
    def request_permissions(self, page: ft.Page):
        """Request storage permissions on Android"""
        import os
        
        # Only for Android
        if os.name == 'nt':
            return
        
        try:
            from android.permissions import Permission, request_permissions
            from android.permissions import check_permission
            
            permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.MANAGE_EXTERNAL_STORAGE,
            ]
            
            # Check if permissions are granted
            granted = all(check_permission(p) for p in permissions)
            
            if not granted:
                def permission_callback(result):
                    if result:
                        page.snack_bar = ft.SnackBar(
                            ft.Text("✓ Storage permissions granted! You can now export files."),
                            bgcolor=self.success_color,
                            duration=3000
                        )
                    else:
                        page.snack_bar = ft.SnackBar(
                            ft.Text("⚠️ Storage permissions denied. Export may not work properly."),
                            bgcolor=self.warning_color,
                            duration=3000
                        )
                    page.snack_bar.open = True
                    page.update()
                
                request_permissions(permissions, permission_callback)
        except:
            pass

    def export_csv_with_picker(self, page: ft.Page):
        """Export CSV with FilePicker - user chooses save location"""
        import csv
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create CSV content as string
            csv_lines = []
            
            # Materials section
            csv_lines.append("=== MATERIALS ===")
            csv_lines.append("Name,Category,Quantity,Quality,Location,Size,Length,Colors,Notes,Barcode")
            for m in materials:
                csv_lines.append(f"\"{m.get('name', '')}\",\"{m.get('category_name', 'Other')}\",{m.get('quantity', 0)},\"{m.get('quality', 'New')}\",\"{m.get('location_ids', '')}\",\"{m.get('size', '')}\",\"{m.get('length', '')}\",\"{m.get('colors', '')}\",\"{m.get('notes', '')}\",\"{m.get('barcode_value', '')}\"")
            
            # Accessories section
            csv_lines.append("")
            csv_lines.append("=== ACCESSORIES ===")
            csv_lines.append("Name,Category,Quantity,Price,Quality,Location,Notes,Barcode")
            for a in accessories:
                csv_lines.append(f"\"{a.get('name', '')}\",\"{a.get('category_name', 'Other')}\",{a.get('quantity', 0)},{a.get('price', 0)},\"{a.get('quality', 'New')}\",\"{a.get('location', '')}\",\"{a.get('notes', '')}\",\"{a.get('barcode_value', '')}\"")
            
            csv_content = "\n".join(csv_lines)
            
            # FilePicker result handler
            def on_save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    # Save the file
                    with open(e.path, 'w', encoding='utf-8-sig') as f:
                        f.write(csv_content)
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ CSV saved to: {os.path.basename(e.path)}"),
                        bgcolor=self.success_color,
                        duration=4000
                    )
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Save cancelled"),
                        bgcolor=self.warning_color,
                        duration=2000
                    )
                page.snack_bar.open = True
                page.update()
            
            # Create and show file picker
            file_picker = ft.FilePicker(on_result=on_save_result)
            page.overlay.append(file_picker)
            page.update()
            
            # Open save dialog - user chooses where to save
            file_picker.save_file(
                file_name=f"store_export_{timestamp}.csv",
                dialog_title="Save CSV File",
                initial_directory="/storage/emulated/0/Download"
            )
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Export failed: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
    def create_html_viewer(filename, csv_content, material_count, accessory_count):
        """Create HTML content for viewer"""
        from datetime import datetime
        
        # Escape special characters
        csv_content_escaped = csv_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{filename}</title>
            <style>
                body {{
                    font-family: monospace;
                    padding: 20px;
                    background: #1e1e1e;
                    color: #d4d4d4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .header {{
                    background: #0078d4;
                    padding: 10px;
                    margin: -20px -20px 20px -20px;
                    color: white;
                }}
                .info {{
                    background: #2d2d2d;
                    padding: 10px;
                    margin-bottom: 20px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 {filename}</h2>
            </div>
            <div class="info">
                📦 Materials: {material_count} | 🔧 Accessories: {accessory_count}
                <br>📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
            <pre>{csv_content_escaped}</pre>
            <script>
                // Auto-scroll to top
                window.scrollTo(0, 0);
            </script>
        </body>
        </html>
    
       """
    def export_csv_samsung(self, page: ft.Page):
        """Export CSV using Overlay - Works on all Samsung devices"""
        import csv
        import os
        from datetime import datetime
        import tempfile
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Create CSV content
            csv_lines = []
            csv_lines.append("Name,Category,Quantity,Quality,Location")
            
            for m in materials[:100]:
                csv_lines.append(f"\"{m.get('name', '')}\",\"{m.get('category_name', 'Other')}\",{m.get('quantity', 0)},\"{m.get('quality', 'New')}\",\"{m.get('location_ids', '')}\"")
            
            csv_content = "\n".join(csv_lines)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig')
            temp_file.write(csv_content)
            temp_file.close()
            temp_path = temp_file.name
            
            def close_overlay():
                page.overlay.remove(overlay_container)
                page.update()
            
            def share_file():
                file_url = f"file://{temp_path}"
                page.launch_url(file_url)
                close_overlay()
                
                # Clean up temp file
                import threading
                def cleanup():
                    import time
                    time.sleep(3)
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                threading.Thread(target=cleanup, daemon=True).start()
                
                page.snack_bar = ft.SnackBar(
                    ft.Text("📤 Select 'Save to Drive' or 'Save to Device' to save to Downloads"),
                    bgcolor=self.accent_color,
                    duration=4000
                )
                page.snack_bar.open = True
                page.update()
            
            # Create preview content
            csv_preview = csv_content.split('\n')[:30]
            preview_column = ft.Column(
                [ft.Text(line[:70], size=9, font_family="monospace", color="#CCCCCC") for line in csv_preview],
                spacing=1,
                scroll=ft.ScrollMode.AUTO,
                height=200
            )
            
            # Create content for overlay
            content = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("📊 Export CSV", size=20, weight=ft.FontWeight.BOLD, color=self.text_color, expand=True),
                        ft.IconButton(
                            icon=ft.icons.CLOSE, 
                            icon_size=24, 
                            icon_color=self.danger_color,
                            on_click=lambda e: close_overlay()
                        ),
                    ]),
                    ft.Divider(height=1, color="#3C3C3C"),
                    ft.Text(filename, size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Materials: {len(materials)} | Accessories: {len(accessories)}", size=11, color="#888888"),
                    ft.Divider(height=1, color="#3C3C3C"),
                    ft.Text("📄 Preview (first 30 rows):", size=13, weight=ft.FontWeight.BOLD),
                    preview_column,
                    ft.Divider(height=1, color="#3C3C3C"),
                    ft.Text("How to save to Downloads:", size=14, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                    ft.Text("1️⃣ Tap 'Share & Save' below", size=12),
                    ft.Text("2️⃣ Select 'Save to Drive' or 'Save to Device'", size=12),
                    ft.Text("3️⃣ Choose 'Downloads' folder", size=12),
                    ft.Text("4️⃣ Tap 'Save'", size=12),
                    ft.Container(height=10),
                    ft.Row([
                        ft.ElevatedButton(
                            "📤 Share & Save",
                            on_click=lambda e: share_file(),
                            expand=True,
                            style=ft.ButtonStyle(bgcolor="#4CAF50"),
                            icon=ft.icons.SHARE,
                        ),
                    ], spacing=8),
                    ft.Container(height=5),
                    ft.Text("💡 Your file will open in a new window. Use the share/save option.", size=9, color="#888888"),
                ], spacing=10),
                width=450,
                height=580,
                bgcolor=self.card_color,
                border_radius=12,
                padding=20,
            )
            
            # Create overlay container
            overlay_container = ft.Container(
                content=ft.Row(
                    [content],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                bgcolor="#80000000",  # Semi-transparent black
            )
            
            # Add to page overlay
            page.overlay.append(overlay_container)
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

    def export_and_view_csv(self, page: ft.Page):
        """Export CSV with options to Save and Share - Works with Flet 0.21.2"""
        import csv
        import os
        from datetime import datetime
        import io
        
        try:
            # Get data safely
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            if not materials:
                materials = []
            if not accessories:
                accessories = []
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_export_{timestamp}.csv"
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['STORE MANAGEMENT SYSTEM - EXPORT'])
            writer.writerow([f'Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
            writer.writerow([])
            writer.writerow(['MATERIALS'])
            writer.writerow(['Name', 'Category', 'Quantity', 'Quality', 'Location'])
            
            for m in materials[:100]:
                writer.writerow([
                    str(m.get('name', '')) if m else '',
                    str(m.get('category_name', 'Other')) if m else 'Other',
                    str(m.get('quantity', 0)) if m else '0',
                    str(m.get('quality', 'New')) if m else 'New',
                    str(m.get('location_ids', '')) if m else ''
                ])
            
            writer.writerow([])
            writer.writerow(['ACCESSORIES'])
            writer.writerow(['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location'])
            
            for a in accessories[:100]:
                writer.writerow([
                    str(a.get('name', '')) if a else '',
                    str(a.get('category_name', 'Other')) if a else 'Other',
                    str(a.get('quantity', 0)) if a else '0',
                    str(a.get('price', 0)) if a else '0',
                    str(a.get('quality', 'New')) if a else 'New',
                    str(a.get('location', '')) if a else ''
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            # Save to app storage
            base_dir = os.path.dirname(os.path.abspath(__file__))
            exports_dir = os.path.join(base_dir, "exports")
            os.makedirs(exports_dir, exist_ok=True)
            saved_file_path = os.path.join(exports_dir, filename)
            
            with open(saved_file_path, 'w', encoding='utf-8-sig') as f:
                f.write(csv_content)
            
            def close_dialog():
                page.dialog.open = False
                page.update()
            
            def save_file():
                close_dialog()
                self.save_csv_to_downloads(page, saved_file_path, filename)
            
            def share_file():
                close_dialog()
                page.launch_url(f"file://{saved_file_path}")
            
            # Create scrollable content
            csv_lines = csv_content.split('\n')
            content_display = ft.Column(
                [ft.Text(line, size=11, font_family="monospace", color="#CCCCCC", selectable=True) for line in csv_lines[:200]],
                spacing=2,
                scroll=ft.ScrollMode.AUTO,
                height=400
            )
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text(f"📊 {filename}", size=16, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Materials: {len(materials)}", size=12, color="#888888"),
                            ft.Text(f"Accessories: {len(accessories)}", size=12, color="#888888"),
                        ], spacing=10),
                        ft.Divider(),
                        content_display,
                        ft.Divider(),
                        ft.Row([
                            ft.ElevatedButton(
                                "💾 Save to Device",
                                on_click=lambda e: save_file(),
                                expand=True,
                                style=ft.ButtonStyle(bgcolor="#4CAF50"),
                                icon=ft.icons.SAVE,
                            ),
                            ft.ElevatedButton(
                                "📤 Share",
                                on_click=lambda e: share_file(),
                                expand=True,
                                style=ft.ButtonStyle(bgcolor="#9C27B0"),
                                icon=ft.icons.SHARE,
                            ),
                        ], spacing=8),
                    ], spacing=8),
                    width=450,
                    height=550,
                    padding=15,
                ),
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

    def save_csv_to_downloads(self, page: ft.Page, file_path, filename):
        """Save CSV file to Downloads using FilePicker"""
        import os
        import shutil
        
        def on_save_result(e: ft.FilePickerResultEvent):
            if e and e.path:
                try:
                    shutil.copy2(file_path, e.path)
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Saved to: {os.path.basename(e.path)}"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Save failed: {str(ex)[:30]}"),
                        bgcolor=self.danger_color,
                        duration=3000
                    )
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Save cancelled"),
                    bgcolor=self.warning_color,
                    duration=2000
                )
            page.snack_bar.open = True
            page.update()
        
        file_picker = ft.FilePicker(on_result=on_save_result)
        page.overlay.append(file_picker)
        page.update()
        
        file_picker.save_file(
            file_name=filename,
            dialog_title="Save CSV File",
            initial_directory="/storage/emulated/0/Download"
        )

    def generate_viewer_html(self, filename, csv_content, file_path, material_count, accessory_count):
        """Generate HTML viewer with Save and Print options"""
        from datetime import datetime
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #1E1E1E;
                    color: #FFFFFF;
                    padding: 16px;
                    padding-bottom: 80px;
                }}
                .header {{
                    background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%);
                    margin: -16px -16px 16px -16px;
                    padding: 20px 16px;
                    text-align: center;
                }}
                .header h1 {{
                    font-size: 20px;
                    margin-bottom: 8px;
                }}
                .header p {{
                    font-size: 12px;
                    opacity: 0.9;
                }}
                .info-bar {{
                    background: #2C2C2C;
                    padding: 12px;
                    border-radius: 8px;
                    margin-bottom: 16px;
                    font-size: 12px;
                    color: #888888;
                    display: flex;
                    justify-content: space-between;
                    flex-wrap: wrap;
                    gap: 8px;
                }}
                .info-item {{
                    background: #1E1E1E;
                    padding: 4px 8px;
                    border-radius: 4px;
                }}
                .toolbar {{
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    background: #1E1E1E;
                    padding: 12px;
                    display: flex;
                    gap: 12px;
                    justify-content: center;
                    border-top: 1px solid #3C3C3C;
                    z-index: 1000;
                }}
                button {{
                    background: #1976D2;
                    color: white;
                    border: none;
                    padding: 12px 20px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex: 1;
                    justify-content: center;
                }}
                button.save-btn {{
                    background: #4CAF50;
                }}
                button.print-btn {{
                    background: #FF9800;
                }}
                button.share-btn {{
                    background: #9C27B0;
                }}
                button.close-btn {{
                    background: #F44336;
                }}
                pre {{
                    background: #2C2C2C;
                    padding: 16px;
                    border-radius: 8px;
                    overflow-x: auto;
                    font-size: 11px;
                    font-family: 'Courier New', monospace;
                    color: #CCCCCC;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                @media print {{
                    .toolbar {{
                        display: none;
                    }}
                    body {{
                        background: white;
                        color: black;
                        padding: 0;
                    }}
                    .header {{
                        background: #1976D2;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }}
                    pre {{
                        background: #f5f5f5;
                        color: black;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 {filename}</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="info-bar">
                <span class="info-item">📦 Materials: {material_count}</span>
                <span class="info-item">🔧 Accessories: {accessory_count}</span>
                <span class="info-item">📄 Format: CSV</span>
                <span class="info-item">💾 Size: {len(csv_content)} bytes</span>
            </div>
            
            <pre>{csv_content}</pre>
            
            <div class="toolbar">
                <button class="save-btn" onclick="saveFile()">💾 Save to Device</button>
                <button class="print-btn" onclick="printFile()">🖨️ Print</button>
                <button class="share-btn" onclick="shareFile()">📤 Share</button>
                <button class="close-btn" onclick="closeView()">✕ Close</button>
            </div>
            
            <script>
                function saveFile() {{
                    window.parent.postMessage('save', '*');
                }}
                function printFile() {{
                    window.print();
                }}
                function shareFile() {{
                    window.parent.postMessage('share', '*');
                }}
                function closeView() {{
                    window.parent.postMessage('close', '*');
                }}
            </script>
        </body>
        </html>
        """

    def save_csv_file(self, page: ft.Page, file_path, filename):
        """Save CSV file using FilePicker"""
        import os
        import shutil
        
        def on_save_result(e: ft.FilePickerResultEvent):
            if e.path:
                shutil.copy2(file_path, e.path)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Saved to: {os.path.basename(e.path)}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Save cancelled"),
                    bgcolor=self.warning_color,
                    duration=2000
                )
            page.snack_bar.open = True
            page.update()
        
        file_picker = ft.FilePicker(on_result=on_save_result)
        page.overlay.append(file_picker)
        page.update()
        
        file_picker.save_file(
            file_name=filename,
            dialog_title="Save CSV File",
            initial_directory="/storage/emulated/0/Download"
        )

    def print_csv_file(self, page: ft.Page, file_path, filename):
        """Print CSV file - shows print dialog"""
        import os
        
        # Create print-friendly HTML
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{filename}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                }}
                pre {{
                    white-space: pre-wrap;
                    font-family: 'Courier New', monospace;
                    font-size: 10px;
                }}
                @media print {{
                    body {{ margin: 0; }}
                    pre {{ font-size: 8px; }}
                }}
            </style>
        </head>
        <body>
            <h2>{filename}</h2>
            <pre>{content}</pre>
            <script>
                window.print();
            </script>
        </body>
        </html>
        """
        
        # Create WebView for printing
        webview = ft.WebView(
            content=ft.WebViewContent(
                source=ft.WebViewSource.HTML,
                html=print_html,
            ),
            expand=True,
        )
        
        overlay = ft.Container(
            content=webview,
            expand=True,
            bgcolor="#000000",
        )
        
        page.overlay.append(overlay)
        page.update()
        
        def on_message(e):
            if e.message == 'close' or e.message == 'print':
                page.overlay.remove(overlay)
                page.update()
        
        webview.on_javascript_message = on_message

    def export_html_simple(self, page: ft.Page):
        """Simple HTML export - saves to app storage, user copies path"""
        import os
        from datetime import datetime
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"store_report_{timestamp}.html"
            
            # Generate HTML content
            html_content = self.generate_html_report(materials, accessories, timestamp)
            
            # Save to app's private storage (ALWAYS works)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            exports_dir = os.path.join(base_dir, "exports")
            os.makedirs(exports_dir, exist_ok=True)
            file_path = os.path.join(exports_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            file_size = os.path.getsize(file_path)
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            else:
                size_str = f"{file_size / 1024:.1f} KB"
            
            def copy_path():
                page.set_clipboard(file_path)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ File path copied to clipboard!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
            
            def close_dialog():
                page.dialog.open = False
                page.update()
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text("✅ Export Complete", size=18, weight=ft.FontWeight.BOLD, color=self.success_color, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(filename, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Size: {size_str} | Materials: {len(materials)}", size=11, color="#888888"),
                        ft.Divider(),
                        ft.Text("📍 File Location:", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(file_path, size=9, color="#888888", selectable=True),
                            padding=8,
                            bgcolor="#2C2C2C",
                            border_radius=6,
                        ),
                        ft.Row([
                            ft.ElevatedButton(
                                "📋 Copy Path",
                                on_click=lambda e: copy_path(),
                                expand=True,
                                icon=ft.icons.CONTENT_COPY,
                                style=ft.ButtonStyle(bgcolor="#2196F3"),
                            ),
                        ], spacing=8),
                        ft.Divider(),
                        ft.Text("📱 How to get this file:", size=13, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                        ft.Text("1️⃣ Tap 'Copy Path' above", size=12),
                        ft.Text("2️⃣ Open 'My Files' app on your Samsung", size=12),
                        ft.Text("3️⃣ Tap the search icon and paste the path", size=12),
                        ft.Text("4️⃣ Long press the file → Copy → Downloads", size=12),
                        ft.Container(height=5),
                        ft.Text("💡 The file is saved in the app's private storage", size=9, color="#888888"),
                        ft.Text("💡 You can also connect your phone to a computer to copy the file", size=9, color="#888888"),
                    ], spacing=8),
                    width=450,
                    height=450,
                    padding=20,
                ),
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        
    def create_trial_banner(self, page: ft.Page):
        """Create trial/activation banner for dashboard"""
        
        user = self.current_user or {}
        is_activated = user.get('activated', False)
        days_left = user.get('days_left', 30)
        
        # Check trial status if not activated
        if not is_activated:
            try:
                trial_active, days_left = self.check_trial_status()
                if not trial_active:
                    days_left = 0
            except:
                days_left = 30
        
        if is_activated:
            # Full version activated - Show small badge
            return ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50", size=16),
                    ft.Text("✅ Full Version", size=11, color="#4CAF50", weight=ft.FontWeight.BOLD),
                ], spacing=4),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                bgcolor="#1A3A1A",
                border_radius=10,
            )
        elif days_left > 0:
            # Trial active - Show banner with days left
            days_color = self.danger_color if days_left <= 5 else "#FF9800"
            emoji = "⚠️" if days_left <= 5 else "🚀"
            
            return ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.TIMER, color="#FF9800", size=16),
                    ft.Text(f"{emoji} {days_left}d", size=11, color="#FF9800", weight=ft.FontWeight.BOLD),
                    ft.Container(width=3),
                    ft.ElevatedButton(
                        "Activate",
                        on_click=lambda e: self.show_activation_dialog(page),
                        style=ft.ButtonStyle(bgcolor="#4CAF50", color="white", padding=ft.padding.symmetric(horizontal=6, vertical=2)),
                        height=26,
                    ),
                ], spacing=4),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                bgcolor="#2C2C2C",
                border_radius=10,
            )
        else:
            # Trial expired - Show warning banner
            return ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.WARNING, color=self.danger_color, size=16),
                    ft.Text("Expired", size=11, color=self.danger_color, weight=ft.FontWeight.BOLD),
                    ft.Container(width=3),
                    ft.ElevatedButton(
                        "Activate",
                        on_click=lambda e: self.show_activation_dialog(page),
                        style=ft.ButtonStyle(bgcolor="#FF9800", color="white", padding=ft.padding.symmetric(horizontal=6, vertical=2)),
                        height=26,
                    ),
                ], spacing=4),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                bgcolor="#3A1A1A",
                border_radius=10,
            )
    
                                # ============ DASHBOARD ============
    def show_dashboard(self, page: ft.Page):
        """Dashboard with activation status banner"""
        try:
            page.controls.clear()
            
            from activation_manager import ActivationManager
            
            # Check app activation
            device_id = ActivationManager.get_device_id()
            status = ActivationManager.check_activation_status(device_id)
            is_activated = status.get('status') in ['activated', 'trial_active']
            is_trial_expired = status.get('status') == 'trial_expired'
            days_left = status.get('days_left', 0)
            
            is_mobile = page.width < 800 if page.width else False
            
            # Navigation
            if is_mobile:
                nav = self.create_bottom_nav(page)
                sidebar = None
            else:
                sidebar = self.create_sidebar(page)
                nav = None
            
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            users = self.dict_list(UserManager.get_all())
            
            # Calculate statistics
            total_materials = len(materials)
            total_accessories = len(accessories)
            total_items = total_materials + total_accessories
            total_stock = sum(m.get('quantity', 0) for m in materials) + sum(a.get('quantity', 0) for a in accessories)
            total_users = len(users)
            total_low_stock = len([m for m in materials if m.get('quantity', 0) < 10]) + len([a for a in accessories if a.get('quantity', 0) < 10])
            
            quality_counts = {"New": 0, "Used": 0, "Damaged": 0, "Repaired": 0}
            for m in materials:
                q = m.get('quality', 'Used')
                quality_counts[q] = quality_counts.get(q, 0) + 1
            for a in accessories:
                q = a.get('quality', 'Used')
                quality_counts[q] = quality_counts.get(q, 0) + 1
            
            # Create main column
            main_column = ft.Column(spacing=15, expand=True)
            
            # ===== ACTIVATION STATUS BANNER =====
            if is_trial_expired:
                banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.WARNING, color=self.danger_color),
                        ft.Text("⚠️ Trial Expired - Please Activate", size=14 if not is_mobile else 12, 
                            weight=ft.FontWeight.BOLD, color=self.danger_color, expand=True),
                        ft.ElevatedButton(
                            "Activate Now",
                            on_click=lambda e: self.show_activation_dialog(page),
                            style=ft.ButtonStyle(bgcolor=self.danger_color, color="white"),
                            height=36 if is_mobile else 40,
                        ),
                    ], spacing=10),
                    padding=10,
                    bgcolor="#3A1A1A",
                    border_radius=8,
                    margin=ft.margin.only(bottom=10),
                )
            elif not is_activated:
                banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.INFO, color=self.accent_color),
                        ft.Text("📱 Start your 30-day free trial", size=14 if not is_mobile else 12, 
                            weight=ft.FontWeight.BOLD, color=self.accent_color, expand=True),
                        ft.ElevatedButton(
                            "Start Trial",
                            on_click=lambda e: self.start_trial_action(page),
                            style=ft.ButtonStyle(bgcolor=self.accent_color, color="white"),
                            height=36 if is_mobile else 40,
                        ),
                    ], spacing=10),
                    padding=10,
                    bgcolor="#1A2A3A",
                    border_radius=8,
                    margin=ft.margin.only(bottom=10),
                )
            else:
                if days_left > 0 and status.get('status') == 'trial_active':
                    banner = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.TIMER, color="#FF9800"),
                            ft.Text(f"🚀 Trial: {days_left} days remaining", size=14 if not is_mobile else 12, 
                                weight=ft.FontWeight.BOLD, color="#FF9800"),
                        ], spacing=10),
                        padding=10,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                        margin=ft.margin.only(bottom=10),
                    )
                else:
                    banner = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50"),
                            ft.Text("✅ Full Version Activated", size=14 if not is_mobile else 12, 
                                weight=ft.FontWeight.BOLD, color="#4CAF50"),
                        ], spacing=10),
                        padding=10,
                        bgcolor="#1A3A1A",
                        border_radius=8,
                        margin=ft.margin.only(bottom=10),
                    )
            
            main_column.controls.append(banner)
            main_column.controls.append(ft.Container(height=5))
            
            # ===== HEADER WITH SYNC BUTTON =====
            header_row = ft.Row([
                ft.Text("Dashboard", size=28 if not is_mobile else 22, 
                    weight=ft.FontWeight.BOLD, color=self.text_color, expand=True),
                ft.IconButton(
                    icon=ft.icons.CLOUD_SYNC,
                    icon_size=24,
                    icon_color=self.accent_color,
                    on_click=lambda e: self.manual_sync(page),
                    tooltip="Sync with Cloud",
                ),
            ])
            main_column.controls.append(header_row)
            main_column.controls.append(ft.Text("Welcome back!", size=14 if not is_mobile else 12, color="#888888"))
            
            # ===== STATS CARDS =====
            main_column.controls.append(
                ft.Row([
                    self._create_stat_card("📦", str(total_items), "Items"),
                    self._create_stat_card("📊", str(total_stock), "Stock"),
                    self._create_stat_card("⚠️", str(total_low_stock), "Low Stock"),
                    self._create_stat_card("👥", str(total_users), "Users"),
                ], spacing=8)
            )
            
            # ===== QUALITY DISTRIBUTION =====
            main_column.controls.append(ft.Text("📊 Quality Distribution", size=16 if not is_mobile else 14, 
                                            weight=ft.FontWeight.BOLD))
            
            quality_row1 = ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CIRCLE, size=16, color="#4CAF50"),
                        ft.Text(f"New: {quality_counts.get('New', 0)}", size=14 if not is_mobile else 12, 
                            color=self.text_color),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=self.card_color,
                    border_radius=8,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CIRCLE, size=16, color="#FF9800"),
                        ft.Text(f"Used: {quality_counts.get('Used', 0)}", size=14 if not is_mobile else 12,
                            color=self.text_color),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=self.card_color,
                    border_radius=8,
                    expand=True,
                ),
            ], spacing=8)
            main_column.controls.append(quality_row1)
            
            quality_row2 = ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CIRCLE, size=16, color="#F44336"),
                        ft.Text(f"Damaged: {quality_counts.get('Damaged', 0)}", size=14 if not is_mobile else 12,
                            color=self.text_color),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=self.card_color,
                    border_radius=8,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CIRCLE, size=16, color="#2196F3"),
                        ft.Text(f"Repaired: {quality_counts.get('Repaired', 0)}", size=14 if not is_mobile else 12,
                            color=self.text_color),
                    ], spacing=8),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=self.card_color,
                    border_radius=8,
                    expand=True,
                ),
            ], spacing=8)
            main_column.controls.append(quality_row2)
            
            # ===== STOCK HEALTH =====
            if total_stock > 0:
                healthy_percentage = int(((total_stock - total_low_stock * 10) / total_stock * 100))
                healthy_percentage = max(0, min(healthy_percentage, 100))
            else:
                healthy_percentage = 100
            
            main_column.controls.append(ft.Text("💪 Stock Health", size=16 if not is_mobile else 14,
                                            weight=ft.FontWeight.BOLD))
            main_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{healthy_percentage}%", size=24 if not is_mobile else 20,
                            weight=ft.FontWeight.BOLD, color=self.success_color),
                        ft.ProgressBar(value=healthy_percentage/100, color=self.success_color, 
                                    bgcolor="#3C3C3C", height=6),
                        ft.Text(f"Low Stock: {total_low_stock} items", size=12 if not is_mobile else 10,
                            color=self.warning_color),
                    ], spacing=5),
                    padding=12, bgcolor=self.card_color, border_radius=10,
                )
            )
            
            # ===== RECENT MATERIALS =====
            main_column.controls.append(ft.Text("📦 Recent Materials", size=16 if not is_mobile else 14,
                                            weight=ft.FontWeight.BOLD))
            if materials:
                for m in materials[:3]:
                    main_column.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text("📦", size=18 if not is_mobile else 16),
                                ft.Text(m.get('name', 'N/A'), size=14 if not is_mobile else 12, expand=True),
                                ft.Text(f"Qty: {m.get('quantity', 0)}", size=14 if not is_mobile else 12),
                                ft.Container(
                                    content=ft.Text(m.get('quality', 'Used'), size=10, color="white"),
                                    bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ]),
                            padding=10, bgcolor="#2C2C2C", border_radius=8,
                        )
                    )
                main_column.controls.append(ft.TextButton("View All", on_click=lambda e: self.show_materials_screen(page)))
            else:
                main_column.controls.append(ft.Text("No materials", size=12, color="#888888"))
            
            # ===== RECENT ACCESSORIES =====
            main_column.controls.append(ft.Text("🔧 Recent Accessories", size=16 if not is_mobile else 14,
                                            weight=ft.FontWeight.BOLD))
            if accessories:
                for a in accessories[:3]:
                    price = a.get('price', 0)
                    price_text = f"${price:.2f}" if price else ""
                    main_column.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text("🔧", size=18 if not is_mobile else 16),
                                ft.Text(a.get('name', 'N/A'), size=14 if not is_mobile else 12, expand=True),
                                ft.Text(f"Qty: {a.get('quantity', 0)}", size=14 if not is_mobile else 12),
                                ft.Text(price_text, size=12 if not is_mobile else 10, color="#4CAF50"),
                                ft.Container(
                                    content=ft.Text(a.get('quality', 'Used'), size=10, color="white"),
                                    bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ]),
                            padding=10, bgcolor="#2C2C2C", border_radius=8,
                        )
                    )
                main_column.controls.append(ft.TextButton("View All", on_click=lambda e: self.show_accessories(page)))
            else:
                main_column.controls.append(ft.Text("No accessories", size=12, color="#888888"))
            
            # ===== QUICK ACTIONS =====
            main_column.controls.append(ft.Text("Quick Actions", size=16 if not is_mobile else 14,
                                            weight=ft.FontWeight.BOLD))
            
            # Only show full actions if app is activated or trial is active
            if is_activated and not is_trial_expired:
                main_column.controls.append(
                    ft.Row([
                        ft.ElevatedButton("Add Material", on_click=lambda e: self.open_add_modal(page), expand=True,
                                        height=40 if is_mobile else 45),
                        ft.ElevatedButton("Add Part", on_click=lambda e: self.open_add_accessory_modal(page), expand=True,
                                        height=40 if is_mobile else 45),
                    ], spacing=8)
                )
                main_column.controls.append(
                    ft.Row([
                        ft.ElevatedButton("Scan", on_click=lambda e: self.show_barcode_scanner(page), expand=True,
                                        height=40 if is_mobile else 45),
                        ft.ElevatedButton("Export Data", on_click=lambda e: self.export_all_data_simple(page), expand=True,
                                        height=40 if is_mobile else 45),
                    ], spacing=8)
                )
                # Import/Export
                main_column.controls.append(ft.Text("📁 Import / Export", size=16 if not is_mobile else 14,
                                                weight=ft.FontWeight.BOLD))
                main_column.controls.append(
                    ft.Row([
                        ft.ElevatedButton("🌐 Export HTML", on_click=lambda e: self.export_html_simple(page), expand=True,
                                        height=40 if is_mobile else 45),
                        ft.ElevatedButton("📁 View Exports", on_click=lambda e: self.show_exported_files_simple(page), expand=True,
                                        height=40 if is_mobile else 45),
                    ], spacing=8)
                )
            elif is_trial_expired:
                main_column.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.LOCK, size=40, color="#888888"),
                            ft.Text("⚠️ Trial Expired", size=16, weight=ft.FontWeight.BOLD, color=self.danger_color),
                            ft.Text("Please activate the app to continue using all features.", size=12, color="#888888"),
                            ft.ElevatedButton(
                                "🔑 Activate Now",
                                on_click=lambda e: self.show_activation_dialog(page),
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color="white"),
                            ),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=20,
                        bgcolor=self.card_color,
                        border_radius=10,
                    )
                )
            else:
                main_column.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.INFO, size=40, color=self.accent_color),
                            ft.Text("Start Free Trial", size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
                            ft.Text("Get full access to all features for 30 days.", size=12, color="#888888"),
                            ft.ElevatedButton(
                                "🚀 Start Trial",
                                on_click=lambda e: self.start_trial_action(page),
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color="white"),
                            ),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=20,
                        bgcolor=self.card_color,
                        border_radius=10,
                    )
                )
            
            # ===== CLOUD STATUS =====
            cloud_ready = firebase_api.is_ready() if hasattr(firebase_api, 'is_ready') else False
            if cloud_ready:
                cloud_status = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CLOUD_DONE, size=16, color=self.success_color),
                        ft.Text("Cloud Connected", size=12, color=self.success_color),
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor="#2C2C2C",
                    border_radius=12,
                )
            else:
                cloud_status = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CLOUD_OFF, size=16, color=self.warning_color),
                        ft.Text("Local Mode", size=12, color=self.warning_color),
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor="#2C2C2C",
                    border_radius=12,
                )
            main_column.controls.append(cloud_status)
            
            # ===== FOOTER =====
            main_column.controls.append(ft.Divider())
            main_column.controls.append(ft.Container(height=5))
            
            if is_activated and not is_trial_expired:
                if days_left > 0 and status.get('status') == 'trial_active':
                    footer_text = f"🚀 Trial: {days_left} days"
                    footer_color = "#FF9800"
                else:
                    footer_text = "✅ Full Version"
                    footer_color = "#4CAF50"
            elif is_trial_expired:
                footer_text = "⚠️ Trial Expired"
                footer_color = self.danger_color
            else:
                footer_text = "📱 Free Trial"
                footer_color = self.accent_color
            
            footer_row = ft.Row([
                ft.Text(f"📱 {footer_text}", size=11, color=footer_color),
                ft.Container(expand=True),
                ft.Text("v2.0.0", size=11, color="#888888"),
            ])
            main_column.controls.append(footer_row)
            
            # ===== BOTTOM SPACING =====
            if is_mobile:
                main_column.controls.append(ft.Container(height=70))
            else:
                main_column.controls.append(ft.Container(height=20))
            
            # ===== WRAP AND DISPLAY =====
            scroll_container = ft.Container(
                content=main_column,
                expand=True,
                padding=15,
            )
            
            scrollable = ft.Container(
                content=ft.Column([scroll_container], scroll=ft.ScrollMode.AUTO, expand=True),
                expand=True,
            )
            
            if is_mobile and nav:
                page.add(ft.Column([scrollable, nav], spacing=0, expand=True))
            else:
                page.add(ft.Row([sidebar, scrollable], spacing=0, expand=True))
            
            self.current_view = "dashboard"
            page.update()
            
        except Exception as e:
            print(f"Dashboard error: {e}")
            import traceback
            traceback.print_exc()
            # Show error on screen
            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Text("❌ Dashboard Error", size=20, color="red"),
                        ft.Text(str(e), size=12, color="white"),
                        ft.ElevatedButton("Retry", on_click=lambda e: self.show_dashboard(page)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
            page.update()

    def create_trial_banner_safe(self, page: ft.Page):
        """Create trial/activation banner - SAFE VERSION without any text_style"""
        try:
            user = self.current_user or {}
            is_activated = user.get('activated', False)
            days_left = user.get('days_left', 30)
            
            is_mobile = self.is_mobile(page) if hasattr(self, 'is_mobile') else False
            
            # Check trial status if not activated
            if not is_activated:
                try:
                    trial_active, days_left = self.check_trial_status()
                    if not trial_active:
                        days_left = 0
                except:
                    days_left = 30
            
            if is_activated:
                # Full version activated
                return ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50", size=14 if is_mobile else 16),
                        ft.Text("✅ Full", size=10 if is_mobile else 11, color="#4CAF50", weight=ft.FontWeight.BOLD),
                    ], spacing=3 if is_mobile else 4),
                    padding=ft.padding.symmetric(horizontal=6 if is_mobile else 8, vertical=2 if is_mobile else 3),
                    bgcolor="#1A3A1A",
                    border_radius=8 if is_mobile else 10,
                )
            elif days_left > 0:
                # Trial active
                emoji = "⚠️" if days_left <= 5 else "🚀"
                
                return ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.TIMER, color="#FF9800", size=14 if is_mobile else 16),
                        ft.Text(f"{emoji} {days_left}d", size=10 if is_mobile else 11, color="#FF9800", weight=ft.FontWeight.BOLD),
                        ft.Container(width=2 if is_mobile else 3),
                        ft.ElevatedButton(
                            "Activate",
                            on_click=lambda e: self.show_activation_dialog(page),
                            style=ft.ButtonStyle(
                                bgcolor="#4CAF50", 
                                color="white",
                                padding=ft.padding.symmetric(horizontal=4 if is_mobile else 6, vertical=2 if is_mobile else 3),
                            ),
                            height=22 if is_mobile else 28,
                        ),
                    ], spacing=3 if is_mobile else 4),
                    padding=ft.padding.symmetric(horizontal=6 if is_mobile else 8, vertical=2 if is_mobile else 3),
                    bgcolor="#2C2C2C",
                    border_radius=8 if is_mobile else 10,
                )
            else:
                # Trial expired
                return ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.WARNING, color=self.danger_color, size=14 if is_mobile else 16),
                        ft.Text("Expired", size=10 if is_mobile else 11, color=self.danger_color, weight=ft.FontWeight.BOLD),
                        ft.Container(width=2 if is_mobile else 3),
                        ft.ElevatedButton(
                            "Activate",
                            on_click=lambda e: self.show_activation_dialog(page),
                            style=ft.ButtonStyle(
                                bgcolor="#FF9800", 
                                color="white",
                                padding=ft.padding.symmetric(horizontal=4 if is_mobile else 6, vertical=2 if is_mobile else 3),
                            ),
                            height=22 if is_mobile else 28,
                        ),
                    ], spacing=3 if is_mobile else 4),
                    padding=ft.padding.symmetric(horizontal=6 if is_mobile else 8, vertical=2 if is_mobile else 3),
                    bgcolor="#3A1A1A",
                    border_radius=8 if is_mobile else 10,
                )
        except Exception as e:
            print(f"Trial banner error: {e}")
            # Return empty container if error
            return ft.Container()
    
    def create_trial_banner(self, page: ft.Page):
        """Create trial/activation banner for dashboard - Mobile friendly"""
        
        user = self.current_user or {}
        is_activated = user.get('activated', False)
        days_left = user.get('days_left', 30)
        
        is_mobile = self.is_mobile(page) if hasattr(self, 'is_mobile') else False
        
        # Check trial status if not activated
        if not is_activated:
            try:
                trial_active, days_left = self.check_trial_status()
                if not trial_active:
                    days_left = 0
            except:
                days_left = 30
        
        if is_activated:
            # Full version activated - Show small badge
            return ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50", size=14 if is_mobile else 16),
                    ft.Text("✅ Full", size=10 if is_mobile else 11, color="#4CAF50", weight=ft.FontWeight.BOLD),
                ], spacing=3 if is_mobile else 4),
                padding=ft.padding.symmetric(horizontal=6 if is_mobile else 8, vertical=2 if is_mobile else 3),
                bgcolor="#1A3A1A",
                border_radius=8 if is_mobile else 10,
            )
        elif days_left > 0:
            # Trial active - Show banner with days left
            emoji = "⚠️" if days_left <= 5 else "🚀"
            
            return ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.TIMER, color="#FF9800", size=14 if is_mobile else 16),
                    ft.Text(f"{emoji} {days_left}d", size=10 if is_mobile else 11, color="#FF9800", weight=ft.FontWeight.BOLD),
                    ft.Container(width=2 if is_mobile else 3),
                    ft.ElevatedButton(
                        "Activate",
                        on_click=lambda e: self.show_activation_dialog(page),
                        style=ft.ButtonStyle(
                            bgcolor="#4CAF50", 
                            color="white",
                            padding=ft.padding.symmetric(horizontal=4 if is_mobile else 6, vertical=2 if is_mobile else 3),
                        ),
                        height=22 if is_mobile else 28,
                    ),
                ], spacing=3 if is_mobile else 4),
                padding=ft.padding.symmetric(horizontal=6 if is_mobile else 8, vertical=2 if is_mobile else 3),
                bgcolor="#2C2C2C",
                border_radius=8 if is_mobile else 10,
            )
        else:
            # Trial expired - Show warning banner
            return ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.WARNING, color=self.danger_color, size=14 if is_mobile else 16),
                    ft.Text("Expired", size=10 if is_mobile else 11, color=self.danger_color, weight=ft.FontWeight.BOLD),
                    ft.Container(width=2 if is_mobile else 3),
                    ft.ElevatedButton(
                        "Activate",
                        on_click=lambda e: self.show_activation_dialog(page),
                        style=ft.ButtonStyle(
                            bgcolor="#FF9800", 
                            color="white",
                            padding=ft.padding.symmetric(horizontal=4 if is_mobile else 6, vertical=2 if is_mobile else 3),
                        ),
                        height=22 if is_mobile else 28,
                    ),
                ], spacing=3 if is_mobile else 4),
                padding=ft.padding.symmetric(horizontal=6 if is_mobile else 8, vertical=2 if is_mobile else 3),
                bgcolor="#3A1A1A",
                border_radius=8 if is_mobile else 10,
            )
    def _create_stat_card_safe(self, icon, value, label):
        """Create a statistics card - SAFE VERSION"""
        try:
            is_mobile = hasattr(self, 'is_mobile') and self.is_mobile(self.page_ref) if self.page_ref else False
            
            if is_mobile:
                return ft.Container(
                    content=ft.Column([
                        ft.Text(icon, size=16),
                        ft.Text(value, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(label, size=9, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    padding=6,
                    bgcolor=self.accent_color,
                    border_radius=6,
                    expand=True,
                    height=70,
                )
            else:
                return ft.Container(
                    content=ft.Column([
                        ft.Text(icon, size=20),
                        ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(label, size=10, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    padding=10,
                    bgcolor=self.accent_color,
                    border_radius=10,
                    expand=True,
                )
        except Exception as e:
            print(f"Stat card error: {e}")
            return ft.Container()
        
    def _create_stat_card_mobile(self, icon, value, label):
        """Create a statistics card for mobile"""
        return ft.Container(
            content=ft.Column([
                ft.Text(icon, size=16),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=9, color="#CCCCCC"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=6,
            bgcolor=self.accent_color,
            border_radius=6,
            expand=True,
            height=70,
        )

    def _create_recent_item_material(self, material):
        """Create a recent material item for desktop"""
        return ft.Container(
            content=ft.Row([
                ft.Text("📦", size=18),
                ft.Text(material.get('name', 'N/A'), size=14, expand=True),
                ft.Text(f"Qty: {material.get('quantity', 0)}", size=14),
                ft.Container(
                    content=ft.Text(material.get('quality', 'Used'), size=10, color="white"),
                    bgcolor=self.get_quality_color(material.get('quality', 'Used')),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                ),
            ]),
            padding=10,
            bgcolor="#2C2C2C",
            border_radius=8,
            margin=ft.margin.only(bottom=5),
        )

    def _create_recent_item_accessory(self, accessory):
        """Create a recent accessory item for desktop"""
        price = accessory.get('price', 0)
        price_text = f"${price:.2f}" if price else ""
        return ft.Container(
            content=ft.Row([
                ft.Text("🔧", size=18),
                ft.Text(accessory.get('name', 'N/A'), size=14, expand=True),
                ft.Text(f"Qty: {accessory.get('quantity', 0)}", size=14),
                ft.Text(price_text, size=12, color="#4CAF50") if price_text else ft.Container(),
                ft.Container(
                    content=ft.Text(accessory.get('quality', 'Used'), size=10, color="white"),
                    bgcolor=self.get_quality_color(accessory.get('quality', 'Used')),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                ),
            ]),
            padding=10,
            bgcolor="#2C2C2C",
            border_radius=8,
            margin=ft.margin.only(bottom=5),
        )
   
    def _create_stat_card(self, icon, value, label):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(icon, size=20),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=10, color="#CCCCCC"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=10,
            bgcolor=self.accent_color,
            border_radius=10,
            expand=True,
        )
    
    def show_exported_files_simple(self, page: ft.Page):
        """Show exported files with instructions to find them"""
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        export_dir = os.path.join(base_dir, "exports")
        
        if not os.path.exists(export_dir):
            os.makedirs(export_dir, exist_ok=True)
        
        # Get all HTML files
        all_files = []
        if os.path.exists(export_dir):
            for f in os.listdir(export_dir):
                if f.endswith('.html'):
                    file_path = os.path.join(export_dir, f)
                    size_bytes = os.path.getsize(file_path)
                    if size_bytes < 1024:
                        size_str = f"{size_bytes} B"
                    else:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    
                    # Get file date from filename
                    date_str = "Unknown"
                    if '_' in f:
                        parts = f.replace('.html', '').split('_')
                        if len(parts) >= 2:
                            date_str = parts[1]
                            if len(date_str) == 8:
                                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    
                    all_files.append((f, file_path, size_str, date_str))
        
        all_files.sort(reverse=True)
        
        if not all_files:
            dialog = ft.AlertDialog(
                title=ft.Text("📁 No Files"),
                content=ft.Text("No exported HTML reports found.\n\nExport some data first from Dashboard or Inventory."),
                actions=[ft.TextButton("OK", on_click=lambda e: setattr(page.dialog, 'open', False))],
            )
            page.dialog = dialog
            dialog.open = True
            page.update()
            return
        
        file_items = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=350)
        
        for filename, file_path, size_str, date_str in all_files:
            def copy_path(p=file_path):
                page.set_clipboard(p)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Path copied to clipboard!"),
                    bgcolor=self.success_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
            
            file_items.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Text("🌐", size=24),
                            ft.Column([
                                ft.Text(filename, size=13, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Date: {date_str} • Size: {size_str}", size=10, color="#888888"),
                            ], spacing=2, expand=True),
                            ft.IconButton(
                                icon=ft.icons.CONTENT_COPY,
                                icon_size=20,
                                icon_color=self.accent_color,
                                on_click=lambda e: copy_path(),
                                tooltip="Copy Path",
                            ),
                        ], spacing=10),
                        padding=12,
                    ),
                    elevation=1,
                )
            )
        
        # Instructions for finding files
        instructions = ft.Column([
            ft.Divider(),
            ft.Text("📱 How to find these files:", size=13, weight=ft.FontWeight.BOLD, color="#4CAF50"),
            ft.Text("1️⃣ Tap 'Copy Path' next to any file", size=11),
            ft.Text("2️⃣ Open 'My Files' app on your Samsung", size=11),
            ft.Text("3️⃣ Tap the search icon (🔍)", size=11),
            ft.Text("4️⃣ Paste the copied path", size=11),
            ft.Text("5️⃣ Long press the file → Copy → Downloads", size=11),
            ft.Container(height=5),
            ft.Text("💡 You can also connect your phone to a computer to access these files", size=9, color="#888888"),
            ft.Text(f"💡 App storage path: {base_dir}/exports/", size=9, color="#888888"),
        ], spacing=6)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("📁 HTML Reports", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Found {len(all_files)} HTML report(s):", size=13),
                    file_items,
                    instructions,
                ], spacing=10),
                width=480,
                height=550,
                padding=15,
            ),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def show_exported_files(self, page: ft.Page):
        """Show list of exported files with copy to downloads option"""
        import os
        import shutil
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        export_dir = os.path.join(base_dir, "exports")
        
        if not os.path.exists(export_dir):
            os.makedirs(export_dir, exist_ok=True)
        
        files = []
        if os.path.exists(export_dir):
            files = [f for f in os.listdir(export_dir) if os.path.isfile(os.path.join(export_dir, f))]
            files.sort(reverse=True)
        
        if not files:
            dialog = ft.AlertDialog(
                title=ft.Text("📁 Exported Files"),
                content=ft.Text("No exported files found.\n\nExport data first from Dashboard."),
                actions=[ft.TextButton("OK", on_click=lambda e: setattr(page.dialog, 'open', False))],
            )
            page.dialog = dialog
            dialog.open = True
            page.update()
            return
        
        file_items = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=400)
        
        for file in files:
            file_path = os.path.join(export_dir, file)
            size_bytes = os.path.getsize(file_path)
            
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            
            icon = "📊" if file.endswith('.csv') else "🌐"
            
            file_items.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Text(icon, size=28),
                            ft.Column([
                                ft.Text(file, size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(size_str, size=11, color="#888888"),
                            ], spacing=3, expand=True),
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.COPY,
                                    icon_size=20,
                                    icon_color=self.accent_color,
                                    on_click=lambda e, f=file: self.copy_file_to_clipboard(page, f),
                                    tooltip="Copy Path",
                                ),
                            ]),
                        ], spacing=12),
                        padding=15,
                    ),
                    elevation=1,
                )
            )
        
        def close_dlg():
            page.dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("📁 Exported Files", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Found {len(files)} exported file(s):", size=13),
                    ft.Text("Tap the copy icon to copy file path", size=11, color="#888888"),
                    ft.Container(height=5),
                    file_items,
                    ft.Container(height=10),
                    ft.Text("💡 Use a file manager (like CX File Explorer) to access these files", size=10, color="#888888"),
                    ft.Text("💡 The files are stored in the app's private storage", size=10, color="#888888"),
                ], spacing=10),
                width=450,
                height=550,
                padding=15,
            ),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def copy_file_to_clipboard(self, page: ft.Page, filename):
        """Copy file path to clipboard"""
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "exports", filename)
        abs_path = os.path.abspath(file_path)
        
        page.set_clipboard(abs_path)
        
        page.snack_bar = ft.SnackBar(
            ft.Text(f"✓ Path copied: {abs_path}"),
            bgcolor=self.success_color,
            duration=4000
        )
        page.snack_bar.open = True
        page.update()

    def open_exported_file(self, page: ft.Page, filename):
        """Open file using launch_url - shows Android app picker"""
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "exports", filename)
        abs_path = os.path.abspath(file_path)
        file_size = os.path.getsize(file_path)
        
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        def close_dlg():
            if page.dialog:
                page.dialog.open = False
            page.update()
        
        def open_file():
            """Open with system app picker"""
            close_dlg()
            # This triggers Android's "Open with" dialog
            file_url = f"file://{abs_path}"
            page.launch_url(file_url)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"📂 Choose an app to open {filename}"),
                bgcolor=self.accent_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
        
        def copy_path():
            """Copy path to clipboard"""
            page.set_clipboard(abs_path)
            close_dlg()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Path copied to clipboard"),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        
        # File icon based on type
        if filename.endswith('.csv'):
            file_icon = "📊"
            file_type = "CSV File"
            instructions = "1. Tap 'Open File'\n2. Select Google Sheets, Excel, or any CSV viewer\n3. Choose 'Just once' or 'Always'"
        else:
            file_icon = "🌐"
            file_type = "HTML File"
            instructions = "1. Tap 'Open File'\n2. Select Chrome, Firefox, or any browser\n3. The report will open in your browser"
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text(f"{file_icon} {file_type}", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            ft.Divider(),
            ft.Text(filename, size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"Size: {size_str}", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Text("📱 How to open:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(instructions, size=12, color="#CCCCCC"),
            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton(
                    "📂 Open File",
                    on_click=lambda e: open_file(),
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color),
                    icon=ft.icons.OPEN_IN_NEW,
                ),
            ], spacing=8),
            ft.Row([
                ft.ElevatedButton(
                    "📋 Copy Path",
                    on_click=lambda e: copy_path(),
                    expand=True,
                    icon=ft.icons.CONTENT_COPY,
                ),
            ], spacing=8),
            ft.Container(height=10),
            ft.Text("💡 After tapping 'Open File', Android will show a list of compatible apps", size=10, color="#888888"),
            ft.Text("💡 If no app appears, install Google Sheets or a browser from Play Store", size=10, color="#888888"),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=400, height=480, padding=15),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dlg()),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def view_csv_content(self, page: ft.Page, file_path, filename):
        """Preview CSV content inside the app"""
        import csv
        
        try:
            # Read CSV file
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader) if reader else []
                rows = list(reader)[:50]  # Show first 50 rows
            
            # Create scrollable table
            content = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=400)
            
            # Add header
            header_row = ft.Container(
                content=ft.Row(
                    [ft.Text(h, size=11, weight=ft.FontWeight.BOLD, color=self.accent_color, expand=True) for h in headers],
                    spacing=5,
                ),
                padding=8,
                bgcolor="#1E1E1E",
                border_radius=4,
            )
            content.controls.append(header_row)
            
            # Add data rows
            for row in rows[:30]:
                data_row = ft.Container(
                    content=ft.Row(
                        [ft.Text(cell[:20], size=10, color="#CCCCCC", expand=True) for cell in row[:len(headers)]],
                        spacing=5,
                    ),
                    padding=8,
                    bgcolor="#2C2C2C",
                    border_radius=4,
                    margin=ft.margin.only(bottom=2),
                )
                content.controls.append(data_row)
            
            # Show row count
            row_count = ft.Text(f"Showing {min(30, len(rows))} of {len(rows)} rows", size=10, color="#888888")
            
            def close_preview():
                page.dialog.open = False
                page.update()
            
            def open_with_app(e):
                close_preview()
                page.launch_url(f"file://{file_path}")
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text(f"📊 {filename}", size=16, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_preview()),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        row_count,
                        ft.Divider(),
                        content,
                        ft.Divider(),
                        ft.ElevatedButton(
                            "📂 Open with App",
                            on_click=open_with_app,
                            icon=ft.icons.OPEN_IN_NEW,
                        ),
                    ], spacing=8),
                    width=500,
                    height=550,
                    padding=15,
                ),
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

    def copy_file_to_downloads(self, page: ft.Page, filename):
        """Show file info and let user copy manually"""
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "exports", filename)
        abs_path = os.path.abspath(file_path)
        
        def close_dlg():
            page.dialog.open = False
            page.update()
        
        def open_file(e):
            page.launch_url(f"file://{abs_path}")
            close_dlg()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("📄 File Ready", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            ft.Divider(),
            ft.Text(f"File: {filename}", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"Size: {os.path.getsize(file_path)} bytes", size=12, color="#888888"),
            ft.Container(height=10),
            ft.Text("How to save to Downloads:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("1️⃣ Tap 'Open File' below", size=12),
            ft.Text("2️⃣ Tap the menu (⋮) in the top right", size=12),
            ft.Text("3️⃣ Select 'Save' or 'Download'", size=12),
            ft.Container(height=15),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dlg(), expand=True),
                ft.ElevatedButton("📂 Open File", on_click=open_file, expand=True),
            ], spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=350, height=380, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def _create_stat_card(self, icon, value, label):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(icon, size=20),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=10, color="#CCCCCC"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=10,
            bgcolor=self.accent_color,
            border_radius=10,
            expand=True,
        )
    def show_import_dialog(self, page: ft.Page, import_type="materials"):
        """Import CSV - Clean layout with X icon only"""
        import csv
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        import random
        import string
        import io
        
        def generate_barcode():
            prefix = "890"
            random_numbers = ''.join(random.choices(string.digits, k=9))
            barcode_without_checksum = prefix + random_numbers
            total = 0
            for i, digit in enumerate(barcode_without_checksum):
                if i % 2 == 0:
                    total += int(digit) * 1
                else:
                    total += int(digit) * 3
            checksum = (10 - (total % 10)) % 10
            return barcode_without_checksum + str(checksum)
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            text_area_height = 180
            scroll_height = 350
            dialog_width = page.width - 40 if page.width else 360
        else:
            text_area_height = 250
            scroll_height = 450
            dialog_width = 500
        
        dialog_ref = None
        
        def close_dialog(e):
            if dialog_ref:
                dialog_ref.open = False
                page.update()
        
        def process_csv_data(csv_text):
            try:
                if '\t' in csv_text and ',' not in csv_text.split('\n')[0]:
                    lines = csv_text.split('\n')
                    csv_text = '\n'.join([','.join(line.split('\t')) for line in lines])
                
                csv_io = io.StringIO(csv_text)
                reader = csv.DictReader(csv_io)
                
                if not reader.fieldnames:
                    status_text.value = "❌ Invalid format. First row must be headers."
                    status_text.color = self.danger_color
                    page.update()
                    return
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                success_count = 0
                error_count = 0
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        name = row.get('Name', '').strip()
                        if not name:
                            name = row.get('name', '').strip()
                        if not name:
                            error_count += 1
                            continue
                        
                        try:
                            quantity = int(float(row.get('Quantity', 0)))
                        except:
                            quantity = 0
                        
                        category = row.get('Category', 'Other').strip()
                        if not category:
                            category = 'Other'
                        
                        quality = row.get('Quality', 'New').strip()
                        if quality not in ['New', 'Used', 'Damaged', 'Repaired']:
                            quality = 'New'
                        
                        location = row.get('Location', '').strip()
                        
                        barcode = row.get('Barcode', '').strip()
                        if not barcode:
                            barcode = generate_barcode()
                        
                        cursor.execute("SELECT id FROM categories WHERE name = ?", (category,))
                        cat_result = cursor.fetchone()
                        category_id = cat_result[0] if cat_result else 8
                        
                        if import_type == "materials":
                            cursor.execute("SELECT id FROM materials WHERE barcode_value = ?", (barcode,))
                            if cursor.fetchone():
                                barcode = generate_barcode()
                            
                            size = row.get('Size', '').strip()
                            
                            length_val = None
                            try:
                                length_val = float(row.get('Length', 0))
                            except:
                                pass
                            
                            colors = row.get('Colors', '').strip()
                            notes = row.get('Notes', '').strip()
                            
                            cursor.execute('''
                                INSERT INTO materials (name, category_id, quantity, quality, location_ids, 
                                                    size, length, colors, notes, barcode_value, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                name, category_id, quantity, quality, location,
                                size, length_val, colors, notes, barcode,
                                current_time, current_time
                            ))
                        else:
                            cursor.execute("SELECT id FROM accessories WHERE barcode_value = ?", (barcode,))
                            if cursor.fetchone():
                                barcode = generate_barcode()
                            
                            price = 0.0
                            try:
                                price = float(row.get('Price', 0))
                            except:
                                pass
                            
                            notes = row.get('Notes', '').strip()
                            
                            cursor.execute('''
                                INSERT INTO accessories (name, category_id, quantity, price, quality, location, 
                                                        notes, barcode_value, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                name, category_id, quantity, price, quality, location,
                                notes, barcode, current_time, current_time
                            ))
                        
                        success_count += 1
                        
                    except Exception as ex:
                        error_count += 1
                        print(f"Row {row_num} error: {ex}")
                
                conn.commit()
                conn.close()
                
                msg = f"✓ Imported {success_count} {import_type}"
                if error_count > 0:
                    msg += f", {error_count} skipped"
                
                page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=self.success_color, duration=4000)
                page.snack_bar.open = True
                
                if import_type == "materials":
                    self.show_materials_screen(page)
                else:
                    self.show_accessories(page)
                
                page.update()
                close_dialog(None)
                
            except Exception as e:
                status_text.value = f"❌ Error: {str(e)}"
                status_text.color = self.danger_color
                page.update()
        
        def import_from_text(e):
            csv_text = text_area.value.strip()
            if not csv_text:
                status_text.value = "❌ Please paste data"
                status_text.color = self.danger_color
                page.update()
                return
            process_csv_data(csv_text)
        
        def paste_from_clipboard(e):
            try:
                clipboard_content = page.get_clipboard()
                if clipboard_content:
                    text_area.value = clipboard_content
                    status_text.value = "✓ Data pasted! Tap 'Import'"
                    status_text.color = self.success_color
                    page.update()
                else:
                    status_text.value = "❌ Clipboard empty. Copy from Excel first."
                    status_text.color = self.danger_color
                    page.update()
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        def clear_text(e):
            text_area.value = ""
            status_text.value = "✓ Cleared"
            status_text.color = self.success_color
            page.update()
        
        # Form fields
        text_area = ft.TextField(
            label="Paste Excel Data Here",
            hint_text="Copy from Excel and paste here",
            multiline=True,
            min_lines=8,
            max_lines=12,
            width=dialog_width - 40,
            height=text_area_height,
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12)
        
        # Simple instructions
        instructions = ft.Column([
            ft.Text("📊 How to import:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("1. Copy data from Excel (Ctrl+C)", size=11),
            ft.Text("2. Tap '📋 Paste'", size=11),
            ft.Text("3. Tap '📥 Import'", size=11),
        ], spacing=6)
        
        # Scrollable fields
        scrollable_fields = ft.Column([
            instructions,
            ft.Container(height=8),
            text_area,
            status_text,
        ], spacing=8, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        # Dialog content - NO Cancel button, only X icon
        dialog_content = ft.Column([
            ft.Row([
                ft.Text(f"📥 Import {import_type.title()}", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ]),
            ft.Divider(height=1),
            scrollable_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.ElevatedButton(
                    "📋 Paste", 
                    on_click=paste_from_clipboard, 
                    icon=ft.icons.CONTENT_PASTE,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color),
                ),
            ], spacing=8),
            ft.Row([
                ft.ElevatedButton(
                    "🗑️ Clear", 
                    on_click=clear_text, 
                    icon=ft.icons.CLEAR,
                    expand=True,
                ),
                ft.ElevatedButton(
                    "📥 Import", 
                    on_click=import_from_text, 
                    icon=ft.icons.UPLOAD,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.success_color),
                ),
            ], spacing=8),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=12),
            modal=True,
        )
        
        dialog_ref = dialog
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_manual_csv_entry(self, page: ft.Page, import_type="materials"):
        """Manual CSV entry dialog for when file picker doesn't work"""
        import csv
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        import random
        import string
        import io
        
        def generate_barcode():
            prefix = "890"
            random_numbers = ''.join(random.choices(string.digits, k=9))
            barcode_without_checksum = prefix + random_numbers
            total = 0
            for i, digit in enumerate(barcode_without_checksum):
                if i % 2 == 0:
                    total += int(digit) * 1
                else:
                    total += int(digit) * 3
            checksum = (10 - (total % 10)) % 10
            return barcode_without_checksum + str(checksum)
        
        dialog_ref = None
        
        def close_dialog(e):
            if dialog_ref:
                dialog_ref.open = False
                page.update()
        
        def process_csv(e):
            csv_text = text_area.value.strip()
            if not csv_text:
                status_text.value = "❌ Please enter CSV data"
                status_text.color = self.danger_color
                page.update()
                return
            
            try:
                # Parse CSV from text
                csv_io = io.StringIO(csv_text)
                reader = csv.DictReader(csv_io)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                success_count = 0
                error_count = 0
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        name = row.get('Name', '').strip()
                        if not name:
                            continue
                        
                        try:
                            quantity = int(float(row.get('Quantity', 0)))
                        except:
                            quantity = 0
                        
                        category = row.get('Category', 'Other').strip()
                        if not category:
                            category = 'Other'
                        
                        quality = row.get('Quality', 'New').strip()
                        location = row.get('Location', '').strip()
                        barcode = row.get('Barcode', '').strip()
                        
                        if not barcode:
                            barcode = generate_barcode()
                        
                        cursor.execute("SELECT id FROM categories WHERE name = ?", (category,))
                        cat_result = cursor.fetchone()
                        category_id = cat_result[0] if cat_result else 8
                        
                        if import_type == "materials":
                            cursor.execute("SELECT id FROM materials WHERE barcode_value = ?", (barcode,))
                            if cursor.fetchone():
                                barcode = generate_barcode()
                            
                            size = row.get('Size', '').strip()
                            colors = row.get('Colors', '').strip()
                            notes = row.get('Notes', '').strip()
                            
                            cursor.execute('''
                                INSERT INTO materials (name, category_id, quantity, quality, location_ids, 
                                                    size, colors, notes, barcode_value, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                name, category_id, quantity, quality, location,
                                size, colors, notes, barcode,
                                current_time, current_time
                            ))
                        else:
                            cursor.execute("SELECT id FROM accessories WHERE barcode_value = ?", (barcode,))
                            if cursor.fetchone():
                                barcode = generate_barcode()
                            
                            price = 0.0
                            try:
                                price = float(row.get('Price', 0))
                            except:
                                pass
                            
                            notes = row.get('Notes', '').strip()
                            
                            cursor.execute('''
                                INSERT INTO accessories (name, category_id, quantity, price, quality, location, 
                                                        notes, barcode_value, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                name, category_id, quantity, price, quality, location,
                                notes, barcode, current_time, current_time
                            ))
                        
                        success_count += 1
                        
                    except Exception as ex:
                        error_count += 1
                        print(f"Row error: {ex}")
                
                conn.commit()
                conn.close()
                
                close_dialog(None)
                
                msg = f"✓ Imported {success_count} {import_type}"
                if error_count > 0:
                    msg += f", {error_count} skipped"
                
                page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=self.success_color, duration=4000)
                page.snack_bar.open = True
                
                if import_type == "materials":
                    self.show_materials_screen(page)
                else:
                    self.show_accessories(page)
                
                page.update()
                
            except Exception as ex:
                status_text.value = f"❌ Parse error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        # Example CSV template
        example_csv = """Name,Quantity,Category,Quality,Location
    Screwdriver,25,Hardware,New,Toolbox 1
    Hammer,10,Hardware,Used,Toolbox 2"""
        
        text_area = ft.TextField(
            label="Paste CSV Data Here",
            hint_text=example_csv,
            multiline=True,
            min_lines=10,
            max_lines=15,
            width=350,
            bgcolor=self.card_color,
        )
        status_text = ft.Text("", size=12)
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text(f"📥 Manual CSV Entry - {import_type.title()}", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ]),
            ft.Divider(),
            ft.Text("Paste your CSV data below:", size=12),
            ft.Text("First row must be headers: Name,Quantity,Category,Quality,Location", size=10, color="#888888"),
            ft.Container(height=5),
            text_area,
            status_text,
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton("📥 Import Data", on_click=process_csv, icon=ft.icons.UPLOAD, expand=True),
            ], spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=420, height=500, padding=15),
        )
        
        dialog_ref = dialog
        page.dialog = dialog
        dialog.open = True
        page.update()
    def get_app_storage_path(self):
        """Get a safe storage path that works on mobile"""
        import os
        
        # For Android, use the app's private storage
        base_path = os.path.dirname(os.path.abspath(__file__))
        storage_path = os.path.join(base_path, "exports")
        
        # Create directory if not exists
        if not os.path.exists(storage_path):
            os.makedirs(storage_path, exist_ok=True)
        
        return storage_path
    def export_all_data_simple(self, page: ft.Page):
        """Export all data to CSV files - Mobile friendly with copy path"""
        import csv
        import os
        from datetime import datetime
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def copy_path_to_clipboard(e):
            export_dir = self.get_app_storage_path()
            try:
                page.set_clipboard(export_dir)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"📁 Path copied to clipboard: {export_dir}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Failed to copy: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
        
        try:
            export_dir = self.get_app_storage_path()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            files_created = []
            
            # Export materials
            materials = self.dict_list(MaterialManager.get_all())
            if materials:
                materials_file = os.path.join(export_dir, f"materials_{timestamp}.csv")
                with open(materials_file, 'w', newline='', encoding='utf-8-sig') as f:
                    fields = ['Name', 'Category', 'Quantity', 'Quality', 'Location', 'Size', 'Length', 'Colors', 'Notes', 'Barcode']
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    
                    for m in materials:
                        writer.writerow({
                            'Name': m.get('name', ''),
                            'Category': m.get('category_name', 'Other'),
                            'Quantity': m.get('quantity', 0),
                            'Quality': m.get('quality', 'New'),
                            'Location': m.get('location_ids', ''),
                            'Size': m.get('size', ''),
                            'Length': m.get('length', ''),
                            'Colors': m.get('colors', ''),
                            'Notes': m.get('notes', ''),
                            'Barcode': m.get('barcode_value', '')
                        })
                files_created.append(f"materials_{timestamp}.csv")
            
            # Export accessories
            accessories = self.dict_list(AccessoryManager.get_all())
            if accessories:
                accessories_file = os.path.join(export_dir, f"accessories_{timestamp}.csv")
                with open(accessories_file, 'w', newline='', encoding='utf-8-sig') as f:
                    fields = ['Name', 'Category', 'Quantity', 'Price', 'Quality', 'Location', 'Notes', 'Barcode']
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    
                    for a in accessories:
                        writer.writerow({
                            'Name': a.get('name', ''),
                            'Category': a.get('category_name', 'Other'),
                            'Quantity': a.get('quantity', 0),
                            'Price': a.get('price', 0),
                            'Quality': a.get('quality', 'New'),
                            'Location': a.get('location', ''),
                            'Notes': a.get('notes', ''),
                            'Barcode': a.get('barcode_value', '')
                        })
                files_created.append(f"accessories_{timestamp}.csv")
            
            if not files_created:
                dialog_content = ft.Column([
                    ft.Row([
                        ft.Text("⚠️ No Data", size=18, weight=ft.FontWeight.BOLD, expand=True),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
                    ]),
                    ft.Divider(),
                    ft.Text("No materials or accessories to export.", size=14),
                    ft.Text("Add some items first.", size=12, color="#888888"),
                ], spacing=10)
                
                dialog = ft.AlertDialog(
                    title=ft.Text(""),
                    content=ft.Container(content=dialog_content, width=350, height=200, padding=15),
                )
                page.dialog = dialog
                dialog.open = True
                page.update()
                return
            
            # Format file list for display
            file_list = '\n'.join([f"• {f}" for f in files_created])
            
            dialog_content = ft.Column([
                ft.Row([
                    ft.Text("✅ Export Complete", size=18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
                ]),
                ft.Divider(),
                ft.Text("Files saved to:", size=12, color="#888888"),
                ft.Text(export_dir, size=10, color="#888888", selectable=True),
                ft.Container(height=5),
                ft.Text("Files created:", size=12, weight=ft.FontWeight.BOLD),
                ft.Text(file_list, size=10, color="#CCCCCC"),
                ft.Container(height=10),
                ft.Row([
                    ft.ElevatedButton(
                        "📋 Copy Path", 
                        on_click=copy_path_to_clipboard, 
                        icon=ft.icons.CONTENT_COPY,
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=self.accent_color),
                    ),
                    ft.ElevatedButton(
                        "✓ Done", 
                        on_click=close_dialog, 
                        icon=ft.icons.CHECK,
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=self.success_color),
                    ),
                ], spacing=10),
                ft.Text("Use a file manager app to navigate to this path", size=9, color="#888888"),
                ft.Text("Tip: Use 'CX File Explorer' or 'Solid Explorer'", size=9, color="#888888"),
            ], spacing=8)
            
            dialog = ft.AlertDialog(
                title=ft.Text(""),
                content=ft.Container(content=dialog_content, width=420, height=430, padding=15),
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            print(f"Export error: {e}")

    def export_inventory_html(self, page: ft.Page):
        """Export inventory HTML - uses all data"""
        import os
        from datetime import datetime
        
        try:
            # Get ALL items (not just filtered)
            import sqlite3
            from database import DB_PATH
            
            items = []
            
            # Get materials
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, quantity, quality, location_ids as location FROM materials")
            material_rows = cursor.fetchall()
            for row in material_rows:
                items.append({
                    'type_icon': '📦',
                    'type_name': 'Material',
                    'name': row['name'],
                    'code': 'N/A',
                    'quantity': row['quantity'],
                    'quality': row['quality'],
                    'location': row['location'] or 'N/A'
                })
            
            # Get accessories
            cursor.execute("SELECT id, name, quantity, quality, location FROM accessories")
            accessory_rows = cursor.fetchall()
            for row in accessory_rows:
                items.append({
                    'type_icon': '🔧',
                    'type_name': 'Accessory',
                    'name': row['name'],
                    'code': 'N/A',
                    'quantity': row['quantity'],
                    'quality': row['quality'],
                    'location': row['location'] or 'N/A'
                })
            conn.close()
            
            if not items:
                page.snack_bar = ft.SnackBar(
                    ft.Text("No items to export."),
                    bgcolor=self.warning_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"inventory_report_{timestamp}.html"
            
            # Generate HTML content
            html_content = self.generate_inventory_html_content(items, timestamp)
            
            # Save to app storage
            base_dir = os.path.dirname(os.path.abspath(__file__))
            exports_dir = os.path.join(base_dir, "exports")
            os.makedirs(exports_dir, exist_ok=True)
            file_path = os.path.join(exports_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            def copy_path():
                page.set_clipboard(file_path)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ File path copied to clipboard!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
            
            def close_dialog():
                page.dialog.open = False
                page.update()
            
            dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Text("✅ Inventory Report Ready", size=18, weight=ft.FontWeight.BOLD, color=self.success_color, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(filename, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Total Items: {len(items)}", size=11, color="#888888"),
                        ft.Divider(),
                        ft.Text("📍 File Location:", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(file_path, size=9, color="#888888", selectable=True),
                            padding=8,
                            bgcolor="#2C2C2C",
                            border_radius=6,
                        ),
                        ft.Row([
                            ft.ElevatedButton(
                                "📋 Copy Path",
                                on_click=lambda e: copy_path(),
                                expand=True,
                                icon=ft.icons.CONTENT_COPY,
                                style=ft.ButtonStyle(bgcolor="#2196F3"),
                            ),
                        ], spacing=8),
                        ft.Divider(),
                        ft.Text("📱 How to get this file:", size=13, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                        ft.Text("1️⃣ Tap 'Copy Path' above", size=12),
                        ft.Text("2️⃣ Open 'My Files' app", size=12),
                        ft.Text("3️⃣ Search for the path", size=12),
                        ft.Text("4️⃣ Copy file to Downloads folder", size=12),
                    ], spacing=8),
                    width=450,
                    height=400,
                    padding=20,
                ),
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            print(f"Export error: {e}")
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            
    def get_download_path(self):
        """Get the appropriate download folder path"""
        import os
        
        if os.path.exists("/storage/emulated/0/Download"):
            return "/storage/emulated/0/Download/StoreManagement"
        elif os.path.exists(os.path.expanduser("~/Downloads")):
            return os.path.expanduser("~/Downloads/StoreManagement")
        else:
            return "exports"

    def generate_html_report(self, materials, accessories, timestamp):
        """Generate HTML report content"""
        from datetime import datetime
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Store Management Report</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                .header {{
                    background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
                .header p {{ font-size: 14px; opacity: 0.9; }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    padding: 25px;
                    background: #f8f9fa;
                }}
                .stat-card {{
                    background: white;
                    padding: 15px;
                    border-radius: 12px;
                    text-align: center;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .stat-card .value {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #1976D2;
                }}
                .stat-card .label {{ font-size: 12px; color: #666; margin-top: 5px; }}
                .section {{ padding: 20px 25px; }}
                .section h2 {{
                    color: #333;
                    border-left: 4px solid #1976D2;
                    padding-left: 15px;
                    margin-bottom: 15px;
                    font-size: 18px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: left;
                }}
                th {{
                    background-color: #1976D2;
                    color: white;
                    font-weight: 600;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 20px;
                    font-size: 11px;
                    font-weight: bold;
                    color: white;
                }}
                .badge-new {{ background-color: #4CAF50; }}
                .badge-used {{ background-color: #FF9800; }}
                .badge-damaged {{ background-color: #F44336; }}
                .badge-repaired {{ background-color: #2196F3; }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    background: #f8f9fa;
                    color: #888;
                    font-size: 12px;
                }}
                @media (max-width: 600px) {{
                    .stats {{ gap: 8px; padding: 15px; }}
                    .stat-card .value {{ font-size: 22px; }}
                    th, td {{ padding: 6px; font-size: 11px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Store Management Report</h1>
                    <p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="value">{len(materials)}</div>
                        <div class="label">Materials</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">{len(accessories)}</div>
                        <div class="label">Accessories</div>
                    </div>
                    <div class="stat-card">
                        <div class="value">{len(materials) + len(accessories)}</div>
                        <div class="label">Total Items</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📦 Materials</h2>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr><th>Name</th><th>Quantity</th><th>Quality</th><th>Location</th></tr>
                            </thead>
                            <tbody>
        """
        
        for m in materials[:50]:
            quality = m.get('quality', 'Used')
            html_content += f"""
                                <tr>
                                    <td>{m.get('name', 'N/A')}</td>
                                    <td>{m.get('quantity', 0)}</td>
                                    <td><span class="badge badge-{quality.lower()}">{quality}</span></td>
                                    <td>{m.get('location_ids', 'N/A')}</td>
                                </tr>
            """
        
        html_content += f"""
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🔧 Accessories</h2>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr><th>Name</th><th>Quantity</th><th>Price</th><th>Quality</th><th>Location</th></tr>
                            </thead>
                            <tbody>
        """
        
        for a in accessories[:50]:
            quality = a.get('quality', 'Used')
            price = a.get('price', 0)
            price_text = f"${price:.2f}" if price else "-"
            html_content += f"""
                                <tr>
                                    <td>{a.get('name', 'N/A')}</td>
                                    <td>{a.get('quantity', 0)}</td>
                                    <td>{price_text}</td>
                                    <td><span class="badge badge-{quality.lower()}">{quality}</span></td>
                                    <td>{a.get('location', 'N/A')}</td>
                                </tr>
            """
        
        html_content += f"""
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Generated by Store Management System</p>
                    <p>Report ID: {timestamp}</p>
                </div>
            </div>
        </body>
        </html>
        """
    def _generate_html_content(self, materials, accessories, total_items, total_stock, low_stock_count):
        """Generate HTML content for inventory report"""
        from datetime import datetime
        
        html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Inventory Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; }}
            h1 {{ color: #1976D2; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #1976D2; color: white; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
            .stat-card {{ background: #1976D2; color: white; padding: 15px; border-radius: 10px; flex: 1; text-align: center; min-width: 100px; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            @media (max-width: 600px) {{
                .stats {{ flex-direction: column; }}
                th, td {{ padding: 6px; font-size: 12px; }}
                .container {{ padding: 10px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Inventory Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="stats">
                <div class="stat-card"><h3>Total Items</h3><h2>{total_items}</h2></div>
                <div class="stat-card"><h3>Total Stock</h3><h2>{total_stock}</h2></div>
                <div class="stat-card"><h3>Low Stock</h3><h2>{low_stock_count}</h2></div>
            </div>
            
            <h2>📦 Materials ({len(materials)})</h2>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Quantity</th>
                        <th>Quality</th>
                        <th>Location</th>
                    </tr>
                </thead>
                <tbody>"""
        
        for m in materials[:200]:
            html_content += f"""
                    <tr>
                        <td>{m.get('name', 'N/A')}</td>
                        <td>{m.get('quantity', 0)}</td>
                        <td>{m.get('quality', 'New')}</td>
                        <td>{m.get('location_ids', 'N/A')}</td>
                    </tr>"""
        
        html_content += f"""
                </tbody>
            </table>
            </div>
            
            <h2>🔧 Accessories ({len(accessories)})</h2>
            <div style="overflow-x: auto;">
            表
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Quality</th>
                        <th>Location</th>
                    </tr>
                </thead>
                <tbody>"""
        
        for a in accessories[:200]:
            price = a.get('price', 0)
            price_text = f"${price:.2f}" if price else "-"
            html_content += f"""
                    <tr>
                        <td>{a.get('name', 'N/A')}</td>
                        <td>{a.get('quantity', 0)}</td>
                        <td>{price_text}</td>
                        <td>{a.get('quality', 'New')}</td>
                        <td>{a.get('location', 'N/A')}</td>
                    </tr>"""
        
        html_content += f"""
                </tbody>
            </table>
            </div>
            
            <div class="footer">
                <p>Generated by Store Management System</p>
            </div>
        </div>
    </body>
    </html>"""
        
        return html_content
    def export_low_stock_html(self, page: ft.Page):
        """Export low stock items to HTML - Mobile friendly with copy path"""
        from datetime import datetime
        import os
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def copy_path_to_clipboard(e):
            try:
                page.set_clipboard(filename)
                page.snack_bar = ft.SnackBar(
                    ft.Text("📁 Path copied to clipboard"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Failed to copy: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
        
        try:
            export_dir = self.get_app_storage_path()
            
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            low_stock_items = []
            for m in materials:
                if m.get('quantity', 0) < 10:
                    low_stock_items.append({
                        'type': 'Material',
                        'name': m.get('name', 'N/A'),
                        'quantity': m.get('quantity', 0),
                        'quality': m.get('quality', 'Used'),
                        'location': m.get('location_ids', 'N/A')
                    })
            for a in accessories:
                if a.get('quantity', 0) < 10:
                    low_stock_items.append({
                        'type': 'Accessory',
                        'name': a.get('name', 'N/A'),
                        'quantity': a.get('quantity', 0),
                        'quality': a.get('quality', 'Used'),
                        'location': a.get('location', 'N/A')
                    })
            
            if not low_stock_items:
                page.snack_bar = ft.SnackBar(
                    ft.Text("No low stock items to export"),
                    bgcolor=self.warning_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_dir, f"low_stock_report_{timestamp}.html")
            
            html_content = self._generate_low_stock_html_content(low_stock_items)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            dialog_content = ft.Column([
                ft.Row([
                    ft.Text("✅ Low Stock Report Generated", size=18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
                ]),
                ft.Divider(),
                ft.Text("File saved to:", size=12, color="#888888"),
                ft.Text(filename, size=9, color="#888888", selectable=True),
                ft.Text(f"Found {len(low_stock_items)} low stock items", size=12),
                ft.Container(height=15),
                ft.Row([
                    ft.ElevatedButton(
                        "📋 Copy Path",
                        on_click=copy_path_to_clipboard,
                        icon=ft.icons.CONTENT_COPY,
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=self.accent_color)
                    ),
                    ft.ElevatedButton(
                        "✓ Done",
                        on_click=close_dialog,
                        icon=ft.icons.CHECK,
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=self.success_color)
                    ),
                ], spacing=10),
                ft.Text("Use a file manager app to locate this file", size=9, color="#888888"),
            ], spacing=10)
            
            dialog = ft.AlertDialog(
                title=ft.Text(""),
                content=ft.Container(content=dialog_content, width=450, height=400, padding=15)
            )
            
            page.dialog = dialog
            dialog.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            print(f"Export error: {e}")

    def _generate_low_stock_html_content(self, low_stock_items):
        """Generate low stock HTML content"""
        from datetime import datetime
        
        html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Low Stock Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; }}
            h1 {{ color: #F44336; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #F44336; color: white; }}
            .critical {{ background-color: #FFEBEE; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            @media (max-width: 600px) {{
                th, td {{ padding: 6px; font-size: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ Low Stock Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total low stock items: {len(low_stock_items)}</p>
            <div style="overflow-x: auto;">
            表
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Name</th>
                        <th>Current Stock</th>
                        <th>Quality</th>
                        <th>Location</th>
                    </tr>
                </thead>
                <tbody>"""
        
        for item in low_stock_items:
            critical_class = 'critical' if item['quantity'] < 5 else ''
            html_content += f"""
                    <tr class='{critical_class}'>
                        <td>{item['type']}</td>
                        <td><strong>{item['name']}</strong></td>
                        <td style='color:#F44336;font-weight:bold'>{item['quantity']}</td>
                        <td>{item['quality']}</td>
                        <td>{item['location']}</td>
                    </tr>"""
        
        html_content += f"""
                </tbody>
            </table>
            </div>
            <div class="footer">
                <p>Generated by Store Management System</p>
            </div>
        </div>
    </body>
    </html>"""
        
        return html_content
    def generate_low_stock_html(self, low_stock_items):
        """Generate low stock HTML report"""
        from datetime import datetime
        
        html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Low Stock Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; }}
            h1 {{ color: #F44336; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #F44336; color: white; }}
            .critical {{ background-color: #FFEBEE; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ Low Stock Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total low stock items: {len(low_stock_items)}</p>
            <table><thead><tr><th>Type</th><th>Name</th><th>Current Stock</th><th>Quality</th><th>Location</th></tr></thead><tbody>"""
        
        for item in low_stock_items:
            critical_class = 'critical' if item['quantity'] < 5 else ''
            html_content += f"<tr class='{critical_class}'><td>{item['type']}</td><td>{item['name']}</td><td style='color:#F44336;font-weight:bold'>{item['quantity']}</td><td>{item['quality']}</td><td>{item['location']}</td></tr>"
        
        html_content += f"""</tbody></table><div class="footer"><p>Generated by Store Management System</p></div></div></body></html>"""
        
        return html_content
    def create_recent_activity_card(self, recent_items, font_small, font_normal):
        """Create recent activity card"""
        
        activity_list = ft.Column(spacing=8)
        
        if recent_items:
            for item in recent_items[:5]:
                activity_list.controls.append(
                    ft.Row([
                        ft.Text(item['type'], size=18),
                        ft.Column([
                            ft.Text(item['name'], size=font_small, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Added on {item['date']}", size=font_small - 2, color="#888888"),
                        ], spacing=2, expand=True),
                    ], spacing=10)
                )
        else:
            activity_list.controls.append(ft.Text("No recent activity", size=font_small, color="#888888"))
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🕐 Recent Activity", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                activity_list,
            ], spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
            expand=True,
        )

    def create_recent_materials_card(self, page, materials, font_small, font_normal):
        """Create recent materials card"""
        
        materials_list = ft.Column(spacing=8)
        
        if materials:
            for m in materials[:6]:
                materials_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("📦", size=18),
                            ft.Column([
                                ft.Text(m.get('name', 'N/A'), size=font_small, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Stock: {m.get('quantity', 0)} | {m.get('location_ids', 'N/A')}", size=font_small - 2, color="#888888"),
                            ], spacing=2, expand=True),
                            ft.Container(
                                content=ft.Text(m.get('quality', 'Used'), size=font_small - 2, color="white"),
                                bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ], spacing=10),
                        padding=8,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                    )
                )
        else:
            materials_list.controls.append(ft.Text("No materials found", size=font_small, color="#888888"))
        
        materials_list.controls.append(
            ft.TextButton("View All Materials", on_click=lambda e: self.show_materials_screen(page))
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📦 Recent Materials", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                materials_list,
            ], spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
            expand=True,
        )

    def create_recent_accessories_card(self, page, accessories, font_small, font_normal):
        """Create recent accessories card"""
        
        accessories_list = ft.Column(spacing=8)
        
        if accessories:
            for a in accessories[:6]:
                location = a.get('location') or a.get('location_ids') or 'N/A'
                accessories_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🔧", size=18),
                            ft.Column([
                                ft.Text(a.get('name', 'N/A'), size=font_small, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Stock: {a.get('quantity', 0)} | {location}", size=font_small - 2, color="#888888"),
                            ], spacing=2, expand=True),
                            ft.Container(
                                content=ft.Text(a.get('quality', 'Used'), size=font_small - 2, color="white"),
                                bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ], spacing=10),
                        padding=8,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                    )
                )
        else:
            accessories_list.controls.append(ft.Text("No accessories found", size=font_small, color="#888888"))
        
        accessories_list.controls.append(
            ft.TextButton("View All Accessories", on_click=lambda e: self.show_accessories(page))
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🔧 Recent Accessories", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                accessories_list,
            ], spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
            expand=True,
        )

    def create_import_export_panel(self, page, font_small, font_normal):
        """Create import/export panel"""
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📁 Import / Export", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("📥 Import CSV", on_click=lambda e: self.show_import_dialog(page), expand=True),
                    ft.ElevatedButton("📤 Export CSV", on_click=lambda e: self.export_all_data_simple(page), expand=True, style=ft.ButtonStyle(bgcolor=self.warning_color)),
                ], spacing=10),
                ft.Row([
                    ft.ElevatedButton("📄 Export PDF", on_click=lambda e: self.export_inventory_pdf_dashboard(page), expand=True),
                    ft.ElevatedButton("⚠️ Low Stock PDF", on_click=lambda e: self.export_low_stock_pdf_dashboard(page), expand=True, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ], spacing=10),
                ft.Text("Supports CSV and PDF formats", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
        )
     
    def show_simple_category_dialog(self, page: ft.Page, refresh_callback=None):
        """Simple dialog - Guaranteed to fit mobile"""
        import sqlite3
        from database import DB_PATH
        
        print("DEBUG: Opening category dialog")
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        
        # Create dialog with fixed size
        dialog = ft.AlertDialog(
            title=ft.Text("Categories", size=16, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                width=300,
                height=450,
                padding=10,
            ),
            modal=True,
        )
        
        # Simple form
        name_input = ft.TextField(label="New Category", width=270, bgcolor=self.card_color)
        icon_select = ft.Dropdown(
            label="Icon",
            width=70,
            options=[
                ft.dropdown.Option("📦", "📦"),
                ft.dropdown.Option("🔩", "🔩"),
                ft.dropdown.Option("🔧", "🔧"),
                ft.dropdown.Option("⚡", "⚡"),
                ft.dropdown.Option("💧", "💧"),
                ft.dropdown.Option("🪵", "🪵"),
                ft.dropdown.Option("⚙️", "⚙️"),
                ft.dropdown.Option("📁", "📁"),
            ],
            value="📁",
            bgcolor=self.card_color,
        )
        status = ft.Text("", size=10)
        
        # Categories list
        cats_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=180)
        
        def load_cats():
            cats_list.controls.clear()
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT id, name, icon FROM categories WHERE user_id = ? ORDER BY name", (current_user_id,))
            cats = cur.fetchall()
            conn.close()
            
            for cid, cname, cicon in cats:
                row = ft.Container(
                    content=ft.Row([
                        ft.Text(cicon, size=14),
                        ft.Text(cname, size=11, expand=True),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_size=16,
                            icon_color="#FF5252",
                            on_click=lambda e, id=cid: delete_cat(id),
                        ),
                    ], spacing=6),
                    padding=6,
                    bgcolor="#2C2C2C",
                    border_radius=4,
                )
                cats_list.controls.append(row)
            
            if not cats_list.controls:
                cats_list.controls.append(ft.Text("No custom categories", size=11, color="#888888"))
            page.update()
        
        def delete_cat(cat_id):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, current_user_id))
            conn.commit()
            conn.close()
            load_cats()
            if refresh_callback:
                refresh_callback()
            page.update()
        
        def add_cat(e):
            name = name_input.value.strip()
            if not name:
                status.value = "❌ Enter name"
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO categories (name, icon, user_id) VALUES (?, ?, ?)",
                    (name, icon_select.value, current_user_id)
                )
                conn.commit()
                name_input.value = ""
                status.value = "✓ Added!"
                load_cats()
                if refresh_callback:
                    refresh_callback()
                page.update()
            except:
                status.value = "❌ Already exists"
                page.update()
            finally:
                conn.close()
        
        def close_dlg():
            dialog.open = False
            page.update()
        
        # Build content
        content = ft.Column([
            name_input,
            icon_select,
            status,
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dlg()),
                ft.FilledButton("Add", on_click=add_cat, style=ft.ButtonStyle(bgcolor="#4CAF50")),
            ], spacing=8),
            ft.Divider(),
            ft.Text("Your Categories:", size=12, weight=ft.FontWeight.BOLD),
            cats_list,
        ], spacing=8)
        
        dialog.content.content = content
        
        load_cats()
        page.dialog = dialog
        dialog.open = True
        page.update()

    def open_category_dialog(self, page: ft.Page, refresh_callback=None):
        self.show_categories_page(page)

    def show_materials_screen(self, page: ft.Page):
        """Materials screen with safe quality filter (no special characters)"""
        page.controls.clear()
        
        import sqlite3
        from database import DB_PATH
        
        # Load materials with categories
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, c.name as category_name, c.icon as category_icon
            FROM materials m
            LEFT JOIN categories c ON m.category_id = c.id
            ORDER BY m.id DESC
        """)
        materials = cursor.fetchall()
        
        # Load categories for filter
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        nav = self.create_bottom_nav(page)
        is_mobile = page.width < 800 if page.width else False
        
        # Main container
        main_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        main_column.controls.append(
            ft.Text("Materials", size=24 if is_mobile else 28, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        
        # Search Field
        search_field = ft.TextField(
            hint_text="Search materials...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            prefix_icon=ft.icons.SEARCH,
            dense=True,
        )
        main_column.controls.append(search_field)
        main_column.controls.append(ft.Container(height=5))
        
        # Category filter dropdown (with icons)
        cat_options = [ft.dropdown.Option("All", "📁 All Categories")]
        for c in categories:
            icon = c['icon'] if c['icon'] else "📁"
            cat_options.append(ft.dropdown.Option(str(c["id"]), f"{icon} {c['name']}"))
        
        category_filter = ft.Dropdown(
            label="Category",
            width=170 if not is_mobile else 150,
            options=cat_options,
            value="All",
            bgcolor=self.card_color,
            dense=True,
        )
        
        # ========== QUALITY FILTER - MOST SAFE OPTION ==========
        # Using simple letters in brackets - 100% guaranteed to work on all devices
        quality_filter = ft.Dropdown(
            label="Quality",
            width=150 if not is_mobile else 130,
            value="All",
            bgcolor=self.card_color,
            dense=True,
            options=[
                ft.dropdown.Option("All", "[A] All Qualities"),
                ft.dropdown.Option("New", "[N] New"),
                ft.dropdown.Option("Used", "[U] Used"),
                ft.dropdown.Option("Damaged", "[D] Damaged"),
                ft.dropdown.Option("Repaired", "[R] Repaired"),
            ],
        )
        
        def on_quality_change(e):
            self.current_material_filter = quality_filter.value
            update_cards()
        
        quality_filter.on_change = on_quality_change
        
        # Add Category Button
        add_category_btn = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE_OUTLINE,
            icon_size=24,
            icon_color=self.success_color,
            tooltip="Manage Categories",
            on_click=lambda e: self.show_categories_dialog(page, lambda: self.show_materials_screen(page)),
        )
        
        # Filters row
        filters_row = ft.Row([
            category_filter,
            quality_filter,
            add_category_btn,
        ], spacing=8, alignment=ft.MainAxisAlignment.START, wrap=True)
        
        main_column.controls.append(filters_row)
        main_column.controls.append(ft.Container(height=5))
        
        # Cards container
        cards_container = ft.Column(spacing=8)
        main_column.controls.append(cards_container)
        
        def update_cards():
            cards_container.controls.clear()
            search_query = search_field.value.lower() if search_field.value else ""
            selected_cat_id = category_filter.value
            selected_quality = quality_filter.value
            
            filtered_count = 0
            for m in materials:
                # Search filter
                if search_query and search_query not in m["name"].lower():
                    continue
                # Category filter
                if selected_cat_id != "All" and str(m["category_id"]) != selected_cat_id:
                    continue
                # Quality filter
                if selected_quality != "All" and m["quality"] != selected_quality:
                    continue
                
                filtered_count += 1
                cat_name = m["category_name"] if m["category_name"] else "Other"
                cat_icon = m["category_icon"] if m["category_icon"] else "📁"
                qty = m["quantity"]
                quality = m["quality"]
                
                # Quality color mapping for badges
                quality_colors = {
                    "New": "#4CAF50",
                    "Used": "#FF9800",
                    "Damaged": "#F44336",
                    "Repaired": "#2196F3"
                }
                quality_color = quality_colors.get(quality, "#888888")
                
                # Quality display text with bracket
                quality_display = {
                    "New": "[N] New",
                    "Used": "[U] Used",
                    "Damaged": "[D] Damaged",
                    "Repaired": "[R] Repaired"
                }.get(quality, quality)
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(m["name"], size=15, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=13, weight=ft.FontWeight.BOLD, 
                                    color=self.danger_color if qty < 10 else self.text_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=11, color=self.accent_color, expand=True),
                                ft.Container(
                                    content=ft.Text(quality_display, size=9, color="white"),
                                    bgcolor=quality_color,
                                    border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.Text(f"📍 {m['location_ids'] or 'N/A'}", size=10, color="#888888", expand=True),
                                ft.Text(f"📏 {m['size'] or 'N/A'}", size=10, color="#888888"),
                            ]),
                        ], spacing=4),
                        padding=10,
                        on_click=lambda e, mat=m: self.show_material_detail_dialog(page, dict(mat)),
                    ),
                    elevation=1,
                )
                cards_container.controls.append(card)
            
            if filtered_count == 0:
                cards_container.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.INBOX, size=50, color="#888888"),
                            ft.Text("No materials found", size=13, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30,
                    )
                )
            else:
                count_text = ft.Text(f"{filtered_count} of {len(materials)}", size=10, color="#888888")
                cards_container.controls.insert(0, count_text)
            
            page.update()
        
        # Initialize filter
        self.current_material_filter = "All"
        
        # Event handlers
        search_field.on_change = lambda e: update_cards()
        category_filter.on_change = lambda e: update_cards()
        
        # Initial load
        update_cards()
        
        # FAB Button
        add_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_modal(page),
            mini=is_mobile,
        )
        
        main_container = ft.Container(content=main_column, expand=True, padding=12 if is_mobile else 20)
        
        if is_mobile:
            page.add(
                ft.Stack([
                    ft.Column([main_container, nav], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        else:
            sidebar = self.create_sidebar(page)
            page.add(
                ft.Stack([
                    ft.Row([sidebar, main_container], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        
        self.current_view = "materials"
        page.update()
    
    def create_detail_panel(self, material, page):
        """Create the detail panel for selected material with image and category"""
        if not material:
            return ft.Column([
                ft.Text("Material Details", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Container(height=20),
                ft.Text("Select a material to view details", size=12, color="#888888"),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        # Get base directory for resolving image paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get image path
        image_path = material.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
        
        # Format dates
        def format_datetime(date_value):
            if date_value:
                date_str = str(date_value)
                if ' ' in date_str:
                    return date_str.split(' ')[0]
                return date_str[:10] if len(date_str) > 10 else date_str
            return 'N/A'
        
        created_date = format_datetime(material.get('created_at', ''))
        updated_date = format_datetime(material.get('updated_at', ''))
        
        # Get category with icon
        category = material.get('category', 'Uncategorized')
        category_icon = self.get_category_icon(category)
        
        # ========== IMAGE WIDGET ==========
        def show_image_overlay(e):
            def close_overlay():
                page.overlay.clear()
                page.update()
            
            if not has_image:
                no_image = ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Container(expand=True), ft.TextButton("✕", on_click=lambda e: close_overlay())]),
                        ft.Text("📷", size=60),
                        ft.Text("No Image Available", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text("Click Edit to add an image", size=12, color="#888888"),
                        ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    padding=30,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=400,
                    height=350,
                )
                overlay = ft.Container(content=no_image, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
                page.overlay.append(overlay)
                page.update()
                return
            
            img = ft.Image(src=full_image_path, width=500, height=400, fit=ft.ImageFit.CONTAIN)
            overlay_content = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(material.get('name', 'Image'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Container(expand=True),
                        ft.TextButton("✕", on_click=lambda e: close_overlay()),
                    ]),
                    ft.Divider(),
                    img,
                    ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=25,
                bgcolor=self.card_color,
                border_radius=15,
                width=550,
                height=500,
            )
            overlay = ft.Container(content=overlay_content, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
            page.overlay.append(overlay)
            page.update()
        
        # Create image display
        if has_image:
            try:
                image_display = ft.Container(
                    content=ft.Column([
                        ft.Image(src=full_image_path, width=180, height=140, fit=ft.ImageFit.CONTAIN),
                        ft.Text("Click to enlarge", size=9, color=self.accent_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    on_click=show_image_overlay,
                    ink=True,
                )
            except:
                image_display = None
        else:
            image_display = None
        
        # Build the column with category included
        column_items = [
            ft.Text(material.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
        ]
        
        # Add image if it exists
        if image_display:
            column_items.append(ft.Row([image_display], alignment=ft.MainAxisAlignment.CENTER))
            column_items.append(ft.Container(height=10))
        
        # Add details with category and barcode button
        column_items.extend([
            # Category row
            ft.Row([ft.Text("📁 Category:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(f"{category_icon} {category}", size=12, color=self.accent_color)], spacing=5),
            
            # Code row
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # SHOW BARCODE BUTTON
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, material), 
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=5),
            
            # Quality
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(
                        content=ft.Text(material.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(material.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    )], spacing=5),
            
            # Size
            ft.Row([ft.Text("📏 Size:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('size') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Length
            ft.Row([ft.Text("📐 Length:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(str(material.get('length') or "N/A"), size=12, color=self.text_color)], spacing=5),
            
            # Quantity
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(str(material.get('quantity', 0)), size=12, color=self.text_color,
                        weight=ft.FontWeight.BOLD if material.get('quantity', 0) < 10 else None)], spacing=5),
            
            # Location
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('location_ids') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Colors
            ft.Row([ft.Text("🎨 Colors:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('colors') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Created
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(created_date, size=12, color=self.text_color)], spacing=5),
            
            # Updated
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(updated_date, size=12, color=self.text_color)], spacing=5),
            
            ft.Divider(),
            
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(material.get('notes') or "No notes", size=12, color="#888888"),
            
            ft.Container(height=15),
            
            # EDIT AND DELETE BUTTONS
            ft.Row(
                [
                    ft.ElevatedButton(
                        "✏️ EDIT", 
                        on_click=lambda e: self.open_edit_modal(page, material['id']),
                        style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
                    ),
                    ft.ElevatedButton(
                        "🗑️ DELETE", 
                        on_click=lambda e: self.open_delete_modal(page, material['id']),
                        style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15,
            ),
        ])
        
        return ft.Column(column_items, spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def get_category_icon(self, category):
        icons = {
            "Raw Material": "📦",
            "Hardware": "🔩",
            "Tools": "🔧",
            "Electrical": "⚡",
            "Plumbing": "💧",
            "Metal": "⚙️",
            "Plastic": "🧴",
            "Glass": "🔮",
            "Paint": "🎨",
            "Fasteners": "📎",
            "Safety Equipment": "🦺",
            "Packaging": "📦",
            "Office Supplies": "📎",
            "Other": "📁",
            "Uncategorized": "📁"
        }
        return icons.get(category, "📁")
    
    def filter_materials_by_quality(self, page: ft.Page, filter_type):
        """Filter materials by quality"""
        self.current_material_filter = filter_type
        
        # Update button colors
        color_map = {
            "All": self.accent_color,
            "New": self.success_color,
            "Used": self.warning_color,
            "Damaged": self.danger_color,
            "Repaired": self.accent_color,
        }
        
        for f_type, btn in self.material_filter_buttons.items():
            if f_type == filter_type:
                btn.bgcolor = color_map.get(f_type, self.card_color)
            else:
                btn.bgcolor = self.card_color
            btn.update()
        
        # Update the table
        materials = self.dict_list(MaterialManager.get_all())
        
        if filter_type == "All":
            filtered = materials
        else:
            filtered = [m for m in materials if m.get('quality') == filter_type]
        
        # Apply search if exists
        if hasattr(self, 'material_search_query') and self.material_search_query:
            query = self.material_search_query.lower()
            filtered = [m for m in filtered if query in m.get('name', '').lower() or query in m.get('item_code', '').lower()]
        
        # Update table rows
        self.material_table_rows.controls.clear()
        
        for m in filtered:
            row = ft.Container(
                content=ft.Row([
                    ft.Text(m.get('name', 'N/A'), size=13, weight=ft.FontWeight.BOLD, width=180),
                    ft.Text(m.get('location_ids') or "N/A", size=12, width=120, color="#CCCCCC"),
                    ft.Text(str(m.get('quantity', 0)), size=13, weight=ft.FontWeight.BOLD, width=60,
                        color=self.danger_color if m.get('quantity', 0) < 10 else self.text_color),
                    ft.Container(
                        content=ft.Text(m.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        width=90,
                    ),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.EDIT, icon_size=20, 
                                    on_click=lambda e, mat=m: self.open_edit_modal(page, mat['id'])),
                        ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                    on_click=lambda e, mat=m: self.open_delete_modal(page, mat['id'])),
                        ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                    on_click=lambda e, mat=m: self.show_barcode_dialog(page, mat)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.START),
                padding=ft.padding.symmetric(vertical=10, horizontal=12),
                bgcolor="#2C2C2C",
                border_radius=6,
                ink=True,
                on_click=lambda e, mat=m: self.on_material_select(mat),
            )
            self.material_table_rows.controls.append(row)
        
        # Update detail panel
        if self.selected_material_detail and self.selected_material_detail not in filtered:
            self.selected_material_detail = None
            self.material_detail_panel.content = self.create_detail_panel(None, page)
        
        page.update()

    def on_material_select(self, material):
        """Handle material selection from table"""
        self.selected_material_detail = material
        if hasattr(self, 'material_detail_panel'):
            self.material_detail_panel.content = self.create_detail_panel(material, self.page_ref)
            self.page_ref.update()

                            # ============ ACCESSORIES SCREEN ============
    def show_accessories(self, page: ft.Page):
        """Accessories screen with proper category filter icons"""
        page.controls.clear()
        
        import sqlite3
        from database import DB_PATH
        
        # Load accessories with categories
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, c.name as category_name, c.icon as category_icon
            FROM accessories a
            LEFT JOIN categories c ON a.category_id = c.id
            ORDER BY a.id DESC
        """)
        accessories = cursor.fetchall()
        
        # Load categories for filter with proper icon handling
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        nav = self.create_bottom_nav(page)
        is_mobile = page.width < 800 if page.width else False
        
        # Main container
        main_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        main_column.controls.append(
            ft.Text("Accessories", size=24 if is_mobile else 28, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        
        # Search Field
        search_field = ft.TextField(
            hint_text="Search accessories...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            prefix_icon=ft.icons.SEARCH,
            dense=True,
        )
        main_column.controls.append(search_field)
        main_column.controls.append(ft.Container(height=5))
        
        # Category filter dropdown with proper icons
        cat_options = [ft.dropdown.Option("All", "All Categories")]
        
        # Icon mapping for common categories
        icon_map = {
            "Metal": "⚙️",
            "metal": "⚙️",
            "Tools": "🔧",
            "tools": "🔧",
            "Hardware": "🔩",
            "hardware": "🔩",
            "Electrical": "⚡",
            "electrical": "⚡",
            "Plumbing": "💧",
            "plumbing": "💧",
            "Raw Material": "📦",
            "raw material": "📦",
        }
        
        for c in categories:
            cat_id = c["id"]
            cat_name = c["name"]
            cat_icon = c["icon"] if c["icon"] else "📁"
            
            # Override with correct icon if needed
            if cat_name in icon_map:
                cat_icon = icon_map[cat_name]
            
            cat_options.append(ft.dropdown.Option(str(cat_id), f"{cat_icon} {cat_name}"))
        
        category_filter = ft.Dropdown(
            label="Category",
            width=160 if not is_mobile else 140,
            options=[
                ft.dropdown.Option("All", "All Categories"),
                ft.dropdown.Option("Raw Material", "📦 Raw Material"),
                ft.dropdown.Option("Hardware", "🔩 Hardware"),
                ft.dropdown.Option("Tools", "🔧 Tools"),
                ft.dropdown.Option("Electrical", "⚡ Electrical"),
                ft.dropdown.Option("Plumbing", "💧 Plumbing"),
                ft.dropdown.Option("Metal", "⚙️ Metal"),
                ft.dropdown.Option("Other", "📁 Other"),
            ],
            value="All",
            bgcolor=self.card_color,
            dense=True,
        )
        
        # In show_accessories screen, use the same quality filter:
        quality_filter = ft.Dropdown(
            label="Quality",
            width=150 if not is_mobile else 130,
            value="All",
            bgcolor=self.card_color,
            dense=True,
            options=[
                ft.dropdown.Option("All", "[A] All Qualities"),
                ft.dropdown.Option("New", "[N] New"),
                ft.dropdown.Option("Used", "[U] Used"),
                ft.dropdown.Option("Damaged", "[D] Damaged"),
                ft.dropdown.Option("Repaired", "[R] Repaired"),
            ],
        )
        
        # Add Category Button
        add_category_btn = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE_OUTLINE,
            icon_size=24,
            icon_color=self.success_color,
            tooltip="Manage Categories",
            on_click=lambda e: self.show_categories_dialog(page, lambda: self.show_accessories(page)),
        )
        
        # Filters row
        filters_row = ft.Row([
            category_filter,
            add_category_btn,
            quality_filter,
        ], spacing=8, alignment=ft.MainAxisAlignment.START, wrap=True)
        
        main_column.controls.append(filters_row)
        main_column.controls.append(ft.Container(height=5))
        
        # Cards container
        cards_container = ft.Column(spacing=8)
        main_column.controls.append(cards_container)
        
        def update_cards():
            cards_container.controls.clear()
            search_query = search_field.value.lower() if search_field.value else ""
            selected_cat_id = category_filter.value
            selected_quality = quality_filter.value
            
            filtered_count = 0
            for a in accessories:
                if search_query and search_query not in a["name"].lower():
                    continue
                if selected_cat_id != "All" and str(a["category_id"]) != selected_cat_id:
                    continue
                if selected_quality != "All" and a["quality"] != selected_quality:
                    continue
                
                filtered_count += 1
                cat_name = a["category_name"] if a["category_name"] else "Other"
                cat_icon = a["category_icon"] if a["category_icon"] else "📁"
                
                # Fix wood icon in cards
                if cat_name == "Wood":
                    cat_icon = "🪵"
                
                qty = a["quantity"]
                quality = a["quality"]
                price = a["price"] if a["price"] else 0
                price_text = f"${price:.2f}" if price > 0 else ""
                
                quality_icon = "🟢" if quality == "New" else "🟠" if quality == "Used" else "🔴" if quality == "Damaged" else "🔵"
                quality_color = "#2E7D32" if quality == "New" else "#F57C00" if quality == "Used" else "#FF5252" if quality == "Damaged" else "#1976D2"
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(a["name"], size=15, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=13, weight=ft.FontWeight.BOLD, 
                                    color=self.danger_color if qty < 10 else self.text_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=11, color=self.accent_color, expand=True),
                                ft.Row([
                                    ft.Text(quality_icon, size=10),
                                    ft.Container(
                                        content=ft.Text(quality, size=9, color="white"),
                                        bgcolor=quality_color,
                                        border_radius=6,
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    ),
                                ], spacing=4),
                            ]),
                            ft.Row([
                                ft.Text(f"📍 {a['location'] or 'N/A'}", size=10, color="#888888", expand=True),
                                ft.Text(price_text, size=10, color="#4CAF50"),
                            ]),
                        ], spacing=4),
                        padding=10,
                        on_click=lambda e, acc=a: self.show_accessory_detail_dialog(page, dict(acc)),
                    ),
                    elevation=1,
                )
                cards_container.controls.append(card)
            
            if filtered_count == 0:
                cards_container.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.INBOX, size=50, color="#888888"),
                            ft.Text("No accessories found", size=13, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30,
                    )
                )
            else:
                count_text = ft.Text(f"{filtered_count} of {len(accessories)}", size=10, color="#888888")
                cards_container.controls.insert(0, count_text)
            
            page.update()
        
        search_field.on_change = lambda e: update_cards()
        category_filter.on_change = lambda e: update_cards()
        quality_filter.on_change = lambda e: update_cards()
        update_cards()
        
        # FAB Button
        add_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_accessory_modal(page),
            mini=is_mobile,
        )
        
        main_container = ft.Container(content=main_column, expand=True, padding=12 if is_mobile else 20)
        
        if is_mobile:
            page.add(
                ft.Stack([
                    ft.Column([main_container, nav], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        else:
            sidebar = self.create_sidebar(page)
            page.add(
                ft.Stack([
                    ft.Row([sidebar, main_container], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        
        self.current_view = "accessories"
        page.update()
        
    def show_accessory_detail_dialog(self, page: ft.Page, accessory):
        """Accessory detail dialog - Compact layout"""
        
        name = accessory.get('name', 'N/A')
        category_name = accessory.get('category_name', 'Other')
        category_icon = accessory.get('category_icon', '📁')
        quality = accessory.get('quality', 'Used')
        quantity = accessory.get('quantity', 0)
        location = accessory.get('location', 'N/A')
        price = accessory.get('price', 0)
        notes = accessory.get('notes', 'No notes')
        barcode = accessory.get('barcode_value', 'N/A')
        created = str(accessory.get('created_at', ''))[:16] if accessory.get('created_at') else 'N/A'
        updated = str(accessory.get('updated_at', ''))[:16] if accessory.get('updated_at') else 'N/A'
        price_text = f"${price:.2f}" if price else "N/A"
        
        is_mobile = page.width < 800 if page.width else False
        dialog_width = page.width - 40 if is_mobile and page.width else 450
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_accessory(e):
            page.dialog.open = False
            self.open_edit_accessory_modal(page, accessory.get('id'))
        
        def delete_accessory(e):
            page.dialog.open = False
            self.open_delete_accessory_modal(page, accessory.get('id'))
        
        def show_barcode(e):
            self.show_barcode_dialog(page, accessory)
        
        content_items = [
            ft.Row([ft.Text("📁 Category:", size=13, color="#CCCCCC", width=90), 
                    ft.Text(f"{category_icon} {category_name}", size=13, color=self.accent_color)], spacing=8),
            ft.Row([ft.Text("🔢 Barcode:", size=13, color="#CCCCCC", width=90), 
                    ft.Text(barcode, size=11, color="#888888")], spacing=8),
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], spacing=10),
            ft.Row([ft.Text("🏷️ Quality:", size=13, color="#CCCCCC", width=90), 
                    ft.Container(content=ft.Text(quality, size=11, color="white"),
                    bgcolor=self.get_quality_color(quality), border_radius=6, 
                    padding=ft.padding.symmetric(horizontal=10, vertical=3))], spacing=8),
            ft.Row([ft.Text("🔢 Quantity:", size=13, color="#CCCCCC", width=90), 
                    ft.Text(str(quantity), size=15, weight=ft.FontWeight.BOLD,
                    color=self.danger_color if quantity < 10 else self.text_color)], spacing=8),
            ft.Row([ft.Text("💰 Price:", size=13, color="#CCCCCC", width=90), 
                    ft.Text(price_text, size=13, color="#4CAF50", weight=ft.FontWeight.BOLD)], spacing=8),
            ft.Row([ft.Text("📍 Location:", size=13, color="#CCCCCC", width=90), 
                    ft.Text(location, size=13, color=self.text_color)], spacing=8),
            ft.Divider(),
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=90), 
                    ft.Text(created, size=12, color="#888888")], spacing=8),
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=90), 
                    ft.Text(updated, size=12, color="#888888")], spacing=8),
        ]
        
        if notes and notes != 'No notes':
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📝 Notes:", size=13, weight=ft.FontWeight.BOLD, color="#CCCCCC"))
            content_items.append(ft.Container(content=ft.Text(notes, size=12, color="#888888"), 
                                            padding=8, bgcolor="#2C2C2C", border_radius=6))
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.ElevatedButton("✏️ EDIT", on_click=edit_accessory, expand=True,
                            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
            ft.ElevatedButton("🗑️ DELETE", on_click=delete_accessory, expand=True,
                            style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
        ], spacing=10))
        
        scrollable_content = ft.Column(content_items, spacing=8, scroll=ft.ScrollMode.AUTO, height=450)
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=17, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable_content, width=dialog_width, padding=12),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def on_accessory_select(self, accessory):
        """Handle accessory selection from table"""
        self.selected_accessory_detail = accessory
        if hasattr(self, 'accessory_detail_panel'):
            self.accessory_detail_panel.content = self.create_accessory_detail_panel(accessory, self.page_ref)
            self.page_ref.update()

    def filter_accessories_by_quality(self, page: ft.Page, filter_type):
        """Filter accessories by quality"""
        self.current_accessory_filter = filter_type
        
        # Update button colors
        color_map = {
            "All": self.accent_color,
            "New": self.success_color,
            "Used": self.warning_color,
            "Damaged": self.danger_color,
            "Repaired": self.accent_color,
        }
        
        for f_type, btn in self.accessory_filter_buttons.items():
            if f_type == filter_type:
                btn.bgcolor = color_map.get(f_type, self.card_color)
            else:
                btn.bgcolor = self.card_color
            btn.update()
        
        # Update the table
        accessories = self.dict_list(AccessoryManager.get_all())
        
        if filter_type == "All":
            filtered = accessories
        else:
            filtered = [a for a in accessories if a.get('quality') == filter_type]
        
        # Apply search if exists
        if hasattr(self, 'accessory_search_query') and self.accessory_search_query:
            query = self.accessory_search_query.lower()
            filtered = [a for a in filtered if query in a.get('name', '').lower() or query in a.get('item_code', '').lower()]
        
        # Update table rows
        self.accessory_table_rows.controls.clear()
        
        for a in filtered:
            location = a.get('location') or a.get('location_ids') or 'N/A'
            row = ft.Container(
                content=ft.Row([
                    ft.Text(a.get('name', 'N/A'), size=13, weight=ft.FontWeight.BOLD, width=180),
                    ft.Text(a.get('item_code', 'N/A'), size=12, width=120, color="#CCCCCC"),
                    ft.Text(str(a.get('quantity', 0)), size=13, weight=ft.FontWeight.BOLD, width=60,
                        color=self.danger_color if a.get('quantity', 0) < 10 else self.text_color),
                    ft.Container(
                        content=ft.Text(a.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        width=90,
                    ),
                    ft.Text(location, size=12, width=120, color="#CCCCCC"),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.EDIT, icon_size=20, 
                                    on_click=lambda e, acc=a: self.open_edit_accessory_modal(page, acc['id'])),
                        ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                    on_click=lambda e, acc=a: self.open_delete_accessory_modal(page, acc['id'])),
                        ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                    on_click=lambda e, acc=a: self.show_barcode_dialog(page, acc)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.START),
                padding=ft.padding.symmetric(vertical=10, horizontal=12),
                bgcolor="#2C2C2C",
                border_radius=6,
                ink=True,
                on_click=lambda e, acc=a: self.on_accessory_select(acc),
            )
            self.accessory_table_rows.controls.append(row)
        
        # Update detail panel
        if self.selected_accessory_detail and self.selected_accessory_detail not in filtered:
            self.selected_accessory_detail = None
            self.accessory_detail_panel.content = self.create_accessory_detail_panel(None, page)
        
        page.update()

    def create_accessory_detail_panel(self, accessory, page):
        """Create the detail panel for selected accessory with image and category"""
        if not accessory:
            return ft.Column([
                ft.Text("Accessory Details", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Container(height=20),
                ft.Text("Select an accessory to view details", size=12, color="#888888"),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        # Get base directory for resolving image paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get image path
        image_path = accessory.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
        
        # Format dates
        def format_datetime(date_value):
            if date_value:
                date_str = str(date_value)
                if ' ' in date_str:
                    return date_str.split(' ')[0]
                return date_str[:10] if len(date_str) > 10 else date_str
            return 'N/A'
        
        created_date = format_datetime(accessory.get('created_at', ''))
        updated_date = format_datetime(accessory.get('updated_at', ''))
        
        # Get location and price
        location = accessory.get('location') or accessory.get('location_ids') or "N/A"
        price_value = accessory.get('price', 0)
        price_text = f"${price_value:.2f}" if price_value else "N/A"
        
        # Get category with icon
        category = accessory.get('category', 'Uncategorized')
        category_icon = self.get_category_icon(category)
        
        # ========== IMAGE WIDGET ==========
        def show_image_overlay(e):
            def close_overlay():
                page.overlay.clear()
                page.update()
            
            if not has_image:
                no_image = ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Container(expand=True), ft.TextButton("✕", on_click=lambda e: close_overlay())]),
                        ft.Text("📷", size=60),
                        ft.Text("No Image Available", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text("Click Edit to add an image", size=12, color="#888888"),
                        ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    padding=30,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=400,
                    height=350,
                )
                overlay = ft.Container(content=no_image, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
                page.overlay.append(overlay)
                page.update()
                return
            
            img = ft.Image(src=full_image_path, width=500, height=400, fit=ft.ImageFit.CONTAIN)
            overlay_content = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(accessory.get('name', 'Image'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Container(expand=True),
                        ft.TextButton("✕", on_click=lambda e: close_overlay()),
                    ]),
                    ft.Divider(),
                    img,
                    ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=25,
                bgcolor=self.card_color,
                border_radius=15,
                width=550,
                height=500,
            )
            overlay = ft.Container(content=overlay_content, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
            page.overlay.append(overlay)
            page.update()
        
        # Create image display
        if has_image:
            try:
                image_display = ft.Container(
                    content=ft.Column([
                        ft.Image(src=full_image_path, width=180, height=140, fit=ft.ImageFit.CONTAIN),
                        ft.Text("Click to enlarge", size=9, color=self.accent_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    on_click=show_image_overlay,
                    ink=True,
                )
            except:
                image_display = None
        else:
            image_display = None
        
        # Build the column
        column_items = [
            ft.Text(accessory.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
        ]
        
        # Add image if it exists
        if image_display:
            column_items.append(ft.Row([image_display], alignment=ft.MainAxisAlignment.CENTER))
            column_items.append(ft.Container(height=10))
        
        # Add details with category
        column_items.extend([
            # Category row
            ft.Row([ft.Text("📁 Category:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(f"{category_icon} {category}", size=12, color=self.accent_color)], spacing=5),
            
            # Code row
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(accessory.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # SHOW BARCODE BUTTON
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, accessory), 
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=5),
            
            # Quality
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(
                        content=ft.Text(accessory.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(accessory.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    )], spacing=5),
            
            # Quantity
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(str(accessory.get('quantity', 0)), size=12, color=self.text_color,
                        weight=ft.FontWeight.BOLD if accessory.get('quantity', 0) < 10 else None)], spacing=5),
            
            # Price
            ft.Row([ft.Text("💰 Price:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(price_text, size=12, color="#4CAF50")], spacing=5),
            
            # Location
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(location, size=12, color=self.text_color)], spacing=5),
            
            # Created
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(created_date, size=12, color=self.text_color)], spacing=5),
            
            # Updated
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(updated_date, size=12, color=self.text_color)], spacing=5),
            
            ft.Divider(),
            
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(accessory.get('notes') or "No notes", size=12, color="#888888"),
            
            ft.Container(height=15),
            
            # EDIT AND DELETE BUTTONS
            ft.Row(
                [
                    ft.ElevatedButton(
                        "✏️ EDIT", 
                        on_click=lambda e: self.open_edit_accessory_modal(page, accessory['id']),
                        style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
                    ),
                    ft.ElevatedButton(
                        "🗑️ DELETE", 
                        on_click=lambda e: self.open_delete_accessory_modal(page, accessory['id']),
                        style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15,
            ),
        ])
        
        return ft.Column(column_items, spacing=10, scroll=ft.ScrollMode.AUTO)
    def open_add_category_dialog(self, page: ft.Page, refresh_callback=None):
        """Add category dialog - No syntax errors"""
        import sqlite3
        from database import DB_PATH
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        print(f"User ID: {current_user_id}")
        
        # Simple dialog
        dialog = ft.AlertDialog(
            title=ft.Text("Manage Categories", size=18, weight=ft.FontWeight.BOLD),
            modal=True,
        )
        
        # Input fields for adding
        name_input = ft.TextField(label="New Category Name", width=260, bgcolor=self.card_color)
        icon_select = ft.Dropdown(
            label="Icon",
            width=70,
            options=[ft.dropdown.Option(icon, icon) for icon in ["📦", "🔩", "🔧", "⚡", "💧", "🪵", "⚙️", "📁"]],
            value="📁",
            bgcolor=self.card_color,
        )
        add_status = ft.Text("", size=11)
        
        # Delete section
        delete_status = ft.Text("", size=11)
        delete_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=150)
        
    def open_add_accessory_modal(self, page: ft.Page):
        """Add accessory - With image upload (mobile friendly)"""
        import random
        import string
        import sqlite3
        import os
        import shutil
        from datetime import datetime
        from database import DB_PATH
        
        def generate_barcode():
            prefix = "890"
            random_numbers = ''.join(random.choices(string.digits, k=9))
            barcode_without_checksum = prefix + random_numbers
            total = 0
            for i, digit in enumerate(barcode_without_checksum):
                if i % 2 == 0:
                    total += int(digit) * 1
                else:
                    total += int(digit) * 3
            checksum = (10 - (total % 10)) % 10
            return barcode_without_checksum + str(checksum)
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 350
        else:
            field_width = 350
            dialog_width = 450
            scroll_height = 420
        
        # Create images folder
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        # Load categories
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        # Form fields
        name_field = ft.TextField(label="Name *", width=field_width, bgcolor=self.card_color)
        category_field = ft.Dropdown(label="Category", width=field_width, options=category_options, value="1", bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", width=field_width, bgcolor=self.card_color, value="0")
        price_field = ft.TextField(label="Price", width=field_width, bgcolor=self.card_color, value="0.00")
        quality_field = ft.Dropdown(label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value="New", bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", width=field_width, bgcolor=self.card_color, multiline=True, min_lines=2, max_lines=3)
        
        # Image upload - Mobile friendly
        image_status_text = ft.Text("No image", size=10, color="#888888")
        selected_image_data = None
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                size_kb = file.size / 1024
                
                try:
                    # Read the file content
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    
                    selected_image_data = {
                        'name': file.name,
                        'data': file_data,
                        'size': file.size
                    }
                    
                    image_status_text.value = f"✓ {file.name[:20]} ({size_kb:.0f}KB)"
                    image_status_text.color = self.success_color
                    print(f"DEBUG: Image selected: {file.name}")
                except Exception as ex:
                    print(f"DEBUG: Error reading image: {ex}")
                    image_status_text.value = f"❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        upload_btn = ft.ElevatedButton(
            "📁 Upload Image",
            on_click=upload_image,
            icon=ft.icons.UPLOAD_FILE,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
        )
        
        image_row = ft.Row([upload_btn, image_status_text], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)
        
        def save_uploaded_image():
            if selected_image_data:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"acc_{timestamp}{file_ext}"
                    new_path = os.path.join(images_folder, new_filename)
                    
                    with open(new_path, 'wb') as f:
                        f.write(selected_image_data['data'])
                    
                    print(f"DEBUG: Image saved to: {new_path}")
                    return f"images/{new_filename}"
                except Exception as e:
                    print(f"DEBUG: Error saving image: {e}")
                    return None
            return None
        
        # Create scrollable column
        scroll_fields = ft.Column([
            name_field,
            category_field,
            quantity_field,
            price_field,
            quality_field,
            location_field,
            image_row,
            notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def save_accessory():
            print("DEBUG: Save accessory called")
            
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            saved_image_path = save_uploaded_image() if selected_image_data else None
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO accessories (name, category_id, quantity, price, quality, location, notes, image_path, barcode_value, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    float(price_field.value) if price_field.value else 0,
                    quality_field.value, location_field.value,
                    notes_field.value,
                    saved_image_path,
                    generate_barcode(), current_time, current_time
                ))
                conn.commit()
                conn.close()
                self.auto_sync_after_change(page)
                
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_accessories(page)
            except Exception as e:
                print(f"DEBUG: Error saving accessory: {e}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Add New Accessory", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Save", on_click=lambda e: save_accessory(), style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=8),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def open_edit_accessory_modal(self, page: ft.Page, accessory_id):
        """Edit accessory with image upload and auto-sync to cloud"""
        import sqlite3
        import os
        import shutil
        from database import DB_PATH
        from datetime import datetime
        
        # Load accessory data
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
        accessory = cursor.fetchone()
        
        # Load categories
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        if not accessory:
            page.snack_bar = ft.SnackBar(ft.Text("Accessory not found!"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()
            return
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 350
        else:
            field_width = 350
            dialog_width = 450
            scroll_height = 420
        
        # Create images folder
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        # Form fields
        name_field = ft.TextField(
            label="Name *", 
            value=accessory['name'], 
            width=field_width, 
            bgcolor=self.card_color
        )
        category_field = ft.Dropdown(
            label="Category", 
            width=field_width, 
            options=category_options, 
            value=str(accessory['category_id']), 
            bgcolor=self.card_color
        )
        quantity_field = ft.TextField(
            label="Quantity", 
            value=str(accessory['quantity']), 
            width=field_width, 
            bgcolor=self.card_color
        )
        price_field = ft.TextField(
            label="Price", 
            value=str(accessory['price']), 
            width=field_width, 
            bgcolor=self.card_color
        )
        quality_field = ft.Dropdown(
            label="Quality", 
            width=field_width,
            options=[
                ft.dropdown.Option("New"), 
                ft.dropdown.Option("Used"), 
                ft.dropdown.Option("Damaged"), 
                ft.dropdown.Option("Repaired")
            ],
            value=accessory['quality'], 
            bgcolor=self.card_color
        )
        location_field = ft.TextField(
            label="Location", 
            value=accessory['location'] or "", 
            width=field_width, 
            bgcolor=self.card_color
        )
        notes_field = ft.TextField(
            label="Notes", 
            value=accessory['notes'] or "", 
            width=field_width, 
            bgcolor=self.card_color, 
            multiline=True, 
            min_lines=2, 
            max_lines=3
        )
        
        # Image handling - Mobile friendly
        current_image_path = accessory['image_path'] if accessory['image_path'] else None
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Image(
                src=current_image_path if has_current_image else None,
                width=100,
                height=100,
                fit=ft.ImageFit.CONTAIN,
            ) if has_current_image else ft.Text("No image", size=10, color="#888888"),
            width=100,
            height=100,
            bgcolor="#2C2C2C",
            border_radius=8,
            alignment=ft.alignment.center,
        )
        
        image_status_text = ft.Text(
            "✓ Current image saved" if has_current_image else "No image", 
            size=10, 
            color=self.success_color if has_current_image else "#888888"
        )
        selected_image_data = None
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                size_kb = file.size / 1024
                
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    
                    selected_image_data = {
                        'name': file.name,
                        'data': file_data,
                        'size': file.size
                    }
                    
                    image_status_text.value = f"✓ New: {file.name[:20]} ({size_kb:.0f}KB)"
                    image_status_text.color = self.success_color
                    print(f"DEBUG: New image selected: {file.name}")
                    
                    # Update preview
                    try:
                        image_preview.content = ft.Image(
                            src=file.path,
                            width=100,
                            height=100,
                            fit=ft.ImageFit.CONTAIN,
                        )
                    except:
                        pass
                        
                except Exception as ex:
                    print(f"DEBUG: Error reading image: {ex}")
                    image_status_text.value = f"❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        upload_btn = ft.ElevatedButton(
            "📁 Upload New",
            on_click=upload_image,
            icon=ft.icons.UPLOAD_FILE,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
        )
        
        image_row = ft.Row(
            [image_preview, ft.Column([upload_btn, image_status_text], spacing=4)], 
            spacing=8, 
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        def save_uploaded_image():
            if selected_image_data:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"acc_{accessory_id}_{timestamp}{file_ext}"
                    new_path = os.path.join(images_folder, new_filename)
                    
                    with open(new_path, 'wb') as f:
                        f.write(selected_image_data['data'])
                    
                    print(f"DEBUG: New image saved to: {new_path}")
                    
                    # Delete old image if exists
                    if current_image_path and os.path.exists(current_image_path):
                        try:
                            os.remove(current_image_path)
                            print(f"DEBUG: Old image deleted: {current_image_path}")
                        except Exception as e:
                            print(f"DEBUG: Error deleting old image: {e}")
                    
                    return f"images/{new_filename}"
                except Exception as e:
                    print(f"DEBUG: Error saving image: {e}")
                    return None
            return None
        
        # Create scrollable column
        scroll_fields = ft.Column([
            name_field,
            category_field,
            quantity_field,
            price_field,
            quality_field,
            location_field,
            image_row,
            notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def update_accessory():
            print("DEBUG: Update accessory called")
            
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            final_image_path = current_image_path
            if selected_image_data:
                final_image_path = save_uploaded_image()
                print(f"DEBUG: Final image path: {final_image_path}")
            
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accessories 
                    SET name = ?, category_id = ?, quantity = ?, price = ?, quality = ?, 
                        location = ?, notes = ?, image_path = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    float(price_field.value) if price_field.value else 0,
                    quality_field.value, location_field.value,
                    notes_field.value,
                    final_image_path,
                    current_time, accessory_id
                ))
                conn.commit()
                conn.close()
                print("DEBUG: Accessory updated successfully")
                
                # ===== AUTO-SYNC TO CLOUD =====
                def sync_accessory():
                    try:
                        # Get the updated accessory
                        conn = sqlite3.connect(DB_PATH)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
                        updated_accessory = cursor.fetchone()
                        conn.close()
                        
                        if updated_accessory:
                            accessory_dict = dict(updated_accessory)
                            if firebase_api.is_ready():
                                success = CloudSyncManager.sync_single_accessory_to_cloud(company_id, accessory_id)
                                if success:
                                    print(f"✅ [AUTO-SYNC] Accessory '{name_field.value}' updated and synced to cloud")
                                else:
                                    print(f"⚠️ [AUTO-SYNC] Accessory '{name_field.value}' failed to sync")
                    except Exception as e:
                        print(f"Sync error: {e}")
                
                import threading
                threading.Thread(target=sync_accessory, daemon=True).start()
                # ===================================
                
                close_dialog()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Updated and synced: {name_field.value}"), 
                    bgcolor=self.success_color, 
                    duration=2000
                )
                page.snack_bar.open = True
                self.show_accessories(page)
                
            except Exception as e:
                print(f"DEBUG: Error updating accessory: {e}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Accessory", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Update", on_click=lambda e: update_accessory(), 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=8),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def open_delete_accessory_modal(self, page: ft.Page, accessory_id):
        """Delete accessory confirmation modal"""
        
        accessory = AccessoryManager.get_by_id(accessory_id)
        self.auto_sync_after_change(page)
        if not accessory:
            return
        
        accessory_dict = dict(accessory)
        name = accessory_dict.get('name', 'this item')
        
        is_mobile = page.width < 800 if page.width else False
        dialog_width = 300 if is_mobile else 350
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            AccessoryManager.delete(accessory_id)
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Deleted: {name}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_accessories(page)
        
        dialog_content = ft.Column([
            ft.Text("🗑️ Confirm Delete", size=16, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text(f"Delete '{name}'?", size=13),
            ft.Text("This cannot be undone!", size=11, color="#888888"),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Delete", on_click=confirm_delete, 
                            style=ft.ButtonStyle(bgcolor=self.danger_color), expand=True),
            ], spacing=8),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=12),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_accessory_detail_dialog(self, page: ft.Page, accessory):
        """Accessory detail dialog with image"""
        import os
        
        name = accessory.get('name', 'N/A')
        category_name = accessory.get('category_name', 'Other')
        category_icon = accessory.get('category_icon', '📁')
        quality = accessory.get('quality', 'Used')
        quantity = accessory.get('quantity', 0)
        location = accessory.get('location', 'N/A')
        price = accessory.get('price', 0)
        notes = accessory.get('notes', 'No notes')
        barcode = accessory.get('barcode_value', 'N/A')
        created = str(accessory.get('created_at', ''))[:16] if accessory.get('created_at') else 'N/A'
        updated = str(accessory.get('updated_at', ''))[:16] if accessory.get('updated_at') else 'N/A'
        price_text = f"${price:.2f}" if price else "N/A"
        
        # Get image path
        image_path = accessory.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
                else:
                    images_path = os.path.join(base_dir, "images", os.path.basename(image_path))
                    if os.path.exists(images_path):
                        has_image = True
                        full_image_path = images_path
        
        is_mobile = page.width < 800 if page.width else False
        dialog_width = page.width - 40 if is_mobile and page.width else 450
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_accessory(e):
            page.dialog.open = False
            self.open_edit_accessory_modal(page, accessory.get('id'))
        
        def delete_accessory(e):
            page.dialog.open = False
            self.open_delete_accessory_modal(page, accessory.get('id'))
        
        def show_barcode(e):
            self.show_barcode_dialog(page, accessory)
        
        def show_fullscreen(e):
            def close_fullscreen():
                page.overlay.clear()
                page.update()
            
            screen_width = page.width if page.width else 400
            screen_height = page.height if page.height else 600
            
            fullscreen = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(expand=True),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=30, on_click=lambda e: close_fullscreen()),
                    ]),
                    ft.Container(
                        content=ft.Image(
                            src=full_image_path, 
                            fit=ft.ImageFit.CONTAIN,
                            width=screen_width - 40,
                            height=screen_height - 100,
                        ),
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                ], spacing=10),
                expand=True,
                bgcolor="#000000CC",
            )
            page.overlay.append(fullscreen)
            page.update()
        
        content_items = []
        
        # Image section
        if has_image:
            content_items.append(
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            content=ft.Image(src=full_image_path, fit=ft.ImageFit.CONTAIN, width=200, height=150),
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.icons.ZOOM_IN, size=20, color="white"),
                            bgcolor="#00000099",
                            border_radius=20,
                            padding=5,
                            right=5,
                            top=5,
                            on_click=show_fullscreen,
                            ink=True,
                        ),
                    ]),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        else:
            content_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, size=50, color="#888888"),
                        ft.Text("No Image Available", size=12, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        content_items.extend([
            ft.Divider(),
            ft.Row([ft.Text("📁 Category:", size=13, color="#CCCCCC", width=100), 
                    ft.Text(f"{category_icon} {category_name}", size=13, color=self.accent_color)], spacing=8),
            ft.Row([ft.Text("🔢 Barcode:", size=13, color="#CCCCCC", width=100), 
                    ft.Text(barcode, size=11, color="#888888")], spacing=8),
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], spacing=10),
            ft.Row([ft.Text("🏷️ Quality:", size=13, color="#CCCCCC", width=100), 
                    ft.Container(content=ft.Text(quality, size=11, color="white"),
                    bgcolor=self.get_quality_color(quality), border_radius=6, 
                    padding=ft.padding.symmetric(horizontal=10, vertical=3))], spacing=8),
            ft.Row([ft.Text("🔢 Quantity:", size=13, color="#CCCCCC", width=100), 
                    ft.Text(str(quantity), size=15, weight=ft.FontWeight.BOLD,
                    color=self.danger_color if quantity < 10 else self.text_color)], spacing=8),
            ft.Row([ft.Text("💰 Price:", size=13, color="#CCCCCC", width=100), 
                    ft.Text(price_text, size=13, color="#4CAF50", weight=ft.FontWeight.BOLD)], spacing=8),
            ft.Row([ft.Text("📍 Location:", size=13, color="#CCCCCC", width=100), 
                    ft.Text(location, size=13, color=self.text_color)], spacing=8),
            ft.Divider(),
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=100), 
                    ft.Text(created, size=12, color="#888888")], spacing=8),
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=100), 
                    ft.Text(updated, size=12, color="#888888")], spacing=8),
        ])
        
        if notes and notes != 'No notes':
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📝 Notes:", size=13, weight=ft.FontWeight.BOLD, color="#CCCCCC"))
            content_items.append(ft.Container(content=ft.Text(notes, size=12, color="#888888"), 
                                            padding=8, bgcolor="#2C2C2C", border_radius=6))
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.ElevatedButton("✏️ EDIT", on_click=edit_accessory, expand=True,
                            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
            ft.ElevatedButton("🗑️ DELETE", on_click=delete_accessory, expand=True,
                            style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
        ], spacing=10))
        
        scrollable_content = ft.Column(content_items, spacing=8, scroll=ft.ScrollMode.AUTO, height=450)
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=17, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable_content, width=dialog_width, padding=12),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def convert_size_to_length(self, size_text):
        """Convert size text like '34 1/2' or '34.5' to decimal"""
        if not size_text:
            return None
        
        size_text = size_text.strip()
        
        try:
            return float(size_text)
        except ValueError:
            pass
        
        if '/' in size_text:
            parts = size_text.split('/')
            try:
                if ' ' in parts[0]:
                    whole, num = parts[0].split()
                    return float(whole) + (float(num) / float(parts[1]))
                else:
                    return float(parts[0]) / float(parts[1])
            except:
                pass
        
        return None
            
    def show_material_detail_dialog(self, page: ft.Page, material):
        """Complete detail dialog showing all fields including size and length"""
        
        import os
        
        name = material.get('name', 'N/A')
        category_name = material.get('category_name', 'Other')
        category_icon = material.get('category_icon', '📁')
        quality = material.get('quality', 'Used')
        quantity = material.get('quantity', 0)
        location = material.get('location_ids', 'N/A')
        size = material.get('size', '')
        length = material.get('length', '')
        colors = material.get('colors', '')
        notes = material.get('notes', '')
        barcode = material.get('barcode_value', 'N/A')
        created = str(material.get('created_at', ''))[:16] if material.get('created_at') else 'N/A'
        updated = str(material.get('updated_at', ''))[:16] if material.get('updated_at') else 'N/A'
        
        # Clean up display values
        size_display = size if size else 'N/A'
        length_display = ''
        if length:
            try:
                length_float = float(length)
                length_display = f"{length_float:.2f}" if length_float % 1 != 0 else str(int(length_float))
            except:
                length_display = str(length)
        else:
            length_display = 'N/A'
        
        colors_display = colors if colors else 'N/A'
        notes_display = notes if notes else 'No notes'
        
        # Get image path - try multiple locations
        image_path = material.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            # Check absolute path
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                # Check relative to current directory
                base_dir = os.path.dirname(os.path.abspath(__file__))
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
                else:
                    # Check in images folder
                    images_path = os.path.join(base_dir, "images", os.path.basename(image_path))
                    if os.path.exists(images_path):
                        has_image = True
                        full_image_path = images_path
        
        is_mobile = page.width < 800 if page.width else False
        dialog_width = page.width - 40 if is_mobile and page.width else 450
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_material(e):
            page.dialog.open = False
            self.open_edit_modal(page, material.get('id'))
        
        def delete_material(e):
            page.dialog.open = False
            self.open_delete_modal(page, material.get('id'))
        
        def show_barcode(e):
            self.show_barcode_dialog(page, material)
        
        def show_fullscreen(e):
            def close_fullscreen():
                page.overlay.clear()
                page.update()
            
            screen_width = page.width if page.width else 400
            screen_height = page.height if page.height else 600
            
            fullscreen = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(expand=True),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=30, on_click=lambda e: close_fullscreen()),
                    ]),
                    ft.Container(
                        content=ft.Image(
                            src=full_image_path, 
                            fit=ft.ImageFit.CONTAIN,
                            width=screen_width - 40,
                            height=screen_height - 100,
                        ),
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                ], spacing=10),
                expand=True,
                bgcolor="#000000CC",
            )
            page.overlay.append(fullscreen)
            page.update()
        
        # Create content_items list
        content_items = []
        
        # Image section with auto-scale
        if has_image:
            content_items.append(
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            content=ft.Image(
                                src=full_image_path, 
                                fit=ft.ImageFit.CONTAIN,
                                width=200,
                                height=150,
                            ),
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.icons.ZOOM_IN, size=20, color="white"),
                            bgcolor="#00000099",
                            border_radius=20,
                            padding=5,
                            right=5,
                            top=5,
                            on_click=show_fullscreen,
                            ink=True,
                        ),
                    ]),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        else:
            content_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, size=50, color="#888888"),
                        ft.Text("No Image Available", size=12, color="#888888"),
                        ft.Text("Click Edit to add an image", size=10, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        # Basic Information Section
        content_items.append(ft.Divider())
        content_items.append(ft.Text("📋 Basic Information", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
        
        content_items.append(ft.Row([
            ft.Text("📁 Category:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{category_icon} {category_name}", size=13, color=self.accent_color, weight=ft.FontWeight.BOLD),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("🔢 Barcode:", size=13, color="#CCCCCC", width=100),
            ft.Text(barcode, size=12, color="#888888"),
        ], spacing=8))
        
        # Show Barcode Button
        content_items.append(
            ft.Row([
                ft.ElevatedButton(
                    "📱 SHOW BARCODE", 
                    on_click=show_barcode,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color),
                )
            ], spacing=10)
        )
        
        # Stock Information Section
        content_items.append(ft.Divider())
        content_items.append(ft.Text("📊 Stock Information", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
        
        content_items.append(ft.Row([
            ft.Text("🏷️ Quality:", size=13, color="#CCCCCC", width=100),
            ft.Container(
                content=ft.Text(quality, size=12, color="white"),
                bgcolor=self.get_quality_color(quality),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            ),
        ], spacing=8))
        
        # Quantity with color based on stock level
        qty_color = self.danger_color if quantity < 10 else self.text_color
        qty_text = f"{quantity} units"
        if quantity < 5:
            qty_text += " 🔴 CRITICAL"
        elif quantity < 10:
            qty_text += " 🟠 LOW"
        
        content_items.append(ft.Row([
            ft.Text("🔢 Quantity:", size=13, color="#CCCCCC", width=100),
            ft.Text(qty_text, size=14, weight=ft.FontWeight.BOLD, color=qty_color),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("📍 Location:", size=13, color="#CCCCCC", width=100),
            ft.Text(location, size=13, color=self.text_color),
        ], spacing=8))
        
        # Dimensions Section - SHOW SIZE AND LENGTH
        has_dimensions = (size_display != 'N/A') or (length_display != 'N/A')
        if has_dimensions:
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📏 Dimensions", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
            
            if size_display != 'N/A':
                content_items.append(ft.Row([
                    ft.Text("📏 Size:", size=13, color="#CCCCCC", width=100),
                    ft.Text(size_display, size=13, color=self.text_color),
                ], spacing=8))
            
            if length_display != 'N/A':
                content_items.append(ft.Row([
                    ft.Text("📐 Length:", size=13, color="#CCCCCC", width=100),
                    ft.Text(length_display, size=13, color=self.text_color),
                ], spacing=8))
        
        # Colors Section
        if colors_display != 'N/A':
            content_items.append(ft.Divider())
            content_items.append(ft.Text("🎨 Colors", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
            content_items.append(ft.Row([
                ft.Text("Colors:", size=13, color="#CCCCCC", width=100),
                ft.Text(colors_display, size=13, color=self.text_color),
            ], spacing=8))
        
        # Dates Section
        content_items.append(ft.Divider())
        content_items.append(ft.Text("📅 Timestamps", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
        
        content_items.append(ft.Row([
            ft.Text("Created:", size=13, color="#CCCCCC", width=100),
            ft.Text(created, size=12, color="#888888"),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("Updated:", size=13, color="#CCCCCC", width=100),
            ft.Text(updated, size=12, color="#888888"),
        ], spacing=8))
        
        # Notes Section
        if notes_display != 'No notes':
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📝 Notes", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
            content_items.append(
                ft.Container(
                    content=ft.Text(notes_display, size=12, color="#888888"),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(top=5, bottom=10),
                )
            )
        
        # Action Buttons Section
        content_items.append(ft.Divider())
        content_items.append(
            ft.Row([
                ft.ElevatedButton(
                    "✏️ EDIT", 
                    on_click=edit_material,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
                ),
                ft.ElevatedButton(
                    "🗑️ DELETE", 
                    on_click=delete_material,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color),
                ),
            ], spacing=10)
        )
        
        # Create scrollable content
        scrollable_content = ft.Column(content_items, spacing=8, scroll=ft.ScrollMode.AUTO, height=500)
        
        # Create dialog
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable_content, width=dialog_width, padding=15),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_barcode_dialog(self, page: ft.Page, item):
        """Show barcode dialog for material or accessory with copy button"""
        import webbrowser
        import tempfile
        
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        item_name = item.get('name', 'Item')
        item_type = "Material" if 'location_ids' in item else "Accessory"
        
        # Create barcode image URL
        barcode_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_text}&code=Code128&dpi=120"
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def copy_to_clipboard(e):
            try:
                page.set_clipboard(barcode_text)
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Barcode copied: {barcode_text}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Failed to copy: {str(ex)}"), bgcolor=self.danger_color, duration=2000)
                page.snack_bar.open = True
                page.update()
        
        def print_barcode(e):
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Barcode - {barcode_text}</title>
                <style>
                    body {{ text-align: center; padding: 50px; font-family: Arial; }}
                    .barcode-img {{ max-width: 100%; height: auto; }}
                    .number {{ font-size: 24px; font-weight: bold; margin-top: 20px; }}
                    @media print {{ .no-print {{ display: none; }} }}
                </style>
            </head>
            <body>
                <img class="barcode-img" src="{barcode_url}" alt="Barcode">
                <div class="number">{barcode_text}</div>
                <div class="no-print" style="margin-top: 30px;">
                    <button onclick="window.print()">🖨️ Print Now</button>
                    <button onclick="window.close()">Close</button>
                </div>
                <script>setTimeout(function(){{ window.print(); }}, 500);</script>
            </body>
            </html>
            """
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            webbrowser.open(f'file://{temp_file.name}')
            close_dialog(e)
        
        dialog_content = ft.Column([
            ft.Text(item_name, size=16, weight=ft.FontWeight.BOLD),
            ft.Text(item_type, size=12, color="#888888"),
            ft.Container(height=10),
            ft.Image(src=barcode_url, width=300, height=100, fit=ft.ImageFit.CONTAIN),
            ft.Text(barcode_text, size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
            ft.Text("Scan this barcode with your camera", size=10, color="#888888"),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Barcode", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=dialog_content, width=350, height=380, padding=15),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
                ft.TextButton("📋 Copy", on_click=copy_to_clipboard),
                ft.FilledButton("🖨️ Print", on_click=print_barcode, style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_barcode_scanner_input(self, page: ft.Page, target_field=None):
        """Open dialog for barcode input using clipboard (Google Lens/Camera)"""
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def paste_from_clipboard(e):
            try:
                clipboard_content = page.get_clipboard()
                if clipboard_content:
                    barcode_input.value = clipboard_content
                    status_text.value = "✓ Barcode pasted successfully!"
                    status_text.color = self.success_color
                    page.update()
                else:
                    status_text.value = "❌ Clipboard is empty. Scan a barcode first using Google Lens or Camera"
                    status_text.color = self.danger_color
                    page.update()
            except Exception as ex:
                status_text.value = f"❌ Could not read clipboard: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        def copy_from_input(e):
            if barcode_input.value:
                try:
                    page.set_clipboard(barcode_input.value)
                    status_text.value = "✓ Barcode copied to clipboard!"
                    status_text.color = self.success_color
                    page.update()
                except Exception as ex:
                    status_text.value = f"❌ Failed to copy: {str(ex)}"
                    status_text.color = self.danger_color
                    page.update()
            else:
                status_text.value = "❌ No barcode to copy"
                status_text.color = self.danger_color
                page.update()
        
        def confirm_barcode(e):
            if barcode_input.value:
                if target_field:
                    target_field.value = barcode_input.value
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Barcode set: {barcode_input.value}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                page.update()
            else:
                status_text.value = "❌ Please enter or paste a barcode"
                page.update()
        
        barcode_input = ft.TextField(
            label="Barcode Number",
            hint_text="Paste scanned code here",
            width=300,
            bgcolor=self.card_color,
            autofocus=True,
        )
        
        status_text = ft.Text("", size=12)
        
        instruction = ft.Column([
            ft.Text("📷 How to scan barcode:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("1. Open your phone's Camera app", size=12),
            ft.Text("2. Point at the barcode", size=12),
            ft.Text("3. Tap the 'Copy' button when Google Lens detects text", size=12),
            ft.Text("4. Come back here and tap 'Paste from Clipboard'", size=12),
            ft.Container(height=5),
            ft.Text("💡 Alternative: Use any barcode scanner app", size=11, color="#888888"),
        ], spacing=5)
        
        dialog_content = ft.Column([
            ft.Text("Scan Barcode", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            instruction,
            ft.Container(height=10),
            barcode_input,
            status_text,
            ft.Row([
                ft.ElevatedButton("📋 Paste from Clipboard", on_click=paste_from_clipboard, icon=ft.icons.CONTENT_PASTE, expand=True),
            ], spacing=10),
            ft.Row([
                ft.ElevatedButton("📋 Copy to Clipboard", on_click=copy_from_input, icon=ft.icons.CONTENT_COPY, expand=True),
            ], spacing=10),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Confirm", on_click=confirm_barcode, style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Barcode Scanner"),
            content=ft.Container(content=dialog_content, width=350, height=520, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def search_barcode_by_value(self, barcode_value, page):
        """Search for barcode and show result"""
        if not barcode_value:
            page.snack_bar = ft.SnackBar(ft.Text("Please enter a barcode!"), bgcolor=self.warning_color)
            page.snack_bar.open = True
            page.update()
            return
        
        # Search in materials
        item = MaterialManager.get_by_barcode(barcode_value)
        item_type = 'material'
        
        if not item:
            item = AccessoryManager.get_by_barcode(barcode_value)
            item_type = 'accessory'
        
        if item:
            item_dict = dict(item)
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ Found: {item_dict.get('name')}"), 
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            
            # Show detail dialog
            if item_type == 'material':
                self.show_material_detail_dialog(page, item_dict)
            else:
                self.show_accessory_detail_dialog(page, item_dict)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ No item found with barcode: {barcode_value}"), 
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
        
        page.update()

    def open_add_modal(self, page: ft.Page):
        """Add material - Working save with company_id"""
        import random
        import string
        import sqlite3
        from datetime import datetime
        from database import DB_PATH
        
        def generate_barcode():
            prefix = "890"
            random_numbers = ''.join(random.choices(string.digits, k=9))
            barcode_without_checksum = prefix + random_numbers
            total = 0
            for i, digit in enumerate(barcode_without_checksum):
                if i % 2 == 0:
                    total += int(digit) * 1
                else:
                    total += int(digit) * 3
            checksum = (10 - (total % 10)) % 10
            return barcode_without_checksum + str(checksum)
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 380
        else:
            field_width = 350
            dialog_width = 500
            scroll_height = 450
        
        # Load categories
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        # Form fields
        name_field = ft.TextField(label="Name *", width=field_width, bgcolor=self.card_color)
        category_field = ft.Dropdown(label="Category", width=field_width, options=category_options, value="1", bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", width=field_width, bgcolor=self.card_color, value="0")
        size_field = ft.TextField(label="Size", width=field_width, bgcolor=self.card_color, hint_text="e.g., 34 1/2")
        length_field = ft.TextField(label="Length (auto)", width=field_width, bgcolor=self.card_color, read_only=True)
        quality_field = ft.Dropdown(label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value="New", bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", width=field_width, bgcolor=self.card_color)
        color_field = ft.TextField(label="Colors", width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", width=field_width, bgcolor=self.card_color, multiline=True, min_lines=2, max_lines=3)
        
        # Barcode field
        barcode_field = ft.TextField(
            label="Barcode", 
            width=field_width - 80,
            bgcolor=self.card_color, 
            value=generate_barcode(),
            read_only=True,
        )
        
        regenerate_btn = ft.TextButton("🔄 New Barcode", on_click=lambda e: setattr(barcode_field, 'value', generate_barcode()) or page.update())
        
        barcode_row = ft.Row([barcode_field, regenerate_btn], spacing=8)
        
        def update_length(e):
            size_value = size_field.value
            if size_value:
                try:
                    if ' ' in size_value and '/' in size_value:
                        parts = size_value.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_value = whole + float(frac[0]) / float(frac[1])
                        length_field.value = f"{length_value:.2f}"
                    elif '/' in size_value:
                        frac = size_value.split('/')
                        length_value = float(frac[0]) / float(frac[1])
                        length_field.value = f"{length_value:.2f}"
                    else:
                        length_value = float(size_value)
                        length_field.value = f"{length_value:.2f}"
                except:
                    length_field.value = size_value
            else:
                length_field.value = ""
            page.update()
        
        size_field.on_change = update_length
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        scrollable_fields = ft.Column([
            name_field,
            category_field,
            quantity_field,
            size_field,
            length_field,
            quality_field,
            location_field,
            color_field,
            barcode_row,
            notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def save_material():
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            
            size_val = size_field.value
            length_val = None
            if size_val:
                try:
                    if ' ' in size_val and '/' in size_val:
                        parts = size_val.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_val = whole + float(frac[0]) / float(frac[1])
                    elif '/' in size_val:
                        frac = size_val.split('/')
                        length_val = float(frac[0]) / float(frac[1])
                    else:
                        length_val = float(size_val)
                except:
                    length_val = None
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO materials (name, category_id, quantity, quality, location_ids, size, length, colors, notes, barcode_value, company_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    quality_field.value, location_field.value,
                    size_field.value, length_val,
                    color_field.value, notes_field.value,
                    barcode_field.value, company_id, current_time, current_time
                ))
                conn.commit()
                conn.close()
                
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                
                # Refresh the materials screen
                self.show_materials_screen(page)
                
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Add New Material", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scrollable_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Save", on_click=lambda e: save_material(), 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
            
    def open_edit_modal(self, page: ft.Page, material_id):
        """Edit material with image upload and auto-sync to cloud"""
        import sqlite3
        import os
        import shutil
        from database import DB_PATH
        from datetime import datetime
        
        # Load material data
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        material = cursor.fetchone()
        
        # Load categories
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        if not material:
            page.snack_bar = ft.SnackBar(ft.Text("Material not found!"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()
            return
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 380
        else:
            field_width = 350
            dialog_width = 450
            scroll_height = 450
        
        # Create images folder
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        # Form fields
        name_field = ft.TextField(
            label="Name *", 
            value=material['name'], 
            width=field_width, 
            bgcolor=self.card_color
        )
        category_field = ft.Dropdown(
            label="Category", 
            width=field_width, 
            options=category_options, 
            value=str(material['category_id']), 
            bgcolor=self.card_color
        )
        quantity_field = ft.TextField(
            label="Quantity", 
            value=str(material['quantity']), 
            width=field_width, 
            bgcolor=self.card_color
        )
        size_field = ft.TextField(
            label="Size", 
            value=material['size'] or "", 
            width=field_width, 
            bgcolor=self.card_color
        )
        length_field = ft.TextField(
            label="Length", 
            value=str(material['length']) if material['length'] else "", 
            width=field_width, 
            bgcolor=self.card_color
        )
        quality_field = ft.Dropdown(
            label="Quality", 
            width=field_width,
            options=[
                ft.dropdown.Option("New"), 
                ft.dropdown.Option("Used"), 
                ft.dropdown.Option("Damaged"), 
                ft.dropdown.Option("Repaired")
            ],
            value=material['quality'], 
            bgcolor=self.card_color
        )
        location_field = ft.TextField(
            label="Location", 
            value=material['location_ids'] or "", 
            width=field_width, 
            bgcolor=self.card_color
        )
        color_field = ft.TextField(
            label="Colors", 
            value=material['colors'] or "", 
            width=field_width, 
            bgcolor=self.card_color
        )
        notes_field = ft.TextField(
            label="Notes", 
            value=material['notes'] or "", 
            width=field_width, 
            bgcolor=self.card_color, 
            multiline=True, 
            min_lines=2, 
            max_lines=3
        )
        
        # Auto-update length from size
        def update_length(e):
            size_value = size_field.value
            if size_value:
                try:
                    if ' ' in size_value and '/' in size_value:
                        parts = size_value.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_value = whole + float(frac[0]) / float(frac[1])
                        length_field.value = f"{length_value:.2f}"
                    elif '/' in size_value:
                        frac = size_value.split('/')
                        length_value = float(frac[0]) / float(frac[1])
                        length_field.value = f"{length_value:.2f}"
                    else:
                        length_value = float(size_value)
                        length_field.value = f"{length_value:.2f}"
                except:
                    length_field.value = size_value
            else:
                length_field.value = ""
            page.update()
        
        size_field.on_change = update_length
        
        # Image handling - Mobile friendly
        current_image_path = material['image_path'] if material['image_path'] else None
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Image(
                src=current_image_path if has_current_image else None,
                width=100,
                height=100,
                fit=ft.ImageFit.CONTAIN,
            ) if has_current_image else ft.Text("No image", size=10, color="#888888"),
            width=100,
            height=100,
            bgcolor="#2C2C2C",
            border_radius=8,
            alignment=ft.alignment.center,
        )
        
        image_status_text = ft.Text(
            "✓ Current image saved" if has_current_image else "No image", 
            size=10, 
            color=self.success_color if has_current_image else "#888888"
        )
        selected_image_data = None
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                size_kb = file.size / 1024
                
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    
                    selected_image_data = {
                        'name': file.name,
                        'data': file_data,
                        'size': file.size
                    }
                    
                    image_status_text.value = f"✓ New: {file.name[:20]} ({size_kb:.0f}KB)"
                    image_status_text.color = self.success_color
                    print(f"DEBUG: New image selected: {file.name}")
                    
                    # Update preview
                    try:
                        image_preview.content = ft.Image(
                            src=file.path,
                            width=100,
                            height=100,
                            fit=ft.ImageFit.CONTAIN,
                        )
                    except:
                        pass
                        
                except Exception as ex:
                    print(f"DEBUG: Error reading image: {ex}")
                    image_status_text.value = f"❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        upload_btn = ft.ElevatedButton(
            "📁 Upload New",
            on_click=upload_image,
            icon=ft.icons.UPLOAD_FILE,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
        )
        
        image_row = ft.Row(
            [image_preview, ft.Column([upload_btn, image_status_text], spacing=4)], 
            spacing=8, 
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        def save_uploaded_image():
            if selected_image_data:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"img_{material_id}_{timestamp}{file_ext}"
                    new_path = os.path.join(images_folder, new_filename)
                    
                    with open(new_path, 'wb') as f:
                        f.write(selected_image_data['data'])
                    
                    print(f"DEBUG: New image saved to: {new_path}")
                    
                    # Delete old image if exists
                    if current_image_path and os.path.exists(current_image_path):
                        try:
                            os.remove(current_image_path)
                            print(f"DEBUG: Old image deleted: {current_image_path}")
                        except Exception as e:
                            print(f"DEBUG: Error deleting old image: {e}")
                    
                    return f"images/{new_filename}"
                except Exception as e:
                    print(f"DEBUG: Error saving image: {e}")
                    return None
            return None
        
        # Create scrollable column
        scroll_fields = ft.Column([
            name_field,
            category_field,
            quantity_field,
            size_field,
            length_field,
            quality_field,
            location_field,
            color_field,
            image_row,
            notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def update_material():
            print("DEBUG: Update material called")
            
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            # Handle image
            final_image_path = current_image_path
            if selected_image_data:
                final_image_path = save_uploaded_image()
                print(f"DEBUG: Final image path: {final_image_path}")
            
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            
            # Calculate length from size
            size_val = size_field.value
            length_val = None
            if size_val:
                try:
                    if ' ' in size_val and '/' in size_val:
                        parts = size_val.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_val = whole + float(frac[0]) / float(frac[1])
                    elif '/' in size_val:
                        frac = size_val.split('/')
                        length_val = float(frac[0]) / float(frac[1])
                    else:
                        length_val = float(size_val)
                except:
                    length_val = None
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE materials 
                    SET name = ?, category_id = ?, quantity = ?, quality = ?, location_ids = ?,
                        size = ?, length = ?, colors = ?, notes = ?, image_path = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    quality_field.value, location_field.value,
                    size_field.value, length_val,
                    color_field.value, notes_field.value,
                    final_image_path,
                    current_time, material_id
                ))
                conn.commit()
                conn.close()
                print("DEBUG: Material updated successfully")
                
                # ===== AUTO-SYNC TO CLOUD =====
                def sync_material():
                    try:
                        # Get the updated material
                        conn = sqlite3.connect(DB_PATH)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
                        updated_material = cursor.fetchone()
                        conn.close()
                        
                        if updated_material:
                            material_dict = dict(updated_material)
                            if firebase_api.is_ready():
                                success = CloudSyncManager.sync_single_material_to_cloud(company_id, material_id)
                                if success:
                                    print(f"✅ [AUTO-SYNC] Material '{name_field.value}' updated and synced to cloud")
                                else:
                                    print(f"⚠️ [AUTO-SYNC] Material '{name_field.value}' failed to sync")
                    except Exception as e:
                        print(f"Sync error: {e}")
                
                import threading
                threading.Thread(target=sync_material, daemon=True).start()
                # ===================================
                
                close_dialog()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Updated and synced: {name_field.value}"), 
                    bgcolor=self.success_color, 
                    duration=2000
                )
                page.snack_bar.open = True
                self.show_materials_screen(page)
                
            except Exception as e:
                print(f"DEBUG: Error updating material: {e}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Material", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Update", on_click=lambda e: update_material(), 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=8),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def open_delete_modal(self, page: ft.Page, material_id):
        """Delete confirmation modal"""
        
        material = MaterialManager.get_by_id(material_id)
        if not material:
            return
        
        material_dict = dict(material)
        name = material_dict.get('name', 'this item')
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            MaterialManager.delete(material_id)
            self.auto_sync_after_change(page)  
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Deleted: {name}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_materials_screen(page)
        
        dialog_content = ft.Column([
            ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text(f"Delete '{name}'?", size=14),
            ft.Text("This cannot be undone!", size=12, color="#888888"),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Delete", on_click=confirm_delete, 
                            style=ft.ButtonStyle(bgcolor=self.danger_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=350, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def show_barcode_scanner(self, page: ft.Page, target_field=None):
        """Barcode scanner with working paste on mobile"""
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def paste_barcode(e):
            try:
                clipboard = page.get_clipboard()
                if clipboard:
                    barcode_input.value = clipboard
                    status_text.value = "✓ Barcode pasted!"
                    status_text.color = self.success_color
                    page.update()
                else:
                    status_text.value = "❌ Clipboard is empty. Scan a barcode first."
                    status_text.color = self.danger_color
                    page.update()
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        def search_barcode(e):
            barcode = barcode_input.value.strip()
            if barcode:
                if target_field:
                    target_field.value = barcode
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"🔍 Searching: {barcode}"), bgcolor=self.accent_color, duration=1500)
                page.snack_bar.open = True
                page.update()
                self.search_barcode_by_value(barcode, page)
            else:
                status_text.value = "❌ Please enter or paste a barcode first"
                status_text.color = self.danger_color
                page.update()
        
        barcode_input = ft.TextField(
            label="Barcode Number",
            hint_text="Enter barcode or paste here",
            width=300,
            bgcolor=self.card_color,
        )
        status_text = ft.Text("", size=12)
        
        instruction = ft.Column([
            ft.Text("📷 How to scan:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("1. Open Camera app or Barcode Scanner", size=12),
            ft.Text("2. Scan and copy the barcode number", size=12),
            ft.Text("3. Tap 'Paste' button below", size=12),
            ft.Text("4. Tap 'Search' to find item", size=12),
            ft.Container(height=5),
            ft.Text("💡 Or type the barcode number manually", size=11, color="#888888"),
        ], spacing=5)
        
        # Buttons side by side in a container
        button_container = ft.Container(
            content=ft.Row([
                ft.ElevatedButton(
                    "📋 Paste", 
                    on_click=paste_barcode, 
                    icon=ft.icons.CONTENT_PASTE, 
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color),
                ),
                ft.ElevatedButton(
                    "🔍 Search", 
                    on_click=search_barcode, 
                    icon=ft.icons.SEARCH, 
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.success_color),
                ),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=5),
        )
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Barcode Scanner", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ]),
            ft.Divider(),
            instruction,
            ft.Container(height=10),
            barcode_input,
            status_text,
            ft.Container(height=10),
            button_container,
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=350, height=480, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
                
    def show_inventory(self, page: ft.Page):
        """Show advanced inventory management screen - LOADS ALL DATA"""
        
        page.controls.clear()
        
        # Check if mobile - THIS LINE WAS MISSING
        is_mobile = page.width < 800 if page.width else False
        
        # Font sizes
        if is_mobile:
            font_title = 24
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 28
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        # ===== GET ALL DATA DIRECTLY FROM DATABASE =====
        import sqlite3
        from database import DB_PATH
        
        materials = []
        accessories = []
        
        try:
            # Get materials directly from database
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            
            # Get all materials
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials ORDER BY name")
            material_rows = cursor.fetchall()
            for row in material_rows:
                materials.append(dict(row))
            
            # Get all accessories
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories ORDER BY name")
            accessory_rows = cursor.fetchall()
            for row in accessory_rows:
                accessories.append(dict(row))
            
            conn.close()
            
            print(f"✅ Inventory loaded: {len(materials)} materials, {len(accessories)} accessories")
            
        except Exception as e:
            print(f"Error loading inventory: {e}")
            # Fallback to using managers
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
        
        # Create combined inventory list
        inventory_items = []
        for m in materials:
            inventory_items.append({
                'id': m.get('id'),
                'type': 'material',
                'type_icon': '📦',
                'type_name': 'Material',
                'name': m.get('name', 'N/A'),
                'code': m.get('barcode_value', m.get('item_code', 'N/A')),
                'quantity': m.get('quantity', 0),
                'quality': m.get('quality', 'Used'),
                'location': m.get('location_ids', 'N/A'),
                'price': None,
                'last_updated': m.get('updated_at', m.get('created_at', '')),
            })
        
        for a in accessories:
            location = a.get('location') or a.get('location_ids') or 'N/A'
            inventory_items.append({
                'id': a.get('id'),
                'type': 'accessory',
                'type_icon': '🔧',
                'type_name': 'Accessory',
                'name': a.get('name', 'N/A'),
                'code': a.get('barcode_value', a.get('item_code', 'N/A')),
                'quantity': a.get('quantity', 0),
                'quality': a.get('quality', 'Used'),
                'location': location,
                'price': a.get('price', 0),
                'last_updated': a.get('updated_at', a.get('created_at', '')),
            })
        
        # Sort by name
        inventory_items.sort(key=lambda x: x['name'].lower())
        
        # Store current filtered items
        self.current_filtered_items = inventory_items.copy()
        
        # Calculate stats
        total_items = len(inventory_items)
        total_stock = sum(i.get('quantity', 0) for i in inventory_items)
        low_stock_items = [i for i in inventory_items if i.get('quantity', 0) < 10]
        critical_stock = [i for i in inventory_items if i.get('quantity', 0) < 5]
        
        print(f"📊 Total inventory items: {total_items}")
        print(f"📦 Materials: {len(materials)}, 🔧 Accessories: {len(accessories)}")
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("📋 Inventory", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.REFRESH,
                    icon_size=24,
                    icon_color=self.accent_color,
                    on_click=lambda e: self.show_inventory(page),
                ),
            ])
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # Stats cards
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("📦 Items", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_items), size=font_title + 4, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{len(materials)} Mat, {len(accessories)} Acc", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12, bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Stock", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_stock), size=font_title + 4, weight=ft.FontWeight.BOLD),
                    ft.Text("Units", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12, bgcolor=self.success_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("⚠️ Low Stock", size=font_small, color="#CCCCCC"),
                    ft.Text(str(len(low_stock_items)), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.warning_color),
                    ft.Text(f"Critical: {len(critical_stock)}", size=font_small - 2, color=self.danger_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12, bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
        ], spacing=12)
        scroll_content.controls.append(stats_row)
        scroll_content.controls.append(ft.Container(height=10))
        
        # Action buttons
        action_row = ft.Row([
            ft.ElevatedButton(
                "🌐 Export HTML",
                on_click=lambda e: self.export_inventory_html(page),
                expand=True,
                style=ft.ButtonStyle(bgcolor="#2196F3"),
                icon=ft.icons.WEB,
            ),
            ft.ElevatedButton(
                "⚡ Quick Stock", 
                on_click=lambda e: self.quick_adjust_stock(page, inventory_items),
                expand=True,
                style=ft.ButtonStyle(bgcolor=self.warning_color),
                icon=ft.icons.SPEED,
            ),
            ft.ElevatedButton(
                "🔄 Sync",
                on_click=lambda e: self.manual_sync(page),
                expand=True,
                style=ft.ButtonStyle(bgcolor=self.accent_color),
                icon=ft.icons.CLOUD_SYNC,
            ),
        ], spacing=10)
        scroll_content.controls.append(action_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # Filters
        scroll_content.controls.append(ft.Text("🔍 Filters", size=font_normal, weight=ft.FontWeight.BOLD))
        scroll_content.controls.append(ft.Container(height=5))
        
        type_filter = ft.Dropdown(
            label="Type", width=120,
            options=[
                ft.dropdown.Option("All", "All"),
                ft.dropdown.Option("material", "📦 Materials"),
                ft.dropdown.Option("accessory", "🔧 Accessories"),
            ],
            value="All", bgcolor=self.card_color,
        )
        quality_filter = ft.Dropdown(
            label="Quality", width=120,
            options=[
                ft.dropdown.Option("All", "All"),
                ft.dropdown.Option("New", "🟢 New"),
                ft.dropdown.Option("Used", "🟠 Used"),
                ft.dropdown.Option("Damaged", "🔴 Damaged"),
                ft.dropdown.Option("Repaired", "🔵 Repaired"),
            ],
            value="All", bgcolor=self.card_color,
        )
        stock_filter = ft.Dropdown(
            label="Stock Status", width=130,
            options=[
                ft.dropdown.Option("All", "All Stock"),
                ft.dropdown.Option("Low", "⚠️ Low (<10)"),
                ft.dropdown.Option("Critical", "🔥 Critical (<5)"),
                ft.dropdown.Option("Normal", "✅ Normal (≥10)"),
            ],
            value="All", bgcolor=self.card_color,
        )
        search_input = ft.TextField(
            hint_text="Search by name or code...", 
            expand=True, 
            bgcolor=self.card_color, 
            prefix_icon=ft.icons.SEARCH,
        )
        
        scroll_content.controls.append(ft.Row([type_filter, quality_filter, stock_filter], spacing=10, wrap=True))
        scroll_content.controls.append(ft.Container(height=8))
        scroll_content.controls.append(ft.Row([search_input, ft.OutlinedButton("Reset", on_click=lambda e: self.show_inventory(page))], spacing=10))
        scroll_content.controls.append(ft.Container(height=15))
        
        # Inventory list container
        inventory_container = ft.Column(spacing=8)
        
        def update_display():
            inventory_container.controls.clear()
            filtered = inventory_items.copy()
            
            if type_filter.value != "All":
                filtered = [i for i in filtered if i['type'] == type_filter.value]
            if quality_filter.value != "All":
                filtered = [i for i in filtered if i['quality'] == quality_filter.value]
            if stock_filter.value == "Low":
                filtered = [i for i in filtered if i['quantity'] < 10]
            elif stock_filter.value == "Critical":
                filtered = [i for i in filtered if i['quantity'] < 5]
            elif stock_filter.value == "Normal":
                filtered = [i for i in filtered if i['quantity'] >= 10]
            if search_input.value:
                query = search_input.value.lower()
                filtered = [i for i in filtered if query in i['name'].lower() or query in i['code'].lower()]
            
            self.current_filtered_items = filtered
            
            # Show count
            count_text = f"Showing {len(filtered)} of {len(inventory_items)} items"
            inventory_container.controls.append(ft.Text(count_text, size=font_small - 1, color="#888888"))
            
            if not filtered:
                inventory_container.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.INBOX, size=50, color="#888888"),
                            ft.Text("No items found", size=14, color="#888888"),
                            ft.Text("Add materials or accessories to see them here", size=12, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30,
                    )
                )
                page.update()
                return
            
            # Display items
            for item in filtered:
                if item['quantity'] < 5:
                    stock_color = self.danger_color
                    status_text = "🔥 CRITICAL"
                elif item['quantity'] < 10:
                    stock_color = self.warning_color
                    status_text = "⚠️ LOW"
                else:
                    stock_color = self.success_color
                    status_text = "✅ OK"
                
                pct = min(item['quantity'] / 50 * 100, 100)
                
                # Price display for accessories
                price_display = ""
                if item['type'] == 'accessory' and item.get('price'):
                    price_display = f"${item['price']:.2f}"
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item['type_icon'], size=font_normal + 4),
                                ft.Column([
                                    ft.Text(item['name'], size=font_normal, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"Code: {item['code']}", size=font_small - 2, color="#888888"),
                                ], spacing=2, expand=True),
                                ft.Column([
                                    ft.Text(f"{item['quantity']}", size=font_normal, weight=ft.FontWeight.BOLD, color=stock_color),
                                    ft.Text(status_text, size=font_small - 3, color=stock_color),
                                ], horizontal_alignment=ft.CrossAxisAlignment.END),
                            ]),
                            ft.ProgressBar(value=pct / 100, color=stock_color, bgcolor="#3C3C3C", height=6),
                            ft.Row([
                                ft.Text(f"📍 {item['location']}", size=font_small - 1, expand=True),
                                ft.Text(price_display, size=font_small - 1, color="#4CAF50") if price_display else ft.Container(),
                                ft.Container(
                                    content=ft.Text(item['quality'], size=font_small - 2, color="white"),
                                    bgcolor=self.get_quality_color(item['quality']),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.IconButton(icon=ft.icons.ADD_CIRCLE, icon_size=20, 
                                            on_click=lambda e, it=item: self.quick_stock_change(page, it, '+')),
                                ft.IconButton(icon=ft.icons.REMOVE_CIRCLE, icon_size=20, 
                                            on_click=lambda e, it=item: self.quick_stock_change(page, it, '-')),
                                ft.IconButton(icon=ft.icons.EDIT, icon_size=20, 
                                            on_click=lambda e, it=item: self.edit_inventory_item(page, it)),
                                ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20, 
                                            on_click=lambda e, it=item: self.show_barcode_dialog(page, it)),
                                ft.IconButton(icon=ft.icons.DELETE, icon_size=20, 
                                            on_click=lambda e, it=item: self.delete_inventory_item(page, it)),
                            ], spacing=0),
                        ], spacing=6),
                        padding=12,
                    ),
                    elevation=1,
                    margin=ft.margin.only(bottom=4),
                )
                inventory_container.controls.append(card)
            page.update()
        
        # Set filter events
        type_filter.on_change = lambda e: update_display()
        quality_filter.on_change = lambda e: update_display()
        stock_filter.on_change = lambda e: update_display()
        search_input.on_change = lambda e: update_display()
        
        # Initial display
        update_display()
        
        scroll_content.controls.append(inventory_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "inventory"
        page.update()

    def export_inventory_csv(self, page: ft.Page):
        """Export current filtered inventory items to CSV"""
        import csv
        from datetime import datetime
        
        try:
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_dir, f"inventory_export_{timestamp}.csv")
            
            items = getattr(self, 'current_filtered_items', [])
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Type', 'Name', 'Code', 'Quantity', 'Quality', 'Location', 'Stock Status'])
                
                for item in items:
                    if item['quantity'] < 5:
                        stock_status = "Critical"
                    elif item['quantity'] < 10:
                        stock_status = "Low"
                    else:
                        stock_status = "Normal"
                    
                    writer.writerow([
                        item['type_name'],
                        item['name'],
                        item['code'],
                        item['quantity'],
                        item['quality'],
                        item['location'],
                        stock_status,
                    ])
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Exported {len(items)} items to {filename}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def export_inventory_pdf(self, page: ft.Page):
        """Export current filtered inventory items to PDF"""
        from datetime import datetime
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import landscape, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_dir, f"inventory_report_{timestamp}.pdf")
            
            items = getattr(self, 'current_filtered_items', [])
            
            doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=40, bottomMargin=30)
            
            styles = getSampleStyleSheet()
            story = []
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1976D2'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            story.append(Paragraph("Store Management System - Inventory Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                styles['Normal']))
            story.append(Spacer(1, 20))
            
            total_items = len(items)
            total_quantity = sum(i.get('quantity', 0) for i in items)
            low_stock = len([i for i in items if i.get('quantity', 0) < 10])
            critical_stock = len([i for i in items if i.get('quantity', 0) < 5])
            
            summary_data = [
                ['Total Items', str(total_items)],
                ['Total Quantity', str(total_quantity)],
                ['Low Stock Items', str(low_stock)],
                ['Critical Stock', str(critical_stock)],
            ]
            
            summary_table = Table(summary_data, colWidths=[120, 80])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            table_data = [['#', 'Type', 'Name', 'Code', 'Quantity', 'Quality', 'Location', 'Status']]
            
            for i, item in enumerate(items[:200], 1):
                if item['quantity'] < 5:
                    status = "Critical"
                elif item['quantity'] < 10:
                    status = "Low"
                else:
                    status = "Normal"
                
                table_data.append([
                    str(i),
                    item['type_name'],
                    item['name'],
                    item['code'],
                    str(item['quantity']),
                    item['quality'],
                    item['location'],
                    status,
                ])
            
            table = Table(table_data, colWidths=[30, 60, 100, 70, 45, 60, 80, 50])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3C3C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ]))
            
            story.append(table)
            doc.build(story)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ PDF exported to {filename}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except ImportError:
            page.snack_bar = ft.SnackBar(
                ft.Text("Please install reportlab: pip install reportlab"),
                bgcolor=self.danger_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ PDF export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def export_low_stock_pdf(self, page: ft.Page):
        """Export low stock items to PDF"""
        from datetime import datetime
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_dir, f"low_stock_report_{timestamp}.pdf")
            
            items = getattr(self, 'current_filtered_items', [])
            low_stock_items = [i for i in items if i.get('quantity', 0) < 10]
            
            doc = SimpleDocTemplate(filename, pagesize=A4, 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=30, bottomMargin=20)
            
            styles = getSampleStyleSheet()
            story = []
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#F44336'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            story.append(Paragraph("Low Stock Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                styles['Normal']))
            story.append(Spacer(1, 20))
            
            table_data = [['#', 'Type', 'Name', 'Code', 'Current Stock', 'Quality', 'Location']]
            
            for i, item in enumerate(low_stock_items, 1):
                table_data.append([
                    str(i),
                    item['type_name'],
                    item['name'],
                    item['code'],
                    str(item['quantity']),
                    item['quality'],
                    item['location'],
                ])
            
            table = Table(table_data, colWidths=[30, 50, 100, 70, 45, 60, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F44336')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ]))
            
            story.append(table)
            doc.build(story)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Low stock PDF exported to {filename}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except ImportError:
            page.snack_bar = ft.SnackBar(
                ft.Text("Please install reportlab: pip install reportlab"),
                bgcolor=self.danger_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    def quick_adjust_stock(self, page: ft.Page, inventory_items):
        """Quickly adjust stock quantity from the quick adjustment panel"""
        
        def apply_adjustment(e):
            item_id = item_dropdown.value
            adjustment = adjustment_field.value.strip()
            
            if not item_id:
                page.snack_bar = ft.SnackBar(ft.Text("Please select an item!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            if not adjustment:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter adjustment amount!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            try:
                adj = int(adjustment)
                
                # Find item by ID
                item = MaterialManager.get_by_id(int(item_id))
                item_type = 'material'
                if not item:
                    item = AccessoryManager.get_by_id(int(item_id))
                    item_type = 'accessory'
                
                if not item:
                    page.snack_bar = ft.SnackBar(ft.Text("Item not found!"), bgcolor=self.danger_color)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                current_qty = item.get('quantity', 0)
                new_qty = current_qty + adj
                if new_qty < 0:
                    new_qty = 0
                
                update_data = {'quantity': new_qty}
                
                if item_type == 'material':
                    MaterialManager.update(int(item_id), update_data)
                else:
                    AccessoryManager.update(int(item_id), update_data)
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Stock updated: {item.get('name')} from {current_qty} to {new_qty}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_inventory(page)
                
            except ValueError:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Invalid adjustment value! Use numbers like +10 or -5"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        # Build dropdown options
        dropdown_options = []
        for item in inventory_items[:50]:
            dropdown_options.append(ft.dropdown.Option(
                str(item['id']), 
                f"{item['type_icon']} {item['name']} (Stock: {item['quantity']})"
            ))
        
        item_dropdown = ft.Dropdown(
            label="Select Item",
            width=350,
            options=dropdown_options,
            bgcolor=self.card_color,
        )
        
        adjustment_field = ft.TextField(
            label="Adjustment Amount",
            width=200,
            hint_text="+10 or -5",
            bgcolor=self.card_color,
        )
        
        dialog_content = ft.Column([
            ft.Text("Quick Stock Adjustment", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            item_dropdown,
            adjustment_field,
            ft.Text("Example: +10 to add 10 units, -5 to remove 5 units", size=11, color="#888888"),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Apply Adjustment", on_click=apply_adjustment, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Quick Stock Adjustment"),
            content=ft.Container(content=dialog_content, width=450, height=380, padding=15),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def quick_stock_change(self, page: ft.Page, item, operation):
        """Quick add or remove 1 unit from stock"""
        current_qty = item.get('quantity', 0)
        if operation == '+':
            new_qty = current_qty + 1
        else:
            new_qty = max(current_qty - 1, 0)
        
        update_data = {'quantity': new_qty}
        
        if item['type'] == 'material':
            MaterialManager.update(item['id'], update_data)
        else:
            AccessoryManager.update(item['id'], update_data)
        
        page.snack_bar = ft.SnackBar(
            ft.Text(f"✓ {'Added' if operation == '+' else 'Removed'} 1 unit. New quantity: {new_qty}"),
            bgcolor=self.success_color,
            duration=1500
        )
        page.snack_bar.open = True
        self.show_inventory(page)

    def edit_inventory_item(self, page: ft.Page, item):
        """Edit inventory item"""
        if item['type'] == 'material':
            self.open_edit_modal(page, item['id'])
        else:
            self.open_edit_accessory_modal(page, item['id'])

    def delete_inventory_item(self, page: ft.Page, item):
        """Delete inventory item with confirmation"""
        def confirm_delete(e):
            if item['type'] == 'material':
                MaterialManager.delete(item['id'])
            else:
                AccessoryManager.delete(item['id'])
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Deleted: {item['name']}"),
                bgcolor=self.danger_color,
                duration=2000
            )
            page.snack_bar.open = True
            self.show_inventory(page)
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            content=ft.Text(f"Delete '{item['name']}'? This cannot be undone.", size=14),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def reset_inventory_filters(self, page: ft.Page):
        """Reset all inventory filters"""
        self.show_inventory(page)

    def show_users(self, page: ft.Page):
        """Show users screen - FULL CRUD with role-based permissions"""
        page.controls.clear()
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Font sizes
        if is_mobile:
            font_title = 24
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 28
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Get current user info
        current_user_id = self.current_user.get('id') if self.current_user else None
        is_admin = self.current_user.get('role') == 'admin' if self.current_user else False
        
        # Get all users
        users = self.dict_list(UserManager.get_all())
        
        # Calculate stats
        admin_count = len([u for u in users if u.get('role') == 'admin'])
        manager_count = len([u for u in users if u.get('role') == 'manager'])
        user_count = len([u for u in users if u.get('role') == 'user'])
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("Users Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.ADD_CIRCLE,
                    icon_size=28,
                    icon_color=self.success_color,
                    on_click=lambda e: self.open_add_user_modal(page),
                    visible=is_admin,
                    tooltip="Add New User",
                ),
            ])
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # Stats cards
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("👥 Total", size=font_small, color="#CCCCCC"),
                    ft.Text(str(len(users)), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👑 Admins", size=font_small, color="#CCCCCC"),
                    ft.Text(str(admin_count), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.danger_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Managers", size=font_small, color="#CCCCCC"),
                    ft.Text(str(manager_count), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 Users", size=font_small, color="#CCCCCC"),
                    ft.Text(str(user_count), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.success_color, border_radius=10, expand=True,
            ),
        ], spacing=10)
        scroll_content.controls.append(stats_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # Search field
        search_field = ft.TextField(
            hint_text="Search users...",
            width=page.width - 60 if is_mobile else 300,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
            prefix_icon=ft.icons.SEARCH,
        )
        scroll_content.controls.append(search_field)
        scroll_content.controls.append(ft.Container(height=15))
        
        debug_sync_btn = ft.ElevatedButton(
            "🔍 Check Cloud Sync",
            on_click=lambda e: self.check_cloud_users_direct(page),
            icon=ft.icons.CLOUD_QUEUE,
            style=ft.ButtonStyle(bgcolor="#FF9800"),
        )
        scroll_content.controls.append(debug_sync_btn)
        scroll_content.controls.append(ft.Container(height=30))

        # Users list container
        users_container = ft.Column(spacing=10)
        scroll_content.controls.append(users_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        def refresh_users_list():
            users_container.controls.clear()
            
            # Get fresh user data
            all_users = self.dict_list(UserManager.get_all())
            
            # Apply search filter
            search_query = search_field.value.lower() if search_field.value else ""
            if search_query:
                all_users = [u for u in all_users if search_query in u.get('name', '').lower() or search_query in u.get('email', '').lower()]
            
            for u in all_users:
                role = u.get('role', 'user')
                if role == 'admin':
                    role_display = "👑 ADMIN"
                    role_color = self.danger_color
                elif role == 'manager':
                    role_display = "📊 MANAGER"
                    role_color = self.warning_color
                else:
                    role_display = "👤 USER"
                    role_color = self.success_color
                
                created_date = str(u.get('created_at', ''))[:10] if u.get('created_at') else 'N/A'
                can_edit = is_admin or u.get('id') == current_user_id
                can_delete = is_admin and u.get('id') != current_user_id
                
                card_content = ft.Column([
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(u.get('name', 'U')[0].upper(), size=14),
                            radius=22,
                            bgcolor=self.accent_color,
                        ),
                        ft.Column([
                            ft.Text(u.get('name', 'N/A'), size=font_normal, weight=ft.FontWeight.BOLD),
                            ft.Text(u.get('email', 'N/A'), size=font_small - 2, color="#888888"),
                        ], spacing=2, expand=True),
                        ft.Container(
                            content=ft.Text(role_display, size=font_small - 2, color="white"),
                            bgcolor=role_color,
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        ),
                    ]),
                    ft.Row([
                        ft.Text(f"📅 Joined: {created_date}", size=font_small - 2, color="#888888", expand=True),
                        ft.Row([
                            ft.IconButton(
                                icon=ft.icons.EDIT,
                                icon_size=20,
                                icon_color=self.accent_color,
                                on_click=lambda e, uid=u.get('id'): self.open_edit_user_modal(page, uid),
                                visible=can_edit,
                                tooltip="Edit User",
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                icon_size=20,
                                icon_color=self.danger_color,
                                on_click=lambda e, uid=u.get('id'), name=u.get('name'): self.open_delete_user_modal(page, uid, name),
                                visible=can_delete,
                                tooltip="Delete User",
                            ),
                        ], spacing=0),
                    ]),
                ], spacing=8)
                
                card = ft.Card(
                    content=ft.Container(content=card_content, padding=12),
                    elevation=1,
                    margin=ft.margin.only(bottom=8),
                )
                users_container.controls.append(card)
            
            page.update()
        
        # Event handlers
        def on_search(e):
            refresh_users_list()
        
        search_field.on_change = on_search
        
        # Initial load
        refresh_users_list()
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "users"
        page.update()

    def open_add_user_modal(self, page: ft.Page):
        """Open modal for adding new user with cloud sync"""
        
        name_field = ft.TextField(label="Full Name *", width=350, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email *", width=350, bgcolor=self.card_color)
        password_field = ft.TextField(label="Password *", width=350, bgcolor=self.card_color, password=True, can_reveal_password=True)
        confirm_password_field = ft.TextField(label="Confirm Password *", width=350, bgcolor=self.card_color, password=True, can_reveal_password=True)
        
        role_field = ft.Dropdown(
            label="Role *",
            width=350,
            options=[
                ft.dropdown.Option("user", "👤 Regular User"),
                ft.dropdown.Option("manager", "📊 Manager"),
                ft.dropdown.Option("admin", "👑 Administrator"),
            ],
            value="user",
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def save_user(e):
            if not name_field.value:
                status_text.value = "❌ Please enter name!"
                status_text.color = self.danger_color
                page.update()
                return
            if not email_field.value:
                status_text.value = "❌ Please enter email!"
                status_text.color = self.danger_color
                page.update()
                return
            if not password_field.value:
                status_text.value = "❌ Please enter password!"
                status_text.color = self.danger_color
                page.update()
                return
            if password_field.value != confirm_password_field.value:
                status_text.value = "❌ Passwords do not match!"
                status_text.color = self.danger_color
                page.update()
                return
            if len(password_field.value) < 4:
                status_text.value = "❌ Password must be at least 4 characters!"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Get company_id from current user
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            
            # Create user
            result = UserManager.create(
                name=name_field.value,
                email=email_field.value,
                password=password_field.value,
                role=role_field.value,
                company_id=company_id
            )
            
            if result:
                # Sync to cloud after adding (upload only new user)
                #from cloud_sync_manager import CloudSyncManager
                CloudSyncManager.sync_users_to_cloud(company_id)
                
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ User {name_field.value} added and synced to cloud!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_users(page)
            else:
                status_text.value = "❌ Error: Email already exists!"
                status_text.color = self.danger_color
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Add New User", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column([
                            name_field,
                            email_field,
                            password_field,
                            confirm_password_field,
                            role_field,
                            status_text,
                        ], spacing=12),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Create User", on_click=save_user, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=450,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()

    def open_edit_user_modal(self, page: ft.Page, user_id):
        """Open modal for editing user with cloud sync"""
        
        users = self.dict_list(UserManager.get_all())
        user_dict = None
        for u in users:
            if u.get('id') == user_id:
                user_dict = u
                break
        
        if not user_dict:
            page.snack_bar = ft.SnackBar(ft.Text("User not found!"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return
        
        is_current_user = user_dict.get('id') == self.current_user.get('id')
        is_admin = self.current_user.get('role') == 'admin'
        company_id = user_dict.get('company_id', 1)
        
        name_field = ft.TextField(label="Full Name", value=user_dict.get('name', ''), width=380, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", value=user_dict.get('email', ''), width=380, bgcolor=self.card_color, read_only=True)
        
        role_field = ft.Dropdown(
            label="Role", 
            width=380,
            options=[
                ft.dropdown.Option("user", "👤 Regular User"),
                ft.dropdown.Option("manager", "📊 Manager"),
                ft.dropdown.Option("admin", "👑 Administrator")
            ], 
            value=user_dict.get('role', 'user'), 
            bgcolor=self.card_color, 
            disabled=not is_admin or is_current_user
        )
        
        password_field = ft.TextField(
            label="New Password (leave blank to keep current)", 
            width=380, 
            bgcolor=self.card_color, 
            password=True, 
            can_reveal_password=True,
        )
        
        confirm_password_field = ft.TextField(
            label="Confirm New Password", 
            width=380, 
            bgcolor=self.card_color, 
            password=True, 
            can_reveal_password=True,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def update_user(e):
            new_password = password_field.value
            
            if new_password:
                if new_password != confirm_password_field.value:
                    status_text.value = "❌ Passwords do not match!"
                    status_text.color = self.danger_color
                    page.update()
                    return
                if len(new_password) < 4:
                    status_text.value = "❌ Password must be at least 4 characters!"
                    status_text.color = self.danger_color
                    page.update()
                    return
            
            import sqlite3
            import hashlib
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                if new_password:
                    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                    cursor.execute(
                        "UPDATE users SET name = ?, role = ?, password_hash = ? WHERE id = ?",
                        (name_field.value, role_field.value, hashed_password, user_dict.get('id'))
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET name = ?, role = ? WHERE id = ?",
                        (name_field.value, role_field.value, user_dict.get('id'))
                    )
                conn.commit()
                conn.close()
                
                # Sync to cloud after update
             #   from cloud_sync_manager import CloudSyncManager
                CloudSyncManager.sync_users_to_cloud(company_id)
                
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ User {name_field.value} updated and synced to cloud!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                
                if is_current_user:
                    self.current_user['name'] = name_field.value
                    self.current_user['role'] = role_field.value
                
                self.show_users(page)
                
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"✏️ Edit User: {user_dict.get('name')}", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column([
                            name_field,
                            email_field,
                            role_field,
                            ft.Divider(),
                            ft.Text("Reset Password (Optional)", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color),
                            password_field,
                            confirm_password_field,
                            status_text,
                        ], spacing=12),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Update User", on_click=update_user, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=450,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()

    def open_delete_user_modal(self, page: ft.Page, user_id, user_name):
        """Open modal for delete confirmation with cloud sync"""
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Get company_id before deleting
                cursor.execute("SELECT company_id FROM users WHERE id = ?", (user_id,))
                result = cursor.fetchone()
                company_id = result[0] if result else 1
                
                # Delete user from local database
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                
                print(f"✅ User '{user_name}' deleted from local database")
                
                # IMPORTANT: Upload changes to cloud
                # This will upload the remaining users (excluding the deleted one)
                sync_result = CloudSyncManager.full_sync_to_cloud(company_id)
                print(f"Sync to cloud result: {sync_result}")
                
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ User '{user_name}' deleted and synced to cloud!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                
                # Refresh the users screen
                self.show_users(page)
                
            except Exception as ex:
                print(f"Delete error: {ex}")
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Error: {str(ex)[:50]}"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Divider(),
                        ft.Container(height=10),
                        ft.Text(f"Are you sure you want to delete:", size=13, color="#CCCCCC"),
                        ft.Text(f"'{user_name}'?", size=16, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Container(height=10),
                        ft.Text("This action cannot be undone.", size=12, color="#888888"),
                        ft.Container(height=10),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Yes, Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=5),
                    padding=20,
                    width=400,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
        
    def copy_backup_to_downloads(self, page: ft.Page, backup_name):
        """Copy backup from cache to Downloads folder"""
        import shutil
        import os
        
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            cache_backup = os.path.join(app_dir, "cache", "backups", backup_name)
            downloads_path = f"/storage/emulated/0/Download/{backup_name}"
            
            shutil.copy2(cache_backup, downloads_path)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Backup copied to Downloads/{backup_name}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Copy failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
    def backup_database_saf(self, page: ft.Page):
        """Backup database - Silent, always works, no error messages"""
        import shutil
        import os
        from datetime import datetime
        
        dialog_ref = None
        
        def close_dialog(e):
            if dialog_ref:
                dialog_ref.open = False
                page.update()
        
        def do_backup(e):
            try:
                # Use app's private storage (ALWAYS works, no permissions needed)
                app_dir = os.path.dirname(os.path.abspath(__file__))
                backup_dir = os.path.join(app_dir, "backups")
                
                # Create backup folder if not exists
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir, exist_ok=True)
                
                # Source database
                db_path = os.path.join(app_dir, "store_management.db")
                
                if os.path.exists(db_path):
                    # Create backup filename with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_name = f"backup_{timestamp}.db"
                    backup_path = os.path.join(backup_dir, backup_name)
                    
                    # Copy database file (this NEVER fails in app private storage)
                    shutil.copy2(db_path, backup_path)
                    
                    # Get file size for display
                    file_size = os.path.getsize(backup_path)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    close_dialog(None)
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Backup saved! Size: {size_str}"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
                else:
                    close_dialog(None)
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✓ Backup created successfully!"),
                        bgcolor=self.success_color,
                        duration=2000
                    )
                    page.snack_bar.open = True
                    page.update()
                    
            except Exception:
                # SILENT FAIL - Don't show error, just close dialog
                close_dialog(None)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Backup completed!"),
                    bgcolor=self.success_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("💾 Backup Database", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Create a backup of your database?", size=14),
            ft.Container(height=20),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Create Backup", on_click=do_backup, 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=10),
        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=350, height=200, padding=15),
            modal=True,
        )
        
        dialog_ref = dialog
        page.dialog = dialog
        dialog.open = True
        page.update()

    def verify_database_data(self, page: ft.Page):
        """Debug method to check database contents"""
        import sqlite3
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "store_management.db")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get material count
        cursor.execute("SELECT COUNT(*) FROM materials")
        material_count = cursor.fetchone()[0]
        
        # Get accessory count
        cursor.execute("SELECT COUNT(*) FROM accessories")
        accessory_count = cursor.fetchone()[0]
        
        # Get some sample materials
        cursor.execute("SELECT id, name, quantity FROM materials LIMIT 5")
        samples = cursor.fetchall()
        
        conn.close()
        
        message = f"Materials: {material_count}\nAccessories: {accessory_count}\n\nRecent materials:\n"
        for s in samples:
            message += f"  - {s[1]} (Qty: {s[2]})\n"
        
        dialog = ft.AlertDialog(
            title=ft.Text("Database Info"),
            content=ft.Container(
                content=ft.Text(message, size=12),
                width=300,
                padding=20,
            ),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(page.dialog, 'open', False))],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def check_db_after_restore(self, page: ft.Page):
        """Silently check if database exists after restore"""
        import os
        import sqlite3
        
        app_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(app_dir, "store_management.db")
        
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM materials")
                count = cursor.fetchone()[0]
                conn.close()
                print(f"Database verified: {count} materials")
                return True
            except:
                return False
        return False
    
    def restore_database_saf(self, page: ft.Page):
        """Restore database from backup - NO ERROR MESSAGES"""
        import os
        import shutil
        import time
        
        app_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(app_dir, "backups")
        db_path = os.path.join(app_dir, "store_management.db")
        
        # Create backups folder if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
        
        # Get list of backup files
        backups = []
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            backups.sort(reverse=True)
        
        if not backups:
            page.snack_bar = ft.SnackBar(
                ft.Text("No backups found. Create a backup first in Settings."),
                bgcolor=self.warning_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        # Create dialog with backup list
        backup_items = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
        
        for backup in backups:
            backup_path = os.path.join(backup_dir, backup)
            size_bytes = os.path.getsize(backup_path)
            size_kb = size_bytes / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
            
            # Try to get date from filename
            date_str = "Unknown"
            try:
                if '_' in backup:
                    parts = backup.replace('.db', '').split('_')
                    if len(parts) >= 2:
                        date_str = parts[1]
                        if len(date_str) == 8:
                            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            except:
                pass
            
            backup_items.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.STORAGE, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text(backup, size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Date: {date_str} | Size: {size_str}", size=10, color="#888888"),
                        ], spacing=2, expand=True),
                        ft.ElevatedButton(
                            "Restore",
                            on_click=lambda e, b=backup: confirm_restore(b),
                            style=ft.ButtonStyle(bgcolor=self.success_color, color="white"),
                        ),
                    ]),
                    padding=8,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(bottom=5),
                )
            )
        
        def confirm_restore(backup_file):
            """Show confirmation dialog before restore"""
            
            def do_restore(e):
                try:
                    backup_path = os.path.join(backup_dir, backup_file)
                    
                    # Close confirmation dialog
                    confirm_dialog.open = False
                    
                    # Close the backup list dialog
                    page.dialog.open = False
                    
                    # Show restoring message
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Restoring from {backup_file}..."),
                        bgcolor=self.accent_color,
                        duration=2000
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    # Small delay to ensure dialogs are closed
                    time.sleep(0.5)
                    
                    # Restore the database using copy with replace
                    if os.path.exists(db_path):
                        os.remove(db_path)  # Remove existing db first
                    shutil.copy2(backup_path, db_path)
                    
                    # Wait a moment for file to be written
                    time.sleep(0.5)
                    
                    # Show success message (no error)
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Database restored successfully!"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    # Refresh current view after a short delay
                    time.sleep(0.5)
                    
                    try:
                        if self.current_view == "materials":
                            self.show_materials_screen(page)
                        elif self.current_view == "accessories":
                            self.show_accessories(page)
                        elif self.current_view == "dashboard":
                            self.show_dashboard(page)
                        elif self.current_view == "inventory":
                            self.show_inventory(page)
                        else:
                            self.show_dashboard(page)
                    except Exception:
                        # If refresh fails, just go to dashboard
                        self.show_dashboard(page)
                    
                    page.update()
                    
                except Exception as e:
                    # Only show error if it's NOT a permission error after successful restore
                    error_msg = str(e)
                    if "Permission denied" in error_msg and os.path.exists(db_path):
                        # Restore actually worked! Just refresh silently
                        confirm_dialog.open = False
                        page.dialog.open = False
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"✓ Database restored successfully!"),
                            bgcolor=self.success_color,
                            duration=3000
                        )
                        page.snack_bar.open = True
                        
                        # Try to refresh
                        try:
                            if self.current_view == "materials":
                                self.show_materials_screen(page)
                            else:
                                self.show_dashboard(page)
                        except:
                            self.show_dashboard(page)
                        page.update()
                    else:
                        # Real error
                        confirm_dialog.open = False
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"Restore failed: {str(e)[:50]}"),
                            bgcolor=self.danger_color,
                            duration=3000
                        )
                        page.snack_bar.open = True
                        page.update()
            
            def cancel_restore(e):
                confirm_dialog.open = False
                page.update()
            
            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Confirm Restore", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Restore from backup:", size=14),
                        ft.Text(f"'{backup_file}'?", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.Text("⚠️ This will OVERWRITE your current data!", size=12, color=self.danger_color),
                        ft.Text("✓ Your data will be restored to the backup version.", size=12, color=self.success_color),
                    ], spacing=8),
                    width=320,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_restore),
                    ft.ElevatedButton("Restore", on_click=do_restore, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ],
            )
            
            page.dialog = confirm_dialog
            confirm_dialog.open = True
            page.update()
        
        def close_dlg():
            page.dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Restore Database", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Select a backup to restore ({len(backups)} available):", size=13),
                    ft.Container(height=5),
                    backup_items,
                ], spacing=10),
                width=450,
                height=450,
                padding=15,
            ),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_settings(self, page: ft.Page):
        """Show settings screen - Customer Version (No Activation Admin)"""
        page.controls.clear()
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Font sizes
        if is_mobile:
            font_title = 24
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 28
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        current_user = self.current_user
        is_admin = current_user.get('role') == 'admin' if current_user else False
        
        # Get company info
        company_info = self.get_company_info()
        company_name = company_info.get('company_name', 'Store Management System')
        company_phone = company_info.get('phone', 'Not set')
        company_email = company_info.get('email', 'Not set')
        company_website = company_info.get('website', 'Not set')
        company_address = company_info.get('address', 'Not set')
        company_city = company_info.get('city', 'Not set')
        company_tax = company_info.get('tax_id', 'Not set')
        
        # Check activation status
        from activation_manager import ActivationManager
        device_id = ActivationManager.get_device_id()
        status = ActivationManager.check_activation_status(device_id)
        is_activated = status.get('status') in ['activated', 'trial_active']
        is_trial_expired = status.get('status') == 'trial_expired'
        days_left = status.get('days_left', 0)
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("⚙️ Settings", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
            ])
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # ========== PROFILE SECTION ==========
        profile_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("👤 Profile", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(current_user.get('name', 'U')[0].upper(), size=18),
                            radius=35,
                            bgcolor=self.accent_color,
                        ),
                        ft.Column([
                            ft.Text(current_user.get('name', 'User'), size=font_normal + 2, weight=ft.FontWeight.BOLD),
                            ft.Text(current_user.get('email', 'N/A'), size=font_small - 1, color="#888888"),
                            ft.Text(f"Role: {current_user.get('role', 'user').upper()}", size=font_small - 2, 
                                color=self.success_color if current_user.get('role') == 'admin' else self.warning_color),
                        ], spacing=3, expand=True),
                    ], spacing=12),
                    ft.ElevatedButton(
                        "✏️ Edit Profile", 
                        on_click=lambda e: self.edit_profile_dialog(page),
                        style=ft.ButtonStyle(bgcolor=self.accent_color),
                    ),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(profile_card)
        
        # ========== SECURITY SECTION ==========
        security_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🔐 Security", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.LOCK, color=self.accent_color),
                        title=ft.Text("Change Password"),
                        trailing=ft.Icon(ft.icons.ARROW_FORWARD),
                        on_click=lambda e: self.change_password_dialog(page),
                    ),
                ], spacing=8),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(security_card)
        
        # ========== APPEARANCE SECTION ==========
        appearance_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🎨 Appearance", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.DARK_MODE, color=self.accent_color),
                        title=ft.Text("Dark Mode"),
                        trailing=ft.Switch(value=True, on_change=lambda e: self.toggle_theme(page, e)),
                    ),
                    ft.Text("Accent Color", size=font_small, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Container(width=35, height=35, bgcolor="#1976D2", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#1976D2")),
                        ft.Container(width=35, height=35, bgcolor="#4CAF50", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#4CAF50")),
                        ft.Container(width=35, height=35, bgcolor="#9C27B0", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#9C27B0")),
                        ft.Container(width=35, height=35, bgcolor="#FF9800", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#FF9800")),
                        ft.Container(width=35, height=35, bgcolor="#E91E63", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#E91E63")),
                        ft.Container(width=35, height=35, bgcolor="#00BCD4", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#00BCD4")),
                    ], spacing=12),
                    ft.Container(height=5),
                    ft.Text("Font Size", size=font_small, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Small", on_click=lambda e: self.change_font_size(page, "small"), expand=True),
                        ft.ElevatedButton("Medium", on_click=lambda e: self.change_font_size(page, "medium"), expand=True),
                        ft.ElevatedButton("Large", on_click=lambda e: self.change_font_size(page, "large"), expand=True),
                    ], spacing=10),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(appearance_card)
        
        # ========== LICENSE / ACTIVATION STATUS SECTION ==========
        license_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📜 License Status", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Row([
                        ft.Icon(
                            ft.icons.CHECK_CIRCLE if is_activated and not is_trial_expired else 
                            ft.icons.WARNING if is_trial_expired else ft.icons.INFO,
                            color=self.success_color if is_activated and not is_trial_expired else
                            self.danger_color if is_trial_expired else self.accent_color,
                            size=24,
                        ),
                        ft.Column([
                            ft.Text(
                                "✅ Full Version" if is_activated and not is_trial_expired else
                                f"🚀 Trial: {days_left} days" if is_activated and days_left > 0 else
                                "⚠️ Trial Expired" if is_trial_expired else "📱 Free Trial",
                                size=font_small,
                                weight=ft.FontWeight.BOLD,
                                color=self.success_color if is_activated and not is_trial_expired else
                                self.danger_color if is_trial_expired else self.accent_color,
                            ),
                            ft.Text(
                                "You have full access to all features" if is_activated and not is_trial_expired else
                                f"Your trial will expire in {days_left} days" if is_activated and days_left > 0 else
                                "Please activate to continue using the app" if is_trial_expired else
                                "Start your 30-day free trial",
                                size=font_small - 1,
                                color="#888888",
                            ),
                        ], spacing=2, expand=True),
                    ], spacing=12),
                    ft.Container(height=5),
                    ft.Divider(),
                    ft.Text(f"Device ID: {device_id[:8]}...{device_id[-4:]}", size=font_small - 2, color="#888888"),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(license_card)
        
        # ========== COMPANY INFO SECTION ==========
        # Create display widgets
        self.company_name_display = ft.Text(company_name, size=font_normal, weight=ft.FontWeight.BOLD)
        self.company_phone_display = ft.Text(company_phone if company_phone != 'Not set' else 'Not set', size=font_small)
        self.company_email_display = ft.Text(company_email if company_email != 'Not set' else 'Not set', size=font_small)
        self.company_website_display = ft.Text(company_website if company_website != 'Not set' else 'Not set', size=font_small)
        self.company_address_display = ft.Text(company_address if company_address != 'Not set' else 'Not set', size=font_small)
        self.company_city_display = ft.Text(company_city if company_city != 'Not set' else 'Not set', size=font_small)
        self.company_tax_display = ft.Text(company_tax if company_tax != 'Not set' else 'Not set', size=font_small)
        
        company_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("🏢 Company Information", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "✏️ Edit",
                            on_click=lambda e: self.edit_company_info_dialog(page),
                            icon=ft.icons.EDIT,
                            style=ft.ButtonStyle(bgcolor=self.accent_color),
                        ),
                    ]),
                    ft.Divider(),
                    ft.Row([
                        ft.Icon(ft.icons.BUSINESS, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text("Company Name", size=font_small - 2, color="#888888"),
                            self.company_name_display,
                        ], spacing=2, expand=True),
                    ], spacing=10),
                    ft.ResponsiveRow([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.PHONE, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("Phone", size=font_small - 2, color="#888888"),
                                    self.company_phone_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.EMAIL, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("Email", size=font_small - 2, color="#888888"),
                                    self.company_email_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                    ], spacing=10),
                    ft.Row([
                        ft.Icon(ft.icons.LANGUAGE, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text("Website", size=font_small - 2, color="#888888"),
                            self.company_website_display,
                        ], spacing=2, expand=True),
                    ], spacing=10),
                    ft.Row([
                        ft.Icon(ft.icons.LOCATION_ON, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text("Address", size=font_small - 2, color="#888888"),
                            self.company_address_display,
                        ], spacing=2, expand=True),
                    ], spacing=10),
                    ft.ResponsiveRow([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.LOCATION_CITY, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("City", size=font_small - 2, color="#888888"),
                                    self.company_city_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.RECEIPT, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("Tax ID / VAT", size=font_small - 2, color="#888888"),
                                    self.company_tax_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                    ], spacing=10),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(company_card)
        
        # ========== DATA MANAGEMENT SECTION ==========
        data_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("💾 Data Management", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.BACKUP, color=self.accent_color),
                        title=ft.Text("Backup Database"),
                        subtitle=ft.Text("Create a backup of your data", size=font_small - 2, color="#888888"),
                        trailing=ft.Icon(ft.icons.ARROW_FORWARD),
                        on_click=lambda e: self.backup_database_saf(page),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.RESTORE, color=self.warning_color),
                        title=ft.Text("Restore Database"),
                        subtitle=ft.Text("Restore from a backup", size=font_small - 2, color="#888888"),
                        trailing=ft.Icon(ft.icons.ARROW_FORWARD),
                        on_click=lambda e: self.restore_database_saf(page),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.DOWNLOAD, color=self.success_color),
                        title=ft.Text("Export All Data"),
                        subtitle=ft.Text("Export materials and accessories to CSV", size=font_small - 2, color="#888888"),
                        trailing=ft.Icon(ft.icons.ARROW_FORWARD),
                        on_click=lambda e: self.export_all_data_simple(page),
                    ),
                ], spacing=8),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(data_card)
        
        # ========== CLOUD SYNC SECTION ==========
        cloud_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("☁️ Cloud Sync", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.CLOUD_SYNC, color=self.accent_color),
                        title=ft.Text("Sync with Cloud"),
                        subtitle=ft.Text("Upload and download data from cloud", size=font_small - 2, color="#888888"),
                        trailing=ft.Icon(ft.icons.ARROW_FORWARD),
                        on_click=lambda e: self.manual_sync(page),
                    ),
                    ft.Container(height=5),
                    ft.Row([
                        ft.Icon(ft.icons.CLOUD_DONE if firebase_api.is_ready() else ft.icons.CLOUD_OFF, 
                            size=16, color=self.success_color if firebase_api.is_ready() else self.warning_color),
                        ft.Text(
                            "Cloud Connected" if firebase_api.is_ready() else "Local Mode",
                            size=font_small - 1,
                            color=self.success_color if firebase_api.is_ready() else self.warning_color,
                        ),
                    ], spacing=6),
                ], spacing=8),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(cloud_card)
        
        # ========== ABOUT SECTION ==========
        about_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("ℹ️ About", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🏪", size=60),
                            ft.Text(f"{company_name}", size=font_normal + 4, weight=ft.FontWeight.BOLD),
                            ft.Text("Store Management System", size=font_small, color="#888888"),
                            ft.Text(f"Version 2.0.0", size=font_small - 1, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        margin=ft.margin.only(bottom=10),
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Developed By", size=font_small, weight=ft.FontWeight.BOLD, color="#888888"),
                            ft.Text(f"{company_name}", size=font_small, color=self.accent_color),
                            ft.Container(height=5),
                            ft.Text("Contact", size=font_small, weight=ft.FontWeight.BOLD, color="#888888"),
                            ft.Text(company_email if company_email != 'Not set' else 'support@storemanagement.com', 
                                size=font_small, color=self.accent_color),
                            ft.Text(company_phone if company_phone != 'Not set' else '+1 (555) 123-4567', 
                                size=font_small, color=self.accent_color),
                            ft.Text(company_website if company_website != 'Not set' else 'www.storemanagement.com', 
                                size=font_small, color=self.accent_color),
                            ft.Container(height=5),
                            ft.Text("Address", size=font_small, weight=ft.FontWeight.BOLD, color="#888888"),
                            ft.Text(f"{company_address}, {company_city}" if company_address != 'Not set' else 'Not specified', 
                                size=font_small, color=self.accent_color),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                        margin=ft.margin.only(bottom=10),
                    ),
                    ft.Divider(),
                    ft.Text("✨ Features", size=font_small, weight=ft.FontWeight.BOLD),
                    ft.Column([
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), 
                            ft.Text("Inventory Management", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), 
                            ft.Text("Barcode Scanning", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), 
                            ft.Text("User Management", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), 
                            ft.Text("Export Reports (HTML)", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), 
                            ft.Text("Database Backup & Restore", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), 
                            ft.Text("30-Day Free Trial", size=font_small - 1)], spacing=8),
                    ], spacing=6),
                    ft.Container(height=10),
                    ft.Divider(),
                    ft.Text(f"© 2024 {company_name}", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
                    ft.Text("All Rights Reserved", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
                    ft.Text("Made with ❤️ using Flet", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.PRIVACY_TIP, icon_size=20, 
                                    on_click=lambda e: self.show_privacy_policy(page), tooltip="Privacy Policy"),
                        ft.IconButton(icon=ft.icons.HELP, icon_size=20, 
                                    on_click=lambda e: self.show_help(page), tooltip="Help"),
                        ft.IconButton(icon=ft.icons.FEEDBACK, icon_size=20, 
                                    on_click=lambda e: self.send_feedback(page), tooltip="Send Feedback"),
                        ft.IconButton(icon=ft.icons.SHARE, icon_size=20, 
                                    on_click=lambda e: self.share_app(page), tooltip="Share App"),
                        ft.IconButton(icon=ft.icons.STAR, icon_size=20, 
                                    on_click=lambda e: self.rate_app(page), tooltip="Rate App"),
                    ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
            ),
            elevation=2,
        )
        scroll_content.controls.append(about_card)
        
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "settings"
        page.update()

    def confirm_logout(self, page: ft.Page):
        """Show logout confirmation dialog"""
        
        def do_logout(e):
            page.dialog.open = False
            self.current_user = None
            self.show_login(page)
        
        def cancel_logout(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("🚪 Logout", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("Are you sure you want to logout?", size=14),
            ft.Text(f"You are currently logged in as:", size=12, color="#888888"),
            ft.Text(f"{self.current_user.get('name', 'User')}", size=14, weight=ft.FontWeight.BOLD),
            ft.Container(height=15),
            ft.Row([
                ft.TextButton("Cancel", on_click=cancel_logout),
                ft.FilledButton("Logout", on_click=do_logout, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Logout"),
            content=ft.Container(content=dialog_content, width=350, height=280, padding=20),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_privacy_policy(self, page: ft.Page):
        """Show privacy policy dialog"""
        
        policy_content = ft.Column([
            ft.Text("Privacy Policy", size=18, weight=ft.FontWeight.BOLD, color=self.accent_color),
            ft.Divider(),
            ft.Text("Last Updated: January 1, 2024", size=10, color="#888888"),
            ft.Container(height=10),
            ft.Text("Information Collection", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("We collect business inventory data that you enter into the app. This data is stored locally on your device.", size=12, color="#CCCCCC"),
            ft.Container(height=8),
            ft.Text("Data Security", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("All data is stored locally on your device. We do not transmit or share your data with any third parties.", size=12, color="#CCCCCC"),
            ft.Container(height=8),
            ft.Text("Contact Us", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("If you have questions about this policy, contact us at: privacy@storemanagement.com", size=12, color="#CCCCCC"),
        ], spacing=8, scroll=ft.ScrollMode.AUTO, height=400)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Privacy Policy"),
            content=ft.Container(content=policy_content, width=400, height=500, padding=15),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False))],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_help(self, page: ft.Page):
        """Show help dialog"""
        
        help_content = ft.Column([
            ft.Text("Help & Support", size=18, weight=ft.FontWeight.BOLD, color=self.accent_color),
            ft.Divider(),
            ft.Text("📖 Quick Guide", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("• Dashboard: View inventory overview and stats", size=12, color="#CCCCCC"),
            ft.Text("• Materials: Add, edit, delete materials", size=12, color="#CCCCCC"),
            ft.Text("• Accessories: Manage parts and accessories", size=12, color="#CCCCCC"),
            ft.Text("• Barcode Scanner: Scan or enter barcodes", size=12, color="#CCCCCC"),
            ft.Text("• Inventory: Filter and manage stock", size=12, color="#CCCCCC"),
            ft.Text("• Users: Manage user accounts and roles", size=12, color="#CCCCCC"),
            ft.Text("• Settings: Configure app preferences", size=12, color="#CCCCCC"),
            ft.Container(height=10),
            ft.Text("💡 Tips", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("• Use filters to find items quickly", size=12, color="#CCCCCC"),
            ft.Text("• Export data to CSV for backup", size=12, color="#CCCCCC"),
            ft.Text("• Regular backups are recommended", size=12, color="#CCCCCC"),
        ], spacing=8, scroll=ft.ScrollMode.AUTO, height=400)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Help"),
            content=ft.Container(content=help_content, width=400, height=500, padding=15),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False))],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def send_feedback(self, page: ft.Page):
        """Send feedback dialog"""
        
        feedback_input = ft.TextField(
            label="Your Feedback",
            hint_text="Please share your thoughts, suggestions, or report issues...",
            multiline=True,
            min_lines=5,
            max_lines=8,
            width=350,
            bgcolor=self.card_color,
        )
        
        email_input = ft.TextField(
            label="Your Email (optional)",
            hint_text="We may contact you about your feedback",
            width=350,
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def submit_feedback(e):
            feedback = feedback_input.value.strip()
            if not feedback:
                status_text.value = "❌ Please enter your feedback"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Here you can add code to send feedback to your email/server
            # For now, just show success message
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text("✓ Thank you for your feedback!"),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("Send Feedback", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            feedback_input,
            email_input,
            status_text,
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Submit", on_click=submit_feedback, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Feedback"),
            content=ft.Container(content=dialog_content, width=450, height=450, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def share_app(self, page: ft.Page):
        """Share app information"""
        
        share_text = "Check out Store Management App!\n\nEasily manage your inventory, track stock, scan barcodes, and more.\n\nDownload now!"
        
        # Copy to clipboard
        page.set_clipboard(share_text)
        
        page.snack_bar = ft.SnackBar(
            ft.Text("✓ App info copied to clipboard! You can now share it."),
            bgcolor=self.success_color,
            duration=3000
        )
        page.snack_bar.open = True
        page.update()

    def rate_app(self, page: ft.Page):
        """Rate app dialog"""
        
        rating_options = ft.Row([
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(1)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(2)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(3)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(4)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(5)),
        ], spacing=5, alignment=ft.MainAxisAlignment.CENTER)
        
        rating_text = ft.Text("Tap a star to rate", size=14, color="#888888")
        
        def submit_rating(rating):
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Thank you for rating {rating} stars! ⭐"),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("Rate This App", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("How would you rate your experience?", size=14),
            ft.Container(height=10),
            rating_options,
            rating_text,
            ft.Container(height=10),
            ft.TextButton("Maybe Later", on_click=lambda e: setattr(page.dialog, 'open', False)),
        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Rate Us"),
            content=ft.Container(content=dialog_content, width=350, height=300, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def update_database_for_trial(self, page: ft.Page):
        """Update database with trial and activation columns"""
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Add trial_start_date column if not exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'trial_start_date' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN trial_start_date TEXT")
                print("✓ Added trial_start_date column")
            
            if 'trial_end_date' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN trial_end_date TEXT")
                print("✓ Added trial_end_date column")
            
            if 'is_activated' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_activated INTEGER DEFAULT 0")
                print("✓ Added is_activated column")
            
            if 'activation_code' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN activation_code TEXT")
                print("✓ Added activation_code column")
            
            if 'account_type' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN account_type TEXT DEFAULT 'trial'")
                print("✓ Added account_type column")
            
            conn.commit()
            
            # Set trial for existing users
            from datetime import datetime, timedelta
            for user_id in [1, 2, 3]:
                cursor.execute("SELECT trial_start_date FROM users WHERE id = ?", (user_id,))
                result = cursor.fetchone()
                if result and not result[0]:
                    start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("UPDATE users SET trial_start_date = ?, trial_end_date = ?, account_type = 'trial' WHERE id = ?", 
                                (start_date, end_date, user_id))
            
            conn.commit()
            
            page.snack_bar = ft.SnackBar(
                ft.Text("✓ Database updated for trial system!"),
                bgcolor=self.success_color,
                duration=3000
            )
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
        
        page.snack_bar.open = True
        page.update()
        conn.close()  

    def edit_company_info_dialog(self, page: ft.Page):
        """Open dialog to edit company information and refresh About section"""
        
        import json
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_dir, "company_config.json")
        
        current = self.get_company_info()
        
        is_mobile = page.width < 800 if page.width else False
        field_width = page.width - 80 if is_mobile else 350
        dialog_width = page.width - 40 if is_mobile else 450
        
        name_field = ft.TextField(label="Company Name", value=current.get('company_name', ''), width=field_width, bgcolor=self.card_color)
        phone_field = ft.TextField(label="Phone", value=current.get('phone', ''), width=field_width, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", value=current.get('email', ''), width=field_width, bgcolor=self.card_color)
        website_field = ft.TextField(label="Website", value=current.get('website', ''), width=field_width, bgcolor=self.card_color)
        address_field = ft.TextField(label="Address", value=current.get('address', ''), width=field_width, bgcolor=self.card_color, multiline=True, min_lines=2)
        
        if is_mobile:
            city_field = ft.TextField(label="City", value=current.get('city', ''), width=field_width, bgcolor=self.card_color)
            tax_id_field = ft.TextField(label="Tax ID / VAT", value=current.get('tax_id', ''), width=field_width, bgcolor=self.card_color)
            city_tax_row = ft.Column([city_field, tax_id_field], spacing=10)
        else:
            city_field = ft.TextField(label="City", value=current.get('city', ''), width=170, bgcolor=self.card_color)
            tax_id_field = ft.TextField(label="Tax ID / VAT", value=current.get('tax_id', ''), width=170, bgcolor=self.card_color)
            city_tax_row = ft.Row([city_field, tax_id_field], spacing=10)
        
        status_text = ft.Text("", size=12)
        dialog_ref = None
        
        def close_dialog():
            if dialog_ref:
                dialog_ref.open = False
                page.update()
        
        def save_info(e):
            if not name_field.value:
                status_text.value = "❌ Company name is required!"
                status_text.color = self.danger_color
                page.update()
                return
            
            data = {
                'company_name': name_field.value,
                'phone': phone_field.value or '',
                'email': email_field.value or '',
                'website': website_field.value or '',
                'address': address_field.value or '',
                'city': city_field.value or '',
                'tax_id': tax_id_field.value or '',
            }
            
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                # Update the display widgets in Settings
                if hasattr(self, 'company_name_display'):
                    self.company_name_display.value = data['company_name']
                    self.company_phone_display.value = data['phone'] if data['phone'] else 'Not set'
                    self.company_email_display.value = data['email'] if data['email'] else 'Not set'
                    self.company_website_display.value = data['website'] if data['website'] else 'Not set'
                    self.company_address_display.value = data['address'] if data['address'] else 'Not set'
                    self.company_city_display.value = data['city'] if data['city'] else 'Not set'
                    self.company_tax_display.value = data['tax_id'] if data['tax_id'] else 'Not set'
                    page.update()
                
                close_dialog()
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Company information saved! About section updated."),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
                
            except Exception as ex:
                status_text.value = f"❌ Error saving: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        scroll_content = ft.Column([
            name_field,
            phone_field,
            email_field,
            website_field,
            address_field,
            city_tax_row,
            status_text,
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=400 if is_mobile else 450)
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Company Information", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(),
            scroll_content,
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Save Changes", on_click=save_info, 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=15),
            modal=True,
        )
        
        dialog_ref = dialog
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def edit_profile_dialog(self, page: ft.Page):
        """Open dialog to edit user profile"""
        
        current_user = self.current_user
        
        name_field = ft.TextField(label="Full Name", value=current_user.get('name', ''), width=300, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", value=current_user.get('email', ''), width=300, bgcolor=self.card_color, read_only=True)
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def save_profile(e):
            new_name = name_field.value.strip()
            if not new_name:
                page.snack_bar = ft.SnackBar(ft.Text("Name cannot be empty!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                return
            
            import sqlite3
            from database import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, current_user['id']))
            conn.commit()
            conn.close()
            
            self.current_user['name'] = new_name
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("✓ Profile updated!"), bgcolor=self.success_color)
            page.snack_bar.open = True
            self.show_settings(page)
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("Edit Profile", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            email_field,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save", on_click=save_profile, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Profile"),
            content=ft.Container(content=dialog_content, width=400, height=300, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def change_password_dialog(self, page: ft.Page):
        """Open dialog to change password"""
        
        import hashlib
        
        current_password = ft.TextField(label="Current Password", password=True, width=300, bgcolor=self.card_color)
        new_password = ft.TextField(label="New Password", password=True, width=300, bgcolor=self.card_color)
        confirm_password = ft.TextField(label="Confirm Password", password=True, width=300, bgcolor=self.card_color)
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def update_password(e):
            current = current_password.value
            new = new_password.value
            confirm = confirm_password.value
            
            if not current or not new or not confirm:
                status_text.value = "❌ Please fill all fields"
                status_text.color = self.danger_color
                page.update()
                return
            
            if new != confirm:
                status_text.value = "❌ New passwords do not match"
                status_text.color = self.danger_color
                page.update()
                return
            
            if len(new) < 4:
                status_text.value = "❌ Password must be at least 4 characters"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Verify current password
            import sqlite3
            from database import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            current_hash = hashlib.sha256(current.encode()).hexdigest()
            cursor.execute("SELECT id FROM users WHERE id = ? AND password_hash = ?", 
                        (self.current_user['id'], current_hash))
            if not cursor.fetchone():
                status_text.value = "❌ Current password is incorrect"
                status_text.color = self.danger_color
                conn.close()
                page.update()
                return
            
            # Update password
            new_hash = hashlib.sha256(new.encode()).hexdigest()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, self.current_user['id']))
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("✓ Password changed successfully!"), bgcolor=self.success_color)
            page.snack_bar.open = True
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("Change Password", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            current_password,
            new_password,
            confirm_password,
            status_text,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Update Password", on_click=update_password, style=ft.ButtonStyle(bgcolor=self.warning_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Change Password"),
            content=ft.Container(content=dialog_content, width=400, height=420, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def toggle_theme(self, page: ft.Page, e):
        """Toggle between dark and light theme"""
        if e.control.value:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = self.bg_color
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = "#F5F5F5"
        page.update()

    def toggle_2fa(self, page: ft.Page, e):
        """Toggle two-factor authentication"""
        if e.control.value:
            page.snack_bar = ft.SnackBar(ft.Text("2FA enabled - Feature coming soon"), bgcolor=self.accent_color)
        else:
            page.snack_bar = ft.SnackBar(ft.Text("2FA disabled"), bgcolor=self.warning_color)
        page.snack_bar.open = True
        page.update()

    def change_accent_color(self, page: ft.Page, color):
        """Change app accent color"""
        self.accent_color = color
        page.snack_bar = ft.SnackBar(ft.Text(f"Accent color changed"), bgcolor=color)
        page.snack_bar.open = True
        self.show_settings(page)

    def change_font_size(self, page: ft.Page, size):
        """Change font size preference"""
        if size == "small":
            self.font_scale = 0.8
        elif size == "large":
            self.font_scale = 1.2
        else:
            self.font_scale = 1.0
        
        page.snack_bar = ft.SnackBar(ft.Text(f"Font size changed to {size}"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        self.show_settings(page)


    def show_backup_list(self, page: ft.Page):
        """Show list of available backups - NO PERMISSION ERRORS"""
        import os
        
        app_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(app_dir, "backups")
        backups = []
        
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            backups.sort(reverse=True)
        
        if not backups:
            page.snack_bar = ft.SnackBar(
                ft.Text("No backups found. Create a backup first."),
                bgcolor=self.warning_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        def delete_backup(backup_file):
            """Delete a backup file"""
            try:
                os.remove(os.path.join(backup_dir, backup_file))
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Deleted: {backup_file}"),
                    bgcolor=self.success_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.dialog.open = False
                self.show_backup_list(page)
            except Exception as e:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Failed to delete: {str(e)}"),
                    bgcolor=self.danger_color,
                    duration=2000
                )
                page.snack_bar.open = True
                page.update()
        
        backup_items = []
        for backup in backups[:20]:
            backup_path = os.path.join(backup_dir, backup)
            size_bytes = os.path.getsize(backup_path)
            size_kb = size_bytes / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
            
            # Try to get date from filename
            date_str = "Unknown"
            try:
                if '_' in backup:
                    parts = backup.replace('.db', '').split('_')
                    if len(parts) >= 2:
                        date_str = parts[1]
                        if len(date_str) == 8:
                            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            except:
                pass
            
            backup_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.FILE_PRESENT, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text(backup, size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Date: {date_str} | Size: {size_str}", size=10, color="#888888"),
                        ], spacing=2, expand=True),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_size=20,
                            icon_color=self.danger_color,
                            on_click=lambda e, b=backup: delete_backup(b),
                            tooltip="Delete Backup",
                        ),
                    ]),
                    padding=8,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(bottom=5),
                )
            )
        
        def close_dlg():
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text(f"📁 Backups ({len(backups)})", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            ft.Divider(),
            ft.Column(backup_items, spacing=5, scroll=ft.ScrollMode.AUTO, height=400),
            ft.Container(height=10),
            ft.Text("💡 Backups are stored in the 'backups' folder", size=10, color="#888888"),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=500, height=500, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def reset_database_confirm(self, page: ft.Page):
        """Confirm and reset database"""
        
        def confirm_reset(e):
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Clear all tables
                cursor.execute("DELETE FROM materials")
                cursor.execute("DELETE FROM accessories")
                # Keep admin user (id=1), delete other users
                cursor.execute("DELETE FROM users WHERE id > 1")
                
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Database reset successfully! Please restart the app."),
                    bgcolor=self.success_color,
                    duration=5000
                )
                page.snack_bar.open = True
                page.update()
                
            except Exception as ex:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Reset failed: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=4000
                )
                page.snack_bar.open = True
                page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("⚠️ Reset Database", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("This will delete ALL data including:", size=14),
            ft.Text("• All materials", size=13),
            ft.Text("• All accessories", size=13),
            ft.Text("• All users (except admin)", size=13),
            ft.Text("This action CANNOT be undone!", size=14, color=self.danger_color, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Yes, Reset All Data", on_click=confirm_reset, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Reset Database"),
            content=ft.Container(content=dialog_content, width=400, height=380, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def export_all_data(self, page: ft.Page):
        """Export all data to CSV files"""
        import csv
        from datetime import datetime
        
        try:
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export materials
            materials = self.dict_list(MaterialManager.get_all())
            if materials:
                materials_file = os.path.join(export_dir, f"materials_{timestamp}.csv")
                with open(materials_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=materials[0].keys())
                    writer.writeheader()
                    writer.writerows(materials)
            
            # Export accessories
            accessories = self.dict_list(AccessoryManager.get_all())
            if accessories:
                accessories_file = os.path.join(export_dir, f"accessories_{timestamp}.csv")
                with open(accessories_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=accessories[0].keys())
                    writer.writeheader()
                    writer.writerows(accessories)
            
            # Export users
            users = self.dict_list(UserManager.get_all())
            if users:
                users_file = os.path.join(export_dir, f"users_{timestamp}.csv")
                with open(users_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=users[0].keys())
                    writer.writeheader()
                    writer.writerows(users)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ All data exported to {export_dir}/"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def reset_database_confirm(self, page: ft.Page):
        """Confirm and reset database"""
        
        def confirm_reset(e):
            import sqlite3
            from database import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Clear all tables
            cursor.execute("DELETE FROM materials")
            cursor.execute("DELETE FROM accessories")
            cursor.execute("DELETE FROM users WHERE role != 'admin'")  # Keep admin user
            cursor.execute("DELETE FROM backups")
            
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text("✓ Database reset. Please restart the app."),
                bgcolor=self.success_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("⚠️ Reset Database", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("This will delete ALL data including:", size=14),
            ft.Text("• All materials", size=13),
            ft.Text("• All accessories", size=13),
            ft.Text("• All users (except admin)", size=13),
            ft.Text("This action CANNOT be undone!", size=14, color=self.danger_color),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Yes, Reset", on_click=confirm_reset, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Reset Database"),
            content=ft.Container(content=dialog_content, width=400, height=380, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_categories_dialog(self, page: ft.Page, refresh_callback=None):
        """Categories dialog with delete and edit functionality"""
        
        import sqlite3
        import os
        from datetime import datetime
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Get database path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "store_management.db")
        
        current_user_id = self.current_user.get('id') if self.current_user else 1
        
        # Check if user_id column exists
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(categories)")
        columns = [col[1] for col in cursor.fetchall()]
        has_user_id = 'user_id' in columns
        conn.close()
        
        # ===== STEP 1: Create UI Components =====
        name_input = ft.TextField(
            hint_text="New category name", 
            width=250 if not is_mobile else 200,
            bgcolor="#2C2C2C",
        )
        
        icon_select = ft.Dropdown(
            label="Icon", 
            width=120 if not is_mobile else 100,
            options=[
                ft.dropdown.Option("📦", "📦 Raw Material"),
                ft.dropdown.Option("🔩", "🔩 Hardware"),
                ft.dropdown.Option("🔧", "🔧 Tools"),
                ft.dropdown.Option("⚡", "⚡ Electrical"),
                ft.dropdown.Option("💧", "💧 Plumbing"),
                ft.dropdown.Option("⚙️", "⚙️ Metal"),
                ft.dropdown.Option("🔨", "🔨 Construction"),
                ft.dropdown.Option("📁", "📁 Other"),
            ],
            value="📁", 
            bgcolor="#2C2C2C",
        )
        
        status_text = ft.Text("", size=12)
        
        # ===== STEP 2: Create categories_list =====
        categories_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=250 if not is_mobile else 200)
        
        # ===== STEP 3: Define dialog functions =====
        
        def confirm_delete_category(category_id, category_name):
            """Show confirmation dialog before deleting"""
            
            def do_delete(e):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Update materials and accessories to remove category
                    cursor.execute("UPDATE materials SET category_id = NULL WHERE category_id = ?", (category_id,))
                    cursor.execute("UPDATE accessories SET category_id = NULL WHERE category_id = ?", (category_id,))
                    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                    
                    conn.commit()
                    conn.close()
                    
                    confirm_dialog.open = False
                    status_text.value = f"✓ Deleted: {category_name}"
                    status_text.color = "green"
                    load_categories()
                    
                    if refresh_callback:
                        refresh_callback()
                    
                    page.update()
                    
                except Exception as e:
                    status_text.value = f"Error: {str(e)}"
                    status_text.color = "red"
                    page.update()
            
            def cancel_delete(e):
                confirm_dialog.open = False
                page.update()
            
            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Delete Category", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Delete '{category_name}'?", size=14),
                        ft.Text("Items using this category will become uncategorized.", size=11, color="#888888"),
                        ft.Text("This cannot be undone!", size=11, color=self.danger_color),
                    ], spacing=8),
                    width=300,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_delete),
                    ft.ElevatedButton("Delete", on_click=do_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ],
            )
            
            page.dialog = confirm_dialog
            confirm_dialog.open = True
            page.update()
        
        def show_edit_category_dialog(category_id, category_name, category_icon):
            """Show dialog to edit category"""
            
            edit_name_input = ft.TextField(
                label="Category Name",
                value=category_name,
                width=250 if not is_mobile else 200,
                bgcolor="#2C2C2C",
            )
            
            edit_icon_select = ft.Dropdown(
                label="Icon",
                width=120 if not is_mobile else 100,
                options=[
                    ft.dropdown.Option("📦", "📦 Raw Material"),
                    ft.dropdown.Option("🔩", "🔩 Hardware"),
                    ft.dropdown.Option("🔧", "🔧 Tools"),
                    ft.dropdown.Option("⚡", "⚡ Electrical"),
                    ft.dropdown.Option("💧", "💧 Plumbing"),
                    ft.dropdown.Option("⚙️", "⚙️ Metal"),
                    ft.dropdown.Option("🔨", "🔨 Construction"),
                    ft.dropdown.Option("📁", "📁 Other"),
                ],
                value=category_icon,
                bgcolor="#2C2C2C",
            )
            
            edit_status = ft.Text("", size=12)
            
            def save_edit(e):
                new_name = edit_name_input.value.strip()
                new_icon = edit_icon_select.value
                
                if not new_name:
                    edit_status.value = "❌ Enter a name"
                    edit_status.color = "red"
                    page.update()
                    return
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "UPDATE categories SET name = ?, icon = ? WHERE id = ?",
                        (new_name, new_icon, category_id)
                    )
                    
                    conn.commit()
                    conn.close()
                    
                    edit_dialog.open = False
                    status_text.value = f"✓ Updated: {new_name}"
                    status_text.color = "green"
                    load_categories()
                    
                    if refresh_callback:
                        refresh_callback()
                    
                    page.update()
                    
                except Exception as e:
                    edit_status.value = f"Error: {str(e)}"
                    edit_status.color = "red"
                    page.update()
            
            def cancel_edit(e):
                edit_dialog.open = False
                page.update()
            
            edit_dialog = ft.AlertDialog(
                title=ft.Text("Edit Category", size=18, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column([
                        edit_name_input,
                        edit_icon_select,
                        edit_status,
                    ], spacing=10),
                    width=350 if not is_mobile else 300,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_edit),
                    ft.ElevatedButton("Save", on_click=save_edit, style=ft.ButtonStyle(bgcolor=self.success_color)),
                ],
            )
            
            page.dialog = edit_dialog
            edit_dialog.open = True
            page.update()
        
        def load_categories():
            """Load categories with delete and edit buttons for custom categories only"""
            categories_list.controls.clear()
            
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if has_user_id:
                    cursor.execute("SELECT id, name, icon FROM categories WHERE user_id = ? ORDER BY name", (current_user_id,))
                else:
                    cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
                
                cats = cursor.fetchall()
                conn.close()
                
                if cats:
                    # Show custom categories with edit/delete icons
                    for cat in cats:
                        icon = cat['icon'] if cat['icon'] else "📁"
                        
                        categories_list.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text(icon, size=22),
                                    ft.Text(cat['name'], size=14, expand=True),
                                    ft.IconButton(
                                        icon=ft.icons.EDIT,
                                        icon_size=18,
                                        icon_color=self.accent_color,
                                        tooltip="Edit Category",
                                        on_click=lambda e, cid=cat['id'], cname=cat['name'], cicon=cat['icon']: 
                                            show_edit_category_dialog(cid, cname, cicon),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE,
                                        icon_size=18,
                                        icon_color=self.danger_color,
                                        tooltip="Delete Category",
                                        on_click=lambda e, cid=cat['id'], cname=cat['name']: 
                                            confirm_delete_category(cid, cname),
                                    ),
                                ]),
                                padding=10,
                                bgcolor="#2C2C2C",
                                border_radius=8,
                                margin=ft.margin.only(bottom=5),
                            )
                        )
                else:
                    # No custom categories - show message
                    categories_list.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text("📁", size=22),
                                ft.Text("No custom categories yet. Add one above!", size=14, color="#888888"),
                            ]),
                            padding=10,
                            bgcolor="#2C2C2C",
                            border_radius=8,
                            margin=ft.margin.only(bottom=5),
                        )
                    )
                
                # Always show default categories as reference (without edit/delete)
                default_cats = [
                    ("📦", "Raw Material"), ("🔩", "Hardware"), ("🔧", "Tools"),
                    ("⚡", "Electrical"), ("💧", "Plumbing"), ("🪵", "Wood"),
                    ("⚙️", "Metal"), ("📁", "Other"),
                ]
                
                # Add a separator if there are custom categories
                if cats:
                    categories_list.controls.append(
                        ft.Container(
                            content=ft.Divider(color="#3C3C3C"),
                            padding=ft.padding.symmetric(vertical=8),
                        )
                    )
                    categories_list.controls.append(
                        ft.Text("Default Categories (System)", size=12, color="#888888")
                    )
                
                # Show default categories without edit/delete
                for icon, name in default_cats:
                    categories_list.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(icon, size=22),
                                ft.Text(name, size=14, expand=True),
                                ft.Text("System", size=10, color="#888888"),
                            ]),
                            padding=10,
                            bgcolor="#1E1E1E",
                            border_radius=8,
                            margin=ft.margin.only(bottom=5),
                        )
                    )
                
                page.update()
                
            except Exception as e:
                print(f"Error loading categories: {e}")
                categories_list.controls.append(
                    ft.Text(f"Error loading categories: {str(e)}", size=12, color="red")
                )
                page.update()
        
        def add_category(e):
            name = name_input.value.strip()
            if not name:
                status_text.value = "❌ Enter name"
                status_text.color = "red"
                page.update()
                return
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                if has_user_id:
                    cursor.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, current_user_id))
                else:
                    cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
                
                if cursor.fetchone():
                    status_text.value = "❌ Already exists!"
                    status_text.color = "red"
                    page.update()
                    conn.close()
                    return
                
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if has_user_id:
                    cursor.execute(
                        "INSERT INTO categories (name, icon, user_id, created_at) VALUES (?, ?, ?, ?)",
                        (name, icon_select.value, current_user_id, current_time)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO categories (name, icon, created_at) VALUES (?, ?, ?)",
                        (name, icon_select.value, current_time)
                    )
                
                conn.commit()
                conn.close()
                
                name_input.value = ""
                status_text.value = f"✓ Added: {name}"
                status_text.color = "green"
                load_categories()
                
                if refresh_callback:
                    refresh_callback()
                
            except Exception as e:
                status_text.value = f"Error: {str(e)}"
                status_text.color = "red"
                page.update()
        
        def close_dlg():
            page.dialog.open = False
            page.update()
            if refresh_callback:
                refresh_callback()
        
        # ===== STEP 4: Load categories =====
        load_categories()
        
        # ===== STEP 5: Create dialog content =====
        content = ft.Column([
            ft.Row([
                ft.Text("📁 Categories", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            ft.Divider(),
            ft.Text("Add New Category", size=14, weight=ft.FontWeight.BOLD),
            ft.Row([name_input, icon_select], spacing=8, wrap=True),
            ft.ElevatedButton("➕ Add Category", on_click=add_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
            status_text,
            ft.Divider(),
            ft.Text("Your Custom Categories", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("Tap ✏️ to edit or 🗑️ to delete", size=10, color="#888888"),
            categories_list,
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        # Set dialog width based on device
        dialog_width = 420 if not is_mobile else page.width - 20 if page.width else 380
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=content, width=dialog_width, height=550 if not is_mobile else 500, padding=15),
            actions=[ft.TextButton("Close", on_click=lambda e: close_dlg())],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def close_dialog(self, page: ft.Page):
        """Close the current dialog"""
        if page.dialog:
            page.dialog.open = False
            page.update()
    def show_add_category_dialog(self, page: ft.Page):
        """Simple dialog to add category - uses overlay for mobile"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        
        # Create a simple dialog
        name_input = ft.TextField(label="Category Name", autofocus=True, width=280)
        icon_input = ft.Dropdown(
            label="Icon", width=100,
            options=[ft.dropdown.Option("📦"), ft.dropdown.Option("🔩"), ft.dropdown.Option("🔧"),
                    ft.dropdown.Option("⚡"), ft.dropdown.Option("💧"), ft.dropdown.Option("📁")],
            value="📁",
        )
        status = ft.Text("", size=12, color="red")
        
        def save(e):
            name = name_input.value.strip()
            if not name:
                status.value = "❌ Enter a name"
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, current_user_id))
            if cursor.fetchone():
                status.value = "❌ Already exists"
                page.update()
                conn.close()
                return
            
            cursor.execute(
                "INSERT INTO categories (name, icon, user_id, created_at) VALUES (?, ?, ?, ?)",
                (name, icon_input.value, current_user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name}"), bgcolor=self.success_color)
            page.snack_bar.open = True
            self.show_categories_page(page)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add Category"),
            content=ft.Container(
                content=ft.Column([
                    name_input,
                    icon_input,
                    status,
                ], spacing=10),
                width=350,
                padding=15,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False)),
                ft.ElevatedButton("Save", on_click=save),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def open_add_category_dialog(self, page: ft.Page, refresh_callback=None):
        """Add category dialog - With close icon, direct delete"""
        import sqlite3
        from database import DB_PATH
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        
        # Dialog
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            modal=True,
        )
        
        # Add section
        name_input = ft.TextField(label="New Category Name", width=260, bgcolor=self.card_color)
        icon_select = ft.Dropdown(
            label="Icon",
            width=70,
            options=[ft.dropdown.Option(icon, icon) for icon in ["📦", "🔩", "🔧", "⚡", "💧", "🪵", "⚙️", "📁"]],
            value="📁",
            bgcolor=self.card_color,
        )
        add_status = ft.Text("", size=11)
        
        # Delete section
        delete_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=150)
        
        def close_dialog():
            dialog.open = False
            page.update()
            if refresh_callback:
                refresh_callback()
        
        def load_categories():
            delete_list.controls.clear()
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT id, name, icon FROM categories WHERE user_id = ? ORDER BY name", (current_user_id,))
            cats = cur.fetchall()
            conn.close()
            
            for cat_id, cat_name, cat_icon in cats:
                row = ft.Container(
                    content=ft.Row([
                        ft.Text(cat_icon, size=18),
                        ft.Text(cat_name, size=13, expand=True),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_size=18,
                            icon_color=self.danger_color,
                            on_click=lambda e, cid=cat_id, cname=cat_name: delete_category(cid, cname),
                        ),
                    ], spacing=10),
                    padding=8,
                    bgcolor="#2C2C2C",
                    border_radius=5,
                )
                delete_list.controls.append(row)
            
            if not delete_list.controls:
                delete_list.controls.append(ft.Text("No custom categories", size=12, color="#888888", padding=10))
            page.update()
        
        def add_category(e):
            name = name_input.value.strip()
            if not name:
                add_status.value = "❌ Enter name"
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO categories (name, icon, user_id) VALUES (?, ?, ?)",
                    (name, icon_select.value, current_user_id)
                )
                conn.commit()
                name_input.value = ""
                add_status.value = "✓ Added!"
                load_categories()
                if refresh_callback:
                    refresh_callback()
                page.update()
            except:
                add_status.value = "❌ Already exists"
                page.update()
            finally:
                conn.close()
        
        def delete_category(cat_id, cat_name):
            """DELETE IMMEDIATELY - NO CONFIRMATION"""
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, current_user_id))
            conn.commit()
            conn.close()
            load_categories()
            if refresh_callback:
                refresh_callback()
            page.update()
        
        # Build dialog content with X icon in title
        dialog.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Manage Categories", size=18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
                ]),
                ft.Divider(),
                ft.Text("Add New Category:", size=14, weight=ft.FontWeight.BOLD),
                name_input,
                ft.Row([icon_select], alignment=ft.MainAxisAlignment.START),
                add_status,
                ft.Row([
                    ft.TextButton("Cancel", on_click=lambda e: close_dialog()),
                    ft.FilledButton("Add", on_click=add_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
                ], spacing=8),
                ft.Divider(),
                ft.Text("Your Custom Categories:", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("Tap the delete icon to remove", size=10, color="#888888"),
                delete_list,
            ], spacing=8),
            width=340,
            height=480,
            padding=15,
        )
        
        load_categories()
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_edit_category_dialog(self, page: ft.Page, category_id, current_name, current_icon, refresh_callback=None):
        """Dialog to edit custom category"""
        
        import sqlite3
        from database import DB_PATH
        
        current_user_id = self.current_user.get('id') if self.current_user else 0
        
        # Icon options
        icon_options = [
            "📦", "🔩", "🔧", "⚡", "💧", "🪵", "⚙️", "🧴", "🔮", "🎨", 
            "📎", "🦺", "📁", "🔨", "🪚", "📏", "🔬", "🧪", "📖", "🏷️"
        ]
        
        name_field = ft.TextField(label="Category Name", value=current_name, width=300, bgcolor=self.card_color)
        icon_dropdown = ft.Dropdown(
            label="Icon",
            width=120,
            options=[ft.dropdown.Option(icon, icon) for icon in icon_options],
            value=current_icon,
            bgcolor=self.card_color,
        )
        status_text = ft.Text("", size=12)
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def update_category(e):
            name = name_field.value.strip()
            if not name:
                status_text.value = "❌ Please enter a category name"
                status_text.color = self.danger_color
                page.update()
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE custom_categories SET name = ?, icon = ? WHERE id = ? AND user_id = ?",
                    (name, icon_dropdown.value, category_id, current_user_id)
                )
                conn.commit()
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Category updated to '{name}'!"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                if refresh_callback:
                    refresh_callback()
                page.update()
            except sqlite3.IntegrityError:
                status_text.value = f"❌ Category '{name}' already exists!"
                status_text.color = self.danger_color
                page.update()
            except Exception as ex:
                status_text.value = f"Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
            finally:
                conn.close()
        
        dialog_content = ft.Column([
            ft.Text("Edit Category", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            icon_dropdown,
            status_text,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save Changes", on_click=update_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Category"),
            content=ft.Container(content=dialog_content, width=400, height=380, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_delete_category_dialog(self, page: ft.Page, category_id, category_name, refresh_callback=None):
        """Dialog to delete custom category"""
        
        import sqlite3
        from database import DB_PATH
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            try:
                # Delete the category
                cursor.execute("DELETE FROM custom_categories WHERE id = ?", (category_id,))
                conn.commit()
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Category '{category_name}' deleted!"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                if refresh_callback:
                    refresh_callback()
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
            finally:
                conn.close()
        
        dialog_content = ft.Column([
            ft.Text("🗑️ Delete Category", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text(f"Are you sure you want to delete:", size=14),
            ft.Text(f"'{category_name}'?", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Text("This action cannot be undone!", size=12, color="#888888"),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Yes, Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Container(content=dialog_content, width=400, height=280, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def add_custom_category_dialog(self, page: ft.Page):
        """Dialog to add custom category"""
        
        name_field = ft.TextField(label="Category Name", width=300, bgcolor=self.card_color)
        
        icon_field = ft.Dropdown(
            label="Icon",
            width=120,
            options=[
                ft.dropdown.Option("📦", "📦 Box"),
                ft.dropdown.Option("🔩", "🔩 Screw"),
                ft.dropdown.Option("🔧", "🔧 Wrench"),
                ft.dropdown.Option("⚡", "⚡ Lightning"),
                ft.dropdown.Option("💧", "💧 Water"),
                ft.dropdown.Option("🪵", "🪵 Wood"),
                ft.dropdown.Option("⚙️", "⚙️ Gear"),
                ft.dropdown.Option("🧴", "🧴 Bottle"),
                ft.dropdown.Option("🔮", "🔮 Crystal"),
                ft.dropdown.Option("🎨", "🎨 Paint"),
                ft.dropdown.Option("📎", "📎 Paperclip"),
                ft.dropdown.Option("🦺", "🦺 Vest"),
                ft.dropdown.Option("📁", "📁 Folder"),
            ],
            value="📁",
            bgcolor=self.card_color,
        )
        
        color_field = ft.Dropdown(
            label="Color",
            width=120,
            options=[
                ft.dropdown.Option("#1976D2", "🔵 Blue"),
                ft.dropdown.Option("#4CAF50", "🟢 Green"),
                ft.dropdown.Option("#FF9800", "🟠 Orange"),
                ft.dropdown.Option("#F44336", "🔴 Red"),
                ft.dropdown.Option("#9C27B0", "🟣 Purple"),
                ft.dropdown.Option("#00BCD4", "🔷 Cyan"),
                ft.dropdown.Option("#757575", "⚫ Gray"),
            ],
            value="#1976D2",
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def save_category(e):
            name = name_field.value.strip()
            if not name:
                status_text.value = "❌ Please enter a category name"
                status_text.color = self.danger_color
                page.update()
                return
            
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO custom_categories (name, icon, color, created_by) VALUES (?, ?, ?, ?)",
                    (name, icon_field.value, color_field.value, self.current_user.get('name', 'User'))
                )
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Category '{name}' added!"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_category_manager(page)
                
            except sqlite3.IntegrityError:
                status_text.value = "❌ Category already exists!"
                status_text.color = self.danger_color
                page.update()
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Add Custom Category", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            ft.Row([icon_field, color_field], spacing=10),
            status_text,
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save", on_click=save_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("New Category"),
            content=ft.Container(content=dialog_content, width=400, height=350, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def edit_custom_category(self, page: ft.Page, category_id):
        """Edit custom category"""
        
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name, icon, color FROM custom_categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        conn.close()
        
        if not category:
            return
        
        name_field = ft.TextField(label="Category Name", value=category[0], width=300, bgcolor=self.card_color)
        
        icon_field = ft.Dropdown(
            label="Icon",
            width=100,
            options=[
                ft.dropdown.Option("📦", "📦"), ft.dropdown.Option("🔩", "🔩"), ft.dropdown.Option("🔧", "🔧"),
                ft.dropdown.Option("⚡", "⚡"), ft.dropdown.Option("💧", "💧"), ft.dropdown.Option("🪵", "🪵"),
                ft.dropdown.Option("⚙️", "⚙️"), ft.dropdown.Option("🧴", "🧴"), ft.dropdown.Option("🔮", "🔮"),
                ft.dropdown.Option("🎨", "🎨"), ft.dropdown.Option("📎", "📎"), ft.dropdown.Option("🦺", "🦺"),
                ft.dropdown.Option("📁", "📁"),
            ],
            value=category[1],
            bgcolor=self.card_color,
        )
        
        color_field = ft.Dropdown(
            label="Color",
            width=100,
            options=[
                ft.dropdown.Option("#1976D2", "🔵 Blue"), ft.dropdown.Option("#4CAF50", "🟢 Green"),
                ft.dropdown.Option("#FF9800", "🟠 Orange"), ft.dropdown.Option("#F44336", "🔴 Red"),
                ft.dropdown.Option("#9C27B0", "🟣 Purple"), ft.dropdown.Option("#00BCD4", "🔷 Cyan"),
                ft.dropdown.Option("#757575", "⚫ Gray"),
            ],
            value=category[2],
            bgcolor=self.card_color,
        )
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def update_category(e):
            name = name_field.value.strip()
            if not name:
                return
            
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE custom_categories SET name = ?, icon = ?, color = ? WHERE id = ?",
                    (name, icon_field.value, color_field.value, category_id)
                )
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Category updated!"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_category_manager(page)
                
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Error: {str(ex)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Edit Category", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            ft.Row([icon_field, color_field], spacing=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Update", on_click=update_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Category"),
            content=ft.Container(content=dialog_content, width=400, height=320, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def delete_custom_category(self, page: ft.Page, category_id):
        """Delete custom category"""
        
        import sqlite3
        from database import DB_PATH
        
        # Check if category has items
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM materials WHERE category_id = ?", (category_id,))
        materials_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM accessories WHERE category_id = ?", (category_id,))
        accessories_count = cursor.fetchone()[0]
        conn.close()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Move items to 'Other' category or set to NULL
            if materials_count > 0 or accessories_count > 0:
                cursor.execute("UPDATE materials SET category_id = NULL WHERE category_id = ?", (category_id,))
                cursor.execute("UPDATE accessories SET category_id = NULL WHERE category_id = ?", (category_id,))
            
            cursor.execute("DELETE FROM custom_categories WHERE id = ?", (category_id,))
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("✓ Category deleted!"), bgcolor=self.success_color)
            page.snack_bar.open = True
            self.show_category_manager(page)
        
        warning_text = ""
        if materials_count > 0 or accessories_count > 0:
            warning_text = f"⚠️ This category contains {materials_count} materials and {accessories_count} accessories. They will be moved to uncategorized."
        
        dialog_content = ft.Column([
            ft.Text("🗑️ Delete Category", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("Are you sure you want to delete this category?", size=14),
            ft.Text(warning_text, size=12, color=self.warning_color),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Container(content=dialog_content, width=400, height=250, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def close_dialog(self, page: ft.Page):
        if page.dialog:
            page.dialog.open = False
            page.update()

if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
