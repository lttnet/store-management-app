# firebase_rest.py
import requests
import json
import os

class FirebaseRestAPI:
    def __init__(self):
        self.api_key = None
        self.project_id = None
        self._load_config()
    
    def _load_config(self):
        # Try to get from environment (GitHub Actions)
        self.api_key = os.environ.get('FIREBASE_WEB_API_KEY')
        self.project_id = os.environ.get('FIREBASE_PROJECT_ID')
        
        # If not, try from local files
        if not self.api_key and os.path.exists("firebase_api_key.txt"):
            with open("firebase_api_key.txt", 'r') as f:
                self.api_key = f.read().strip()
        
        if not self.project_id and os.path.exists("firebase_project_id.txt"):
            with open("firebase_project_id.txt", 'r') as f:
                self.project_id = f.read().strip()
        
        # Also try from serviceAccountKey.json
        if not self.project_id and os.path.exists("serviceAccountKey.json"):
            try:
                with open("serviceAccountKey.json", 'r') as f:
                    data = json.load(f)
                    self.project_id = data.get('project_id')
            except:
                pass
        
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
        """Build Firebase REST API URL"""
        return f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{path}?key={self.api_key}"
    
    def sync_users(self, company_id, users):
        """Sync users to Firebase"""
        if not self.is_ready():
            return False
        
        try:
            for user in users:
                url = self._get_url(f"companies/{company_id}/users/{user['id']}")
                
                # Convert to Firestore format
                document = {
                    "fields": {
                        "id": {"integerValue": str(user['id'])},
                        "name": {"stringValue": user['name']},
                        "email": {"stringValue": user['email']},
                        "role": {"stringValue": user['role']},
                    }
                }
                
                response = requests.patch(url, json=document)
                if response.status_code not in [200, 201]:
                    print(f"Error syncing user {user['id']}: {response.text}")
                    return False
            
            print(f"✅ Synced {len(users)} users to Firebase")
            return True
        except Exception as e:
            print(f"Sync error: {e}")
            return False
    
    def get_users(self, company_id):
        """Get users from Firebase"""
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
                user = {'id': int(doc['name'].split('/')[-1])}
                fields = doc.get('fields', {})
                
                for key, value in fields.items():
                    if 'stringValue' in value:
                        user[key] = value['stringValue']
                    elif 'integerValue' in value:
                        user[key] = int(value['integerValue'])
                
                users.append(user)
            
            print(f"✅ Downloaded {len(users)} users from Firebase")
            return users
        except Exception as e:
            print(f"Get error: {e}")
            return []


# ========== THIS IS THE IMPORTANT PART - MAKE SURE THIS EXISTS ==========
firebase_api = FirebaseRestAPI()