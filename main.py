"""Store Management App - Desktop Interface Auto-Scales to Any Screen"""
import sys
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Mock problematic modules BEFORE any real imports
class DummyModule:
    def __getattr__(self, name):
        return None
    def __call__(self, *args, **kwargs):
        return None

# Replace problematic modules
problematic_modules = ['numpy', 'cv2', 'pyzbar', 'matplotlib', 'cmake', 'skbuild']
for module in problematic_modules:
    if module not in sys.modules:
        sys.modules[module] = DummyModule()
        
import time
import webbrowser
import tempfile
import flet as ft
import re
import shutil
import requests
import threading
from database import init_database
from managers.material_manager import MaterialManager
from managers.accessory_manager import AccessoryManager
from managers.user_manager import UserManager

import hashlib
import json
import os
from datetime import datetime, timedelta

# ========== FLET VERSION COMPATIBILITY WRAPPER ==========
if not hasattr(ft, 'Icons'):
    ft.Icons = ft.icons
if not hasattr(ft, 'Colors'):
    ft.Colors = ft.colors
if not hasattr(ft, 'ImageFit'):
    ft.ImageFit = ft.ImageFit
if not hasattr(ft, 'MainAxisAlignment'):
    ft.MainAxisAlignment = ft.MainAxisAlignment
if not hasattr(ft, 'CrossAxisAlignment'):
    ft.CrossAxisAlignment = ft.CrossAxisAlignment

print("✅ Flet compatibility wrapper loaded")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, 'images', 'Logo-store.png')
background_path = os.path.join(BASE_DIR, 'images', 'backgound_storemgt.png')

# ============ SCALE HELPER CLASS ============
class ScaleHelper:
    """Automatically scales desktop interface to fit any screen"""
    
    # Desktop reference size (what the UI was designed for)
    DESKTOP_WIDTH = 1600
    DESKTOP_HEIGHT = 900
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.scale = 1.0
        self.update_scale()
    
    def update_scale(self):
        """Calculate scale factor based on current window size"""
        if self.page.width and self.page.height:
            # Calculate scale to fit both width and height
            scale_w = self.page.width / self.DESKTOP_WIDTH
            scale_h = self.page.height / self.DESKTOP_HEIGHT
            # Use the smaller scale to ensure everything fits
            self.scale = min(scale_w, scale_h, 1.0)  # Max scale 1.0 (don't enlarge)
        else:
            self.scale = 1.0
        
        print(f"Screen: {self.page.width}x{self.page.height}, Scale: {self.scale:.2f}")
    
    def get_scaled_size(self, original_size):
        """Get scaled size for a dimension"""
        return original_size * self.scale
    
    def get_scaled_font(self, original_size):
        """Get scaled font size (minimum 8px)"""
        scaled = int(original_size * self.scale)
        return max(scaled, 8)
    
    def get_scaled_padding(self, original_padding):
        """Get scaled padding"""
        return original_padding * self.scale


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
        self.scale_helper = None
        
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
        if row is None:
            return None
        return dict(row)
    
    def dict_list(self, rows):
        if rows is None:
            return []
        return [dict(row) for row in rows]
    
    def convert_size_to_length(self, size_text):
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
    
    def main(self, page: ft.Page):
        # Initialize scale helper
        self.scale_helper = ScaleHelper(page)
        
        # FORCE FULL SCREEN - remove all constraints
        page.window_width = None
        page.window_height = None
        page.window_maximized = True
        page.window_resizable = True
        page.window_min_width = None
        page.window_min_height = None
        
        # Set page to use full available space
        page.title = "Store Management System"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = self.bg_color
        page.padding = 0
        page.spacing = 0
        
        # Handle resize
        def on_resize(e):
            self.scale_helper.update_scale()
            if self.current_user:
                # Force rebuild of current view
                if self.current_view == "dashboard":
                    self.show_dashboard(page)
                elif self.current_view == "materials":
                    self.show_materials_screen(page)
                elif self.current_view == "accessories":
                    self.show_accessories(page)
                elif self.current_view == "inventory":
                    self.show_inventory(page)
                elif self.current_view == "users":
                    self.show_users(page)
                elif self.current_view == "settings":
                    self.show_settings(page)
        
        page.on_resize = on_resize
        
        init_database()
        self.show_login(page)
        page.update()
    
    def get_scaled_size(self, original):
        """Get scaled size from helper"""
        if self.scale_helper:
            return self.scale_helper.get_scaled_size(original)
        return original
    
    def get_scaled_font(self, original):
        """Get scaled font from helper"""
        if self.scale_helper:
            return self.scale_helper.get_scaled_font(original)
        return original
    
    def wrap_scaled(self, content):
        """Wrap content in scaled container"""
        if self.scale_helper:
            # Create a container that centers the scaled content
            return ft.Container(
                content=ft.Container(
                    content=content,
                    width=self.scale_helper.DESKTOP_WIDTH,
                    height=self.scale_helper.DESKTOP_HEIGHT,
                ),
                width=float('inf'),
                height=float('inf'),
                alignment=ft.alignment.center,
                expand=True,
            )
        return content
    
    def show_login(self, page: ft.Page):
        """Show login screen - also scaled"""
        page.controls.clear()
        
        field_width = 280
        logo_exists = os.path.exists(logo_path)
        
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
        
        def on_login(e):
            user = UserManager.authenticate(email_field.value, password_field.value)
            if user:
                user_dict = dict(user)
                # Check license
                if user_dict.get('is_premium', False):
                    license_key = user_dict.get('license_key')
                    if license_key:
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
            self.current_user = {
                'id': 0,
                'name': 'Guest User',
                'email': 'guest@store.com',
                'role': 'guest',
                'guest_mode': True,
                'is_premium': False
            }
            self.show_dashboard(page)
        
        logo = ft.Image(src=logo_path, width=80, height=80, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=60)
        
        # Login card (fixed size, will be scaled)
        login_card_content = ft.Column(
            [
                ft.Text("Welcome", size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Text("Sign in to manage your inventory", size=13, color="#AAAAAA"),
                ft.Container(height=20),
                ft.Container(width=50, height=2, bgcolor=self.accent_color, border_radius=1),
                ft.Container(height=20),
                email_field,
                ft.Container(height=15),
                password_field,
                ft.Container(height=15),
                status_text,
                ft.Container(height=10),
                ft.Row([logo, ft.Container(width=20), ft.FilledButton("Sign In", width=140, height=45, on_click=on_login)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=20, color="#3C3C3C"),
                ft.OutlinedButton("Continue as Guest", width=field_width, height=40, on_click=on_guest_login),
                ft.Container(height=10),
                ft.TextButton("Forgot Password?", on_click=lambda e: self.show_forgot_password(page), style=ft.ButtonStyle(color="#888888")),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )
        
        login_card = ft.Container(
            content=login_card_content,
            padding=40,
            bgcolor=None,
            border_radius=20,
            width=500,
        )
        
        centered_login = ft.Container(
            content=login_card,
            alignment=ft.alignment.center,
            expand=True,
        )
        
        bg_image = ft.Image(src=background_path, fit=ft.ImageFit.COVER) if os.path.exists(background_path) else None
        
        if bg_image:
            page.add(ft.Stack([bg_image, centered_login], expand=True))
        else:
            page.add(centered_login)
        page.update()
    
    def show_dashboard(self, page: ft.Page):
        """Show dashboard - FULL SCREEN no borders"""
        page.controls.clear()
        
        # Trial expiration check
        if self.current_user and self.current_user.get('trial_mode', False):
            trial_end_str = self.current_user.get('trial_end_date')
            if trial_end_str:
                trial_end_date = datetime.strptime(trial_end_str, '%Y-%m-%d')
                if datetime.now().date() > trial_end_date.date():
                    self.show_upgrade_screen(page)
                    return
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        stats = MaterialManager.get_stats()
        accessory_stats = AccessoryManager.get_stats()
        
        # Create sidebar
        sidebar = self.create_sidebar(page)
        
        # Get current scale
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        
        # Calculate responsive sizes based on scale
        padding_size = int(20 * scale)
        font_title = int(28 * scale)
        font_stats = int(36 * scale)
        font_normal = int(14 * scale)
        
        # Stats cards row
        stats_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("📦 Total Materials", size=font_normal, color="#CCCCCC"),
                        ft.Text(str(stats.get('total_items', 0)), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=padding_size, bgcolor=self.success_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🔧 Accessories", size=font_normal, color="#CCCCCC"),
                        ft.Text(str(accessory_stats.get('total_items', 0)), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=padding_size, bgcolor=self.accent_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📄 Export Records", size=font_normal, color="#CCCCCC"),
                        ft.Text("120", size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=padding_size, bgcolor=self.warning_color, border_radius=10, expand=True,
                ),
            ],
            spacing=int(15 * scale),
            expand=True,
        )
        
        # Materials Table Panel
        materials_rows = []
        for m in materials[:10]:
            materials_rows.append(
                ft.Row([
                    ft.Text(m.get('name', 'N/A'), size=font_normal - 2, width=int(140 * scale)),
                    ft.Text(m.get('location_ids') or "N/A", size=font_normal - 2, width=int(90 * scale)),
                    ft.Text(m.get('size') or "N/A", size=font_normal - 2, width=int(80 * scale)),
                    ft.Container(
                        content=ft.Text(m.get('quality', 'Used'), size=font_normal - 4, color="white"),
                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=int(6 * scale), vertical=int(2 * scale)),
                        width=int(70 * scale),
                    ),
                    ft.Text(str(m.get('quantity', 0)), size=font_normal - 2, width=int(55 * scale)),
                ], alignment=ft.MainAxisAlignment.START)
            )
        
        if not materials_rows:
            materials_rows.append(ft.Text("No materials found", size=font_normal - 2, color="#888888"))
        
        materials_table = ft.Column([
            ft.Row([
                ft.Text("Materials", size=font_normal + 2, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_materials_screen(page)),
            ]),
            ft.Divider(height=1, color="#3C3C3C"),
            ft.Container(height=int(5 * scale)),
            ft.Row([
                ft.Text("Name", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(140 * scale)),
                ft.Text("Location", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
                ft.Text("Size", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(80 * scale)),
                ft.Text("Quality", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(70 * scale)),
                ft.Text("Stock", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(55 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
        ] + materials_rows, spacing=int(6 * scale), scroll=ft.ScrollMode.AUTO, height=int(300 * scale))
        
        left_panel = ft.Container(
            content=materials_table,
            padding=int(12 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Accessories Table Panel
        accessories_rows = []
        for a in accessories[:10]:
            has_image = a.get('image_path') and os.path.exists(a.get('image_path', '')) if a.get('image_path') else False
            image_icon = "🖼️" if has_image else "📷"
            accessories_rows.append(
                ft.Row([
                    ft.Text(image_icon, size=font_normal - 2, width=int(30 * scale)),
                    ft.Text(a.get('name', 'N/A'), size=font_normal - 2, width=int(140 * scale)),
                    ft.Text(str(a.get('quantity', 0)), size=font_normal - 2, width=int(70 * scale)),
                    ft.Container(
                        content=ft.Text(a.get('quality', 'Used'), size=font_normal - 4, color="white"),
                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=int(6 * scale), vertical=int(2 * scale)),
                        width=int(70 * scale),
                    ),
                    ft.Text("View", size=font_normal - 4, color=self.accent_color, width=int(50 * scale)),
                ], alignment=ft.MainAxisAlignment.START)
            )
        
        if not accessories_rows:
            accessories_rows.append(ft.Text("No accessories found", size=font_normal - 2, color="#888888"))
        
        accessories_table = ft.Column([
            ft.Row([
                ft.Text("Accessories & Parts", size=font_normal + 2, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_accessories(page)),
            ]),
            ft.Divider(height=1, color="#3C3C3C"),
            ft.Container(height=int(5 * scale)),
            ft.Row([
                ft.Text("Img", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(30 * scale)),
                ft.Text("Part Name", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(140 * scale)),
                ft.Text("Qty", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(70 * scale)),
                ft.Text("Quality", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(70 * scale)),
                ft.Text("Notes", size=font_normal - 4, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
        ] + accessories_rows, spacing=int(6 * scale), scroll=ft.ScrollMode.AUTO, height=int(300 * scale))
        
        right_panel = ft.Container(
            content=accessories_table,
            padding=int(12 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        middle_row = ft.Row([left_panel, right_panel], spacing=int(15 * scale), expand=True)
        
        # Low Stock Panel
        low_stock_materials = [m for m in materials if m.get('quantity', 0) < 10]
        low_stock_accessories = [a for a in accessories if a.get('quantity', 0) < 10]
        
        low_stock_list = ft.Column(spacing=int(5 * scale), scroll=ft.ScrollMode.AUTO, height=int(180 * scale))
        
        for item in low_stock_materials[:8]:
            low_stock_list.controls.append(
                ft.Row([
                    ft.Text("📦", size=font_normal - 2, width=int(35 * scale)),
                    ft.Text(item.get('name', 'Unknown')[:20], size=font_normal - 3, width=int(160 * scale)),
                    ft.Text(f"Stock: {item.get('quantity', 0)}", size=font_normal - 3, color=self.danger_color),
                ])
            )
        
        for item in low_stock_accessories[:8]:
            low_stock_list.controls.append(
                ft.Row([
                    ft.Text("🔧", size=font_normal - 2, width=int(35 * scale)),
                    ft.Text(item.get('name', 'Unknown')[:20], size=font_normal - 3, width=int(160 * scale)),
                    ft.Text(f"Stock: {item.get('quantity', 0)}", size=font_normal - 3, color=self.danger_color),
                ])
            )
        
        if not low_stock_list.controls:
            low_stock_list.controls.append(ft.Text("✅ No low stock items", size=font_normal - 2, color=self.success_color))
        
        low_stock_panel = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("⚠️ Low Stock Items", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.Text(f"Total: {len(low_stock_materials) + len(low_stock_accessories)}", size=font_normal - 3, color="#888888"),
                ]),
                ft.Divider(height=1, color="#3C3C3C"),
                ft.Container(height=int(5 * scale)),
                low_stock_list,
            ], spacing=int(8 * scale)),
            padding=int(12 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Import/Export Panel
        import_panel = ft.Container(
            content=ft.Column([
                ft.Text("📁 Import/Export", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(height=1, color="#3C3C3C"),
                ft.Container(height=int(5 * scale)),
                ft.Row([
                    ft.ElevatedButton("📥 Import", on_click=lambda e: None, expand=True),
                    ft.ElevatedButton("📤 Export", on_click=lambda e: None, expand=True),
                ], spacing=int(10 * scale)),
            ], spacing=int(8 * scale), horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=int(12 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Users Panel
        users = self.dict_list(UserManager.get_all())
        users_list = ft.Column(spacing=int(5 * scale), scroll=ft.ScrollMode.AUTO, height=int(150 * scale))
        for u in users[:5]:
            users_list.controls.append(
                ft.Row([
                    ft.Text(u.get('name', 'N/A')[:15], size=font_normal - 3, width=int(100 * scale)),
                    ft.Container(
                        content=ft.Text(u.get('role', 'user')[:8], size=font_normal - 5, color="white"),
                        bgcolor=self.success_color if u.get('role') == 'user' else self.warning_color,
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=int(6 * scale), vertical=int(2 * scale)),
                    ),
                ])
            )
        
        users_panel = ft.Container(
            content=ft.Column([
                ft.Text("👥 Users & Permissions", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(height=1, color="#3C3C3C"),
                ft.Container(height=int(5 * scale)),
                users_list,
                ft.Container(expand=True),
                ft.TextButton("Manage Users", on_click=lambda e: self.show_users(page)),
            ], spacing=int(8 * scale)),
            padding=int(12 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        bottom_row = ft.Row([low_stock_panel, import_panel, users_panel], spacing=int(15 * scale), expand=True)
        
        # Main content
        main_content = ft.Column([
            ft.Text("Dashboard", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(height=int(15 * scale)),
            stats_row,
            ft.Container(height=int(15 * scale)),
            middle_row,
            ft.Container(height=int(15 * scale)),
            bottom_row,
        ], spacing=int(5 * scale), expand=True, scroll=ft.ScrollMode.AUTO)
        
        main_container = ft.Container(
            content=main_content,
            expand=True,
            padding=padding_size,
        )
        
        # Combine sidebar and main content
        dashboard_layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        
        # Add to page with expand=True to fill screen
        page.add(dashboard_layout)
        page.update()
        
        self.current_view = "dashboard"
    
    def create_sidebar(self, page: ft.Page):
        """Create sidebar navigation with responsive sizing"""
        
        # Get current scale
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        
        # Calculate responsive widths
        sidebar_width = int(250 * scale)
        font_size_title = int(18 * scale)
        font_size_nav = int(14 * scale)
        font_size_user = int(10 * scale)
        padding_vertical = int(12 * scale)
        padding_horizontal = int(15 * scale)
        
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
        
        for emoji, label, view, permission in nav_items:
            if self.has_permission(permission):
                btn = ft.Container(
                    content=ft.Row(
                        [ft.Text(emoji, size=font_size_nav + 6), ft.Text(label, size=font_size_nav, color=self.text_color)], 
                        spacing=int(10 * scale)
                    ),
                    padding=ft.padding.symmetric(horizontal=padding_horizontal, vertical=padding_vertical),
                    border_radius=8,
                    ink=True,
                    on_click=lambda e, v=view: navigate(e, v),
                )
                nav_buttons.append(btn)
        
        def logout(e):
            self.current_user = None
            self.show_login(page)
        
        logout_btn = ft.Container(
            content=ft.Row([ft.Text("🚪", size=font_size_nav + 6), ft.Text("Logout", size=font_size_nav, color="#FF5252")], spacing=int(10 * scale)),
            padding=ft.padding.symmetric(horizontal=padding_horizontal, vertical=padding_vertical),
            border_radius=8,
            ink=True,
            on_click=logout,
        )
        
        logo_exists = os.path.exists(logo_path)
        sidebar_logo = ft.Image(src=logo_path, width=int(30 * scale), height=int(30 * scale), fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=font_size_title)
        
        title_content = ft.Row(
            [sidebar_logo, ft.Text("Store Manager", size=font_size_title, weight=ft.FontWeight.BOLD, color=self.text_color)],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=int(5 * scale),
        )
        
        role = self.current_user.get('role', 'guest') if self.current_user else 'guest'
        is_premium = self.current_user.get('is_premium', False) if self.current_user else False
        role_display = "💎 PREMIUM" if is_premium else role.upper()
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=title_content, padding=int(20 * scale)),
                    ft.Divider(),
                    ft.Column(nav_buttons, spacing=int(5 * scale)),
                    ft.Container(expand=True),
                    ft.Divider(),
                    logout_btn,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(f"User: {self.current_user.get('name', 'User') if self.current_user else 'Guest'}", 
                                    size=font_size_user, color="#888888", text_align=ft.TextAlign.CENTER),
                                ft.Text(role_display, size=font_size_user, weight=ft.FontWeight.BOLD, 
                                    color=self.success_color if is_premium else self.text_color, text_align=ft.TextAlign.CENTER),
                            ],
                            spacing=int(3 * scale),
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=int(10 * scale),
                    ),
                ],
                spacing=0,
            ),
            width=sidebar_width,
            bgcolor=self.sidebar_color,
        )
    
    # ==================== STUB METHODS for other screens ====================
    
    def show_materials_screen(self, page: ft.Page):
        """Show materials screen - FULL SCREEN like dashboard"""
        page.controls.clear()
        
        self.page_ref = page
        materials = self.dict_list(MaterialManager.get_all())
        sidebar = self.create_sidebar(page)
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(24 * scale)
        font_normal = int(14 * scale)
        font_small = int(12 * scale)
        
        # Search field
        search_field = ft.TextField(
            hint_text="Search...",
            width=int(200 * scale),
            bgcolor=self.card_color,
            border_color=self.accent_color,
            on_change=lambda e: self.search_materials_table(page, e.control.value),
        )
        
        # Filter buttons
        self.filter_buttons = {}
        
        def create_filter_button(label, color, filter_type):
            btn = ft.Container(
                content=ft.Text(label, size=font_small, weight=ft.FontWeight.BOLD, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=int(12 * scale), vertical=int(6 * scale)),
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
        ], spacing=int(8 * scale))
        
        if "All" in self.filter_buttons:
            self.filter_buttons["All"].bgcolor = self.accent_color
        
        add_button = ft.FilledButton(
            "➕ Add Material",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
            on_click=lambda e: self.open_add_modal(page),
        )
        
        # Table header
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Image", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Name", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(160 * scale)),
                ft.Text("Length", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Size", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(70 * scale)),
                ft.Text("Qty", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(45 * scale)),
                ft.Text("Quality", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(75 * scale)),
                ft.Text("Location", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Created", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
                ft.Text("Actions", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=int(6 * scale), horizontal=int(8 * scale)),
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # Table rows container
        self.table_rows_container = ft.Column(spacing=int(2 * scale), scroll=ft.ScrollMode.AUTO, height=int(450 * scale))
        self.update_materials_table(materials)
        
        left_panel = ft.Container(
            content=ft.Column([header_row, self.table_rows_container], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(5 * scale),
        )
        
        # Detail panel (right side)
        self.detail_panel = ft.Container(
            content=self.create_detail_panel(None, page),
            width=int(300 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(12 * scale),
        )
        
        # Main content
        content = ft.Column([
            ft.Row([
                ft.Text("Materials", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.Row([ft.Icon(ft.icons.SEARCH, size=int(18 * scale)), search_field], spacing=int(5 * scale)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=int(8 * scale)),
            ft.Row([filter_buttons, ft.Container(expand=True), add_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=int(12 * scale)),
            ft.Row([left_panel, ft.Container(width=int(12 * scale)), self.detail_panel], spacing=0, expand=True),
        ], expand=True)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # Combine with sidebar
        materials_layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        page.add(materials_layout)
        
        self.current_view = "materials"
        page.update()
    
    def show_accessories(self, page: ft.Page):
        """Show accessories screen - FULL SCREEN like dashboard"""
        page.controls.clear()
        
        self.page_ref = page
        accessories = self.dict_list(AccessoryManager.get_all())
        sidebar = self.create_sidebar(page)
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(24 * scale)
        font_normal = int(14 * scale)
        font_small = int(12 * scale)
        
        # Search field
        search_field = ft.TextField(
            hint_text="Search accessories...",
            width=int(200 * scale),
            bgcolor=self.card_color,
            border_color=self.accent_color,
            on_change=lambda e: self.search_accessories_table(page, e.control.value),
        )
        
        # Filter buttons
        self.accessory_filter_buttons = {}
        
        def create_filter_button(label, color, filter_type):
            btn = ft.Container(
                content=ft.Text(label, size=font_small, weight=ft.FontWeight.BOLD, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=int(12 * scale), vertical=int(6 * scale)),
                bgcolor=self.card_color if self.current_accessory_filter != filter_type else color,
                border_radius=20,
                ink=True,
                on_click=lambda e, f=filter_type: self.filter_accessories(page, f),
            )
            self.accessory_filter_buttons[filter_type] = btn
            return btn
        
        filter_buttons = ft.Row([
            create_filter_button("All", self.accent_color, "All"),
            create_filter_button("New", self.success_color, "New"),
            create_filter_button("Used", self.warning_color, "Used"),
            create_filter_button("Damaged", self.danger_color, "Damaged"),
            create_filter_button("Repaired", self.accent_color, "Repaired"),
        ], spacing=int(8 * scale))
        
        add_button = ft.FilledButton(
            "➕ Add Accessory",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
            on_click=lambda e: self.open_add_accessory_modal(page),
        )
        
        # Table header
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Image", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Name", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(160 * scale)),
                ft.Text("Code", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Qty", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(45 * scale)),
                ft.Text("Quality", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(75 * scale)),
                ft.Text("Location", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Created", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
                ft.Text("Actions", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=int(6 * scale), horizontal=int(8 * scale)),
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # Table rows container
        self.accessory_rows_container = ft.Column(spacing=int(2 * scale), scroll=ft.ScrollMode.AUTO, height=int(450 * scale))
        self.update_accessories_table(accessories)
        
        left_panel = ft.Container(
            content=ft.Column([header_row, self.accessory_rows_container], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(5 * scale),
        )
        
        # Detail panel
        self.accessory_detail_panel = ft.Container(
            content=self.create_accessory_detail_panel(None, page),
            width=int(300 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(12 * scale),
        )
        
        # Main content
        content = ft.Column([
            ft.Row([
                ft.Text("Accessories & Parts", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.Row([ft.Icon(ft.icons.SEARCH, size=int(18 * scale)), search_field], spacing=int(5 * scale)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=int(8 * scale)),
            ft.Row([filter_buttons, ft.Container(expand=True), add_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=int(12 * scale)),
            ft.Row([left_panel, ft.Container(width=int(12 * scale)), self.accessory_detail_panel], spacing=0, expand=True),
        ], expand=True)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # Combine with sidebar
        accessories_layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        page.add(accessories_layout)
        
        self.current_view = "accessories"
        page.update()
    
    def show_inventory(self, page: ft.Page):
        """Show inventory screen - FULL SCREEN like dashboard"""
        page.controls.clear()
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        sidebar = self.create_sidebar(page)
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(28 * scale)
        font_normal = int(14 * scale)
        font_stats = int(32 * scale)
        
        # Create combined inventory list
        inventory_items = []
        for m in materials:
            inventory_items.append({
                'type': '📦 Material',
                'name': m.get('name', 'N/A'),
                'code': m.get('item_code', 'N/A'),
                'quantity': m.get('quantity', 0),
                'quality': m.get('quality', 'Used'),
                'location': m.get('location_ids', 'N/A'),
            })
        
        for a in accessories:
            inventory_items.append({
                'type': '🔧 Accessory',
                'name': a.get('name', 'N/A'),
                'code': a.get('item_code', 'N/A'),
                'quantity': a.get('quantity', 0),
                'quality': a.get('quality', 'Used'),
                'location': a.get('location') or a.get('location_ids', 'N/A'),
            })
        
        inventory_items.sort(key=lambda x: x['name'])
        
        total_materials = len(materials)
        total_accessories = len(accessories)
        total_items = total_materials + total_accessories
        total_stock = sum(i.get('quantity', 0) for i in inventory_items)
        low_items = [i for i in inventory_items if i.get('quantity', 0) < 10]
        
        # Stats cards
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("📦 Total Items", size=font_normal, color="#CCCCCC"),
                    ft.Text(str(total_items), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text(f"{total_materials} Mat, {total_accessories} Acc", size=font_normal - 4, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Total Stock", size=font_normal, color="#CCCCCC"),
                    ft.Text(str(total_stock), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Units in inventory", size=font_normal - 4, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.success_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("⚠️ Low Stock", size=font_normal, color="#CCCCCC"),
                    ft.Text(str(len(low_items)), size=font_stats, weight=ft.FontWeight.BOLD, color=self.danger_color),
                    ft.Text("Items below 10 units", size=font_normal - 4, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
        ], spacing=int(15 * scale))
        
        # Inventory table header
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Type", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
                ft.Text("Name", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(200 * scale)),
                ft.Text("Code", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Qty", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Quality", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(80 * scale)),
                ft.Text("Location", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(120 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=int(8 * scale), horizontal=int(10 * scale)),
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # Table rows
        table_rows = ft.Column(spacing=int(2 * scale), scroll=ft.ScrollMode.AUTO, height=int(400 * scale))
        
        for i, item in enumerate(inventory_items[:200]):
            row_color = "#3C3C3C" if i % 2 == 0 else ft.colors.TRANSPARENT
            table_rows.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(item['type'], size=font_normal - 3, width=int(90 * scale)),
                        ft.Text(item['name'], size=font_normal - 3, width=int(200 * scale)),
                        ft.Text(item['code'], size=font_normal - 4, width=int(100 * scale)),
                        ft.Text(str(item['quantity']), size=font_normal - 3, width=int(50 * scale), 
                            color=self.danger_color if item['quantity'] < 10 else self.text_color),
                        ft.Container(
                            content=ft.Text(item['quality'], size=font_normal - 4, color="white"),
                            bgcolor=self.get_quality_color(item['quality']),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=int(6 * scale), vertical=int(2 * scale)),
                            width=int(75 * scale),
                        ),
                        ft.Text(item['location'], size=font_normal - 4, width=int(120 * scale)),
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.symmetric(vertical=int(6 * scale), horizontal=int(10 * scale)),
                    bgcolor=row_color,
                    border_radius=4,
                )
            )
        
        inventory_panel = ft.Container(
            content=ft.Column([header_row, table_rows], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(5 * scale),
        )
        
        # Main content
        content = ft.Column([
            ft.Text("Inventory Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(height=int(12 * scale)),
            stats_row,
            ft.Container(height=int(15 * scale)),
            ft.Text("📋 Inventory List", size=font_normal + 2, weight=ft.FontWeight.BOLD),
            ft.Container(height=int(8 * scale)),
            inventory_panel,
        ], expand=True, scroll=ft.ScrollMode.AUTO)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # Combine with sidebar
        inventory_layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        page.add(inventory_layout)
        
        self.current_view = "inventory"
        page.update()
    
    def show_users(self, page: ft.Page):
        """Show users screen - FULL SCREEN like dashboard"""
        page.controls.clear()
        
        users = self.dict_list(UserManager.get_all())
        sidebar = self.create_sidebar(page)
        is_admin = self.current_user.get('role') == 'admin' if self.current_user else False
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(28 * scale)
        font_normal = int(14 * scale)
        font_stats = int(32 * scale)
        
        # Stats
        admin_count = len([u for u in users if u.get('role') == 'admin'])
        manager_count = len([u for u in users if u.get('role') == 'manager'])
        user_count = len([u for u in users if u.get('role') == 'user'])
        
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("👥 Total Users", size=font_normal, color="#CCCCCC"),
                    ft.Text(str(len(users)), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👑 Admins", size=font_normal, color="#CCCCCC"),
                    ft.Text(str(admin_count), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.danger_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Managers", size=font_normal, color="#CCCCCC"),
                    ft.Text(str(manager_count), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 Users", size=font_normal, color="#CCCCCC"),
                    ft.Text(str(user_count), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.success_color, border_radius=10, expand=True,
            ),
        ], spacing=int(15 * scale))
        
        # User table header
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("ID", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Name", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(150 * scale)),
                ft.Text("Email", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(200 * scale)),
                ft.Text("Role", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
                ft.Text("Created", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Actions", size=font_normal - 3, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=int(8 * scale), horizontal=int(10 * scale)),
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # User table rows
        table_rows = ft.Column(spacing=int(2 * scale), scroll=ft.ScrollMode.AUTO, height=int(400 * scale))
        
        for u in users:
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
            
            table_rows.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(str(u.get('id', '')), size=font_normal - 3, width=int(50 * scale)),
                        ft.Text(u.get('name', 'N/A'), size=font_normal - 3, width=int(150 * scale)),
                        ft.Text(u.get('email', 'N/A'), size=font_normal - 4, width=int(200 * scale)),
                        ft.Container(
                            content=ft.Text(role_display, size=font_normal - 4, color="white"),
                            bgcolor=role_color,
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=int(8 * scale), vertical=int(4 * scale)),
                            width=int(85 * scale),
                            alignment=ft.alignment.center,
                        ),
                        ft.Text(created_date, size=font_normal - 4, width=int(100 * scale), color="#888888"),
                        ft.Row([
                            ft.IconButton(icon=ft.icons.EDIT, icon_size=int(18 * scale), 
                                        on_click=lambda e, uid=u.get('id'): self.open_edit_user_modal(page, uid)),
                            ft.IconButton(icon=ft.icons.DELETE, icon_size=int(18 * scale),
                                        on_click=lambda e, uid=u.get('id'), name=u.get('name'): self.open_delete_user_modal(page, uid, name)),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.symmetric(vertical=int(6 * scale), horizontal=int(10 * scale)),
                    border_radius=4,
                )
            )
        
        add_button = ft.FilledButton(
            "➕ Add New User",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
            on_click=lambda e: self.open_add_user_modal(page),
            visible=is_admin,
        )
        
        users_panel = ft.Container(
            content=ft.Column([header_row, table_rows], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(5 * scale),
        )
        
        # Main content
        content = ft.Column([
            ft.Row([
                ft.Text("Users Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                add_button,
            ]),
            ft.Container(height=int(12 * scale)),
            stats_row,
            ft.Container(height=int(15 * scale)),
            users_panel,
        ], expand=True)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # Combine with sidebar
        users_layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        page.add(users_layout)
        
        self.current_view = "users"
        page.update()
    
    def show_settings(self, page: ft.Page):
        """Show settings screen - FULL SCREEN like dashboard"""
        page.controls.clear()
        
        sidebar = self.create_sidebar(page)
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(28 * scale)
        font_normal = int(16 * scale)
        font_small = int(14 * scale)
        
        # Settings sections
        settings_sections = ft.Column([
            # Profile Section
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 Profile", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Row([
                        ft.Icon(ft.icons.PERSON, size=int(40 * scale)),
                        ft.Column([
                            ft.Text(f"Name: {self.current_user.get('name', 'User')}", size=font_small),
                            ft.Text(f"Email: {self.current_user.get('email', 'N/A')}", size=font_small),
                            ft.Text(f"Role: {self.current_user.get('role', 'user').upper()}", size=font_small),
                        ], spacing=int(5 * scale)),
                    ], spacing=int(15 * scale)),
                    ft.TextButton("Edit Profile", on_click=lambda e: None),
                ]),
                padding=int(15 * scale),
                bgcolor=self.card_color,
                border_radius=10,
            ),
            
            # Security Section
            ft.Container(
                content=ft.Column([
                    ft.Text("🔐 Security", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.TextButton("Change Password", on_click=lambda e: None),
                    ft.TextButton("Two-Factor Authentication", on_click=lambda e: None),
                ]),
                padding=int(15 * scale),
                bgcolor=self.card_color,
                border_radius=10,
            ),
            
            # Database Section
            ft.Container(
                content=ft.Column([
                    ft.Text("💾 Database", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.TextButton("Backup Database", on_click=lambda e: None),
                    ft.TextButton("Restore Database", on_click=lambda e: None),
                    ft.TextButton("Export All Data", on_click=lambda e: None),
                ]),
                padding=int(15 * scale),
                bgcolor=self.card_color,
                border_radius=10,
            ),
            
            # Appearance Section
            ft.Container(
                content=ft.Column([
                    ft.Text("🎨 Appearance", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Text("Theme: Dark Mode", size=font_small),
                    ft.Text("Accent Color: Blue", size=font_small),
                ]),
                padding=int(15 * scale),
                bgcolor=self.card_color,
                border_radius=10,
            ),
        ], spacing=int(15 * scale))
        
        # Main content
        content = ft.Column([
            ft.Text("Settings", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(height=int(15 * scale)),
            ft.Row([
                ft.Container(content=settings_sections, expand=True),
            ], expand=True),
        ], expand=True, scroll=ft.ScrollMode.AUTO)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # Combine with sidebar
        settings_layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        page.add(settings_layout)
        
        self.current_view = "settings"
        page.update()
    
    def show_barcode_scanner(self, page: ft.Page):
        """Show barcode scanner - FULL SCREEN like dashboard"""
        page.controls.clear()
        
        sidebar = self.create_sidebar(page)
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(28 * scale)
        font_normal = int(16 * scale)
        font_small = int(14 * scale)
        font_stats = int(24 * scale)
        
        # Scanner state
        scanner = None
        is_scanning = False
        current_item = None
        
        # Statistics counters
        today_scans = 0
        found_items = 0
        not_found_items = 0
        
        # UI Components
        barcode_input = ft.TextField(
            hint_text="Enter barcode number",
            width=int(400 * scale),
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_align=ft.TextAlign.CENTER,
            text_size=int(16 * scale),
        )
        
        scan_result_container = ft.Container(
            content=ft.Column([
                ft.Text("No item scanned yet", size=font_normal, color="#888888", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=int(15 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            height=int(300 * scale),
        )
        
        history_list = ft.Column(spacing=int(3 * scale), scroll=ft.ScrollMode.AUTO, height=int(120 * scale))
        
        status_text = ft.Text("Ready", size=font_small, color="#888888")
        
        # Stats display
        stats_today = ft.Text("0", size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color)
        stats_found = ft.Text("0", size=font_stats, weight=ft.FontWeight.BOLD, color=self.success_color)
        stats_not_found = ft.Text("0", size=font_stats, weight=ft.FontWeight.BOLD, color=self.danger_color)
        
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
                        ft.Text(f"🕐 {timestamp}", size=font_small - 2, color="#888888", width=int(65 * scale)),
                        ft.Text(f"{item_name[:30]}", size=font_small - 1, color=self.text_color, expand=True),
                        ft.Text(f"{barcode_val[-12:]}", size=font_small - 2, color="#888888", width=int(90 * scale)),
                        ft.Text(found_icon, size=font_small, width=int(25 * scale)),
                    ], spacing=int(8 * scale)),
                    padding=ft.padding.symmetric(vertical=int(6 * scale), horizontal=int(10 * scale)),
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
            item_type = "🔧 Accessory" if is_accessory else "📦 Material"
            
            qualities = ["New", "Used", "Damaged", "Repaired"]
            current_quality = item.get('quality', 'New')
            current_quantity = item.get('quantity', 0)
            
            quality_dropdown = ft.Dropdown(
                label="New Quality",
                width=int(120 * scale),
                options=[ft.dropdown.Option(q) for q in qualities],
                value=current_quality,
                bgcolor=self.card_color,
            )
            
            quantity_field = ft.TextField(
                label="Remove",
                width=int(90 * scale),
                value="0",
                bgcolor=self.card_color,
                keyboard_type=ft.KeyboardType.NUMBER,
                text_align=ft.TextAlign.CENTER,
            )
            
            note_field = ft.TextField(
                label="Note (optional)",
                width=int(250 * scale),
                multiline=True,
                min_lines=2,
                max_lines=2,
                bgcolor=self.card_color,
                text_size=font_small - 1,
            )
            
            def confirm_update(e):
                new_qty = 0
                try:
                    new_qty = int(quantity_field.value) if quantity_field.value else 0
                except ValueError:
                    new_qty = 0
                
                new_quality = quality_dropdown.value
                note = note_field.value
                
                if is_accessory:
                    current_qty = item.get('quantity', 0)
                    new_total = current_qty - new_qty if new_qty > 0 else current_qty
                    update_data = {'quantity': new_total, 'quality': new_quality}
                    if note:
                        existing_note = item.get('notes', '')
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                        update_data['notes'] = f"{existing_note}\n[{timestamp}] {note}" if existing_note else f"[{timestamp}] {note}"
                    result = AccessoryManager.update(item['id'], update_data)
                else:
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
            
            location_text = item.get('location', 'N/A') if is_accessory else item.get('location_ids', 'N/A')
            
            scan_result_container.content = ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("✅ ITEM FOUND", size=font_normal, weight=ft.FontWeight.BOLD, color=self.success_color),
                        ft.Container(expand=True),
                        ft.Text(item.get('name', 'N/A'), size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(bottom=8),
                ),
                ft.Divider(),
                ft.Row([ft.Text("Barcode:", size=font_small, color="#CCCCCC", width=int(60 * scale)), 
                    ft.Text(item.get('barcode_value') or item.get('item_code', 'N/A'), size=font_small, color=self.text_color)], spacing=int(8 * scale)),
                ft.Row([ft.Text("Type:", size=font_small, color="#CCCCCC", width=int(60 * scale)), 
                    ft.Text(item_type, size=font_small, color=self.text_color)], spacing=int(8 * scale)),
                ft.Row([ft.Text("Quality:", size=font_small, color="#CCCCCC", width=int(60 * scale)), 
                    ft.Container(content=ft.Text(item.get('quality', 'N/A'), size=font_small - 1, color="white"), 
                                bgcolor=self.get_quality_color(item.get('quality', 'Used')), 
                                border_radius=8, padding=ft.padding.symmetric(horizontal=int(8 * scale), vertical=int(3 * scale)))], spacing=int(8 * scale)),
                ft.Row([ft.Text("Quantity:", size=font_small, color="#CCCCCC", width=int(60 * scale)), 
                    ft.Text(str(item.get('quantity', 0)), size=font_small + 1, weight=ft.FontWeight.BOLD, color=self.text_color)], spacing=int(8 * scale)),
                ft.Row([ft.Text("Location:", size=font_small, color="#CCCCCC", width=int(60 * scale)), 
                    ft.Text(location_text, size=font_small, color=self.text_color)], spacing=int(8 * scale)),
                ft.Divider(),
                ft.Text("✏️ UPDATE STOCK", size=font_small, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Row([quantity_field, quality_dropdown], spacing=int(10 * scale), wrap=True),
                note_field,
                ft.Row([
                    ft.FilledButton("✅ UPDATE", on_click=confirm_update, width=int(110 * scale), height=int(40 * scale), 
                                style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ft.OutlinedButton("❌ CANCEL", on_click=lambda e: display_item_details(item), 
                                    width=int(110 * scale), height=int(40 * scale)),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=int(20 * scale)),
            ], spacing=int(8 * scale), scroll=ft.ScrollMode.AUTO, height=int(300 * scale))
            scan_result_container.height = None
            page.update()
        
        def display_not_found(barcode_val):
            scan_result_container.content = ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("⚠️ ITEM NOT FOUND", size=font_normal, weight=ft.FontWeight.BOLD, color=self.warning_color),
                        ft.Text("❌", size=font_normal + 4),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(bottom=8),
                ),
                ft.Divider(),
                ft.Text(f"Barcode: {barcode_val}", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Text("No item found in database with this barcode.", size=font_small, color="#888888"),
                ft.Text("You can add this item from the Materials or Accessories screen.", 
                    size=font_small - 1, color="#888888", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=int(10 * scale))
            scan_result_container.height = int(200 * scale)
            page.update()
        
        def on_barcode_detected(barcode_val):
            search_barcode(barcode_val)
        
        def start_camera(e):
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
        
        def stop_camera(e):
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
        start_btn = ft.ElevatedButton("▶ START CAMERA", on_click=start_camera, 
                                    style=ft.ButtonStyle(bgcolor=self.success_color))
        stop_btn = ft.ElevatedButton("⏹ STOP CAMERA", on_click=stop_camera, visible=False,
                                    style=ft.ButtonStyle(bgcolor=self.danger_color))
        
        # Stats row
        stats_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 Today's Scans", size=font_small, color="#CCCCCC"),
                        stats_today,
                        ft.Text("Total scans today", size=font_small - 2, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=int(3 * scale)),
                    padding=int(12 * scale),
                    bgcolor=self.card_color,
                    border_radius=12,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("✅ Found Items", size=font_small, color="#CCCCCC"),
                        stats_found,
                        ft.Text("Successfully found", size=font_small - 2, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=int(3 * scale)),
                    padding=int(12 * scale),
                    bgcolor=self.card_color,
                    border_radius=12,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("❌ Not Found", size=font_small, color="#CCCCCC"),
                        stats_not_found,
                        ft.Text("Items not in database", size=font_small - 2, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=int(3 * scale)),
                    padding=int(12 * scale),
                    bgcolor=self.card_color,
                    border_radius=12,
                    expand=True,
                ),
            ],
            spacing=int(15 * scale),
        )
        
        # Barcode input section
        barcode_section = ft.Container(
            content=ft.Column([
                ft.Text("📷 Barcode Scanner", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Text("Scan a product barcode to view details or update stock", size=font_small - 1, color="#888888"),
                ft.Container(height=int(8 * scale)),
                barcode_input,
                ft.Row([
                    ft.ElevatedButton("🔍 SCAN", on_click=scan_action, icon=ft.icons.SEARCH, 
                                    style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    start_btn,
                    stop_btn,
                    ft.ElevatedButton("📋 PASTE", on_click=paste_action, icon=ft.icons.CONTENT_PASTE,
                                    style=ft.ButtonStyle(bgcolor=self.warning_color)),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=int(12 * scale)),
                ft.Text("Or use camera to scan barcode (if available)", size=font_small - 2, color="#888888"),
            ], spacing=int(8 * scale), horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=int(15 * scale),
            bgcolor=self.card_color,
            border_radius=12,
        )
        
        # Scan result section
        result_section = ft.Container(
            content=ft.Column([
                ft.Text("📋 Scan Result", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                scan_result_container,
            ], spacing=int(8 * scale)),
            padding=int(12 * scale),
            bgcolor=self.card_color,
            border_radius=12,
        )
        
        # History section
        history_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📜 Recent Scans", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.TextButton("Clear History", on_click=clear_history, style=ft.ButtonStyle(color=self.danger_color)),
                ]),
                ft.Container(content=history_list, height=int(130 * scale), bgcolor=self.card_color, border_radius=8, padding=5),
            ], spacing=int(8 * scale)),
            padding=int(12 * scale),
            bgcolor=self.card_color,
            border_radius=12,
        )
        
        # Main content
        main_content = ft.Column([
            ft.Text("📷 BARCODE SCANNER", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(height=int(12 * scale)),
            stats_row,
            ft.Container(height=int(15 * scale)),
            barcode_section,
            ft.Container(height=int(15 * scale)),
            result_section,
            ft.Container(height=int(15 * scale)),
            history_section,
            ft.Container(height=int(10 * scale)),
            status_text,
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        main_container = ft.Container(content=main_content, expand=True, padding=padding_size)
        
        # Combine with sidebar
        barcode_layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        page.add(barcode_layout)
        
        self.current_view = "barcode_scanner"
        page.update()
    
    def show_no_permission(self, page: ft.Page):
        page.snack_bar = ft.SnackBar(ft.Text("❌ No permission"), bgcolor=self.danger_color)
        page.snack_bar.open = True
        page.update()
    
    def has_permission(self, permission):
        if not self.current_user:
            return False
        role = self.current_user.get('role', 'user')
        is_guest = self.current_user.get('guest_mode', False)
        is_premium = self.current_user.get('is_premium', False)
        
        if is_premium:
            return True
        if is_guest:
            guest_permissions = ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'scan_barcode']
            return permission in guest_permissions
        
        permissions = {
            'admin': ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'view_users', 'view_settings',
                      'add_material', 'edit_material', 'delete_material', 'add_accessory', 'edit_accessory', 'delete_accessory',
                      'add_user', 'edit_user', 'delete_user', 'export_reports', 'scan_barcode'],
            'manager': ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'view_users', 'view_settings',
                        'add_material', 'edit_material', 'delete_material', 'add_accessory', 'edit_accessory', 'delete_accessory',
                        'export_reports', 'scan_barcode'],
            'user': ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'scan_barcode']
        }
        return permission in permissions.get(role, [])
    
    def show_forgot_password(self, page: ft.Page):
        page.snack_bar = ft.SnackBar(ft.Text("Password reset - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()
    
    def show_upgrade_screen(self, page: ft.Page):
        page.controls.clear()
        page.add(ft.Text("Trial Expired", size=30, color=self.danger_color))
        page.update()
    
    def show_barcode_dialog(self, page: ft.Page, item):
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        barcode_image_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_text}&code=Code128&dpi=120"
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Barcode"),
            content=ft.Column([
                ft.Image(src=barcode_image_url, width=300, height=100),
                ft.Text(barcode_text, size=16, weight=ft.FontWeight.BOLD),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[ft.TextButton("Close", on_click=close_dialog)],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()


# Run the app
if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
