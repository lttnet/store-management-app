# managers/material_manager.py
import sqlite3
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DB_PATH

class MaterialManager:
    
    @classmethod
    def get_connection(cls):
        """Get database connection that returns rows as dictionaries"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
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
        """Get all materials"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)
    
    @classmethod
    def get_by_id(cls, material_id):
        """Get material by ID"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        row = cursor.fetchone()
        conn.close()
        return cls._row_to_dict(row)
    
    @classmethod
    def get_by_barcode(cls, barcode):
        """Get material by barcode"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE barcode_value = ?", (barcode,))
        row = cursor.fetchone()
        conn.close()
        return cls._row_to_dict(row)
    
    @classmethod
    def create(cls, data):
        """Create a new material with timestamps"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        try:
            # Let database handle both timestamps
            cursor.execute("""
                INSERT INTO materials 
                (name, item_code, quantity, size, length, quality, location_ids, colors, notes, barcode_value, barcode_path, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('name'), 
                data.get('item_code'),
                data.get('quantity', 0), 
                data.get('size'), 
                data.get('length'),
                data.get('quality'), 
                data.get('location_ids'), 
                data.get('colors'),
                data.get('notes'), 
                data.get('barcode_value'), 
                data.get('barcode_path'),
                data.get('image_path')
            ))
            conn.commit()
            
            # Get the created material to verify timestamps
            material_id = cursor.lastrowid
            cursor.execute("SELECT created_at, updated_at FROM materials WHERE id = ?", (material_id,))
            row = cursor.fetchone()
            print(f"Created material {material_id} with created_at: {row[0]}, updated_at: {row[1]}")
            
            return material_id
        except Exception as e:
            print(f"Error creating material: {e}")
            return None
        finally:
            conn.close()
    
    @classmethod
    def update(cls, material_id, data, user_id=None):
        """Update a material with manual updated_at"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        try:
            allowed_fields = ['name', 'item_code', 'quantity', 'size', 'length', 
                            'quality', 'location_ids', 'colors', 'notes', 
                            'barcode_value', 'barcode_path', 'image_path']
            
            set_clause = []
            values = []
            
            for field in allowed_fields:
                if field in data and data[field] is not None:
                    set_clause.append(f"{field} = ?")
                    values.append(data[field])
                    print(f"  Setting {field} = {data[field]}")
            
            if not set_clause:
                return False
            
            # Manually set updated_at to current timestamp
            set_clause.append("updated_at = CURRENT_TIMESTAMP")
            values.append(material_id)
            
            query = f"UPDATE materials SET {', '.join(set_clause)} WHERE id = ?"
            
            print(f"UPDATE query: {query}")
            print(f"Values: {values}")
            
            cursor.execute(query, values)
            conn.commit()
            
            success = cursor.rowcount > 0
            print(f"Update success: {success}, rows affected: {cursor.rowcount}")
            
            # Verify the update
            if success:
                cursor.execute("SELECT updated_at FROM materials WHERE id = ?", (material_id,))
                row = cursor.fetchone()
                print(f"Verified updated_at in DB: {row[0] if row else 'None'}")
            
            return success
            
        except Exception as e:
            print(f"Error updating material: {e}")
            return False
        finally:
            conn.close()
    
    @classmethod
    def delete(cls, material_id):
        """Delete a material"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting material: {e}")
            return False
        finally:
            conn.close()
    
    @classmethod
    def search(cls, query):
        """Search materials"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM materials 
            WHERE name LIKE ? OR item_code LIKE ? OR location_ids LIKE ?
            ORDER BY created_at DESC
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)
    
    @classmethod
    def get_stats(cls):
        """Get material statistics"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM materials")
        total_items = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(quantity) FROM materials")
        total_quantity = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_items': total_items,
            'total_quantity': total_quantity
        }
    
    @classmethod
    def get_low_stock(cls, threshold=10):
        """Get low stock materials"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE quantity < ? ORDER BY quantity ASC", (threshold,))
        rows = cursor.fetchall()
        conn.close()
        return cls._rows_to_list(rows)