# firebase_client.py - Updated with auto-creation

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
    
    def _ensure_company_exists(self, company_id):
        """Ensure company document exists in Firestore"""
        try:
            url = self._get_url(f"companies/{company_id}")
            response = requests.get(url)
            
            if response.status_code == 404:
                # Create company document
                company_data = {
                    "fields": {
                        "id": {"integerValue": str(company_id)},
                        "name": {"stringValue": f"Company {company_id}"},
                        "created_at": {"stringValue": datetime.now().isoformat()}
                    }
                }
                create_response = requests.patch(url, json=company_data)
                return create_response.status_code in [200, 201]
            return True
        except Exception as e:
            print(f"Error ensuring company exists: {e}")
            return False
    
    def _ensure_collection_exists(self, company_id, collection_name):
        """Ensure a collection exists under a company"""
        try:
            # Ensure company exists first
            if not self._ensure_company_exists(company_id):
                return False
            
            # Try to create a test document in the collection
            url = self._get_url(f"companies/{company_id}/{collection_name}/_init_")
            
            # Check if collection exists by trying to get it
            check_url = self._get_url(f"companies/{company_id}/{collection_name}")
            response = requests.get(check_url)
            
            if response.status_code == 404:
                # Collection doesn't exist, create a placeholder
                init_data = {
                    "fields": {
                        "init": {"stringValue": "true"},
                        "created_at": {"stringValue": datetime.now().isoformat()}
                    }
                }
                create_response = requests.patch(url, json=init_data)
                if create_response.status_code in [200, 201]:
                    print(f"✅ Created collection: {collection_name} for company {company_id}")
                    # Delete the init document
                    requests.delete(url)
                    return True
                return False
            return True
        except Exception as e:
            print(f"Error ensuring collection exists: {e}")
            return False
    
    # ============================================================
    # MATERIAL METHODS (Existing)
    # ============================================================
    
    def sync_material(self, company_id, material_data):
        """Sync a single material to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            # Ensure company and materials collection exist
            if not self._ensure_company_exists(company_id):
                return False
            if not self._ensure_collection_exists(company_id, "materials"):
                return False
            
            material_id = material_data.get('id')
            if not material_id:
                print("❌ No material ID provided")
                return False
            
            url = self._get_url(f"companies/{company_id}/materials/{material_id}")
            
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
                return False
                
        except Exception as e:
            print(f"Sync material error: {e}")
            return False
    
    # ============================================================
    # ACCESSORY METHODS (Existing)
    # ============================================================
    
    def sync_accessory(self, company_id, accessory_data):
        """Sync a single accessory to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            # Ensure company and accessories collection exist
            if not self._ensure_company_exists(company_id):
                return False
            if not self._ensure_collection_exists(company_id, "accessories"):
                return False
            
            accessory_id = accessory_data.get('id')
            if not accessory_id:
                print("❌ No accessory ID provided")
                return False
            
            url = self._get_url(f"companies/{company_id}/accessories/{accessory_id}")
            
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
                return False
                
        except Exception as e:
            print(f"Sync accessory error: {e}")
            return False
    
    # ============================================================
    # USER METHODS (Existing)
    # ============================================================
    
    def sync_user(self, company_id, user_data):
        """Sync a single user to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            # Ensure company and users collection exist
            if not self._ensure_company_exists(company_id):
                return False
            if not self._ensure_collection_exists(company_id, "users"):
                return False
            
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
    # ACTIVATION CODE METHODS (NEW - Auto Creates Collection)
    # ============================================================
    
    def sync_activation_codes(self, company_id, codes):
        """Sync activation codes to Firebase - Auto creates collection"""
        if not self.is_ready():
            return False
        
        try:
            # Ensure company exists
            if not self._ensure_company_exists(company_id):
                print("❌ Failed to ensure company exists")
                return False
            
            # Ensure activation_codes collection exists
            if not self._ensure_collection_exists(company_id, "activation_codes"):
                print("❌ Failed to ensure activation_codes collection exists")
                return False
            
            url = self._get_url(f"companies/{company_id}/activation_codes/codes")
            
            # Convert codes to serializable format
            codes_data = []
            for code in codes:
                codes_data.append({
                    'code': code.get('code', ''),
                    'customer_name': code.get('customer_name', ''),
                    'customer_email': code.get('customer_email', ''),
                    'company_name': code.get('company_name', ''),
                    'is_used': code.get('is_used', 0),
                    'device_id': code.get('device_id', ''),
                    'activated_at': code.get('activated_at', ''),
                    'created_at': code.get('created_at', '')
                })
            
            # Create document
            document = {
                "fields": {
                    "codes": {"stringValue": json.dumps(codes_data)},
                    "last_sync": {"stringValue": datetime.now().isoformat()},
                    "total_codes": {"integerValue": str(len(codes_data))}
                }
            }
            
            print(f"📤 Syncing {len(codes_data)} activation codes to Firebase...")
            response = requests.patch(url, json=document)
            
            if response.status_code in [200, 201]:
                print(f"✅ Synced {len(codes_data)} activation codes to Firebase")
                return True
            else:
                print(f"❌ Failed to sync activation codes: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"Sync activation codes error: {e}")
            return False
    
    def get_activation_codes(self, company_id):
        """Get activation codes from Firebase"""
        if not self.is_ready():
            return []
        
        try:
            url = self._get_url(f"companies/{company_id}/activation_codes/codes")
            response = requests.get(url)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            fields = data.get('fields', {})
            
            if 'codes' in fields and 'stringValue' in fields['codes']:
                codes_data = json.loads(fields['codes']['stringValue'])
                print(f"✅ Downloaded {len(codes_data)} activation codes from Firebase")
                return codes_data
            return []
        except Exception as e:
            print(f"Get activation codes error: {e}")
            return []
    
    def sync_single_activation_code(self, company_id, code_data):
        """Sync a single activation code to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            # Get existing codes
            existing_codes = self.get_activation_codes(company_id)
            
            # Update or add the code
            code_found = False
            for i, code in enumerate(existing_codes):
                if code.get('code') == code_data.get('code'):
                    existing_codes[i] = code_data
                    code_found = True
                    break
            
            if not code_found:
                existing_codes.append(code_data)
            
            # Sync all codes back
            return self.sync_activation_codes(company_id, existing_codes)
            
        except Exception as e:
            print(f"Sync single activation code error: {e}")
            return False

# Create singleton instance
firebase_api = FirebaseRestAPI()
