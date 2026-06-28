# activation_manager.py - Updated

import sqlite3
import random
import string
from datetime import datetime, timedelta
from database import DB_PATH

class ActivationManager:
    """Manage activation codes for purchased apps"""
    
    @staticmethod
    def ensure_table():
        """Ensure activation_codes table exists"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activation_codes'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE activation_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    company_id INTEGER,
                    created_at TEXT,
                    expires_at TEXT,
                    used INTEGER DEFAULT 0,
                    used_by INTEGER,
                    used_at TEXT
                )
            ''')
            conn.commit()
            print("✅ Created activation_codes table")
        
        conn.close()
    
    @staticmethod
    def generate_activation_code():
        """Generate a unique activation code"""
        prefix = "ACT"
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"{prefix}-{random_part}"
    
    @staticmethod
    def create_activation_code(company_id, days_valid=365):
        """Create a new activation code for a company"""
        ActivationManager.ensure_table()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        code = ActivationManager.generate_activation_code()
        expires_at = (datetime.now() + timedelta(days=days_valid)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO activation_codes 
            (code, company_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (code, company_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), expires_at))
        
        conn.commit()
        conn.close()
        
        return code
    
    @staticmethod
    def verify_activation_code(code):
        """Verify if an activation code is valid"""
        ActivationManager.ensure_table()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, company_id, used, expires_at 
            FROM activation_codes 
            WHERE code = ?
        ''', (code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None, "Invalid activation code"
        
        code_id, company_id, used, expires_at = result
        
        if used == 1:
            return None, "Activation code already used"
        
        if expires_at and datetime.now() > datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S'):
            return None, "Activation code has expired"
        
        return company_id, "Valid"
    
    @staticmethod
    def use_activation_code(code, user_id):
        """Mark an activation code as used"""
        ActivationManager.ensure_table()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE activation_codes 
            SET used = 1, used_by = ?, used_at = datetime('now')
            WHERE code = ?
        ''', (user_id, code))
        
        conn.commit()
        conn.close()
        
        return True