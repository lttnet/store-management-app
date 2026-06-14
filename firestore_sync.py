# firestore_sync.py - Complete with materials and accessories
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime

class FirestoreSync:
    _instance = None
    db = None
    initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirestoreSync, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        try:
            if os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.initialized = True
                print("✅ Connected to Firestore Cloud!")
            elif os.path.exists("google-services.json"):
                firebase_admin.initialize_app()
                self.db = firestore.client()
                self.initialized = True
                print("✅ Connected to Firestore Cloud!")
            else:
                print("⚠️ No Firebase credentials found")
                self.initialized = False
        except Exception as e:
            print(f"Firestore error: {e}")
            self.initialized = False
    
    def is_ready(self):
        return self.initialized and self.db is not None
    
    # ============ USERS SYNC ============
    def sync_users_to_firestore(self, company_id, users):
        """Sync users to Firestore"""
        if not self.is_ready():
            return False
        
        try:
            company_ref = self.db.collection('companies').document(str(company_id))
            batch = self.db.batch()
            
            # Get existing users to handle deletions
            existing_users = {}
            users_ref = company_ref.collection('users')
            docs = users_ref.stream()
            for doc in docs:
                existing_users[int(doc.id)] = doc.to_dict()
            
            current_user_ids = set()
            
            for user in users:
                user_id = user.get('id')
                current_user_ids.add(user_id)
                user_ref = users_ref.document(str(user_id))
                batch.set(user_ref, user)
            
            for existing_id in existing_users:
                if existing_id not in current_user_ids:
                    user_ref = users_ref.document(str(existing_id))
                    batch.delete(user_ref)
            
            batch.commit()
            print(f"✅ Synced {len(users)} users to Firestore")
            return True
        except Exception as e:
            print(f"Sync users error: {e}")
            return False
    
    def get_users_from_firestore(self, company_id):
        """Get users from Firestore"""
        if not self.is_ready():
            return []
        
        try:
            company_ref = self.db.collection('companies').document(str(company_id))
            users_ref = company_ref.collection('users')
            docs = users_ref.stream()
            
            users = []
            for doc in docs:
                user = doc.to_dict()
                user['id'] = int(doc.id)
                users.append(user)
            
            return users
        except Exception as e:
            print(f"Get users error: {e}")
            return []
    
    # ============ MATERIALS SYNC ============
    def sync_materials_to_firestore(self, company_id, materials):
        """Sync materials to Firestore"""
        if not self.is_ready():
            return False
        
        try:
            company_ref = self.db.collection('companies').document(str(company_id))
            batch = self.db.batch()
            
            # Get existing materials to handle deletions
            existing_materials = {}
            materials_ref = company_ref.collection('materials')
            docs = materials_ref.stream()
            for doc in docs:
                existing_materials[int(doc.id)] = doc.to_dict()
            
            current_material_ids = set()
            
            for material in materials:
                material_id = material.get('id')
                current_material_ids.add(material_id)
                material_ref = materials_ref.document(str(material_id))
                batch.set(material_ref, material)
            
            for existing_id in existing_materials:
                if existing_id not in current_material_ids:
                    material_ref = materials_ref.document(str(existing_id))
                    batch.delete(material_ref)
            
            batch.commit()
            print(f"✅ Synced {len(materials)} materials to Firestore")
            return True
        except Exception as e:
            print(f"Sync materials error: {e}")
            return False
    
    def get_materials_from_firestore(self, company_id):
        """Get materials from Firestore"""
        if not self.is_ready():
            return []
        
        try:
            company_ref = self.db.collection('companies').document(str(company_id))
            materials_ref = company_ref.collection('materials')
            docs = materials_ref.stream()
            
            materials = []
            for doc in docs:
                material = doc.to_dict()
                material['id'] = int(doc.id)
                materials.append(material)
            
            return materials
        except Exception as e:
            print(f"Get materials error: {e}")
            return []
    
    # ============ ACCESSORIES SYNC ============
    def sync_accessories_to_firestore(self, company_id, accessories):
        """Sync accessories to Firestore"""
        if not self.is_ready():
            return False
        
        try:
            company_ref = self.db.collection('companies').document(str(company_id))
            batch = self.db.batch()
            
            # Get existing accessories to handle deletions
            existing_accessories = {}
            accessories_ref = company_ref.collection('accessories')
            docs = accessories_ref.stream()
            for doc in docs:
                existing_accessories[int(doc.id)] = doc.to_dict()
            
            current_accessory_ids = set()
            
            for accessory in accessories:
                accessory_id = accessory.get('id')
                current_accessory_ids.add(accessory_id)
                accessory_ref = accessories_ref.document(str(accessory_id))
                batch.set(accessory_ref, accessory)
            
            for existing_id in existing_accessories:
                if existing_id not in current_accessory_ids:
                    accessory_ref = accessories_ref.document(str(existing_id))
                    batch.delete(accessory_ref)
            
            batch.commit()
            print(f"✅ Synced {len(accessories)} accessories to Firestore")
            return True
        except Exception as e:
            print(f"Sync accessories error: {e}")
            return False
    
    def get_accessories_from_firestore(self, company_id):
        """Get accessories from Firestore"""
        if not self.is_ready():
            return []
        
        try:
            company_ref = self.db.collection('companies').document(str(company_id))
            accessories_ref = company_ref.collection('accessories')
            docs = accessories_ref.stream()
            
            accessories = []
            for doc in docs:
                accessory = doc.to_dict()
                accessory['id'] = int(doc.id)
                accessories.append(accessory)
            
            return accessories
        except Exception as e:
            print(f"Get accessories error: {e}")
            return []

# Create global instance
firestore_sync = FirestoreSync()
