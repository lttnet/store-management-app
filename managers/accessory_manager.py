# managers/accessory_manager.py
import sqlite3
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DB_PATH

class AccessoryManager:
    
    @classmethod
    def get_connection(cls):
        """Get database connection that returns rows as dictionaries"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @classmethod
    def _row_to_dict(cls, row):
        """Convert sqlite3.Row to dictionary"""
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}
    
    @classmethod
    def _rows_to_list(cls, rows):
        """Convert list of sqlite3.Row to list of dictionaries"""
        if rows is None:
            return []
        return [cls._row_to_dict(row) for row in rows]
    
    @classmethod
    def get_all(cls):
        """Get all accessories"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)
    
    @classmethod
    def get_by_id(cls, accessory_id):
        """Get accessory by ID"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
        row = cursor.fetchone()
        conn.close()
        return cls._row_to_dict(row)
    
    @classmethod
    def get_by_barcode(cls, barcode):
        """Get accessory by barcode"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE barcode_value = ?", (barcode,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = cls._row_to_dict(row)
            print(f"Accessory found - fields: {list(result.keys())}")
            return result
        return None
    
    @classmethod
    def create(cls, data):
        """Create a new accessory"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO accessories 
                (name, item_code, quantity, price, quality, location, notes, barcode_value, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('name'), 
                data.get('item_code'),
                data.get('quantity', 0), 
                data.get('price', 0),
                data.get('quality'), 
                data.get('location'), 
                data.get('notes'),
                data.get('barcode_value'), 
                data.get('image_path')
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creating accessory: {e}")
            return None
        finally:
            conn.close()
    
    @classmethod
    def update(cls, accessory_id, data, user_id=None):
        """Update an accessory"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        try:
            allowed_fields = ['name', 'item_code', 'quantity', 'price', 'quality', 
                            'location', 'notes', 'barcode_value', 'image_path']
            
            set_clause = []
            values = []
            
            for field in allowed_fields:
                if field in data and data[field] is not None:
                    set_clause.append(f"{field} = ?")
                    values.append(data[field])
                    print(f"  Setting {field} = {data[field]}")
            
            if not set_clause:
                return False
            
            set_clause.append("updated_at = CURRENT_TIMESTAMP")
            values.append(accessory_id)
            
            query = f"UPDATE accessories SET {', '.join(set_clause)} WHERE id = ?"
            print(f"UPDATE query: {query}")
            print(f"Values: {values}")
            
            cursor.execute(query, values)
            conn.commit()
            
            success = cursor.rowcount > 0
            print(f"Update success: {success}, rows affected: {cursor.rowcount}")
            
            return success
            
        except Exception as e:
            print(f"Error updating accessory: {e}")
            return False
        finally:
            conn.close()
    
    @classmethod
    def delete(cls, accessory_id):
        """Delete an accessory"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get image path to delete file if exists
            cursor.execute("SELECT image_path FROM accessories WHERE id = ?", (accessory_id,))
            row = cursor.fetchone()
            if row and row['image_path']:
                image_path = row['image_path']
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except:
                        pass
            
            cursor.execute("DELETE FROM accessories WHERE id = ?", (accessory_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting accessory: {e}")
            return False
        finally:
            conn.close()
    
    @classmethod
    def search(cls, query):
        """Search accessories"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM accessories 
            WHERE name LIKE ? OR item_code LIKE ? OR location LIKE ?
            ORDER BY created_at DESC
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)
    
    @classmethod
    def get_stats(cls):
        """Get accessory statistics"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM accessories")
        total_items = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(quantity) FROM accessories")
        total_quantity = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_items': total_items,
            'total_quantity': total_quantity
        }
    
    @classmethod
    def get_low_stock(cls, threshold=10):
        """Get low stock accessories"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE quantity < ? ORDER BY quantity ASC", (threshold,))
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)
    
    @classmethod
    def get_by_location(cls, location):
        """Get accessories by location"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE location LIKE ? ORDER BY name", (f'%{location}%',))
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)
    
    @classmethod
    def get_by_quality(cls, quality):
        """Get accessories by quality"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE quality = ? ORDER BY name", (quality,))
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)