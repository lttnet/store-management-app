# managers/material_manager.py

import sqlite3
import sys
import os
from datetime import datetime

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from database import DB_PATH
except ImportError:
    DB_PATH = os.path.join(parent_dir, "store_management.db")

class MaterialManager:
    """Manages all material operations with auto-sync"""
    
    @staticmethod
    def _auto_sync(company_id):
        """Auto-sync materials to cloud"""
        try:
            import threading
            try:
                from main import CloudSyncManager
                threading.Thread(
                    target=CloudSyncManager.sync_materials_to_cloud,
                    args=(company_id,),
                    daemon=True
                ).start()
                print(f"🔄 Auto-sync triggered for materials (company: {company_id})")
            except ImportError:
                print("⚠️ CloudSyncManager not available")
        except Exception as e:
            print(f"Auto-sync error: {e}")
    
    # ============================================================
    # CREATE
    # ============================================================
    
    @staticmethod
    def create(data):
        """Create material with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO materials (
                    name, category_id, quantity, quality, location_ids,
                    size, length, colors, notes, barcode_value, image_path,
                    company_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('category_id', 0),
                data.get('quantity', 0),
                data.get('quality', 'New'),
                data.get('location_ids', ''),
                data.get('size', ''),
                data.get('length'),
                data.get('colors', ''),
                data.get('notes', ''),
                data.get('barcode_value', ''),
                data.get('image_path', ''),
                data.get('company_id', 1),
                current_time,
                current_time
            ))
            
            material_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Material created locally: ID={material_id}")
            
            # Auto-sync to cloud
            MaterialManager._auto_sync(data.get('company_id', 1))
            
            return material_id
            
        except Exception as e:
            print(f"Error creating material: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ============================================================
    # READ / GET
    # ============================================================
    
    @staticmethod
    def get_all(company_id=None):
        """Get all materials, optionally filtered by company_id"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if company_id:
                cursor.execute("SELECT * FROM materials WHERE company_id = ? ORDER BY id DESC", (company_id,))
            else:
                cursor.execute("SELECT * FROM materials ORDER BY id DESC")
            
            materials = cursor.fetchall()
            conn.close()
            return materials
            
        except Exception as e:
            print(f"Error getting materials: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def get_by_id(material_id):
        """Get a material by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            material = cursor.fetchone()
            conn.close()
            return material
            
        except Exception as e:
            print(f"Error getting material by ID: {e}")
            return None
    
    @staticmethod
    def get_by_barcode(barcode_value):
        """Get a material by barcode"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE barcode_value = ?", (barcode_value,))
            material = cursor.fetchone()
            conn.close()
            return material
            
        except Exception as e:
            print(f"Error getting material by barcode: {e}")
            return None
    
    @staticmethod
    def get_by_category(category_id, company_id=None):
        """Get materials by category"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if company_id:
                cursor.execute("SELECT * FROM materials WHERE category_id = ? AND company_id = ? ORDER BY name", 
                             (category_id, company_id))
            else:
                cursor.execute("SELECT * FROM materials WHERE category_id = ? ORDER BY name", (category_id,))
            
            materials = cursor.fetchall()
            conn.close()
            return materials
            
        except Exception as e:
            print(f"Error getting materials by category: {e}")
            return []
    
    @staticmethod
    def get_low_stock(threshold=10, company_id=None):
        """Get materials with low stock"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if company_id:
                cursor.execute("SELECT * FROM materials WHERE quantity < ? AND company_id = ? ORDER BY quantity ASC", 
                             (threshold, company_id))
            else:
                cursor.execute("SELECT * FROM materials WHERE quantity < ? ORDER BY quantity ASC", (threshold,))
            
            materials = cursor.fetchall()
            conn.close()
            return materials
            
        except Exception as e:
            print(f"Error getting low stock materials: {e}")
            return []
    
    @staticmethod
    def get_by_quality(quality, company_id=None):
        """Get materials by quality"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if company_id:
                cursor.execute("SELECT * FROM materials WHERE quality = ? AND company_id = ? ORDER BY name", 
                             (quality, company_id))
            else:
                cursor.execute("SELECT * FROM materials WHERE quality = ? ORDER BY name", (quality,))
            
            materials = cursor.fetchall()
            conn.close()
            return materials
            
        except Exception as e:
            print(f"Error getting materials by quality: {e}")
            return []
    
    @staticmethod
    def search(query, company_id=None):
        """Search materials by name or barcode"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            search_term = f"%{query}%"
            
            if company_id:
                cursor.execute('''
                    SELECT * FROM materials 
                    WHERE (name LIKE ? OR barcode_value LIKE ?) 
                    AND company_id = ? 
                    ORDER BY name
                ''', (search_term, search_term, company_id))
            else:
                cursor.execute('''
                    SELECT * FROM materials 
                    WHERE name LIKE ? OR barcode_value LIKE ? 
                    ORDER BY name
                ''', (search_term, search_term))
            
            materials = cursor.fetchall()
            conn.close()
            return materials
            
        except Exception as e:
            print(f"Error searching materials: {e}")
            return []
    
    @staticmethod
    def get_count(company_id=None):
        """Get total count of materials"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            if company_id:
                cursor.execute("SELECT COUNT(*) FROM materials WHERE company_id = ?", (company_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM materials")
            
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            print(f"Error getting material count: {e}")
            return 0
    
    # ============================================================
    # UPDATE
    # ============================================================
    
    @staticmethod
    def update(material_id, data):
        """Update material with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get company_id
            cursor.execute("SELECT company_id FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            # Build update query
            fields = []
            values = []
            
            for key, value in data.items():
                if key not in ['id', 'company_id', 'created_at']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            values.append(material_id)
            
            query = f"UPDATE materials SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            print(f"✅ Material updated: ID={material_id}")
            
            # Auto-sync to cloud
            MaterialManager._auto_sync(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error updating material: {e}")
            return False
    
    @staticmethod
    def update_quantity(material_id, new_quantity):
        """Update only quantity"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT company_id FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            cursor.execute('''
                UPDATE materials 
                SET quantity = ?, updated_at = ? 
                WHERE id = ?
            ''', (new_quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), material_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Material quantity updated: ID={material_id}")
            
            MaterialManager._auto_sync(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error updating material quantity: {e}")
            return False
    
    # ============================================================
    # DELETE
    # ============================================================
    
    @staticmethod
    def delete(material_id):
        """Delete material with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get company_id
            cursor.execute("SELECT company_id FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            
            print(f"✅ Material deleted locally: ID={material_id}")
            
            # Auto-sync deletion to cloud
            MaterialManager._auto_sync(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error deleting material: {e}")
            return False
    
    @staticmethod
    def delete_by_company(company_id):
        """Delete all materials for a company"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM materials WHERE company_id = ?", (company_id,))
            conn.commit()
            conn.close()
            
            print(f"✅ All materials deleted for company {company_id}")
            
            MaterialManager._auto_sync(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error deleting materials by company: {e}")
            return False
