"""
Material Manager - CRUD operations for materials
Works with SQLite local database
"""

import sqlite3
from datetime import datetime
from database import DB_PATH


class MaterialManager:

    # ---------- READ ----------

    @staticmethod
    def get_all():
        """Return all materials ordered by newest first"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_by_id(material_id):
        """Return one material by id"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    @staticmethod
    def get_by_barcode(barcode_value):
        """Return one material by barcode"""
        if not barcode_value:
            return None
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM materials WHERE barcode_value = ?",
            (barcode_value,),
        )
        row = cursor.fetchone()
        conn.close()
        return row

    @staticmethod
    def search(query):
        """Search materials by name or barcode"""
        if not query:
            return MaterialManager.get_all()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        like = f"%{query}%"
        cursor.execute(
            "SELECT * FROM materials "
            "WHERE name LIKE ? OR barcode_value LIKE ? "
            "ORDER BY id DESC",
            (like, like),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_by_category(category_id):
        """Return materials in a specific category"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM materials WHERE category_id = ? ORDER BY id DESC",
            (category_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    # ---------- CREATE ----------

    @staticmethod
    def create(data):
        """
        Insert a new material.
        Returns the new row id.
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO materials
            (name, category_id, quantity, quality, location_ids,
             size, length, colors, notes, barcode_value, image_path,
             company_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('name', ''),
            data.get('category_id', 1),
            data.get('quantity', 0),
            data.get('quality', 'New'),
            data.get('location_ids', ''),
            data.get('size', ''),
            data.get('length', None),
            data.get('colors', ''),
            data.get('notes', ''),
            data.get('barcode_value', ''),
            data.get('image_path', ''),
            data.get('company_id', 1),
            now,
            now,
        ))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return new_id

    # ---------- UPDATE ----------

    @staticmethod
    def update(material_id, data):
        """
        Update a material.
        Only fields present in `data` dict will be updated.
        """
        if not data:
            return False

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        allowed = [
            'name', 'category_id', 'quantity', 'quality', 'location_ids',
            'size', 'length', 'colors', 'notes', 'barcode_value', 'image_path',
        ]

        set_parts = []
        values = []
        for field in allowed:
            if field in data:
                set_parts.append(f"{field} = ?")
                values.append(data[field])

        if not set_parts:
            return False

        set_parts.append("updated_at = ?")
        values.append(now)
        values.append(material_id)

        sql = f"UPDATE materials SET {', '.join(set_parts)} WHERE id = ?"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        conn.close()
        return True

    # ---------- DELETE ----------

    @staticmethod
    def delete(material_id):
        """Delete a material by id"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        conn.commit()
        conn.close()
        return True

    # ---------- STATS ----------

    @staticmethod
    def count():
        """Return total number of materials"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM materials")
        total = cursor.fetchone()[0]
        conn.close()
        return total

    @staticmethod
    def total_stock():
        """Sum of all quantities across materials"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM materials")
        total = cursor.fetchone()[0]
        conn.close()
        return total

    @staticmethod
    def get_low_stock(threshold=10):
        """Return materials with quantity below threshold"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM materials WHERE quantity < ? ORDER BY quantity ASC",
            (threshold,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    print("MaterialManager self-test")
    try:
        all_mat = MaterialManager.get_all()
        print(f"✅ get_all    → {len(all_mat)} materials")
        print(f"✅ count      → {MaterialManager.count()}")
        print(f"✅ total_stock → {MaterialManager.total_stock()}")

        if all_mat:
            first = all_mat[0]
            print(f"✅ first      → id={first['id']}, name={first['name']}")
            bc = first['barcode_value']
            if bc:
                print(f"✅ by_barcode → {MaterialManager.get_by_barcode(bc) is not None}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
