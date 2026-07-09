# firebase_client.py
import requests
import os
import json
from datetime import datetime

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
    # USER METHODS
    # ============================================================
    
    def sync_user(self, company_id, user_data):
        """Sync a single user to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            user_id = user_data.get('id')
            if not user_id:
                print("❌ No user ID provided")
                return False
            
            url = self._get_url(f"companies/{company_id}/users/{user_id}")
            
            document = {
                "fields": {
                    "id": {"integerValue": str(user_id)},
                    "name": {"stringValue": str(user_data.get('name', ''))},
                    "email": {"stringValue": str(user_data.get('email', ''))},
                    "role": {"stringValue": str(user_data.get('role', 'user'))},
                    "company_id": {"integerValue": str(company_id)},
                    "synced_at": {"stringValue": datetime.now().isoformat()}
                }
            }
            
            response = requests.patch(url, json=document)
            
            if response.status_code in [200, 201]:
                print(f"  ✅ Synced user {user_id}: {user_data.get('name')}")
                return True
            else:
                print(f"  ❌ Failed to sync user {user_id}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Sync user error: {e}")
            return False
    
    def delete_user(self, company_id, user_id):
        """Delete a user from Firebase"""
        if not self.is_ready():
            return False
        
        try:
            url = self._get_url(f"companies/{company_id}/users/{user_id}")
            response = requests.delete(url)
            
            if response.status_code in [200, 204]:
                print(f"  ✅ Deleted user {user_id} from cloud")
                return True
            else:
                print(f"  ❌ Failed to delete user {user_id}: {response.status_code}")
                return False
        except Exception as e:
            print(f"Delete user error: {e}")
            return False
    
    def get_users(self, company_id):
        """Get all users from Firebase"""
        if not self.is_ready():
            return []
        
        try:
            url = self._get_url(f"companies/{company_id}/users")
            response = requests.get(url)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            users = []
            
            for doc in data.get('documents', []):
                doc_id = doc['name'].split('/')[-1]
                fields = doc.get('fields', {})
                
                user = {
                    'id': int(doc_id),
                    'name': fields.get('name', {}).get('stringValue', ''),
                    'email': fields.get('email', {}).get('stringValue', ''),
                    'role': fields.get('role', {}).get('stringValue', 'user'),
                    'company_id': int(fields.get('company_id', {}).get('integerValue', company_id))
                }
                users.append(user)
            
            print(f"✅ Downloaded {len(users)} users from Firebase")
            return users
            
        except Exception as e:
            print(f"Get users error: {e}")
            return []
    
    # ============================================================
    # MATERIAL METHODS
    # ============================================================
    
    def sync_material(self, company_id, material_data):
        """Sync a single material to Firebase - FIXED to handle all fields"""
        if not self.is_ready():
            return False
        
        try:
            material_id = material_data.get('id')
            if not material_id:
                print("❌ No material ID provided")
                return False
            
            url = self._get_url(f"companies/{company_id}/materials/{material_id}")
            
            # Debug: Print what we're syncing
            print(f"  📤 Syncing material {material_id}: {material_data.get('name')}")
            print(f"     Quantity: {material_data.get('quantity')}")
            print(f"     Quality: {material_data.get('quality')}")
            print(f"     Location: {material_data.get('location_ids')}")
            
            # Build document with all fields
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
            
            # Send to Firebase
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
                }
                materials.append(material)
            
            print(f"✅ Downloaded {len(materials)} materials from Firebase")
            return materials
            
        except Exception as e:
            print(f"Get materials error: {e}")
            return []
    
    # ============================================================
    # ACCESSORY METHODS
    # ============================================================
    
    def sync_accessory(self, company_id, accessory_data):
        """Sync a single accessory to Firebase - FIXED to handle all fields"""
        if not self.is_ready():
            return False
        
        try:
            accessory_id = accessory_data.get('id')
            if not accessory_id:
                print("❌ No accessory ID provided")
                return False
            
            url = self._get_url(f"companies/{company_id}/accessories/{accessory_id}")
            
            # Debug: Print what we're syncing
            print(f"  📤 Syncing accessory {accessory_id}: {accessory_data.get('name')}")
            print(f"     Quantity: {accessory_data.get('quantity')}")
            print(f"     Price: {accessory_data.get('price')}")
            print(f"     Location: {accessory_data.get('location')}")
            
            # Build document with all fields
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
            
            # Send to Firebase
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
                }
                accessories.append(accessory)
            
            print(f"✅ Downloaded {len(accessories)} accessories from Firebase")
            return accessories
            
        except Exception as e:
            print(f"Get accessories error: {e}")
            return []

# Create singleton instance
firebase_api = FirebaseRestAPI()
