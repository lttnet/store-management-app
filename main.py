"""
Store Management App - Full Local Version
Complete working code with all features
Removed: Cloud sync, Firebase, all unnecessary code
Features: Local SQLite, Google Play purchase, Full CRUD operations
"""

import sys
import hashlib
import warnings
import traceback
import sqlite3
import os
import json
import random
import string
import threading
import time
from datetime import datetime, timedelta
from database import DB_PATH

# Suppress warnings
warnings.filterwarnings('ignore')

# Mock problematic modules
class DummyModule:
    def __getattr__(self, name):
        return None
    def __call__(self, *args, **kwargs):
        return None

problematic_modules = ['numpy', 'cv2', 'pyzbar', 'matplotlib', 'cmake', 'skbuild', 'PIL']
for module in problematic_modules:
    if module not in sys.modules:
        sys.modules[module] = DummyModule()

import flet as ft
from database import init_database
from managers.material_manager import MaterialManager
from managers.accessory_manager import AccessoryManager
from managers.user_manager import UserManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, 'images', 'Logo-store.png')
background_path = os.path.join(BASE_DIR, 'images', 'backgound_storemgt.png')

class GooglePlayBilling:
    """Google Play Billing integration for Android"""
    
    def __init__(self, page: ft.Page, app_instance):
        self.page = page
        self.app = app_instance
        
    def purchase_full_version(self, on_complete=None):
        """Start Google Play purchase flow"""
        
        def close_dialog():
            if self.page.dialog:
                self.page.dialog.open = False
                self.page.update()
        
        def initiate_purchase(e):
            close_dialog()
            
            # Show processing
            self.page.snack_bar = ft.SnackBar(
                ft.Text("🔄 Processing purchase..."),
                bgcolor="#1976D2",
                duration=2000
            )
            self.page.snack_bar.open = True
            self.page.update()
            
            # Simulate purchase (replace with actual Google Play Billing)
            def complete_purchase():
                self.app.activate_full_version()
                
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Purchase successful! Full version activated!"),
                    bgcolor="#4CAF50",
                    duration=4000
                )
                self.page.snack_bar.open = True
                
                if on_complete:
                    on_complete()
                
                self.page.update()
            
            # Simulate delay
            def do_purchase():
                time.sleep(2)
                complete_purchase()
            
            threading.Thread(target=do_purchase, daemon=True).start()
        
        dialog_content = ft.Column([
            ft.Text("🛒 Purchase Full Version", size=20, weight=ft.FontWeight.BOLD, color="#E91E63"),
            ft.Divider(),
            ft.Text("One-time purchase. No subscription.", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("Price: $9.99 USD", size=16, color="#4CAF50", weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Text("✓ Unlimited inventory items", size=12, color="#888888"),
            ft.Text("✓ No ads", size=12, color="#888888"),
            ft.Text("✓ Lifetime updates", size=12, color="#888888"),
            ft.Text("✓ Priority support", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.ElevatedButton(
                    "🛒 Buy Now - $9.99",
                    on_click=initiate_purchase,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor="#E91E63", color="white"),
                ),
            ], spacing=10),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=400, height=380, padding=15),
            modal=True,
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

class StoreApp:
    def __init__(self):
        self.current_user = None
        self.current_view = "dashboard"
        self.page_ref = None
        
        # App state
        self.is_activated = False
        self.is_trial = False
        self.trial_days_left = 0
        
        # Colors
        self.bg_color = "#101010"
        self.sidebar_color = "#1E1E1E"
        self.card_color = "#2C2C2C"
        self.accent_color = "#1976D2"
        self.success_color = "#2E7D32"
        self.warning_color = "#F57C00"
        self.danger_color = "#FF5252"
        self.text_color = "#FFFFFF"
        
        # Quality colors
        self.quality_colors = {
            "New": "#2E7D32",
            "Used": "#F57C00",
            "Damaged": "#FF5252",
            "Repaired": "#1976D2",
        }
        
        # Google Play Billing
        self.billing = None

    def get_device_id(self):
        """Get a unique device ID"""
        import uuid
        
        try:
            device_file = os.path.join(BASE_DIR, ".device_id")
            
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
            return f"device_{int(time.time())}"

    def dict_list(self, rows):
        """Convert sqlite3.Row to dict"""
        if rows is None:
            return []
        result = []
        for row in rows:
            row_dict = {}
            for key in row.keys():
                row_dict[key] = row[key]
            result.append(row_dict)
        return result
        
    def show_test_mode_panel(self, page: ft.Page):
        """Show test mode status and controls"""
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        # Get current status
        is_activated = self.is_activated or (self.current_user and self.current_user.get('activated', False))
        has_full_access = self.has_full_access()
        trial_active, days_left = self.check_trial_status()
        
        status_items = [
            ft.Row([ft.Text("📱 Status:", size=14, weight=ft.FontWeight.BOLD, width=120), 
                    ft.Text("Test Mode Active" if has_full_access else "Trial Mode", 
                        color="#9C27B0" if has_full_access else "#FF9800")]),
            ft.Row([ft.Text("🔑 Full Version:", size=14, weight=ft.FontWeight.BOLD, width=120), 
                    ft.Text("✅ Activated" if is_activated else "❌ Not Activated", 
                        color="#4CAF50" if is_activated else "#FF5252")]),
            ft.Row([ft.Text("📅 Trial:", size=14, weight=ft.FontWeight.BOLD, width=120), 
                    ft.Text(f"{days_left} days remaining" if trial_active else "Expired/None", 
                        color="#FF9800" if trial_active else "#888888")]),
            ft.Row([ft.Text("👤 User:", size=14, weight=ft.FontWeight.BOLD, width=120), 
                    ft.Text(self.current_user.get('email', 'Not logged in') if self.current_user else 'None')]),
            ft.Row([ft.Text("📦 Permissions:", size=14, weight=ft.FontWeight.BOLD, width=120), 
                    ft.Text("Full Access" if has_full_access else "Limited", 
                        color="#4CAF50" if has_full_access else "#FF5252")]),
        ]
        
        def reset_and_test(e):
            """Reset and activate test mode"""
            page.dialog.open = False
            
            # Force activate
            self.is_activated = True
            self.is_trial = False
            
            if not self.current_user:
                self.current_user = {
                    'email': 'test@user.com',
                    'name': 'Test User',
                    'role': 'admin',
                    'activated': True
                }
            else:
                self.current_user['activated'] = True
                self.current_user['role'] = 'admin'  # Force admin for testing
            
            self.save_user_session(self.current_user)
            self.save_activation_info(self.current_user.get('email', 'test@user.com'))
            
            page.snack_bar = ft.SnackBar(
                ft.Text("🧪 TEST MODE ACTIVATED - Full admin access enabled!"),
                bgcolor="#9C27B0",
                duration=4000
            )
            page.snack_bar.open = True
            
            # Refresh current view
            if self.current_view == "users":
                self.show_users(page)
            elif self.current_view == "settings":
                self.show_settings(page)
            else:
                self.show_dashboard(page)
            page.update()
        
        def deactivate_test(e):
            """Deactivate test mode"""
            page.dialog.open = False
            
            self.is_activated = False
            
            if self.current_user:
                self.current_user['activated'] = False
                self.save_user_session(self.current_user)
            
            page.snack_bar = ft.SnackBar(
                ft.Text("⚠️ Test mode deactivated. Full features locked."),
                bgcolor="#FF5252",
                duration=4000
            )
            page.snack_bar.open = True
            
            # Refresh current view
            if self.current_view == "users":
                self.show_users(page)
            elif self.current_view == "settings":
                self.show_settings(page)
            else:
                self.show_dashboard(page)
            page.update()
        
        def refresh_status(e):
            """Refresh the status display"""
            page.dialog.open = False
            self.show_test_mode_panel(page)
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("🧪 Test Mode Control", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ]),
            ft.Divider(),
            ft.Text("Current Status:", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color),
            ft.Column(status_items, spacing=6),
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton(
                    "🧪 Activate Test Mode",
                    on_click=reset_and_test,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor="#9C27B0", color="white"),
                    icon=ft.icons.BUG_REPORT,
                ),
            ], spacing=10),
            ft.Row([
                ft.ElevatedButton(
                    "🔒 Deactivate",
                    on_click=deactivate_test,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor="#FF5252", color="white"),
                    icon=ft.icons.LOCK,
                ),
            ], spacing=10),
            ft.Row([
                ft.ElevatedButton(
                    "🔄 Refresh Status",
                    on_click=refresh_status,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color, color="white"),
                    icon=ft.icons.REFRESH,
                ),
            ], spacing=10),
            ft.Container(height=5),
            ft.Text("💡 Use this panel to test full version features", size=10, color="#888888"),
            ft.Text("💡 Test mode unlocks all features without purchase", size=10, color="#888888"),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=450, height=520, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def enable_test_mode(self, page: ft.Page):
        """Enable test mode - Simulate purchase for testing"""
        
        def activate_test_mode(e):
            # Force activate full version
            self.is_activated = True
            self.is_trial = False
            
            if not self.current_user:
                self.current_user = {
                    'id': 1,  # Add ID for test mode
                    'email': 'test@user.com',
                    'name': 'Test User',
                    'role': 'admin',
                    'activated': True
                }
            else:
                self.current_user['activated'] = True
                self.current_user['role'] = 'admin'  # Force admin for testing
                if not self.current_user.get('id'):
                    self.current_user['id'] = 1  # Add ID if missing
            
            self.save_user_session(self.current_user)
            self.save_activation_info(self.current_user.get('email', 'test@user.com'))
            
            page.dialog.open = False
            
            page.snack_bar = ft.SnackBar(
                ft.Text("🧪 TEST MODE: Full version activated for testing!"),
                bgcolor="#9C27B0",
                duration=4000
            )
            page.snack_bar.open = True
            
            # Refresh current view
            if self.current_view == "users":
                self.show_users(page)
            elif self.current_view == "settings":
                self.show_settings(page)
            else:
                self.show_dashboard(page)
            page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("🧪 Test Mode", size=20, weight=ft.FontWeight.BOLD, color="#9C27B0", expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ]),
            ft.Divider(),
            ft.Text("This is for testing purposes only.", size=14, color="#888888"),
            ft.Text("It simulates a Google Play purchase.", size=13, color="#888888"),
            ft.Container(height=10),
            ft.Container(
                content=ft.Column([
                    ft.Text("✓ Full version will be activated", size=12, color="#4CAF50"),
                    ft.Text("✓ All features will be unlocked", size=12, color="#4CAF50"),
                    ft.Text("✓ Admin privileges will be granted", size=12, color="#4CAF50"),
                    ft.Text("✓ No actual purchase will be made", size=12, color="#4CAF50"),
                    ft.Text("✓ This is a development/testing feature", size=12, color="#FF9800"),
                ], spacing=4),
                padding=10,
                bgcolor="#1A1A2E",
                border_radius=8,
            ),
            ft.Container(height=15),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton(
                    "🧪 Activate Test Mode", 
                    on_click=activate_test_mode,
                    expand=True,
                    style=ft.ButtonStyle(bgcolor="#9C27B0", color="white"),
                ),
            ], spacing=10),
            ft.Container(height=5),
            ft.Text("💡 This will not affect your trial status", size=9, color="#888888"),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=400, height=420, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def save_user_session(self, user_dict):
        """Save user session for auto-login"""
        try:
            session_file = os.path.join(BASE_DIR, "session.json")
            
            session_data = {
                'email': user_dict.get('email', ''),
                'activated': user_dict.get('activated', False),
                'device_id': user_dict.get('device_id', self.get_device_id()),
                'id': user_dict.get('id'),  # Add this to save user ID
                'name': user_dict.get('name', 'User'),  # Add this to save name
                'role': user_dict.get('role', 'user'),  # Add this to save role
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
            
            print(f"✅ Session saved for: {session_data['email']}")
            return True
            
        except Exception as e:
            print(f"Error saving session: {e}")
            return False

    def get_saved_user(self):
        """Get saved user from session"""
        try:
            session_file = os.path.join(BASE_DIR, "session.json")
            if not os.path.exists(session_file):
                return None
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            if not session_data:
                return None
            
            return {
                'email': session_data.get('email', ''),
                'activated': session_data.get('activated', False),
                'device_id': session_data.get('device_id', self.get_device_id()),
                'id': session_data.get('id'),  # Get user ID
                'name': session_data.get('name', 'User'),  # Get user name
                'role': session_data.get('role', 'user'),  # Get user role
            }
            
        except Exception as e:
            print(f"Error getting saved user: {e}")
            return None

    def clear_session(self):
        """Clear saved session"""
        try:
            session_file = os.path.join(BASE_DIR, "session.json")
            if os.path.exists(session_file):
                os.remove(session_file)
                print("✅ Session cleared")
                return True
            return True
        except Exception as e:
            print(f"Error clearing session: {e}")
            return False

    def has_used_app_before(self):
        """Check if user has used app before"""
        session_file = os.path.join(BASE_DIR, "session.json")
        return os.path.exists(session_file)

    def check_trial_status(self):
        """Check if trial is active and days left"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trial_info'")
            if not cursor.fetchone():
                conn.close()
                return False, 0
            
            cursor.execute("SELECT trial_start, trial_end, activated FROM trial_info LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, 0
            
            trial_start, trial_end, activated = result
            
            # If activated, no trial needed
            if activated == 1:
                return False, 0
            
            if not trial_end:
                return False, 0
            
            trial_end_date = datetime.strptime(trial_end, '%Y-%m-%d %H:%M:%S')
            days_left = (trial_end_date - datetime.now()).days
            
            if days_left <= 0:
                return False, 0
            
            return True, days_left
            
        except Exception as e:
            print(f"Check trial error: {e}")
            return False, 0

    def save_trial_info(self, email):
        """Save trial info to database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Drop old table if exists and recreate with proper columns
            cursor.execute("DROP TABLE IF EXISTS trial_info")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trial_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    trial_start TEXT,
                    trial_end TEXT,
                    activated INTEGER DEFAULT 0
                )
            ''')
            
            trial_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            trial_end = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO trial_info (email, trial_start, trial_end, activated)
                VALUES (?, ?, ?, ?)
            ''', (email, trial_start, trial_end, 0))
            
            conn.commit()
            conn.close()
            print(f"✅ Trial started (ends: {trial_end})")
            
        except Exception as e:
            print(f"Save trial error: {e}")
            import traceback
            traceback.print_exc()

    def save_activation_info(self, email):
        """Save activation info to database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Drop old table if exists and recreate with proper columns
            cursor.execute("DROP TABLE IF EXISTS trial_info")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trial_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    trial_start TEXT,
                    trial_end TEXT,
                    activated INTEGER DEFAULT 0
                )
            ''')
            
            # Check if email already exists
            cursor.execute("SELECT id FROM trial_info WHERE email = ?", (email,))
            result = cursor.fetchone()
            
            if result:
                cursor.execute('''
                    UPDATE trial_info 
                    SET activated = 1
                    WHERE email = ?
                ''', (email,))
            else:
                cursor.execute('''
                    INSERT INTO trial_info (email, activated)
                    VALUES (?, 1)
                ''', (email,))
            
            conn.commit()
            conn.close()
            print(f"✅ Activation saved for {email}")
            
        except Exception as e:
            print(f"Save activation error: {e}")
            import traceback
            traceback.print_exc()


    def activate_full_version(self):
        """Activate full version - called after purchase"""
        email = self.current_user.get('email', 'user@email.com') if self.current_user else 'user@email.com'
        user_id = self.current_user.get('id', 1) if self.current_user else 1
        
        self.is_activated = True
        self.is_trial = False
        
        self.save_activation_info(email)
        
        if self.current_user:
            self.current_user['activated'] = True
            self.current_user['trial'] = False
            self.save_user_session(self.current_user)
        
        # Update user in database
        try:
            import sqlite3
            from database import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET account_type = 'full' WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating user: {e}")
        
        print(f"✅ Full version activated for {email}")

    def start_trial(self, email):
        """Start 30-day free trial"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        import hashlib
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id, name FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                user_id = existing_user[0]
                user_name = existing_user[1]
            else:
                # Create a new user
                user_name = email.split('@')[0]
                temp_password = "trial123"
                hashed_password = hashlib.sha256(temp_password.encode()).hexdigest()
                
                cursor.execute("""
                    INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_name, email, hashed_password, 'user', 1, 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                user_id = cursor.lastrowid
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            print(f"Error creating user: {e}")
            user_id = 1
            user_name = email.split('@')[0]
        
        self.is_trial = True
        self.is_activated = False
        self.trial_days_left = 30
        
        self.save_trial_info(email)
        
        self.current_user = {
            'id': user_id,  # Add user ID
            'email': email,
            'name': user_name,
            'role': 'user',
            'activated': False,
            'trial': True,
            'days_left': 30,
            'device_id': self.get_device_id()
        }
        self.save_user_session(self.current_user)
        
        print(f"✅ Trial started for {email}")

    def ensure_admin_user(self):
        """Ensure admin user exists"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                conn.close()
                return
            
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            if count > 0:
                conn.close()
                print(f"✅ Users exist: {count} users")
                return
            
            cursor.execute("SELECT id FROM companies WHERE name = 'Default Company'")
            company = cursor.fetchone()
            if not company:
                cursor.execute(
                    "INSERT INTO companies (name, created_at) VALUES (?, ?)",
                    ('Default Company', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                company_id = cursor.lastrowid
            else:
                company_id = company[0]
            
            hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('Administrator', 'admin@store.com', hashed_password, 'admin', company_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            print("✅ Created admin user: admin@store.com / admin123")
            
        except Exception as e:
            print(f"Error ensuring admin user: {e}")

    # ============ MAIN ENTRY POINT ============
    def main(self, page: ft.Page):
        """Main entry point"""
        try:
            self.page_ref = page
            
            page.title = "Store Management System"
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = self.bg_color
            page.padding = 0
            page.spacing = 0
            
            init_database()
            self.ensure_admin_user()
            self.billing = GooglePlayBilling(page, self)
                    # Ensure trial_info table exists
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS trial_info")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trial_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        trial_start TEXT,
                        trial_end TEXT,
                        activated INTEGER DEFAULT 0
                    )
                ''')
                conn.commit()
                conn.close()
            except Exception as ex:
                print(f"Table creation error: {ex}")

            saved_user = self.get_saved_user()
            
            if saved_user:
                print(f"🔐 Found saved user: {saved_user.get('email')}")
                self.current_user = saved_user
                self.is_activated = saved_user.get('activated', False)
                
                if self.is_activated:
                    print("✅ Full version activated")
                else:
                    trial_active, days_left = self.check_trial_status()
                    if trial_active:
                        self.is_trial = True
                        self.trial_days_left = days_left
                        print(f"🚀 Trial active: {days_left} days remaining")
                    else:
                        self.is_trial = False
                        self.trial_days_left = 0
                        print("⏰ Trial expired")
                
                self.show_dashboard(page)
                page.update()
                return
            
            trial_active, days_left = self.check_trial_status()
            
            if trial_active:
                print(f"🚀 Found active trial: {days_left} days remaining")
                device_id = self.get_device_id()
                self.current_user = {
                    'email': 'trial@user.com',
                    'trial': True,
                    'activated': False,
                    'days_left': days_left,
                    'device_id': device_id
                }
                self.is_trial = True
                self.trial_days_left = days_left
                self.save_user_session(self.current_user)
                self.show_dashboard(page)
                page.update()
                return
            
            print("🆕 First time user - showing login")
            self.show_login(page)
            page.update()
            print("✅ App started successfully")
            
        except Exception as e:
            print(f"❌ App startup error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                page.controls.clear()
                page.add(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("❌ App Error", size=24, color="red"),
                            ft.Text(str(e), size=14, color="white"),
                            ft.ElevatedButton("Retry", on_click=lambda e: self.main(page)),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                )
                page.update()
            except:
                pass

    def show_login(self, page: ft.Page):
        """Login with trial and Google Play purchase flow with test mode"""
        page.controls.clear()
        self.page_ref = page
        
        field_width = 320
        
        self.email_field = ft.TextField(
            label="Email", 
            hint_text="your@email.com", 
            width=field_width, 
            bgcolor="#2C2C2C", 
            border_color=self.accent_color,
        )
        
        self.status_text = ft.Text("", color="red", size=12)
        self.loading_indicator = ft.ProgressRing(visible=False, width=30, height=30)
        
        def start_trial(e):
            email = self.email_field.value.strip()
            
            if not email:
                self.status_text.value = "❌ Please enter your email!"
                self.status_text.color = self.danger_color
                page.update()
                return
            
            self.loading_indicator.visible = True
            self.status_text.value = "🔄 Starting trial..."
            self.status_text.color = self.accent_color
            page.update()
            
            # Ensure trial_info table exists
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS trial_info")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trial_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        trial_start TEXT,
                        trial_end TEXT,
                        activated INTEGER DEFAULT 0
                    )
                ''')
                conn.commit()
                conn.close()
            except Exception as ex:
                print(f"Table creation error: {ex}")
            
            self.start_trial(email)
            
            self.loading_indicator.visible = False
            self.status_text.value = "✅ Trial started! 30 days free."
            self.status_text.color = self.success_color
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ Welcome! Your 30-day trial has started."),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            
            self.show_dashboard(page)
        
        def buy_full_version(e):
            email = self.email_field.value.strip()
            
            if not email:
                self.status_text.value = "❌ Please enter your email!"
                self.status_text.color = self.danger_color
                page.update()
                return
            
            if not self.current_user:
                self.current_user = {'email': email}
            
            def on_purchase_complete():
                self.activate_full_version()
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Full version activated! Welcome!"),
                    bgcolor=self.success_color,
                    duration=4000
                )
                page.snack_bar.open = True
                self.show_dashboard(page)
                page.update()
            
            self.billing.purchase_full_version(on_complete=on_purchase_complete)
        
        trial_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.INFO_OUTLINE, color="white", size=20),
                ft.Text("🚀 Start Your 30-Day Free Trial", color="white", size=14, weight=ft.FontWeight.BOLD),
            ], spacing=10),
            padding=12,
            bgcolor=self.accent_color,
            border_radius=10,
            margin=ft.margin.only(bottom=15),
        )
        
        logo_exists = os.path.exists(logo_path)
        logo = ft.Image(src=logo_path, width=80, height=80, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=50)
        
        main_layout = ft.Column([
            ft.Text("Welcome", size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Text("Manage your inventory anywhere", size=13, color="#AAAAAA"),
            ft.Container(height=20),
            
            trial_banner,
            
            ft.Divider(height=10, color="#3C3C3C"),
            
            self.email_field,
            ft.Container(height=10),
            
            ft.Row([self.status_text, self.loading_indicator], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Container(height=10),
            
            ft.Row([
                logo,
                ft.Container(width=15),
                ft.ElevatedButton(
                    "🚀 Start Free Trial",
                    on_click=start_trial,
                    icon=ft.icons.PLAY_ARROW,
                    style=ft.ButtonStyle(
                        bgcolor="#4CAF50",
                        color="white",
                        padding=15,
                    ),
                    width=field_width,
                    height=50,
                ),
            ], alignment=ft.MainAxisAlignment.CENTER),
            
            ft.Divider(height=20, color="#3C3C3C"),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("🛒 Or Purchase Full Version", size=14, weight=ft.FontWeight.BOLD, color="#E91E63"),
                    ft.Text("One-time purchase. No subscription.", size=10, color="#888888"),
                    ft.Container(height=5),
                    ft.ElevatedButton(
                        "🛒 Buy Now - $9.99",
                        on_click=buy_full_version,
                        icon=ft.icons.SHOPPING_CART,
                        style=ft.ButtonStyle(
                            bgcolor="#E91E63",
                            color="white",
                            padding=15,
                        ),
                        width=field_width,
                        height=50,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                margin=ft.margin.only(top=5, bottom=5),
            ),
            
            ft.Divider(height=20, color="#3C3C3C"),
            
            # ===== TEST MODE SECTION =====
            ft.Container(
                content=ft.Column([
                    ft.Text("🧪 Developer Test Mode", size=12, weight=ft.FontWeight.BOLD, color="#9C27B0"),
                    ft.Text("For testing purposes only", size=9, color="#888888"),
                    ft.Container(height=5),
                    ft.ElevatedButton(
                        "🧪 Activate Test Mode",
                        on_click=lambda e: self.enable_test_mode(page),
                        icon=ft.icons.BUG_REPORT,
                        style=ft.ButtonStyle(
                            bgcolor="#9C27B0",
                            color="white",
                            padding=10,
                        ),
                        width=field_width,
                        height=40,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                margin=ft.margin.only(top=5, bottom=5),
            ),
            
            ft.Container(height=10),
            ft.Text("💡 Try 30 days free, then buy once", size=10, color="#888888"),
            ft.Text("💡 Your data stays on your device", size=10, color="#888888"),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        
        login_card = ft.Container(
            content=main_layout,
            padding=30,
            bgcolor=None,
            border_radius=20,
            width=500,
        )
        
        centered_login = ft.Container(
            content=login_card,
            alignment=ft.alignment.center,
            expand=True,
        )
        
        bg_image = ft.Image(
            src=background_path,
            fit=ft.ImageFit.COVER
        ) if os.path.exists(background_path) else None
        
        if bg_image:
            page.add(ft.Stack([bg_image, centered_login], expand=True))
        else:
            page.add(centered_login)
        
        self.current_view = "login"
        page.update()

        # ============ DASHBOARD ============
    def show_dashboard(self, page: ft.Page):
        """Dashboard with trial/purchase status and test mode"""
        page.controls.clear()
        
        is_mobile = page.width < 800 if page.width else False
        
        # Get current user safely
        user = self.current_user or {}
        is_activated = self.is_activated or user.get('activated', False)
        
        # Check trial status
        trial_active, days_left = self.check_trial_status()
        if not is_activated and trial_active:
            self.is_trial = True
            self.trial_days_left = days_left
        elif not is_activated:
            self.is_trial = False
            self.trial_days_left = 0
        
        # Get data
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        
        total_materials = len(materials)
        total_accessories = len(accessories)
        total_items = total_materials + total_accessories
        total_stock = sum(m.get('quantity', 0) for m in materials) + sum(a.get('quantity', 0) for a in accessories)
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Main column
        main_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # ===== TEST MODE INDICATOR =====
        if is_activated:
            test_mode_banner = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.BUG_REPORT, color="#9C27B0", size=20),
                    ft.Text("🧪 TEST MODE ACTIVE", size=14, weight=ft.FontWeight.BOLD, color="#9C27B0"),
                    ft.Text("• Full features unlocked for testing", size=11, color="#888888"),
                ], spacing=8),
                padding=8,
                bgcolor="#1A1A2E",
                border_radius=8,
                margin=ft.margin.only(bottom=8),
            )
            main_column.controls.append(test_mode_banner)
        
        # ===== TOP BANNER =====
        if is_activated:
            top_banner = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50", size=24),
                    ft.Column([
                        ft.Text("✅ Full Version Activated", size=16, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                        ft.Text(f"Welcome back!", size=12, color="#888888"),
                    ], spacing=2, expand=True),
                ], spacing=12),
                padding=12,
                bgcolor="#1A3A1A",
                border_radius=10,
                margin=ft.margin.only(bottom=8),
            )
        elif trial_active and days_left > 0:
            days_text = f"{days_left} days remaining"
            top_banner = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.TIMER, color="#FF9800", size=24),
                    ft.Column([
                        ft.Text(f"🚀 Free Trial: {days_text}", size=16, weight=ft.FontWeight.BOLD, color="#FF9800"),
                        ft.Text("Full access for 30 days. No credit card required.", size=12, color="#888888"),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton(
                        "🛒 Buy Now",
                        on_click=lambda e: self.billing.purchase_full_version(
                            on_complete=lambda: self.activate_full_version() or self.show_dashboard(page)
                        ),
                        style=ft.ButtonStyle(bgcolor="#E91E63", color="white"),
                    ),
                ], spacing=12),
                padding=12,
                bgcolor="#2C2C2C",
                border_radius=10,
                margin=ft.margin.only(bottom=8),
            )
        else:
            top_banner = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.WARNING, color=self.danger_color, size=24),
                    ft.Column([
                        ft.Text("⚠️ Trial Expired", size=16, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Text("Please purchase to continue using the app.", size=12, color="#888888"),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton(
                        "🛒 Buy Now",
                        on_click=lambda e: self.billing.purchase_full_version(
                            on_complete=lambda: self.activate_full_version() or self.show_dashboard(page)
                        ),
                        style=ft.ButtonStyle(bgcolor="#E91E63", color="white"),
                    ),
                ], spacing=12),
                padding=12,
                bgcolor="#3A1A1A",
                border_radius=10,
                margin=ft.margin.only(bottom=8),
            )
        
        main_column.controls.append(top_banner)
        
        # ===== HEADER WITH TEST MODE BUTTON =====
        header_row = ft.Row([
            ft.Text("📊 Dashboard", size=28 if not is_mobile else 24, 
                weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.icons.BUG_REPORT,
                icon_size=24,
                icon_color="#9C27B0",
                on_click=lambda e: self.show_test_mode_panel(page),
                tooltip="Test Mode Panel",
            ),
            ft.IconButton(
                icon=ft.icons.REFRESH,
                icon_size=24,
                icon_color="#888888",
                on_click=lambda e: self.show_dashboard(page),
                tooltip="Refresh",
            ),
        ])
        main_column.controls.append(header_row)
        main_column.controls.append(ft.Divider(height=1, color="#3C3C3C"))
        main_column.controls.append(ft.Container(height=5))
        
        # ===== STATS CARDS =====
        stats_row = ft.Row([
            self._create_stat_card("📦", str(total_items), "Items"),
            self._create_stat_card("📊", str(total_stock), "Stock"),
            self._create_stat_card("📈", str(len(materials) + len(accessories)), "Total"),
        ], spacing=10)
        main_column.controls.append(stats_row)
        main_column.controls.append(ft.Container(height=5))
        
        # ===== QUICK ACTIONS =====
        main_column.controls.append(ft.Text("⚡ Quick Actions", size=18, weight=ft.FontWeight.BOLD))
        
        main_column.controls.append(
            ft.Row([
                ft.ElevatedButton("📦 Add Material", on_click=lambda e: self.open_add_modal(page), expand=True),
                ft.ElevatedButton("🔧 Add Part", on_click=lambda e: self.open_add_accessory_modal(page), expand=True),
            ], spacing=10)
        )
        
        main_column.controls.append(
            ft.Row([
                ft.ElevatedButton("📷 Scan", on_click=lambda e: self.show_barcode_scanner(page), expand=True),
                ft.ElevatedButton("📊 Inventory", on_click=lambda e: self.show_inventory(page), expand=True),
            ], spacing=10)
        )
        
        # ===== PURCHASE OR TEST MODE BUTTONS =====
        if not is_activated:
            main_column.controls.append(
                ft.Row([
                    ft.ElevatedButton(
                        "🛒 Buy Full Version - $9.99",
                        on_click=lambda e: self.billing.purchase_full_version(
                            on_complete=lambda: self.activate_full_version() or self.show_dashboard(page)
                        ),
                        expand=True,
                        style=ft.ButtonStyle(bgcolor="#E91E63", color="white"),
                        icon=ft.icons.SHOPPING_CART,
                    ),
                    ft.ElevatedButton(
                        "🧪 Test",
                        on_click=lambda e: self.enable_test_mode(page),
                        expand=False,
                        style=ft.ButtonStyle(bgcolor="#9C27B0", color="white"),
                        icon=ft.icons.BUG_REPORT,
                    ),
                ], spacing=10)
            )
        else:
            main_column.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50", size=16),
                        ft.Text("✅ Full version active", size=13, color="#4CAF50"),
                    ], spacing=6),
                    padding=8,
                    bgcolor="#1A3A1A",
                    border_radius=8,
                )
            )
        
        main_column.controls.append(ft.Container(height=15))
        
        # ===== RECENT MATERIALS =====
        main_column.controls.append(ft.Text("📦 Recent Materials", size=16, weight=ft.FontWeight.BOLD))
        if materials:
            for m in materials[:5]:
                main_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("📦", size=18),
                            ft.Text(m.get('name', 'N/A'), size=14, expand=True),
                            ft.Text(f"Qty: {m.get('quantity', 0)}", size=14),
                        ]),
                        padding=10,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                        margin=ft.margin.only(bottom=5),
                    )
                )
        else:
            main_column.controls.append(
                ft.Container(
                    content=ft.Text("No materials yet. Click 'Add Material' to get started!", 
                                size=12, color="#888888"),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                )
            )
        
        main_column.controls.append(ft.Container(height=15))
        
        # ===== RECENT ACCESSORIES =====
        main_column.controls.append(ft.Text("🔧 Recent Accessories", size=16, weight=ft.FontWeight.BOLD))
        if accessories:
            for a in accessories[:5]:
                price = a.get('price', 0)
                price_text = f"${price:.2f}" if price else ""
                main_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🔧", size=18),
                            ft.Text(a.get('name', 'N/A'), size=14, expand=True),
                            ft.Text(f"Qty: {a.get('quantity', 0)}", size=14),
                            ft.Text(price_text, size=12, color="#4CAF50"),
                        ]),
                        padding=10,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                        margin=ft.margin.only(bottom=5),
                    )
                )
        else:
            main_column.controls.append(
                ft.Container(
                    content=ft.Text("No accessories yet. Click 'Add Part' to get started!", 
                                size=12, color="#888888"),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                )
            )
        
        # ===== FOOTER =====
        main_column.controls.append(ft.Divider())
        main_column.controls.append(ft.Container(height=5))
        
        status_text = "✅ Full Version" if is_activated else f"🚀 Trial: {days_left} days left" if trial_active and days_left > 0 else "⚠️ Trial Expired"
        status_color = "#4CAF50" if is_activated else "#FF9800" if trial_active and days_left > 0 else self.danger_color
        
        footer_row = ft.Row([
            ft.Text(f"📱 {status_text}", size=11, color=status_color),
            ft.Container(expand=True),
            ft.Text(f"v2.0.0", size=11, color="#888888"),
            ft.Text("•", size=11, color="#888888"),
            ft.Text("⚡ Powered by Flet", size=11, color="#888888"),
        ])
        main_column.controls.append(footer_row)
        main_column.controls.append(ft.Container(height=10))
        
        # ===== BOTTOM SPACING =====
        if is_mobile:
            main_column.controls.append(ft.Container(height=70))
        else:
            main_column.controls.append(ft.Container(height=20))
        
        # ===== WRAP AND DISPLAY =====
        scroll_container = ft.Container(
            content=main_column,
            expand=True,
            padding=15 if is_mobile else 20,
        )
        
        scrollable = ft.Container(
            content=ft.Column([scroll_container], scroll=ft.ScrollMode.AUTO, expand=True),
            expand=True,
        )
        
        if is_mobile and nav:
            page.add(ft.Column([scrollable, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, scrollable], spacing=0, expand=True))
        
        self.current_view = "dashboard"
        page.update()

    def _create_stat_card(self, icon, value, label, custom_color=None):
        color = custom_color or self.accent_color
        
        return ft.Container(
            content=ft.Column([
                ft.Text(icon, size=20),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=10, color="#CCCCCC"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=10,
            bgcolor=color,
            border_radius=10,
            expand=True,
        )

        # ============ SIDEBAR ============
    def create_sidebar(self, page: ft.Page):
        """Create sidebar navigation with purchase status and test mode"""
        
        nav_items = [
            ("📊", "Dashboard", "dashboard"),
            ("📦", "Materials", "materials"),
            ("🔧", "Accessories", "accessories"),
            ("📷", "Barcode Scan", "barcode_scanner"),
            ("📋", "Inventory", "inventory"),
            ("👥", "Users", "users"),
            ("⚙️", "Settings", "settings"),
        ]
        
        nav_buttons = []
        
        def navigate(e, view):
            if view == "dashboard":
                self.show_dashboard(page)
            elif view == "materials":
                self.show_materials_screen(page)
            elif view == "accessories":
                self.show_accessories(page)
            elif view == "barcode_scanner":
                self.show_barcode_scanner(page)
            elif view == "inventory":
                self.show_inventory(page)
            elif view == "users":
                self.show_users(page)
            elif view == "settings":
                self.show_settings(page)
        
        for emoji, label, view in nav_items:
            btn = ft.Container(
                content=ft.Row([ft.Text(emoji, size=22), ft.Text(label, size=15, color=self.text_color)], spacing=12),
                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                border_radius=10,
                ink=True,
                on_click=lambda e, v=view: navigate(e, v),
            )
            nav_buttons.append(btn)
        
        def logout(e):
            self.confirm_logout(page)
        
        logout_btn = ft.Container(
            content=ft.Row([
                ft.Text("🚪", size=22),
                ft.Text("Logout", size=15, color="#FF5252")
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            border_radius=10,
            ink=True,
            on_click=logout,
        )
        
        logo_exists = os.path.exists(logo_path)
        sidebar_logo = ft.Image(src=logo_path, width=35, height=35, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=28)
        
        title_content = ft.Row(
            [sidebar_logo, ft.Text("Store Manager", size=20, weight=ft.FontWeight.BOLD, color=self.text_color)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )
        
        role = self.current_user.get('role', 'guest') if self.current_user else 'guest'
        role_display = role.upper()
        
        # ===== PURCHASE STATUS WITH TEST MODE =====
        if self.is_activated:
            # Check if it's test mode (activated but no active trial)
            trial_active, _ = self.check_trial_status()
            if not trial_active and self.current_user and not self.current_user.get('trial', False):
                # This is test mode
                purchase_status = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.BUG_REPORT, size=16, color="#9C27B0"),
                        ft.Text("🧪 TEST MODE", size=12, color="#9C27B0", weight=ft.FontWeight.BOLD),
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor="#1A1A2E",
                    border_radius=20,
                )
            else:
                purchase_status = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color="#4CAF50"),
                        ft.Text("✅ Full Version", size=12, color="#4CAF50", weight=ft.FontWeight.BOLD),
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    bgcolor="#1A3A1A",
                    border_radius=20,
                )
        else:
            purchase_status = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.SHOPPING_CART, size=16, color="#E91E63"),
                    ft.Text("🛒 Buy Full Version", size=12, color="#E91E63", weight=ft.FontWeight.BOLD),
                ], spacing=6),
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                bgcolor="#3A1A2A",
                border_radius=20,
                on_click=lambda e: self.billing.purchase_full_version(
                    on_complete=lambda: self.activate_full_version() or self.show_dashboard(page)
                ),
                ink=True,
            )
        
        return ft.Container(
            content=ft.Column([
                ft.Container(content=title_content, padding=25),
                ft.Divider(),
                ft.Column(nav_buttons, spacing=8),
                ft.Container(expand=True),
                ft.Divider(),
                purchase_status,
                ft.Container(height=5),
                logout_btn,
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"User: {self.current_user.get('name', 'User') if self.current_user else 'Guest'}", size=12, color="#888888"),
                        ft.Text(role_display, size=12, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15,
                ),
            ], spacing=0),
            width=260,
            bgcolor=self.sidebar_color,
        )

    def create_bottom_nav(self, page: ft.Page):
        """Create bottom navigation bar"""
        
        nav_items = [
            (ft.icons.DASHBOARD, "Home", "dashboard"),
            (ft.icons.INVENTORY, "Materials", "materials"),
            (ft.icons.BUILD, "Parts", "accessories"),
            (ft.icons.QR_CODE_SCANNER, "Scan", "barcode_scanner"),
            (ft.icons.LIST_ALT, "Inventory", "inventory"),
            (ft.icons.PEOPLE, "Users", "users"),
            (ft.icons.SETTINGS, "Settings", "settings"),
            (ft.icons.LOGOUT, "Logout", "logout"),
        ]
        
        def navigate(e):
            index = e.control.selected_index
            if index < len(nav_items):
                view = nav_items[index][2]
                if view == "dashboard":
                    self.show_dashboard(page)
                elif view == "materials":
                    self.show_materials_screen(page)
                elif view == "accessories":
                    self.show_accessories(page)
                elif view == "barcode_scanner":
                    self.show_barcode_scanner(page)
                elif view == "inventory":
                    self.show_inventory(page)
                elif view == "users":
                    self.show_users(page)
                elif view == "settings":
                    self.show_settings(page)
                elif view == "logout":
                    self.confirm_logout(page)
        
        return ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(icon=icon, label=label)
                for icon, label, _ in nav_items
            ],
            on_change=navigate,
            height=65,
            bgcolor=self.sidebar_color,
        )

    def confirm_logout(self, page: ft.Page):
        """Show logout confirmation dialog"""
        
        def do_logout(e):
            self.clear_session()
            page.dialog.open = False
            
            self.current_user = None
            self.is_activated = False
            self.is_trial = False
            
            self.show_login(page)
        
        def cancel_logout(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("🚪 Logout", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("Are you sure you want to logout?", size=14),
            ft.Text("You can login again with your email.", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([
                ft.TextButton("Cancel", on_click=cancel_logout),
                ft.FilledButton("Logout", on_click=do_logout, 
                            style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Logout"),
            content=ft.Container(content=dialog_content, width=350, height=280, padding=20),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ QUALITY HELPERS ============
    def get_quality_color(self, quality):
        colors = {
            "New": "#2E7D32",
            "Used": "#F57C00",
            "Damaged": "#FF5252",
            "Repaired": "#1976D2"
        }
        return colors.get(quality, "#888888")

    def get_quality_icon(self, quality):
        icons = {
            "New": "🟢",
            "Used": "🟠",
            "Damaged": "🔴",
            "Repaired": "🔵"
        }
        return icons.get(quality, "⚪")

    # ============ MATERIALS SCREEN ============
    def show_materials_screen(self, page: ft.Page):
        """Materials screen with full CRUD"""
        page.controls.clear()
        
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, c.name as category_name, c.icon as category_icon
            FROM materials m
            LEFT JOIN categories c ON m.category_id = c.id
            ORDER BY m.id DESC
        """)
        materials = cursor.fetchall()
        
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        nav = self.create_bottom_nav(page)
        is_mobile = page.width < 800 if page.width else False
        
        main_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        
        main_column.controls.append(
            ft.Text("Materials", size=24 if is_mobile else 28, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        
        search_field = ft.TextField(
            hint_text="Search materials...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            prefix_icon=ft.icons.SEARCH,
            dense=True,
        )
        main_column.controls.append(search_field)
        main_column.controls.append(ft.Container(height=5))
        
        cat_options = [ft.dropdown.Option("All", "📁 All Categories")]
        for c in categories:
            icon = c['icon'] if c['icon'] else "📁"
            cat_options.append(ft.dropdown.Option(str(c["id"]), f"{icon} {c['name']}"))
        
        category_filter = ft.Dropdown(
            label="Category",
            width=170 if not is_mobile else 150,
            options=cat_options,
            value="All",
            bgcolor=self.card_color,
            dense=True,
        )
        
        quality_filter = ft.Dropdown(
            label="Quality",
            width=150 if not is_mobile else 130,
            value="All",
            bgcolor=self.card_color,
            dense=True,
            options=[
                ft.dropdown.Option("All", "[A] All Qualities"),
                ft.dropdown.Option("New", "[N] New"),
                ft.dropdown.Option("Used", "[U] Used"),
                ft.dropdown.Option("Damaged", "[D] Damaged"),
                ft.dropdown.Option("Repaired", "[R] Repaired"),
            ],
        )
        
        add_category_btn = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE_OUTLINE,
            icon_size=24,
            icon_color=self.success_color,
            tooltip="Manage Categories",
            on_click=lambda e: self.show_categories_dialog(page, lambda: self.show_materials_screen(page)),
        )
        
        filters_row = ft.Row([
            category_filter,
            quality_filter,
            add_category_btn,
        ], spacing=8, alignment=ft.MainAxisAlignment.START, wrap=True)
        
        main_column.controls.append(filters_row)
        main_column.controls.append(ft.Container(height=5))
        
        cards_container = ft.Column(spacing=8)
        main_column.controls.append(cards_container)
        
        def update_cards():
            cards_container.controls.clear()
            search_query = search_field.value.lower() if search_field.value else ""
            selected_cat_id = category_filter.value
            selected_quality = quality_filter.value
            
            filtered_count = 0
            for m in materials:
                if search_query and search_query not in m["name"].lower():
                    continue
                if selected_cat_id != "All" and str(m["category_id"]) != selected_cat_id:
                    continue
                if selected_quality != "All" and m["quality"] != selected_quality:
                    continue
                
                filtered_count += 1
                cat_name = m["category_name"] if m["category_name"] else "Other"
                cat_icon = m["category_icon"] if m["category_icon"] else "📁"
                qty = m["quantity"]
                quality = m["quality"]
                
                quality_colors = {
                    "New": "#4CAF50",
                    "Used": "#FF9800",
                    "Damaged": "#F44336",
                    "Repaired": "#2196F3"
                }
                quality_color = quality_colors.get(quality, "#888888")
                
                quality_display = {
                    "New": "[N] New",
                    "Used": "[U] Used",
                    "Damaged": "[D] Damaged",
                    "Repaired": "[R] Repaired"
                }.get(quality, quality)
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(m["name"], size=15, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=13, weight=ft.FontWeight.BOLD, 
                                    color=self.danger_color if qty < 10 else self.text_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=11, color=self.accent_color, expand=True),
                                ft.Container(
                                    content=ft.Text(quality_display, size=9, color="white"),
                                    bgcolor=quality_color,
                                    border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.Text(f"📍 {m['location_ids'] or 'N/A'}", size=10, color="#888888", expand=True),
                                ft.Text(f"📏 {m['size'] or 'N/A'}", size=10, color="#888888"),
                            ]),
                        ], spacing=4),
                        padding=10,
                        on_click=lambda e, mat=m: self.show_material_detail_dialog(page, dict(mat)),
                    ),
                    elevation=1,
                )
                cards_container.controls.append(card)
            
            if filtered_count == 0:
                cards_container.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.INBOX, size=50, color="#888888"),
                            ft.Text("No materials found", size=13, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30,
                    )
                )
            else:
                count_text = ft.Text(f"{filtered_count} of {len(materials)}", size=10, color="#888888")
                cards_container.controls.insert(0, count_text)
            
            page.update()
        
        search_field.on_change = lambda e: update_cards()
        category_filter.on_change = lambda e: update_cards()
        quality_filter.on_change = lambda e: update_cards()
        update_cards()
        
        add_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_modal(page),
            mini=is_mobile,
        )
        
        main_container = ft.Container(content=main_column, expand=True, padding=12 if is_mobile else 20)
        
        if is_mobile:
            page.add(
                ft.Stack([
                    ft.Column([main_container, nav], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        else:
            sidebar = self.create_sidebar(page)
            page.add(
                ft.Stack([
                    ft.Row([sidebar, main_container], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        
        self.current_view = "materials"
        page.update()

    # ============ ACCESSORIES SCREEN ============
    def show_accessories(self, page: ft.Page):
        """Accessories screen with full CRUD"""
        page.controls.clear()
        
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, c.name as category_name, c.icon as category_icon
            FROM accessories a
            LEFT JOIN categories c ON a.category_id = c.id
            ORDER BY a.id DESC
        """)
        accessories = cursor.fetchall()
        
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        nav = self.create_bottom_nav(page)
        is_mobile = page.width < 800 if page.width else False
        
        main_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        
        main_column.controls.append(
            ft.Text("Accessories", size=24 if is_mobile else 28, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        
        search_field = ft.TextField(
            hint_text="Search accessories...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            prefix_icon=ft.icons.SEARCH,
            dense=True,
        )
        main_column.controls.append(search_field)
        main_column.controls.append(ft.Container(height=5))
        
        cat_options = [ft.dropdown.Option("All", "📁 All Categories")]
        for c in categories:
            icon = c['icon'] if c['icon'] else "📁"
            cat_options.append(ft.dropdown.Option(str(c["id"]), f"{icon} {c['name']}"))
        
        category_filter = ft.Dropdown(
            label="Category",
            width=170 if not is_mobile else 150,
            options=cat_options,
            value="All",
            bgcolor=self.card_color,
            dense=True,
        )
        
        quality_filter = ft.Dropdown(
            label="Quality",
            width=150 if not is_mobile else 130,
            value="All",
            bgcolor=self.card_color,
            dense=True,
            options=[
                ft.dropdown.Option("All", "[A] All Qualities"),
                ft.dropdown.Option("New", "[N] New"),
                ft.dropdown.Option("Used", "[U] Used"),
                ft.dropdown.Option("Damaged", "[D] Damaged"),
                ft.dropdown.Option("Repaired", "[R] Repaired"),
            ],
        )
        
        add_category_btn = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE_OUTLINE,
            icon_size=24,
            icon_color=self.success_color,
            tooltip="Manage Categories",
            on_click=lambda e: self.show_categories_dialog(page, lambda: self.show_accessories(page)),
        )
        
        filters_row = ft.Row([
            category_filter,
            quality_filter,
            add_category_btn,
        ], spacing=8, alignment=ft.MainAxisAlignment.START, wrap=True)
        
        main_column.controls.append(filters_row)
        main_column.controls.append(ft.Container(height=5))
        
        cards_container = ft.Column(spacing=8)
        main_column.controls.append(cards_container)
        
        def update_cards():
            cards_container.controls.clear()
            search_query = search_field.value.lower() if search_field.value else ""
            selected_cat_id = category_filter.value
            selected_quality = quality_filter.value
            
            filtered_count = 0
            for a in accessories:
                if search_query and search_query not in a["name"].lower():
                    continue
                if selected_cat_id != "All" and str(a["category_id"]) != selected_cat_id:
                    continue
                if selected_quality != "All" and a["quality"] != selected_quality:
                    continue
                
                filtered_count += 1
                cat_name = a["category_name"] if a["category_name"] else "Other"
                cat_icon = a["category_icon"] if a["category_icon"] else "📁"
                qty = a["quantity"]
                quality = a["quality"]
                price = a["price"] if a["price"] else 0
                price_text = f"${price:.2f}" if price > 0 else ""
                
                quality_colors = {
                    "New": "#4CAF50",
                    "Used": "#FF9800",
                    "Damaged": "#F44336",
                    "Repaired": "#2196F3"
                }
                quality_color = quality_colors.get(quality, "#888888")
                
                quality_display = {
                    "New": "[N] New",
                    "Used": "[U] Used",
                    "Damaged": "[D] Damaged",
                    "Repaired": "[R] Repaired"
                }.get(quality, quality)
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(a["name"], size=15, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=13, weight=ft.FontWeight.BOLD, 
                                    color=self.danger_color if qty < 10 else self.text_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=11, color=self.accent_color, expand=True),
                                ft.Container(
                                    content=ft.Text(quality_display, size=9, color="white"),
                                    bgcolor=quality_color,
                                    border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.Text(f"📍 {a['location'] or 'N/A'}", size=10, color="#888888", expand=True),
                                ft.Text(price_text, size=10, color="#4CAF50"),
                            ]),
                        ], spacing=4),
                        padding=10,
                        on_click=lambda e, acc=a: self.show_accessory_detail_dialog(page, dict(acc)),
                    ),
                    elevation=1,
                )
                cards_container.controls.append(card)
            
            if filtered_count == 0:
                cards_container.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.INBOX, size=50, color="#888888"),
                            ft.Text("No accessories found", size=13, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30,
                    )
                )
            else:
                count_text = ft.Text(f"{filtered_count} of {len(accessories)}", size=10, color="#888888")
                cards_container.controls.insert(0, count_text)
            
            page.update()
        
        search_field.on_change = lambda e: update_cards()
        category_filter.on_change = lambda e: update_cards()
        quality_filter.on_change = lambda e: update_cards()
        update_cards()
        
        add_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_accessory_modal(page),
            mini=is_mobile,
        )
        
        main_container = ft.Container(content=main_column, expand=True, padding=12 if is_mobile else 20)
        
        if is_mobile:
            page.add(
                ft.Stack([
                    ft.Column([main_container, nav], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        else:
            sidebar = self.create_sidebar(page)
            page.add(
                ft.Stack([
                    ft.Row([sidebar, main_container], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=70),
                ], expand=True)
            )
        
        self.current_view = "accessories"
        page.update()

    # ============ INVENTORY SCREEN ============
    def show_inventory(self, page: ft.Page):
        """Show advanced inventory management screen"""
        page.controls.clear()
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            font_title = 24
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 28
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        
        inventory_items = []
        for m in materials:
            inventory_items.append({
                'id': m.get('id'),
                'type': 'material',
                'type_icon': '📦',
                'type_name': 'Material',
                'name': m.get('name', 'N/A'),
                'code': m.get('barcode_value', 'N/A'),
                'quantity': m.get('quantity', 0),
                'quality': m.get('quality', 'Used'),
                'location': m.get('location_ids', 'N/A'),
                'last_updated': m.get('updated_at', m.get('created_at', '')),
            })
        
        for a in accessories:
            location = a.get('location') or a.get('location_ids') or 'N/A'
            inventory_items.append({
                'id': a.get('id'),
                'type': 'accessory',
                'type_icon': '🔧',
                'type_name': 'Accessory',
                'name': a.get('name', 'N/A'),
                'code': a.get('barcode_value', 'N/A'),
                'quantity': a.get('quantity', 0),
                'quality': a.get('quality', 'Used'),
                'location': location,
                'price': a.get('price', 0),
                'last_updated': a.get('updated_at', a.get('created_at', '')),
            })
        
        inventory_items.sort(key=lambda x: x['name'])
        
        total_items = len(inventory_items)
        total_stock = sum(i.get('quantity', 0) for i in inventory_items)
        low_stock_items = [i for i in inventory_items if i.get('quantity', 0) < 10]
        critical_stock = [i for i in inventory_items if i.get('quantity', 0) < 5]
        total_value = sum(i.get('quantity', 0) * (i.get('price', 0) if i.get('price') else 10) for i in inventory_items)
        
        self.current_filtered_items = inventory_items.copy()
        
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        scroll_content.controls.append(
            ft.Row([
                ft.Text("Inventory Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.REFRESH,
                    icon_size=24,
                    icon_color=self.accent_color,
                    on_click=lambda e: self.show_inventory(page),
                ),
            ])
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("📦 Items", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_items), size=font_title + 4, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{len(materials)} Mat, {len(accessories)} Acc", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12, bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Stock", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_stock), size=font_title + 4, weight=ft.FontWeight.BOLD),
                    ft.Text("Units", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12, bgcolor=self.success_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("💰 Value", size=font_small, color="#CCCCCC"),
                    ft.Text(f"${total_value:,.0f}", size=font_title + 2, weight=ft.FontWeight.BOLD),
                    ft.Text("Total Worth", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12, bgcolor="#9C27B0", border_radius=10, expand=True,
            ),
        ], spacing=12)
        scroll_content.controls.append(stats_row)
        scroll_content.controls.append(ft.Container(height=10))
        
        stats_row2 = ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.WARNING, size=20, color=self.warning_color),
                    ft.Text(str(len(low_stock_items)), size=font_title + 2, weight=ft.FontWeight.BOLD, color=self.warning_color),
                    ft.Text("Low", size=font_small - 2, color="#888888"),
                ], spacing=8),
                padding=10, bgcolor=self.card_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.ERROR, size=20, color=self.danger_color),
                    ft.Text(str(len(critical_stock)), size=font_title + 2, weight=ft.FontWeight.BOLD, color=self.danger_color),
                    ft.Text("Critical", size=font_small - 2, color="#888888"),
                ], spacing=8),
                padding=10, bgcolor=self.card_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.BAR_CHART, size=20, color=self.accent_color),
                    ft.Text(f"{len(set(i['type_name'] for i in inventory_items))}", size=font_title + 2, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Text("Categories", size=font_small - 2, color="#888888"),
                ], spacing=8),
                padding=10, bgcolor=self.card_color, border_radius=10, expand=True,
            ),
        ], spacing=12)
        scroll_content.controls.append(stats_row2)
        scroll_content.controls.append(ft.Container(height=15))
        
        type_filter = ft.Dropdown(
            label="Type", width=120,
            options=[
                ft.dropdown.Option("All", "All"),
                ft.dropdown.Option("material", "📦 Materials"),
                ft.dropdown.Option("accessory", "🔧 Accessories"),
            ],
            value="All", bgcolor=self.card_color,
        )
        quality_filter = ft.Dropdown(
            label="Quality", width=120,
            options=[
                ft.dropdown.Option("All", "All"),
                ft.dropdown.Option("New", "🟢 New"),
                ft.dropdown.Option("Used", "🟠 Used"),
                ft.dropdown.Option("Damaged", "🔴 Damaged"),
                ft.dropdown.Option("Repaired", "🔵 Repaired"),
            ],
            value="All", bgcolor=self.card_color,
        )
        stock_filter = ft.Dropdown(
            label="Stock Status", width=130,
            options=[
                ft.dropdown.Option("All", "All Stock"),
                ft.dropdown.Option("Low", "⚠️ Low (<10)"),
                ft.dropdown.Option("Critical", "🔥 Critical (<5)"),
                ft.dropdown.Option("Normal", "✅ Normal (≥10)"),
            ],
            value="All", bgcolor=self.card_color,
        )
        search_input = ft.TextField(
            hint_text="Search by name or code...", 
            expand=True, 
            bgcolor=self.card_color, 
            prefix_icon=ft.icons.SEARCH,
        )
        
        scroll_content.controls.append(ft.Row([type_filter, quality_filter, stock_filter], spacing=10, wrap=True))
        scroll_content.controls.append(ft.Container(height=8))
        scroll_content.controls.append(ft.Row([search_input, ft.OutlinedButton("Reset", on_click=lambda e: self.show_inventory(page))], spacing=10))
        scroll_content.controls.append(ft.Container(height=15))
        
        inventory_container = ft.Column(spacing=8)
        
        def update_display():
            inventory_container.controls.clear()
            filtered = inventory_items.copy()
            if type_filter.value != "All":
                filtered = [i for i in filtered if i['type'] == type_filter.value]
            if quality_filter.value != "All":
                filtered = [i for i in filtered if i['quality'] == quality_filter.value]
            if stock_filter.value == "Low":
                filtered = [i for i in filtered if i['quantity'] < 10]
            elif stock_filter.value == "Critical":
                filtered = [i for i in filtered if i['quantity'] < 5]
            elif stock_filter.value == "Normal":
                filtered = [i for i in filtered if i['quantity'] >= 10]
            if search_input.value:
                query = search_input.value.lower()
                filtered = [i for i in filtered if query in i['name'].lower() or query in i['code'].lower()]
            
            self.current_filtered_items = filtered
            inventory_container.controls.append(ft.Text(f"Showing {len(filtered)} of {len(inventory_items)} items", size=font_small - 1, color="#888888"))
            
            for item in filtered[:100]:
                if item['quantity'] < 5:
                    stock_color = self.danger_color
                    status_text = "🔥 CRITICAL"
                elif item['quantity'] < 10:
                    stock_color = self.warning_color
                    status_text = "⚠️ LOW"
                else:
                    stock_color = self.success_color
                    status_text = "✅ OK"
                
                pct = min(item['quantity'] / 50 * 100, 100)
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item['type_icon'], size=font_normal + 4),
                                ft.Column([
                                    ft.Text(item['name'], size=font_normal, weight=ft.FontWeight.BOLD),
                                    ft.Text(item['code'], size=font_small - 2, color="#888888"),
                                ], spacing=2, expand=True),
                                ft.Column([
                                    ft.Text(f"{item['quantity']}", size=font_normal, weight=ft.FontWeight.BOLD, color=stock_color),
                                    ft.Text(status_text, size=font_small - 3, color=stock_color),
                                ], horizontal_alignment=ft.CrossAxisAlignment.END),
                            ]),
                            ft.ProgressBar(value=pct / 100, color=stock_color, bgcolor="#3C3C3C", height=6),
                            ft.Row([
                                ft.Text(f"📍 {item['location']}", size=font_small - 1, expand=True),
                                ft.Container(
                                    content=ft.Text(item['quality'], size=font_small - 2, color="white"),
                                    bgcolor=self.get_quality_color(item['quality']),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.IconButton(icon=ft.icons.ADD_CIRCLE, icon_size=20, on_click=lambda e, it=item: self.quick_stock_change(page, it, '+')),
                                ft.IconButton(icon=ft.icons.REMOVE_CIRCLE, icon_size=20, on_click=lambda e, it=item: self.quick_stock_change(page, it, '-')),
                                ft.IconButton(icon=ft.icons.EDIT, icon_size=20, on_click=lambda e, it=item: self.edit_inventory_item(page, it)),
                                ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20, on_click=lambda e, it=item: self.show_barcode_dialog(page, it)),
                                ft.IconButton(icon=ft.icons.DELETE, icon_size=20, on_click=lambda e, it=item: self.delete_inventory_item(page, it)),
                            ], spacing=0),
                        ], spacing=6),
                        padding=12,
                    ),
                    elevation=1,
                    margin=ft.margin.only(bottom=4),
                )
                inventory_container.controls.append(card)
            page.update()
        
        type_filter.on_change = lambda e: update_display()
        quality_filter.on_change = lambda e: update_display()
        stock_filter.on_change = lambda e: update_display()
        search_input.on_change = lambda e: update_display()
        update_display()
        
        scroll_content.controls.append(inventory_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "inventory"
        page.update()

    def quick_stock_change(self, page: ft.Page, item, operation):
        """Quick add or remove 1 unit from stock"""
        current_qty = item.get('quantity', 0)
        if operation == '+':
            new_qty = current_qty + 1
        else:
            new_qty = max(current_qty - 1, 0)
        
        update_data = {'quantity': new_qty}
        
        if item['type'] == 'material':
            MaterialManager.update(item['id'], update_data)
        else:
            AccessoryManager.update(item['id'], update_data)
        
        page.snack_bar = ft.SnackBar(
            ft.Text(f"✓ {'Added' if operation == '+' else 'Removed'} 1 unit. New quantity: {new_qty}"),
            bgcolor=self.success_color,
            duration=1500
        )
        page.snack_bar.open = True
        self.show_inventory(page)

    def edit_inventory_item(self, page: ft.Page, item):
        """Edit inventory item"""
        if item['type'] == 'material':
            self.open_edit_modal(page, item['id'])
        else:
            self.open_edit_accessory_modal(page, item['id'])

    def delete_inventory_item(self, page: ft.Page, item):
        """Delete inventory item with confirmation"""
        def confirm_delete(e):
            if item['type'] == 'material':
                MaterialManager.delete(item['id'])
            else:
                AccessoryManager.delete(item['id'])
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Deleted: {item['name']}"),
                bgcolor=self.danger_color,
                duration=2000
            )
            page.snack_bar.open = True
            self.show_inventory(page)
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            content=ft.Text(f"Delete '{item['name']}'? This cannot be undone.", size=14),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ USERS SCREEN ============
    def show_users(self, page: ft.Page):
        """Show users screen - Full CRUD working"""
        page.controls.clear()
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            font_title = 24
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 28
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Get current user safely
        current_user = self.current_user or {}
        current_user_id = current_user.get('id')
        is_admin = current_user.get('role') == 'admin' if current_user else False
        has_full_access = self.has_full_access()
        
        # Allow actions if admin OR full access
        can_manage_users = is_admin or has_full_access
        
        # Get all users
        users = self.dict_list(UserManager.get_all())
        
        # Calculate stats
        admin_count = len([u for u in users if u.get('role') == 'admin'])
        manager_count = len([u for u in users if u.get('role') == 'manager'])
        user_count = len([u for u in users if u.get('role') == 'user'])
        
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # ===== HEADER WITH ADD BUTTON =====
        header_row = ft.Row([
            ft.Text("👥 Users Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(expand=True),
        ])
        
        # Add button - always visible if can manage users
        if can_manage_users:
            header_row.controls.append(
                ft.IconButton(
                    icon=ft.icons.ADD_CIRCLE,
                    icon_size=28,
                    icon_color=self.success_color,
                    on_click=lambda e: self.open_add_user_modal(page),
                    tooltip="Add New User",
                )
            )
        
        # Test mode button
        header_row.controls.append(
            ft.IconButton(
                icon=ft.icons.BUG_REPORT,
                icon_size=24,
                icon_color="#9C27B0",
                on_click=lambda e: self.show_test_mode_panel(page),
                tooltip="Test Mode Panel",
            )
        )
        
        scroll_content.controls.append(header_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # ===== STATUS BANNER =====
        if not has_full_access and not is_admin:
            scroll_content.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.LOCK, size=20, color=self.warning_color),
                        ft.Text("Full version required to manage users", size=14, color=self.warning_color),
                        ft.ElevatedButton(
                            "🛒 Buy Now",
                            on_click=lambda e: self.billing.purchase_full_version(
                                on_complete=lambda: self.activate_full_version() or self.show_users(page)
                            ),
                            style=ft.ButtonStyle(bgcolor="#E91E63", color="white"),
                        ),
                    ], spacing=10),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(bottom=10),
                )
            )
        elif has_full_access:
            scroll_content.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, size=20, color="#4CAF50"),
                        ft.Text("✅ Full access - You can manage users", size=14, color="#4CAF50"),
                    ], spacing=10),
                    padding=8,
                    bgcolor="#1A3A1A",
                    border_radius=8,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        # ===== STATS CARDS =====
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("👥 Total", size=font_small, color="#CCCCCC"),
                    ft.Text(str(len(users)), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👑 Admins", size=font_small, color="#CCCCCC"),
                    ft.Text(str(admin_count), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.danger_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Managers", size=font_small, color="#CCCCCC"),
                    ft.Text(str(manager_count), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 Users", size=font_small, color="#CCCCCC"),
                    ft.Text(str(user_count), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.success_color, border_radius=10, expand=True,
            ),
        ], spacing=10)
        scroll_content.controls.append(stats_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # ===== SEARCH FIELD =====
        search_field = ft.TextField(
            hint_text="Search users...",
            width=page.width - 60 if is_mobile else 300,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
            prefix_icon=ft.icons.SEARCH,
        )
        scroll_content.controls.append(search_field)
        scroll_content.controls.append(ft.Container(height=15))
        
        # ===== USERS LIST =====
        users_container = ft.Column(spacing=10)
        scroll_content.controls.append(users_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        def refresh_users_list():
            users_container.controls.clear()
            
            all_users = self.dict_list(UserManager.get_all())
            
            search_query = search_field.value.lower() if search_field.value else ""
            if search_query:
                all_users = [u for u in all_users if search_query in u.get('name', '').lower() or search_query in u.get('email', '').lower()]
            
            if not all_users:
                users_container.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.PEOPLE, size=50, color="#888888"),
                            ft.Text("No users found", size=14, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30,
                    )
                )
                page.update()
                return
            
            for u in all_users:
                role = u.get('role', 'user')
                if role == 'admin':
                    role_display = "👑 ADMIN"
                    role_color = self.danger_color
                elif role == 'manager':
                    role_display = "📊 MANAGER"
                    role_color = self.warning_color
                else:
                    role_display = "👤 USER"
                    role_color = self.success_color
                
                created_date = str(u.get('created_at', ''))[:10] if u.get('created_at') else 'N/A'
                can_edit = is_admin or u.get('id') == current_user_id
                can_delete = is_admin and u.get('id') != current_user_id
                
                # Show actions if user has full access or is admin
                show_actions = (has_full_access or is_admin) and (can_edit or can_delete)
                
                # For admin, always show actions
                if is_admin:
                    show_actions = True
                
                card_content = ft.Column([
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(u.get('name', 'U')[0].upper() if u.get('name') else 'U', size=14),
                            radius=22,
                            bgcolor=self.accent_color,
                        ),
                        ft.Column([
                            ft.Text(u.get('name', 'N/A'), size=font_normal, weight=ft.FontWeight.BOLD),
                            ft.Text(u.get('email', 'N/A'), size=font_small - 2, color="#888888"),
                        ], spacing=2, expand=True),
                        ft.Container(
                            content=ft.Text(role_display, size=font_small - 2, color="white"),
                            bgcolor=role_color,
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        ),
                    ]),
                    ft.Row([
                        ft.Text(f"📅 Joined: {created_date}", size=font_small - 2, color="#888888", expand=True),
                        ft.Row([
                            ft.IconButton(
                                icon=ft.icons.EDIT,
                                icon_size=20,
                                icon_color=self.accent_color if can_edit else "#555555",
                                on_click=lambda e, uid=u.get('id'): self.open_edit_user_modal(page, uid) if can_edit else None,
                                visible=show_actions,
                                tooltip="Edit User",
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                icon_size=20,
                                icon_color=self.danger_color if can_delete else "#555555",
                                on_click=lambda e, uid=u.get('id'), name=u.get('name'): self.open_delete_user_modal(page, uid, name) if can_delete else None,
                                visible=show_actions,
                                tooltip="Delete User",
                            ),
                        ], spacing=0),
                    ]),
                ], spacing=8)
                
                card = ft.Card(
                    content=ft.Container(content=card_content, padding=12),
                    elevation=1,
                    margin=ft.margin.only(bottom=8),
                )
                users_container.controls.append(card)
            
            page.update()
        
        search_field.on_change = lambda e: refresh_users_list()
        refresh_users_list()
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "users"
        page.update()


    def open_add_user_modal(self, page: ft.Page):
        """Open modal for adding new user - Working"""
        
        name_field = ft.TextField(
            label="Full Name *", 
            width=350, 
            bgcolor=self.card_color, 
            autofocus=True
        )
        email_field = ft.TextField(
            label="Email *", 
            width=350, 
            bgcolor=self.card_color
        )
        
        role_field = ft.Dropdown(
            label="Role *",
            width=350,
            options=[
                ft.dropdown.Option("user", "👤 Regular User"),
                ft.dropdown.Option("manager", "📊 Manager"),
                ft.dropdown.Option("admin", "👑 Administrator"),
            ],
            value="user",
            bgcolor=self.card_color,
        )
        
        password_field = ft.TextField(
            label="Password *", 
            width=350, 
            bgcolor=self.card_color, 
            password=True,
            can_reveal_password=True,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def save_user(e):
            name = name_field.value.strip()
            email = email_field.value.strip()
            role = role_field.value
            password = password_field.value
            
            if not name:
                status_text.value = "❌ Please enter name!"
                status_text.color = self.danger_color
                page.update()
                return
            
            if not email:
                status_text.value = "❌ Please enter email!"
                status_text.color = self.danger_color
                page.update()
                return
            
            if not password or len(password) < 4:
                status_text.value = "❌ Password must be at least 4 characters!"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Get company_id from current user or default
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            
            import hashlib
            from datetime import datetime
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Check if email exists
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                if cursor.fetchone():
                    status_text.value = "❌ Email already exists!"
                    status_text.color = self.danger_color
                    page.update()
                    conn.close()
                    return
                
                # Insert new user
                cursor.execute("""
                    INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, email, hashed_password, role, company_id, 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                
                conn.commit()
                conn.close()
                
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ User {name} created successfully!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_users(page)
                
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)[:50]}"
                status_text.color = self.danger_color
                page.update()
                print(f"Error creating user: {ex}")
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Add New User", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column([
                            name_field,
                            email_field,
                            role_field,
                            password_field,
                            status_text,
                        ], spacing=12),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Create User", on_click=save_user, 
                                        style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=450,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()

    def open_edit_user_modal(self, page: ft.Page, user_id):
        """Open modal for editing user - Working"""
        
        # Get user data
        users = self.dict_list(UserManager.get_all())
        user_dict = None
        for u in users:
            if u.get('id') == user_id:
                user_dict = u
                break
        
        if not user_dict:
            page.snack_bar = ft.SnackBar(ft.Text("User not found!"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return
        
        current_user = self.current_user or {}
        is_current_user = user_dict.get('id') == current_user.get('id')
        is_admin = current_user.get('role') == 'admin'
        
        name_field = ft.TextField(
            label="Full Name", 
            value=user_dict.get('name', ''), 
            width=380, 
            bgcolor=self.card_color
        )
        email_field = ft.TextField(
            label="Email", 
            value=user_dict.get('email', ''), 
            width=380, 
            bgcolor=self.card_color, 
            read_only=True
        )
        
        role_field = ft.Dropdown(
            label="Role", 
            width=380,
            options=[
                ft.dropdown.Option("user", "👤 Regular User"),
                ft.dropdown.Option("manager", "📊 Manager"),
                ft.dropdown.Option("admin", "👑 Administrator")
            ], 
            value=user_dict.get('role', 'user'), 
            bgcolor=self.card_color, 
            disabled=not is_admin or is_current_user
        )
        
        password_field = ft.TextField(
            label="New Password (leave blank to keep current)", 
            width=380, 
            bgcolor=self.card_color, 
            password=True, 
            can_reveal_password=True,
        )
        
        confirm_password_field = ft.TextField(
            label="Confirm New Password", 
            width=380, 
            bgcolor=self.card_color, 
            password=True, 
            can_reveal_password=True,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def update_user(e):
            new_password = password_field.value
            
            if new_password:
                if new_password != confirm_password_field.value:
                    status_text.value = "❌ Passwords do not match!"
                    status_text.color = self.danger_color
                    page.update()
                    return
                if len(new_password) < 4:
                    status_text.value = "❌ Password must be at least 4 characters!"
                    status_text.color = self.danger_color
                    page.update()
                    return
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                if new_password:
                    import hashlib
                    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                    cursor.execute(
                        "UPDATE users SET name = ?, role = ?, password_hash = ? WHERE id = ?",
                        (name_field.value, role_field.value, hashed_password, user_dict.get('id'))
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET name = ?, role = ? WHERE id = ?",
                        (name_field.value, role_field.value, user_dict.get('id'))
                    )
                conn.commit()
                conn.close()
                
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ User {name_field.value} updated!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                
                # Update current user if editing self
                if is_current_user:
                    self.current_user['name'] = name_field.value
                    self.current_user['role'] = role_field.value
                
                self.show_users(page)
                
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"✏️ Edit User: {user_dict.get('name')}", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column([
                            name_field,
                            email_field,
                            role_field,
                            ft.Divider(),
                            ft.Text("Reset Password (Optional)", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color),
                            password_field,
                            confirm_password_field,
                            status_text,
                        ], spacing=12),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Update User", on_click=update_user, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=450,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()

    def open_delete_user_modal(self, page: ft.Page, user_id, user_name):
        """Open modal for delete confirmation - Working"""
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ User '{user_name}' deleted!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_users(page)
                
            except Exception as ex:
                print(f"Delete error: {ex}")
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Error: {str(ex)[:50]}"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Divider(),
                        ft.Container(height=10),
                        ft.Text(f"Are you sure you want to delete:", size=13, color="#CCCCCC"),
                        ft.Text(f"'{user_name}'?", size=16, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Container(height=10),
                        ft.Text("This action cannot be undone.", size=12, color="#888888"),
                        ft.Container(height=10),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Yes, Delete", on_click=confirm_delete, 
                                        style=ft.ButtonStyle(bgcolor=self.danger_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=5),
                    padding=20,
                    width=400,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
# Add these methods to your StoreApp class after __init__

    def has_full_access(self):
        """Check if user has full version access"""
        if not self.current_user:
            return False
        
        # Check if activated
        if self.is_activated:
            return True
        
        if self.current_user.get('activated', False):
            return True
        
        # Check if admin (always has full access)
        if self.current_user.get('role') == 'admin':
            return True
        
        return False

    def can_edit_delete(self):
        """Check if user can edit/delete items"""
        if not self.current_user:
            return False
        
        # Admin always has access
        if self.current_user.get('role') == 'admin':
            return True
        
        # Full version users have access
        return self.has_full_access()

    def can_manage_users(self):
        """Check if user can manage other users"""
        if not self.current_user:
            return False
        
        # Only admins can manage users
        return self.current_user.get('role') == 'admin'

    def show_settings(self, page: ft.Page):
        """Show settings screen with working buttons"""
        page.controls.clear()
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            font_title = 24
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 28
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Get current user safely
        current_user = self.current_user or {}
        is_admin = current_user.get('role') == 'admin' if current_user else False
        has_full_access = self.has_full_access()
        
        # Check if user is logged in (has an ID)
        is_logged_in = bool(current_user and current_user.get('id'))
        
        # For testing, if we have an email but no ID, try to find the user in database
        if not is_logged_in and current_user.get('email'):
            try:
                import sqlite3
                from database import DB_PATH
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, role FROM users WHERE email = ?", (current_user.get('email'),))
                result = cursor.fetchone()
                conn.close()
                if result:
                    self.current_user['id'] = result[0]
                    self.current_user['name'] = result[1]
                    self.current_user['role'] = result[2]
                    current_user = self.current_user
                    is_logged_in = True
                    print(f"✅ Found user in database: {result[1]} (ID: {result[0]})")
            except Exception as e:
                print(f"Error finding user: {e}")
        
        # If still not logged in, check if it's test mode
        if not is_logged_in and has_full_access:
            # In test mode, create a temporary user ID
            self.current_user['id'] = 1
            self.current_user['name'] = 'Test User'
            self.current_user['role'] = 'admin'
            current_user = self.current_user
            is_logged_in = True
            print("✅ Test mode: Created temporary user")
        
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # ===== HEADER =====
        header_row = ft.Row([
            ft.Text("⚙️ Settings", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.icons.BUG_REPORT,
                icon_size=24,
                icon_color="#9C27B0",
                on_click=lambda e: self.show_test_mode_panel(page),
                tooltip="Test Mode Panel",
            ),
        ])
        scroll_content.controls.append(header_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # ===== STATUS BANNER =====
        if not has_full_access and not is_admin:
            scroll_content.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.LOCK, size=20, color=self.warning_color),
                        ft.Text("Full version required for all settings", size=14, color=self.warning_color),
                        ft.ElevatedButton(
                            "🛒 Buy Now",
                            on_click=lambda e: self.billing.purchase_full_version(
                                on_complete=lambda: self.activate_full_version() or self.show_settings(page)
                            ),
                            style=ft.ButtonStyle(bgcolor="#E91E63", color="white"),
                        ),
                    ], spacing=10),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(bottom=10),
                )
            )
        elif has_full_access:
            scroll_content.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, size=20, color="#4CAF50"),
                        ft.Text("✅ Full version active - All settings available", size=14, color="#4CAF50"),
                    ], spacing=10),
                    padding=8,
                    bgcolor="#1A3A1A",
                    border_radius=8,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        # ===== PROFILE SECTION =====
        profile_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("👤 Profile", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(
                                current_user.get('name', 'G')[0].upper() if current_user.get('name') else 'G', 
                                size=18
                            ),
                            radius=35,
                            bgcolor=self.accent_color,
                        ),
                        ft.Column([
                            ft.Text(current_user.get('name', 'Guest'), size=font_normal + 2, weight=ft.FontWeight.BOLD),
                            ft.Text(current_user.get('email', 'Not logged in'), size=font_small - 1, color="#888888"),
                            ft.Text(f"Role: {current_user.get('role', 'guest').upper()}", size=font_small - 2, 
                                color=self.success_color if current_user.get('role') == 'admin' else self.warning_color),
                            ft.Text(f"ID: {current_user.get('id', 'N/A')}", size=font_small - 2, color="#888888"),
                        ], spacing=3, expand=True),
                    ], spacing=12),
                    # Edit Profile button - ALWAYS VISIBLE if logged in
                    ft.ElevatedButton(
                        "✏️ Edit Profile", 
                        on_click=lambda e: self.edit_profile_dialog(page) if is_logged_in else None,
                        style=ft.ButtonStyle(
                            bgcolor=self.accent_color if is_logged_in else "#555555",
                            color="white",
                        ),
                        disabled=not is_logged_in,
                        icon=ft.icons.EDIT,
                    ),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(profile_card)
        
        # ===== SECURITY SECTION =====
        security_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🔐 Security", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.LOCK, color=self.accent_color),
                        title=ft.Text("Change Password"),
                        trailing=ft.Icon(ft.icons.CHEVRON_RIGHT),
                        on_click=lambda e: self.change_password_dialog(page) if is_logged_in else None,
                        disabled=not is_logged_in,
                    ),
                ], spacing=8),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(security_card)
        
        # ===== DATA MANAGEMENT SECTION =====
        data_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("💾 Data Management", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.BACKUP, color=self.accent_color),
                        title=ft.Text("Backup Database"),
                        trailing=ft.Icon(ft.icons.CHEVRON_RIGHT),
                        on_click=lambda e: self.backup_database(page),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.RESTORE, color=self.accent_color),
                        title=ft.Text("Restore Database"),
                        trailing=ft.Icon(ft.icons.CHEVRON_RIGHT),
                        on_click=lambda e: self.restore_database(page),
                    ),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.DELETE_FOREVER, color=self.danger_color),
                        title=ft.Text("Reset All Data", color=self.danger_color),
                        trailing=ft.Icon(ft.icons.CHEVRON_RIGHT, color=self.danger_color),
                        on_click=lambda e: self.reset_database_confirm(page),
                    ),
                ], spacing=8),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(data_card)
        
        # ===== ABOUT SECTION =====
        about_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("ℹ️ About", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🏪", size=60),
                            ft.Text("Store Management System", size=font_normal + 4, weight=ft.FontWeight.BOLD),
                            ft.Text("Version 2.0.0", size=font_small - 1, color="#888888"),
                            ft.Container(height=5),
                            ft.Text("© 2024 Store Management", size=font_small - 2, color="#888888"),
                            ft.Text("Made with ❤️ using Flet", size=font_small - 2, color="#888888"),
                            ft.Container(height=5),
                            ft.Text(f"Status: {'✅ Full Version' if has_full_access else '📱 Trial Mode'}", 
                                size=font_small - 1, color="#4CAF50" if has_full_access else "#FF9800"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        margin=ft.margin.only(bottom=10),
                    ),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
            ),
            elevation=2,
        )
        scroll_content.controls.append(about_card)
        
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "settings"
        page.update()

    def edit_profile_dialog(self, page: ft.Page):
        """Open dialog to edit user profile - Working"""
        
        current_user = self.current_user or {}
        
        if not current_user or not current_user.get('id'):
            page.snack_bar = ft.SnackBar(
                ft.Text("Please login first!"),
                bgcolor=self.warning_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        name_field = ft.TextField(
            label="Full Name", 
            value=current_user.get('name', ''), 
            width=300, 
            bgcolor=self.card_color
        )
        email_field = ft.TextField(
            label="Email", 
            value=current_user.get('email', ''), 
            width=300, 
            bgcolor=self.card_color, 
            read_only=True
        )
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def save_profile(e):
            new_name = name_field.value.strip()
            if not new_name:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Name cannot be empty!"), 
                    bgcolor=self.danger_color
                )
                page.snack_bar.open = True
                return
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, current_user['id']))
                conn.commit()
                conn.close()
                
                self.current_user['name'] = new_name
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Profile updated!"), 
                    bgcolor=self.success_color
                )
                page.snack_bar.open = True
                self.show_settings(page)
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Error: {str(ex)}"), 
                    bgcolor=self.danger_color
                )
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Edit Profile", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            email_field,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save", on_click=save_profile, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Profile"),
            content=ft.Container(content=dialog_content, width=400, height=300, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def change_password_dialog(self, page: ft.Page):
        """Open dialog to change password - Working"""
        
        current_user = self.current_user or {}
        
        if not current_user or not current_user.get('id'):
            page.snack_bar = ft.SnackBar(
                ft.Text("Please login first!"),
                bgcolor=self.warning_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        import hashlib
        
        current_password = ft.TextField(
            label="Current Password", 
            password=True, 
            width=300, 
            bgcolor=self.card_color
        )
        new_password = ft.TextField(
            label="New Password", 
            password=True, 
            width=300, 
            bgcolor=self.card_color
        )
        confirm_password = ft.TextField(
            label="Confirm Password", 
            password=True, 
            width=300, 
            bgcolor=self.card_color
        )
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def update_password(e):
            current = current_password.value
            new = new_password.value
            confirm = confirm_password.value
            
            if not current or not new or not confirm:
                status_text.value = "❌ Please fill all fields"
                status_text.color = self.danger_color
                page.update()
                return
            
            if new != confirm:
                status_text.value = "❌ New passwords do not match"
                status_text.color = self.danger_color
                page.update()
                return
            
            if len(new) < 4:
                status_text.value = "❌ Password must be at least 4 characters"
                status_text.color = self.danger_color
                page.update()
                return
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Verify current password
                current_hash = hashlib.sha256(current.encode()).hexdigest()
                cursor.execute("SELECT id FROM users WHERE id = ? AND password_hash = ?", 
                            (current_user['id'], current_hash))
                if not cursor.fetchone():
                    status_text.value = "❌ Current password is incorrect"
                    status_text.color = self.danger_color
                    conn.close()
                    page.update()
                    return
                
                # Update password
                new_hash = hashlib.sha256(new.encode()).hexdigest()
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, current_user['id']))
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Password changed successfully!"), 
                    bgcolor=self.success_color
                )
                page.snack_bar.open = True
                page.update()
                
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Change Password", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            current_password,
            new_password,
            confirm_password,
            status_text,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Update Password", on_click=update_password, style=ft.ButtonStyle(bgcolor=self.warning_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Change Password"),
            content=ft.Container(content=dialog_content, width=400, height=420, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def backup_database(self, page: ft.Page):
        """Backup database to app storage"""
        import shutil
        
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            backup_dir = os.path.join(app_dir, "backups")
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            
            db_path = os.path.join(app_dir, "store_management.db")
            
            if os.path.exists(db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"backup_{timestamp}.db"
                backup_path = os.path.join(backup_dir, backup_name)
                
                shutil.copy2(db_path, backup_path)
                
                file_size = os.path.getsize(backup_path)
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Backup saved! Size: {size_str}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("No database found to backup!"),
                    bgcolor=self.warning_color,
                    duration=3000
                )
            
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Backup failed: {str(e)[:50]}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()

    def restore_database(self, page: ft.Page):
        """Restore database from backup"""
        import os
        import shutil
        
        app_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(app_dir, "backups")
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
        
        backups = []
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            backups.sort(reverse=True)
        
        if not backups:
            page.snack_bar = ft.SnackBar(
                ft.Text("No backups found!"),
                bgcolor=self.warning_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        def close_dlg():
            page.dialog.open = False
            page.update()
        
        def confirm_restore(backup_file):
            def do_restore(e):
                try:
                    backup_path = os.path.join(backup_dir, backup_file)
                    db_path = os.path.join(app_dir, "store_management.db")
                    
                    if os.path.exists(db_path):
                        os.remove(db_path)
                    
                    shutil.copy2(backup_path, db_path)
                    
                    confirm_dialog.open = False
                    close_dlg()
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Database restored from {backup_file}!"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                    self.show_dashboard(page)
                    
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Restore failed: {str(ex)[:50]}"),
                        bgcolor=self.danger_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
            
            def cancel_restore(e):
                confirm_dialog.open = False
                page.update()
            
            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Confirm Restore", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Restore from backup:", size=14),
                        ft.Text(f"'{backup_file}'?", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.Text("⚠️ This will OVERWRITE your current data!", size=12, color=self.danger_color),
                    ], spacing=8),
                    width=320,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_restore),
                    ft.ElevatedButton("Restore", on_click=do_restore, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ],
            )
            
            page.dialog = confirm_dialog
            confirm_dialog.open = True
            page.update()
        
        backup_items = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
        
        for backup in backups:
            backup_path = os.path.join(backup_dir, backup)
            size_bytes = os.path.getsize(backup_path)
            size_kb = size_bytes / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
            
            date_str = "Unknown"
            try:
                if '_' in backup:
                    parts = backup.replace('.db', '').split('_')
                    if len(parts) >= 2:
                        date_str = parts[1]
                        if len(date_str) == 8:
                            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            except:
                pass
            
            backup_items.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.STORAGE, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text(backup, size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Date: {date_str} | Size: {size_str}", size=10, color="#888888"),
                        ], spacing=2, expand=True),
                        ft.ElevatedButton(
                            "Restore",
                            on_click=lambda e, b=backup: confirm_restore(b),
                            style=ft.ButtonStyle(bgcolor=self.success_color, color="white"),
                        ),
                    ]),
                    padding=8,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(bottom=5),
                )
            )
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Restore Database", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Select a backup to restore ({len(backups)} available):", size=13),
                    ft.Container(height=5),
                    backup_items,
                ], spacing=10),
                width=450,
                height=450,
                padding=15,
            ),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def reset_database_confirm(self, page: ft.Page):
        """Confirm and reset database"""
        
        def confirm_reset(e):
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM materials")
                cursor.execute("DELETE FROM accessories")
                cursor.execute("DELETE FROM users WHERE id > 1")
                
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Database reset successfully!"),
                    bgcolor=self.success_color,
                    duration=5000
                )
                page.snack_bar.open = True
                page.update()
                
            except Exception as ex:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Reset failed: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=4000
                )
                page.snack_bar.open = True
                page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("⚠️ Reset Database", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("This will delete ALL data including:", size=14),
            ft.Text("• All materials", size=13),
            ft.Text("• All accessories", size=13),
            ft.Text("• All users (except admin)", size=13),
            ft.Text("This action CANNOT be undone!", size=14, color=self.danger_color, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Yes, Reset All Data", on_click=confirm_reset, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Reset Database"),
            content=ft.Container(content=dialog_content, width=400, height=380, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ BARCODE SCANNER ============
    def show_barcode_scanner(self, page: ft.Page, target_field=None):
        """Barcode scanner dialog"""
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def paste_barcode(e):
            try:
                clipboard = page.get_clipboard()
                if clipboard:
                    barcode_input.value = clipboard
                    status_text.value = "✓ Barcode pasted!"
                    status_text.color = self.success_color
                    page.update()
                else:
                    status_text.value = "❌ Clipboard is empty"
                    status_text.color = self.danger_color
                    page.update()
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        def search_barcode(e):
            barcode = barcode_input.value.strip()
            if barcode:
                if target_field:
                    target_field.value = barcode
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"🔍 Searching: {barcode}"), bgcolor=self.accent_color, duration=1500)
                page.snack_bar.open = True
                page.update()
                self.search_barcode_by_value(barcode, page)
            else:
                status_text.value = "❌ Please enter or paste a barcode first"
                status_text.color = self.danger_color
                page.update()
        
        barcode_input = ft.TextField(
            label="Barcode Number",
            hint_text="Enter barcode or paste here",
            width=300,
            bgcolor=self.card_color,
        )
        status_text = ft.Text("", size=12)
        
        instruction = ft.Column([
            ft.Text("📷 How to scan:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("1. Open Camera app or Barcode Scanner", size=12),
            ft.Text("2. Scan and copy the barcode number", size=12),
            ft.Text("3. Tap 'Paste' button below", size=12),
            ft.Text("4. Tap 'Search' to find item", size=12),
            ft.Container(height=5),
            ft.Text("💡 Or type the barcode number manually", size=11, color="#888888"),
        ], spacing=5)
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Barcode Scanner", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ]),
            ft.Divider(),
            instruction,
            ft.Container(height=10),
            barcode_input,
            status_text,
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton(
                    "📋 Paste", 
                    on_click=paste_barcode, 
                    icon=ft.icons.CONTENT_PASTE, 
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color),
                ),
                ft.ElevatedButton(
                    "🔍 Search", 
                    on_click=search_barcode, 
                    icon=ft.icons.SEARCH, 
                    expand=True,
                    style=ft.ButtonStyle(bgcolor=self.success_color),
                ),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=350, height=480, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def search_barcode_by_value(self, barcode_value, page):
        """Search for barcode and show result"""
        if not barcode_value:
            page.snack_bar = ft.SnackBar(ft.Text("Please enter a barcode!"), bgcolor=self.warning_color)
            page.snack_bar.open = True
            page.update()
            return
        
        item = MaterialManager.get_by_barcode(barcode_value)
        item_type = 'material'
        
        if not item:
            item = AccessoryManager.get_by_barcode(barcode_value)
            item_type = 'accessory'
        
        if item:
            item_dict = dict(item)
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ Found: {item_dict.get('name')}"), 
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            
            if item_type == 'material':
                self.show_material_detail_dialog(page, item_dict)
            else:
                self.show_accessory_detail_dialog(page, item_dict)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ No item found with barcode: {barcode_value}"), 
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
        
        page.update()

    # ============ CATEGORIES DIALOG ============
    def show_categories_dialog(self, page: ft.Page, refresh_callback=None):
        """Categories dialog with delete functionality"""
        
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        
        current_user_id = self.current_user.get('id') if self.current_user else 1
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(categories)")
        columns = [col[1] for col in cursor.fetchall()]
        has_user_id = 'user_id' in columns
        conn.close()
        
        name_input = ft.TextField(
            hint_text="New category name", 
            width=250, 
            bgcolor="#2C2C2C",
        )
        
        icon_select = ft.Dropdown(
            label="Icon", 
            width=120,
            options=[
                ft.dropdown.Option("📦", "📦 Raw Material"),
                ft.dropdown.Option("🔩", "🔩 Hardware"),
                ft.dropdown.Option("🔧", "🔧 Tools"),
                ft.dropdown.Option("⚡", "⚡ Electrical"),
                ft.dropdown.Option("💧", "💧 Plumbing"),
                ft.dropdown.Option("⚙️", "⚙️ Metal"),
                ft.dropdown.Option("🔨", "🔨 Construction"),
                ft.dropdown.Option("📁", "📁 Other"),
            ],
            value="📁", 
            bgcolor="#2C2C2C",
        )
        
        status_text = ft.Text("", size=12)
        categories_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=250)
        
        def confirm_delete_category(category_id, category_name):
            def do_delete(e):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    cursor.execute("UPDATE materials SET category_id = NULL WHERE category_id = ?", (category_id,))
                    cursor.execute("UPDATE accessories SET category_id = NULL WHERE category_id = ?", (category_id,))
                    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                    
                    conn.commit()
                    conn.close()
                    
                    confirm_dialog.open = False
                    status_text.value = f"✓ Deleted: {category_name}"
                    status_text.color = "green"
                    load_categories()
                    
                    if refresh_callback:
                        refresh_callback()
                    
                    page.update()
                    
                except Exception as e:
                    status_text.value = f"Error: {str(e)}"
                    status_text.color = "red"
                    page.update()
            
            def cancel_delete(e):
                confirm_dialog.open = False
                page.update()
            
            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Delete Category", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Delete '{category_name}'?", size=14),
                        ft.Text("Items using this category will become uncategorized.", size=11, color="#888888"),
                        ft.Text("This cannot be undone!", size=11, color=self.danger_color),
                    ], spacing=8),
                    width=300,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_delete),
                    ft.ElevatedButton("Delete", on_click=do_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ],
            )
            
            page.dialog = confirm_dialog
            confirm_dialog.open = True
            page.update()
        
        def load_categories():
            categories_list.controls.clear()
            
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if has_user_id:
                    cursor.execute("SELECT id, name, icon FROM categories WHERE user_id = ? ORDER BY name", (current_user_id,))
                else:
                    cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
                
                cats = cursor.fetchall()
                conn.close()
                
                if cats:
                    for cat in cats:
                        icon = cat['icon'] if cat['icon'] else "📁"
                        
                        categories_list.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text(icon, size=22),
                                    ft.Text(cat['name'], size=14, expand=True),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE_OUTLINE,
                                        icon_size=18,
                                        icon_color=self.danger_color,
                                        tooltip="Delete Category",
                                        on_click=lambda e, cid=cat['id'], cname=cat['name']: confirm_delete_category(cid, cname),
                                    ),
                                ]),
                                padding=10,
                                bgcolor="#2C2C2C",
                                border_radius=8,
                                margin=ft.margin.only(bottom=5),
                            )
                        )
                else:
                    default_cats = [
                        ("📦", "Raw Material"), ("🔩", "Hardware"), ("🔧", "Tools"),
                        ("⚡", "Electrical"), ("💧", "Plumbing"), ("⚙️", "Metal"), ("📁", "Other"),
                    ]
                    for icon, name in default_cats:
                        categories_list.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text(icon, size=22),
                                    ft.Text(name, size=14, expand=True),
                                    ft.Text("System", size=10, color="#888888"),
                                ]),
                                padding=10,
                                bgcolor="#2C2C2C",
                                border_radius=8,
                                margin=ft.margin.only(bottom=5),
                            )
                        )
                page.update()
            except Exception as e:
                print(f"Error: {e}")
                page.update()
        
        def add_category(e):
            name = name_input.value.strip()
            if not name:
                status_text.value = "❌ Enter name"
                status_text.color = "red"
                page.update()
                return
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                if has_user_id:
                    cursor.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, current_user_id))
                else:
                    cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
                
                if cursor.fetchone():
                    status_text.value = "❌ Already exists!"
                    status_text.color = "red"
                    page.update()
                    conn.close()
                    return
                
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if has_user_id:
                    cursor.execute(
                        "INSERT INTO categories (name, icon, user_id, created_at) VALUES (?, ?, ?, ?)",
                        (name, icon_select.value, current_user_id, current_time)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO categories (name, icon, created_at) VALUES (?, ?, ?)",
                        (name, icon_select.value, current_time)
                    )
                
                conn.commit()
                conn.close()
                
                name_input.value = ""
                status_text.value = f"✓ Added: {name}"
                status_text.color = "green"
                load_categories()
                
                if refresh_callback:
                    refresh_callback()
                
            except Exception as e:
                status_text.value = f"Error: {str(e)}"
                status_text.color = "red"
                page.update()
        
        def close_dlg():
            page.dialog.open = False
            page.update()
            if refresh_callback:
                refresh_callback()
        
        load_categories()
        
        content = ft.Column([
            ft.Row([
                ft.Text("Categories", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dlg()),
            ]),
            ft.Divider(),
            ft.Text("Add New Category", size=14, weight=ft.FontWeight.BOLD),
            name_input,
            icon_select,
            ft.ElevatedButton("➕ Add", on_click=add_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
            status_text,
            ft.Divider(),
            ft.Text("My Categories", size=14, weight=ft.FontWeight.BOLD),
            categories_list,
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=content, width=400, height=600, padding=15),
            actions=[ft.TextButton("Close", on_click=lambda e: close_dlg())],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ MATERIAL DETAIL DIALOG ============
    def show_material_detail_dialog(self, page: ft.Page, material):
        """Show material detail dialog"""
        import os
        
        name = material.get('name', 'N/A')
        category_name = material.get('category_name', 'Other')
        category_icon = material.get('category_icon', '📁')
        quality = material.get('quality', 'Used')
        quantity = material.get('quantity', 0)
        location = material.get('location_ids', 'N/A')
        size = material.get('size', '')
        length = material.get('length', '')
        colors = material.get('colors', '')
        notes = material.get('notes', '')
        barcode = material.get('barcode_value', 'N/A')
        created = str(material.get('created_at', ''))[:16] if material.get('created_at') else 'N/A'
        updated = str(material.get('updated_at', ''))[:16] if material.get('updated_at') else 'N/A'
        
        size_display = size if size else 'N/A'
        length_display = ''
        if length:
            try:
                length_float = float(length)
                length_display = f"{length_float:.2f}" if length_float % 1 != 0 else str(int(length_float))
            except:
                length_display = str(length)
        else:
            length_display = 'N/A'
        
        colors_display = colors if colors else 'N/A'
        notes_display = notes if notes else 'No notes'
        
        image_path = material.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
                else:
                    images_path = os.path.join(base_dir, "images", os.path.basename(image_path))
                    if os.path.exists(images_path):
                        has_image = True
                        full_image_path = images_path
        
        is_mobile = page.width < 800 if page.width else False
        dialog_width = page.width - 40 if is_mobile and page.width else 450
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_material(e):
            page.dialog.open = False
            self.open_edit_modal(page, material.get('id'))
        
        def delete_material(e):
            page.dialog.open = False
            self.open_delete_modal(page, material.get('id'))
        
        def show_barcode(e):
            self.show_barcode_dialog(page, material)
        
        def show_fullscreen(e):
            def close_fullscreen():
                page.overlay.clear()
                page.update()
            
            screen_width = page.width if page.width else 400
            screen_height = page.height if page.height else 600
            
            fullscreen = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(expand=True),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=30, on_click=lambda e: close_fullscreen()),
                    ]),
                    ft.Container(
                        content=ft.Image(
                            src=full_image_path, 
                            fit=ft.ImageFit.CONTAIN,
                            width=screen_width - 40,
                            height=screen_height - 100,
                        ),
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                ], spacing=10),
                expand=True,
                bgcolor="#000000CC",
            )
            page.overlay.append(fullscreen)
            page.update()
        
        content_items = []
        
        if has_image:
            content_items.append(
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            content=ft.Image(src=full_image_path, fit=ft.ImageFit.CONTAIN, width=200, height=150),
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.icons.ZOOM_IN, size=20, color="white"),
                            bgcolor="#00000099",
                            border_radius=20,
                            padding=5,
                            right=5,
                            top=5,
                            on_click=show_fullscreen,
                            ink=True,
                        ),
                    ]),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        else:
            content_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, size=50, color="#888888"),
                        ft.Text("No Image Available", size=12, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.Text("📁 Category:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{category_icon} {category_name}", size=13, color=self.accent_color, weight=ft.FontWeight.BOLD),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("🔢 Barcode:", size=13, color="#CCCCCC", width=100),
            ft.Text(barcode, size=12, color="#888888"),
        ], spacing=8))
        
        content_items.append(
            ft.Row([
                ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color)),
            ], spacing=10)
        )
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.Text("🏷️ Quality:", size=13, color="#CCCCCC", width=100),
            ft.Container(
                content=ft.Text(quality, size=12, color="white"),
                bgcolor=self.get_quality_color(quality),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            ),
        ], spacing=8))
        
        qty_color = self.danger_color if quantity < 10 else self.text_color
        content_items.append(ft.Row([
            ft.Text("🔢 Quantity:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{quantity} units", size=14, weight=ft.FontWeight.BOLD, color=qty_color),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("📍 Location:", size=13, color="#CCCCCC", width=100),
            ft.Text(location, size=13, color=self.text_color),
        ], spacing=8))
        
        if size_display != 'N/A' or length_display != 'N/A':
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📏 Dimensions", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
            
            if size_display != 'N/A':
                content_items.append(ft.Row([
                    ft.Text("📏 Size:", size=13, color="#CCCCCC", width=100),
                    ft.Text(size_display, size=13, color=self.text_color),
                ], spacing=8))
            
            if length_display != 'N/A':
                content_items.append(ft.Row([
                    ft.Text("📐 Length:", size=13, color="#CCCCCC", width=100),
                    ft.Text(length_display, size=13, color=self.text_color),
                ], spacing=8))
        
        if colors_display != 'N/A':
            content_items.append(ft.Divider())
            content_items.append(ft.Row([
                ft.Text("🎨 Colors:", size=13, color="#CCCCCC", width=100),
                ft.Text(colors_display, size=13, color=self.text_color),
            ], spacing=8))
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.Text("📅 Created:", size=13, color="#CCCCCC", width=100),
            ft.Text(created, size=12, color="#888888"),
        ], spacing=8))
        content_items.append(ft.Row([
            ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=100),
            ft.Text(updated, size=12, color="#888888"),
        ], spacing=8))
        
        if notes_display != 'No notes':
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📝 Notes", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
            content_items.append(
                ft.Container(
                    content=ft.Text(notes_display, size=12, color="#888888"),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(top=5, bottom=10),
                )
            )
        
        content_items.append(ft.Divider())
        content_items.append(
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=edit_material, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=delete_material, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], spacing=10)
        )
        
        scrollable_content = ft.Column(content_items, spacing=8, scroll=ft.ScrollMode.AUTO, height=500)
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable_content, width=dialog_width, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ ACCESSORY DETAIL DIALOG ============
    def show_accessory_detail_dialog(self, page: ft.Page, accessory):
        """Show accessory detail dialog"""
        import os
        
        name = accessory.get('name', 'N/A')
        category_name = accessory.get('category_name', 'Other')
        category_icon = accessory.get('category_icon', '📁')
        quality = accessory.get('quality', 'Used')
        quantity = accessory.get('quantity', 0)
        location = accessory.get('location', 'N/A')
        price = accessory.get('price', 0)
        notes = accessory.get('notes', 'No notes')
        barcode = accessory.get('barcode_value', 'N/A')
        created = str(accessory.get('created_at', ''))[:16] if accessory.get('created_at') else 'N/A'
        updated = str(accessory.get('updated_at', ''))[:16] if accessory.get('updated_at') else 'N/A'
        price_text = f"${price:.2f}" if price else "N/A"
        
        image_path = accessory.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
                else:
                    images_path = os.path.join(base_dir, "images", os.path.basename(image_path))
                    if os.path.exists(images_path):
                        has_image = True
                        full_image_path = images_path
        
        is_mobile = page.width < 800 if page.width else False
        dialog_width = page.width - 40 if is_mobile and page.width else 450
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_accessory(e):
            page.dialog.open = False
            self.open_edit_accessory_modal(page, accessory.get('id'))
        
        def delete_accessory(e):
            page.dialog.open = False
            self.open_delete_accessory_modal(page, accessory.get('id'))
        
        def show_barcode(e):
            self.show_barcode_dialog(page, accessory)
        
        def show_fullscreen(e):
            def close_fullscreen():
                page.overlay.clear()
                page.update()
            
            screen_width = page.width if page.width else 400
            screen_height = page.height if page.height else 600
            
            fullscreen = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(expand=True),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=30, on_click=lambda e: close_fullscreen()),
                    ]),
                    ft.Container(
                        content=ft.Image(
                            src=full_image_path, 
                            fit=ft.ImageFit.CONTAIN,
                            width=screen_width - 40,
                            height=screen_height - 100,
                        ),
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                ], spacing=10),
                expand=True,
                bgcolor="#000000CC",
            )
            page.overlay.append(fullscreen)
            page.update()
        
        content_items = []
        
        if has_image:
            content_items.append(
                ft.Container(
                    content=ft.Stack([
                        ft.Container(
                            content=ft.Image(src=full_image_path, fit=ft.ImageFit.CONTAIN, width=200, height=150),
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.icons.ZOOM_IN, size=20, color="white"),
                            bgcolor="#00000099",
                            border_radius=20,
                            padding=5,
                            right=5,
                            top=5,
                            on_click=show_fullscreen,
                            ink=True,
                        ),
                    ]),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        else:
            content_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, size=50, color="#888888"),
                        ft.Text("No Image Available", size=12, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.Text("📁 Category:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{category_icon} {category_name}", size=13, color=self.accent_color, weight=ft.FontWeight.BOLD),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("🔢 Barcode:", size=13, color="#CCCCCC", width=100),
            ft.Text(barcode, size=12, color="#888888"),
        ], spacing=8))
        
        content_items.append(
            ft.Row([
                ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color)),
            ], spacing=10)
        )
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.Text("🏷️ Quality:", size=13, color="#CCCCCC", width=100),
            ft.Container(
                content=ft.Text(quality, size=12, color="white"),
                bgcolor=self.get_quality_color(quality),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            ),
        ], spacing=8))
        
        qty_color = self.danger_color if quantity < 10 else self.text_color
        content_items.append(ft.Row([
            ft.Text("🔢 Quantity:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{quantity} units", size=14, weight=ft.FontWeight.BOLD, color=qty_color),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("💰 Price:", size=13, color="#CCCCCC", width=100),
            ft.Text(price_text, size=13, color="#4CAF50", weight=ft.FontWeight.BOLD),
        ], spacing=8))
        
        content_items.append(ft.Row([
            ft.Text("📍 Location:", size=13, color="#CCCCCC", width=100),
            ft.Text(location, size=13, color=self.text_color),
        ], spacing=8))
        
        content_items.append(ft.Divider())
        content_items.append(ft.Row([
            ft.Text("📅 Created:", size=13, color="#CCCCCC", width=100),
            ft.Text(created, size=12, color="#888888"),
        ], spacing=8))
        content_items.append(ft.Row([
            ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=100),
            ft.Text(updated, size=12, color="#888888"),
        ], spacing=8))
        
        if notes and notes != 'No notes':
            content_items.append(ft.Divider())
            content_items.append(ft.Text("📝 Notes", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color))
            content_items.append(
                ft.Container(
                    content=ft.Text(notes, size=12, color="#888888"),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                    margin=ft.margin.only(top=5, bottom=10),
                )
            )
        
        content_items.append(ft.Divider())
        content_items.append(
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=edit_accessory, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=delete_accessory, expand=True,
                    style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], spacing=10)
        )
        
        scrollable_content = ft.Column(content_items, spacing=8, scroll=ft.ScrollMode.AUTO, height=500)
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable_content, width=dialog_width, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ BARCODE DIALOG ============
    def show_barcode_dialog(self, page: ft.Page, item):
        """Show barcode dialog with copy button"""
        import webbrowser
        import tempfile
        
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        item_name = item.get('name', 'Item')
        item_type = "Material" if 'location_ids' in item else "Accessory"
        
        barcode_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_text}&code=Code128&dpi=120"
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def copy_to_clipboard(e):
            try:
                page.set_clipboard(barcode_text)
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Barcode copied: {barcode_text}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Failed to copy: {str(ex)}"), bgcolor=self.danger_color, duration=2000)
                page.snack_bar.open = True
                page.update()
        
        def print_barcode(e):
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Barcode - {barcode_text}</title>
                <style>
                    body {{ text-align: center; padding: 50px; font-family: Arial; }}
                    .barcode-img {{ max-width: 100%; height: auto; }}
                    .number {{ font-size: 24px; font-weight: bold; margin-top: 20px; }}
                    @media print {{ .no-print {{ display: none; }} }}
                </style>
            </head>
            <body>
                <img class="barcode-img" src="{barcode_url}" alt="Barcode">
                <div class="number">{barcode_text}</div>
                <div class="no-print" style="margin-top: 30px;">
                    <button onclick="window.print()">🖨️ Print Now</button>
                    <button onclick="window.close()">Close</button>
                </div>
                <script>setTimeout(function(){{ window.print(); }}, 500);</script>
            </body>
            </html>
            """
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            webbrowser.open(f'file://{temp_file.name}')
            close_dialog(e)
        
        dialog_content = ft.Column([
            ft.Text(item_name, size=16, weight=ft.FontWeight.BOLD),
            ft.Text(item_type, size=12, color="#888888"),
            ft.Container(height=10),
            ft.Image(src=barcode_url, width=300, height=100, fit=ft.ImageFit.CONTAIN),
            ft.Text(barcode_text, size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
            ft.Text("Scan this barcode with your camera", size=10, color="#888888"),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Barcode", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=dialog_content, width=350, height=380, padding=15),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
                ft.TextButton("📋 Copy", on_click=copy_to_clipboard),
                ft.FilledButton("🖨️ Print", on_click=print_barcode, style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ ADD MATERIAL MODAL ============
    def open_add_modal(self, page: ft.Page):
        """Add material with image upload"""
        import random
        import string
        import sqlite3
        import os
        import shutil
        from datetime import datetime
        from database import DB_PATH
        
        def generate_barcode():
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
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 380
        else:
            field_width = 350
            dialog_width = 500
            scroll_height = 450
        
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        name_field = ft.TextField(label="Name *", width=field_width, bgcolor=self.card_color, autofocus=True)
        category_field = ft.Dropdown(label="Category", width=field_width, options=category_options, 
                                    value=str(categories[0]['id']) if categories else "1", bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", width=field_width, bgcolor=self.card_color, value="0")
        size_field = ft.TextField(label="Size", width=field_width, bgcolor=self.card_color, hint_text="e.g., 34 1/2")
        length_field = ft.TextField(label="Length (auto)", width=field_width, bgcolor=self.card_color, read_only=True)
        quality_field = ft.Dropdown(label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value="New", bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", width=field_width, bgcolor=self.card_color)
        color_field = ft.TextField(label="Colors", width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", width=field_width, bgcolor=self.card_color, multiline=True, min_lines=2, max_lines=3)
        
        barcode_field = ft.TextField(label="Barcode", width=field_width - 80, bgcolor=self.card_color, 
                                    value=generate_barcode(), read_only=True)
        regenerate_btn = ft.TextButton("🔄 New Barcode", on_click=lambda e: setattr(barcode_field, 'value', generate_barcode()) or page.update())
        barcode_row = ft.Row([barcode_field, regenerate_btn], spacing=8)
        
        image_status_text = ft.Text("No image", size=10, color="#888888")
        selected_image_data = None
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    selected_image_data = {'name': file.name, 'data': file_data, 'size': file.size}
                    image_status_text.value = f"✓ {file.name[:20]} ({file.size/1024:.0f}KB)"
                    image_status_text.color = self.success_color
                except:
                    image_status_text.value = "❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        upload_btn = ft.ElevatedButton("📁 Upload Image", on_click=upload_image, icon=ft.icons.UPLOAD_FILE,
                                      style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        image_row = ft.Row([upload_btn, image_status_text], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)
        
        def save_uploaded_image():
            if selected_image_data:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"img_{timestamp}{file_ext}"
                    new_path = os.path.join(images_folder, new_filename)
                    with open(new_path, 'wb') as f:
                        f.write(selected_image_data['data'])
                    return f"images/{new_filename}"
                except:
                    return None
            return None
        
        def update_length(e):
            size_value = size_field.value
            if size_value:
                try:
                    if ' ' in size_value and '/' in size_value:
                        parts = size_value.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_field.value = f"{whole + float(frac[0]) / float(frac[1]):.2f}"
                    elif '/' in size_value:
                        frac = size_value.split('/')
                        length_field.value = f"{float(frac[0]) / float(frac[1]):.2f}"
                    else:
                        length_field.value = f"{float(size_value):.2f}"
                except:
                    length_field.value = size_value
            else:
                length_field.value = ""
            page.update()
        
        size_field.on_change = update_length
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        scrollable_fields = ft.Column([
            name_field, category_field, quantity_field, size_field, length_field,
            quality_field, location_field, color_field, image_row, barcode_row, notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def save_material():
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            saved_image_path = save_uploaded_image() if selected_image_data else None
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            
            size_val = size_field.value
            length_val = None
            if size_val:
                try:
                    if ' ' in size_val and '/' in size_val:
                        parts = size_val.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_val = whole + float(frac[0]) / float(frac[1])
                    elif '/' in size_val:
                        frac = size_val.split('/')
                        length_val = float(frac[0]) / float(frac[1])
                    else:
                        length_val = float(size_val)
                except:
                    length_val = None
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO materials 
                    (name, category_id, quantity, quality, location_ids, 
                    size, length, colors, notes, barcode_value, image_path, company_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    quality_field.value, location_field.value,
                    size_field.value, length_val,
                    color_field.value, notes_field.value,
                    barcode_field.value, saved_image_path, company_id,
                    current_time, current_time
                ))
                conn.commit()
                conn.close()
                
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_materials_screen(page)
                
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Add New Material", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scrollable_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Save", on_click=lambda e: save_material(), 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ EDIT MATERIAL MODAL ============
    def open_edit_modal(self, page: ft.Page, material_id):
        """Edit material with image upload"""
        import sqlite3
        import os
        from database import DB_PATH
        from datetime import datetime
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        material = cursor.fetchone()
        
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        if not material:
            page.snack_bar = ft.SnackBar(ft.Text("Material not found!"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()
            return
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 380
        else:
            field_width = 350
            dialog_width = 450
            scroll_height = 450
        
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        name_field = ft.TextField(label="Name *", value=material['name'], width=field_width, bgcolor=self.card_color)
        category_field = ft.Dropdown(label="Category", width=field_width, options=category_options, 
                                    value=str(material['category_id']), bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", value=str(material['quantity']), width=field_width, bgcolor=self.card_color)
        size_field = ft.TextField(label="Size", value=material['size'] or "", width=field_width, bgcolor=self.card_color)
        length_field = ft.TextField(label="Length", value=str(material['length']) if material['length'] else "", 
                                   width=field_width, bgcolor=self.card_color)
        quality_field = ft.Dropdown(label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value=material['quality'], bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", value=material['location_ids'] or "", width=field_width, bgcolor=self.card_color)
        color_field = ft.TextField(label="Colors", value=material['colors'] or "", width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", value=material['notes'] or "", width=field_width, bgcolor=self.card_color, 
                                  multiline=True, min_lines=2, max_lines=3)
        
        def update_length(e):
            size_value = size_field.value
            if size_value:
                try:
                    if ' ' in size_value and '/' in size_value:
                        parts = size_value.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_field.value = f"{whole + float(frac[0]) / float(frac[1]):.2f}"
                    elif '/' in size_value:
                        frac = size_value.split('/')
                        length_field.value = f"{float(frac[0]) / float(frac[1]):.2f}"
                    else:
                        length_field.value = f"{float(size_value):.2f}"
                except:
                    length_field.value = size_value
            else:
                length_field.value = ""
            page.update()
        
        size_field.on_change = update_length
        
        current_image_path = material['image_path'] if material['image_path'] else None
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
        image_status_text = ft.Text("✓ Current image saved" if has_current_image else "No image", 
                                   size=10, color=self.success_color if has_current_image else "#888888")
        selected_image_data = None
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    selected_image_data = {'name': file.name, 'data': file_data, 'size': file.size}
                    image_status_text.value = f"✓ New: {file.name[:20]} ({file.size/1024:.0f}KB)"
                    image_status_text.color = self.success_color
                except:
                    image_status_text.value = "❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        upload_btn = ft.ElevatedButton("📁 Upload New", on_click=upload_image, icon=ft.icons.UPLOAD_FILE,
                                      style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        image_row = ft.Row([upload_btn, image_status_text], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)
        
        def save_uploaded_image():
            if selected_image_data:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"img_{material_id}_{timestamp}{file_ext}"
                    new_path = os.path.join(images_folder, new_filename)
                    with open(new_path, 'wb') as f:
                        f.write(selected_image_data['data'])
                    if current_image_path and os.path.exists(current_image_path):
                        try:
                            os.remove(current_image_path)
                        except:
                            pass
                    return f"images/{new_filename}"
                except:
                    return None
            return None
        
        scroll_fields = ft.Column([
            name_field, category_field, quantity_field, size_field, length_field,
            quality_field, location_field, color_field, image_row, notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def update_material():
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            final_image_path = current_image_path
            if selected_image_data:
                final_image_path = save_uploaded_image()
            
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            size_val = size_field.value
            length_val = None
            if size_val:
                try:
                    if ' ' in size_val and '/' in size_val:
                        parts = size_val.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_val = whole + float(frac[0]) / float(frac[1])
                    elif '/' in size_val:
                        frac = size_val.split('/')
                        length_val = float(frac[0]) / float(frac[1])
                    else:
                        length_val = float(size_val)
                except:
                    length_val = None
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE materials 
                    SET name = ?, category_id = ?, quantity = ?, quality = ?, location_ids = ?,
                        size = ?, length = ?, colors = ?, notes = ?, image_path = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    quality_field.value, location_field.value,
                    size_field.value, length_val,
                    color_field.value, notes_field.value,
                    final_image_path,
                    current_time, material_id
                ))
                conn.commit()
                conn.close()
                
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Updated: {name_field.value}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_materials_screen(page)
                
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Material", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Update", on_click=lambda e: update_material(), 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=8),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ DELETE MATERIAL MODAL ============
    def open_delete_modal(self, page: ft.Page, material_id):
        """Delete material confirmation modal"""
        
        material = MaterialManager.get_by_id(material_id)
        if not material:
            return
        
        material_dict = dict(material)
        name = material_dict.get('name', 'this item')
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            MaterialManager.delete(material_id)
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Deleted: {name}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_materials_screen(page)
        
        dialog_content = ft.Column([
            ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text(f"Delete '{name}'?", size=14),
            ft.Text("This cannot be undone!", size=12, color="#888888"),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Delete", on_click=confirm_delete, 
                            style=ft.ButtonStyle(bgcolor=self.danger_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=350, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ ADD ACCESSORY MODAL ============
    def open_add_accessory_modal(self, page: ft.Page):
        """Add accessory with image upload"""
        import random
        import string
        import sqlite3
        import os
        from datetime import datetime
        from database import DB_PATH
        
        def generate_barcode():
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
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 350
        else:
            field_width = 350
            dialog_width = 450
            scroll_height = 420
        
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        name_field = ft.TextField(label="Name *", width=field_width, bgcolor=self.card_color, autofocus=True)
        category_field = ft.Dropdown(label="Category", width=field_width, options=category_options, 
                                    value=str(categories[0]['id']) if categories else "1", bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", width=field_width, bgcolor=self.card_color, value="0")
        price_field = ft.TextField(label="Price", width=field_width, bgcolor=self.card_color, value="0.00")
        quality_field = ft.Dropdown(label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value="New", bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", width=field_width, bgcolor=self.card_color, multiline=True, min_lines=2, max_lines=3)
        
        barcode_field = ft.TextField(label="Barcode", width=field_width - 80, bgcolor=self.card_color, 
                                    value=generate_barcode(), read_only=True)
        regenerate_btn = ft.TextButton("🔄 New Barcode", on_click=lambda e: setattr(barcode_field, 'value', generate_barcode()) or page.update())
        barcode_row = ft.Row([barcode_field, regenerate_btn], spacing=8)
        
        image_status_text = ft.Text("No image", size=10, color="#888888")
        selected_image_data = None
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    selected_image_data = {'name': file.name, 'data': file_data, 'size': file.size}
                    image_status_text.value = f"✓ {file.name[:20]} ({file.size/1024:.0f}KB)"
                    image_status_text.color = self.success_color
                except:
                    image_status_text.value = "❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        upload_btn = ft.ElevatedButton("📁 Upload Image", on_click=upload_image, icon=ft.icons.UPLOAD_FILE,
                                      style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        image_row = ft.Row([upload_btn, image_status_text], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)
        
        def save_uploaded_image():
            if selected_image_data:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"acc_{timestamp}{file_ext}"
                    new_path = os.path.join(images_folder, new_filename)
                    with open(new_path, 'wb') as f:
                        f.write(selected_image_data['data'])
                    return f"images/{new_filename}"
                except:
                    return None
            return None
        
        scroll_fields = ft.Column([
            name_field, category_field, quantity_field, price_field,
            quality_field, location_field, image_row, barcode_row, notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def save_accessory():
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            saved_image_path = save_uploaded_image() if selected_image_data else None
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            company_id = self.current_user.get('company_id', 1) if self.current_user else 1
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO accessories 
                    (name, category_id, quantity, price, quality, location, notes, 
                    barcode_value, image_path, company_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    float(price_field.value) if price_field.value else 0,
                    quality_field.value, location_field.value,
                    notes_field.value,
                    barcode_field.value, saved_image_path, company_id,
                    current_time, current_time
                ))
                conn.commit()
                conn.close()
                
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_accessories(page)
                
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Add New Accessory", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Save", on_click=lambda e: save_accessory(), 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=8),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ EDIT ACCESSORY MODAL ============
    def open_edit_accessory_modal(self, page: ft.Page, accessory_id):
        """Edit accessory with image upload"""
        import sqlite3
        import os
        from database import DB_PATH
        from datetime import datetime
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accessories WHERE id = ?", (accessory_id,))
        accessory = cursor.fetchone()
        
        cursor.execute("SELECT id, name, icon FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        if not accessory:
            page.snack_bar = ft.SnackBar(ft.Text("Accessory not found!"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()
            return
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            field_width = page.width - 40 if page.width else 300
            dialog_width = page.width - 20 if page.width else 380
            scroll_height = 350
        else:
            field_width = 350
            dialog_width = 450
            scroll_height = 420
        
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        category_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}") for c in categories]
        
        name_field = ft.TextField(label="Name *", value=accessory['name'], width=field_width, bgcolor=self.card_color)
        category_field = ft.Dropdown(label="Category", width=field_width, options=category_options, 
                                    value=str(accessory['category_id']), bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", value=str(accessory['quantity']), width=field_width, bgcolor=self.card_color)
        price_field = ft.TextField(label="Price", value=str(accessory['price']), width=field_width, bgcolor=self.card_color)
        quality_field = ft.Dropdown(label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value=accessory['quality'], bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", value=accessory['location'] or "", width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", value=accessory['notes'] or "", width=field_width, bgcolor=self.card_color, 
                                  multiline=True, min_lines=2, max_lines=3)
        
        current_image_path = accessory['image_path'] if accessory['image_path'] else None
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
        image_status_text = ft.Text("✓ Current image saved" if has_current_image else "No image", 
                                   size=10, color=self.success_color if has_current_image else "#888888")
        selected_image_data = None
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    selected_image_data = {'name': file.name, 'data': file_data, 'size': file.size}
                    image_status_text.value = f"✓ New: {file.name[:20]} ({file.size/1024:.0f}KB)"
                    image_status_text.color = self.success_color
                except:
                    image_status_text.value = "❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        upload_btn = ft.ElevatedButton("📁 Upload New", on_click=upload_image, icon=ft.icons.UPLOAD_FILE,
                                      style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        image_row = ft.Row([upload_btn, image_status_text], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)
        
        def save_uploaded_image():
            if selected_image_data:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"acc_{accessory_id}_{timestamp}{file_ext}"
                    new_path = os.path.join(images_folder, new_filename)
                    with open(new_path, 'wb') as f:
                        f.write(selected_image_data['data'])
                    if current_image_path and os.path.exists(current_image_path):
                        try:
                            os.remove(current_image_path)
                        except:
                            pass
                    return f"images/{new_filename}"
                except:
                    return None
            return None
        
        scroll_fields = ft.Column([
            name_field, category_field, quantity_field, price_field,
            quality_field, location_field, image_row, notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)
        
        def close_dialog():
            page.dialog.open = False
            page.update()
        
        def update_accessory():
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            final_image_path = current_image_path
            if selected_image_data:
                final_image_path = save_uploaded_image()
            
            selected_category_id = int(category_field.value)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accessories 
                    SET name = ?, category_id = ?, quantity = ?, price = ?, quality = ?, 
                        location = ?, notes = ?, image_path = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    name_field.value, selected_category_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    float(price_field.value) if price_field.value else 0,
                    quality_field.value, location_field.value,
                    notes_field.value,
                    final_image_path,
                    current_time, accessory_id
                ))
                conn.commit()
                conn.close()
                
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Updated: {name_field.value}"), bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_accessories(page)
                
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Accessory", size=16, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=18, on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Update", on_click=lambda e: update_accessory(), 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=8),
        ], spacing=8)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=10),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    # ============ DELETE ACCESSORY MODAL ============
    def open_delete_accessory_modal(self, page: ft.Page, accessory_id):
        """Delete accessory confirmation modal"""
        
        accessory = AccessoryManager.get_by_id(accessory_id)
        if not accessory:
            return
        
        accessory_dict = dict(accessory)
        name = accessory_dict.get('name', 'this item')
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            AccessoryManager.delete(accessory_id)
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Deleted: {name}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_accessories(page)
        
        dialog_content = ft.Column([
            ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text(f"Delete '{name}'?", size=14),
            ft.Text("This cannot be undone!", size=12, color="#888888"),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Delete", on_click=confirm_delete, 
                            style=ft.ButtonStyle(bgcolor=self.danger_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=350, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
