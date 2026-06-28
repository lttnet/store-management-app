# firebase_config.py - Add this new file

import os
import json
from firebase_admin import credentials, auth, initialize_app

class FirebaseAuth:
    """Firebase Authentication for Google Sign-In"""
    
    def __init__(self):
        self.app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Try to get credentials from environment (GitHub Actions)
            if os.environ.get('FIREBASE_CREDENTIALS'):
                cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
                cred = credentials.Certificate(cred_dict)
                self.app = initialize_app(cred)
                print("✅ Firebase initialized from environment")
                return
            
            # Fallback: use service account file
            cred_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                self.app = initialize_app(cred)
                print("✅ Firebase initialized from serviceAccountKey.json")
                return
            
            print("⚠️ Firebase credentials not found")
            
        except Exception as e:
            print(f"Firebase initialization error: {e}")
    
    def verify_google_token(self, id_token):
        """Verify Google ID token"""
        try:
            if not self.app:
                return None
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def create_user(self, email, name, uid=None):
        """Create a user in Firebase Auth"""
        try:
            if not self.app:
                return None
            
            user_args = {
                'email': email,
                'display_name': name,
                'email_verified': True
            }
            if uid:
                user_args['uid'] = uid
            
            user = auth.create_user(**user_args)
            return user
        except Exception as e:
            print(f"Create user error: {e}")
            return None
