"""
Material Manager - Handles all database operations for materials
"""
import sqlite3
import sys
import os

# Add parent directory to path so we can import database
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from database import DB_PATH
from datetime import datetime

class MaterialManager:
    
    @staticmethod
    def create(data):
        """Create a new material with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Insert material
            cursor.execute('''
                INSERT INTO materials (
                    name, category_id, quantity, quality, location_ids,
                    size, length, colors, notes, barcode_value, image_path,
                    company_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'), data.get('category_id'), data.get('quantity', 0),
                data.get('quality', 'New'), data.get('location_ids', ''),
                data.get('size', ''), data.get('length'), data.get('colors', ''),
                data.get('notes', ''), data.get('barcode_value', ''),
                data.get('image_path', ''), data.get('company_id', 1),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            material_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # ===== AUTO-SYNC AFTER CREATE =====
            MaterialManager._auto_sync_materials(data.get('company_id', 1))
            
            return material_id
            
        except Exception as e:
            print(f"Error creating material: {e}")
            return None
    
    @staticmethod
    def update(material_id, data):
        """Update a material with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get company_id before update
            cursor.execute("SELECT company_id FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            # Build update query dynamically
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id' and key != 'company_id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            values.append(material_id)
            
            query = f"UPDATE materials SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            # ===== AUTO-SYNC AFTER UPDATE =====
            MaterialManager._auto_sync_materials(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error updating material: {e}")
            return False
    
    @staticmethod
    def delete(material_id):
        """Delete a material with auto-sync"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get company_id before delete
            cursor.execute("SELECT company_id FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            company_id = result[0] if result else 1
            
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            
            # ===== AUTO-SYNC AFTER DELETE =====
            MaterialManager._auto_sync_materials(company_id)
            
            return True
            
        except Exception as e:
            print(f"Error deleting material: {e}")
            return False
    
    @staticmethod
    def _auto_sync_materials(company_id):
        """Internal method to auto-sync materials to cloud"""
        try:
            # Import here to avoid circular imports
            from main import CloudSyncManager
            
            # Use threading to not block the main thread
            import threading
            threading.Thread(
                target=CloudSyncManager.sync_materials_full_to_cloud,
                args=(company_id,),
                daemon=True
            ).start()
            print(f"🔄 Auto-sync triggered for materials (company: {company_id})")
        except Exception as e:
            print(f"Auto-sync error: {e}")

    @staticmethod
    def get_all():
        """Get all materials for current user's company"""
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get current user's company_id from the app context
        # This should be passed or stored globally
        cursor.execute("SELECT * FROM materials ORDER BY id DESC")
        
        materials = cursor.fetchall()
        conn.close()
        
        return materials
    
    @staticmethod
    def get_by_id(material_id):
        """Get a single material by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            print(f"Error getting material by ID: {e}")
            return None
    
    @staticmethod
    def get_by_barcode(barcode):
        """Get material by barcode"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE barcode_value = ?", (barcode,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            print(f"Error getting material by barcode: {e}")
            return None
    
    @staticmethod
    def create(data):
        """Create a new material"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if barcode already exists
            if data.get('barcode_value'):
                cursor.execute("SELECT id FROM materials WHERE barcode_value = ?", (data.get('barcode_value'),))
                if cursor.fetchone():
                    conn.close()
                    return False
            
            cursor.execute('''
                INSERT INTO materials (
                    name, category, category_id, item_code, quantity, 
                    size, length, quality, location_ids, colors, 
                    notes, barcode_value, image_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                data.get('name'),
                data.get('category', 'Uncategorized'),
                data.get('category_id'),
                data.get('item_code'),
                data.get('quantity', 0),
                data.get('size'),
                data.get('length'),
                data.get('quality', 'New'),
                data.get('location_ids'),
                data.get('colors'),
                data.get('notes'),
                data.get('barcode_value'),
                data.get('image_path')
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating material: {e}")
            return False
    
    @staticmethod
    def update(material_id, data, user_id=None):
        """Update an existing material"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Build update query dynamically based on provided fields
            update_fields = []
            values = []
            
            if 'name' in data:
                update_fields.append("name = ?")
                values.append(data['name'])
            if 'category' in data:
                update_fields.append("category = ?")
                values.append(data['category'])
            if 'category_id' in data:
                update_fields.append("category_id = ?")
                values.append(data['category_id'])
            if 'item_code' in data:
                update_fields.append("item_code = ?")
                values.append(data['item_code'])
            if 'quantity' in data:
                update_fields.append("quantity = ?")
                values.append(data['quantity'])
            if 'size' in data:
                update_fields.append("size = ?")
                values.append(data['size'])
            if 'length' in data:
                update_fields.append("length = ?")
                values.append(data['length'])
            if 'quality' in data:
                update_fields.append("quality = ?")
                values.append(data['quality'])
            if 'location_ids' in data:
                update_fields.append("location_ids = ?")
                values.append(data['location_ids'])
            if 'colors' in data:
                update_fields.append("colors = ?")
                values.append(data['colors'])
            if 'notes' in data:
                update_fields.append("notes = ?")
                values.append(data['notes'])
            if 'barcode_value' in data:
                update_fields.append("barcode_value = ?")
                values.append(data['barcode_value'])
            if 'image_path' in data:
                update_fields.append("image_path = ?")
                values.append(data['image_path'])
            
            if not update_fields:
                conn.close()
                return False
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(material_id)
            
            query = f"UPDATE materials SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating material: {e}")
            return False
    
    @staticmethod
    def delete(material_id):
        """Delete a material by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting material: {e}")
            return False
    
    @staticmethod
    def search(query):
        """Search materials by name or code"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            search_term = f"%{query}%"
            cursor.execute("""
                SELECT * FROM materials 
                WHERE name LIKE ? OR item_code LIKE ? OR barcode_value LIKE ?
                ORDER BY name ASC
            """, (search_term, search_term, search_term))
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"Error searching materials: {e}")
            return []
    
    @staticmethod
    def get_low_stock(threshold=10):
        """Get materials with low stock"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE quantity < ? ORDER BY quantity ASC", (threshold,))
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"Error getting low stock materials: {e}")
            return []
    
    @staticmethod
    def get_stats():
        """Get material statistics"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Total items
            cursor.execute("SELECT COUNT(*) as total FROM materials")
            total_items = cursor.fetchone()[0]
            
            # Total quantity
            cursor.execute("SELECT SUM(quantity) as total_qty FROM materials")
            total_qty = cursor.fetchone()[0] or 0
            
            # Quality breakdown
            cursor.execute("""
                SELECT quality, COUNT(*) as count, SUM(quantity) as stock 
                FROM materials 
                GROUP BY quality
            """)
            quality_stats = {}
            for row in cursor.fetchall():
                quality_stats[row[0]] = {'count': row[1], 'stock': row[2] or 0}
            
            # Category breakdown
            cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM materials 
                WHERE category IS NOT NULL AND category != ''
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
            """)
            top_categories = [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'total_items': total_items,
                'total_quantity': total_qty,
                'quality_stats': quality_stats,
                'top_categories': top_categories
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total_items': 0,
                'total_quantity': 0,
                'quality_stats': {},
                'top_categories': []
            }
