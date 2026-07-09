# managers/accessory_manager.py
import sqlite3
import sys
import os
from datetime import datetime

# Fix import paths - go up one level to parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from parent directory (NO circular imports)
from database import DB_PATH
from firebase_client import firebase_api
from cloud_sync_manager import CloudSyncManager

class AccessoryManager:
    
    @staticmethod
    def get_all():
        """Get all accessories"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories ORDER BY id DESC")
            accessories = cursor.fetchall()
            conn.close()
            
            result = []
            for a in accessories:
                result.append(dict(a))
            return result
        except Exception as e:
            print(f"Get all accessories error: {e}")
            return []
    
    @staticmethod
    def get_by_id(accessory_id):
        """Get accessory by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
            accessory = cursor.fetchone()
            conn.close()
            
            if accessory:
                return dict(accessory)
            return None
        except Exception as e:
            print(f"Get accessory by ID error: {e}")
            return None
    
    @staticmethod
    def get_by_barcode(barcode_value):
        """Get accessory by barcode"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE barcode_value = ?", (barcode_value,))
            accessory = cursor.fetchone()
            conn.close()
            
            if accessory:
                return dict(accessory)
            return None
        except Exception as e:
            print(f"Get accessory by barcode error: {e}")
            return None
    
    @staticmethod
    def create(data):
        """Create accessory and auto-sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            company_id = data.get('company_id', 1)
            
            cursor.execute('''
                INSERT INTO accessories (name, category_id, quantity, price, quality, location,
                    notes, barcode_value, image_path, company_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('category_id', 1),
                data.get('quantity', 0),
                data.get('price', 0),
                data.get('quality', 'New'),
                data.get('location', ''),
                data.get('notes', ''),
                data.get('barcode_value', ''),
                data.get('image_path', ''),
                company_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            accessory_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # AUTO-SYNC: Sync immediately in background
            if firebase_api.is_ready():
                import threading
                def sync():
                    try:
                        import time
                        time.sleep(0.5)
                        success = CloudSyncManager.sync_single_accessory_to_cloud(company_id, accessory_id)
                        if success:
                            print(f"✅ [AUTO-SYNC] Accessory '{data.get('name')}' synced to cloud")
                        else:
                            print(f"⚠️ [AUTO-SYNC] Accessory '{data.get('name')}' failed to sync")
                    except Exception as e:
                        print(f"[AUTO-SYNC] Error: {e}")
                threading.Thread(target=sync, daemon=True).start()
            else:
                print("⚠️ [AUTO-SYNC] Firebase not ready - accessory saved locally only")
            
            return accessory_id
            
        except Exception as e:
            print(f"Create accessory error: {e}")
            return None
    
# managers/accessory_manager.py

    @staticmethod
    def update(accessory_id, data):
        """Update accessory and auto-sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM accessories WHERE id = ?", (accessory_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            company_id = result[0]
            
            set_clause = []
            values = []
            
            for key, value in data.items():
                if key != 'id' and key != 'company_id':
                    set_clause.append(f"{key} = ?")
                    values.append(value)
            
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            values.append(accessory_id)
            
            query = f"UPDATE accessories SET {', '.join(set_clause)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            
            cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
            updated_accessory = cursor.fetchone()
            conn.close()
            
            if updated_accessory:
                # AUTO-SYNC: Sync immediately in background
                if firebase_api.is_ready():
                    import threading
                    def sync():
                        try:
                            accessory_dict = dict(updated_accessory)
                            success = firebase_api.sync_accessory(company_id, accessory_dict)
                            if success:
                                print(f"✅ [AUTO-SYNC] Accessory '{accessory_dict.get('name')}' updated and synced to cloud")
                            else:
                                print(f"⚠️ [AUTO-SYNC] Accessory '{accessory_dict.get('name')}' failed to sync")
                        except Exception as e:
                            print(f"[AUTO-SYNC] Error: {e}")
                    threading.Thread(target=sync, daemon=True).start()
                else:
                    print("⚠️ [AUTO-SYNC] Firebase not ready - accessory updated locally only")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Update accessory error: {e}")
            return False

    
    @staticmethod
    def delete(accessory_id):
        """Delete accessory and auto-sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id, name FROM accessories WHERE id = ?", (accessory_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            company_id = result[0]
            accessory_name = result[1]
            
            cursor.execute("DELETE FROM accessories WHERE id = ?", (accessory_id,))
            conn.commit()
            conn.close()
            
            # AUTO-SYNC: Delete from cloud
            if firebase_api.is_ready():
                import threading
                def sync():
                    try:
                        success = firebase_api.delete_accessory(company_id, accessory_id)
                        if success:
                            print(f"✅ [AUTO-SYNC] Accessory '{accessory_name}' deleted from cloud")
                        else:
                            print(f"⚠️ [AUTO-SYNC] Accessory '{accessory_name}' failed to delete from cloud")
                    except Exception as e:
                        print(f"[AUTO-SYNC] Error: {e}")
                threading.Thread(target=sync, daemon=True).start()
            else:
                print("⚠️ [AUTO-SYNC] Firebase not ready - accessory deleted locally only")
            
            return True
            
        except Exception as e:
            print(f"Delete accessory error: {e}")
            return False
