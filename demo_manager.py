# demo_manager.py - Complete fixed version

import sqlite3
import hashlib
import random
import string
from datetime import datetime, timedelta
from database import DB_PATH

class DemoManager:
    """Manages demo/trial accounts"""
    
    @staticmethod
    def create_demo_company():
        """Create a demo company with sample data (skip if exists)"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # ===== CHECK IF DEMO ALREADY EXISTS =====
        cursor.execute("SELECT id FROM companies WHERE name = 'Demo Company'")
        existing = cursor.fetchone()
        
        if existing:
            company_id = existing[0]
            print(f"✅ Demo company already exists (ID: {company_id})")
            conn.close()
            return company_id
        
        # ===== CREATE DEMO COMPANY =====
        print("📦 Creating demo company...")
        cursor.execute(
            "INSERT INTO companies (name, created_at) VALUES (?, ?)",
            ('Demo Company', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        company_id = cursor.lastrowid
        
        # ===== CREATE USERS =====
        users = [
            ('Demo Admin', 'demo@store.com', 'demo123', 'admin'),
            ('Demo Manager', 'manager@store.com', 'demo123', 'manager'),
            ('Demo User', 'user@store.com', 'demo123', 'user'),
        ]
        
        for name, email, password, role in users:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, hashed_password, role, company_id, 
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            print(f"  👤 Created user: {name} ({role})")
        
        # ===== CREATE CATEGORIES (with duplicate check) =====
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
            # Check if category already exists
            cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
            existing_cat = cursor.fetchone()
            
            if existing_cat:
                category_ids[name] = existing_cat[0]
                print(f"  📁 Category '{name}' already exists")
            else:
                cursor.execute(
                    "INSERT INTO categories (name, icon, user_id, created_at) VALUES (?, ?, ?, ?)",
                    (name, icon, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                category_ids[name] = cursor.lastrowid
                print(f"  📁 Created category: {name}")
        
        # ===== CREATE MATERIALS =====
        materials = [
            ('Steel Rod', 'Metal', 50, 'New', 'Warehouse A', '2m', 2.0, 'Silver', 'High quality steel'),
            ('Copper Wire', 'Electrical', 100, 'New', 'Warehouse B', '100m', 100.0, 'Copper', 'For electrical work'),
            ('PVC Pipe', 'Plumbing', 30, 'Used', 'Storage 1', '3m', 3.0, 'White', 'For plumbing'),
            ('Wood Plank', 'Wood', 25, 'Used', 'Warehouse A', '2.4m', 2.4, 'Brown', 'For construction'),
            ('Screws Set', 'Hardware', 200, 'New', 'Toolbox 1', 'M4x20', None, 'Silver', 'Machine screws'),
            ('Paint Can', 'Other', 15, 'New', 'Storage 2', '1L', None, 'Red', 'Red paint'),
            ('LED Light', 'Electrical', 45, 'New', 'Warehouse B', '10W', None, 'White', 'LED bulbs'),
            ('Hammer', 'Tools', 8, 'Used', 'Toolbox 2', '500g', None, 'Steel', 'Claw hammer'),
            ('Drill Bit Set', 'Tools', 12, 'New', 'Toolbox 1', '1-10mm', None, 'Various', 'For drilling'),
            ('Gloves', 'Other', 35, 'New', 'Safety Room', 'L', None, 'Blue', 'Safety gloves'),
        ]
        
        for mat in materials:
            name, cat_name, qty, quality, location, size, length, colors, notes = mat
            category_id = category_ids.get(cat_name)
            
            if not category_id:
                print(f"  ⚠️ Warning: Category '{cat_name}' not found, skipping {name}")
                continue
            
            barcode = DemoManager._generate_barcode()
            cursor.execute('''
                INSERT INTO materials 
                (name, category_id, quantity, quality, location_ids, size, length, colors, notes, barcode_value, company_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, category_id, qty, quality, location, size, length, colors, notes, barcode, company_id,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            print(f"  📦 Created material: {name}")
        
        # ===== CREATE ACCESSORIES =====
        accessories = [
            ('Screwdriver Set', 'Tools', 15, 25.99, 'New', 'Toolbox 1', 'Various screwdrivers'),
            ('Power Drill', 'Electrical', 8, 89.99, 'Used', 'Workshop', '18V cordless drill'),
            ('Wrench Set', 'Hardware', 10, 45.50, 'New', 'Toolbox 2', 'Metric wrenches'),
            ('Measuring Tape', 'Tools', 20, 12.99, 'New', 'Warehouse A', '5m tape measure'),
            ('Extension Cord', 'Electrical', 12, 19.99, 'Used', 'Warehouse B', '10m extension'),
            ('Safety Vest', 'Other', 5, 15.00, 'New', 'Safety Room', 'High visibility'),
            ('Hard Hat', 'Other', 7, 29.99, 'New', 'Safety Room', 'White hard hat'),
            ('Glue Gun', 'Tools', 6, 18.50, 'Used', 'Workshop', 'Hot glue gun'),
            ('Pipe Wrench', 'Plumbing', 9, 34.99, 'New', 'Storage 1', 'Heavy duty'),
            ('Wire Stripper', 'Electrical', 14, 12.50, 'New', 'Warehouse B', 'For electrical work'),
        ]
        
        for acc in accessories:
            name, cat_name, qty, price, quality, location, notes = acc
            category_id = category_ids.get(cat_name)
            
            if not category_id:
                print(f"  ⚠️ Warning: Category '{cat_name}' not found, skipping {name}")
                continue
            
            barcode = DemoManager._generate_barcode()
            cursor.execute('''
                INSERT INTO accessories 
                (name, category_id, quantity, price, quality, location, notes, barcode_value, company_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, category_id, qty, price, quality, location, notes, barcode, company_id,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            print(f"  🔧 Created accessory: {name}")
        
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
    
    @staticmethod
    def get_demo_days_left(company_id):
        """Get number of days left in demo"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT created_at FROM companies WHERE id = ?", (company_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return 0
        
        created_at = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        days_active = (datetime.now() - created_at).days
        days_left = max(0, 30 - days_active)
        
        return days_left
    
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