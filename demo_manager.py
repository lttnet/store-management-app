# demo_manager.py - Updated with column check

import sqlite3
import hashlib
import random
import string
from datetime import datetime, timedelta
from database import DB_PATH

class DemoManager:
    """Manages demo/trial accounts with Google Sign-In"""
    
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
    def create_trial_user(email, name, google_uid=None):
        """Create a trial user with 30-day access - HANDLES MISSING COLUMNS"""
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
        
        # Create trial user - build dynamic query based on available columns
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
        else:
            # Fallback if columns don't exist
            pass
        
        conn.commit()
        conn.close()
        
        print(f"✅ Account activated for user {user_id} with code {activation_code}")
        return True, "Account activated successfully!"
