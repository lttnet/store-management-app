import os
import sqlite3
from datetime import datetime

# Get absolute path for database
def get_db_path():
    """Get absolute database path that works in APK"""
    # For Android APK, use the app's internal storage
    import sys
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundle (APK)
        base_path = os.path.dirname(sys.executable)
    else:
        # Normal Python execution
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    db_path = os.path.join(base_path, "store_management.db")
    print(f"DEBUG: Database path = {db_path}")
    return db_path

DB_PATH = get_db_path()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
