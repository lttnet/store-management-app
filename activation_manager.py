# activation_manager.py
import sqlite3
import hashlib
import random
import string
import uuid
import os
from datetime import datetime, timedelta
from database import DB_PATH

class ActivationManager:
    
    @staticmethod
    def ensure_tables():
        """Ensure activation tables exist with all columns"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Create activation_codes table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activation_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_email TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    device_id TEXT,
                    is_used INTEGER DEFAULT 0,
                    activated_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check if columns exist
            cursor.execute("PRAGMA table_info(activation_codes)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'is_used' not in columns:
                cursor.execute("ALTER TABLE activation_codes ADD COLUMN is_used INTEGER DEFAULT 0")
            
            if 'device_id' not in columns:
                cursor.execute("ALTER TABLE activation_codes ADD COLUMN device_id TEXT")
            
            if 'activated_at' not in columns:
                cursor.execute("ALTER TABLE activation_codes ADD COLUMN activated_at TEXT")
            
            if 'customer_name' not in columns:
                cursor.execute("ALTER TABLE activation_codes ADD COLUMN customer_name TEXT NOT NULL DEFAULT ''")
            
            if 'customer_email' not in columns:
                cursor.execute("ALTER TABLE activation_codes ADD COLUMN customer_email TEXT NOT NULL DEFAULT ''")
            
            if 'company_name' not in columns:
                cursor.execute("ALTER TABLE activation_codes ADD COLUMN company_name TEXT NOT NULL DEFAULT ''")
            
            # Create app_activation table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_activation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT UNIQUE NOT NULL,
                    activation_code TEXT,
                    is_activated INTEGER DEFAULT 0,
                    trial_start TEXT,
                    trial_end TEXT,
                    activated_at TEXT,
                    last_verified TEXT
                )
            ''')
            
            # Check if columns exist in app_activation
            cursor.execute("PRAGMA table_info(app_activation)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'last_verified' not in columns:
                cursor.execute("ALTER TABLE app_activation ADD COLUMN last_verified TEXT")
            
            conn.commit()
            conn.close()
            print("✅ Activation tables verified")
            return True
        except Exception as e:
            print(f"Error creating tables: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_device_id():
        """Get or create a unique device ID"""
        try:
            # Ensure tables exist first
            ActivationManager.ensure_tables()
            
            device_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".device_id")
            if os.path.exists(device_file):
                with open(device_file, 'r') as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id
            
            device_id = str(uuid.uuid4())
            try:
                with open(device_file, 'w') as f:
                    f.write(device_id)
            except:
                pass
            return device_id
            
        except Exception as e:
            print(f"Error getting device ID: {e}")
            import time
            return f"device_{int(time.time())}"
    
    @staticmethod
    def start_trial(device_id, days=30):
        """Start a 30-day trial for a device"""
        try:
            print(f"🔍 Starting trial for device: {device_id}")
            
            # Ensure tables exist
            ActivationManager.ensure_tables()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            print("✅ Database connected")
            
            # Check if already activated
            cursor.execute("SELECT is_activated, trial_end FROM app_activation WHERE device_id = ?", (device_id,))
            result = cursor.fetchone()
            print(f"📊 Existing record: {result}")
            
            if result:
                is_activated, trial_end = result
                if is_activated == 1:
                    conn.close()
                    return {'status': 'activated', 'message': 'App is already activated'}
                
                # Check if trial is still active
                if trial_end:
                    trial_end_date = datetime.strptime(trial_end, '%Y-%m-%d %H:%M:%S')
                    if trial_end_date > datetime.now():
                        days_left = (trial_end_date - datetime.now()).days
                        conn.close()
                        return {'status': 'trial_active', 'days_left': days_left}
            
            # Start new trial
            trial_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            trial_end = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"📝 Inserting trial: start={trial_start}, end={trial_end}")
            
            cursor.execute('''
                INSERT OR REPLACE INTO app_activation 
                (device_id, trial_start, trial_end, is_activated)
                VALUES (?, ?, ?, ?)
            ''', (device_id, trial_start, trial_end, 0))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Trial started successfully: {days} days")
            return {'status': 'trial_started', 'days_left': days}
            
        except Exception as e:
            print(f"❌ Start trial error: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def check_activation_status(device_id):
        """Check the activation status for a device"""
        try:
            # Ensure tables exist
            ActivationManager.ensure_tables()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT is_activated, trial_start, trial_end, activation_code 
                FROM app_activation WHERE device_id = ?
            ''', (device_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return {'status': 'no_trial', 'is_activated': False, 'days_left': 30}
            
            is_activated, trial_start, trial_end, activation_code = result
            
            if is_activated == 1:
                return {
                    'status': 'activated',
                    'is_activated': True,
                    'activation_code': activation_code
                }
            
            # Check trial
            if trial_end:
                trial_end_date = datetime.strptime(trial_end, '%Y-%m-%d %H:%M:%S')
                days_left = (trial_end_date - datetime.now()).days
                
                if days_left > 0:
                    return {
                        'status': 'trial_active',
                        'is_activated': False,
                        'days_left': days_left,
                        'trial_end': trial_end
                    }
                else:
                    return {
                        'status': 'trial_expired',
                        'is_activated': False,
                        'days_left': 0
                    }
            
            return {'status': 'no_trial', 'is_activated': False, 'days_left': 30}
            
        except Exception as e:
            print(f"Check activation error: {e}")
            return {'status': 'no_trial', 'is_activated': False, 'days_left': 30}
    
    @staticmethod
    def activate_app(device_id, activation_code):
        """Activate the app with a valid activation code"""
        try:
            # Ensure tables exist
            ActivationManager.ensure_tables()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Verify activation code
            cursor.execute('''
                SELECT id, customer_name, customer_email, company_name, is_used 
                FROM activation_codes WHERE code = ?
            ''', (activation_code,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {'success': False, 'message': '❌ Invalid activation code'}
            
            code_id, customer_name, customer_email, company_name, is_used = result
            
            if is_used == 1:
                conn.close()
                return {'success': False, 'message': '❌ This activation code has already been used'}
            
            # Check if device is already activated
            cursor.execute("SELECT is_activated FROM app_activation WHERE device_id = ?", (device_id,))
            existing = cursor.fetchone()
            
            if existing and existing[0] == 1:
                conn.close()
                return {'success': False, 'message': '✅ This device is already activated'}
            
            # Activate the device
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if existing:
                cursor.execute('''
                    UPDATE app_activation 
                    SET is_activated = 1, activation_code = ?, activated_at = ?
                    WHERE device_id = ?
                ''', (activation_code, current_time, device_id))
            else:
                cursor.execute('''
                    INSERT INTO app_activation 
                    (device_id, activation_code, is_activated, activated_at)
                    VALUES (?, ?, ?, ?)
                ''', (device_id, activation_code, 1, current_time))
            
            # Mark activation code as used
            cursor.execute('''
                UPDATE activation_codes 
                SET is_used = 1, device_id = ?, activated_at = ?
                WHERE id = ?
            ''', (device_id, current_time, code_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': '✅ App activated successfully!',
                'customer_name': customer_name,
                'company_name': company_name
            }
            
        except Exception as e:
            print(f"Activation error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'❌ Activation error: {str(e)}'}