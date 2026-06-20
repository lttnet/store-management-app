"""
Accessory Manager - Handles all database operations for accessories
"""
import sqlite3
import sys
import os

# Add parent directory to path so we can import database
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH
from datetime import datetime


class AccessoryManager:
    """Manager class for accessory operations"""
    
    @staticmethod
    def get_all():
        """Get all accessories from database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories ORDER BY created_at DESC")
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"Error getting accessories: {e}")
            return []
    
    @staticmethod
    def get_by_id(accessory_id):
        """Get a single accessory by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            print(f"Error getting accessory by ID: {e}")
            return None
    
    @staticmethod
    def get_by_barcode(barcode):
        """Get accessory by barcode"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE barcode_value = ?", (barcode,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            print(f"Error getting accessory by barcode: {e}")
            return None
    
    @staticmethod
    def create(data):
        """Create a new accessory"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if barcode already exists
            if data.get('barcode_value'):
                cursor.execute("SELECT id FROM accessories WHERE barcode_value = ?", (data.get('barcode_value'),))
                if cursor.fetchone():
                    conn.close()
                    return False
            
            cursor.execute('''
                INSERT INTO accessories (
                    name, category, category_id, item_code, quantity, 
                    price, quality, location, notes, barcode_value, 
                    image_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                data.get('name'),
                data.get('category', 'Uncategorized'),
                data.get('category_id'),
                data.get('item_code'),
                data.get('quantity', 0),
                data.get('price', 0.0),
                data.get('quality', 'New'),
                data.get('location'),
                data.get('notes'),
                data.get('barcode_value'),
                data.get('image_path')
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating accessory: {e}")
            return False
    
    @staticmethod
    def update(accessory_id, data, user_id=None):
        """Update an existing accessory"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
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
            if 'price' in data:
                update_fields.append("price = ?")
                values.append(data['price'])
            if 'quality' in data:
                update_fields.append("quality = ?")
                values.append(data['quality'])
            if 'location' in data:
                update_fields.append("location = ?")
                values.append(data['location'])
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
            values.append(accessory_id)
            
            query = f"UPDATE accessories SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating accessory: {e}")
            return False
    
    @staticmethod
    def delete(accessory_id):
        """Delete an accessory by ID"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accessories WHERE id = ?", (accessory_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting accessory: {e}")
            return False
    
    @staticmethod
    def search(query):
        """Search accessories by name or code"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            search_term = f"%{query}%"
            cursor.execute("""
                SELECT * FROM accessories 
                WHERE name LIKE ? OR item_code LIKE ? OR barcode_value LIKE ?
                ORDER BY name ASC
            """, (search_term, search_term, search_term))
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"Error searching accessories: {e}")
            return []
    
    @staticmethod
    def get_low_stock(threshold=10):
        """Get accessories with low stock"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accessories WHERE quantity < ? ORDER BY quantity ASC", (threshold,))
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            print(f"Error getting low stock accessories: {e}")
            return []
    
    @staticmethod
    def get_stats():
        """Get accessory statistics"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM accessories")
            total_items = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(quantity) as total_qty FROM accessories")
            total_qty = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(quantity * price) as total_value FROM accessories")
            total_value = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT quality, COUNT(*) as count, SUM(quantity) as stock 
                FROM accessories 
                GROUP BY quality
            """)
            quality_stats = {}
            for row in cursor.fetchall():
                quality_stats[row[0]] = {'count': row[1], 'stock': row[2] or 0}
            
            conn.close()
            
            return {
                'total_items': total_items,
                'total_quantity': total_qty,
                'total_value': total_value,
                'quality_stats': quality_stats
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total_items': 0,
                'total_quantity': 0,
                'total_value': 0,
                'quality_stats': {}
            }
