# managers/sync_manager.py

import threading
from datetime import datetime

class SyncManager:
    """Centralized auto-sync manager"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SyncManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._sync_queue = {}
        self._sync_timer = None
    
    @staticmethod
    def trigger_sync(company_id, data_type='all'):
        """Trigger a sync for a specific data type"""
        try:
            from main import CloudSyncManager
            
            def do_sync():
                try:
                    if data_type == 'users' or data_type == 'all':
                        CloudSyncManager.sync_users_full_to_cloud(company_id)
                    
                    if data_type == 'materials' or data_type == 'all':
                        CloudSyncManager.sync_materials_full_to_cloud(company_id)
                    
                    if data_type == 'accessories' or data_type == 'all':
                        CloudSyncManager.sync_accessories_full_to_cloud(company_id)
                    
                    print(f"✅ Auto-sync completed for company {company_id} ({data_type})")
                except Exception as e:
                    print(f"Auto-sync error: {e}")
            
            # Run in background thread
            thread = threading.Thread(target=do_sync, daemon=True)
            thread.start()
            
        except Exception as e:
            print(f"Trigger sync error: {e}")
    
    @staticmethod
    def sync_materials(company_id):
        """Convenience method to sync only materials"""
        SyncManager.trigger_sync(company_id, 'materials')
    
    @staticmethod
    def sync_accessories(company_id):
        """Convenience method to sync only accessories"""
        SyncManager.trigger_sync(company_id, 'accessories')
    
    @staticmethod
    def sync_users(company_id):
        """Convenience method to sync only users"""
        SyncManager.trigger_sync(company_id, 'users')
    
    @staticmethod
    def sync_all(company_id):
        """Convenience method to sync all data"""
        SyncManager.trigger_sync(company_id, 'all')
