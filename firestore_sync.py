# firestore_sync.py - Simple version to avoid import errors
class FirestoreSync:
    _instance = None
    initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirestoreSync, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def is_ready(self):
        return False

firestore_sync = FirestoreSync()
print("✅ firestore_sync loaded")
