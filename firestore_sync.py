# firestore_sync.py - Real Firestore cloud sync
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
            # Check for service account key
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
                print("⚠️ No Firebase credentials found. Using local mode.")
                self.initialized = False
        except Exception as e:
            print(f"Firestore error: {e}")
            self.initialized = False
    
    def is_ready(self):
        return self.initialized and self.db is not None
    
    def sync_users_to_firestore(self, company_id, users):
        """Sync users to Firestore (real cloud)"""
        if not self.is_ready():
            return False
        
        try:
            company_ref = self.db.collection('companies').document(str(company_id))
            batch = self.db.batch()
            
            # First, get existing users in Firestore to handle deletions
            existing_users = {}
            users_ref = company_ref.collection('users')
            docs = users_ref.stream()
            for doc in docs:
                existing_users[int(doc.id)] = doc.to_dict()
            
            # Track changes
            current_user_ids = set()
            
            # Add/update users
            for user in users:
                user_id = user.get('id')
                current_user_ids.add(user_id)
                user_ref = users_ref.document(str(user_id))
                batch.set(user_ref, user)
            
            # Delete users that no longer exist locally
            for existing_id in existing_users:
                if existing_id not in current_user_ids:
                    user_ref = users_ref.document(str(existing_id))
                    batch.delete(user_ref)
                    print(f"  Deleted user ID {existing_id} from Firestore")
            
            batch.commit()
            print(f"✅ Synced {len(users)} users to Firestore Cloud!")
            return True
        except Exception as e:
            print(f"Sync to Firestore error: {e}")
            return False
    
    def get_users_from_firestore(self, company_id):
        """Get users from Firestore (real cloud)"""
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
            
            print(f"✅ Downloaded {len(users)} users from Firestore Cloud")
            return users
        except Exception as e:
            print(f"Get from Firestore error: {e}")
            return []

# Create global instance
firestore_sync = FirestoreSync()