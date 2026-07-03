# managers/accessory_manager.py

import sqlite3
import sys
import os
from datetime import datetime

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from database import DB_PATH
except ImportError:
    DB_PATH = os.path.join(parent_dir, "store_management.db")

class AccessoryManager:
    
    @staticmethod
    def _auto_sync(company_id):
        """Auto-sync accessories to cloud"""
        try:
            import threading
            try:
                from main import CloudSyncManager
                threading.Thread(
                    target=CloudSyncManager.sync_accessories_to_cloud,
                    args=(company_id,),
                    daemon=True
                ).start()
                print(f"🔄 Auto-sync triggered for accessories (company: {company_id})")
            except ImportError:
                print("⚠️ CloudSyncManager not available")
        except Exception as e:
            print(f"Auto-sync error: {e}")
    
    @staticmethod
    def create(data):
        """Create accessory with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO accessories (
                    name, category_id, quantity, price, quality, location,
                    notes, barcode_value, image_path, company_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('category_id', 0),
                data.get('quantity', 0),
                data.get('price', 0),
                data.get('quality', 'New'),
                data.get('location', ''),
                data.get('notes', ''),
                data.get('barcode_value', ''),
                data.get('image_path', ''),
                data.get('company_id', 1),
                current_time,
                current_time
            ))
            
            accessory_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Accessory created locally: ID={accessory_id}")
            
            # ===== AUTO-SYNC TO CLOUD =====
            AccessoryManager._auto_sync(data.get('company_id', 1))
            
            return accessory_id
            
        except Exception as e:
            print(f"Error creating accessory: {e}")
            return None
    
    @staticmethod
    def update(accessory_id, data):
        """Update accessory with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM accessories WHERE id = ?", (accessory_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            fields = []
            values = []
            
            for key, value in data.items():
                if key not in ['id', 'company_id', 'created_at']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            values.append(accessory_id)
            
            query = f"UPDATE accessories SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            print(f"✅ Accessory updated: ID={accessory_id}")
            
            # ===== AUTO-SYNC TO CLOUD =====
            AccessoryManager._auto_sync(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error updating accessory: {e}")
            return False
    
    @staticmethod
    def delete(accessory_id):
        """Delete accessory with auto-sync (also deletes from cloud)"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM accessories WHERE id = ?", (accessory_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            cursor.execute("DELETE FROM accessories WHERE id = ?", (accessory_id,))
            conn.commit()
            conn.close()
            
            print(f"✅ Accessory deleted locally: ID={accessory_id}")
            
            # ===== AUTO-SYNC DELETE TO CLOUD =====
            AccessoryManager._auto_sync(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error deleting accessory: {e}")
            return False
    # managers/accessory_manager.py - Add this method

    @staticmethod
    def get_all(company_id=None):
        """Get all accessories, optionally filtered by company_id"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if company_id:
                cursor.execute("SELECT * FROM accessories WHERE company_id = ? ORDER BY id DESC", (company_id,))
            else:
                cursor.execute("SELECT * FROM accessories ORDER BY id DESC")
            
            accessories = cursor.fetchall()
            conn.close()
            return accessories
            
        except Exception as e:
            print(f"Error getting accessories: {e}")
            return []
