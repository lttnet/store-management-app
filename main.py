"""Store Management App - Mobile Compatible Build with Responsive Layout"""
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

# ============ RESPONSIVE HELPER CLASS ============
class ResponsiveHelper:
    def __init__(self, page: ft.Page):
        self.page = page
        self.update()
    
    def update(self):
        width = self.page.width if self.page.width else 1200
        # For landscape mode, use width to determine device type
        # On mobile in landscape, width is typically > 600
        self.is_mobile = width < 800  # Landscape tablets are usually wider
        self.is_tablet = 800 <= width < 1200
        self.is_desktop = width >= 1200
        # Smaller sidebar on mobile landscape
        self.sidebar_width = 200 if self.is_mobile else 250
    
    def get_padding(self):
        # Smaller padding on mobile landscape
        return 10 if self.is_mobile else 20
    
    def get_font_size(self, desktop_size):
        if self.is_mobile:
            return desktop_size - 2  # Less reduction for landscape
        return desktop_size
    
    def get_spacing(self):
        return 10 if self.is_mobile else 15
    
    def get_sidebar_visible(self):
        # Always show sidebar on landscape (it fits)
        return True


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
        self.responsive = None
        self.bottom_nav = None
        
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
        
    def main(self, page: ft.Page):
        """Main entry point with landscape orientation support"""
        
        # Initialize responsive helper
        self.responsive = ResponsiveHelper(page)
        
        # FORCE LANDSCAPE/HORIZONTAL ORIENTATION
        # This keeps your desktop layout usable on mobile
        if self.responsive.is_mobile:
            # Mobile landscape settings
            page.window_maximized = True
            page.window_width = None  # Auto full width
            page.window_height = None  # Auto full height
            page.window_min_width = 600
            page.window_min_height = 400
            page.window_max_width = None
            page.window_max_height = None
        else:
            # Desktop original settings
            page.window_width = 1600
            page.window_height = 900
            page.window_min_width = 1200
            page.window_min_height = 700
        
        # Page settings
        page.title = "Store Management System"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = self.bg_color
        page.padding = 0
        page.spacing = 0
        
        # Prevent window from being resized too small
        page.window_resizable = True
        
        # Handle resize events to maintain responsiveness
        def on_resize(e):
            self.responsive.update()
            # Refresh current view on resize
            if self.current_user:
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
                elif self.current_view == "barcode_scanner":
                    self.show_barcode_scanner(page)
            page.update()
        
        page.on_resize = on_resize
        
        # Initialize database and show login
        init_database()
        self.show_login(page)
        page.update()
    
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
    
    def show_login(self, page: ft.Page):
        """Show login screen - optimized for landscape orientation"""
        page.controls.clear()
        
        # Calculate responsive field width based on screen size
        if self.responsive and self.responsive.is_mobile:
            field_width = min(page.width - 100, 350) if page.width else 280
        else:
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
        
        logo_exists = os.path.exists(logo_path)
        
        def on_login(e):
            user = UserManager.authenticate(email_field.value, password_field.value)
            if user:
                user_dict = dict(user)
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
        
        logo = ft.Image(src=logo_path, width=100, height=100, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=60)
        
        # For landscape mode, use Row layout instead of Column for better fit
        if self.responsive and self.responsive.is_mobile and page.width and page.width < 800:
            # Landscape mobile layout - horizontal arrangement
            main_layout = ft.Row(
                [
                    ft.Container(
                        content=ft.Column([
                            logo,
                            ft.Container(height=20),
                            ft.FilledButton("Sign In", width=140, height=45, on_click=on_login),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        width=200,
                    ),
                    ft.VerticalDivider(width=20, color="#3C3C3C"),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Welcome", size=24, weight=ft.FontWeight.BOLD, color=self.text_color),
                            ft.Text("Sign in to manage your inventory", size=12, color="#AAAAAA"),
                            ft.Container(height=15),
                            email_field,
                            ft.Container(height=10),
                            password_field,
                            ft.Container(height=10),
                            status_text,
                            ft.Container(height=10),
                            ft.OutlinedButton("Guest", width=field_width, height=40, on_click=on_guest_login),
                            ft.TextButton("Forgot Password?", on_click=lambda e: self.show_forgot_password(page)),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        expand=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            login_card = ft.Container(content=main_layout, padding=30, border_radius=20, width=min(700, page.width - 40))
        else:
            # Desktop/Tablet layout - vertical centered
            main_layout = ft.Column(
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
                    ft.Row([logo, ft.Container(width=20), ft.FilledButton("Sign In", width=140, height=45, on_click=on_login)], 
                        alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=20, color="#3C3C3C"),
                    ft.OutlinedButton("Continue as Guest", width=field_width, height=40, on_click=on_guest_login),
                    ft.Container(height=10),
                    ft.TextButton("Forgot Password?", on_click=lambda e: self.show_forgot_password(page), style=ft.ButtonStyle(color="#888888")),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            )
            login_card = ft.Container(content=main_layout, padding=40, border_radius=20, width=min(500, page.width - 40))
        
        centered_login = ft.Container(content=login_card, alignment=ft.alignment.center, expand=True)
        
        bg_image = ft.Image(src=background_path, fit=ft.ImageFit.COVER) if os.path.exists(background_path) else None
        
        if bg_image:
            page.add(ft.Stack([bg_image, centered_login], expand=True))
        else:
            page.add(centered_login)
        page.update()
    
    def guest_login(self, page):
        self.current_user = {'id': 0, 'name': 'Guest', 'email': 'guest@store.com', 'role': 'guest', 'guest_mode': True}
        self.show_dashboard(page)
    
    def free_trial(self, page):
        import datetime
        trial_end = datetime.datetime.now() + datetime.timedelta(days=14)
        self.current_user = {
            'id': 0,
            'name': 'Trial User',
            'email': 'trial@store.com',
            'role': 'trial',
            'trial_mode': True,
            'trial_end_date': trial_end.strftime('%Y-%m-%d'),
            'is_premium': False
        }
        self.show_dashboard(page)
    
    def create_bottom_nav(self, page: ft.Page):
        nav_items = [
            (ft.icons.DASHBOARD, "Home", "dashboard"),
            (ft.icons.INVENTORY, "Materials", "materials"),
            (ft.icons.BUILD, "Parts", "accessories"),
            (ft.icons.QR_CODE_SCANNER, "Scan", "barcode_scanner"),
            (ft.icons.PEOPLE, "Users", "users"),
            (ft.icons.SETTINGS, "Settings", "settings"),
        ]
        
        def navigate(e):
            view = nav_items[e.control.selected_index][2]
            if view == "dashboard":
                self.show_dashboard(page)
            elif view == "materials":
                self.show_materials_screen(page)
            elif view == "accessories":
                self.show_accessories(page)
            elif view == "barcode_scanner":
                self.show_barcode_scanner(page)
            elif view == "users":
                self.show_users(page)
            elif view == "settings":
                self.show_settings(page)
        
        self.bottom_nav = ft.NavigationBar(
            destinations=[ft.NavigationDestination(icon=icon, label=label) for icon, label, _ in nav_items],
            on_change=navigate,
            height=65,
            bgcolor=self.sidebar_color,
        )
        return self.bottom_nav
    
    def create_sidebar(self, page: ft.Page):
        # On mobile, return bottom navigation instead
        if self.responsive and self.responsive.is_mobile:
            return self.create_bottom_nav(page)
        
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
                    content=ft.Row([ft.Text(emoji, size=20), ft.Text(label, size=14, color=self.text_color)], spacing=10),
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
        
        logo_exists = os.path.exists(logo_path)
        sidebar_logo = ft.Image(src=logo_path, width=30, height=30, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=24)
        
        title_content = ft.Row(
            [sidebar_logo, ft.Text("Store Manager", size=18, weight=ft.FontWeight.BOLD, color=self.text_color)],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5,
        )
        
        role = self.current_user.get('role', 'guest') if self.current_user else 'guest'
        role_display = "💎 PREMIUM" if self.current_user and self.current_user.get('is_premium') else role.upper()
        
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
                                ft.Text(f"User: {self.current_user.get('name', 'User') if self.current_user else 'Guest'}", size=10, color="#888888", text_align=ft.TextAlign.CENTER),
                                ft.Text(role_display, size=10, weight=ft.FontWeight.BOLD, color=self.success_color, text_align=ft.TextAlign.CENTER),
                            ],
                            spacing=3,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=10,
                    ),
                ],
                spacing=0,
            ),
            width=self.responsive.sidebar_width if self.responsive else 250,
            bgcolor=self.sidebar_color,
        )
    
    def show_no_permission(self, page: ft.Page):
        page.snack_bar = ft.SnackBar(ft.Text("❌ No permission"), bgcolor=self.danger_color)
        page.snack_bar.open = True
        page.update()
    
    def has_permission(self, permission):
        if not self.current_user:
            return False
        role = self.current_user.get('role', 'user')
        is_guest = self.current_user.get('guest_mode', False)
        is_trial = self.current_user.get('trial_mode', False)
        is_premium = self.current_user.get('is_premium', False)
        
        if is_premium:
            return True
        if is_guest or is_trial:
            guest_permissions = ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'scan_barcode']
            return permission in guest_permissions
        
        permissions = {
            'admin': ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'view_users', 'view_settings',
                      'add_material', 'edit_material', 'delete_material', 'add_accessory', 'edit_accessory', 'delete_accessory',
                      'add_user', 'edit_user', 'delete_user', 'export_reports', 'scan_barcode'],
            'manager': ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'view_users', 'view_settings',
                        'add_material', 'edit_material', 'delete_material', 'add_accessory', 'edit_accessory', 'delete_accessory', 'export_reports', 'scan_barcode'],
            'user': ['view_dashboard', 'view_materials', 'view_accessories', 'view_inventory', 'scan_barcode']
        }
        return permission in permissions.get(role, [])
    
    def show_dashboard(self, page: ft.Page):
        # Trial expiration check
        if self.current_user and self.current_user.get('trial_mode', False):
            trial_end_str = self.current_user.get('trial_end_date')
            if trial_end_str:
                trial_end_date = datetime.strptime(trial_end_str, '%Y-%m-%d')
                if datetime.now().date() > trial_end_date.date():
                    self.show_upgrade_screen(page)
                    return
        
        page.controls.clear()
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        stats = MaterialManager.get_stats()
        accessory_stats = AccessoryManager.get_stats()
        low_stock = self.dict_list(MaterialManager.get_low_stock(10))
        
        sidebar = self.create_sidebar(page)
        padding = self.responsive.get_padding() if self.responsive else 20
        
        # Stats row - responsive
        stats_row = ft.ResponsiveRow(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("📦 Total Materials", size=self.responsive.get_font_size(14) if self.responsive else 14, color="#CCCCCC"),
                        ft.Text(str(stats.get('total_items', 0)), size=self.responsive.get_font_size(32) if self.responsive else 36, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=padding,
                    bgcolor=self.success_color,
                    border_radius=10,
                    col={"xs": 12, "sm": 6, "md": 4},
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🔧 Accessories", size=self.responsive.get_font_size(14) if self.responsive else 14, color="#CCCCCC"),
                        ft.Text(str(accessory_stats.get('total_items', 0)), size=self.responsive.get_font_size(32) if self.responsive else 36, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=padding,
                    bgcolor=self.accent_color,
                    border_radius=10,
                    col={"xs": 12, "sm": 6, "md": 4},
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📄 Export Records", size=self.responsive.get_font_size(14) if self.responsive else 14, color="#CCCCCC"),
                        ft.Text("120", size=self.responsive.get_font_size(32) if self.responsive else 36, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=padding,
                    bgcolor=self.warning_color,
                    border_radius=10,
                    col={"xs": 12, "sm": 12, "md": 4},
                ),
            ],
            spacing=15,
        )
        
        # Materials Table Panel
        materials_rows = []
        for m in materials[:10]:
            materials_rows.append(
                ft.Row([
                    ft.Text(m.get('name', 'N/A'), size=self.responsive.get_font_size(12) if self.responsive else 12, width=140),
                    ft.Text(m.get('location_ids') or "N/A", size=self.responsive.get_font_size(12) if self.responsive else 12, width=90),
                    ft.Text(m.get('size') or "N/A", size=self.responsive.get_font_size(12) if self.responsive else 12, width=80),
                    ft.Container(
                        content=ft.Text(m.get('quality', 'Used'), size=10, color="white"),
                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        width=70,
                    ),
                    ft.Text(str(m.get('quantity', 0)), size=self.responsive.get_font_size(12) if self.responsive else 12, width=55),
                ], alignment=ft.MainAxisAlignment.START)
            )
        
        if not materials_rows:
            materials_rows.append(ft.Text("No materials found", size=12, color="#888888"))
        
        materials_table = ft.Column([
            ft.Row([ft.Text("Materials", size=16, weight=ft.FontWeight.BOLD, color=self.text_color), ft.Container(expand=True), ft.TextButton("View All", on_click=lambda e: self.show_materials_screen(page))]),
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
        
        left_panel = ft.Container(content=materials_table, padding=12, bgcolor=self.card_color, border_radius=10, expand=True)
        
        # Accessories Table Panel
        accessories_rows = []
        for a in accessories[:10]:
            accessories_rows.append(
                ft.Row([
                    ft.Text("🖼️" if a.get('image_path') else "📷", size=12, width=30),
                    ft.Text(a.get('name', 'N/A'), size=self.responsive.get_font_size(12) if self.responsive else 12, width=140),
                    ft.Text(str(a.get('quantity', 0)), size=self.responsive.get_font_size(12) if self.responsive else 12, width=70),
                    ft.Container(
                        content=ft.Text(a.get('quality', 'Used'), size=10, color="white"),
                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        width=70,
                    ),
                    ft.Text("View", size=10, color=self.accent_color, width=50),
                ], alignment=ft.MainAxisAlignment.START)
            )
        
        if not accessories_rows:
            accessories_rows.append(ft.Text("No accessories found", size=12, color="#888888"))
        
        accessories_table = ft.Column([
            ft.Row([ft.Text("Accessories & Parts", size=16, weight=ft.FontWeight.BOLD, color=self.text_color), ft.Container(expand=True), ft.TextButton("View All", on_click=lambda e: self.show_accessories(page))]),
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
        
        right_panel = ft.Container(content=accessories_table, padding=12, bgcolor=self.card_color, border_radius=10, expand=True)
        
        # Middle row - responsive
        if self.responsive and self.responsive.is_mobile:
            middle_row = ft.Column([left_panel, ft.Container(height=15), right_panel], expand=True)
        else:
            middle_row = ft.Row([left_panel, right_panel], spacing=15, expand=True, height=380)
        
        # Low Stock Panel
        low_stock_materials = [m for m in materials if m.get('quantity', 0) < 10]
        low_stock_accessories = [a for a in accessories if a.get('quantity', 0) < 10]
        
        all_low_stock = []
        for m in low_stock_materials:
            all_low_stock.append({'name': m.get('name', 'Unknown'), 'quantity': m.get('quantity', 0), 'type': '📦'})
        for a in low_stock_accessories:
            all_low_stock.append({'name': a.get('name', 'Unknown'), 'quantity': a.get('quantity', 0), 'type': '🔧'})
        
        all_low_stock.sort(key=lambda x: x['quantity'])
        top_low_stock = all_low_stock[:15]
        max_qty = max([item['quantity'] for item in top_low_stock]) if top_low_stock else 10
        
        chart_items = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=180)
        
        if top_low_stock:
            for item in top_low_stock:
                percentage = (item['quantity'] / max_qty) * 100
                bar_color = self.danger_color if item['quantity'] < 5 else self.warning_color
                chart_items.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item['type'], size=14, width=30),
                                ft.Text(item['name'][:25], size=12, color=self.text_color, width=150),
                                ft.Text(f"Stock: {item['quantity']}", size=11, color=bar_color, width=80),
                                ft.Container(expand=True),
                                ft.Text(f"{percentage:.0f}%", size=10, width=40, color="#888888"),
                            ]),
                            ft.ProgressBar(value=item['quantity'] / max_qty, color=bar_color, bgcolor="#3C3C3C", height=8),
                        ], spacing=5),
                        padding=ft.padding.symmetric(vertical=4, horizontal=5),
                    )
                )
        else:
            chart_items.controls.append(ft.Container(content=ft.Text("✅ No low stock items!", size=12, color=self.success_color), padding=20, alignment=ft.alignment.center))
        
        low_stock_panel = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("⚠️ Low Stock Items", size=16, weight=ft.FontWeight.BOLD, color=self.text_color), ft.Container(expand=True), ft.Text(f"Total: {len(low_stock_materials) + len(low_stock_accessories)} items", size=11, color="#888888")]),
                ft.Divider(height=1, color="#3C3C3C"),
                ft.Container(height=5),
                chart_items,
            ], spacing=8),
            padding=9,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Import/Export Panel
        import_panel = ft.Container(
            content=ft.Column([
                ft.Text("📁 Import/Export Management", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(height=1, color="#3C3C3C"),
                ft.Container(height=5),
                ft.Row([
                    ft.ElevatedButton("📥 Import", on_click=lambda e: None, style=ft.ButtonStyle(bgcolor=self.accent_color, padding=10)),
                    ft.ElevatedButton("📤 Export", on_click=lambda e: None, style=ft.ButtonStyle(bgcolor=self.warning_color, padding=10)),
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=10),
                ft.Text("Click Import to paste CSV data", size=11, color="#888888"),
                ft.Text("Supported formats: CSV", size=10, color="#888888"),
                ft.Container(expand=True),
            ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Users Panel
        users = self.dict_list(UserManager.get_all())
        users_panel = ft.Container(
            content=ft.Column(
                [ft.Text("👥 Users & Permissions", size=16, weight=ft.FontWeight.BOLD, color=self.text_color), ft.Divider(height=1, color="#3C3C3C"), ft.Container(height=5)] +
                [ft.Row([ft.Text(u.get('name', 'N/A'), size=12, weight=ft.FontWeight.BOLD, width=100), ft.Text(u.get('role', 'user'), size=11, color="#4CAF50", width=70), ft.Text("Active", size=11, color="#4CAF50")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN) for u in users[:5]] +
                [ft.Container(expand=True)],
                spacing=8,
            ),
            padding=15,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Bottom row - responsive
        if self.responsive and self.responsive.is_mobile:
            bottom_row = ft.Column([low_stock_panel, ft.Container(height=15), import_panel, ft.Container(height=15), users_panel], expand=True)
        else:
            bottom_row = ft.Row([low_stock_panel, import_panel, users_panel], spacing=15, expand=True, height=260)
        
        # Main content
        main_content = ft.Container(
            content=ft.Column([
                ft.Text("Dashboard", size=self.responsive.get_font_size(28) if self.responsive else 28, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=15),
                stats_row,
                ft.Container(height=15),
                middle_row,
                ft.Container(height=15),
                bottom_row,
            ], spacing=5, expand=True),
            expand=True,
            padding=padding,
        )
        
        # Add to page
        if self.responsive and self.responsive.is_mobile and hasattr(self, 'bottom_nav'):
            page.add(ft.Column([main_content, self.bottom_nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        
        self.current_view = "dashboard"
        page.update()
    
    def show_materials_screen(self, page: ft.Page):
        page.controls.clear()
        self.page_ref = page
        materials = self.dict_list(MaterialManager.get_all())
        sidebar = self.create_sidebar(page)
        padding = self.responsive.get_padding() if self.responsive else 20
        is_mobile = self.responsive.is_mobile if self.responsive else False
        
        # Search and filters
        search_field = ft.TextField(hint_text="Search...", width=180 if not is_mobile else 150, bgcolor=self.card_color, border_color=self.accent_color,
                                    on_change=lambda e: self.search_materials_table(page, e.control.value))
        
        self.filter_buttons = {}
        def create_filter_button(label, color, filter_type):
            btn = ft.Container(content=ft.Text(label, size=13 if not is_mobile else 11, weight=ft.FontWeight.BOLD, color=self.text_color),
                               padding=ft.padding.symmetric(horizontal=15 if not is_mobile else 10, vertical=8), bgcolor=self.card_color, border_radius=20, ink=True,
                               on_click=lambda e, f=filter_type: self.filter_materials(page, f))
            self.filter_buttons[filter_type] = btn
            return btn
        
        filter_buttons = ft.Row([create_filter_button("All", self.accent_color, "All"), create_filter_button("New", self.success_color, "New"),
                                  create_filter_button("Used", self.warning_color, "Used"), create_filter_button("Damaged", self.danger_color, "Damaged"),
                                  create_filter_button("Repaired", self.accent_color, "Repaired")], spacing=8 if is_mobile else 10, wrap=True)
        
        if "All" in self.filter_buttons:
            self.filter_buttons["All"].bgcolor = self.accent_color
        
        add_button = ft.FilledButton("➕ Add Material", on_click=lambda e: self.open_add_modal(page), style=ft.ButtonStyle(bgcolor=self.success_color))
        
        # Table header
        header_row = ft.Container(content=ft.Row([ft.Text("Image", size=11, weight=ft.FontWeight.BOLD, width=60), ft.Text("Name", size=11, weight=ft.FontWeight.BOLD, width=160),
                                                   ft.Text("Length", size=11, weight=ft.FontWeight.BOLD, width=60), ft.Text("Size", size=11, weight=ft.FontWeight.BOLD, width=80),
                                                   ft.Text("Qty", size=11, weight=ft.FontWeight.BOLD, width=50), ft.Text("Quality", size=11, weight=ft.FontWeight.BOLD, width=80),
                                                   ft.Text("Location", size=11, weight=ft.FontWeight.BOLD, width=100), ft.Text("Created", size=11, weight=ft.FontWeight.BOLD, width=100)],
                                                  alignment=ft.MainAxisAlignment.START), padding=ft.padding.symmetric(vertical=8, horizontal=10), bgcolor="#3C3C3C", border_radius=6)
        
        self.table_rows_container = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=450 if not is_mobile else 350)
        self.update_materials_table(materials)
        
        if is_mobile:
            table_container = ft.Container(content=ft.Column([header_row, self.table_rows_container], spacing=0), width=page.width - 40, overflow=ft.Overflow(horizontal=True))
            left_panel = ft.Container(content=table_container, expand=True, bgcolor=self.card_color, border_radius=10, padding=5)
        else:
            left_panel = ft.Container(content=ft.Column([header_row, self.table_rows_container], spacing=0), expand=True, bgcolor=self.card_color, border_radius=10, padding=5)
        
        self.detail_panel = ft.Container(content=self.create_detail_panel(None, page), width=320 if not is_mobile else None, bgcolor=self.card_color, border_radius=10, padding=15)
        
        if is_mobile:
            content = ft.Column([
                ft.Row([ft.Text("Materials", size=20, weight=ft.FontWeight.BOLD), ft.Container(expand=True), ft.Row([ft.Text("🔍", size=16), search_field], spacing=5)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=5), ft.Row([filter_buttons], alignment=ft.MainAxisAlignment.START), ft.Container(height=10),
                ft.Row([add_button], alignment=ft.MainAxisAlignment.END), ft.Container(height=15), left_panel, ft.Container(height=15), self.detail_panel
            ], expand=True, scroll=ft.ScrollMode.AUTO)
        else:
            content = ft.Column([
                ft.Row([ft.Text("Materials", size=24, weight=ft.FontWeight.BOLD), ft.Container(expand=True), ft.Row([ft.Text("🔍", size=16), search_field], spacing=5)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=5), ft.Row([filter_buttons, ft.Container(expand=True), add_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=15), ft.Row([left_panel, ft.Container(width=15), self.detail_panel], spacing=0, expand=True)
            ], expand=True)
        
        main_content = ft.Container(content=content, expand=True, padding=padding)
        
        if is_mobile and hasattr(self, 'bottom_nav'):
            page.add(ft.Column([main_content, self.bottom_nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        
        self.current_view = "materials"
        page.update()
    
    def update_materials_table(self, materials):
        self.table_rows_container.controls.clear()
        def format_datetime_short(date_value):
            if date_value:
                date_str = str(date_value)
                return date_str.split(' ')[0] if ' ' in date_str else (date_str[:10] if len(date_str) > 10 else date_str)
            return 'N/A'
        
        for m in materials:
            is_selected = self.selected_material_detail and self.selected_material_detail.get('id') == m.get('id')
            has_image = m.get('image_path') and os.path.exists(m.get('image_path', '')) if m.get('image_path') else False
            image_icon = "🖼️" if has_image else "📷"
            created_date = format_datetime_short(m.get('created_at', ''))
            
            row = ft.Container(content=ft.Row([ft.Text(image_icon, size=14, width=60), ft.Text(m.get('name', 'N/A'), size=11, width=160),
                                               ft.Text(str(m.get('length') or ""), size=11, width=60), ft.Text(m.get('size') or "N/A", size=11, width=80),
                                               ft.Text(str(m.get('quantity', 0)), size=11, width=50),
                                               ft.Container(content=ft.Text(m.get('quality', 'Used'), size=10, color="white"), bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                                           border_radius=8, padding=ft.padding.symmetric(horizontal=6, vertical=2), width=75),
                                               ft.Text(m.get('location_ids') or "N/A", size=11, width=100), ft.Text(created_date, size=10, width=100, color="#888888")],
                                              alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                               padding=ft.padding.symmetric(vertical=8, horizontal=10), bgcolor=self.accent_color if is_selected else ft.colors.TRANSPARENT,
                               border_radius=6, ink=True, on_click=lambda e, mat=m: self.on_material_select(mat))
            self.table_rows_container.controls.append(row)
    
    def search_materials_table(self, page: ft.Page, query):
        if not query:
            if self.current_filter == "All":
                materials = self.dict_list(MaterialManager.get_all())
            else:
                all_materials = self.dict_list(MaterialManager.get_all())
                materials = [m for m in all_materials if m.get('quality') == self.current_filter]
        else:
            searched_materials = self.dict_list(MaterialManager.search(query))
            materials = searched_materials if self.current_filter == "All" else [m for m in searched_materials if m.get('quality') == self.current_filter]
        self.update_materials_table(materials)
        page.update()
    
    def filter_materials(self, page: ft.Page, filter_type):
        self.current_filter = filter_type
        for btn, color in [("All", self.accent_color), ("New", self.success_color), ("Used", self.warning_color), ("Damaged", self.danger_color), ("Repaired", self.accent_color)]:
            if btn in self.filter_buttons:
                self.filter_buttons[btn].bgcolor = self.accent_color if btn == filter_type else self.card_color
        materials = self.dict_list(MaterialManager.get_all()) if filter_type == "All" else [m for m in self.dict_list(MaterialManager.get_all()) if m.get('quality') == filter_type]
        self.update_materials_table(materials)
        page.update()
    
    def on_material_select(self, material):
        self.selected_material_detail = material
        self.detail_panel.content = self.create_detail_panel(material, self.page_ref)
        self.page_ref.update()
        self.update_materials_table(self.dict_list(MaterialManager.get_all()))
    
    def create_detail_panel(self, material, page):
        if not material:
            return ft.Column([ft.Text("Material Details", size=18, weight=ft.FontWeight.BOLD), ft.Divider(), ft.Container(height=20),
                              ft.Text("Select a material to view details", size=12, color="#888888"), ft.Container(expand=True)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        has_image = material.get('image_path') and os.path.exists(material.get('image_path', '')) if material.get('image_path') else False
        
        return ft.Column([
            ft.Text(material.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD), ft.Divider(),
            ft.Row([ft.Text("📝 Code:", size=12, width=80), ft.Text(material.get('item_code') or "N/A", size=12)], spacing=5),
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, material))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.Text("🏷️ Quality:", size=12, width=80), ft.Container(content=ft.Text(material.get('quality', 'Used'), size=11, color="white"), bgcolor=self.get_quality_color(material.get('quality', 'Used')), border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))], spacing=5),
            ft.Row([ft.Text("📏 Size:", size=12, width=80), ft.Text(material.get('size') or "N/A", size=12)], spacing=5),
            ft.Row([ft.Text("🔢 Quantity:", size=12, width=80), ft.Text(str(material.get('quantity', 0)), size=12)], spacing=5),
            ft.Row([ft.Text("📍 Location:", size=12, width=80), ft.Text(material.get('location_ids') or "N/A", size=12)], spacing=5),
            ft.Row([ft.Text("📅 Created:", size=12, width=80), ft.Text(str(material.get('created_at', ''))[:10] if material.get('created_at') else 'N/A', size=12)], spacing=5),
            ft.Divider(), ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD), ft.Text(material.get('notes') or "No notes", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([ft.ElevatedButton("✏️ EDIT", on_click=lambda e: self.open_edit_modal(page, material['id']), style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    ft.ElevatedButton("🗑️ DELETE", on_click=lambda e: self.open_delete_modal(page, material['id']), style=ft.ButtonStyle(bgcolor=self.danger_color))],
                   alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def show_accessories(self, page: ft.Page):
        page.controls.clear()
        self.page_ref = page
        accessories = AccessoryManager.get_all()
        sidebar = self.create_sidebar(page)
        padding = self.responsive.get_padding() if self.responsive else 20
        is_mobile = self.responsive.is_mobile if self.responsive else False
        
        search_field = ft.TextField(hint_text="Search accessories...", width=180 if not is_mobile else 150, bgcolor=self.card_color, border_color=self.accent_color,
                                    on_change=lambda e: self.search_accessories_table(page, e.control.value))
        
        self.accessory_filter_buttons = {}
        def create_filter_button(label, color, filter_type):
            btn = ft.Container(content=ft.Text(label, size=13 if not is_mobile else 11, weight=ft.FontWeight.BOLD, color=self.text_color),
                               padding=ft.padding.symmetric(horizontal=15 if not is_mobile else 10, vertical=8), bgcolor=self.card_color if self.current_accessory_filter != filter_type else color,
                               border_radius=20, ink=True, on_click=lambda e, f=filter_type: self.filter_accessories(page, f))
            self.accessory_filter_buttons[filter_type] = btn
            return btn
        
        filter_buttons = ft.Row([create_filter_button("All", self.accent_color, "All"), create_filter_button("New", self.success_color, "New"),
                                  create_filter_button("Used", self.warning_color, "Used"), create_filter_button("Damaged", self.danger_color, "Damaged"),
                                  create_filter_button("Repaired", self.accent_color, "Repaired")], spacing=8 if is_mobile else 10, wrap=True)
        
        add_button = ft.FilledButton("➕ Add Accessory", on_click=lambda e: self.open_add_accessory_modal(page), style=ft.ButtonStyle(bgcolor=self.success_color))
        
        header_row = ft.Container(content=ft.Row([ft.Text("Image", size=11, weight=ft.FontWeight.BOLD, width=60), ft.Text("Name", size=11, weight=ft.FontWeight.BOLD, width=200),
                                                   ft.Text("Item Code", size=11, weight=ft.FontWeight.BOLD, width=120), ft.Text("Qty", size=11, weight=ft.FontWeight.BOLD, width=50),
                                                   ft.Text("Quality", size=11, weight=ft.FontWeight.BOLD, width=80), ft.Text("Location", size=11, weight=ft.FontWeight.BOLD, width=100),
                                                   ft.Text("Created", size=11, weight=ft.FontWeight.BOLD, width=110)], alignment=ft.MainAxisAlignment.START),
                                  padding=ft.padding.symmetric(vertical=8, horizontal=10), bgcolor="#3C3C3C", border_radius=6)
        
        self.accessory_rows_container = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=450 if not is_mobile else 350)
        self.update_accessories_table(accessories)
        
        if is_mobile:
            table_container = ft.Container(content=ft.Column([header_row, self.accessory_rows_container], spacing=0), width=page.width - 40, overflow=ft.Overflow(horizontal=True))
            left_panel = ft.Container(content=table_container, expand=True, bgcolor=self.card_color, border_radius=10, padding=5)
        else:
            left_panel = ft.Container(content=ft.Column([header_row, self.accessory_rows_container], spacing=0), expand=True, bgcolor=self.card_color, border_radius=10, padding=5)
        
        self.accessory_detail_panel = ft.Container(content=self.create_accessory_detail_panel(None, page), width=320 if not is_mobile else None, bgcolor=self.card_color, border_radius=10, padding=15)
        
        if is_mobile:
            content = ft.Column([
                ft.Row([ft.Text("Accessories & Parts", size=20, weight=ft.FontWeight.BOLD), ft.Container(expand=True), ft.Row([ft.Text("🔍", size=16), search_field], spacing=5)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=5), ft.Row([filter_buttons], alignment=ft.MainAxisAlignment.START), ft.Container(height=10),
                ft.Row([add_button], alignment=ft.MainAxisAlignment.END), ft.Container(height=15), left_panel, ft.Container(height=15), self.accessory_detail_panel
            ], expand=True, scroll=ft.ScrollMode.AUTO)
        else:
            content = ft.Column([
                ft.Row([ft.Text("Accessories & Parts", size=24, weight=ft.FontWeight.BOLD), ft.Container(expand=True), ft.Row([ft.Text("🔍", size=16), search_field], spacing=5)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=5), ft.Row([filter_buttons, ft.Container(expand=True), add_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=15), ft.Row([left_panel, ft.Container(width=15), self.accessory_detail_panel], spacing=0, expand=True)
            ], expand=True)
        
        main_content = ft.Container(content=content, expand=True, padding=padding)
        
        if is_mobile and hasattr(self, 'bottom_nav'):
            page.add(ft.Column([main_content, self.bottom_nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_content], spacing=0, expand=True))
        
        self.current_view = "accessories"
        page.update()
    
    def update_accessories_table(self, accessories):
        self.accessory_rows_container.controls.clear()
        for a in accessories:
            has_image = a.get('image_path') and os.path.exists(a.get('image_path', '')) if a.get('image_path') else False
            image_text = "🖼️" if has_image else "📷"
            location = a.get('location') or a.get('location_ids') or "N/A"
            created_date = str(a.get('created_at', ''))[:10] if a.get('created_at') else 'N/A'
            
            row = ft.Container(content=ft.Row([ft.Text(image_text, size=14, width=60), ft.Text(a.get('name', 'N/A'), size=11, width=200),
                                               ft.Text(a.get('item_code', 'N/A'), size=11, width=120), ft.Text(str(a.get('quantity', 0)), size=11, width=50),
                                               ft.Container(content=ft.Text(a.get('quality', 'Used'), size=10, color="white"), bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                                                           border_radius=8, padding=ft.padding.symmetric(horizontal=6, vertical=2), width=75),
                                               ft.Text(location, size=11, width=100), ft.Text(created_date, size=10, width=110, color="#888888")],
                                              alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                               padding=ft.padding.symmetric(vertical=8, horizontal=10), border_radius=6, ink=True,
                               on_click=lambda e, acc=a: self.on_accessory_select(acc))
            self.accessory_rows_container.controls.append(row)
    
    def search_accessories_table(self, page: ft.Page, query):
        if not query:
            accessories = self.dict_list(AccessoryManager.get_all()) if self.current_accessory_filter == "All" else [a for a in self.dict_list(AccessoryManager.get_all()) if a.get('quality') == self.current_accessory_filter]
        else:
            searched = self.dict_list(AccessoryManager.search(query))
            accessories = searched if self.current_accessory_filter == "All" else [a for a in searched if a.get('quality') == self.current_accessory_filter]
        self.update_accessories_table(accessories)
        page.update()
    
    def filter_accessories(self, page: ft.Page, filter_type):
        self.current_accessory_filter = filter_type
        for f_type, color in [("All", self.accent_color), ("New", self.success_color), ("Used", self.warning_color), ("Damaged", self.danger_color), ("Repaired", self.accent_color)]:
            if f_type in self.accessory_filter_buttons:
                self.accessory_filter_buttons[f_type].bgcolor = color if f_type == filter_type else self.card_color
        accessories = self.dict_list(AccessoryManager.get_all()) if filter_type == "All" else [a for a in self.dict_list(AccessoryManager.get_all()) if a.get('quality') == filter_type]
        self.update_accessories_table(accessories)
        page.update()
    
    def on_accessory_select(self, accessory):
        self.selected_accessory_detail = accessory
        self.accessory_detail_panel.content = self.create_accessory_detail_panel(accessory, self.page_ref)
        self.page_ref.update()
    
    def create_accessory_detail_panel(self, accessory, page):
        if not accessory:
            return ft.Column([ft.Text("Accessory Details", size=18, weight=ft.FontWeight.BOLD), ft.Divider(), ft.Container(height=20),
                              ft.Text("Select an accessory to view details", size=12, color="#888888"), ft.Container(expand=True)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        has_image = accessory.get('image_path') and os.path.exists(accessory.get('image_path', '')) if accessory.get('image_path') else False
        location = accessory.get('location') or accessory.get('location_ids') or "N/A"
        price_text = f"${accessory.get('price', 0):.2f}" if accessory.get('price') else "N/A"
        
        return ft.Column([
            ft.Text(accessory.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD), ft.Divider(),
            ft.Row([ft.Text("📝 Code:", size=12, width=80), ft.Text(accessory.get('item_code') or "N/A", size=12)], spacing=5),
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, accessory))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.Text("🏷️ Quality:", size=12, width=80), ft.Container(content=ft.Text(accessory.get('quality', 'Used'), size=11, color="white"), bgcolor=self.get_quality_color(accessory.get('quality', 'Used')), border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))], spacing=5),
            ft.Row([ft.Text("🔢 Quantity:", size=12, width=80), ft.Text(str(accessory.get('quantity', 0)), size=12)], spacing=5),
            ft.Row([ft.Text("💰 Price:", size=12, width=80), ft.Text(price_text, size=12)], spacing=5),
            ft.Row([ft.Text("📍 Location:", size=12, width=80), ft.Text(location, size=12)], spacing=5),
            ft.Row([ft.Text("📅 Created:", size=12, width=80), ft.Text(str(accessory.get('created_at', ''))[:10] if accessory.get('created_at') else 'N/A', size=12)], spacing=5),
            ft.Divider(), ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD), ft.Text(accessory.get('notes') or "No notes", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([ft.ElevatedButton("✏️ EDIT", on_click=lambda e: self.open_edit_accessory_modal(page, accessory['id']), style=ft.ButtonStyle(bgcolor=self.accent_color)),
                    ft.ElevatedButton("🗑️ DELETE", on_click=lambda e: self.open_delete_accessory_modal(page, accessory['id']), style=ft.ButtonStyle(bgcolor=self.danger_color))],
                   alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
    
    # Stub methods for other screens (implement as needed)
    def show_inventory(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Inventory Screen - Coming Soon", size=24)], expand=True))
        self.current_view = "inventory"
        page.update()
    
    def show_users(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Users Management - Coming Soon", size=24)], expand=True))
        self.current_view = "users"
        page.update()
    
    def show_settings(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Settings - Coming Soon", size=24)], expand=True))
        self.current_view = "settings"
        page.update()
    
    def show_barcode_scanner(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Barcode Scanner - Coming Soon", size=24)], expand=True))
        self.current_view = "barcode_scanner"
        page.update()
    
    def show_barcode_dialog(self, page: ft.Page, item):
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        item_name = item.get('name', 'Item')
        barcode_image_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_text}&code=Code128&dpi=120"
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Barcode: {item_name}"),
            content=ft.Column([
                ft.Image(src=barcode_image_url, width=300, height=100),
                ft.Text(barcode_text, size=16, weight=ft.FontWeight.BOLD),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[ft.TextButton("Close", on_click=close_dialog)],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def open_add_modal(self, page: ft.Page):
        page.snack_bar = ft.SnackBar(ft.Text("Add Material - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()
    
    def open_edit_modal(self, page: ft.Page, material_id):
        page.snack_bar = ft.SnackBar(ft.Text(f"Edit Material {material_id} - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()
    
    def open_delete_modal(self, page: ft.Page, material_id):
        page.snack_bar = ft.SnackBar(ft.Text(f"Delete Material {material_id} - Coming Soon"), bgcolor=self.danger_color)
        page.snack_bar.open = True
        page.update()
    
    def open_add_accessory_modal(self, page: ft.Page):
        page.snack_bar = ft.SnackBar(ft.Text("Add Accessory - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()
    
    def open_edit_accessory_modal(self, page: ft.Page, accessory_id):
        page.snack_bar = ft.SnackBar(ft.Text(f"Edit Accessory {accessory_id} - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()
    
    def open_delete_accessory_modal(self, page: ft.Page, accessory_id):
        page.snack_bar = ft.SnackBar(ft.Text(f"Delete Accessory {accessory_id} - Coming Soon"), bgcolor=self.danger_color)
        page.snack_bar.open = True
        page.update()
    
    def show_upgrade_screen(self, page: ft.Page):
        page.controls.clear()
        page.add(ft.Text("Trial Expired - Please Upgrade", size=24, color=self.danger_color))
        page.update()
    
    def show_forgot_password(self, page: ft.Page):
        page.snack_bar = ft.SnackBar(ft.Text("Password reset - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()


# Run the app
if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
