# managers/material_manager.py
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

class MaterialManager:
    
    @staticmethod
    def get_all():
        """Get all materials"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials ORDER BY id DESC")
            materials = cursor.fetchall()
            conn.close()
            
            result = []
            for m in materials:
                result.append(dict(m))
            return result
        except Exception as e:
            print(f"Get all materials error: {e}")
            return []
    
    @staticmethod
    def get_by_id(material_id):
        """Get material by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            material = cursor.fetchone()
            conn.close()
            
            if material:
                return dict(material)
            return None
        except Exception as e:
            print(f"Get material by ID error: {e}")
            return None
    
    @staticmethod
    def get_by_barcode(barcode_value):
        """Get material by barcode"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE barcode_value = ?", (barcode_value,))
            material = cursor.fetchone()
            conn.close()
            
            if material:
                return dict(material)
            return None
        except Exception as e:
            print(f"Get material by barcode error: {e}")
            return None
    
    @staticmethod
    def create(data):
        """Create material and auto-sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            company_id = data.get('company_id', 1)
            
            cursor.execute('''
                INSERT INTO materials (name, category_id, quantity, quality, location_ids,
                    size, length, colors, notes, barcode_value, image_path, company_id,
                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('category_id', 1),
                data.get('quantity', 0),
                data.get('quality', 'New'),
                data.get('location_ids', ''),
                data.get('size', ''),
                data.get('length', 0),
                data.get('colors', ''),
                data.get('notes', ''),
                data.get('barcode_value', ''),
                data.get('image_path', ''),
                company_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            material_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # AUTO-SYNC: Sync immediately in background
            if firebase_api.is_ready():
                import threading
                def sync():
                    try:
                        # Wait a moment for the database to be ready
                        import time
                        time.sleep(0.5)
                        success = CloudSyncManager.sync_single_material_to_cloud(company_id, material_id)
                        if success:
                            print(f"✅ [AUTO-SYNC] Material '{data.get('name')}' synced to cloud")
                        else:
                            print(f"⚠️ [AUTO-SYNC] Material '{data.get('name')}' failed to sync")
                    except Exception as e:
                        print(f"[AUTO-SYNC] Error: {e}")
                threading.Thread(target=sync, daemon=True).start()
            else:
                print("⚠️ [AUTO-SYNC] Firebase not ready - material saved locally only")
            
            return material_id
            
        except Exception as e:
            print(f"Create material error: {e}")
            return None
    
    @staticmethod
    def update(material_id, data):
        """Update material and auto-sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            company_id = result[0]
            
            # Build update query
            set_clause = []
            values = []
            
            for key, value in data.items():
                if key != 'id' and key != 'company_id':
                    set_clause.append(f"{key} = ?")
                    values.append(value)
            
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            values.append(material_id)
            
            query = f"UPDATE materials SET {', '.join(set_clause)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            
            # Get the updated material data
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            updated_material = cursor.fetchone()
            conn.close()
            
            if updated_material:
                # AUTO-SYNC: Sync immediately in background
                if firebase_api.is_ready():
                    import threading
                    def sync():
                        try:
                            material_dict = dict(updated_material)
                            success = firebase_api.sync_material(company_id, material_dict)
                            if success:
                                print(f"✅ [AUTO-SYNC] Material '{material_dict.get('name')}' updated and synced to cloud")
                            else:
                                print(f"⚠️ [AUTO-SYNC] Material '{material_dict.get('name')}' failed to sync")
                        except Exception as e:
                            print(f"[AUTO-SYNC] Error: {e}")
                    threading.Thread(target=sync, daemon=True).start()
                else:
                    print("⚠️ [AUTO-SYNC] Firebase not ready - material updated locally only")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Update material error: {e}")
            return False
    
    @staticmethod
    def delete(material_id):
        """Delete material and auto-sync to cloud"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id, name FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            company_id = result[0]
            material_name = result[1]
            
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            
            # AUTO-SYNC: Delete from cloud
            if firebase_api.is_ready():
                import threading
                def sync():
                    try:
                        success = firebase_api.delete_material(company_id, material_id)
                        if success:
                            print(f"✅ [AUTO-SYNC] Material '{material_name}' deleted from cloud")
                        else:
                            print(f"⚠️ [AUTO-SYNC] Material '{material_name}' failed to delete from cloud")
                    except Exception as e:
                        print(f"[AUTO-SYNC] Error: {e}")
                threading.Thread(target=sync, daemon=True).start()
            else:
                print("⚠️ [AUTO-SYNC] Firebase not ready - material deleted locally only")
            
            return True
            
        except Exception as e:
            print(f"Delete material error: {e}")
            return False
