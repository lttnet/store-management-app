"""
Store Management App - Full Features with Users Management
"""
import time
import webbrowser
import tempfile
import flet as ft
import re
import shutil
import requests
import threading  # ← This line should be present
from database import init_database
from managers.material_manager import MaterialManager
from managers.accessory_manager import AccessoryManager
from managers.user_manager import UserManager
#import cv2
#import numpy as np
#from pyzbar import pyzbar
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Create dummy Image class
    class Image:
        @staticmethod
        def open(*args, **kwargs):
            raise ImportError("PIL not available")

from pil_compat import Image, PIL_AVAILABLE

import hashlib
import json
import os
from datetime import datetime, timedelta

import plotly.graph_objects as go
from flet.plotly_chart import PlotlyChart

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("NumPy not available - using fallback")

# ========== FLET VERSION COMPATIBILITY WRAPPER ==========
# This makes newer Flet versions work with old code

# Fix for Icons (capital I)
if not hasattr(ft, 'Icons'):
    ft.Icons = ft.icons

# Fix for Colors (capital C)
if not hasattr(ft, 'Colors'):
    ft.Colors = ft.colors

# Fix for ImageFit (if needed)
if not hasattr(ft, 'ImageFit'):
    ft.ImageFit = ft.ImageFit

# Fix for MainAxisAlignment (if needed)
if not hasattr(ft, 'MainAxisAlignment'):
    ft.MainAxisAlignment = ft.MainAxisAlignment

# Fix for CrossAxisAlignment (if needed)
if not hasattr(ft, 'CrossAxisAlignment'):
    ft.CrossAxisAlignment = ft.CrossAxisAlignment

print("✅ Flet compatibility wrapper loaded")
#print(f"   Flet version: {ft.__version__}")
# ========== END COMPATIBILITY WRAPPER ==========

# After imports, add this:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logo_path = os.path.join(BASE_DIR, 'images', 'Logo-store.png')
background_path = os.path.join(BASE_DIR, 'images', 'backgound_storemgt.png')

class LicenseManager:
    def __init__(self, license_file="licenses.json"):
        self.license_file = license_file
        self.licenses = self.load_licenses()
    
    def load_licenses(self):
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_licenses(self):
        with open(self.license_file, 'w') as f:
            json.dump(self.licenses, f, indent=2)
    
    def generate_license_key(self, email, plan_type, duration_days=365):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data = f"{email}|{plan_type}|{timestamp}|{os.urandom(8).hex()}"
        license_key = hashlib.sha256(data.encode()).hexdigest()[:20].upper()
        formatted_key = '-'.join([license_key[i:i+5] for i in range(0, 20, 5)])
        
        if plan_type == "lifetime":
            expiry_date = (datetime.now() + timedelta(days=3650)).isoformat()
        else:
            expiry_date = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        self.licenses[formatted_key] = {
            'email': email,
            'plan_type': plan_type,
            'issue_date': datetime.now().isoformat(),
            'expiry_date': expiry_date,
            'active': True
        }
        self.save_licenses()
        return formatted_key
    
    def validate_license(self, license_key):
        if license_key in self.licenses:
            license_info = self.licenses[license_key]
            if not license_info.get('active', True):
                return False, "License has been deactivated"
            expiry_date = datetime.fromisoformat(license_info['expiry_date'])
            if datetime.now() > expiry_date:
                return False, f"License expired on {expiry_date.strftime('%Y-%m-%d')}"
            return True, license_info
        return False, "Invalid license key"
    
class StoreApp:
    def __init__(self):
        self.current_user = None
        self.current_view = "dashboard"
        self.selected_material_detail = None
        self.selected_accessory_detail = None
        self.current_filter = "All"
        self.current_accessory_filter = "All"
        self.page_ref = None
        self.barcode_page = None
        self.barcode_result_container = None
        
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
        
    def dict_row(self, row):
        """Convert sqlite3.Row to dictionary"""
        if row is None:
            return None
        return dict(row)
    
    def dict_list(self, rows):
        """Convert list of sqlite3.Row to list of dictionaries"""
        if rows is None:
            return []
        return [dict(row) for row in rows]
        
    def main(self, page: ft.Page):
        page.title = "Store Management System"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = self.bg_color
        page.padding = 0
        page.spacing = 0
        page.window_width = 1600
        page.window_height = 900
        page.window_min_width = 1200
        page.window_min_height = 700
        
        init_database()
        self.show_login(page)
        page.update()
    
    def convert_size_to_length(self, size_text):
        """Convert size text like '34 1/2' or '34.5' to decimal"""
        if not size_text:
            return None
        
        size_text = size_text.strip()
        
        try:
            return float(size_text)
        except ValueError:
            pass
        
        if '/' in size_text:
            parts = size_text.split('/')
            try:
                if ' ' in parts[0]:
                    whole, num = parts[0].split()
                    return float(whole) + (float(num) / float(parts[1]))
                else:
                    return float(parts[0]) / float(parts[1])
            except:
                pass
        
        return None
    
    def get_quality_color(self, quality):
        return self.quality_colors.get(quality, "#CCCCCC")
    
    def check_premium_users(self, page: ft.Page):
        """Check all premium users in database"""
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, check what columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print("Available columns:", columns)
        
        status_msg = []
        
        # Check if is_premium column exists
        if 'is_premium' in columns:
            cursor.execute("SELECT id, name, email, role, is_premium, premium_plan FROM users WHERE is_premium = 1")
            premium_users = cursor.fetchall()
            
            if premium_users:
                status_msg.append(f"✅ Found {len(premium_users)} premium user(s) in database")
                for user in premium_users:
                    plan = user[5] if len(user) > 5 else 'N/A'
                    status_msg.append(f"   - {user[2]} (Plan: {plan})")
            else:
                status_msg.append("❌ No premium users found in database")
        else:
            status_msg.append("⚠️ is_premium column not found. Please run add_premium_columns.py first.")
        
        # Check for trial users
        if 'trial_mode' in columns:
            cursor.execute("SELECT id, name, email, trial_mode, trial_end_date FROM users WHERE trial_mode = 1")
            trial_users = cursor.fetchall()
            
            if trial_users:
                status_msg.append(f"\n📋 Found {len(trial_users)} trial user(s):")
                for user in trial_users:
                    end_date = user[4] if len(user) > 4 else 'N/A'
                    status_msg.append(f"   - {user[2]} (Expires: {end_date})")
        
        # Show all users in database
        cursor.execute("SELECT id, name, email, role FROM users")
        all_users = cursor.fetchall()
        status_msg.append(f"\n📊 Total users in database: {len(all_users)}")
        
        conn.close()
        
        # Show result in app
        page.snack_bar = ft.SnackBar(
            ft.Text("\n".join(status_msg[:5])),  # Show first 5 lines
            bgcolor=self.accent_color,
            duration=8000
        )
        page.snack_bar.open = True
        page.update()
        
        # Print full details to console
        print("\n" + "=" * 50)
        for msg in status_msg:
            print(msg)
        print("=" * 50)
    
    def quick_premium_login(self, page: ft.Page):
        """Quick login as the premium user (for testing)"""
        email_used = "newcustomer@test.com"  # Change to the email you used
        
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check what columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Select appropriate columns
        if 'is_premium' in columns and 'premium_plan' in columns:
            cursor.execute("SELECT id, name, email, password_hash, role, is_premium, premium_plan FROM users WHERE email = ?", (email_used,))
        else:
            cursor.execute("SELECT id, name, email, password_hash, role FROM users WHERE email = ?", (email_used,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.current_user = {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'role': user[4],
                'is_premium': user[5] if len(user) > 5 else False,
                'premium_plan': user[6] if len(user) > 6 else None,
                'trial_mode': False
            }
            print(f"✅ Logged in as: {email_used}")
            print(f"   Role: {self.current_user['role']}")
            print(f"   Premium: {self.current_user.get('is_premium', False)}")
            self.show_dashboard(page)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ User {email_used} not found. Try creating one first."),
                bgcolor=self.danger_color
            )
            page.snack_bar.open = True
            page.update()
    def manually_create_premium_user(self, page: ft.Page):
        """Manually create premium user for the email you used"""
        email_used = "newcustomer@test.com"  # Change to YOUR email
        import sqlite3
        import hashlib
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check what columns exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email_used,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing user
            update_fields = []
            update_values = []
            
            if 'role' in columns:
                update_fields.append("role = ?")
                update_values.append("premium")
            if 'is_premium' in columns:
                update_fields.append("is_premium = ?")
                update_values.append(1)
            if 'premium_plan' in columns:
                update_fields.append("premium_plan = ?")
                update_values.append("monthly")
            if 'trial_mode' in columns:
                update_fields.append("trial_mode = ?")
                update_values.append(0)
            
            update_values.append(email_used)
            
            if update_fields:
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE email = ?"
                cursor.execute(query, update_values)
                print(f"✅ Updated {email_used} to premium!")
                message = f"✅ Updated {email_used} to PREMIUM!"
            else:
                message = "⚠️ No premium columns found. Run add_premium_columns.py first."
        else:
            # Create new user
            password_hash = hashlib.sha256("premium123".encode()).hexdigest()
            
            # Determine available columns
            available_columns = ['name', 'email', 'password_hash']
            available_values = ["Premium Customer", email_used, password_hash]
            
            if 'role' in columns:
                available_columns.append('role')
                available_values.append('premium')
            if 'is_premium' in columns:
                available_columns.append('is_premium')
                available_values.append(1)
            if 'premium_plan' in columns:
                available_columns.append('premium_plan')
                available_values.append('monthly')
            if 'trial_mode' in columns:
                available_columns.append('trial_mode')
                available_values.append(0)
            
            placeholders = ','.join(['?'] * len(available_values))
            query = f"INSERT INTO users ({','.join(available_columns)}) VALUES ({placeholders})"
            cursor.execute(query, available_values)
            
            print(f"✅ Created premium user: {email_used} / premium123")
            message = f"✅ Created premium user: {email_used} / premium123"
        
        conn.commit()
        conn.close()
        
        page.snack_bar = ft.SnackBar(
            ft.Text(message),
            bgcolor=self.success_color,
            duration=5000
        )
        page.snack_bar.open = True
        page.update()

    def show_login(self, page: ft.Page):
        """Show login screen - PRODUCTION VERSION (no test buttons)"""
        page.controls.clear()
        
        # All fields with SAME SIZE
        field_width = 280
        
        email_field = ft.TextField(
            label="Email",
            hint_text="your@email.com",
            width=field_width,
            bgcolor="#2C2C2C",
            border_color=self.accent_color,
        )
        
        password_field = ft.TextField(
            label="Password",
            hint_text="••••••••",
            password=True,
            can_reveal_password=True,
            width=field_width,
            bgcolor="#2C2C2C",
            border_color=self.accent_color,
        )
        
        status_text = ft.Text("", color="red", size=12)
        
        # Check if logo exists - use BASE_DIR for dynamic path
        logo_path = os.path.join(BASE_DIR, "images", "Logo-store.png")
        logo_exists = os.path.exists(logo_path)
        
        def on_login(e):
            user = UserManager.authenticate(email_field.value, password_field.value)
            if user:
                user_dict = dict(user)
                
                # Check if user has valid license
                if user_dict.get('is_premium', False):
                    license_key = user_dict.get('license_key')
                    if license_key:
                        from datetime import datetime
                        license_manager = LicenseManager()
                        is_valid, result = license_manager.validate_license(license_key)
                        if not is_valid:
                            status_text.value = "⚠️ Your license has expired. Please renew."
                            status_text.color = self.warning_color
                            page.update()
                            return
                
                self.current_user = user_dict
                self.show_dashboard(page)
            else:
                status_text.value = "Invalid email or password!"
                page.update()
        
        def on_guest_login(e):
            """Guest login with limited permissions"""
            self.current_user = {
                'id': 0,
                'name': 'Guest User',
                'email': 'guest@store.com',
                'role': 'guest',
                'trial_mode': False,
                'guest_mode': True,
                'is_premium': False
            }
            self.show_dashboard(page)
        
        def on_free_trial(e):
            """Free trial with 14-day trial period"""
            import datetime
            trial_end = datetime.datetime.now() + datetime.timedelta(days=14)
            self.current_user = {
                'id': 0,
                'name': 'Trial User',
                'email': 'trial@store.com',
                'role': 'trial',
                'trial_mode': True,
                'trial_end_date': trial_end.strftime('%Y-%m-%d'),
                'guest_mode': False,
                'is_premium': False
            }
            self.show_dashboard(page)
        
        # Create logo widget
        if logo_exists:
            logo = ft.Image(
                src=logo_path,
                width=100,
                height=100,
                fit=ft.ImageFit.CONTAIN,
            )
        else:
            logo = ft.Text("🏪", size=60)
        
        # Create Sign In Button
        signin_button = ft.FilledButton(
            "Sign In",
            width=140,
            height=45, 
            on_click=on_login,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
        )
        
        # Guest Button
        guest_button = ft.OutlinedButton(
            "Continue as Guest",
            width=280,
            height=40,
            on_click=on_guest_login,
            style=ft.ButtonStyle(
                color=self.text_color,
                side=ft.BorderSide(1, self.accent_color),
            ),
        )
        
        # Free Trial Button
        trial_button = ft.OutlinedButton(
            "Start Free Trial (14 days)",
            width=280,
            height=40,
            on_click=on_free_trial,
            style=ft.ButtonStyle(
                color=self.warning_color,
                side=ft.BorderSide(1, self.warning_color),
            ),
        )
        
        # Create container for logo and sign in button
        logo_button_container = ft.Container(
            content=ft.Row(
                [
                    logo,
                    ft.Container(width=20),
                    signin_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=field_width,
            padding=ft.padding.symmetric(vertical=10, horizontal=0),
        )
        
        # Create main layout (NO TEST BUTTONS SECTION - removed)
        main_layout = ft.Column(
            [
                # Title section
                ft.Text("Welcome", size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Text("Sign in to manage your inventory", size=13, color="#AAAAAA"),
                ft.Container(height=20),
                
                # Decorative line
                ft.Container(
                    width=50,
                    height=2,
                    bgcolor=self.accent_color,
                    border_radius=1,
                ),
                ft.Container(height=20),
                
                # Email field
                email_field,
                ft.Container(height=15),
                
                # Password field
                password_field,
                ft.Container(height=15),
                
                # Status text
                status_text,
                ft.Container(height=10),
                
                # Logo & Button Container
                logo_button_container,
                
                ft.Divider(height=20, color="#3C3C3C"),
                
                # Guest and Trial options
                guest_button,
                ft.Container(height=10),
                trial_button,
                ft.Container(height=10),
                
                # Info text
                ft.Text(
                    "Guest: Limited read-only access | Trial: Full access for 14 days",
                    size=9,
                    color="#666666",
                    text_align=ft.TextAlign.CENTER,
                ),
                
                # Forgot password link
                ft.TextButton(
                    "Forgot Password?",
                    on_click=lambda e: self.show_forgot_password(page),
                    style=ft.ButtonStyle(color="#888888"),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )
        
        # Create login card
        login_card = ft.Container(
            content=main_layout,
            padding=40,
            bgcolor=None,
            border_radius=20,
            width=500,
        )
        
        # Position login card below center using margin
        centered_login = ft.Container(
            content=login_card,
            alignment=ft.alignment.center,
            expand=True,
            margin=ft.margin.only(top=60),
        )
        
        # Background image - use dynamic path
        background_path = os.path.join(BASE_DIR, "images", "backgound_storemgt.png")
        background_image = ft.Image(
            src=background_path,
            fit=ft.ImageFit.COVER,
        )
        
        # Stack background image and centered login
        page.add(
            ft.Stack([
                background_image,
                centered_login,
            ], expand=True)
        )
        page.update()
        
    def show_dashboard(self, page: ft.Page):
        """Show main dashboard with stats cards, tables, and bottom panels"""
        
        # ========== ADD THIS TRIAL EXPIRATION CHECK AT THE VERY TOP ==========
        if self.current_user and self.current_user.get('trial_mode', False):
            trial_end_str = self.current_user.get('trial_end_date')
            if trial_end_str:
                from datetime import datetime
                trial_end_date = datetime.strptime(trial_end_str, '%Y-%m-%d')
                if datetime.now().date() > trial_end_date.date():
                    self.show_upgrade_screen(page)
                    return
        # ========== END OF TRIAL CHECK ==========
        
        # ========== YOUR ORIGINAL DASHBOARD CODE - UNCHANGED ==========
        page.controls.clear()
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        stats = MaterialManager.get_stats()
        accessory_stats = AccessoryManager.get_stats()
        low_stock = self.dict_list(MaterialManager.get_low_stock(10))
        
        sidebar = self.create_sidebar(page)
        
        # Stats cards row
        stats_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("📦 Total Materials", size=14, color="#CCCCCC"),
                        ft.Text(str(stats.get('total_items', 0)), size=36, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20, bgcolor=self.success_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🔧 Accessories", size=14, color="#CCCCCC"),
                        ft.Text(str(accessory_stats.get('total_items', 0)), size=36, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20, bgcolor=self.accent_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📄 Export Records", size=14, color="#CCCCCC"),
                        ft.Text("120", size=36, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20, bgcolor=self.warning_color, border_radius=10, expand=True,
                ),
            ],
            spacing=15,
            expand=True,
        )
        
        # Materials Table Panel (Left)
        materials_rows = []
        for m in materials[:10]:
            materials_rows.append(
                ft.Row([
                    ft.Text(m.get('name', 'N/A'), size=12, width=140),
                    ft.Text(m.get('location_ids') or "N/A", size=12, width=90),
                    ft.Text(m.get('size') or "N/A", size=12, width=80),
                    ft.Container(
                        content=ft.Text(m.get('quality', 'Used'), size=10, color="white"),
                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        width=70,
                    ),
                    ft.Text(str(m.get('quantity', 0)), size=12, width=55),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )
        
        if not materials_rows:
            materials_rows.append(ft.Text("No materials found", size=12, color="#888888"))
        
        materials_table = ft.Column([
            ft.Row([
                ft.Text("Materials", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_materials_screen(page)),
            ]),
            ft.Divider(height=1, color="#3C3C3C"),
            ft.Container(height=5),
            ft.Row([
                ft.Text("Name", size=10, weight=ft.FontWeight.BOLD, width=140),
                ft.Text("Location", size=10, weight=ft.FontWeight.BOLD, width=90),
                ft.Text("Size", size=10, weight=ft.FontWeight.BOLD, width=80),
                ft.Text("Quality", size=10, weight=ft.FontWeight.BOLD, width=70),
                ft.Text("Stock", size=10, weight=ft.FontWeight.BOLD, width=55),
            ], alignment=ft.MainAxisAlignment.START),
        ] + materials_rows, spacing=6, scroll=ft.ScrollMode.AUTO, height=300)
        
        left_panel = ft.Container(
            content=materials_table,
            padding=12,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Accessories Table Panel (Right)
        accessories_rows = []
        for a in accessories[:10]:
            has_image = a.get('image_path') and os.path.exists(a.get('image_path', '')) if a.get('image_path') else False
            image_icon = "🖼️" if has_image else "📷"
            accessories_rows.append(
                ft.Row([
                    ft.Text(image_icon, size=12, width=30),
                    ft.Text(a.get('name', 'N/A'), size=12, width=140),
                    ft.Text(str(a.get('quantity', 0)), size=12, width=70),
                    ft.Container(
                        content=ft.Text(a.get('quality', 'Used'), size=10, color="white"),
                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        width=70,
                    ),
                    ft.Text("View", size=10, color=self.accent_color, width=50),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )
        
        if not accessories_rows:
            accessories_rows.append(ft.Text("No accessories found", size=12, color="#888888"))
        
        accessories_table = ft.Column([
            ft.Row([
                ft.Text("Accessories & Parts", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_accessories(page)),
            ]),
            ft.Divider(height=1, color="#3C3C3C"),
            ft.Container(height=5),
            ft.Row([
                ft.Text("Img", size=10, weight=ft.FontWeight.BOLD, width=30),
                ft.Text("Part Name", size=10, weight=ft.FontWeight.BOLD, width=140),
                ft.Text("Qty", size=10, weight=ft.FontWeight.BOLD, width=70),
                ft.Text("Quality", size=10, weight=ft.FontWeight.BOLD, width=70),
                ft.Text("Notes", size=10, weight=ft.FontWeight.BOLD, width=50),
            ], alignment=ft.MainAxisAlignment.START),
        ] + accessories_rows, spacing=6, scroll=ft.ScrollMode.AUTO, height=300)
        
        right_panel = ft.Container(
            content=accessories_table,
            padding=12,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Middle row
        middle_row = ft.Row([left_panel, right_panel], spacing=15, expand=True, height=380)
        
        # Low Stock Panel
        low_stock_items = []
        for item in low_stock[:5]:
            low_stock_items.append(
                ft.Row([
                    ft.Text(f"• {item.get('name', 'N/A')}", size=12, color=self.text_color, width=150),
                    ft.Text(f"Stock: {item.get('quantity', 0)}", size=12, color=self.danger_color),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
        if not low_stock_items:
            low_stock_items.append(ft.Text("No low stock items", size=12, color="#888888"))
        
        # Low Stock Panel with Bar Chart and Scroll
        low_stock_items = []
        
        # Get low stock materials and accessories
        low_stock_materials = [m for m in materials if m.get('quantity', 0) < 10]
        low_stock_accessories = [a for a in accessories if a.get('quantity', 0) < 10]
        
        # Combine and sort by quantity (lowest first)
        all_low_stock = []
        for m in low_stock_materials:
            all_low_stock.append({
                'name': m.get('name', 'Unknown'),
                'quantity': m.get('quantity', 0),
                'type': '📦',
                'color': self.accent_color
            })
        for a in low_stock_accessories:
            all_low_stock.append({
                'name': a.get('name', 'Unknown'),
                'quantity': a.get('quantity', 0),
                'type': '🔧',
                'color': self.warning_color
            })
        
        # Sort by quantity (lowest first)
        all_low_stock.sort(key=lambda x: x['quantity'])
        top_low_stock = all_low_stock[:15]  # Show up to 15 items
        
        # Find max quantity for scaling
        max_qty = max([item['quantity'] for item in top_low_stock]) if top_low_stock else 10
        max_qty = max(max_qty, 10)
        
        # Create scrollable list of bar chart items
        chart_items = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=180)
        
        if top_low_stock:
            for idx, item in enumerate(top_low_stock):
                percentage = (item['quantity'] / max_qty) * 100
                bar_color = self.danger_color if item['quantity'] < 5 else self.warning_color
                
                chart_items.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"{item['type']}", size=14, width=30),
                                ft.Text(item['name'][:25], size=12, color=self.text_color, width=150),
                                ft.Text(f"Stock: {item['quantity']}", size=11, color=bar_color, width=80),
                                ft.Container(expand=True),
                                ft.Text(f"{percentage:.0f}%", size=10, width=40, color="#888888"),
                            ]),
                            ft.ProgressBar(
                                value=item['quantity'] / max_qty,
                                color=bar_color,
                                bgcolor="#3C3C3C",
                                height=8,
                            ),
                        ], spacing=5),
                        padding=ft.padding.symmetric(vertical=4, horizontal=5),
                    )
                )
            
            # Add legend
            chart_items.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(width=12, height=12, bgcolor=self.danger_color, border_radius=2),
                        ft.Text("Critical (<5)", size=9, color="#888888"),
                        ft.Container(width=12),
                        ft.Container(width=12, height=12, bgcolor=self.warning_color, border_radius=2),
                        ft.Text("Low (<10)", size=9, color="#888888"),
                        ft.Container(width=12),
                        ft.Container(width=12, height=12, bgcolor=self.accent_color, border_radius=2),
                        ft.Text("Materials", size=9, color="#888888"),
                        ft.Container(width=12),
                        ft.Container(width=12, height=12, bgcolor=self.warning_color, border_radius=2),
                        ft.Text("Accessories", size=9, color="#888888"),
                    ], spacing=5, wrap=True),
                    padding=ft.padding.only(top=5),
                )
            )
        else:
            chart_items.controls.append(
                ft.Container(
                    content=ft.Text("✅ No low stock items! All inventory levels are healthy.", size=12, color=self.success_color),
                    padding=20,
                    alignment=ft.alignment.center,
                )
            )
        
        low_stock_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        ft.Text("⚠️ Low Stock Items", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Container(expand=True),
                        ft.Text(f"Total: {len(low_stock_materials) + len(low_stock_accessories)} items", size=11, color="#888888"),
                    ]),
                    ft.Divider(height=1, color="#3C3C3C"),
                    ft.Container(height=5),
                    chart_items,  # Scrollable chart items
                ], spacing=8),
            padding=9,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Import/Export Panel
        # Import/Export Panel
        # Import/Export Panel using Overlay (working version)
        def show_import_overlay(e):
            """Show import overlay at top right"""
            print("Import button clicked!")
            
            def close_overlay():
                page.overlay.clear()
                page.update()
            
            def import_materials(e):
                print("Import Materials clicked")
                close_overlay()
                show_csv_overlay("materials")
            
            def import_accessories(e):
                print("Import Accessories clicked")
                close_overlay()
                show_csv_overlay("accessories")
            
            def show_csv_overlay(data_type):
                """Show CSV input overlay"""
                print(f"Showing CSV overlay for {data_type}")
                
                def close_csv_overlay():
                    page.overlay.clear()
                    page.update()
                
                def process_import(e):
                    csv_text = csv_input.value
                    if not csv_text:
                        page.snack_bar = ft.SnackBar(ft.Text("Please enter CSV data!"), bgcolor=self.danger_color)
                        page.snack_bar.open = True
                        page.update()
                        return
                    
                    try:
                        import csv
                        import io
                        import sqlite3
                        from database import DB_PATH
                        
                        csv_reader = csv.DictReader(io.StringIO(csv_text))
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        imported_count = 0
                        
                        if data_type == "materials":
                            for row in csv_reader:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO materials 
                                    (name, item_code, quantity, size, length, quality, location_ids, colors, notes, barcode_value)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    row.get('name'), row.get('item_code'),
                                    int(row.get('quantity', 0)) if row.get('quantity') else 0,
                                    row.get('size'), row.get('length'), row.get('quality'),
                                    row.get('location_ids'), row.get('colors'), row.get('notes'),
                                    row.get('barcode_value')
                                ))
                                imported_count += 1
                        else:
                            for row in csv_reader:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO accessories 
                                    (name, item_code, quantity, price, quality, location, notes, barcode_value)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    row.get('name'), row.get('item_code'),
                                    int(row.get('quantity', 0)) if row.get('quantity') else 0,
                                    float(row.get('price', 0)) if row.get('price') else 0,
                                    row.get('quality'), row.get('location'),
                                    row.get('notes'), row.get('barcode_value')
                                ))
                                imported_count += 1
                        
                        conn.commit()
                        conn.close()
                        
                        close_csv_overlay()
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"✓ Imported {imported_count} {data_type}"),
                            bgcolor=self.success_color,
                            duration=4000
                        )
                        page.snack_bar.open = True
                        # Refresh dashboard
                        self.show_dashboard(page)
                        
                    except Exception as ex:
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"❌ Import failed: {str(ex)}"),
                            bgcolor=self.danger_color,
                            duration=4000
                        )
                        page.snack_bar.open = True
                        page.update()
                
                # Template
                if data_type == "materials":
                    template = """name,item_code,quantity,size,length,quality,location_ids,colors,notes,barcode_value
    Steel Beam,STL001,50,2x4,96.0,New,Warehouse A,Silver,Heavy duty steel,8901234567890
    Wood Plank,WOD001,30,1x4,48.0,Used,Warehouse B,Brown,Construction wood,8901234567891"""
                else:
                    template = """name,item_code,quantity,price,quality,location,notes,barcode_value
    Drill Bit,DRB001,25,15.99,New,Shelf A1,Professional grade,8901234567892
    Hammer,HAM001,10,24.99,Used,Shelf B2,16oz hammer,8901234567893"""
                
                csv_input = ft.TextField(
                    label="Paste CSV Data",
                    value=template,
                    multiline=True,
                    min_lines=10,
                    max_lines=15,
                    width=550,
                    bgcolor=self.card_color,
                    text_size=11,
                )
                
                # Overlay at top right - INCREASED WIDTH
                overlay_content = ft.Container(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Import {data_type.capitalize()}", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                                ft.Container(expand=True),
                                ft.TextButton("✕", on_click=lambda e: close_csv_overlay()),
                            ]),
                            ft.Divider(),
                            ft.Text("CSV Format (first row must be headers):", size=12, color="#888888"),
                            csv_input,
                            ft.Container(height=10),
                            ft.Row([
                                ft.TextButton("Cancel", on_click=lambda e: close_csv_overlay()),
                                ft.ElevatedButton("Import", on_click=process_import),
                            ], alignment=ft.MainAxisAlignment.END, spacing=10),
                        ], spacing=10),
                        padding=20,
                        bgcolor=self.card_color,
                        border_radius=15,
                        width=700,  # Increased width
                    ),
                    margin=ft.margin.only(top=50, right=50),
                )
                
                page.overlay.append(overlay_content)
                page.update()
            
            # First dialog: choose material or accessory - INCREASED SIZE
            overlay_choice = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Import Data", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                            ft.Container(expand=True),
                            ft.TextButton("✕", on_click=lambda e: close_overlay()),
                        ]),
                        ft.Divider(),
                        ft.Text("Select what to import:", size=14, color="#CCCCCC"),
                        ft.Container(height=15),
                        ft.Row([
                            ft.ElevatedButton("📦 Import Materials", on_click=import_materials, 
                                            style=ft.ButtonStyle(padding=15)),
                            ft.ElevatedButton("🔧 Import Accessories", on_click=import_accessories,
                                            style=ft.ButtonStyle(padding=15)),
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=25,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=400,  # Wider
                    height=220,  # Taller
                ),
                margin=ft.margin.only(top=50, right=50),
            )
            
            page.overlay.append(overlay_choice)
            page.update()
        
        def show_export_overlay(e):
            """Show export overlay at top right"""
            print("Export button clicked!")
            
            def close_overlay():
                page.overlay.clear()
                page.update()
            
            def do_export(e):
                print("Exporting data...")
                try:
                    import csv
                    from datetime import datetime
                    import os
                    
                    export_dir = "exports"
                    if not os.path.exists(export_dir):
                        os.makedirs(export_dir)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    
                    # Export materials
                    materials = self.dict_list(MaterialManager.get_all())
                    if materials:
                        materials_file = os.path.join(export_dir, f"materials_{timestamp}.csv")
                        with open(materials_file, 'w', newline='', encoding='utf-8-sig') as f:
                            writer = csv.DictWriter(f, fieldnames=materials[0].keys())
                            writer.writeheader()
                            writer.writerows(materials)
                    
                    # Export accessories
                    accessories = self.dict_list(AccessoryManager.get_all())
                    if accessories:
                        accessories_file = os.path.join(export_dir, f"accessories_{timestamp}.csv")
                        with open(accessories_file, 'w', newline='', encoding='utf-8-sig') as f:
                            writer = csv.DictWriter(f, fieldnames=accessories[0].keys())
                            writer.writeheader()
                            writer.writerows(accessories)
                    
                    close_overlay()
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Exported to {export_dir}/"),
                        bgcolor=self.success_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    page.update()
                    
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"❌ Export failed: {str(ex)}"),
                        bgcolor=self.danger_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    page.update()
            
            overlay_content = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Export Data", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                            ft.Container(expand=True),
                            ft.TextButton("✕", on_click=lambda e: close_overlay()),
                        ]),
                        ft.Divider(),
                        ft.Text("Click Export to save all data to CSV files", size=14),
                        ft.Container(height=20),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=lambda e: close_overlay()),
                            ft.ElevatedButton("📊 Export All Data", on_click=do_export,
                                            style=ft.ButtonStyle(padding=15)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=400,
                    height=200,
                ),
                margin=ft.margin.only(top=50, right=50),
            )
            
            page.overlay.append(overlay_content)
            page.update()
        
        import_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("📁 Import/Export Management", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(height=1, color="#3C3C3C"),
                    ft.Container(height=5),
                    ft.Row([
                        ft.ElevatedButton("📥 Import Records", on_click=show_import_overlay, 
                                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color, padding=10)),
                        ft.ElevatedButton("📤 Export Records", on_click=show_export_overlay,
                                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color, padding=10)),
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),  # Added alignment
                    ft.Container(height=10),
                    ft.Text("Recent Imports:", size=12, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
                    ft.Text("Click Import to paste CSV data", size=11, color="#888888"),
                    ft.Text("Supported formats: CSV", size=10, color="#888888"),
                    ft.Container(expand=True),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # Added horizontal alignment
            ),
            padding=15,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Users Panel
        users = self.dict_list(UserManager.get_all())
        users_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("👥 Users & Permissions", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(height=1, color="#3C3C3C"),
                    ft.Container(height=5),
                ] + [
                    ft.Row([
                        ft.Text(u.get('name', 'N/A'), size=12, weight=ft.FontWeight.BOLD, color=self.text_color, width=100),
                        ft.Text(u.get('role', 'user'), size=11, color="#4CAF50", width=70),
                        ft.Text("Active", size=11, color="#4CAF50"),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN) for u in users[:5]
                ] + [ft.Container(expand=True)],
                spacing=8,
            ),
            padding=15,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Bottom panels row
        bottom_row = ft.Row([low_stock_panel, import_panel, users_panel], spacing=15, expand=True, height=260)
        
        # Main content
        main_content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(height=15),
                    stats_row,
                    ft.Container(height=15),
                    middle_row,
                    ft.Container(height=15),
                    bottom_row,
                ],
                spacing=5,
                expand=True,
            ),
            expand=True,
            padding=20,
        )
        
        page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        page.update()
        
    def create_sidebar(self, page: ft.Page):
        """Create sidebar navigation with permission-based visibility"""
        
        # Define navigation items: (emoji, label, view, permission)
        nav_items = [
            ("📊", "Dashboard", "dashboard", "view_dashboard"),
            ("📦", "Materials", "materials", "view_materials"),
            ("🔧", "Accessories", "accessories", "view_accessories"),
            ("📷", "Barcode Scan", "barcode_scanner", "scan_barcode"),
            ("📋", "Inventory", "inventory", "view_inventory"),
            ("👥", "Users", "users", "view_users"),
            ("⚙️", "Settings", "settings", "view_settings"),
        ]
        
        nav_buttons = []
        
        def navigate(e, view):
            """Handle navigation with permission check"""
            if view == "dashboard":
                self.show_dashboard(page)
            elif view == "materials":
                if self.has_permission('view_materials'):
                    self.show_materials_screen(page)
                else:
                    self.show_no_permission(page)
            elif view == "accessories":
                if self.has_permission('view_accessories'):
                    self.show_accessories(page)
                else:
                    self.show_no_permission(page)
            elif view == "barcode_scanner":
                if self.has_permission('scan_barcode'):
                    self.show_barcode_scanner(page)
                else:
                    self.show_no_permission(page)
            elif view == "inventory":
                if self.has_permission('view_inventory'):
                    self.show_inventory(page)
                else:
                    self.show_no_permission(page)
            elif view == "users":
                if self.has_permission('view_users'):
                    self.show_users(page)
                else:
                    self.show_no_permission(page)
            elif view == "settings":
                if self.has_permission('view_settings'):
                    self.show_settings(page)
                else:
                    self.show_no_permission(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"{view} screen coming soon!"))
                page.snack_bar.open = True
                page.update()
        
        # Create navigation buttons
        for emoji, label, view, permission in nav_items:
            if self.has_permission(permission):
                btn = ft.Container(
                    content=ft.Row(
                        [ft.Text(emoji, size=20), ft.Text(label, size=14, color=self.text_color)], 
                        spacing=10
                    ),
                    padding=ft.padding.symmetric(horizontal=15, vertical=12),
                    border_radius=8,
                    ink=True,
                    on_click=lambda e, v=view: navigate(e, v),
                )
                nav_buttons.append(btn)
        
        def logout(e):
            self.current_user = None
            self.show_login(page)
        
        logout_btn = ft.Container(
            content=ft.Row([ft.Text("🚪", size=20), ft.Text("Logout", size=14, color="#FF5252")], spacing=10),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=8,
            ink=True,
            on_click=logout,
        )
        
        # Check if logo exists for sidebar
        logo_path = "D:/Project2026/Store Management/images/Logo-store.png"
        logo_exists = os.path.exists(logo_path)
        
        # Create logo for sidebar
        if logo_exists:
            sidebar_logo = ft.Image(
                src=logo_path,
                width=30,
                height=30,
                fit=ft.ImageFit.CONTAIN,
            )
        else:
            sidebar_logo = ft.Text("🏪", size=24)
        
        # Create title row with logo
        title_content = ft.Row(
            [
                sidebar_logo,
                ft.Text("Store Manager", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5,
        )
        
        # Get user role display text
        role = self.current_user.get('role', 'guest') if self.current_user else 'guest'
        is_premium = self.current_user.get('is_premium', False) if self.current_user else False
        is_trial = self.current_user.get('trial_mode', False) if self.current_user else False
        is_guest = self.current_user.get('guest_mode', False) if self.current_user else False
        
        # Set role display color and text
        if is_premium:
            role_display = "💎 PREMIUM"
            role_color = self.success_color
        elif is_trial:
            role_display = "📋 TRIAL"
            role_color = self.warning_color
        elif is_guest:
            role_display = "👤 GUEST"
            role_color = self.accent_color
        else:
            role_display = role.upper()
            role_color = self.text_color
        
        # Add premium expiry info if available
        expiry_info = ""
        if self.current_user and self.current_user.get('license_expiry'):
            expiry_date = datetime.fromisoformat(self.current_user['license_expiry']).strftime('%Y-%m-%d')
            expiry_info = f"Expires: {expiry_date}"
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=title_content, padding=20),
                    ft.Divider(),
                    ft.Column(nav_buttons, spacing=5),
                    ft.Container(expand=True),
                    ft.Divider(),
                    logout_btn,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"User: {self.current_user.get('name', 'User') if self.current_user else 'Guest'}",
                                    size=10,
                                    color="#888888",
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    role_display,
                                    size=10,
                                    color=role_color,
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    expiry_info,
                                    size=9,
                                    color="#666666",
                                    text_align=ft.TextAlign.CENTER,
                                    visible=expiry_info != "",
                                ),
                            ],
                            spacing=3,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=10,
                    ),
                ],
                spacing=0,
            ),
            width=250,
            bgcolor=self.sidebar_color,
        )
    
    def show_no_permission(self, page: ft.Page):
        """Show no permission message"""
        page.snack_bar = ft.SnackBar(
            ft.Text("❌ You don't have permission to access this feature. Please upgrade to premium."),
            bgcolor=self.danger_color,
            duration=4000
        )
        page.snack_bar.open = True
        page.update()

    # ==================== MATERIALS MANAGEMENT ====================
    
    def open_add_modal(self, page: ft.Page):
        """Open a modal overlay for adding material with image upload"""
        
        import random
        import string
        import os
        import shutil
        from datetime import datetime
        
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
        
        # Create images folder if not exists
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
            print(f"Created images folder: {images_folder}")
        
        # Form fields
        name_field = ft.TextField(label="Name *", width=380, bgcolor=self.card_color)
        
        barcode_field = ft.TextField(
            label="Barcode (13 digits)", 
            width=380, 
            bgcolor=self.card_color, 
            hint_text="Auto-generated 13-digit barcode",
            read_only=True,
        )
        
        quantity_field = ft.TextField(label="Quantity", width=380, bgcolor=self.card_color, value="0")
        
        size_field = ft.TextField(
            label="Size", 
            width=380, 
            bgcolor=self.card_color, 
            hint_text="e.g., 34 1/2\" or 24.5",
        )
        
        length_field = ft.TextField(
            label="Length (auto-calculated)", 
            width=380, 
            bgcolor=self.card_color, 
            read_only=True,
            hint_text="Will auto-convert from Size",
        )
        
        quality_field = ft.Dropdown(
            label="Quality *", 
            width=380,
            options=[
                ft.dropdown.Option("New"),
                ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"),
                ft.dropdown.Option("Repaired"),
            ],
            value="New",
            bgcolor=self.card_color,
        )
        
        location_field = ft.TextField(
            label="Location", 
            width=380, 
            bgcolor=self.card_color, 
            hint_text="e.g., Warehouse A, Shelf B1"
        )
        
        color_field = ft.TextField(
            label="Colors", 
            width=380, 
            bgcolor=self.card_color, 
            hint_text="e.g., Red, Blue, Green (comma separated)"
        )
        
        notes_field = ft.TextField(
            label="Notes", 
            width=380, 
            bgcolor=self.card_color, 
            multiline=True,
            min_lines=3,
            max_lines=5,
            hint_text="Enter any additional notes here...",
        )
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Column([
                ft.Text("📷", size=50),
                ft.Text("No Image", size=12, color="#888888"),
                ft.Text("Click 'Upload Image' to select", size=9, color="#888888"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            width=180,
            height=150,
            bgcolor="#2C2C2C",
            border_radius=8,
        )
        
        selected_temp_image = None
        
        # File picker for image upload
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_temp_image
            if e.files:
                file = e.files[0]
                selected_temp_image = file.path
                print(f"Image selected: {selected_temp_image}")
                try:
                    image_preview.content = ft.Column([
                        ft.Image(src=selected_temp_image, width=160, height=120, fit=ft.ImageFit.CONTAIN),
                        ft.Text(file.name[:25] + "..." if len(file.name) > 25 else file.name, size=9, color=self.accent_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                    page.update()
                except Exception as ex:
                    print(f"Preview error: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Image selected: {file.name}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
                dialog_title="Select an Image"
            )
        
        upload_btn = ft.FilledButton("📁 Upload Image", on_click=upload_image, icon="cloud_upload",
                                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        
        def save_uploaded_image():
            """Save the uploaded image to images folder and return the path"""
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"material_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                print(f"Image saved to: {new_path}")
                return new_path
            return None
        
        # Initialize with a barcode
        current_barcode = generate_barcode()
        barcode_field.value = current_barcode
        
        def regenerate_barcode(e):
            nonlocal current_barcode
            current_barcode = generate_barcode()
            barcode_field.value = current_barcode
            page.update()
        
        regenerate_btn = ft.TextButton("🔄 Generate New Barcode", on_click=regenerate_barcode)
        
        def update_length(e):
            size_value = size_field.value
            if size_value:
                converted = self.convert_size_to_length(size_value)
                if converted is not None:
                    length_field.value = str(converted)
                else:
                    length_field.value = ""
            else:
                length_field.value = ""
            page.update()
        
        size_field.on_change = update_length
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def save_material(e):
            name = name_field.value
            if not name:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            
            if not quality_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please select a quality!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            
            barcode_value = barcode_field.value
            quantity = int(quantity_field.value) if quantity_field.value and quantity_field.value.isdigit() else 0
            
            size_value = size_field.value
            length_value = None
            if size_value:
                length_value = self.convert_size_to_length(size_value)
            
            # Save uploaded image if exists
            saved_image_path = save_uploaded_image() if selected_temp_image else None
            print(f"Saving material with image_path: {saved_image_path}")
            
            data = {
                'name': name,
                'item_code': barcode_value,
                'quantity': quantity,
                'size': size_value,
                'length': length_value,
                'quality': quality_field.value,
                'location_ids': location_field.value,
                'colors': color_field.value,
                'notes': notes_field.value,
                'barcode_value': barcode_value,
                'barcode_path': "",
                'image_path': saved_image_path,
            }
            
            result = MaterialManager.create(data)
            
            if result:
                page.overlay.clear()
                quality_color = self.get_quality_color(quality_field.value)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Added: {name}"),
                    bgcolor=quality_color,
                )
                page.snack_bar.open = True
                self.show_materials_screen(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error: Barcode already exists!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
        
        form_column = ft.Column([
            name_field,
            barcode_field,
            ft.Row([regenerate_btn], alignment=ft.MainAxisAlignment.START),
            quantity_field,
            size_field,
            length_field,
            quality_field,
            location_field,
            color_field,
            upload_btn,
            image_preview,
            notes_field,
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=650)
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("➕ Add New Material", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        form_column,
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Save", on_click=save_material, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=520,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
    
    def open_edit_modal(self, page: ft.Page, material_id):
        """Open modal for editing material with working image save"""
        import os
        import shutil
        from datetime import datetime
        
        # Get fresh material data from database
        material = MaterialManager.get_by_id(material_id)
        if not material:
            return
        
        material_dict = dict(material) if material else {}
        
        # Create images folder if not exists
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        # Form fields
        name_field = ft.TextField(label="Name *", value=material_dict.get('name', ''), width=380, bgcolor=self.card_color)
        
        barcode_field = ft.TextField(
            label="Barcode (13 digits)", 
            width=380, 
            bgcolor=self.card_color, 
            value=material_dict.get('barcode_value', ''),
            read_only=True,
        )
        
        quantity_field = ft.TextField(label="Quantity", value=str(material_dict.get('quantity', 0)), width=380, bgcolor=self.card_color)
        
        size_field = ft.TextField(
            label="Size", 
            value=material_dict.get('size') or "", 
            width=380, 
            bgcolor=self.card_color,
            hint_text="e.g., 34 1/2\" or 24.5"
        )
        
        length_field = ft.TextField(
            label="Length (auto-calculated)", 
            value=str(material_dict.get('length') or ""), 
            width=380, 
            bgcolor=self.card_color,
            read_only=True,
        )
        
        quality_field = ft.Dropdown(
            label="Quality *", 
            width=380,
            options=[
                ft.dropdown.Option("New"),
                ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"),
                ft.dropdown.Option("Repaired"),
            ],
            value=material_dict.get('quality', 'New'),
            bgcolor=self.card_color,
        )
        
        location_field = ft.TextField(label="Location", value=material_dict.get('location_ids') or "", width=380, bgcolor=self.card_color)
        color_field = ft.TextField(label="Colors", value=material_dict.get('colors') or "", width=380, bgcolor=self.card_color)
        notes_field = ft.TextField(
            label="Notes", 
            width=380, 
            bgcolor=self.card_color, 
            value=material_dict.get('notes', ''),
            multiline=True, 
            min_lines=3,
            max_lines=5,
        )
        
        # Get the current image path from database - THIS IS THE KEY
        current_image_path = material_dict.get('image_path', '')
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
        print(f"Current image path from DB: {current_image_path}")
        print(f"Has current image: {has_current_image}")
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Column([
                ft.Text("📷", size=40),
                ft.Text("No image", size=10, color="#888888"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            width=150, height=120,
            bgcolor="#2C2C2C",
            border_radius=8,
        )
        
        if has_current_image:
            try:
                image_preview.content = ft.Column([
                    ft.Image(src=current_image_path, width=140, height=100, fit=ft.ImageFit.CONTAIN),
                    ft.Text("Current image", size=8, color=self.accent_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            except Exception as e:
                print(f"Error loading preview: {e}")
        
        selected_temp_image = None
        
        # File picker for image upload
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_temp_image
            if e.files:
                file = e.files[0]
                selected_temp_image = file.path
                print(f"Selected image: {selected_temp_image}")
                try:
                    image_preview.content = ft.Column([
                        ft.Image(src=selected_temp_image, width=140, height=100, fit=ft.ImageFit.CONTAIN),
                        ft.Text("New image selected", size=8, color=self.success_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                    page.update()
                except:
                    pass
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Image selected: {file.name}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
                dialog_title="Select an Image"
            )
        
        upload_btn = ft.FilledButton("📁 Upload New Image", on_click=upload_image, icon="cloud_upload",
                                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        
        def save_uploaded_image():
            """Save uploaded image and return the path"""
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"material_{material_id}_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                print(f"Image saved to: {new_path}")
                return new_path
            return None
        
        def delete_current_image(e):
            """Delete the current image"""
            nonlocal selected_temp_image
            if current_image_path and os.path.exists(current_image_path):
                try:
                    os.remove(current_image_path)
                    print(f"Deleted image: {current_image_path}")
                    image_preview.content = ft.Column([
                        ft.Text("📷", size=40),
                        ft.Text("Image deleted", size=10, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
                    selected_temp_image = "DELETE"
                    page.update()
                    page.snack_bar = ft.SnackBar(ft.Text("✓ Image deleted"), bgcolor=self.success_color)
                    page.snack_bar.open = True
                    page.update()
                except Exception as ex:
                    print(f"Error deleting: {ex}")
        
        delete_btn = ft.TextButton("🗑️ Delete Image", on_click=delete_current_image,
                                style=ft.ButtonStyle(color=self.danger_color),
                                visible=has_current_image)
        
        def regenerate_barcode(e):
            import random
            import string
            
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
            
            new_barcode = barcode_without_checksum + str(checksum)
            barcode_field.value = new_barcode
            page.update()
        
        regenerate_btn = ft.TextButton("🔄 Generate New Barcode", on_click=regenerate_barcode)
        
        def update_length(e):
            size_value = size_field.value
            if size_value:
                converted = self.convert_size_to_length(size_value)
                if converted is not None:
                    length_field.value = str(converted)
                else:
                    length_field.value = ""
            else:
                length_field.value = ""
            page.update()
        
        size_field.on_change = update_length
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def update_material(e):
            name = name_field.value
            if not name:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            
            # Calculate length
            size_value = size_field.value
            length_value = self.convert_size_to_length(size_value) if size_value else None
            
            # Handle image - THIS IS THE CRITICAL PART
            final_image_path = current_image_path  # Start with existing image
            
            if selected_temp_image == "DELETE":
                final_image_path = None
                print("Image will be deleted")
            elif selected_temp_image:
                # New image uploaded
                saved_path = save_uploaded_image()
                if saved_path:
                    final_image_path = saved_path
                    print(f"New image path: {final_image_path}")
                    # Delete old image if it exists and is different
                    if current_image_path and os.path.exists(current_image_path) and current_image_path != saved_path:
                        try:
                            os.remove(current_image_path)
                            print(f"Deleted old image: {current_image_path}")
                        except:
                            pass
            # else: keep existing image (final_image_path already set to current_image_path)
            
            # Prepare data for update
            data = {
                'name': name,
                'quantity': int(quantity_field.value) if quantity_field.value.isdigit() else 0,
                'size': size_value,
                'length': length_value,
                'quality': quality_field.value,
                'location_ids': location_field.value,
                'colors': color_field.value,
                'notes': notes_field.value,
                'barcode_value': barcode_field.value,
                'image_path': final_image_path,  # This MUST be included
            }
            
            print(f"Updating material {material_id}")
            print(f"  image_path to save: {final_image_path}")
            
            # Update using MaterialManager
            result = MaterialManager.update(material_id, data, self.current_user['id'] if self.current_user else None)
            
            if result:
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Updated material: {name}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_materials_screen(page)
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("❌ Error updating material!"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
        
        # Image buttons row
        image_buttons_row = ft.Row(
            [upload_btn, delete_btn],
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        
        form_column = ft.Column([
            name_field,
            barcode_field,
            ft.Row([regenerate_btn], alignment=ft.MainAxisAlignment.START),
            quantity_field,
            size_field,
            length_field,
            quality_field,
            location_field,
            color_field,
            image_buttons_row,
            image_preview,
            notes_field,
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=650)
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("✏️ Edit Material", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        form_column,
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Update Material", on_click=update_material, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=520,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
    
    def open_delete_modal(self, page: ft.Page, material_id):
        """Open modal for delete confirmation"""
        material = MaterialManager.get_by_id(material_id)
        if not material:
            return
        
        material_dict = dict(material)
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            MaterialManager.delete(material_id)
            page.overlay.clear()
            page.snack_bar = ft.SnackBar(ft.Text(f"Deleted: {material_dict.get('name', 'item')}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_materials_screen(page)
            page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Text(f"Delete '{material_dict.get('name', 'item')}'?"),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor="red", color=self.text_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=15),
                    padding=20,
                    width=350,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
    
    def show_barcode_dialog(self, page: ft.Page, item):
        """Show barcode dialog for material or accessory with print option"""
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        item_name = item.get('name', 'Item')
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def print_barcode(e):
            """Open browser print dialog for barcode"""
            page.dialog.open = False
            
            # Create HTML content for printing
            html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Barcode - {barcode_text}</title>
<style>
body {{
    font-family: monospace;
    text-align: center;
    padding: 50px;
    background: white;
}}
.title {{
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 30px;
}}
.item-name {{
    font-size: 18px;
    color: #333;
    margin-bottom: 20px;
}}
.barcode-line {{
    font-size: 48px;
    letter-spacing: 2px;
    color: #1976D2;
}}
.barcode-number {{
    font-size: 32px;
    font-weight: bold;
    margin: 20px 0;
    color: #1976D2;
}}
.instruction {{
    margin-top: 30px;
    font-size: 14px;
    color: #666;
}}
@media print {{
    .no-print {{ display: none; }}
}}
</style>
</head>
<body>
    <div class="title">Product Barcode</div>
    <div class="item-name">{item_name}</div>
    <div class="barcode-line">########################################</div>
    <div class="barcode-number">{barcode_text}</div>
    <div class="barcode-line">########################################</div>
    <div class="instruction">Scan this barcode with your camera</div>
    <div class="no-print" style="margin-top: 40px;">
        <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px;">Print Now</button>
        <button onclick="window.close()" style="padding: 10px 20px; font-size: 16px; margin-left: 10px;">Close</button>
    </div>
    <script>
        setTimeout(function() {{
            window.print();
        }}, 1000);
    </script>
</body>
</html>"""
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            webbrowser.open(f'file://{temp_file.name}')
            
            page.snack_bar = ft.SnackBar(ft.Text("Print window opened! Use browser print (Ctrl+P)"), bgcolor=self.accent_color)
            page.snack_bar.open = True
            page.update()
        
        # Create barcode display for dialog
        barcode_display = ft.Container(
            content=ft.Column([
                ft.Text("#" * 35, size=20, font_family="monospace", color=self.accent_color),
                ft.Text(barcode_text, size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Text("#" * 35, size=20, font_family="monospace", color=self.accent_color),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=20,
            bgcolor="#060B44",
            border_radius=10,
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Barcode: {item_name}", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    barcode_display,
                    ft.Text(f"Value: {barcode_text}", size=12, color="#888888"),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=400,
                height=300,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
                ft.FilledButton("Print Barcode", on_click=print_barcode, style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_barcode_scanner(self, page: ft.Page):
        """Show barcode scanner with manual entry (compatible with Android)"""
        page.controls.clear()
        
        sidebar = self.create_sidebar(page)
        
        # Scanner state
        scanner = None
        is_scanning = False
        
        # Variables
        current_item = None
        
        # Statistics counters
        today_scans = 0
        found_items = 0
        not_found_items = 0
        
        # UI Components
        barcode_input = ft.TextField(
            hint_text="Enter barcode number",
            width=400,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_align=ft.TextAlign.CENTER,
            text_size=16,
        )
        
        scan_result_container = ft.Container(
            content=ft.Column([
                ft.Text("No item scanned yet", size=14, color="#888888", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor=self.card_color,
            border_radius=10,
            height=300,
        )
        
        history_list = ft.Column(spacing=3, scroll=ft.ScrollMode.AUTO, height=120)
        
        status_text = ft.Text("Ready", size=11, color="#888888")
        
        # Stats display
        stats_today = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=self.text_color)
        stats_found = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=self.success_color)
        stats_not_found = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=self.danger_color)
        
        def update_stats():
            stats_today.value = str(today_scans)
            stats_found.value = str(found_items)
            stats_not_found.value = str(not_found_items)
            page.update()
        
        def add_to_history(barcode_val, item_name, found=True):
            nonlocal today_scans, found_items, not_found_items
            today_scans += 1
            if found:
                found_items += 1
            else:
                not_found_items += 1
            update_stats()
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            found_icon = "✅" if found else "❌"
            history_list.controls.insert(0, 
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"🕐 {timestamp}", size=10, color="#888888", width=70),
                        ft.Text(f"{item_name[:30]}", size=11, color=self.text_color, expand=True),
                        ft.Text(f"{barcode_val[-12:]}", size=9, color="#888888", width=100),
                        ft.Text(found_icon, size=10, width=30),
                    ], spacing=8),
                    padding=ft.padding.symmetric(vertical=6, horizontal=10),
                    bgcolor="#3C3C3C" if len(history_list.controls) % 2 == 0 else ft.Colors.TRANSPARENT,
                    border_radius=6,
                )
            )
            if len(history_list.controls) > 20:
                history_list.controls.pop()
            page.update()
        
        def clear_history(e):
            nonlocal today_scans, found_items, not_found_items
            history_list.controls.clear()
            today_scans = 0
            found_items = 0
            not_found_items = 0
            update_stats()
            page.snack_bar = ft.SnackBar(ft.Text("✓ History cleared"), bgcolor=self.success_color, duration=2000)
            page.snack_bar.open = True
            page.update()
        
        def search_barcode(barcode_val):
            nonlocal current_item
            if not barcode_val:
                return
            
            status_text.value = f"🔍 Searching: {barcode_val}"
            status_text.color = self.warning_color
            page.update()
            
            # Search in accessories first
            item = AccessoryManager.get_by_barcode(barcode_val)
            if item:
                current_item = dict(item)
                display_item_details(current_item)
                add_to_history(barcode_val, current_item.get('name', 'Unknown'), True)
                status_text.value = "✅ Found!"
                status_text.color = self.success_color
            else:
                # Search in materials
                item = MaterialManager.get_by_barcode(barcode_val)
                if item:
                    current_item = dict(item)
                    display_item_details(current_item)
                    add_to_history(barcode_val, current_item.get('name', 'Unknown'), True)
                    status_text.value = "✅ Found!"
                    status_text.color = self.success_color
                else:
                    display_not_found(barcode_val)
                    add_to_history(barcode_val, "Not Found", False)
                    status_text.value = "⚠️ Not found"
                    status_text.color = self.warning_color
            
            page.update()
        
        def display_item_details(item):
            is_accessory = 'location' in item
            is_material = 'location_ids' in item
            
            if is_accessory:
                item_type = "🔧 Accessory"
            else:
                item_type = "📦 Material"
            
            qualities = ["New", "Used", "Damaged", "Repaired"]
            current_quality = item.get('quality', 'New')
            current_quantity = item.get('quantity', 0)
            
            quality_dropdown = ft.Dropdown(
                label="New Quality",
                width=150,
                options=[ft.dropdown.Option(q) for q in qualities],
                value=current_quality,
                bgcolor=self.card_color,
            )
            
            quantity_field = ft.TextField(
                label="Remove",
                width=100,
                value="0",
                bgcolor=self.card_color,
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.CENTER,
            )
            
            note_field = ft.TextField(
                label="Note (optional)",
                width=300,
                multiline=True,
                min_lines=2,
                max_lines=2,
                bgcolor=self.card_color,
                text_size=11,
            )
            
            def confirm_update(e):
                new_qty = 0
                try:
                    new_qty = int(quantity_field.value) if quantity_field.value else 0
                except ValueError:
                    new_qty = 0
                
                new_quality = quality_dropdown.value
                note = note_field.value
                
                result = False
                
                if is_accessory:
                    from managers.accessory_manager import AccessoryManager
                    current_qty = item.get('quantity', 0)
                    new_total = current_qty - new_qty if new_qty > 0 else current_qty
                    update_data = {'quantity': new_total, 'quality': new_quality}
                    if note:
                        existing_note = item.get('notes', '')
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                        update_data['notes'] = f"{existing_note}\n[{timestamp}] {note}" if existing_note else f"[{timestamp}] {note}"
                    result = AccessoryManager.update(item['id'], update_data)
                else:
                    from managers.material_manager import MaterialManager
                    current_qty = item.get('quantity', 0)
                    new_total = current_qty - new_qty if new_qty > 0 else current_qty
                    update_data = {'quantity': new_total, 'quality': new_quality}
                    if note:
                        existing_note = item.get('notes', '')
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                        update_data['notes'] = f"{existing_note}\n[{timestamp}] {note}" if existing_note else f"[{timestamp}] {note}"
                    result = MaterialManager.update(item['id'], update_data)
                
                if result:
                    item['quantity'] = new_total
                    item['quality'] = new_quality
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Updated: Qty: {new_total}, Quality: {new_quality}"),
                        bgcolor=self.success_color,
                        duration=2000
                    )
                    page.snack_bar.open = True
                    display_item_details(item)
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"❌ Update failed!"),
                        bgcolor=self.danger_color,
                        duration=2000
                    )
                    page.snack_bar.open = True
                page.update()
            
            if is_accessory:
                location_text = item.get('location', 'N/A')
            else:
                location_text = item.get('location_ids', 'N/A')
            
            scan_result_container.content = ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("✅ ITEM FOUND", size=14, weight=ft.FontWeight.BOLD, color=self.success_color),
                        ft.Container(expand=True),
                        ft.Text(item.get('name', 'N/A'), size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(bottom=8),
                ),
                ft.Divider(),
                ft.Row([ft.Text("Barcode:", size=12, color="#CCCCCC", width=70), ft.Text(item.get('barcode_value') or item.get('item_code', 'N/A'), size=12, color=self.text_color)], spacing=8),
                ft.Row([ft.Text("Type:", size=12, color="#CCCCCC", width=70), ft.Text(item_type, size=12, color=self.text_color)], spacing=8),
                ft.Row([ft.Text("Quality:", size=12, color="#CCCCCC", width=70), ft.Container(content=ft.Text(item.get('quality', 'N/A'), size=11, color="white"), bgcolor=self.get_quality_color(item.get('quality', 'Used')), border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))], spacing=8),
                ft.Row([ft.Text("Quantity:", size=12, color="#CCCCCC", width=70), ft.Text(str(item.get('quantity', 0)), size=13, weight=ft.FontWeight.BOLD, color=self.text_color)], spacing=8),
                ft.Row([ft.Text("Location:", size=12, color="#CCCCCC", width=70), ft.Text(location_text, size=12, color=self.text_color)], spacing=8),
                ft.Divider(),
                ft.Text("✏️ UPDATE STOCK", size=13, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Row([quantity_field, quality_dropdown], spacing=10, wrap=True),
                note_field,
                ft.Row([
                    ft.FilledButton("✅ UPDATE", on_click=confirm_update, width=130, height=40, style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ft.OutlinedButton("❌ CANCEL", on_click=lambda e: display_item_details(item), width=130, height=40),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            ], spacing=8, scroll=ft.ScrollMode.AUTO, height=280)
            scan_result_container.height = None
            page.update()
        
        def display_not_found(barcode_val):
            scan_result_container.content = ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("⚠️ ITEM NOT FOUND", size=14, weight=ft.FontWeight.BOLD, color=self.warning_color),
                        ft.Text("❌", size=20),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(bottom=8),
                ),
                ft.Divider(),
                ft.Text(f"Barcode: {barcode_val}", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Text("No item found in database with this barcode.", size=12, color="#888888"),
                ft.Text("You can add this item from the Materials or Accessories screen.", size=11, color="#888888", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            scan_result_container.height = 180
            page.update()
        
        # Camera functions - FIXED: added 'e' parameter
        def on_barcode_detected(barcode_val):
            search_barcode(barcode_val)
        
        def start_camera(e):  # <-- ADDED 'e' parameter here
            nonlocal scanner, is_scanning
            try:
                from barcode_scanner import CameraScanner
                
                scanner = CameraScanner()
                success, message = scanner.start_scanning(callback=on_barcode_detected)
                
                if success:
                    is_scanning = True
                    status_text.value = "📷 Camera active"
                    status_text.color = self.success_color
                    start_btn.visible = False
                    stop_btn.visible = True
                    page.update()
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Camera opened. Press 'Q' to close."),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
                else:
                    status_text.value = f"ℹ️ {message} Please use manual entry."
                    status_text.color = self.warning_color
                    page.update()
                    
            except Exception as ex:
                status_text.value = f"Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        def stop_camera(e):  # <-- ADDED 'e' parameter here
            nonlocal scanner, is_scanning
            if scanner:
                scanner.stop()
            is_scanning = False
            status_text.value = "Camera stopped"
            status_text.color = "#888888"
            start_btn.visible = True
            stop_btn.visible = False
            page.update()
            
            page.snack_bar = ft.SnackBar(
                ft.Text("Camera stopped"),
                bgcolor=self.success_color,
                duration=2000
            )
            page.snack_bar.open = True
            page.update()
        
        def scan_action(e):
            barcode_val = barcode_input.value.strip()
            if barcode_val:
                search_barcode(barcode_val)
                barcode_input.value = ""
                barcode_input.update()
        
        def paste_action(e):
            clipboard_content = page.get_clipboard()
            if clipboard_content:
                barcode_input.value = clipboard_content
                barcode_input.update()
                search_barcode(clipboard_content)
                barcode_input.value = ""
                barcode_input.update()
        
        # UI Buttons
        start_btn = ft.ElevatedButton("▶ START CAMERA", on_click=start_camera, style=ft.ButtonStyle(bgcolor=self.success_color))
        stop_btn = ft.ElevatedButton("⏹ STOP CAMERA", on_click=stop_camera, visible=False, style=ft.ButtonStyle(bgcolor=self.danger_color))
        
        # ========== STATS CARDS ==========
        stats_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 Today's Scans", size=12, color="#CCCCCC"),
                        stats_today,
                        ft.Text("Total scans today", size=9, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    padding=15,
                    bgcolor=self.card_color,
                    border_radius=12,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("✅ Found Items", size=12, color="#CCCCCC"),
                        stats_found,
                        ft.Text("Successfully found", size=9, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    padding=15,
                    bgcolor=self.card_color,
                    border_radius=12,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("❌ Not Found", size=12, color="#CCCCCC"),
                        stats_not_found,
                        ft.Text("Items not in database", size=9, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    padding=15,
                    bgcolor=self.card_color,
                    border_radius=12,
                    expand=True,
                ),
            ],
            spacing=15,
        )
        
        # ========== BARCODE INPUT SECTION ==========
        barcode_section = ft.Container(
            content=ft.Column([
                ft.Text("📷 Barcode Scanner", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Text("Scan a product barcode to view details or update stock", size=11, color="#888888"),
                ft.Container(height=10),
                barcode_input,
                ft.Row([
                    ft.ElevatedButton("🔍 SCAN", on_click=scan_action, icon=ft.icons.SEARCH, style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    start_btn,
                    stop_btn,
                    ft.ElevatedButton("📋 PASTE", on_click=paste_action, icon=ft.icons.CONTENT_PASTE, style=ft.ButtonStyle(bgcolor=self.warning_color)),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                ft.Text("Or use camera to scan barcode (if available)", size=10, color="#888888"),
            ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            bgcolor=self.card_color,
            border_radius=12,
        )
        
        # ========== SCAN RESULT SECTION ==========
        result_section = ft.Container(
            content=ft.Column([
                ft.Text("📋 Scan Result", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                scan_result_container,
            ], spacing=8),
            padding=15,
            bgcolor=self.card_color,
            border_radius=12,
        )
        
        # ========== HISTORY SECTION ==========
        history_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📜 Recent Scans", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.TextButton("Clear History", on_click=clear_history, style=ft.ButtonStyle(color=self.danger_color)),
                ]),
                ft.Container(content=history_list, height=150, bgcolor=self.card_color, border_radius=8, padding=5),
            ], spacing=8),
            padding=15,
            bgcolor=self.card_color,
            border_radius=12,
        )
        
        # ========== MAIN LAYOUT ==========
        main_content = ft.Column([
            ft.Text("📷 BARCODE SCANNER", size=24, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(height=15),
            
            stats_row,
            ft.Container(height=20),
            
            barcode_section,
            ft.Container(height=20),
            
            result_section,
            ft.Container(height=20),
            
            history_section,
            ft.Container(height=10),
            
            status_text,
        ], scroll=ft.ScrollMode.AUTO)
        
        main_content_container = ft.Container(content=main_content, expand=True, padding=20)
        page.add(ft.Row([sidebar, main_content_container], spacing=0, expand=True))
        page.update()
        
    def show_materials_screen(self, page: ft.Page):
        """Show full materials screen with table on left and detail panel on right"""
        page.controls.clear()
        
        self.page_ref = page
        materials = self.dict_list(MaterialManager.get_all())
        sidebar = self.create_sidebar(page)
        
        # Create search field
        search_field = ft.TextField(
            hint_text="Search...",
            width=180,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            on_change=lambda e: self.search_materials_table(page, e.control.value),
        )
        
        # Create filter buttons
        self.filter_buttons = {}
        
        def create_filter_button(label, color, filter_type):
            btn = ft.Container(
                content=ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=8),
                bgcolor=self.card_color,
                border_radius=20,
                ink=True,
                on_click=lambda e, f=filter_type: self.filter_materials(page, f),
            )
            self.filter_buttons[filter_type] = btn
            return btn
        
        filter_buttons = ft.Row([
            create_filter_button("All", self.accent_color, "All"),
            create_filter_button("New", self.success_color, "New"),
            create_filter_button("Used", self.warning_color, "Used"),
            create_filter_button("Damaged", self.danger_color, "Damaged"),
            create_filter_button("Repaired", self.accent_color, "Repaired"),
        ], spacing=10)
        
        # Set "All" button as active by default
        if "All" in self.filter_buttons:
            self.filter_buttons["All"].bgcolor = self.accent_color
        
        add_button = ft.FilledButton(
            "➕ Add Material",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
            on_click=lambda e: self.open_add_modal(page),
        )
        
        # Table header - UPDATED: Added Image column, removed Barcode column
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Image", size=11, weight=ft.FontWeight.BOLD, width=60),
                ft.Text("Name", size=11, weight=ft.FontWeight.BOLD, width=160),
                ft.Text("Length", size=11, weight=ft.FontWeight.BOLD, width=60),
                ft.Text("Size", size=11, weight=ft.FontWeight.BOLD, width=80),
                ft.Text("Qty", size=11, weight=ft.FontWeight.BOLD, width=50),
                ft.Text("Quality", size=11, weight=ft.FontWeight.BOLD, width=80),
                ft.Text("Location", size=11, weight=ft.FontWeight.BOLD, width=100),
                ft.Text("Created", size=11, weight=ft.FontWeight.BOLD, width=100),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=8, horizontal=10),
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # Table rows container
        self.table_rows_container = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=450)
        self.update_materials_table(materials)
        
        # Left panel - Table
        left_panel = ft.Container(
            content=ft.Column([header_row, self.table_rows_container], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=10,
            padding=5,
        )
        
        # Right panel - Detail
        self.detail_panel = ft.Container(
            content=self.create_detail_panel(None, page),
            width=320,
            bgcolor=self.card_color,
            border_radius=10,
            padding=15,
        )
        
        # Main content
        content = ft.Column([
            ft.Row([
                ft.Text("Materials", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Row([ft.Text("🔍", size=16), search_field], spacing=5),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=5),
            ft.Row([filter_buttons, ft.Container(expand=True), add_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=15),
            ft.Row([left_panel, ft.Container(width=15), self.detail_panel], spacing=0, expand=True),
        ], expand=True)
        
        main_content = ft.Container(content=content, expand=True, padding=20)
        page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        page.update()
        self.current_view = "materials"
    
    def update_materials_table(self, materials):
        """Update the materials table with given materials"""
        self.table_rows_container.controls.clear()
        
        # Format datetime for table display
        def format_datetime_short(date_value):
            if date_value:
                date_str = str(date_value)
                if ' ' in date_str:
                    return date_str.split(' ')[0]
                elif len(date_str) == 10:
                    return date_str
                else:
                    return date_str[:10] if len(date_str) > 10 else date_str
            return 'N/A'
        
        for m in materials:
            is_selected = self.selected_material_detail and self.selected_material_detail.get('id') == m.get('id')
            
            # Check if image exists
            image_path = m.get('image_path', '')
            has_image = image_path and os.path.exists(image_path) if image_path else False
            image_icon = "🖼️" if has_image else "📷"
            
            # Format created date
            created_date = format_datetime_short(m.get('created_at', ''))
            
            row = ft.Container(
                content=ft.Row([
                    ft.Text(image_icon, size=14, width=60),
                    ft.Text(m.get('name', 'N/A'), size=11, width=160),
                    ft.Text(str(m.get('length') or ""), size=11, width=60),
                    ft.Text(m.get('size') or "N/A", size=11, width=80),
                    ft.Text(str(m.get('quantity', 0)), size=11, width=50),
                    ft.Container(
                        content=ft.Text(m.get('quality', 'Used'), size=10, color="white"),
                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        width=75,
                    ),
                    ft.Text(m.get('location_ids') or "N/A", size=11, width=100),
                    ft.Text(created_date, size=10, width=100, color="#888888"),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(vertical=8, horizontal=10),
                bgcolor=self.accent_color if is_selected else ft.colors.TRANSPARENT,
                border_radius=6,
                ink=True,
                on_click=lambda e, mat=m: self.on_material_select(mat),
            )
            self.table_rows_container.controls.append(row)
    
    def search_materials_table(self, page: ft.Page, query):
        """Search materials and update table"""
        if not query:
            if self.current_filter == "All":
                materials = self.dict_list(MaterialManager.get_all())
            else:
                all_materials = self.dict_list(MaterialManager.get_all())
                materials = [m for m in all_materials if m.get('quality') == self.current_filter]
        else:
            searched_materials = self.dict_list(MaterialManager.search(query))
            if self.current_filter != "All":
                materials = [m for m in searched_materials if m.get('quality') == self.current_filter]
            else:
                materials = searched_materials
        
        self.update_materials_table(materials)
        page.update()
    
    def filter_materials(self, page: ft.Page, filter_type):
        """Filter materials by quality with button color change"""
        self.current_filter = filter_type
        
        # Update button colors
        for btn in self.filter_buttons.values():
            btn.bgcolor = self.card_color
        
        # Set active button color
        if filter_type == "All":
            self.filter_buttons["All"].bgcolor = self.accent_color
        elif filter_type == "New":
            self.filter_buttons["New"].bgcolor = self.success_color
        elif filter_type == "Used":
            self.filter_buttons["Used"].bgcolor = self.warning_color
        elif filter_type == "Damaged":
            self.filter_buttons["Damaged"].bgcolor = self.danger_color
        elif filter_type == "Repaired":
            self.filter_buttons["Repaired"].bgcolor = self.accent_color
        
        # Filter materials
        if filter_type == "All":
            materials = self.dict_list(MaterialManager.get_all())
        else:
            all_materials = self.dict_list(MaterialManager.get_all())
            materials = [m for m in all_materials if m.get('quality') == filter_type]
        
        self.update_materials_table(materials)
        page.update()
    
    def on_material_select(self, material):
        """Handle material selection from table"""
        self.selected_material_detail = material
        self.detail_panel.content = self.create_detail_panel(material, self.page_ref)
        self.page_ref.update()
        self.update_materials_table(self.dict_list(MaterialManager.get_all()))
    
    def create_detail_panel(self, material, page):
        """Create the detail panel for selected material with image"""
        if not material:
            return ft.Column([
                ft.Text("Material Details", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Container(height=20),
                ft.Text("Select a material to view details", size=12, color="#888888"),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        # Get base directory for resolving image paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get image path
        image_path = material.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
        
        # Format dates
        def format_datetime(date_value):
            if date_value:
                date_str = str(date_value)
                if ' ' in date_str:
                    return date_str.split(' ')[0]
                return date_str[:10] if len(date_str) > 10 else date_str
            return 'N/A'
        
        created_date = format_datetime(material.get('created_at', ''))
        updated_date = format_datetime(material.get('updated_at', ''))
        
        # ========== IMAGE WIDGET ==========
        def show_image_overlay(e):
            def close_overlay():
                page.overlay.clear()
                page.update()
            
            if not has_image:
                no_image = ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Container(expand=True), ft.TextButton("✕", on_click=lambda e: close_overlay())]),
                        ft.Text("📷", size=60),
                        ft.Text("No Image Available", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text("Click Edit to add an image", size=12, color="#888888"),
                        ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    padding=30,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=400,
                    height=350,
                )
                overlay = ft.Container(content=no_image, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
                page.overlay.append(overlay)
                page.update()
                return
            
            img = ft.Image(src=full_image_path, width=500, height=400, fit=ft.ImageFit.CONTAIN)
            overlay_content = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(material.get('name', 'Image'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Container(expand=True),
                        ft.TextButton("✕", on_click=lambda e: close_overlay()),
                    ]),
                    ft.Divider(),
                    img,
                    ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=25,
                bgcolor=self.card_color,
                border_radius=15,
                width=550,
                height=500,
            )
            overlay = ft.Container(content=overlay_content, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
            page.overlay.append(overlay)
            page.update()
        
        # Create image display
        if has_image:
            try:
                image_display = ft.Container(
                    content=ft.Column([
                        ft.Image(src=full_image_path, width=180, height=140, fit=ft.ImageFit.CONTAIN),
                        ft.Text("Click to enlarge", size=9, color=self.accent_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    on_click=show_image_overlay,
                    ink=True,
                )
            except:
                image_display = None
        else:
            image_display = None
        
        # Build the column
        column_items = [
            ft.Text(material.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
        ]
        
        # Add image if it exists
        if image_display:
            column_items.append(ft.Row([image_display], alignment=ft.MainAxisAlignment.CENTER))
            column_items.append(ft.Container(height=10))
        
        # Add details with SHOW BARCODE button right after CODE
        column_items.extend([
            # Code row
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # SHOW BARCODE BUTTON - right below the code
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, material), style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=5),
            
            # Quality
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(
                        content=ft.Text(material.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(material.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    )], spacing=5),
            
            # Size
            ft.Row([ft.Text("📏 Size:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('size') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Length
            ft.Row([ft.Text("📐 Length:", size=12, color="#CCCCCC", width=80), ft.Text(str(material.get('length') or "N/A"), size=12, color=self.text_color)], spacing=5),
            
            # Quantity
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), ft.Text(str(material.get('quantity', 0)), size=12, color=self.text_color)], spacing=5),
            
            # Location
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('location_ids') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Colors
            ft.Row([ft.Text("🎨 Colors:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('colors') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Created
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), ft.Text(created_date, size=12, color=self.text_color)], spacing=5),
            
            # Updated
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=80), ft.Text(updated_date, size=12, color=self.text_color)], spacing=5),
            
            ft.Divider(),
            
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(material.get('notes') or "No notes", size=12, color="#888888"),
            
            ft.Container(height=15),
            
            # EDIT AND DELETE BUTTONS
            ft.Row(
                [
                    ft.ElevatedButton(
                        "✏️ EDIT", 
                        on_click=lambda e: self.open_edit_modal(page, material['id']),
                        style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
                    ),
                    ft.ElevatedButton(
                        "🗑️ DELETE", 
                        on_click=lambda e: self.open_delete_modal(page, material['id']),
                        style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15,
            ),
        ])
        
        return ft.Column(column_items, spacing=10, scroll=ft.ScrollMode.AUTO)
    
    # ==================== ACCESSORIES MANAGEMENT ====================
    
    def show_accessories(self, page: ft.Page):
        """Show accessories management screen"""
        page.controls.clear()
        
        self.page_ref = page
      #  accessories = self.dict_list(AccessoryManager.get_all())
        accessories = AccessoryManager.get_all()
        sidebar = self.create_sidebar(page)
        
        # Create search field
        search_field = ft.TextField(
            hint_text="Search accessories...",
            width=180,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            on_change=lambda e: self.search_accessories_table(page, e.control.value),
        )
        
        # Create filter buttons with toggle effect for accessories
        self.accessory_filter_buttons = {}
        
        def create_accessory_filter_button(label, active_color, filter_type):
            btn = ft.Container(
                content=ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=8),
                bgcolor=self.card_color if self.current_accessory_filter != filter_type else active_color,
                border_radius=20,
                ink=True,
                on_click=lambda e, f=filter_type: filter_accessories(f),
            )
            self.accessory_filter_buttons[filter_type] = btn
            return btn
        
        filter_buttons = ft.Row([
            create_accessory_filter_button("All", self.accent_color, "All"),
            create_accessory_filter_button("New", self.success_color, "New"),
            create_accessory_filter_button("Used", self.warning_color, "Used"),
            create_accessory_filter_button("Damaged", self.danger_color, "Damaged"),
            create_accessory_filter_button("Repaired", self.accent_color, "Repaired"),
        ], spacing=10)
        
        def filter_accessories(filter_type):
            self.current_accessory_filter = filter_type
            
            # Update button colors
            for f_type, btn in self.accessory_filter_buttons.items():
                if f_type == filter_type:
                    if f_type == "New":
                        btn.bgcolor = self.success_color
                    elif f_type == "Used":
                        btn.bgcolor = self.warning_color
                    elif f_type == "Damaged":
                        btn.bgcolor = self.danger_color
                    elif f_type == "Repaired":
                        btn.bgcolor = self.accent_color
                    else:  # All
                        btn.bgcolor = self.accent_color
                else:
                    btn.bgcolor = self.card_color
                btn.update()
            
            # Filter accessories
            if filter_type == "All":
                filtered = self.dict_list(AccessoryManager.get_all())
            else:
                all_accessories = self.dict_list(AccessoryManager.get_all())
                filtered = [a for a in all_accessories if a.get('quality') == filter_type]
            
            self.update_accessories_table(filtered)
            page.update()
        
        add_button = ft.FilledButton(
            "➕ Add Accessory",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
            on_click=lambda e: self.open_add_accessory_modal(page),
            disabled=not self.has_permission('add_accessory'),  # Add this
        )
        
        # Table header
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Image", size=11, weight=ft.FontWeight.BOLD, width=60),
                ft.Text("Name", size=11, weight=ft.FontWeight.BOLD, width=200),
                ft.Text("Item Code", size=11, weight=ft.FontWeight.BOLD, width=120),
                ft.Text("Qty", size=11, weight=ft.FontWeight.BOLD, width=50),
                ft.Text("Quality", size=11, weight=ft.FontWeight.BOLD, width=80),
                ft.Text("Location", size=11, weight=ft.FontWeight.BOLD, width=100),
                ft.Text("Created", size=11, weight=ft.FontWeight.BOLD, width=110),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=8, horizontal=10),
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # Table rows container
        self.accessory_rows_container = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=450)
        self.update_accessories_table(accessories)
        
        # Left panel - Table
        left_panel = ft.Container(
            content=ft.Column([header_row, self.accessory_rows_container], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=10,
            padding=5,
        )
        
        # Right panel - Detail
        self.accessory_detail_panel = ft.Container(
            content=self.create_accessory_detail_panel(None, page),
            width=320,
            bgcolor=self.card_color,
            border_radius=10,
            padding=15,
        )
        
        # Main content
        content = ft.Column([
            ft.Row([
                ft.Text("Accessories & Parts", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Row([ft.Text("🔍", size=16), search_field], spacing=5),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=5),
            ft.Row([filter_buttons, ft.Container(expand=True), add_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=15),
            ft.Row([left_panel, ft.Container(width=15), self.accessory_detail_panel], spacing=0, expand=True),
        ], expand=True)
        
        main_content = ft.Container(content=content, expand=True, padding=20)
        page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        page.update()
    
    def update_accessories_table(self, accessories):
        """Update the accessories table with given accessories"""
        self.accessory_rows_container.controls.clear()
        
        # Format datetime for table display
        def format_datetime_short(date_value):
            if date_value:
                date_str = str(date_value)
                if ' ' in date_str:
                    parts = date_str.split(' ')
                    date_part = parts[0]
                    time_part = parts[1][:5] if len(parts[1]) > 5 else parts[1]
                    return f"{date_part} {time_part}"
                elif len(date_str) == 10:
                    return f"{date_str}"
                else:
                    return date_str[:10] if len(date_str) > 10 else date_str
            return 'N/A'
        
        for a in accessories:
            is_selected = self.selected_accessory_detail and self.selected_accessory_detail.get('id') == a.get('id')
            
            # Show image icon
            has_image = a.get('image_path') and os.path.exists(a.get('image_path', '')) if a.get('image_path') else False
            image_text = "🖼️" if has_image else "📷"
            
            # Get location from either field name
            location = a.get('location') or a.get('location_ids') or "N/A"
            
            # Format created date with time
            created_date = format_datetime_short(a.get('created_at', ''))
            
            row = ft.Container(
                content=ft.Row([
                    ft.Text(image_text, size=14, width=60),
                    ft.Text(a.get('name', 'N/A'), size=11, width=200),
                    ft.Text(a.get('item_code', 'N/A'), size=11, width=120),
                    ft.Text(str(a.get('quantity', 0)), size=11, width=50),
                    ft.Container(
                        content=ft.Text(a.get('quality', 'Used'), size=10, color="white"),
                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        width=75,
                    ),
                    ft.Text(location, size=11, width=100),
                    ft.Text(created_date, size=10, width=110, color="#888888"),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(vertical=8, horizontal=10),
                bgcolor=self.accent_color if is_selected else ft.colors.TRANSPARENT,
                border_radius=6,
                ink=True,
                on_click=lambda e, acc=a: self.on_accessory_select(acc),
            )
            self.accessory_rows_container.controls.append(row)
    
    def search_accessories_table(self, page: ft.Page, query):
        """Search accessories and update table"""
        if not query:
            if self.current_accessory_filter == "All":
                accessories = self.dict_list(AccessoryManager.get_all())
            else:
                all_accessories = self.dict_list(AccessoryManager.get_all())
                accessories = [a for a in all_accessories if a.get('quality') == self.current_accessory_filter]
        else:
            searched_accessories = self.dict_list(AccessoryManager.search(query))
            if self.current_accessory_filter != "All":
                accessories = [a for a in searched_accessories if a.get('quality') == self.current_accessory_filter]
            else:
                accessories = searched_accessories
        
        self.update_accessories_table(accessories)
        page.update()
    
    def filter_accessories(self, page: ft.Page, filter_type):
        """Filter accessories by quality"""
        self.current_accessory_filter = filter_type
        
        if filter_type == "All":
            accessories = self.dict_list(AccessoryManager.get_all())
        else:
            all_accessories = self.dict_list(AccessoryManager.get_all())
            accessories = [a for a in all_accessories if a.get('quality') == filter_type]
        
        self.update_accessories_table(accessories)
        page.update()

    def dict_list(self, rows):
        """Convert list of sqlite3.Row to list of dictionaries"""
        if rows is None:
            return []
        result = []
        for row in rows:
            if row is not None:
                # If it's already a dict, use it
                if isinstance(row, dict):
                    result.append(row)
                else:
                    # Convert tuple/row to dict using cursor description
                    try:
                        result.append(dict(row))
                    except:
                        # If dict() fails, create manually
                        if hasattr(row, 'keys'):
                            result.append({key: row[key] for key in row.keys()})
                        else:
                            result.append({})
        return result
    def on_accessory_select(self, accessory):
        """Handle accessory selection from table"""
        self.selected_accessory_detail = accessory
        self.accessory_detail_panel.content = self.create_accessory_detail_panel(accessory, self.page_ref)
        self.page_ref.update()
        self.update_accessories_table(self.dict_list(AccessoryManager.get_all()))
    
    def create_accessory_detail_panel(self, accessory, page):
        """Create the detail panel for selected accessory with image"""
        if not accessory:
            return ft.Column([
                ft.Text("Accessory Details", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Container(height=20),
                ft.Text("Select an accessory to view details", size=12, color="#888888"),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        # Get base directory for resolving image paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Get image path
        image_path = accessory.get('image_path', '')
        has_image = False
        full_image_path = None
        
        if image_path:
            if os.path.exists(image_path):
                has_image = True
                full_image_path = image_path
            else:
                relative_path = os.path.join(base_dir, image_path)
                if os.path.exists(relative_path):
                    has_image = True
                    full_image_path = relative_path
        
        # Format dates
        def format_datetime(date_value):
            if date_value:
                date_str = str(date_value)
                if ' ' in date_str:
                    return date_str.split(' ')[0]
                return date_str[:10] if len(date_str) > 10 else date_str
            return 'N/A'
        
        created_date = format_datetime(accessory.get('created_at', ''))
        updated_date = format_datetime(accessory.get('updated_at', ''))
        
        # Get location (accessories use 'location' field, not 'location_ids')
        location = accessory.get('location') or accessory.get('location_ids') or "N/A"
        
        # Get price (accessories have price field)
        price_value = accessory.get('price', 0)
        price_text = f"${price_value:.2f}" if price_value else "N/A"
        
        # ========== IMAGE WIDGET ==========
        def show_image_overlay(e):
            def close_overlay():
                page.overlay.clear()
                page.update()
            
            if not has_image:
                no_image = ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Container(expand=True), ft.TextButton("✕", on_click=lambda e: close_overlay())]),
                        ft.Text("📷", size=60),
                        ft.Text("No Image Available", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text("Click Edit to add an image", size=12, color="#888888"),
                        ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    padding=30,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=400,
                    height=350,
                )
                overlay = ft.Container(content=no_image, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
                page.overlay.append(overlay)
                page.update()
                return
            
            img = ft.Image(src=full_image_path, width=500, height=400, fit=ft.ImageFit.CONTAIN)
            overlay_content = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(accessory.get('name', 'Image'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Container(expand=True),
                        ft.TextButton("✕", on_click=lambda e: close_overlay()),
                    ]),
                    ft.Divider(),
                    img,
                    ft.ElevatedButton("Close", on_click=lambda e: close_overlay()),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=25,
                bgcolor=self.card_color,
                border_radius=15,
                width=550,
                height=500,
            )
            overlay = ft.Container(content=overlay_content, alignment=ft.alignment.center, expand=True, bgcolor="#80000000")
            page.overlay.append(overlay)
            page.update()
        
        # Create image display
        if has_image:
            try:
                image_display = ft.Container(
                    content=ft.Column([
                        ft.Image(src=full_image_path, width=180, height=140, fit=ft.ImageFit.CONTAIN),
                        ft.Text("Click to enlarge", size=9, color=self.accent_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    on_click=show_image_overlay,
                    ink=True,
                )
            except:
                image_display = None
        else:
            image_display = None
        
        # Build the column
        column_items = [
            ft.Text(accessory.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
        ]
        
        # Add image if it exists
        if image_display:
            column_items.append(ft.Row([image_display], alignment=ft.MainAxisAlignment.CENTER))
            column_items.append(ft.Container(height=10))
        
        # Add details with SHOW BARCODE button right after CODE
        column_items.extend([
            # Code row
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), ft.Text(accessory.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # SHOW BARCODE BUTTON - right below the code
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, accessory), style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=5),
            
            # Quality
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(
                        content=ft.Text(accessory.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(accessory.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    )], spacing=5),
            
            # Quantity
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), ft.Text(str(accessory.get('quantity', 0)), size=12, color=self.text_color)], spacing=5),
            
            # Price (accessories have price field)
            ft.Row([ft.Text("💰 Price:", size=12, color="#CCCCCC", width=80), ft.Text(price_text, size=12, color=self.text_color)], spacing=5),
            
            # Location (accessories use 'location' field)
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), ft.Text(location, size=12, color=self.text_color)], spacing=5),
            
            # Created
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), ft.Text(created_date, size=12, color=self.text_color)], spacing=5),
            
            # Updated
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=80), ft.Text(updated_date, size=12, color=self.text_color)], spacing=5),
            
            ft.Divider(),
            
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(accessory.get('notes') or "No notes", size=12, color="#888888"),
            
            ft.Container(height=15),
            
            # EDIT AND DELETE BUTTONS
            ft.Row(
                [
                    ft.ElevatedButton(
                        "✏️ EDIT", 
                        on_click=lambda e: self.open_edit_accessory_modal(page, accessory['id']),
                        style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color),
                    ),
                    ft.ElevatedButton(
                        "🗑️ DELETE", 
                        on_click=lambda e: self.open_delete_accessory_modal(page, accessory['id']),
                        style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15,
            ),
        ])
        
        return ft.Column(column_items, spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def open_add_accessory_modal(self, page: ft.Page):
        """Open modal for adding accessory with image upload (no path field)"""
        
        import random
        import string
        import os
        import shutil
        from datetime import datetime
        
        def generate_barcode():
            """Generate a unique numeric barcode"""
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
        
        # Create images folder if not exists
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        name_field = ft.TextField(label="Name *", width=380, bgcolor=self.card_color)
        barcode_field = ft.TextField(
            label="Barcode (13 digits)", 
            width=380, 
            bgcolor=self.card_color, 
            read_only=True,
        )
        quantity_field = ft.TextField(label="Quantity", width=380, bgcolor=self.card_color, value="0")
        
        quality_field = ft.Dropdown(
            label="Quality *", 
            width=380,
            options=[
                ft.dropdown.Option("New"),
                ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"),
                ft.dropdown.Option("Repaired"),
            ],
            value="New",
            bgcolor=self.card_color,
        )
        
        location_field = ft.TextField(label="Location", width=380, bgcolor=self.card_color)
        notes_field = ft.TextField(
            label="Notes", 
            width=380, 
            bgcolor=self.card_color, 
            multiline=True, 
            min_lines=3,
            max_lines=5,
        )
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Column([
                ft.Text("📷", size=50),
                ft.Text("No Image", size=12, color="#888888"),
                ft.Text("Click 'Upload Image' to select", size=9, color="#888888"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            width=180,
            height=150,
            bgcolor="#2C2C2C",
            border_radius=8,
        )
        
        selected_temp_image = None
        
        # File picker for image upload
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_temp_image
            if e.files:
                file = e.files[0]
                selected_temp_image = file.path
                # Update preview
                try:
                    image_preview.content = ft.Column([
                        ft.Image(src=selected_temp_image, width=160, height=120, fit=ft.ImageFit.CONTAIN),
                        ft.Text(file.name[:25] + "..." if len(file.name) > 25 else file.name, size=9, color=self.accent_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                    page.update()
                except:
                    pass
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Image selected: {file.name}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
                dialog_title="Select an Image"
            )
        
        upload_btn = ft.FilledButton("📁 Upload Image", on_click=upload_image, icon="cloud_upload",
                                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        
        def save_uploaded_image():
            """Save the uploaded image to images folder"""
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"accessory_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                return new_path
            return None
        
        # Initialize with a barcode
        current_barcode = generate_barcode()
        barcode_field.value = current_barcode
        
        def regenerate_barcode(e):
            nonlocal current_barcode
            current_barcode = generate_barcode()
            barcode_field.value = current_barcode
            page.update()
        
        regenerate_btn = ft.TextButton("🔄 Generate New Barcode", on_click=regenerate_barcode)
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def save_accessory(e):
            name = name_field.value
            if not name:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            
            barcode_value = barcode_field.value
            
            # Save uploaded image if exists
            saved_image_path = save_uploaded_image() if selected_temp_image else None
            
            data = {
                'name': name,
                'item_code': barcode_value,
                'quantity': int(quantity_field.value) if quantity_field.value.isdigit() else 0,
                'quality': quality_field.value,
                'location_ids': location_field.value,
                'image_path': saved_image_path,
                'notes': notes_field.value,
                'barcode_value': barcode_value,
            }
            
            from managers.accessory_manager import AccessoryManager
            result = AccessoryManager.create(data)
            
            if result:
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Added accessory: {name} | Barcode: {barcode_value}"), 
                    bgcolor=self.success_color
                )
                page.snack_bar.open = True
                self.show_accessories(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error: Barcode already exists!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
        
        # Form layout (without Image Path field)
        form_column = ft.Column([
            name_field,
            barcode_field,
            ft.Row([regenerate_btn], alignment=ft.MainAxisAlignment.START),
            quantity_field,
            quality_field,
            location_field,
            upload_btn,
            image_preview,
            notes_field,
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=550)
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("➕ Add New Accessory", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        form_column,
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Save Accessory", on_click=save_accessory, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=500,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
    
    def open_edit_accessory_modal(self, page: ft.Page, accessory_id):
        """Open modal for editing accessory with image upload"""
        import os
        import shutil
        from datetime import datetime
        
        accessory = AccessoryManager.get_by_id(accessory_id)
        if not accessory:
            return
        
        accessory_dict = dict(accessory) if accessory else {}
        
        # Create images folder if not exists
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        name_field = ft.TextField(label="Name *", value=accessory_dict.get('name', ''), width=380, bgcolor=self.card_color)
        
        barcode_field = ft.TextField(
            label="Barcode (13 digits)", 
            width=380, 
            bgcolor=self.card_color, 
            value=accessory_dict.get('barcode_value', ''),
            read_only=True,
        )
        
        quantity_field = ft.TextField(label="Quantity", value=str(accessory_dict.get('quantity', 0)), width=380, bgcolor=self.card_color)
        
        quality_field = ft.Dropdown(
            label="Quality *", 
            width=380,
            options=[
                ft.dropdown.Option("New"),
                ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"),
                ft.dropdown.Option("Repaired"),
            ],
            value=accessory_dict.get('quality', 'New'),
            bgcolor=self.card_color,
        )
        
        location_field = ft.TextField(label="Location", value=accessory_dict.get('location') or "", width=380, bgcolor=self.card_color)
        notes_field = ft.TextField(
            label="Notes", 
            width=380, 
            bgcolor=self.card_color, 
            value=accessory_dict.get('notes', ''),
            multiline=True, 
            min_lines=3,
            max_lines=5,
        )
        
        # Current image
        current_image = accessory_dict.get('image_path', '')
        has_current_image = current_image and os.path.exists(current_image) if current_image else False
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Column([
                ft.Text("📷", size=40),
                ft.Text("No image", size=10, color="#888888"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            width=150, height=120,
            bgcolor="#2C2C2C",
            border_radius=8,
        )
        
        if has_current_image:
            try:
                image_preview.content = ft.Column([
                    ft.Image(src=current_image, width=140, height=100, fit=ft.ImageFit.CONTAIN),
                    ft.Text("Current image", size=8, color=self.accent_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            except:
                pass
        
        selected_temp_image = None
        
        # File picker for image upload
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_temp_image
            if e.files:
                file = e.files[0]
                selected_temp_image = file.path
                try:
                    image_preview.content = ft.Column([
                        ft.Image(src=selected_temp_image, width=140, height=100, fit=ft.ImageFit.CONTAIN),
                        ft.Text("New image selected", size=8, color=self.success_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                    page.update()
                except:
                    pass
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Image selected: {file.name}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                page.update()
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
                dialog_title="Select an Image"
            )
        
        upload_btn = ft.FilledButton("📁 Upload New Image", on_click=upload_image, icon="cloud_upload",
                                    style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        
        def save_uploaded_image():
            """Save the uploaded image to images folder"""
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"accessory_{accessory_id}_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                return new_path
            return None
        
        def regenerate_barcode(e):
            import random
            import string
            
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
            
            new_barcode = barcode_without_checksum + str(checksum)
            barcode_field.value = new_barcode
            page.update()
        
        regenerate_btn = ft.TextButton("🔄 Generate New Barcode", on_click=regenerate_barcode)
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def update_accessory(e):
            name = name_field.value
            if not name:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            
            # Get quantity value safely
            quantity_value = 0
            try:
                quantity_value = int(quantity_field.value) if quantity_field.value else 0
            except ValueError:
                quantity_value = 0
            
            # Save uploaded image if exists
            saved_image_path = save_uploaded_image() if selected_temp_image else current_image
            
            # Delete old image if replaced
            if selected_temp_image and current_image and os.path.exists(current_image) and current_image != saved_image_path:
                try:
                    os.remove(current_image)
                except:
                    pass
            
            data = {
                'name': name,
                'quantity': quantity_value,
                'quality': quality_field.value,
                'location': location_field.value,
                'image_path': saved_image_path,
                'notes': notes_field.value,
                'barcode_value': barcode_field.value,  # Now barcode_field is defined
            }
            
            print(f"Updating accessory {accessory_id} with data: {data}")
            
            result = AccessoryManager.update(accessory_id, data, self.current_user['id'] if self.current_user else None)
            
            if result:
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Updated accessory: {name}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_accessories(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error updating accessory!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
        
        form_column = ft.Column([
            name_field,
            barcode_field,
            ft.Row([regenerate_btn], alignment=ft.MainAxisAlignment.START),
            quantity_field,
            quality_field,
            location_field,
            upload_btn,
            image_preview,
            notes_field,
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=550)
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("✏️ Edit Accessory", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        form_column,
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Update Accessory", on_click=update_accessory, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=500,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()

    def open_delete_accessory_modal(self, page: ft.Page, accessory_id):
        """Open modal for delete confirmation"""
        accessory = AccessoryManager.get_by_id(accessory_id)
        if not accessory:
            return
        
        accessory_dict = dict(accessory)
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            AccessoryManager.delete(accessory_id)
            page.overlay.clear()
            page.snack_bar = ft.SnackBar(ft.Text(f"Deleted: {accessory_dict.get('name', 'item')}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_accessories(page)
            page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Text(f"Delete accessory '{accessory_dict.get('name', 'item')}'?"),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor="red", color=self.text_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=15),
                    padding=20,
                    width=350,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
    
    # ==================== BARCODE SCANNER ====================
    class BarcodeScanner:
        def __init__(self):
            self.cap = None
            self.is_scanning = False
            
            # Try to import OpenCV, but handle gracefully
            self.CV2_AVAILABLE = False
            self.cv2 = None
            self.np = None
            self.pyzbar = None
            
            try:
                import cv2
                import numpy as np
                from pyzbar import pyzbar
                self.cv2 = cv2
                self.np = np
                self.pyzbar = pyzbar
                self.CV2_AVAILABLE = True
                print("✅ Barcode scanner: Camera available")
            except ImportError:
                print("⚠️ Barcode scanner: Camera not available - using manual entry only")
        
        def scan_from_camera(self):
            """Scan barcode using webcam (returns None if camera not available)"""
            if not self.CV2_AVAILABLE:
                print("Camera not available")
                return None
            
            try:
                self.cap = self.cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    return None
                
                barcode_data = None
                
                while True:
                    ret, frame = self.cap.read()
                    if not ret:
                        break
                        
                    # Decode barcodes
                    barcodes = self.pyzbar.decode(frame)
                    
                    for barcode in barcodes:
                        barcode_data = barcode.data.decode('utf-8')
                        # Draw rectangle around barcode
                        (x, y, w, h) = barcode.rect
                        self.cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        self.cv2.putText(frame, barcode_data, (x, y - 10), 
                                self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
                        if barcode_data:
                            self.cap.release()
                            self.cv2.destroyAllWindows()
                            return barcode_data
                    
                    # Show frame
                    self.cv2.imshow('Barcode Scanner - Press Q to quit', frame)
                    
                    if self.cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                self.cap.release()
                self.cv2.destroyAllWindows()
                return None
            except Exception as e:
                print(f"Camera error: {e}")
                return None
        
        def scan_from_image_file(self, image_path):
            """Scan barcode from image file"""
            if not self.CV2_AVAILABLE:
                return None
            
            try:
                from PIL import Image
                # Try with OpenCV first
                image = self.cv2.imread(image_path)
                if image is not None:
                    barcodes = self.pyzbar.decode(image)
                    if barcodes:
                        return barcodes[0].data.decode('utf-8')
                
                # Fallback to PIL
                image = Image.open(image_path)
                barcodes = self.pyzbar.decode(image)
                if barcodes:
                    return barcodes[0].data.decode('utf-8')
                return None
            except Exception as e:
                print(f"Error scanning image: {e}")
                return None
        
        def process_barcode_scan(self, e, page: ft.Page):
            """Process scanned barcode"""
            barcode = e.control.value.strip()
            if not barcode:
                return
            
            # Search in materials
            material = MaterialManager.get_by_barcode(barcode)
            accessory = None
            
            if not material:
                accessory = AccessoryManager.get_by_barcode(barcode)
            
            if material:
                material_dict = dict(material)
                self.barcode_result_container.content = ft.Column([
                    ft.Text("Scan Results", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([ft.Text("📦 Type:", size=12, color="#CCCCCC"), ft.Text("Material", size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("📝 Name:", size=12, color="#CCCCCC"), ft.Text(material_dict.get('name', 'N/A'), size=12)]),
                    ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC"), 
                            ft.Container(content=ft.Text(material_dict.get('quality', 'Used'), size=12, color="white"),
                                        bgcolor=self.get_quality_color(material_dict.get('quality', 'Used')),
                                        border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))]),
                    ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC"), ft.Text(str(material_dict.get('quantity', 0)), size=12)]),
                    ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC"), ft.Text(material_dict.get('location_ids') or "N/A", size=12)]),
                    ft.Divider(),
                    ft.Row([
                        ft.FilledButton("View Details", on_click=lambda e: self.view_material_from_barcode(material_dict['id'])),
                        ft.FilledButton("Update Stock", style=ft.ButtonStyle(bgcolor=self.warning_color)),
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=10)
            elif accessory:
                accessory_dict = dict(accessory)
                location = accessory_dict.get('location') or accessory_dict.get('location_ids') or "N/A"
                self.barcode_result_container.content = ft.Column([
                    ft.Text("Scan Results", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([ft.Text("🔧 Type:", size=12, color="#CCCCCC"), ft.Text("Accessory", size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("📝 Name:", size=12, color="#CCCCCC"), ft.Text(accessory_dict.get('name', 'N/A'), size=12)]),
                    ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC"), 
                            ft.Container(content=ft.Text(accessory_dict.get('quality', 'Used'), size=12, color="white"),
                                        bgcolor=self.get_quality_color(accessory_dict.get('quality', 'Used')),
                                        border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))]),
                    ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC"), ft.Text(str(accessory_dict.get('quantity', 0)), size=12)]),
                    ft.Row([ft.Text("💰 Price:", size=12, color="#CCCCCC"), ft.Text(f"${accessory_dict.get('price', 0):.2f}" if accessory_dict.get('price') else "N/A", size=12)]),
                    ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC"), ft.Text(location, size=12)]),
                    ft.Divider(),
                    ft.Row([
                        ft.FilledButton("View Details", on_click=lambda e: self.view_accessory_from_barcode(accessory_dict['id'])),
                        ft.FilledButton("Update Stock", style=ft.ButtonStyle(bgcolor=self.warning_color)),
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=10)
            else:
                self.barcode_result_container.content = ft.Column([
                    ft.Text("Scan Results", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("❌ No item found with this barcode!", size=14, color=self.danger_color),
                    ft.Text(f"Barcode: {barcode}", size=12, color="#888888"),
                    ft.Container(height=10),
                    ft.FilledButton("Add New Item", on_click=lambda e: self.show_add_from_barcode(page, barcode)),
                ], spacing=10)
            
            e.control.value = ""
            page.update()
        
        def view_material_from_barcode(self, material_id):
            """Navigate to material details from barcode scan"""
            material = MaterialManager.get_by_id(material_id)
            if material:
                self.selected_material_detail = dict(material)
                self.show_materials_screen(self.barcode_page)
        
        def view_accessory_from_barcode(self, accessory_id):
            """Navigate to accessory details from barcode scan"""
            accessory = AccessoryManager.get_by_id(accessory_id)
            if accessory:
                self.selected_accessory_detail = dict(accessory)
                self.show_accessories(self.barcode_page)
        
        def show_add_from_barcode(self, page: ft.Page, barcode):
            """Show add item dialog with pre-filled barcode"""
            def close_modal(e):
                page.overlay.clear()
                page.update()
            
            def add_material(e):
                name = name_field.value
                if not name:
                    return
                
                data = {
                    'name': name,
                    'item_code': barcode,
                    'barcode_value': barcode,
                    'quantity': int(quantity_field.value) if quantity_field.value.isdigit() else 0,
                    'quality': quality_field.value,
                    'location_ids': location_field.value,
                    'notes': notes_field.value,
                }
                
                result = MaterialManager.create(data)
                if result:
                    page.overlay.clear()
                    page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added new material: {name}"), bgcolor=self.success_color)
                    page.snack_bar.open = True
                    self.show_materials_screen(page)
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("Error creating item!"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()
            
            name_field = ft.TextField(label="Name *", width=380, bgcolor=self.card_color)
            quantity_field = ft.TextField(label="Quantity", width=380, bgcolor=self.card_color, value="0")
            quality_field = ft.Dropdown(
                label="Quality", width=380,
                options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), 
                        ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
                value="New", bgcolor=self.card_color,
            )
            location_field = ft.TextField(label="Location", width=380, bgcolor=self.card_color)
            notes_field = ft.TextField(label="Notes", width=380, bgcolor=self.card_color, multiline=True, min_lines=3)
            
            modal = ft.Container(
                content=ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("Add New Item from Barcode", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Barcode: {barcode}", size=12, color="#888888"),
                            ft.Divider(),
                            ft.Column([name_field, quantity_field, quality_field, location_field, notes_field], spacing=12),
                            ft.Divider(),
                            ft.Row([
                                ft.TextButton("Cancel", on_click=close_modal),
                                ft.FilledButton("Add Material", on_click=add_material, style=ft.ButtonStyle(bgcolor=self.success_color)),
                                ft.FilledButton("Add Accessory", on_click=lambda e: self.add_accessory_from_barcode(page, barcode, close_modal),
                                            style=ft.ButtonStyle(bgcolor=self.accent_color)),
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
        
        def add_accessory_from_barcode(self, page: ft.Page, barcode, close_modal_func):
            """Add accessory from barcode scan"""
            name_field = ft.TextField(label="Name *", width=380, bgcolor=self.card_color)
            quantity_field = ft.TextField(label="Quantity", width=380, bgcolor=self.card_color, value="0")
            price_field = ft.TextField(label="Price", width=380, bgcolor=self.card_color, value="0.00")
            quality_field = ft.Dropdown(
                label="Quality", width=380,
                options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"), 
                        ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
                value="New", bgcolor=self.card_color,
            )
            location_field = ft.TextField(label="Location", width=380, bgcolor=self.card_color)
            notes_field = ft.TextField(label="Notes", width=380, bgcolor=self.card_color, multiline=True, min_lines=3)
            
            def save_accessory(e):
                name = name_field.value
                if not name:
                    return
                
                data = {
                    'name': name,
                    'item_code': barcode,
                    'barcode_value': barcode,
                    'quantity': int(quantity_field.value) if quantity_field.value.isdigit() else 0,
                    'price': float(price_field.value) if price_field.value else 0.0,
                    'quality': quality_field.value,
                    'location': location_field.value,
                    'notes': notes_field.value,
                }
                
                result = AccessoryManager.create(data)
                if result:
                    page.overlay.clear()
                    page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added new accessory: {name}"), bgcolor=self.success_color)
                    page.snack_bar.open = True
                    self.show_accessories(page)
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("Error creating accessory!"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()
            
            # Replace modal content
            page.overlay[-1].content.content.content = ft.Column([
                ft.Text("Add Accessory from Barcode", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"Barcode: {barcode}", size=12, color="#888888"),
                ft.Divider(),
                ft.Column([name_field, quantity_field, price_field, quality_field, location_field, notes_field], spacing=12),
                ft.Divider(),
                ft.Row([
                    ft.TextButton("Cancel", on_click=lambda e: page.overlay.clear()),
                    ft.FilledButton("Save Accessory", on_click=save_accessory, style=ft.ButtonStyle(bgcolor=self.success_color)),
                ], alignment=ft.MainAxisAlignment.END, spacing=10),
            ], spacing=10)
            page.update()
        
        def is_camera_available(self):
            """Check if camera functionality is available"""
            return self.CV2_AVAILABLE
    
    def _create_stat_card(self, title, value, subtitle, color):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=14, color="#CCCCCC"),
                ft.Text(value, size=36, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Text(subtitle, size=10, color="#888888", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=20,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )


    def _create_info_box(self, title, count, stock, color):
        """Create an info box"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Row([
                    ft.Column([
                        ft.Text("Items", size=11, color="#888888"),
                        ft.Text(count, size=24, weight=ft.FontWeight.BOLD, color=color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(width=20),
                    ft.Column([
                        ft.Text("Stock", size=11, color="#888888"),
                        ft.Text(str(stock), size=24, weight=ft.FontWeight.BOLD, color=color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=15,
            bgcolor="#2C2C2C",
            border_radius=10,
            expand=True,
        )


    def _create_low_stock_list(self, low_materials, low_accessories, page):
        """Create low stock items list"""
        if not low_materials and not low_accessories:
            return ft.Container(
                content=ft.Text("✅ No low stock items!", size=12, color=self.success_color),
                padding=20,
                alignment=ft.alignment.center,
            )
        
        items = ft.Column(spacing=5)
        
        for m in low_materials[:15]:
            items.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text("📦", size=16, width=35),
                        ft.Text(m.get('name', 'N/A'), size=12, width=180),
                        ft.Text(f"Stock: {m.get('quantity') or 0}", size=12, color=self.danger_color, width=100),
                        ft.Text(m.get('location_ids') or "N/A", size=11, width=150),
                        ft.ElevatedButton("View", height=30, on_click=lambda e, mat=m: self.view_inventory_item(page, mat, 'material')),
                    ]),
                    padding=8,
                    bgcolor="#3C3C3C",
                    border_radius=6,
                )
            )
        
        for a in low_accessories[:15]:
            location = a.get('location') or a.get('location_ids') or 'N/A'
            items.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text("🔧", size=16, width=35),
                        ft.Text(a.get('name', 'N/A'), size=12, width=180),
                        ft.Text(f"Stock: {a.get('quantity') or 0}", size=12, color=self.danger_color, width=100),
                        ft.Text(location, size=11, width=150),
                        ft.ElevatedButton("View", height=30, on_click=lambda e, acc=a: self.view_inventory_item(page, acc, 'accessory')),
                    ]),
                    padding=8,
                    bgcolor="#3C3C3C",
                    border_radius=6,
                )
            )
        
        return items


    def _create_inventory_table(self, inventory_items):
        """Create a simple inventory table"""
        if not inventory_items:
            return ft.Container(
                content=ft.Text("No inventory items found.", size=12, color="#888888"),
                padding=20,
                alignment=ft.alignment.center,
            )
        
        # Header
        header = ft.Container(
            content=ft.Row([
                ft.Text("Type", size=11, weight=ft.FontWeight.BOLD, width=70),
                ft.Text("Name", size=11, weight=ft.FontWeight.BOLD, width=180),
                ft.Text("Code", size=11, weight=ft.FontWeight.BOLD, width=120),
                ft.Text("Qty", size=11, weight=ft.FontWeight.BOLD, width=50),
                ft.Text("Quality", size=11, weight=ft.FontWeight.BOLD, width=80),
                ft.Text("Location", size=11, weight=ft.FontWeight.BOLD, width=140),
            ]),
            padding=25,
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # Rows
        rows = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
        
        for i, item in enumerate(inventory_items[:100]):
            quality_color = self.get_quality_color(item['quality'])
            rows.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(item['type'][:9], size=12),
                            bgcolor=self.accent_color if item['type'] == 'Material' else self.warning_color,
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            width=60,
                        ),
                        ft.Text(item['name'], size=10, width=180),
                        ft.Text(item['item_code'], size=9, width=120),
                        ft.Text(str(item['quantity']), size=10, width=50),
                        ft.Container(
                            content=ft.Text(item['quality'], size=9, color="white"),
                            bgcolor=quality_color,
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            width=75,
                        ),
                        ft.Text(item['location'], size=9, width=140),
                    ]),
                    padding=6,
                    bgcolor="#3C3C3C" if i % 2 == 0 else ft.Colors.TRANSPARENT,
                    border_radius=4,
                )
            )
        
        return ft.Column([header, rows], spacing=5)


    def _export_inventory_csv(self, inventory_items, page):
        """Export inventory to CSV"""
        try:
            import csv
            from datetime import datetime
            filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Type', 'Name', 'Item Code', 'Quantity', 'Quality', 'Location'])
                for item in inventory_items:
                    writer.writerow([item['type'], item['name'], item['item_code'], item['quantity'], item['quality'], item['location']])
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Exported: {filename}"), bgcolor=self.success_color)
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()

    def export_inventory_pdf(self, inventory_items, page):
        """Export inventory to PDF with professional formatting"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import landscape, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from reportlab.lib.units import inch, mm
            from datetime import datetime
            
            filename = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Create PDF document
            doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                                    rightMargin=20, leftMargin=20, 
                                    topMargin=30, bottomMargin=20)
            
            styles = getSampleStyleSheet()
            story = []
            
            # Title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1976D2'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            # Header style
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#2E7D32'),
                spaceAfter=10
            )
            
            # Normal style
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=6
            )
            
            # Title
            story.append(Paragraph("Store Management System", title_style))
            story.append(Paragraph(f"Inventory Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            story.append(Spacer(1, 20))
            
            # Summary section
            story.append(Paragraph("Summary Statistics", header_style))
            
            # Calculate totals
            total_items = len(inventory_items)
            total_materials = sum(1 for i in inventory_items if i['type'] == 'Material')
            total_accessories = sum(1 for i in inventory_items if i['type'] == 'Accessory')
            total_quantity = sum(i['quantity'] for i in inventory_items)
            low_stock_count = sum(1 for i in inventory_items if i['quantity'] < 10)
            
            summary_data = [
                ['Total Items', str(total_items)],
                ['Materials', str(total_materials)],
                ['Accessories', str(total_accessories)],
                ['Total Stock', str(total_quantity)],
                ['Low Stock Items', str(low_stock_count)],
            ]
            
            summary_table = Table(summary_data, colWidths=[120, 80])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Inventory table
            story.append(Paragraph("Inventory List", header_style))
            
            # Prepare table data
            table_data = [['#', 'Type', 'Name', 'Item Code', 'Quantity', 'Quality', 'Location']]
            
            for i, item in enumerate(inventory_items[:200], 1):
                table_data.append([
                    str(i),
                    item['type'][:8],
                    item['name'][:40],
                    item['item_code'][:15],
                    str(item['quantity']),
                    item['quality'],
                    item['location'][:30],
                ])
            
            # Create table
            table = Table(table_data, colWidths=[30, 50, 120, 80, 45, 60, 100])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3C3C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
            
            # Footer
            story.append(Paragraph(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            story.append(Paragraph("Store Management System - All Rights Reserved", normal_style))
            
            # Build PDF
            doc.build(story)
            
            # Show success message
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ PDF exported: {filename}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except ImportError:
            page.snack_bar = ft.SnackBar(
                ft.Text("Please install reportlab: pip install reportlab"),
                bgcolor=self.danger_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(ex)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()


    def export_low_stock_pdf(self, low_stock_items, page):
        """Export low stock items to PDF"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            from datetime import datetime
            
            filename = f"low_stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            doc = SimpleDocTemplate(filename, pagesize=A4, 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=30, bottomMargin=20)
            
            styles = getSampleStyleSheet()
            story = []
            
            # Title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#F44336'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10)
            
            story.append(Paragraph("Store Management System", title_style))
            story.append(Paragraph("Low Stock Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            story.append(Spacer(1, 20))
            
            # Prepare table data
            table_data = [['#', 'Name', 'Item Code', 'Current Stock', 'Quality', 'Location']]
            
            for i, item in enumerate(low_stock_items, 1):
                table_data.append([
                    str(i),
                    item['name'][:35],
                    item['item_code'][:15],
                    str(item['quantity']),
                    item['quality'],
                    item['location'][:25],
                ])
            
            table = Table(table_data, colWidths=[30, 130, 80, 50, 60, 100])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F44336')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ]))
            
            story.append(table)
            doc.build(story)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Low stock PDF exported: {filename}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except ImportError:
            page.snack_bar = ft.SnackBar(
                ft.Text("Please install reportlab: pip install reportlab"),
                bgcolor=self.danger_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {str(ex)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def view_inventory_item(self, page: ft.Page, item, item_type):
        """View inventory item details"""
        if item_type == 'material':
            self.selected_material_detail = item
            self.show_materials_screen(page)
        else:
            self.selected_accessory_detail = item
            self.show_accessories(page)

    def _export_inventory_csv(self, inventory_items, page):
        """Export inventory to CSV"""
        try:
            import csv
            from datetime import datetime
            filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Type', 'Name', 'Item Code', 'Quantity', 'Quality', 'Location'])
                for item in inventory_items:
                    writer.writerow([item['type'], item['name'], item['item_code'], item['quantity'], item['quality'], item['location']])
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Exported: {filename}"), bgcolor=self.success_color)
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()

    def show_inventory(self, page: ft.Page):
        """Show inventory management screen - Single column stacked layout (guaranteed to show all)"""
        page.controls.clear()
        
        sidebar = self.create_sidebar(page)
        
        # Get inventory items
        try:
            materials = MaterialManager.get_all()
            accessories = AccessoryManager.get_all()
        except:
            materials = []
            accessories = []
        
        if materials is None:
            materials = []
        if accessories is None:
            accessories = []
        
        # Create inventory items list
        inventory_items = []
        for m in materials:
            inventory_items.append({
                'type': 'Material',
                'id': m.get('id'),
                'name': m.get('name', 'N/A'),
                'item_code': m.get('item_code', 'N/A'),
                'quantity': m.get('quantity') or 0,
                'quality': m.get('quality', 'Used'),
                'location': m.get('location_ids', 'N/A'),
            })
        
        for a in accessories:
            location = a.get('location') or a.get('location_ids') or 'N/A'
            inventory_items.append({
                'type': 'Accessory',
                'id': a.get('id'),
                'name': a.get('name', 'N/A'),
                'item_code': a.get('item_code', 'N/A'),
                'quantity': a.get('quantity') or 0,
                'quality': a.get('quality', 'Used'),
                'location': location,
            })
        
        inventory_items.sort(key=lambda x: x['name'])
        
        # Calculate statistics
        total_materials = len(materials)
        total_accessories = len(accessories)
        total_items = total_materials + total_accessories
        
        total_material_stock = sum(m.get('quantity') or 0 for m in materials)
        total_accessory_stock = sum(a.get('quantity') or 0 for a in accessories)
        total_stock = total_material_stock + total_accessory_stock
        
        # Low stock
        low_materials = [m for m in materials if (m.get('quantity') or 0) < 10]
        low_accessories = [a for a in accessories if (a.get('quantity') or 0) < 10]
        low_count = len(low_materials) + len(low_accessories)
        
        # Quality breakdown
        quality_stats = {
            'New': {'count': 0, 'stock': 0, 'color': '#4CAF50'},
            'Used': {'count': 0, 'stock': 0, 'color': '#FF9800'},
            'Damaged': {'count': 0, 'stock': 0, 'color': '#F44336'},
            'Repaired': {'count': 0, 'stock': 0, 'color': '#2196F3'},
        }
        
        for m in materials:
            q = m.get('quality', 'Used')
            if q in quality_stats:
                quality_stats[q]['count'] += 1
                quality_stats[q]['stock'] += m.get('quantity') or 0
        
        for a in accessories:
            q = a.get('quality', 'Used')
            if q in quality_stats:
                quality_stats[q]['count'] += 1
                quality_stats[q]['stock'] += a.get('quantity') or 0
        
        max_count = max([s['count'] for s in quality_stats.values()]) or 1
        
        # Variable for filtered items
        current_filtered_items = inventory_items.copy()
        
        # ========== CREATE TABLE ROWS CONTAINER ==========
        table_rows = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=350)
        
        # ========== FILTER COMPONENTS ==========
        type_filter = ft.Dropdown(
            label="Item Type",
            width=150,
            options=[
                ft.dropdown.Option("All", "📦 All Types"),
                ft.dropdown.Option("Material", "📦 Materials Only"),
                ft.dropdown.Option("Accessory", "🔧 Accessories Only"),
            ],
            value="All",
            bgcolor=self.card_color,
            border_color=self.accent_color,
        )
        
        quality_filter = ft.Dropdown(
            label="Quality",
            width=150,
            options=[
                ft.dropdown.Option("All", "🎯 All Qualities"),
                ft.dropdown.Option("New", "🟢 New"),
                ft.dropdown.Option("Used", "🟠 Used"),
                ft.dropdown.Option("Damaged", "🔴 Damaged"),
                ft.dropdown.Option("Repaired", "🔵 Repaired"),
            ],
            value="All",
            bgcolor=self.card_color,
            border_color=self.accent_color,
        )
        
        filter_count_text = ft.Text("", size=11, color="#888888")
        
        # ========== FUNCTION TO UPDATE TABLE ==========
        def update_inventory_table(items):
            nonlocal current_filtered_items
            current_filtered_items = items
            table_rows.controls.clear()
            
            if not items:
                table_rows.controls.append(
                    ft.Container(
                        content=ft.Text("No items found.", size=12, color="#888888"),
                        padding=20,
                        alignment=ft.alignment.center,
                    )
                )
                return
            
            for i, item in enumerate(items[:100]):
                quality_color = self.get_quality_color(item['quality'])
                row_color = "#2C2C2C" if i % 2 == 0 else ft.Colors.TRANSPARENT
                
                table_rows.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Row([
                                    ft.Text("📦" if item['type'] == 'Material' else "🔧", size=12),
                                    ft.Text(item['type'][:4], size=10, weight=ft.FontWeight.BOLD),
                                ], spacing=4),
                                bgcolor=self.accent_color if item['type'] == 'Material' else self.warning_color,
                                border_radius=12,
                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                width=90,
                            ),
                            ft.Container(
                                ft.Text(item['name'], size=11, weight=ft.FontWeight.BOLD),
                                expand=True,
                            ),
                            ft.Container(
                                ft.Text(item['item_code'], size=10),
                                width=110,
                            ),
                            ft.Container(
                                ft.Text(str(item['quantity']), size=11, weight=ft.FontWeight.BOLD if item['quantity'] < 10 else None),
                                width=60,
                                alignment=ft.alignment.center,
                            ),
                            ft.Container(
                                content=ft.Text(item['quality'], size=10, color="white", text_align=ft.TextAlign.CENTER),
                                bgcolor=quality_color,
                                border_radius=12,
                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                width=90,
                            ),
                            ft.Container(
                                ft.Text(item['location'], size=10),
                                width=140,
                            ),
                        ], spacing=10, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.symmetric(vertical=10, horizontal=15),
                        bgcolor=row_color,
                        border_radius=8,
                    )
                )
            
            page.update()
        
        # ========== FUNCTION TO APPLY FILTERS ==========
        def apply_filters(e=None):
            selected_type = type_filter.value
            selected_quality = quality_filter.value
            
            filtered = inventory_items.copy()
            
            if selected_type != "All":
                filtered = [item for item in filtered if item['type'] == selected_type]
            
            if selected_quality != "All":
                filtered = [item for item in filtered if item['quality'] == selected_quality]
            
            filter_count_text.value = f"Showing {len(filtered)} of {len(inventory_items)} items"
            filter_count_text.color = self.accent_color if len(filtered) != len(inventory_items) else "#888888"
            
            update_inventory_table(filtered)
            page.update()
        
        def reset_filters(e):
            type_filter.value = "All"
            quality_filter.value = "All"
            apply_filters()
            page.update()
        
        type_filter.on_change = apply_filters
        quality_filter.on_change = apply_filters
        
        # Initialize table
        update_inventory_table(inventory_items)
        
        # ========== STATS CARDS (Row of 3) ==========
        def create_stat_card(title, value, subtitle, icon, color):
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(icon, size=28),
                        bgcolor=color,
                        border_radius=10,
                        padding=10,
                    ),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(title, size=11, color="#888888"),
                        ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text(subtitle, size=9, color="#888888"),
                    ], spacing=2),
                ]),
                padding=12,
                bgcolor="#1E1E1E",
                border_radius=10,
                expand=True,
            )
        
        stats_row = ft.Row([
            create_stat_card("Total Items", str(total_items), f"{total_materials} Mat, {total_accessories} Acc", "📦", self.accent_color),
            create_stat_card("Total Stock", str(total_stock), f"{total_material_stock} Mat, {total_accessory_stock} Acc", "📊", self.success_color),
            create_stat_card("Low Stock", str(low_count), f"{len(low_materials)} Mat, {len(low_accessories)} Acc", "⚠️", self.danger_color),
        ], spacing=15)
        
        # ========== QUALITY SECTION (Horizontal scroll) ==========
        quality_cards = ft.Row(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("🟢", size=24),
                        ft.Text("New", size=12, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                        ft.Text(f"{quality_stats['New']['count']} items", size=11, color="#888888"),
                        ft.ProgressBar(value=quality_stats['New']['count']/max_count, color="#4CAF50", bgcolor="#3C3C3C", height=4, width=80),
                        ft.Text(f"Stock: {quality_stats['New']['stock']}", size=10, color="#888888"),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12,
                    bgcolor="#2C2C2C",
                    border_radius=10,
                    width=100,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🟠", size=24),
                        ft.Text("Used", size=12, weight=ft.FontWeight.BOLD, color="#FF9800"),
                        ft.Text(f"{quality_stats['Used']['count']} items", size=11, color="#888888"),
                        ft.ProgressBar(value=quality_stats['Used']['count']/max_count, color="#FF9800", bgcolor="#3C3C3C", height=4, width=80),
                        ft.Text(f"Stock: {quality_stats['Used']['stock']}", size=10, color="#888888"),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12,
                    bgcolor="#2C2C2C",
                    border_radius=10,
                    width=100,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🔴", size=24),
                        ft.Text("Damaged", size=12, weight=ft.FontWeight.BOLD, color="#F44336"),
                        ft.Text(f"{quality_stats['Damaged']['count']} items", size=11, color="#888888"),
                        ft.ProgressBar(value=quality_stats['Damaged']['count']/max_count, color="#F44336", bgcolor="#3C3C3C", height=4, width=80),
                        ft.Text(f"Stock: {quality_stats['Damaged']['stock']}", size=10, color="#888888"),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12,
                    bgcolor="#2C2C2C",
                    border_radius=10,
                    width=100,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🔵", size=24),
                        ft.Text("Repaired", size=12, weight=ft.FontWeight.BOLD, color="#2196F3"),
                        ft.Text(f"{quality_stats['Repaired']['count']} items", size=11, color="#888888"),
                        ft.ProgressBar(value=quality_stats['Repaired']['count']/max_count, color="#2196F3", bgcolor="#3C3C3C", height=4, width=80),
                        ft.Text(f"Stock: {quality_stats['Repaired']['stock']}", size=10, color="#888888"),
                    ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12,
                    bgcolor="#2C2C2C",
                    border_radius=10,
                    width=100,
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )
        
        quality_section = ft.Container(
            content=ft.Column([
                ft.Text("📊 Quality Distribution", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=5),
                quality_cards,
            ], spacing=5),
            padding=12,
            bgcolor="#1E1E1E",
            border_radius=10,
        )
        
        # ========== SUMMARY CARDS (Row of 3) ==========
        summary_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("📦", size=20),
                    ft.Text("MATERIALS", size=10, color="#888888"),
                    ft.Text(str(total_materials), size=22, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Text(f"Stock: {total_material_stock}", size=10, color="#888888"),
                    ft.Text(f"Low: {len(low_materials)}", size=10, color=self.danger_color if len(low_materials) > 0 else "#888888"),
                ], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12,
                bgcolor="#2C2C2C",
                border_radius=10,
                expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("🔧", size=20),
                    ft.Text("ACCESSORIES", size=10, color="#888888"),
                    ft.Text(str(total_accessories), size=22, weight=ft.FontWeight.BOLD, color=self.warning_color),
                    ft.Text(f"Stock: {total_accessory_stock}", size=10, color="#888888"),
                    ft.Text(f"Low: {len(low_accessories)}", size=10, color=self.danger_color if len(low_accessories) > 0 else "#888888"),
                ], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12,
                bgcolor="#2C2C2C",
                border_radius=10,
                expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊", size=20),
                    ft.Text("TOTALS", size=10, color="#888888"),
                    ft.Text(str(total_items), size=22, weight=ft.FontWeight.BOLD, color=self.success_color),
                    ft.Text(f"Stock: {total_stock}", size=10, color="#888888"),
                    ft.Text(f"Low: {low_count}", size=10, color=self.danger_color if low_count > 0 else "#888888"),
                ], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=12,
                bgcolor="#2C2C2C",
                border_radius=10,
                expand=True,
            ),
        ], spacing=15)
        
        summary_section = ft.Container(
            content=ft.Column([
                ft.Text("📋 Summary", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=5),
                summary_row,
            ], spacing=5),
            padding=12,
            bgcolor="#1E1E1E",
            border_radius=10,
        )
        
        # ========== LOW STOCK ALERTS ==========
        low_stock_list = ft.Column(spacing=5)
        
        if low_materials or low_accessories:
            for m in low_materials[:10]:
                low_stock_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("📦", size=16, width=35),
                            ft.Text(m.get('name', 'N/A'), size=12, width=180),
                            ft.Text(f"Stock: {m.get('quantity') or 0}", size=12, color=self.danger_color, width=90),
                            ft.Text(m.get('location_ids') or "N/A", size=11, width=150),
                            ft.Container(expand=True),
                            ft.OutlinedButton("View", height=30, on_click=lambda e, mat=m: self.view_inventory_item(page, mat, 'material')),
                        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.symmetric(vertical=6, horizontal=10),
                        bgcolor="#2C2C2C",
                        border_radius=8,
                    )
                )
            
            for a in low_accessories[:10]:
                location = a.get('location') or a.get('location_ids') or 'N/A'
                low_stock_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🔧", size=16, width=35),
                            ft.Text(a.get('name', 'N/A'), size=12, width=180),
                            ft.Text(f"Stock: {a.get('quantity') or 0}", size=12, color=self.danger_color, width=90),
                            ft.Text(location, size=11, width=150),
                            ft.Container(expand=True),
                            ft.OutlinedButton("View", height=30, on_click=lambda e, acc=a: self.view_inventory_item(page, acc, 'accessory')),
                        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.symmetric(vertical=6, horizontal=10),
                        bgcolor="#2C2C2C",
                        border_radius=8,
                    )
                )
        else:
            low_stock_list.controls.append(
                ft.Container(
                    content=ft.Text("✅ No low stock items! All inventory levels are healthy.", size=12, color=self.success_color),
                    padding=15,
                    alignment=ft.alignment.center,
                )
            )
        
        low_stock_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("⚠️ Low Stock Alerts", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.Text(f"Total: {low_count}", size=11, color=self.danger_color),
                ]),
                ft.Divider(height=1, color="#3C3C3C"),
                ft.Container(height=5),
                low_stock_list,
            ], spacing=5),
            padding=12,
            bgcolor="#1E1E1E",
            border_radius=10,
        )
        
        # ========== TABLE HEADER ==========
        table_header = ft.Container(
            content=ft.Row([
                ft.Text("Type", size=10, weight=ft.FontWeight.BOLD, width=90),
                ft.Text("Name", size=10, weight=ft.FontWeight.BOLD, expand=True),
                ft.Text("Code", size=10, weight=ft.FontWeight.BOLD, width=100),
                ft.Text("Qty", size=10, weight=ft.FontWeight.BOLD, width=55),
                ft.Text("Quality", size=10, weight=ft.FontWeight.BOLD, width=85),
                ft.Text("Location", size=10, weight=ft.FontWeight.BOLD, width=130),
            ], spacing=10),
            padding=ft.padding.symmetric(vertical=10, horizontal=12),
            bgcolor="#3C3C3C",
            border_radius=8,
        )
        
        # ========== FILTER BAR ==========
        filter_bar = ft.Container(
            content=ft.Row([
                ft.Row([type_filter, quality_filter], spacing=10),
                ft.Row([
                    ft.OutlinedButton("Reset", on_click=reset_filters, style=ft.ButtonStyle(color=self.warning_color), height=35),
                    filter_count_text,
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(vertical=6, horizontal=12),
            bgcolor="#2C2C2C",
            border_radius=8,
        )
        
        # ========== INVENTORY TABLE SECTION ==========
        inventory_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📋 Inventory Items", size=14, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.Text(f"Total: {len(inventory_items)}", size=11, color="#888888"),
                ]),
                ft.Divider(height=1, color="#3C3C3C"),
                ft.Container(height=5),
                filter_bar,
                ft.Container(height=5),
                table_header,
                table_rows,
            ], spacing=5),
            padding=12,
            bgcolor="#1E1E1E",
            border_radius=10,
        )
        
        # ========== EXPORT BUTTONS ==========
        def export_csv(e):
            try:
                import csv
                from datetime import datetime
                filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(filename, 'w', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Type', 'Name', 'Item Code', 'Quantity', 'Quality', 'Location'])
                    for item in current_filtered_items:
                        writer.writerow([item['type'], item['name'], item['item_code'], item['quantity'], item['quality'], item['location']])
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Exported: {filename}"), bgcolor=self.success_color, duration=3000)
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(ex)}"), bgcolor=self.danger_color, duration=3000)
                page.snack_bar.open = True
                page.update()
        


        def export_pdf(e):
            self.export_inventory_pdf(current_filtered_items, page)
        
        def export_low_stock_pdf(e):
            # Get low stock items from current filtered list
            low_stock_items = [item for item in current_filtered_items if item['quantity'] < 10]
            if low_stock_items:
                self.export_low_stock_pdf(low_stock_items, page)
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("No low stock items to export"),
                    bgcolor=self.warning_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
        
        def refresh_inventory(e):
            self.show_inventory(page)
        
        button_row = ft.Row([
            ft.ElevatedButton("📊 Export CSV", on_click=export_csv, style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ft.ElevatedButton("📄 Export PDF", on_click=export_pdf, style=ft.ButtonStyle(bgcolor=self.warning_color)),
            ft.ElevatedButton("⚠️ Low Stock PDF", on_click=export_low_stock_pdf, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ft.ElevatedButton("🔄 Refresh", on_click=refresh_inventory, style=ft.ButtonStyle(bgcolor=self.success_color)),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
        
        # ========== MAIN CONTENT (SINGLE COLUMN STACKED) ==========
        main_content = ft.Column([
            ft.Text("Inventory Management", size=26, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(height=10),
            stats_row,
            ft.Container(height=15),
            quality_section,
            ft.Container(height=15),
            summary_section,
            ft.Container(height=15),
            low_stock_section,
            ft.Container(height=15),
            inventory_section,
            ft.Container(height=15),
            button_row,
            ft.Container(height=10),
        ], scroll=ft.ScrollMode.AUTO)
        
        main_content_container = ft.Container(content=main_content, expand=True, padding=20)
        page.add(ft.Row([sidebar, main_content_container], spacing=0, expand=True))
        page.update()
        
    def get_company_info(self):
        """Load company information from config file"""
        import json
        import os
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_dir, "company_config.json")
        
        default_info = {
            'company_name': 'Store Management System',
            'phone': '',
            'email': '',
            'website': '',
            'address': '',
            'city': '',
            'tax_id': ''
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    default_info.update(data)
            except:
                pass
        
        return default_info

    def view_inventory_item(self, page: ft.Page, item, item_type):
        """View inventory item details from alerts"""
        if item_type == 'material':
            self.selected_material_detail = item
            self.show_materials_screen(page)
        else:
            self.selected_accessory_detail = item
            self.show_accessories(page)
    
    def edit_inventory_item(self, page: ft.Page, item):
        """Edit inventory item from inventory screen"""
        if item['type'] == 'Material':
            self.open_edit_modal(page, item['id'])
        else:
            self.open_edit_accessory_modal(page, item['id'])
    
    def delete_inventory_item(self, page: ft.Page, item):
        """Delete inventory item from inventory screen"""
        if item['type'] == 'Material':
            self.open_delete_modal(page, item['id'])
        else:
            self.open_delete_accessory_modal(page, item['id'])
    
    # ==================== USERS MANAGEMENT ====================
    def show_users(self, page: ft.Page):
        """Show users management screen - Table Centered"""
        page.controls.clear()
        
        sidebar = self.create_sidebar(page)
        users = self.dict_list(UserManager.get_all())
        
        current_user_id = self.current_user.get('id') if self.current_user else None
        is_admin = self.current_user.get('role') == 'admin' if self.current_user else False
        
        # Title
        title = ft.Text("👥 Users Management", size=28, weight=ft.FontWeight.BOLD, color=self.text_color)
        
        # Stats row
        total_users = len(users)
        admin_count = len([u for u in users if u.get('role') == 'admin'])
        manager_count = len([u for u in users if u.get('role') == 'manager'])
        user_count = len([u for u in users if u.get('role') == 'user'])
        
        stats_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 Total Users", size=14, color="#CCCCCC"),
                        ft.Text(str(total_users), size=32, weight=ft.FontWeight.BOLD, color=self.text_color)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20, bgcolor=self.accent_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("👑 Administrators", size=14, color="#CCCCCC"),
                        ft.Text(str(admin_count), size=32, weight=ft.FontWeight.BOLD, color=self.text_color)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20, bgcolor=self.danger_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 Managers", size=14, color="#CCCCCC"),
                        ft.Text(str(manager_count), size=32, weight=ft.FontWeight.BOLD, color=self.text_color)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20, bgcolor=self.warning_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("👤 Regular Users", size=14, color="#CCCCCC"),
                        ft.Text(str(user_count), size=32, weight=ft.FontWeight.BOLD, color=self.text_color)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20, bgcolor=self.success_color, border_radius=10, expand=True,
                ),
            ],
            spacing=15,
        )
        
        # Add button and search row
        add_button = ft.FilledButton(
            "➕ Add New User",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
            on_click=lambda e: self.open_add_user_modal(page),
            visible=self.has_permission('add_user'),  # Changed from is_admin
        )
        
        search_field = ft.TextField(
            hint_text="🔍 Search by name or email...",
            width=300,
            bgcolor=self.card_color,
            border_color=self.accent_color,
        )
        
        # Create DataTable for users - WITH FIXED WIDTH FOR CENTERING
        user_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD, size=13), numeric=True),
                ft.DataColumn(ft.Text("Name", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("Role", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("Created", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, size=13)),
            ],
            rows=[],
            heading_row_color="#3C3C3C",
            heading_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            data_row_color="#2C2C2C",
            border=ft.border.all(1, "#3C3C3C"),
            border_radius=10,
            horizontal_lines=ft.border.BorderSide(1, "#3C3C3C"),
            column_spacing=50,
            width=1100,  # Fixed width for centering
        )
        
        def refresh_table(filtered_users):
            user_table.rows.clear()
            for u in filtered_users:
                # Set role color and display
                role = u.get('role', 'user')
                if role == 'admin':
                    role_color = self.danger_color
                    role_display = "👑 ADMIN"
                elif role == 'manager':
                    role_color = self.warning_color
                    role_display = "📊 MANAGER"
                else:
                    role_color = self.success_color
                    role_display = "👤 USER"
                
                # Format date
                created = u.get('created_at', '')
                if created:
                    created = str(created)[:10]
                else:
                    created = 'N/A'
                
                # Check permissions
                can_edit = is_admin or u.get('id') == current_user_id
                can_delete = is_admin and u.get('id') != current_user_id
                
                # Create action buttons
                action_buttons = ft.Row([
                    ft.Container(
                        content=ft.Text("✏️ Edit", size=12, color=self.accent_color),
                        on_click=lambda e, uid=u.get('id'): self.open_edit_user_modal(page, uid),
                        ink=True,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    ),
                ], spacing=10)
                
                # Add Delete button only if admin and not deleting themselves
                if can_delete:
                    action_buttons.controls.append(
                        ft.Container(
                            content=ft.Text("🗑️ Delete", size=12, color=self.danger_color),
                            on_click=lambda e, uid=u.get('id'), uname=u.get('name'): self.open_delete_user_modal(page, uid, uname),
                            ink=True,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        )
                    )
                
                user_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(u.get('id', '')), size=12)),
                            ft.DataCell(ft.Text(u.get('name', 'N/A'), size=12, weight=ft.FontWeight.BOLD if u.get('id') == current_user_id else None)),
                            ft.DataCell(ft.Text(u.get('email', 'N/A'), size=11)),
                            ft.DataCell(ft.Container(
                                content=ft.Text(role_display, size=10, color="white", weight=ft.FontWeight.BOLD),
                                bgcolor=role_color,
                                border_radius=12,
                                padding=ft.padding.symmetric(horizontal=12, vertical=5),
                            )),
                            ft.DataCell(ft.Text(created, size=11)),
                            ft.DataCell(action_buttons),
                        ]
                    )
                )
        
        refresh_table(users)
        
        def on_search(e):
            query = search_field.value.lower() if search_field.value else ""
            if query:
                filtered = [u for u in users if query in u.get('name', '').lower() or query in u.get('email', '').lower()]
                refresh_table(filtered)
            else:
                refresh_table(users)
        
        search_field.on_change = on_search
        
        # Main content - with centered table
        content = ft.Column(
            [
                title,
                ft.Container(height=15),
                stats_row,
                ft.Container(height=20),
                ft.Row(
                    [
                        add_button,
                        ft.Container(expand=True),
                        ft.Text(f"📌 Total: {len(users)} users", size=13, color="#888888"),
                        ft.Container(width=15),
                        search_field,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=20),
                # Centered table container
                ft.Container(
                    content=user_table,
                   # alignment=ft.alignment.center,  # Center the table horizontally
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        
        main_content = ft.Container(content=content, expand=True, padding=20)
        page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        page.update()

    def open_add_user_modal(self, page: ft.Page):
        """Open modal for adding new user"""
        name_field = ft.TextField(label="Full Name *", width=350, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email *", width=350, bgcolor=self.card_color)
        password_field = ft.TextField(label="Password *", width=350, bgcolor=self.card_color, password=True, can_reveal_password=True)
        confirm_password_field = ft.TextField(label="Confirm Password *", width=350, bgcolor=self.card_color, password=True, can_reveal_password=True)
        role_field = ft.Dropdown(
            label="Role *",
            width=350,
            options=[
                ft.dropdown.Option("user", "Regular User"),
                ft.dropdown.Option("manager", "Manager"),
                ft.dropdown.Option("admin", "Administrator"),
            ],
            value="user",
            bgcolor=self.card_color,
        )
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def save_user(e):
            # Validation
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter name!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            if not email_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter email!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            if not password_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter password!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            if password_field.value != confirm_password_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Passwords do not match!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            
            # Create user - adjust parameters to match your UserManager
            result = UserManager.create(
                name=name_field.value,
                email=email_field.value,
                password=password_field.value,
                role=role_field.value
            )
            
            if result:
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ User {name_field.value} added!"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_users(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error: Email already exists!"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Add New User", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column([name_field, email_field, password_field, confirm_password_field, role_field], spacing=12),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Create", on_click=save_user, style=ft.ButtonStyle(bgcolor=self.success_color)),
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
        """Open modal for editing user with password reset"""
        # Find user by ID
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
            
        is_current_user = user_dict.get('id') == self.current_user.get('id')
        is_admin = self.current_user.get('role') == 'admin'
        
        name_field = ft.TextField(label="Full Name", value=user_dict.get('name', ''), width=380, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", value=user_dict.get('email', ''), width=380, bgcolor=self.card_color, read_only=True)
        
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
        
        # Password reset fields
        password_field = ft.TextField(
            label="New Password (leave blank to keep current)", 
            width=380, 
            bgcolor=self.card_color, 
            password=True, 
            can_reveal_password=True, 
            hint_text="Enter new password only if you want to change"
        )
        
        confirm_password_field = ft.TextField(
            label="Confirm New Password", 
            width=380, 
            bgcolor=self.card_color, 
            password=True, 
            can_reveal_password=True, 
            hint_text="Re-enter new password"
        )
        
        password_status = ft.Text("", size=11, color="#888888")
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def update_user(e):
            # Validate passwords if provided
            new_password = password_field.value
            if new_password:
                if new_password != confirm_password_field.value:
                    password_status.value = "❌ Passwords do not match!"
                    password_status.color = self.danger_color
                    page.update()
                    return
                if len(new_password) < 4:
                    password_status.value = "❌ Password must be at least 4 characters!"
                    password_status.color = self.danger_color
                    page.update()
                    return
            
            # Update using direct database
            import sqlite3
            from database import DB_PATH
            import hashlib
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                if new_password:
                    # Hash the new password
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
                result = cursor.rowcount > 0
                conn.close()
                
            except Exception as ex:
                print(f"Update error: {ex}")
                result = False
            
            if result:
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ User {name_field.value} updated successfully!"), bgcolor=self.success_color)
                page.snack_bar.open = True
                if is_current_user:
                    self.current_user['name'] = name_field.value
                    self.current_user['role'] = role_field.value
                self.show_users(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error updating user!"), bgcolor="red")
                page.snack_bar.open = True
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
                            ft.Text("Reset Password", size=14, weight=ft.FontWeight.BOLD, color=self.accent_color),
                            password_field,
                            confirm_password_field,
                            password_status,
                        ], spacing=12, height=480),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Update User", on_click=update_user, style=ft.ButtonStyle(bgcolor=self.accent_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=10),
                    padding=20,
                    width=450
                ),
            ),
            expand=True,
            bgcolor="#80000000"
        )
        page.overlay.append(modal)
        page.update()
    
    def open_delete_user_modal(self, page: ft.Page, user_id, user_name):
        """Open modal for delete confirmation"""
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            # Find user by ID
            users = self.dict_list(UserManager.get_all())
            user_to_delete = None
            for u in users:
                if u.get('id') == user_id:
                    user_to_delete = u
                    break
            
            if user_to_delete:
                email = user_to_delete.get('email')
                
                # Try different delete methods
                try:
                    # Attempt to delete using common method names
                    if hasattr(UserManager, 'delete'):
                        result = UserManager.delete(email)
                    elif hasattr(UserManager, 'delete_user'):
                        result = UserManager.delete_user(email)
                    elif hasattr(UserManager, 'remove'):
                        result = UserManager.remove(email)
                    elif hasattr(UserManager, 'delete_by_email'):
                        result = UserManager.delete_by_email(email)
                    else:
                        # If no delete method, try direct database access
                        import sqlite3
                        from database import DB_PATH
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
                        conn.commit()
                        result = cursor.rowcount > 0
                        conn.close()
                    
                    if result:
                        page.overlay.clear()
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"✓ User '{user_name}' deleted successfully!"),
                            bgcolor=self.success_color,
                        )
                        page.snack_bar.open = True
                        self.show_users(page)
                    else:
                        page.snack_bar = ft.SnackBar(
                            ft.Text("Error: Could not delete user!"),
                            bgcolor=self.danger_color,
                        )
                        page.snack_bar.open = True
                        page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Error: {str(ex)}"),
                        bgcolor=self.danger_color,
                    )
                    page.snack_bar.open = True
                    page.update()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("User not found!"),
                    bgcolor=self.danger_color,
                )
                page.snack_bar.open = True
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD),
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
                            ft.FilledButton(
                                "Yes, Delete", 
                                on_click=confirm_delete, 
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color),
                            ),
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

    # ==================== SETTINGS ====================
    
    def show_settings(self, page: ft.Page):
        """Show settings page - Simple button navigation version"""
        page.controls.clear()
        
        sidebar = self.create_sidebar(page)
        is_admin = self.current_user.get('role') == 'admin' if self.current_user else False
        
        # Title
        title = ft.Text("⚙️ Settings", size=28, weight=ft.FontWeight.BOLD, color=self.text_color)
        
        # Section selection
        selected_section = "profile"
        
        # Section buttons
        section_buttons = ft.Row([
            ft.Container(
                content=ft.Text("👤 Profile", size=14, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                bgcolor=self.accent_color,
                border_radius=8,
                data="profile",
                on_click=lambda e: change_section(e.control.data),
                ink=True,
            ),
            ft.Container(
                content=ft.Text("🔐 Security", size=14, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                bgcolor=self.card_color,
                border_radius=8,
                data="security",
                on_click=lambda e: change_section(e.control.data),
                ink=True,
            ),
            ft.Container(
                content=ft.Text("🏢 Company", size=14, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                bgcolor=self.card_color,
                border_radius=8,
                data="company",
                on_click=lambda e: change_section(e.control.data),
                ink=True,
            ),
            ft.Container(
                content=ft.Text("💾 Database", size=14, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                bgcolor=self.card_color,
                border_radius=8,
                data="database",
                on_click=lambda e: change_section(e.control.data),
                ink=True,
            ),
            ft.Container(
                content=ft.Text("🎨 Appearance", size=14, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=10),
                bgcolor=self.card_color,
                border_radius=8,
                data="appearance",
                on_click=lambda e: change_section(e.control.data),
                ink=True,
            ),
        ], spacing=10)
        
        # Content container
        content_container = ft.Container(expand=True)
        
        def change_section(section):
            nonlocal selected_section
            selected_section = section
            
            # Update button colors
            for btn in section_buttons.controls:
                if btn.data == section:
                    btn.bgcolor = self.accent_color
                else:
                    btn.bgcolor = self.card_color
                btn.update()
            
            # Update content
            if section == "profile":
                content_container.content = create_profile_content()
            elif section == "security":
                content_container.content = create_security_content()
            elif section == "company":
                content_container.content = create_company_content()
            elif section == "database":
                content_container.content = create_database_content()
            elif section == "appearance":
                content_container.content = create_appearance_content()
            
            page.update()
        
        # ========== PROFILE CONTENT ==========
        def create_profile_content():
            import os
            import shutil
            from datetime import datetime
            import hashlib
            
            # Create avatars folder if not exists
            avatars_folder = "avatars"
            if not os.path.exists(avatars_folder):
                os.makedirs(avatars_folder)
            
            # Get current avatar
            current_avatar = self.current_user.get('avatar_path', '')
            has_avatar = current_avatar and os.path.exists(current_avatar) if current_avatar else False
            
            # Avatar display
            avatar_display = ft.Container(
                content=ft.Column([
                    ft.Text("👤", size=50),
                    ft.Text("No Avatar", size=10, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                width=100, height=100,
                bgcolor=self.card_color,
                border_radius=50,
                border=ft.border.all(3, self.accent_color),
            )
            
            if has_avatar:
                try:
                    avatar_display.content = ft.Column([
                        ft.Image(src=current_avatar, width=90, height=90, fit=ft.ImageFit.CONTAIN),
                        ft.Text("Current", size=8, color=self.accent_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                except:
                    pass
            
            selected_image_path = None
            selected_image_name = None
            
            # File picker for avatar
            def on_image_picked(e: ft.FilePickerResultEvent):
                nonlocal selected_image_path, selected_image_name
                
                if e.files:
                    file = e.files[0]
                    selected_image_path = file.path
                    selected_image_name = file.name
                    
                    # Update preview
                    try:
                        avatar_display.content = ft.Column([
                            ft.Image(src=selected_image_path, width=90, height=90, fit=ft.ImageFit.CONTAIN),
                            ft.Text("New avatar", size=8, color=self.success_color),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                        page.update()
                    except:
                        pass
                    
                    page.snack_bar = ft.SnackBar(ft.Text(f"✓ Image selected: {selected_image_name}"), bgcolor=self.success_color)
                    page.snack_bar.open = True
                    page.update()
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ No image selected"), bgcolor=self.danger_color)
                    page.snack_bar.open = True
                    page.update()
            
            image_picker = ft.FilePicker(on_result=on_image_picked)
            page.overlay.append(image_picker)
            
            def select_avatar(e):
                image_picker.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
                    dialog_title="Select Avatar Image"
                )
            
            def clear_avatar(e):
                nonlocal selected_image_path
                selected_image_path = None
                selected_image_name = None
                
                # Delete avatar file
                if self.current_user.get('avatar_path') and os.path.exists(self.current_user['avatar_path']):
                    try:
                        os.remove(self.current_user['avatar_path'])
                    except:
                        pass
                
                self.current_user['avatar_path'] = None
                
                avatar_display.content = ft.Column([
                    ft.Text("👤", size=50),
                    ft.Text("No Avatar", size=10, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
                
                page.snack_bar = ft.SnackBar(ft.Text("✓ Avatar cleared"), bgcolor=self.success_color)
                page.snack_bar.open = True
                page.update()
            
            def save_avatar():
                """Save the selected avatar to avatars folder"""
                if selected_image_path and os.path.exists(selected_image_path):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_ext = os.path.splitext(selected_image_path)[1]
                    user_hash = hashlib.md5(f"user_{self.current_user['id']}".encode()).hexdigest()[:8]
                    new_filename = f"avatar_{user_hash}_{timestamp}{file_ext}"
                    new_path = os.path.join(avatars_folder, new_filename)
                    shutil.copy2(selected_image_path, new_path)
                    return new_path
                return None
            
            name_field = ft.TextField(
                label="Full Name", 
                value=self.current_user.get('name', ''), 
                width=350, 
                bgcolor=self.card_color
            )
            email_field = ft.TextField(
                label="Email", 
                value=self.current_user.get('email', ''), 
                width=350, 
                bgcolor=self.card_color, 
                read_only=True
            )
            role_field = ft.TextField(
                label="Role", 
                value=self.current_user.get('role', 'user').upper(), 
                width=350, 
                bgcolor=self.card_color, 
                read_only=True
            )
            
            created_date = self.current_user.get('created_at', '')
            if created_date:
                created_date = str(created_date)[:10] if len(str(created_date)) > 10 else str(created_date)
            else:
                created_date = 'N/A'
            
            member_since = ft.Text(f"Member since: {created_date}", size=11, color="#888888")
            profile_status = ft.Text("", size=12, color="#888888")
            
            def update_profile(e):
                new_name = name_field.value.strip()
                if not new_name:
                    profile_status.value = "❌ Name cannot be empty!"
                    profile_status.color = self.danger_color
                    page.update()
                    return
                
                # Save avatar if selected
                new_avatar_path = save_avatar() if selected_image_path else self.current_user.get('avatar_path')
                
                # Delete old avatar if replaced
                if selected_image_path and self.current_user.get('avatar_path') and os.path.exists(self.current_user['avatar_path']):
                    if self.current_user['avatar_path'] != new_avatar_path:
                        try:
                            os.remove(self.current_user['avatar_path'])
                        except:
                            pass
                
                import sqlite3
                from database import DB_PATH
                
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    if new_avatar_path:
                        cursor.execute("UPDATE users SET name = ?, avatar_path = ? WHERE id = ?", 
                                     (new_name, new_avatar_path, self.current_user['id']))
                    else:
                        cursor.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, self.current_user['id']))
                    
                    conn.commit()
                    result = cursor.rowcount > 0
                    conn.close()
                    
                    if result:
                        self.current_user['name'] = new_name
                        if new_avatar_path:
                            self.current_user['avatar_path'] = new_avatar_path
                        profile_status.value = "✅ Profile updated successfully!"
                        profile_status.color = self.success_color
                        page.snack_bar = ft.SnackBar(ft.Text("✓ Profile updated!"), bgcolor=self.success_color)
                        page.snack_bar.open = True
                    else:
                        profile_status.value = "❌ Error updating profile!"
                        profile_status.color = self.danger_color
                except Exception as ex:
                    profile_status.value = f"❌ Error: {str(ex)}"
                    profile_status.color = self.danger_color
                
                page.update()
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("Profile Information", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(),
                    ft.Container(height=20),
                    ft.Row([
                        ft.Container(
                            content=ft.Column([
                                avatar_display,
                                ft.Row([
                                    ft.TextButton("Select Image", on_click=select_avatar),
                                    ft.TextButton("Clear", on_click=clear_avatar),
                                ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Text("Click 'Update Profile' to save", size=8, color="#888888"),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                            width=150,
                        ),
                        ft.Container(width=30),
                        ft.Container(
                            content=ft.Column([
                                name_field,
                                email_field,
                                role_field,
                                member_since,
                                ft.Container(height=10),
                                profile_status,
                            ], spacing=15),
                            expand=True,
                        ),
                    ], expand=True),
                    ft.Container(height=20),
                    ft.Row([
                        ft.FilledButton("Update Profile", on_click=update_profile, 
                                      style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                        ft.Container(expand=True),
                    ]),
                ], spacing=10),
                padding=20,
                expand=True,
            )
        
        # ========== SECURITY CONTENT ==========
        def create_security_content():
            password_status = ft.Text("", size=12, color="#888888")
            
            current_password = ft.TextField(label="Current Password", width=400, password=True, can_reveal_password=True, bgcolor=self.card_color)
            new_password = ft.TextField(label="New Password", width=400, password=True, can_reveal_password=True, bgcolor=self.card_color)
            confirm_password = ft.TextField(label="Confirm New Password", width=400, password=True, can_reveal_password=True, bgcolor=self.card_color)
            
            def change_password(e):
                current = current_password.value
                new = new_password.value
                confirm = confirm_password.value
                
                if not current or not new or not confirm:
                    password_status.value = "❌ Please fill all fields!"
                    password_status.color = self.danger_color
                    page.update()
                    return
                
                if new != confirm:
                    password_status.value = "❌ New passwords do not match!"
                    password_status.color = self.danger_color
                    page.update()
                    return
                
                from managers.user_manager import UserManager
                user = UserManager.authenticate(self.current_user['email'], current)
                
                if not user:
                    password_status.value = "❌ Current password is incorrect!"
                    password_status.color = self.danger_color
                    page.update()
                    return
                
                import sqlite3
                from database import DB_PATH
                import hashlib
                
                try:
                    hashed_password = hashlib.sha256(new.encode()).hexdigest()
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, self.current_user['id']))
                    conn.commit()
                    success = cursor.rowcount > 0
                    conn.close()
                    
                    if success:
                        password_status.value = "✅ Password changed successfully!"
                        password_status.color = self.success_color
                        current_password.value = ""
                        new_password.value = ""
                        confirm_password.value = ""
                        page.snack_bar = ft.SnackBar(ft.Text("✓ Password changed!"), bgcolor=self.success_color)
                        page.snack_bar.open = True
                    else:
                        password_status.value = "❌ Failed to update password!"
                        password_status.color = self.danger_color
                except Exception as ex:
                    password_status.value = f"❌ Error: {str(ex)}"
                    password_status.color = self.danger_color
                
                page.update()
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("Security Settings", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(),
                    ft.Container(height=20),
                    ft.Text("Change Password", size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Container(height=10),
                    current_password,
                    new_password,
                    confirm_password,
                    password_status,
                    ft.Container(height=20),
                    ft.Row([
                        ft.FilledButton("Change Password", on_click=change_password, style=ft.ButtonStyle(bgcolor=self.warning_color)),
                    ]),
                ], spacing=10),
                padding=20,
                expand=True,
            )
        
        # ========== COMPANY CONTENT ==========
        # ========== COMPANY CONTENT ==========
        def create_company_content():
            import json
            import os
            
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(base_dir, "company_config.json")
            
            company_data = {}
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        company_data = json.load(f)
                except:
                    pass
            
            company_name_field = ft.TextField(
                label="Company Name", 
                width=350, 
                bgcolor=self.card_color, 
                value=company_data.get('company_name', 'Store Management System')
            )
            phone_field = ft.TextField(
                label="Phone Number", 
                width=350, 
                bgcolor=self.card_color, 
                value=company_data.get('phone', '')
            )
            email_field = ft.TextField(
                label="Email Address", 
                width=350, 
                bgcolor=self.card_color, 
                value=company_data.get('email', '')
            )
            website_field = ft.TextField(
                label="Website", 
                width=350, 
                bgcolor=self.card_color, 
                value=company_data.get('website', '')
            )
            address_field = ft.TextField(
                label="Address", 
                width=350, 
                bgcolor=self.card_color, 
                value=company_data.get('address', '')
            )
            city_field = ft.TextField(
                label="City", 
                width=350, 
                bgcolor=self.card_color, 
                value=company_data.get('city', '')
            )
            tax_id_field = ft.TextField(
                label="Tax ID / VAT", 
                width=350, 
                bgcolor=self.card_color, 
                value=company_data.get('tax_id', '')
            )
            
            company_status = ft.Text("", size=12, color="#888888")
            
            def save_company_info(e):
                new_data = {
                    'company_name': company_name_field.value,
                    'phone': phone_field.value,
                    'email': email_field.value,
                    'website': website_field.value,
                    'address': address_field.value,
                    'city': city_field.value,
                    'tax_id': tax_id_field.value,
                }
                
                try:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(new_data, f, indent=4, ensure_ascii=False)
                    
                    company_status.value = "✅ Company information saved successfully!"
                    company_status.color = self.success_color
                    page.snack_bar = ft.SnackBar(ft.Text("✓ Company information saved!"), bgcolor=self.success_color)
                    page.snack_bar.open = True
                except Exception as ex:
                    company_status.value = f"❌ Error saving: {str(ex)}"
                    company_status.color = self.danger_color
                
                page.update()
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("Company Information", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(),
                    ft.Container(height=20),
                    ft.Row([
                        ft.Column([
                            company_name_field,
                            phone_field,
                            email_field,
                            tax_id_field,
                        ], spacing=15),
                        ft.Container(width=40),
                        ft.Column([
                            website_field,
                            address_field,
                            city_field,
                        ], spacing=15),
                    ]),
                    ft.Container(height=20),
                    company_status,
                    ft.Container(height=10),
                    # Center the button
                    ft.Row([
                        ft.Container(expand=True),
                        ft.FilledButton("💾 Save Company Info", on_click=save_company_info, 
                                      style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                        ft.Container(expand=True),
                    ]),
                ], spacing=10),
                padding=20,
                expand=True,
            )
        # ========== DATABASE CONTENT ==========
        def create_database_content():
            """Create database management content"""
            
            def backup_database(e):
                try:
                    import shutil
                    from datetime import datetime
                    import os
                    
                    backup_dir = "backups"
                    if not os.path.exists(backup_dir):
                        os.makedirs(backup_dir)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_name = f"backup_{timestamp}.db"
                    backup_path = os.path.join(backup_dir, backup_name)
                    
                    shutil.copy2("store_management.db", backup_path)
                    
                    file_size = os.path.getsize(backup_path)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Database backed up to: {backup_name} ({size_str})"),
                        bgcolor=self.success_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    refresh_backup_list()
                    page.update()
                    
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"❌ Backup failed: {str(ex)}"),
                        bgcolor=self.danger_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                    page.update()
            
            def restore_database(backup_file):
                print(f"DEBUG: restore_database called with: {backup_file}")
                
                def confirm_restore(e):
                    print(f"DEBUG: User confirmed restore for: {backup_file}")
                    try:
                        import shutil
                        import os
                        
                        backup_path = os.path.join("backups", backup_file)
                        print(f"DEBUG: Restoring from: {backup_path}")
                        shutil.copy2(backup_path, "store_management.db")
                        print("DEBUG: Restore completed")
                        
                        # Close overlay
                        page.overlay.clear()
                        
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"✓ Database restored from: {backup_file}. Please restart the app."),
                            bgcolor=self.success_color,
                            duration=5000
                        )
                        page.snack_bar.open = True
                        page.update()
                        
                    except Exception as ex:
                        print(f"DEBUG: Restore error: {ex}")
                        page.overlay.clear()
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"❌ Restore failed: {str(ex)}"),
                            bgcolor=self.danger_color,
                            duration=4000
                        )
                        page.snack_bar.open = True
                        page.update()
                
                def close_overlay():
                    page.overlay.clear()
                    page.update()
                
                # Create overlay at TOP RIGHT
                overlay_content = ft.Container(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(expand=True),
                                ft.Container(
                                    content=ft.Text("✕", size=16),
                                    on_click=lambda e: close_overlay(),
                                    ink=True,
                                    padding=5,
                                ),
                            ]),
                            ft.Text("⚠️ Confirm Restore", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            ft.Text(f"Restore from:", size=12),
                            ft.Text(f"{backup_file}", size=11, color=self.warning_color),
                            ft.Container(height=8),
                            ft.Text("⚠️ This will OVERWRITE current data!", size=11, color=self.danger_color),
                            ft.Text("This action cannot be undone.", size=10, color="#888888"),
                            ft.Container(height=15),
                            ft.Row([
                                ft.TextButton("Cancel", on_click=lambda e: close_overlay()),
                                ft.FilledButton("Yes, Restore", on_click=confirm_restore, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=20,
                        bgcolor=self.card_color,
                        border_radius=10,
                        width=350,
                    ),
                    top=60,
                    right=20,
                  #  alignment=ft.alignment.top_right,
                )
                
                page.overlay.append(overlay_content)
                page.update()
            
            def delete_backup(backup_file):
                print(f"DEBUG: delete_backup called with: {backup_file}")
                
                def confirm_delete(e):
                    print(f"DEBUG: User confirmed delete for: {backup_file}")
                    try:
                        import os
                        backup_path = os.path.join("backups", backup_file)
                        os.remove(backup_path)
                        print("DEBUG: Delete completed")
                        
                        # Close overlay
                        page.overlay.clear()
                        
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"✓ Deleted backup: {backup_file}"),
                            bgcolor=self.success_color,
                            duration=3000
                        )
                        page.snack_bar.open = True
                        refresh_backup_list()
                        page.update()
                        
                    except Exception as ex:
                        print(f"DEBUG: Delete error: {ex}")
                        page.overlay.clear()
                        page.snack_bar = ft.SnackBar(
                            ft.Text(f"❌ Delete failed: {str(ex)}"),
                            bgcolor=self.danger_color,
                            duration=3000
                        )
                        page.snack_bar.open = True
                        page.update()
                
                def close_overlay():
                    page.overlay.clear()
                    page.update()
                
                # Create overlay at TOP RIGHT
                overlay_content = ft.Container(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(expand=True),
                                ft.Container(
                                    content=ft.Text("✕", size=16),
                                    on_click=lambda e: close_overlay(),
                                    ink=True,
                                    padding=5,
                                ),
                            ]),
                            ft.Text("🗑️ Confirm Delete", size=16, weight=ft.FontWeight.BOLD),
                            ft.Divider(),
                            ft.Text(f"Delete backup file:", size=12),
                            ft.Text(f"{backup_file}", size=11, color=self.danger_color),
                            ft.Container(height=8),
                            ft.Text("This action cannot be undone.", size=10, color="#888888"),
                            ft.Container(height=15),
                            ft.Row([
                                ft.TextButton("Cancel", on_click=lambda e: close_overlay()),
                                ft.FilledButton("Yes, Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=20,
                        bgcolor=self.card_color,
                        border_radius=10,
                        width=350,
                    ),
                    top=60,
                    right=20,
                   # alignment=ft.alignment.top_right,
                )
                
                page.overlay.append(overlay_content)
                page.update()
           
            backup_list_container = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=200)
            
            def refresh_backup_list():
                import os
                from datetime import datetime
                
                backup_list_container.controls.clear()
                backup_dir = "backups"
                
                if os.path.exists(backup_dir):
                    backups = []
                    for file in os.listdir(backup_dir):
                        if file.endswith('.db'):
                            file_path = os.path.join(backup_dir, file)
                            file_size = os.path.getsize(file_path)
                            file_time = os.path.getmtime(file_path)
                            backups.append((file_time, file, file_size))
                    
                    backups.sort(reverse=True)
                    
                    for file_time, file, file_size in backups:
                        if file_size < 1024:
                            size_str = f"{file_size} B"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size / 1024:.1f} KB"
                        else:
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"
                        
                        date_str = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Create separate functions for each button to capture file correctly
                        def make_restore_func(f):
                            return lambda e: restore_database(f)
                        
                        def make_delete_func(f):
                            return lambda e: delete_backup(f)
                        
                        backup_list_container.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text("📁", size=16, width=30),
                                    ft.Text(file, size=12, color=self.text_color, expand=True),
                                    ft.Text(size_str, size=10, color="#888888", width=70),
                                    ft.Text(date_str, size=10, color="#888888", width=140),
                                    ft.TextButton(
                                        "Restore",
                                        on_click=make_restore_func(file),
                                        style=ft.ButtonStyle(padding=5),
                                    ),
                                    ft.TextButton(
                                        "Delete",
                                        on_click=make_delete_func(file),
                                        style=ft.ButtonStyle(padding=5, color=self.danger_color),
                                    ),
                                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=ft.padding.symmetric(vertical=6, horizontal=10),
                                bgcolor="#3C3C3C" if len(backup_list_container.controls) % 2 == 0 else ft.colors.TRANSPARENT,
                                border_radius=6,
                            )
                        )
                else:
                    backup_list_container.controls.append(
                        ft.Text("No backups found. Click 'Backup Database' to create one.", size=12, color="#888888")
                    )
            
            def get_db_size():
                import os
                if os.path.exists("store_management.db"):
                    size = os.path.getsize("store_management.db")
                    if size < 1024:
                        return f"{size} B"
                    elif size < 1024 * 1024:
                        return f"{size / 1024:.1f} KB"
                    else:
                        return f"{size / (1024 * 1024):.1f} MB"
                return "N/A"
            
            refresh_backup_list()
            db_size = get_db_size()
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("Database Management", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(),
                    ft.Container(height=20),
                    ft.Row([
                        ft.Text("🗄️", size=40),
                        ft.Column([
                            ft.Text("Database Size", size=12, color="#888888"),
                            ft.Text(db_size, size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ]),
                    ], spacing=20),
                    ft.Divider(),
                    ft.Container(height=10),
                    ft.Text("Backup & Restore", size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Container(height=10),
                    ft.Row([
                        ft.FilledButton("📥 Create Backup", on_click=backup_database, style=ft.ButtonStyle(bgcolor=self.success_color)),
                        ft.FilledButton("🔄 Refresh List", on_click=lambda e: refresh_backup_list(), style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    ], spacing=15),
                    ft.Container(height=15),
                    ft.Text("Available Backups", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
                    ft.Container(
                        content=backup_list_container,
                        border=ft.border.all(1, "#3C3C3C"),
                        border_radius=8,
                        padding=5,
                        height=250,
                    ),
                    ft.Divider(),
                    ft.Container(height=10),
                    ft.Text("Data Management", size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Container(height=10),
                    ft.Row([
                        ft.FilledButton("🗑️ Clear Logs", style=ft.ButtonStyle(bgcolor=self.danger_color)),
                        ft.FilledButton("📊 Export All Data", style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    ], spacing=15),
                    ft.Container(height=20),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("⚠️ Danger Zone", size=14, weight=ft.FontWeight.BOLD, color=self.danger_color),
                            ft.Text("Reset all data - This action cannot be undone!", size=11, color="#888888"),
                            ft.ElevatedButton("Reset Database", color=self.danger_color),
                        ], spacing=5),
                        padding=15,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                    ),
                ], spacing=10),
                padding=20,
                expand=True,
            )
        
        # ========== APPEARANCE CONTENT ==========
        def create_appearance_content():
            
            # Status message
            appearance_status = ft.Text("", size=12, color="#888888")
            
            # Current accent color display
            current_color_display = ft.Container(
                width=60,
                height=60,
                bgcolor=self.accent_color,
                border_radius=10,
                border=ft.border.all(2, "#FFFFFF"),
            )
            
            # Function to apply color change to the entire app
            def apply_accent_color(color_code):
                # Update StoreApp accent color
                self.accent_color = color_code
                
                # Update the color display
                current_color_display.bgcolor = color_code
                
                # Show success message
                appearance_status.value = f"✓ Accent color changed to {color_code}"
                appearance_status.color = self.success_color
                
                # Show snackbar
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Accent color changed!"),
                    bgcolor=color_code,
                    duration=3000
                )
                page.snack_bar.open = True
                
                # Update the settings page itself to show new accent color
                page.update()
            
            # Color options
            color_options = [
                {"name": "Blue", "code": "#1976D2"},
                {"name": "Green", "code": "#4CAF50"},
                {"name": "Purple", "code": "#9C27B0"},
                {"name": "Orange", "code": "#FF9800"},
                {"name": "Pink", "code": "#E91E63"},
                {"name": "Cyan", "code": "#00BCD4"},
                {"name": "Red", "code": "#F44336"},
                {"name": "Teal", "code": "#009688"},
            ]
            
            # Create color buttons
            color_buttons = ft.Row([], spacing=10, wrap=True)
            for color in color_options:
                is_selected = self.accent_color == color["code"]
                color_buttons.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Container(
                                width=45, height=45,
                                bgcolor=color["code"],
                                border_radius=8,
                                border=ft.border.all(3, "#FFFFFF") if is_selected else ft.border.all(1, "#555555"),
                            ),
                            ft.Text(color["name"], size=10, color="#888888"),
                        ], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        on_click=lambda e, c=color["code"]: apply_accent_color(c),
                        ink=True,
                    )
                )
            
            # Simple theme info
            theme_info = ft.Text(
                "Theme: Dark Mode\nTo change theme, restart the application.",
                size=12,
                color="#888888",
                text_align=ft.TextAlign.CENTER,
            )
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("Appearance Settings", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(),
                    ft.Container(height=20),
                    
                    # Accent Color Section
                    ft.Text("Select Accent Color", size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Container(height=10),
                    
                    ft.Row([
                        current_color_display,
                        ft.Column([
                            ft.Text("Current Color:", size=11, color="#888888"),
                            ft.Text(self.accent_color, size=10, color="#888888", selectable=True),
                        ], spacing=5),
                    ], spacing=15),
                    
                    ft.Container(height=15),
                    color_buttons,
                    
                    ft.Divider(),
                    ft.Container(height=15),
                    
                    # Theme Section
                    ft.Text("Theme", size=16, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Container(height=10),
                    theme_info,
                    
                    ft.Container(height=20),
                    appearance_status,
                    
                ], spacing=15),
                padding=20,
                expand=True,
            )
        
        # Initialize with profile content
        content_container.content = create_profile_content()
        
        # Main content
        main_column = ft.Column([
            title,
            ft.Container(height=20),
            section_buttons,
            ft.Container(height=20),
            ft.Divider(),
            content_container,
        ], expand=True)
        
        main_content = ft.Container(content=main_column, expand=True, padding=20)
        page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        page.update()

    def show_barcode_dialog(self, page: ft.Page, item):
        """Show barcode dialog with real barcode image using OVERLAY"""
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        item_name = item.get('name', 'Item')
        
        # Create real barcode image URL
        barcode_image_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_text}&code=Code128&dpi=120"
        
        def close_overlay():
            page.overlay.clear()
            page.update()
        
        def print_barcode(e):
            """Open print dialog in browser"""
            import webbrowser
            # Open the barcode image in browser
            webbrowser.open(barcode_image_url)
            # Don't close the overlay immediately so user can see both
            page.snack_bar = ft.SnackBar(ft.Text("🖨️ Barcode opened in browser - Press Ctrl+P to print"), bgcolor=self.accent_color, duration=5000)
            page.snack_bar.open = True
            page.update()
        
        def print_directly(e):
            """Try to print directly from image"""
            # Create HTML content for printing
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Barcode - {barcode_text}</title>
                <style>
                    body {{
                        text-align: center;
                        padding: 50px;
                        font-family: monospace;
                    }}
                    .barcode-img {{
                        max-width: 100%;
                        height: auto;
                    }}
                    .number {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-top: 20px;
                    }}
                    @media print {{
                        .no-print {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <img class="barcode-img" src="{barcode_image_url}" alt="Barcode">
                <div class="number">{barcode_text}</div>
                <div class="no-print" style="margin-top: 30px;">
                    <button onclick="window.print()">🖨️ Print Now</button>
                    <button onclick="window.close()">Close</button>
                </div>
                <script>
                    window.onload = function() {{
                        setTimeout(function() {{
                            window.print();
                        }}, 500);
                    }}
                </script>
            </body>
            </html>
            """
            
            import tempfile
            import webbrowser
            import os
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            webbrowser.open(f'file://{temp_file.name}')
            close_overlay()
        
        barcode_display = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text("✕", size=20, color=self.text_color),
                        on_click=lambda e: close_overlay(),
                        ink=True,
                        padding=8,
                    ),
                ]),
                ft.Image(src=barcode_image_url, width=350, height=120),
                ft.Text(barcode_text, size=20, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Text("Scan this barcode with your camera", size=11, color="#888888"),
                ft.Row([
                    ft.Container(expand=True),
                    ft.FilledButton("Close", on_click=lambda e: close_overlay(), style=ft.ButtonStyle(bgcolor=self.card_color, color=self.text_color)),
                    ft.FilledButton("🖨️ Print", on_click=print_directly, style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    ft.Container(expand=True),
                ], spacing=10),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=20,
            bgcolor="#363635",
            border_radius=15,
            width=450,
            height=380,
        )
        
        # Create a row to center the content horizontally at top
        overlay = ft.Container(
            content=ft.Row([
                ft.Container(expand=True),
                barcode_display,
                ft.Container(expand=True),
            ], alignment=ft.MainAxisAlignment.CENTER),
            margin=ft.margin.only(top=10),
        )
        
        page.overlay.append(overlay)
        page.update()

    def has_permission(self, permission):
        """Check if current user has specific permission"""
        if not self.current_user:
            return False
        
        role = self.current_user.get('role', 'user')
        is_guest = self.current_user.get('guest_mode', False)
        is_trial = self.current_user.get('trial_mode', False)
        is_premium = self.current_user.get('is_premium', False)
        
        # Premium users get full access
        if is_premium:
            return True
        
        # Guest and Trial users (read-only)
        if is_guest or is_trial:
            guest_permissions = [
                'view_dashboard', 
                'view_materials', 
                'view_accessories', 
                'view_inventory',
                'scan_barcode'
            ]
            return permission in guest_permissions
        
        # Regular role-based permissions
        permissions = {
            'admin': [
                'view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 
                'view_users', 'view_settings',
                'add_material', 'edit_material', 'delete_material',
                'add_accessory', 'edit_accessory', 'delete_accessory',
                'add_user', 'edit_user', 'delete_user',
                'export_reports', 'scan_barcode', 'backup_database', 'reset_database'
            ],
            'manager': [
                'view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 
                'view_users', 'view_settings',
                'add_material', 'edit_material', 'delete_material',
                'add_accessory', 'edit_accessory', 'delete_accessory',
                'export_reports', 'scan_barcode'
            ],
            'user': [
                'view_dashboard', 'view_materials', 'view_accessories', 'view_inventory',
                'scan_barcode'
            ]
        }
        
        return permission in permissions.get(role, [])
    
    def export_all_data(self, page: ft.Page):
        """Export all data to CSV files"""
        try:
            import csv
            from datetime import datetime
            import os
            
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export materials
            materials = self.dict_list(MaterialManager.get_all())
            materials_file = os.path.join(export_dir, f"materials_{timestamp}.csv")
            with open(materials_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if materials:
                    writer.writerow(materials[0].keys())
                    for m in materials:
                        writer.writerow(m.values())
            
            # Export accessories
            accessories = self.dict_list(AccessoryManager.get_all())
            accessories_file = os.path.join(export_dir, f"accessories_{timestamp}.csv")
            with open(accessories_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if accessories:
                    writer.writerow(accessories[0].keys())
                    for a in accessories:
                        writer.writerow(a.values())
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Exported to {export_dir}/"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(ex)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    
    def import_from_csv_text(self, page: ft.Page, data_type, csv_text):
        """Import data from CSV text"""
        try:
            import csv
            import io
            import sqlite3
            from database import DB_PATH
            
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            imported_count = 0
            
            if data_type == "materials":
                for row in csv_reader:
                    cursor.execute("""
                        INSERT OR REPLACE INTO materials 
                        (name, item_code, quantity, size, length, quality, location_ids, colors, notes, barcode_value)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('name'), row.get('item_code'),
                        int(row.get('quantity', 0)) if row.get('quantity') else 0,
                        row.get('size'), row.get('length'), row.get('quality'),
                        row.get('location_ids'), row.get('colors'), row.get('notes'),
                        row.get('barcode_value')
                    ))
                    imported_count += 1
            else:
                for row in csv_reader:
                    cursor.execute("""
                        INSERT OR REPLACE INTO accessories 
                        (name, item_code, quantity, price, quality, location, notes, barcode_value)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('name'), row.get('item_code'),
                        int(row.get('quantity', 0)) if row.get('quantity') else 0,
                        float(row.get('price', 0)) if row.get('price') else 0,
                        row.get('quality'), row.get('location'),
                        row.get('notes'), row.get('barcode_value')
                    ))
                    imported_count += 1
            
            conn.commit()
            conn.close()
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Imported {imported_count} {data_type}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            return True
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Import failed: {str(ex)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            return False
    
    def export_all_data_simple(self, page: ft.Page):
        """Export all data to CSV files"""
        try:
            import csv
            from datetime import datetime
            import os
            
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export materials
            materials = self.dict_list(MaterialManager.get_all())
            if materials:
                materials_file = os.path.join(export_dir, f"materials_{timestamp}.csv")
                with open(materials_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=materials[0].keys())
                    writer.writeheader()
                    writer.writerows(materials)
            
            # Export accessories
            accessories = self.dict_list(AccessoryManager.get_all())
            if accessories:
                accessories_file = os.path.join(export_dir, f"accessories_{timestamp}.csv")
                with open(accessories_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=accessories[0].keys())
                    writer.writeheader()
                    writer.writerows(accessories)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Exported to {export_dir}/"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(ex)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def show_upgrade_screen(self, page: ft.Page):
        """Simple upgrade screen for testing"""
        page.controls.clear()
        
        print("=" * 50)
        print("UPGRADE SCREEN IS SHOWING!")
        print("=" * 50)
        
        def continue_as_guest(e):
            self.current_user = {
                'id': 0,
                'name': 'Guest User',
                'email': 'guest@store.com',
                'role': 'guest',
                'guest_mode': True,
                'trial_mode': False
            }
            self.show_dashboard(page)
        
        def go_to_license(e):
            self.show_license_activation(page)
        
        # Simple layout to confirm it's working
        main_content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("⚠️", size=60),
                    ft.Text("FREE TRIAL EXPIRED", size=32, weight=ft.FontWeight.BOLD, color=self.danger_color),
                    ft.Text("Your trial has ended. Please upgrade to continue.", size=14, color="#CCCCCC"),
                    ft.Container(height=30),
                    
                    ft.FilledButton(
                        "🔑 Activate License Key",
                        on_click=go_to_license,
                        width=250,
                    ),
                    ft.Container(height=15),
                    ft.OutlinedButton(
                        "Continue as Guest",
                        on_click=continue_as_guest,
                        width=250,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=40,
            bgcolor=None,
            border_radius=20,
            width=500,
        )
        
        centered = ft.Container(content=main_content, alignment=ft.alignment.center, expand=True)
        background = ft.Image(src="D:/Project2026/Store Management/images/backgound_storemgt.png", fit=ft.ImageFit.COVER)
        
        page.add(ft.Stack([background, centered], expand=True))
        page.update()

    def handle_purchase(self, plan_type):
        """Handle purchase (for demo - you can integrate Stripe here)"""
        def handler(e):
            page = e.page
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Purchase {plan_type} plan - Contact admin to get license key"),
                bgcolor=self.warning_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
        return handler
    
    def create_pricing_card(self, title, price, period, badge, on_click):
        """Create a pricing card widget"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=20, weight=ft.FontWeight.BOLD, 
                        color=self.text_color),
                    ft.Container(height=10),
                    ft.Text(price, size=36, weight=ft.FontWeight.BOLD, 
                        color=self.accent_color),
                    ft.Text(period, size=12, color="#888888"),
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "Upgrade Now",
                        on_click=on_click,  # This now receives a function that expects 'e'
                        style=ft.ButtonStyle(
                            bgcolor=self.accent_color, 
                            color=self.text_color
                        ),
                    ),
                    ft.Container(
                        content=ft.Text(badge, size=10, color=self.warning_color),
                        padding=ft.padding.symmetric(horizontal=10, vertical=3),
                        bgcolor="#3C2A1C",
                        border_radius=12,
                        visible=badge != "",
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            padding=20,
            bgcolor=self.card_color,
            border_radius=15,
            width=180,
            height=250,
        )
    
    def monitor_payment_status(self, page: ft.Page):
        """Monitor for payment completion"""
        import threading
        import time
        
        def check_status():
            # Simplified version - in production use webhooks
            for i in range(30):
                time.sleep(2)
                if i == 15:  # Simulate payment completion
                    def update_ui():
                        page.snack_bar = ft.SnackBar(
                            ft.Text("✅ Payment completed! Your account has been upgraded."),
                            bgcolor=self.success_color,
                            duration=5000
                        )
                        page.snack_bar.open = True
                        page.update()
                    
                    # Update UI on main thread
                    page.run_task(update_ui)
                    break
        
        threading.Thread(target=check_status, daemon=True).start()

    def test_upgrade_screen_direct(self, page: ft.Page):
        """Direct test method to show upgrade screen"""
        print("Direct test: Showing upgrade screen")
        self.show_upgrade_screen(page)

    def save_premium_status_to_db(self, email, is_premium, plan_type, license_key, expiry_date):
        """Save premium status to database"""
        import sqlite3
        from database import DB_PATH
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if columns exist
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Build update query based on existing columns
            update_fields = []
            update_values = []
            
            if 'is_premium' in columns:
                update_fields.append("is_premium = ?")
                update_values.append(1 if is_premium else 0)
            if 'premium_plan' in columns:
                update_fields.append("premium_plan = ?")
                update_values.append(plan_type)
            if 'license_key' in columns:
                update_fields.append("license_key = ?")
                update_values.append(license_key)
            if 'license_expiry' in columns:
                update_fields.append("license_expiry = ?")
                update_values.append(expiry_date)
            if 'role' in columns:
                update_fields.append("role = ?")
                update_values.append('premium')
            if 'trial_mode' in columns:
                update_fields.append("trial_mode = ?")
                update_values.append(0)
            
            update_values.append(email)
            
            if update_fields:
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE email = ?"
                cursor.execute(query, update_values)
                conn.commit()
                print(f"✅ Premium status saved for {email}")
            
            conn.close()
        except Exception as e:
            print(f"Error saving premium status: {e}")



    def admin_generate_license(self, page: ft.Page):
            """Admin tool to generate license keys using OVERLAY"""
            
            print("🔑 Opening license generator overlay")
            
            # Create form fields
            email_field = ft.TextField(
                label="Customer Email",
                hint_text="customer@example.com",
                width=350,
                bgcolor=self.card_color,
                border_color=self.accent_color,
            )
            
            plan_dropdown = ft.Dropdown(
                label="Plan Type",
                width=350,
                options=[
                    ft.dropdown.Option("monthly", "📅 Monthly ($9.99) - 1 year"),
                    ft.dropdown.Option("yearly", "⭐ Yearly ($99.99) - 1 year"),
                    ft.dropdown.Option("lifetime", "💎 Lifetime ($299.99) - Never expires"),
                ],
                value="monthly",
                bgcolor=self.card_color,
            )
            
            result_text = ft.Text("", size=12)
            license_manager = LicenseManager()
            
            def close_overlay():
                page.overlay.clear()
                page.update()
            
            def generate(e):
                email = email_field.value.strip()
                plan = plan_dropdown.value
                
                if not email:
                    result_text.value = "❌ Please enter customer email"
                    result_text.color = self.danger_color
                    page.update()
                    return
                
                # Generate license
                if plan == "lifetime":
                    license_key = license_manager.generate_license_key(email, plan, 3650)
                elif plan == "yearly":
                    license_key = license_manager.generate_license_key(email, plan, 365)
                else:
                    license_key = license_manager.generate_license_key(email, plan, 365)
                
                # Get license info
                is_valid, info = license_manager.validate_license(license_key)
                if is_valid:
                    expiry = datetime.fromisoformat(info['expiry_date']).strftime('%Y-%m-%d')
                    
                    result_text.value = f"✅ License Generated!\n\n🔑 Key: {license_key}\n\n📧 Email: {email}\n📋 Plan: {plan}\n📅 Expires: {expiry}"
                    result_text.color = self.success_color
                    
                    # Copy to clipboard
                    page.set_clipboard(license_key)
                    
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✅ License copied! Send to {email}"),
                        bgcolor=self.success_color,
                        duration=4000
                    )
                    page.snack_bar.open = True
                else:
                    result_text.value = "❌ Failed to generate license"
                    result_text.color = self.danger_color
                
                page.update()
            
            # Create overlay content
            overlay_content = ft.Container(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("🔑 Generate License Key", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                                    ft.Container(expand=True),
                                    ft.Container(
                                        content=ft.Text("✕", size=20, color=self.text_color),
                                        on_click=lambda e: close_overlay(),
                                        ink=True,
                                        padding=8,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Divider(height=1, color="#3C3C3C"),
                            ft.Container(height=10),
                            email_field,
                            ft.Container(height=10),
                            plan_dropdown,
                            ft.Container(height=15),
                            result_text,
                            ft.Container(height=10),
                            ft.Row(
                                [
                                    ft.TextButton("Cancel", on_click=lambda e: close_overlay()),
                                    ft.FilledButton(
                                        "Generate & Copy", 
                                        on_click=generate,
                                        style=ft.ButtonStyle(bgcolor=self.success_color),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.END,
                                spacing=10,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=20,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=450,
                ),
                margin=ft.margin.only(top=100),
            )
            
            # Add to overlay
            page.overlay.append(overlay_content)
            page.update()

    def show_license_activation(self, page: ft.Page):
        """Show license activation screen using OVERLAY"""
        
        print("=" * 50)
        print("🔑 Opening License Activation Screen")
        print("=" * 50)
        
        license_manager = LicenseManager()
        
        license_field = ft.TextField(
            label="License Key",
            hint_text="XXXXX-XXXXX-XXXXX-XXXXX",
            width=380,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_align=ft.TextAlign.CENTER,
            text_size=16,
        )
        
        status_text = ft.Text("", size=12)
        
        def close_overlay():
            page.overlay.clear()
            page.update()
        
        def activate_license(e):
            key = license_field.value.strip().upper()
            print(f"\n🔑 Attempting to activate license: {key}")
            
            if not key:
                status_text.value = "❌ Please enter a license key"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Validate license
            is_valid, result = license_manager.validate_license(key)
            
            print(f"Validation result: is_valid={is_valid}")
            
            if is_valid:
                print("✅ LICENSE VALID! Upgrading user...")
                
                # Upgrade user to premium
                self.current_user['is_premium'] = True
                self.current_user['premium_plan'] = result['plan_type']
                self.current_user['license_key'] = key
                self.current_user['license_expiry'] = result['expiry_date']
                self.current_user['trial_mode'] = False
                self.current_user['role'] = 'premium'
                
                expiry_display = datetime.fromisoformat(result['expiry_date']).strftime('%Y-%m-%d')
                
                status_text.value = f"✅ License activated! Premium features unlocked until {expiry_display}"
                status_text.color = self.success_color
                page.update()
                
                # Show success message
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"🎉 Welcome to Premium! Your {result['plan_type']} plan is active."),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                
                # Close overlay and go to dashboard (simplified - no threading)
                close_overlay()
                self.show_dashboard(page)
                
            else:
                print(f"❌ License validation FAILED: {result}")
                status_text.value = f"❌ {result}"
                status_text.color = self.danger_color
                page.update()
        
        def continue_as_guest(e):
            self.current_user = {
                'id': 0,
                'name': 'Guest User',
                'email': 'guest@store.com',
                'role': 'guest',
                'guest_mode': True,
                'trial_mode': False
            }
            close_overlay()
            self.show_dashboard(page)
        
        # Create overlay content
        overlay_content = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("🔑 Activate License", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                                ft.Container(expand=True),
                                ft.Container(
                                    content=ft.Text("✕", size=20, color=self.text_color),
                                    on_click=lambda e: close_overlay(),
                                    ink=True,
                                    padding=8,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(height=1, color="#3C3C3C"),
                        ft.Container(height=15),
                        ft.Text("Enter your license key to unlock premium features", size=13, color="#CCCCCC"),
                        ft.Container(height=15),
                        license_field,
                        ft.Container(height=10),
                        ft.FilledButton(
                            "Activate License",
                            on_click=activate_license,
                            width=250,
                            height=40,
                            style=ft.ButtonStyle(bgcolor=self.success_color),
                        ),
                        ft.Container(height=10),
                        status_text,
                        ft.Container(height=15),
                        ft.Divider(height=1, color="#3C3C3C"),
                        ft.Container(height=10),
                        ft.OutlinedButton(
                            "Continue as Guest",
                            on_click=continue_as_guest,
                            width=200,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=25,
                bgcolor=self.card_color,
                border_radius=15,
                width=480,
            ),
            alignment=ft.alignment.center,
        )
        
        # Add to overlay
        page.overlay.append(overlay_content)
        page.update()

    def show_license_info(self, page: ft.Page):
        """Show current license information"""
        if self.current_user and self.current_user.get('is_premium', False):
            license_key = self.current_user.get('license_key', 'N/A')
            plan = self.current_user.get('premium_plan', 'N/A')
            expiry = self.current_user.get('license_expiry', 'N/A')
            
            if expiry != 'N/A':
                expiry_date = datetime.fromisoformat(expiry).strftime('%Y-%m-%d')
            else:
                expiry_date = expiry
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"💎 Premium Plan: {plan} | Key: {license_key} | Expires: {expiry_date}"),
                bgcolor=self.success_color,
                duration=5000
            )
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("No active license. Please activate a license to unlock premium features."),
                bgcolor=self.warning_color,
                duration=5000
            )
        page.snack_bar.open = True
        page.update()  

    def show_image_overlay(self, page: ft.Page, image_path, title):
        """Show image in overlay when clicked"""
        def close_overlay():
            page.overlay.clear()
            page.update()
        
        img = ft.Image(src=image_path, width=500, height=400, fit=ft.ImageFit.CONTAIN)
        
        overlay_content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text("✕", size=24, weight=ft.FontWeight.BOLD, color=self.text_color),
                        on_click=lambda e: close_overlay(),
                        ink=True,
                        padding=10,
                    ),
                ]),
                ft.Divider(),
                ft.Container(height=10),
                img,
                ft.Container(height=10),
                ft.Row([
                    ft.Container(expand=True),
                    ft.FilledButton("Close", on_click=lambda e: close_overlay(), style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    ft.Container(expand=True),
                ]),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=25,
            bgcolor=self.card_color,
            border_radius=15,
            width=600,
            height=550,
        )
        
        overlay = ft.Container(
            content=overlay_content,
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(overlay)
        page.update() 

    def test_new_material_timestamp(self, page: ft.Page):
        """Test that new materials get proper timestamps"""
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Add a test material
        import random
        import string
        test_name = f"Test_Timestamp_{random.randint(1000, 9999)}"
        test_barcode = "999" + ''.join(random.choices(string.digits, k=10))
        
        cursor.execute("""
            INSERT INTO materials (name, item_code, barcode_value, quantity)
            VALUES (?, ?, ?, ?)
        """, (test_name, test_barcode, test_barcode, 0))
        
        material_id = cursor.lastrowid
        
        # Get the timestamp
        cursor.execute("SELECT id, name, created_at, updated_at FROM materials WHERE id = ?", (material_id,))
        row = cursor.fetchone()
        
        # Clean up
        cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        conn.commit()
        conn.close()
        
        if row and row[2]:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ Timestamp test passed! created_at: {row[2]}"),
                bgcolor=self.success_color,
                duration=5000
            )
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Timestamp test failed! created_at is NULL"),
                bgcolor=self.danger_color,
                duration=5000
            )
        
        page.snack_bar.open = True
        page.update()

    def show_forgot_password(self, page: ft.Page):
        """Show forgot password overlay (more reliable than dialog)"""
        
        def close_overlay():
            page.overlay.clear()
            page.update()
        
        # Step 1: Email input overlay
        email_field = ft.TextField(
            label="Email Address",
            width=320,
            bgcolor=self.card_color,
            hint_text="Enter your registered email",
            border_color=self.accent_color,
        )
        
        status_text = ft.Text("", size=12)
        
        def send_reset_code(e):
            email = email_field.value.strip()
            
            if not email:
                status_text.value = "❌ Please enter your email address"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Check if user exists
            import sqlite3
            from database import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                # Generate reset code
                import random
                import string
                reset_code = ''.join(random.choices(string.digits, k=6))
                
                # Store reset code
                if not hasattr(self, 'reset_codes'):
                    self.reset_codes = {}
                self.reset_codes[email] = reset_code
                
                # Close current overlay and show reset password overlay
                close_overlay()
                show_reset_password_overlay(email, reset_code)
            else:
                status_text.value = "❌ Email not found in our records"
                status_text.color = self.danger_color
                page.update()
        
        # Step 1 Overlay Content
        step1_content = ft.Container(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Forgot Password", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                                ft.Container(expand=True),
                                ft.Container(
                                    content=ft.Text("✕", size=20, color=self.text_color),
                                    on_click=lambda e: close_overlay(),
                                    ink=True,
                                    padding=8,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(height=1, color="#3C3C3C"),
                        ft.Container(height=10),
                        ft.Text("Enter your email address to reset your password.", size=13, color="#CCCCCC"),
                        ft.Container(height=15),
                        email_field,
                        ft.Container(height=10),
                        status_text,
                        ft.Container(height=15),
                        ft.Row(
                            [
                                ft.TextButton("Cancel", on_click=lambda e: close_overlay()),
                                ft.FilledButton(
                                    "Send Reset Code",
                                    on_click=send_reset_code,
                                    style=ft.ButtonStyle(bgcolor=self.accent_color),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=10,
                        ),
                    ],
                    spacing=8,
                ),
                padding=25,
                bgcolor=self.card_color,
                border_radius=15,
                width=400,
            ),
            alignment=ft.alignment.center,
        )
        
        def show_reset_password_overlay(email, reset_code):
            """Step 2: Enter reset code and new password"""
            
            code_field = ft.TextField(
                label="Reset Code",
                width=320,
                bgcolor=self.card_color,
                hint_text="Enter 6-digit code",
                border_color=self.accent_color,
            )
            
            new_password_field = ft.TextField(
                label="New Password",
                width=320,
                bgcolor=self.card_color,
                password=True,
                can_reveal_password=True,
                border_color=self.accent_color,
            )
            
            confirm_password_field = ft.TextField(
                label="Confirm Password",
                width=320,
                bgcolor=self.card_color,
                password=True,
                can_reveal_password=True,
                border_color=self.accent_color,
            )
            
            reset_status = ft.Text("", size=12)
            
            def close_all():
                page.overlay.clear()
                page.update()
            
            def confirm_reset(e):
                code = code_field.value.strip()
                new_password = new_password_field.value
                confirm_password = confirm_password_field.value
                
                if not code:
                    reset_status.value = "❌ Please enter reset code"
                    reset_status.color = self.danger_color
                    page.update()
                    return
                
                if code != reset_code:
                    reset_status.value = "❌ Invalid reset code"
                    reset_status.color = self.danger_color
                    page.update()
                    return
                
                if not new_password:
                    reset_status.value = "❌ Please enter new password"
                    reset_status.color = self.danger_color
                    page.update()
                    return
                
                if len(new_password) < 4:
                    reset_status.value = "❌ Password must be at least 4 characters"
                    reset_status.color = self.danger_color
                    page.update()
                    return
                
                if new_password != confirm_password:
                    reset_status.value = "❌ Passwords do not match"
                    reset_status.color = self.danger_color
                    page.update()
                    return
                
                # Update password in database
                import sqlite3
                import hashlib
                from database import DB_PATH
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                password_hash = hashlib.sha256(new_password.encode()).hexdigest()
                cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, email))
                conn.commit()
                conn.close()
                
                # Clear reset code
                if hasattr(self, 'reset_codes') and email in self.reset_codes:
                    del self.reset_codes[email]
                
                close_all()
                
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Password reset successfully! Please login with your new password."),
                    bgcolor=self.success_color,
                    duration=5000
                )
                page.snack_bar.open = True
                page.update()
            
            def resend_code(e):
                import random
                import string
                new_code = ''.join(random.choices(string.digits, k=6))
                if hasattr(self, 'reset_codes'):
                    self.reset_codes[email] = new_code
                reset_status.value = f"✅ New code sent: {new_code}"
                reset_status.color = self.success_color
                code_field.value = ""
                page.update()
            
            # Step 2 Overlay Content
            step2_content = ft.Container(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("Reset Password", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                                    ft.Container(expand=True),
                                    ft.Container(
                                        content=ft.Text("✕", size=20, color=self.text_color),
                                        on_click=lambda e: close_all(),
                                        ink=True,
                                        padding=8,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Divider(height=1, color="#3C3C3C"),
                            ft.Container(height=10),
                            ft.Text(f"Reset code sent to: {email}", size=12, color="#888888"),
                            ft.Container(height=5),
                            code_field,
                            ft.Row(
                                [ft.TextButton("Resend Code", on_click=resend_code)],
                                alignment=ft.MainAxisAlignment.START,
                            ),
                            new_password_field,
                            confirm_password_field,
                            reset_status,
                            ft.Container(height=10),
                            ft.Row(
                                [
                                    ft.TextButton("Cancel", on_click=lambda e: close_all()),
                                    ft.FilledButton(
                                        "Reset Password",
                                        on_click=confirm_reset,
                                        style=ft.ButtonStyle(bgcolor=self.success_color),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=10,
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=25,
                    bgcolor=self.card_color,
                    border_radius=15,
                    width=420,
                ),
                alignment=ft.alignment.center,
            )
            
            page.overlay.append(step2_content)
            page.update()
        
        page.overlay.append(step1_content)
        page.update()

    def debug_user_permissions(self, page: ft.Page):
        """Debug user permissions"""
        if not self.current_user:
            page.snack_bar = ft.SnackBar(ft.Text("No user logged in"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()
            return
        
        msg = f"User: {self.current_user.get('name', 'Unknown')}\n"
        msg += f"Role: {self.current_user.get('role', 'None')}\n"
        msg += f"Premium: {self.current_user.get('is_premium', False)}\n"
        msg += f"Guest Mode: {self.current_user.get('guest_mode', False)}\n"
        msg += f"Trial Mode: {self.current_user.get('trial_mode', False)}\n"
        msg += "-" * 20 + "\n"
        msg += f"edit_material: {self.has_permission('edit_material')}\n"
        msg += f"delete_material: {self.has_permission('delete_material')}\n"
        msg += f"edit_accessory: {self.has_permission('edit_accessory')}\n"
        msg += f"delete_accessory: {self.has_permission('delete_accessory')}"
        
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=self.accent_color, duration=10000)
        page.snack_bar.open = True
        page.update()

    def debug_inventory_data(self, page: ft.Page):
        """Debug inventory data"""
        print("=" * 50)
        print("DEBUGGING INVENTORY DATA")
        print("=" * 50)
        
        # Test MaterialManager
        try:
            materials = MaterialManager.get_all()
            print(f"Materials type: {type(materials)}")
            print(f"Materials count: {len(materials) if materials else 0}")
            if materials and len(materials) > 0:
                print(f"First material: {materials[0]}")
        except Exception as e:
            print(f"Error getting materials: {e}")
        
        # Test AccessoryManager
        try:
            accessories = AccessoryManager.get_all()
            print(f"Accessories type: {type(accessories)}")
            print(f"Accessories count: {len(accessories) if accessories else 0}")
            if accessories and len(accessories) > 0:
                print(f"First accessory: {accessories[0]}")
        except Exception as e:
            print(f"Error getting accessories: {e}")
        
        # Show snackbar with result
        page.snack_bar = ft.SnackBar(
            ft.Text(f"Materials: {len(materials) if materials else 0}, Accessories: {len(accessories) if accessories else 0}"),
            bgcolor=self.accent_color,
            duration=5000
        )
        page.snack_bar.open = True
        page.update()

    
# Run the app
if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
