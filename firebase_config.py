# firebase_config.py - Mock only, no Firebase installation needed
import os
import json
from datetime import datetime

class MockFirestore:
    """Mock Firestore - saves data locally as JSON file"""
    
    def __init__(self):
        self.data = {}
        self.sync_file = "mock_cloud_data.json"
        self._load_data()
        print(f"📁 Mock cloud storage: {self.sync_file}")
    
    def _load_data(self):
        if os.path.exists(self.sync_file):
            try:
                with open(self.sync_file, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = {'companies': {}}
        else:
            self.data = {'companies': {}}
    
    def _save_data(self):
        with open(self.sync_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def collection(self, name):
        return MockCollection(self, name)

class MockCollection:
    def __init__(self, db, name):
        self.db = db
        self.name = name
    
    def document(self, doc_id):
        return MockDocument(self.db, self.name, doc_id)
    
    def stream(self):
        docs = []
        if self.name in self.db.data:
            for doc_id, data in self.db.data[self.name].items():
                docs.append(MockDocumentSnapshot(doc_id, data))
        return docs

class MockDocument:
    def __init__(self, db, collection_name, doc_id):
        self.db = db
        self.collection_name = collection_name
        self.doc_id = str(doc_id)
    
    def set(self, data):
        if self.collection_name not in self.db.data:
            self.db.data[self.collection_name] = {}
        self.db.data[self.collection_name][self.doc_id] = data
        self.db._save_data()
    
    def collection(self, name):
        return MockCollection(self.db, f"{self.collection_name}/{self.doc_id}/{name}")

class MockDocumentSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
    
    def to_dict(self):
        return self._data
    
    def exists(self):
        return self._data is not None

class FirebaseConfig:
    _instance = None
    db = None
    is_initialized = True
    using_mock = True
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseConfig, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.db = MockFirestore()
        print("✅ Mock Firebase ready (no installation needed)")
    
    def get_db(self):
        return self.db
    
    def is_ready(self):
        return True
    
    def is_mock(self):
        return True

firebase = FirebaseConfig()