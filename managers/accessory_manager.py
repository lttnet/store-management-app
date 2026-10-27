"""
Accessory Manager - CRUD operations for accessories
Works with SQLite local database
"""

import sqlite3
from datetime import datetime
from database import DB_PATH


class AccessoryManager:

    # ---------- READ ----------

    @staticmethod
    def get_all():
        """Return all accessories ordered by newest first"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_by_id(accessory_id):
        """Return one accessory by id"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    @staticmethod
    def get_by_barcode(barcode_value):
        """Return one accessory by barcode"""
        if not barcode_value:
            return None
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM accessories WHERE barcode_value = ?",
            (barcode_value,),
        )
        row = cursor.fetchone()
        conn.close()
        return row

    @staticmethod
    def search(query):
        """Search accessories by name or barcode"""
        if not query:
            return AccessoryManager.get_all()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        like = f"%{query}%"
        cursor.execute(
            "SELECT * FROM accessories "
            "WHERE name LIKE ? OR barcode_value LIKE ? "
            "ORDER BY id DESC",
            (like, like),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    # ---------- CREATE ----------

    @staticmethod
    def create(data):
        """
        Insert a new accessory.
        Returns the new row id.
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accessories
            (name, category_id, quantity, price, quality, location,
             notes, barcode_value, image_path, company_id,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('name', ''),
            data.get('category_id', 1),
            data.get('quantity', 0),
            data.get('price', 0),
            data.get('quality', 'New'),
            data.get('location', ''),
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
    def update(accessory_id, data):
        """
        Update an accessory.
        Only fields present in `data` dict will be updated.
        """
        if not data:
            return False

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Build SET clause dynamically
        allowed = [
            'name', 'category_id', 'quantity', 'price', 'quality',
            'location', 'notes', 'barcode_value', 'image_path',
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
        values.append(accessory_id)

        sql = f"UPDATE accessories SET {', '.join(set_parts)} WHERE id = ?"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        conn.close()
        return True

    # ---------- DELETE ----------

    @staticmethod
    def delete(accessory_id):
        """Delete an accessory by id"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accessories WHERE id = ?", (accessory_id,))
        conn.commit()
        conn.close()
        return True

    # ---------- COUNT / STATS ----------

    @staticmethod
    def count():
        """Return total number of accessories"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM accessories")
        total = cursor.fetchone()[0]
        conn.close()
        return total

    @staticmethod
    def get_low_stock(threshold=10):
        """Return accessories with quantity below threshold"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM accessories WHERE quantity < ? ORDER BY quantity ASC",
            (threshold,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    print("AccessoryManager self-test")
    try:
        all_acc = AccessoryManager.get_all()
        print(f"✅ get_all → {len(all_acc)} accessories")
        print(f"✅ count    → {AccessoryManager.count()}")

        if all_acc:
            first = all_acc[0]
            print(f"✅ first    → id={first['id']}, name={first['name']}")
            print(f"✅ by_barcode test → "
                  f"{AccessoryManager.get_by_barcode(first['barcode_value'])}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
