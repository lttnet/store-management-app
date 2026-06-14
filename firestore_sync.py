# firestore_sync.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import base64

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
            cred = None
            
            # Option 1: From GitHub Secret (base64 encoded)
            firebase_key = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
            if firebase_key:
                try:
                    # Decode from base64
                    decoded = base64.b64decode(firebase_key).decode('utf-8')
                    cred_dict = json.loads(decoded)
                    cred = credentials.Certificate(cred_dict)
                    print("✅ Firebase initialized from GitHub Secret")
                except Exception as e:
                    print(f"Failed to decode GitHub secret: {e}")
            
            # Option 2: From local file (development only)
            if not cred and os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                print("✅ Firebase initialized from local file")
            
            if cred:
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.initialized = True
                print("✅ Connected to Firestore Cloud!")
            else:
                print("⚠️ No Firebase credentials found, using local files")
                self.initialized = False
                
        except Exception as e:
            print(f"Firestore error: {e}")
            self.initialized = False
    
    def is_ready(self):
        return self.initialized and self.db is not None
    
    # Add your sync methods here...

firestore_sync = FirestoreSync()
