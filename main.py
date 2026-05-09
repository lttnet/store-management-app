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
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        content = ft.Text("Materials Screen", size=30, weight=ft.FontWeight.BOLD)
        desktop_layout = ft.Row([sidebar, ft.Container(content=content, expand=True, padding=20)], spacing=0, expand=True)
        
        if self.scale_helper and self.scale_helper.scale < 1.0:
            scaled_content = ft.Container(content=desktop_layout, scale=ft.Scale(self.scale_helper.scale), expand=True, alignment=ft.alignment.center)
            page.add(scaled_content)
        else:
            page.add(desktop_layout)
        self.current_view = "materials"
        page.update()
    
    def show_accessories(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        content = ft.Text("Accessories Screen", size=30, weight=ft.FontWeight.BOLD)
        desktop_layout = ft.Row([sidebar, ft.Container(content=content, expand=True, padding=20)], spacing=0, expand=True)
        
        if self.scale_helper and self.scale_helper.scale < 1.0:
            scaled_content = ft.Container(content=desktop_layout, scale=ft.Scale(self.scale_helper.scale), expand=True, alignment=ft.alignment.center)
            page.add(scaled_content)
        else:
            page.add(desktop_layout)
        self.current_view = "accessories"
        page.update()
    
    def show_inventory(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        content = ft.Text("Inventory Screen", size=30, weight=ft.FontWeight.BOLD)
        desktop_layout = ft.Row([sidebar, ft.Container(content=content, expand=True, padding=20)], spacing=0, expand=True)
        
        if self.scale_helper and self.scale_helper.scale < 1.0:
            scaled_content = ft.Container(content=desktop_layout, scale=ft.Scale(self.scale_helper.scale), expand=True, alignment=ft.alignment.center)
            page.add(scaled_content)
        else:
            page.add(desktop_layout)
        self.current_view = "inventory"
        page.update()
    
    def show_users(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        content = ft.Text("Users Management", size=30, weight=ft.FontWeight.BOLD)
        desktop_layout = ft.Row([sidebar, ft.Container(content=content, expand=True, padding=20)], spacing=0, expand=True)
        
        if self.scale_helper and self.scale_helper.scale < 1.0:
            scaled_content = ft.Container(content=desktop_layout, scale=ft.Scale(self.scale_helper.scale), expand=True, alignment=ft.alignment.center)
            page.add(scaled_content)
        else:
            page.add(desktop_layout)
        self.current_view = "users"
        page.update()
    
    def show_settings(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        content = ft.Text("Settings", size=30, weight=ft.FontWeight.BOLD)
        desktop_layout = ft.Row([sidebar, ft.Container(content=content, expand=True, padding=20)], spacing=0, expand=True)
        
        if self.scale_helper and self.scale_helper.scale < 1.0:
            scaled_content = ft.Container(content=desktop_layout, scale=ft.Scale(self.scale_helper.scale), expand=True, alignment=ft.alignment.center)
            page.add(scaled_content)
        else:
            page.add(desktop_layout)
        self.current_view = "settings"
        page.update()
    
    def show_barcode_scanner(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        content = ft.Text("Barcode Scanner", size=30, weight=ft.FontWeight.BOLD)
        desktop_layout = ft.Row([sidebar, ft.Container(content=content, expand=True, padding=20)], spacing=0, expand=True)
        
        if self.scale_helper and self.scale_helper.scale < 1.0:
            scaled_content = ft.Container(content=desktop_layout, scale=ft.Scale(self.scale_helper.scale), expand=True, alignment=ft.alignment.center)
            page.add(scaled_content)
        else:
            page.add(desktop_layout)
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
