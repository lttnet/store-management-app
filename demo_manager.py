# demo_manager.py - Complete with all methods

import sqlite3
import hashlib
import random
import string
from datetime import datetime, timedelta
from database import DB_PATH

class DemoManager:
    """Manages demo/trial accounts"""
    
    @staticmethod
    def get_table_columns():
        """Get all column names from users table"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            conn.close()
            return columns
        except:
            return []
    
    @staticmethod
    def create_demo_company():
        """Create a demo company with sample data"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if demo already exists
        cursor.execute("SELECT id FROM companies WHERE name = 'Demo Company'")
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return existing[0]
        
        # Create demo company
        cursor.execute(
            "INSERT INTO companies (name, created_at) VALUES (?, ?)",
            ('Demo Company', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        company_id = cursor.lastrowid
        
        # Create admin user
        admin_password = hashlib.sha256("demo123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, company_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Demo Admin', 'demo@store.com', admin_password, 'admin', company_id, 
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Create manager user
        manager_password = hashlib.sha256("demo123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, company_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Demo Manager', 'manager@store.com', manager_password, 'manager', company_id,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Create regular user
        user_password = hashlib.sha256("demo123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, company_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Demo User', 'user@store.com', user_password, 'user', company_id,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Create sample categories
        categories = [
            ('Raw Material', '📦'),
            ('Hardware', '🔩'),
            ('Tools', '🔧'),
            ('Electrical', '⚡'),
            ('Plumbing', '💧'),
            ('Metal', '⚙️'),
            ('Wood', '🪵'),
            ('Other', '📁'),
        ]
        
        category_ids = {}
        for name, icon in categories:
            cursor.execute(
                "INSERT INTO categories (name, icon, user_id, created_at) VALUES (?, ?, ?, ?)",
                (name, icon, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            category_ids[name] = cursor.lastrowid
        
        # Create sample materials
        sample_materials = [
            ('Steel Rod', category_ids['Metal'], 50, 'New', 'Warehouse A', '2m', 2.0, 'Silver', 'High quality steel'),
            ('Copper Wire', category_ids['Electrical'], 100, 'New', 'Warehouse B', '100m', 100.0, 'Copper', 'For electrical work'),
            ('PVC Pipe', category_ids['Plumbing'], 30, 'Used', 'Storage 1', '3m', 3.0, 'White', 'For plumbing'),
            ('Wood Plank', category_ids['Wood'], 25, 'Used', 'Warehouse A', '2.4m', 2.4, 'Brown', 'For construction'),
            ('Screws Set', category_ids['Hardware'], 200, 'New', 'Toolbox 1', 'M4x20', None, 'Silver', 'Machine screws'),
            ('Paint Can', category_ids['Other'], 15, 'New', 'Storage 2', '1L', None, 'Red', 'Red paint'),
            ('LED Light', category_ids['Electrical'], 45, 'New', 'Warehouse B', '10W', None, 'White', 'LED bulbs'),
            ('Hammer', category_ids['Tools'], 8, 'Used', 'Toolbox 2', '500g', None, 'Steel', 'Claw hammer'),
            ('Drill Bit Set', category_ids['Tools'], 12, 'New', 'Toolbox 1', '1-10mm', None, 'Various', 'For drilling'),
            ('Gloves', category_ids['Other'], 35, 'New', 'Safety Room', 'L', None, 'Blue', 'Safety gloves'),
        ]
        
        for mat in sample_materials:
            barcode = DemoManager._generate_barcode()
            cursor.execute('''
                INSERT INTO materials 
                (name, category_id, quantity, quality, location_ids, size, length, colors, notes, barcode_value, company_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (mat[0], mat[1], mat[2], mat[3], mat[4], mat[5], mat[6], mat[7], mat[8], barcode, company_id,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Create sample accessories
        sample_accessories = [
            ('Screwdriver Set', category_ids['Tools'], 15, 25.99, 'New', 'Toolbox 1', 'Various screwdrivers'),
            ('Power Drill', category_ids['Electrical'], 8, 89.99, 'Used', 'Workshop', '18V cordless drill'),
            ('Wrench Set', category_ids['Hardware'], 10, 45.50, 'New', 'Toolbox 2', 'Metric wrenches'),
            ('Measuring Tape', category_ids['Tools'], 20, 12.99, 'New', 'Warehouse A', '5m tape measure'),
            ('Extension Cord', category_ids['Electrical'], 12, 19.99, 'Used', 'Warehouse B', '10m extension'),
            ('Safety Vest', category_ids['Other'], 5, 15.00, 'New', 'Safety Room', 'High visibility'),
            ('Hard Hat', category_ids['Other'], 7, 29.99, 'New', 'Safety Room', 'White hard hat'),
            ('Glue Gun', category_ids['Tools'], 6, 18.50, 'Used', 'Workshop', 'Hot glue gun'),
            ('Pipe Wrench', category_ids['Plumbing'], 9, 34.99, 'New', 'Storage 1', 'Heavy duty'),
            ('Wire Stripper', category_ids['Electrical'], 14, 12.50, 'New', 'Warehouse B', 'For electrical work'),
        ]
        
        for acc in sample_accessories:
            barcode = DemoManager._generate_barcode()
            cursor.execute('''
                INSERT INTO accessories 
                (name, category_id, quantity, price, quality, location, notes, barcode_value, company_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (acc[0], acc[1], acc[2], acc[3], acc[4], acc[5], acc[6], barcode, company_id,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        print("✅ Demo company created successfully!")
        return company_id
    
    @staticmethod
    def _generate_barcode():
        """Generate a random barcode"""
        prefix = "890"
        random_numbers = ''.join(random.choices(string.digits, k=9))
        barcode_without_checksum = prefix + random_numbers
        total = 0
        for i, digit in enumerate(barcode_without_checksum):
            if i % 2 == 0:
                total += int(digit) * 1
            else:
                total += int(digit) * 3
        checksum = (10 - (total % 10)) % 10
        return barcode_without_checksum + str(checksum)
    
    # ============================================================
    # TRIAL METHODS - ADD THESE
    # ============================================================
    
    @staticmethod
    def get_demo_days_left(company_id):
        """Get number of days left in demo for a company"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if company exists
        cursor.execute("SELECT created_at FROM companies WHERE id = ?", (company_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0
        
        try:
            created_at = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            days_active = (datetime.now() - created_at).days
            days_left = max(0, 30 - days_active)
            return days_left
        except:
            return 0
    
    @staticmethod
    def create_trial_user(email, name, google_uid=None):
        """Create a trial user with 30-day access"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return existing[0]
        
        # Get existing columns
        columns = DemoManager.get_table_columns()
        has_google_uid = 'google_uid' in columns
        has_account_type = 'account_type' in columns
        has_trial_end = 'trial_end_date' in columns
        
        # Create trial company
        cursor.execute(
            "INSERT INTO companies (name, created_at) VALUES (?, ?)",
            (f"Trial: {email[:20]}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        company_id = cursor.lastrowid
        
        # Create trial user
        trial_end = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        hashed_password = hashlib.sha256("trial".encode()).hexdigest()
        
        # Build query dynamically
        fields = ['name', 'email', 'password_hash', 'role', 'company_id', 'created_at']
        placeholders = ['?', '?', '?', '?', '?', '?']
        values = [name, email, hashed_password, 'trial_admin', company_id, 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        if has_account_type:
            fields.append('account_type')
            placeholders.append('?')
            values.append('trial')
        
        if has_trial_end:
            fields.append('trial_end_date')
            placeholders.append('?')
            values.append(trial_end)
        
        if has_google_uid and google_uid:
            fields.append('google_uid')
            placeholders.append('?')
            values.append(google_uid)
        
        query = f"INSERT INTO users ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(query, values)
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Trial user created: {email} (expires: {trial_end})")
        return user_id
    
    @staticmethod
    def get_trial_days_left(user_id):
        """Get days left in trial for a user"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if trial_end_date column exists
        columns = DemoManager.get_table_columns()
        if 'trial_end_date' not in columns:
            conn.close()
            return -1  # Full account, no trial limit
        
        cursor.execute(
            "SELECT trial_end_date, account_type FROM users WHERE id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0
        
        trial_end_str, account_type = result
        
        if account_type != 'trial':
            return -1  # Full account, no trial limit
        
        try:
            trial_end = datetime.strptime(trial_end_str, '%Y-%m-%d %H:%M:%S')
            days_left = (trial_end - datetime.now()).days
            return max(0, days_left)
        except:
            return 0
    
    @staticmethod
    def is_trial_active(user_id):
        """Check if trial is still active"""
        days_left = DemoManager.get_trial_days_left(user_id)
        return days_left > 0
    
    @staticmethod
    def activate_account(user_id, activation_code):
        """Activate a trial account with activation code"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if activation_codes table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activation_codes'")
        if not cursor.fetchone():
            conn.close()
            return False, "Activation codes not set up"
        
        # Verify activation code
        cursor.execute(
            "SELECT id FROM activation_codes WHERE code = ? AND used = 0 AND expires_at > datetime('now')",
            (activation_code,)
        )
        code = cursor.fetchone()
        
        if not code:
            conn.close()
            return False, "Invalid or expired activation code"
        
        # Mark code as used
        cursor.execute(
            "UPDATE activation_codes SET used = 1, used_by = ?, used_at = datetime('now') WHERE code = ?",
            (user_id, activation_code)
        )
        
        # Update user account type
        columns = DemoManager.get_table_columns()
        if 'account_type' in columns and 'trial_end_date' in columns:
            cursor.execute('''
                UPDATE users 
                SET account_type = 'full', trial_end_date = NULL 
                WHERE id = ?
            ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Account activated for user {user_id} with code {activation_code}")
        return True, "Account activated successfully!"
    
    @staticmethod
    def reset_demo():
        """Reset demo data (for testing)"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete demo company and all related data
        cursor.execute("DELETE FROM companies WHERE name = 'Demo Company'")
        cursor.execute("DELETE FROM users WHERE company_id NOT IN (SELECT id FROM companies)")
        cursor.execute("DELETE FROM materials WHERE company_id NOT IN (SELECT id FROM companies)")
        cursor.execute("DELETE FROM accessories WHERE company_id NOT IN (SELECT id FROM companies)")
        cursor.execute("DELETE FROM categories WHERE user_id NOT IN (SELECT id FROM users)")
        
        conn.commit()
        conn.close()
        
        print("✅ Demo reset complete")
