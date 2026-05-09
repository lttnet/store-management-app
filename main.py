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
        """Show dashboard - WITH QUALITY STATS FOR MATERIALS"""
        page.controls.clear()
        
        # Get data
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        users = self.dict_list(UserManager.get_all())
        
        # Calculate main stats
        total_materials = len(materials)
        total_accessories = len(accessories)
        
        # Calculate quality breakdown for MATERIALS
        quality_counts = {
            "New": 0,
            "Used": 0,
            "Damaged": 0,
            "Repaired": 0
        }
        
        for m in materials:
            quality = m.get('quality', 'Used')
            if quality in quality_counts:
                quality_counts[quality] += 1
            else:
                quality_counts["Used"] += 1
        
        # Low stock items
        low_stock_materials = [m for m in materials if m.get('quantity', 0) < 10]
        low_stock_accessories = [a for a in accessories if a.get('quantity', 0) < 10]
        total_low_stock = len(low_stock_materials) + len(low_stock_accessories)
        
        # Create sidebar
        sidebar = self.create_sidebar(page)
        
        # Create ListView for scrolling
        list_view = ft.ListView(expand=True, spacing=0, padding=20)
        
        # ========== HEADER ==========
        list_view.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("Dashboard", size=32, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.Text(datetime.now().strftime("%A, %B %d, %Y"), size=12, color="#888888"),
                ]),
                padding=ft.padding.only(bottom=15),
            )
        )
        
        # ========== MAIN STATS CARDS (3 cards) ==========
        list_view.controls.append(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Column([
                            ft.Text("📦 Materials", size=14, color="#CCCCCC"),
                            ft.Text(str(total_materials), size=36, weight=ft.FontWeight.BOLD, color=self.text_color),
                            ft.Text("Total items", size=10, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        padding=20, bgcolor=self.success_color, border_radius=15, expand=True,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🔧 Accessories", size=14, color="#CCCCCC"),
                            ft.Text(str(total_accessories), size=36, weight=ft.FontWeight.BOLD, color=self.text_color),
                            ft.Text("Total parts", size=10, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        padding=20, bgcolor=self.accent_color, border_radius=15, expand=True,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("⚠️ Low Stock", size=14, color="#CCCCCC"),
                            ft.Text(str(total_low_stock), size=36, weight=ft.FontWeight.BOLD, color=self.danger_color),
                            ft.Text("Below 10 units", size=10, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        padding=20, bgcolor=self.warning_color, border_radius=15, expand=True,
                    ),
                ],
                spacing=15,
            )
        )
        
        list_view.controls.append(ft.Container(height=20))
        
        # ========== QUALITY STATS FOR MATERIALS (New, Used, Damaged, Repaired) ==========
        list_view.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Material Quality Breakdown", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Divider(),
                    ft.Row(
                        [
                            # New
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("🟢", size=28),
                                    ft.Text("New", size=12, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                                    ft.Text(str(quality_counts["New"]), size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                                    ft.Text(f"{int(quality_counts['New']/total_materials*100) if total_materials > 0 else 0}%", size=11, color="#888888"),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                                padding=15,
                                bgcolor=self.card_color,
                                border_radius=10,
                                expand=True,
                            ),
                            # Used
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("🟠", size=28),
                                    ft.Text("Used", size=12, weight=ft.FontWeight.BOLD, color="#FF9800"),
                                    ft.Text(str(quality_counts["Used"]), size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                                    ft.Text(f"{int(quality_counts['Used']/total_materials*100) if total_materials > 0 else 0}%", size=11, color="#888888"),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                                padding=15,
                                bgcolor=self.card_color,
                                border_radius=10,
                                expand=True,
                            ),
                            # Damaged
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("🔴", size=28),
                                    ft.Text("Damaged", size=12, weight=ft.FontWeight.BOLD, color="#F44336"),
                                    ft.Text(str(quality_counts["Damaged"]), size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                                    ft.Text(f"{int(quality_counts['Damaged']/total_materials*100) if total_materials > 0 else 0}%", size=11, color="#888888"),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                                padding=15,
                                bgcolor=self.card_color,
                                border_radius=10,
                                expand=True,
                            ),
                            # Repaired
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("🔵", size=28),
                                    ft.Text("Repaired", size=12, weight=ft.FontWeight.BOLD, color="#2196F3"),
                                    ft.Text(str(quality_counts["Repaired"]), size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                                    ft.Text(f"{int(quality_counts['Repaired']/total_materials*100) if total_materials > 0 else 0}%", size=11, color="#888888"),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                                padding=15,
                                bgcolor=self.card_color,
                                border_radius=10,
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                    # Progress bar showing distribution
                    ft.Container(height=10),
                    ft.Row([
                        ft.Container(
                            width=f"{quality_counts['New']/total_materials*100 if total_materials > 0 else 0}%",
                            height=8,
                            bgcolor="#4CAF50",
                            border_radius=4,
                        ),
                        ft.Container(
                            width=f"{quality_counts['Used']/total_materials*100 if total_materials > 0 else 0}%",
                            height=8,
                            bgcolor="#FF9800",
                            border_radius=4,
                        ),
                        ft.Container(
                            width=f"{quality_counts['Damaged']/total_materials*100 if total_materials > 0 else 0}%",
                            height=8,
                            bgcolor="#F44336",
                            border_radius=4,
                        ),
                        ft.Container(
                            width=f"{quality_counts['Repaired']/total_materials*100 if total_materials > 0 else 0}%",
                            height=8,
                            bgcolor="#2196F3",
                            border_radius=4,
                        ),
                    ], spacing=0),
                ]),
                padding=15,
                bgcolor=self.card_color,
                border_radius=15,
            )
        )
        
        list_view.controls.append(ft.Container(height=20))
        
        # ========== MATERIALS SECTION ==========
        list_view.controls.append(
            ft.Row([
                ft.Text("📦 Materials", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_materials_screen(page)),
                ft.IconButton(icon=ft.icons.ADD_CIRCLE, icon_size=24, icon_color=self.success_color,
                            on_click=lambda e: self.open_add_modal(page)),
            ])
        )
        
        list_view.controls.append(ft.Divider())
        
        if materials:
            for m in materials[:10]:
                list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Column([
                                    ft.Text(m.get('name', 'N/A'), size=15, weight=ft.FontWeight.BOLD),
                                    ft.Text(m.get('location_ids', 'N/A'), size=11, color="#888888"),
                                ], expand=True, spacing=3),
                                ft.Column([
                                    ft.Text(f"Qty: {m.get('quantity', 0)}", size=14, weight=ft.FontWeight.BOLD,
                                            color=self.danger_color if m.get('quantity', 0) < 10 else self.text_color),
                                    ft.Container(
                                        content=ft.Text(m.get('quality', 'Used'), size=10, color="white"),
                                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                        border_radius=12,
                                        padding=ft.padding.symmetric(horizontal=12, vertical=4),
                                    ),
                                ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=4),
                            ]),
                            padding=12,
                        ),
                        elevation=2,
                        margin=ft.margin.only(bottom=8),
                    )
                )
        else:
            list_view.controls.append(ft.Text("No materials found", size=13, color="#888888", text_align=ft.TextAlign.CENTER))
        
        list_view.controls.append(ft.Container(height=15))
        
        # ========== ACCESSORIES SECTION ==========
        list_view.controls.append(
            ft.Row([
                ft.Text("🔧 Accessories", size=20, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_accessories(page)),
                ft.IconButton(icon=ft.icons.ADD_CIRCLE, icon_size=24, icon_color=self.success_color,
                            on_click=lambda e: self.open_add_accessory_modal(page)),
            ])
        )
        
        list_view.controls.append(ft.Divider())
        
        if accessories:
            for a in accessories[:10]:
                location = a.get('location') or a.get('location_ids') or 'N/A'
                list_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Column([
                                    ft.Text(a.get('name', 'N/A'), size=15, weight=ft.FontWeight.BOLD),
                                    ft.Text(location, size=11, color="#888888"),
                                ], expand=True, spacing=3),
                                ft.Column([
                                    ft.Text(f"Qty: {a.get('quantity', 0)}", size=14, weight=ft.FontWeight.BOLD,
                                            color=self.danger_color if a.get('quantity', 0) < 10 else self.text_color),
                                    ft.Text(f"${a.get('price', 0):.2f}", size=12, color="#4CAF50") if a.get('price') else ft.Container(),
                                ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=4),
                            ]),
                            padding=12,
                        ),
                        elevation=2,
                        margin=ft.margin.only(bottom=8),
                    )
                )
        else:
            list_view.controls.append(ft.Text("No accessories found", size=13, color="#888888", text_align=ft.TextAlign.CENTER))
        
        list_view.controls.append(ft.Container(height=15))
        
        # ========== LOW STOCK SECTION ==========
        if low_stock_materials or low_stock_accessories:
            list_view.controls.append(
                ft.Row([
                    ft.Icon(ft.icons.WARNING_AMBER, color="#FF9800", size=24),
                    ft.Text("Low Stock Alerts", size=20, weight=ft.FontWeight.BOLD, color="#FF9800"),
                    ft.Container(expand=True),
                    ft.Text(f"{total_low_stock} items need attention", size=12, color="#888888"),
                ])
            )
            list_view.controls.append(ft.Divider())
            
            for m in low_stock_materials[:8]:
                list_view.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(width=8, height=40, bgcolor=self.danger_color, border_radius=4),
                            ft.Container(width=10),
                            ft.Icon(ft.icons.INVENTORY, color=self.danger_color, size=20),
                            ft.Container(width=10),
                            ft.Text(m.get('name', 'Unknown'), size=14, expand=True),
                            ft.Text(f"Stock: {m.get('quantity', 0)}", size=14, color=self.danger_color, weight=ft.FontWeight.BOLD),
                            ft.ElevatedButton("Order", on_click=lambda e, mat=m: None, style=ft.ButtonStyle(bgcolor=self.danger_color, padding=5)),
                        ]),
                        padding=12,
                        bgcolor="#3C2121",
                        border_radius=10,
                        margin=ft.margin.only(bottom=8),
                    )
                )
            
            for a in low_stock_accessories[:8]:
                list_view.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(width=8, height=40, bgcolor=self.danger_color, border_radius=4),
                            ft.Container(width=10),
                            ft.Icon(ft.icons.BUILD, color=self.danger_color, size=20),
                            ft.Container(width=10),
                            ft.Text(a.get('name', 'Unknown'), size=14, expand=True),
                            ft.Text(f"Stock: {a.get('quantity', 0)}", size=14, color=self.danger_color, weight=ft.FontWeight.BOLD),
                            ft.ElevatedButton("Order", on_click=lambda e, acc=a: None, style=ft.ButtonStyle(bgcolor=self.danger_color, padding=5)),
                        ]),
                        padding=12,
                        bgcolor="#3C2121",
                        border_radius=10,
                        margin=ft.margin.only(bottom=8),
                    )
                )
            
            list_view.controls.append(ft.Container(height=15))
        
        # ========== QUICK ACTIONS ==========
        list_view.controls.append(
            ft.Row([
                ft.Text("Quick Actions", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
            ])
        )
        
        list_view.controls.append(ft.Divider())
        
        list_view.controls.append(
            ft.Row([
                ft.ElevatedButton("📥 Import Data", icon=ft.icons.UPLOAD_FILE, on_click=lambda e: None, 
                                style=ft.ButtonStyle(bgcolor=self.accent_color, padding=12), expand=True),
                ft.ElevatedButton("📤 Export Report", icon=ft.icons.DOWNLOAD, on_click=lambda e: None,
                                style=ft.ButtonStyle(bgcolor=self.warning_color, padding=12), expand=True),
                ft.ElevatedButton("🖨️ Print Barcode", icon=ft.icons.PRINT, on_click=lambda e: None,
                                style=ft.ButtonStyle(bgcolor=self.success_color, padding=12), expand=True),
                ft.ElevatedButton("⚙️ Settings", icon=ft.icons.SETTINGS, on_click=lambda e: self.show_settings(page),
                                style=ft.ButtonStyle(bgcolor=self.card_color, padding=12), expand=True),
            ], spacing=15, wrap=True)
        )
        
        list_view.controls.append(ft.Container(height=30))
        
        # Add to page
        page.add(ft.Row([sidebar, list_view], spacing=0, expand=True))
        
        self.current_view = "dashboard"
        page.update()
    
    def create_detail_panel(self, material, page):
        """Create detail panel for selected material"""
        if not material:
            return ft.Column([
                ft.Text("Material Details", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Container(height=20),
                ft.Text("Select a material to view details", size=12, color="#888888"),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        return ft.Column([
            ft.Text(material.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(content=ft.Text(material.get('quality', 'Used'), size=11, color="white"),
                                bgcolor=self.get_quality_color(material.get('quality', 'Used')),
                                border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))], spacing=5),
            ft.Row([ft.Text("📏 Size:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('size') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), ft.Text(str(material.get('quantity', 0)), size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('location_ids') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Divider(),
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(material.get('notes') or "No notes", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=lambda e: self.open_edit_modal(page, material['id']),
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=lambda e: self.open_delete_modal(page, material['id']),
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, material),
                                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], 
                alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
    
    def create_accessory_detail_panel(self, accessory, page):
        """Create detail panel for selected accessory"""
        if not accessory:
            return ft.Column([
                ft.Text("Accessory Details", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Container(height=20),
                ft.Text("Select an accessory to view details", size=12, color="#888888"),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        return ft.Column([
            ft.Text(accessory.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), ft.Text(accessory.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(content=ft.Text(accessory.get('quality', 'Used'), size=11, color="white"),
                                bgcolor=self.get_quality_color(accessory.get('quality', 'Used')),
                                border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))], spacing=5),
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), ft.Text(str(accessory.get('quantity', 0)), size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("💰 Price:", size=12, color="#CCCCCC", width=80), ft.Text(f"${accessory.get('price', 0):.2f}" if accessory.get('price') else "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), ft.Text(accessory.get('location') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Divider(),
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(accessory.get('notes') or "No notes", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=lambda e: self.open_edit_accessory_modal(page, accessory['id']),
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=lambda e: self.open_delete_accessory_modal(page, accessory['id']),
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, accessory),
                                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], 
                alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
    


    def open_add_modal(self, page: ft.Page):
        """Open add material modal"""
        page.snack_bar = ft.SnackBar(ft.Text("Add Material - Will be implemented"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()

    def open_add_accessory_modal(self, page: ft.Page):
        """Open add accessory modal"""
        page.snack_bar = ft.SnackBar(ft.Text("Add Accessory - Will be implemented"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()

    def view_material_from_dashboard(self, page: ft.Page, material):
        """Navigate to material details from dashboard"""
        self.selected_material_detail = material
        self.show_materials_screen(page)

    def view_accessory_from_dashboard(self, page: ft.Page, accessory):
        """Navigate to accessory details from dashboard"""
        self.selected_accessory_detail = accessory
        self.show_accessories(page)

    def view_material_detail(self, page: ft.Page, material):
        """View material detail (called from dashboard)"""
        self.selected_material_detail = material
        self.show_materials_screen(page)

    def view_accessory_detail(self, page: ft.Page, accessory):
        """View accessory detail (called from dashboard)"""
        self.selected_accessory_detail = accessory
        self.show_accessories(page)

    def show_import_dialog(self, page: ft.Page):
        """Show import dialog"""
        page.snack_bar = ft.SnackBar(ft.Text("Import CSV - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()

    def export_data(self, page: ft.Page):
        """Export data to CSV"""
        page.snack_bar = ft.SnackBar(ft.Text("Export CSV - Coming Soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()

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
        """Show materials screen with WORKING filter buttons"""
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
        
        # ========== SEARCH FIELD ==========
        search_field = ft.TextField(
            hint_text="Search materials...",
            width=int(200 * scale),
            bgcolor=self.card_color,
            border_color=self.accent_color,
            on_change=lambda e: self.search_materials_table(page, e.control.value),
        )
        
        # ========== FILTER BUTTONS (THIS IS WHAT YOU WANT) ==========
        self.filter_buttons = {}
        
        def create_filter_button(label, active_color, filter_type):
            btn = ft.Container(
                content=ft.Text(label, size=font_small, weight=ft.FontWeight.BOLD, 
                            color=self.text_color),
                padding=ft.padding.symmetric(horizontal=int(15 * scale), vertical=int(8 * scale)),
                bgcolor=active_color if self.current_filter == filter_type else self.card_color,
                border_radius=20,
                ink=True,
                on_click=lambda e, f=filter_type: self.filter_materials(page, f),
            )
            self.filter_buttons[filter_type] = btn
            return btn
        
        # Create the 5 filter buttons
        filter_row = ft.Row(
            [
                create_filter_button("All", self.accent_color, "All"),
                create_filter_button("New", self.success_color, "New"),
                create_filter_button("Used", self.warning_color, "Used"),
                create_filter_button("Damaged", self.danger_color, "Damaged"),
                create_filter_button("Repaired", self.accent_color, "Repaired"),
            ],
            spacing=int(8 * scale),
            wrap=True,  # This makes them wrap on small screens
        )
        
        # ========== ADD BUTTON ==========
        add_button = ft.FilledButton(
            "➕ Add Material",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
            on_click=lambda e: self.open_add_modal(page),
        )
        
        # ========== TABLE HEADER ==========
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Image", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Name", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(160 * scale)),
                ft.Text("Size", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(80 * scale)),
                ft.Text("Qty", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Quality", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(80 * scale)),
                ft.Text("Location", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Created", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
                ft.Text("Actions", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=int(8 * scale), horizontal=int(10 * scale)),
            bgcolor="#3C3C3C",
            border_radius=6,
        )
        
        # ========== TABLE ROWS CONTAINER ==========
        self.table_rows_container = ft.Column(spacing=int(2 * scale), scroll=ft.ScrollMode.AUTO, height=int(450 * scale))
        self.update_materials_table(materials)
        
        # ========== LEFT PANEL (TABLE) ==========
        left_panel = ft.Container(
            content=ft.Column([header_row, self.table_rows_container], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(5 * scale),
        )
        
        # ========== DETAIL PANEL (RIGHT SIDE) ==========
        self.detail_panel = ft.Container(
            content=self.create_detail_panel(None, page),
            width=int(320 * scale),
            bgcolor=self.card_color,
            border_radius=10,
            padding=int(15 * scale),
        )
        
        # ========== MAIN CONTENT ==========
        content = ft.Column([
            # Title and Search
            ft.Row([
                ft.Text("Materials", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.Row([ft.Icon(ft.icons.SEARCH, size=int(18 * scale)), search_field], spacing=int(5 * scale)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=int(10 * scale)),
            
            # FILTER BUTTONS ROW - THIS WILL SHOW NOW
            ft.Row([filter_row], alignment=ft.MainAxisAlignment.START),
            ft.Container(height=int(10 * scale)),
            
            # Add Button
            ft.Row([add_button], alignment=ft.MainAxisAlignment.END),
            ft.Container(height=int(15 * scale)),
            
            # Table and Detail Panel
            ft.Row([left_panel, ft.Container(width=int(12 * scale)), self.detail_panel], spacing=0, expand=True),
        ], expand=True)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # ========== FINAL LAYOUT ==========
        page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "materials"
        page.update()
    
    def view_material_detail(self, page: ft.Page, material):
        """View material detail from dashboard"""
        self.selected_material_detail = material
        self.show_materials_screen(page)

    def view_accessory_detail(self, page: ft.Page, accessory):
        """View accessory detail from dashboard"""
        self.selected_accessory_detail = accessory
        self.show_accessories(page)

    def update_materials_table(self, materials):
        """Update the materials table with given materials"""
        if not hasattr(self, 'table_rows_container'):
            return
        
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        font_small = int(12 * scale)
        
        self.table_rows_container.controls.clear()
        
        for m in materials:
            has_image = m.get('image_path') and os.path.exists(m.get('image_path', '')) if m.get('image_path') else False
            image_icon = "🖼️" if has_image else "📷"
            created_date = str(m.get('created_at', ''))[:10] if m.get('created_at') else 'N/A'
            
            row = ft.Container(
                content=ft.Row([
                    ft.Text(image_icon, size=font_small + 2, width=int(50 * scale)),
                    ft.Text(m.get('name', 'N/A'), size=font_small, width=int(160 * scale)),
                    ft.Text(str(m.get('length') or ""), size=font_small, width=int(50 * scale)),
                    ft.Text(m.get('size') or "N/A", size=font_small, width=int(70 * scale)),
                    ft.Text(str(m.get('quantity', 0)), size=font_small, width=int(45 * scale)),
                    ft.Container(
                        content=ft.Text(m.get('quality', 'Used'), size=font_small - 2, color="white"),
                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=int(6 * scale), vertical=int(2 * scale)),
                        width=int(75 * scale),
                    ),
                    ft.Text(m.get('location_ids') or "N/A", size=font_small, width=int(100 * scale)),
                    ft.Text(created_date, size=font_small - 2, width=int(90 * scale), color="#888888"),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.EDIT, icon_size=int(18 * scale), 
                                    on_click=lambda e, mat=m: self.open_edit_modal(self.page_ref, mat['id'])),
                        ft.IconButton(icon=ft.icons.DELETE, icon_size=int(18 * scale),
                                    on_click=lambda e, mat=m: self.open_delete_modal(self.page_ref, mat['id'])),
                        ft.IconButton(icon=ft.icons.QR_CODE, icon_size=int(18 * scale),
                                    on_click=lambda e, mat=m: self.show_barcode_dialog(self.page_ref, mat)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(vertical=int(8 * scale), horizontal=int(10 * scale)),
                border_radius=6,
                ink=True,
                on_click=lambda e, mat=m: self.on_material_select(mat),
            )
            self.table_rows_container.controls.append(row)
        
        if self.page_ref:
            self.page_ref.update()

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
        """Filter materials by quality"""
        self.current_filter = filter_type
        
        # Update button colors
        for f_type, btn in self.filter_buttons.items():
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
        
        # Filter materials based on selection
        if filter_type == "All":
            filtered_materials = self.dict_list(MaterialManager.get_all())
        else:
            all_materials = self.dict_list(MaterialManager.get_all())
            filtered_materials = [m for m in all_materials if m.get('quality') == filter_type]
        
        # Update the table
        self.update_materials_table(filtered_materials)
        page.update()

    def on_material_select(self, material):
        """Handle material selection from table"""
        self.selected_material_detail = material
        if hasattr(self, 'detail_panel'):
            self.detail_panel.content = self.create_detail_panel(material, self.page_ref)
            self.page_ref.update()

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
    
    def update_accessories_table(self, accessories):
        """Update the accessories table with given accessories"""
        if not hasattr(self, 'accessory_rows_container'):
            return
        
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        font_small = int(12 * scale)
        
        self.accessory_rows_container.controls.clear()
        
        for a in accessories:
            has_image = a.get('image_path') and os.path.exists(a.get('image_path', '')) if a.get('image_path') else False
            image_text = "🖼️" if has_image else "📷"
            location = a.get('location') or a.get('location_ids') or "N/A"
            created_date = str(a.get('created_at', ''))[:10] if a.get('created_at') else 'N/A'
            
            row = ft.Container(
                content=ft.Row([
                    ft.Text(image_text, size=font_small + 2, width=int(50 * scale)),
                    ft.Text(a.get('name', 'N/A'), size=font_small, width=int(160 * scale)),
                    ft.Text(a.get('item_code', 'N/A'), size=font_small, width=int(100 * scale)),
                    ft.Text(str(a.get('quantity', 0)), size=font_small, width=int(45 * scale)),
                    ft.Container(
                        content=ft.Text(a.get('quality', 'Used'), size=font_small - 2, color="white"),
                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=int(6 * scale), vertical=int(2 * scale)),
                        width=int(75 * scale),
                    ),
                    ft.Text(location, size=font_small, width=int(100 * scale)),
                    ft.Text(created_date, size=font_small - 2, width=int(90 * scale), color="#888888"),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.EDIT, icon_size=int(18 * scale), 
                                    on_click=lambda e, acc=a: self.open_edit_accessory_modal(self.page_ref, acc['id'])),
                        ft.IconButton(icon=ft.icons.DELETE, icon_size=int(18 * scale),
                                    on_click=lambda e, acc=a: self.open_delete_accessory_modal(self.page_ref, acc['id'])),
                        ft.IconButton(icon=ft.icons.QR_CODE, icon_size=int(18 * scale),
                                    on_click=lambda e, acc=a: self.show_barcode_dialog(self.page_ref, acc)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(vertical=int(8 * scale), horizontal=int(10 * scale)),
                border_radius=6,
                ink=True,
                on_click=lambda e, acc=a: self.on_accessory_select(acc),
            )
            self.accessory_rows_container.controls.append(row)
        
        if self.page_ref:
            self.page_ref.update()

    def on_accessory_select(self, accessory):
        """Handle accessory selection from table"""
        self.selected_accessory_detail = accessory
        if hasattr(self, 'accessory_detail_panel'):
            self.accessory_detail_panel.content = self.create_accessory_detail_panel(accessory, self.page_ref)
            self.page_ref.update()

    def show_inventory(self, page: ft.Page):
        """Show inventory screen - ALL SECTIONS VISIBLE with ListView"""
        page.controls.clear()
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        sidebar = self.create_sidebar(page)
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(28 * scale)
        font_normal = int(16 * scale)
        font_small = int(14 * scale)  # ADD THIS LINE - was missing
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
            location = a.get('location') or a.get('location_ids') or 'N/A'
            inventory_items.append({
                'type': '🔧 Accessory',
                'name': a.get('name', 'N/A'),
                'code': a.get('item_code', 'N/A'),
                'quantity': a.get('quantity', 0),
                'quality': a.get('quality', 'Used'),
                'location': location,
            })
        
        inventory_items.sort(key=lambda x: x['name'])
        
        total_materials = len(materials)
        total_accessories = len(accessories)
        total_items = total_materials + total_accessories
        total_stock = sum(i.get('quantity', 0) for i in inventory_items)
        low_items = [i for i in inventory_items if i.get('quantity', 0) < 10]
        
        # Create ListView for scrolling
        list_view = ft.ListView(expand=True, spacing=0, padding=padding_size)
        
        # ========== HEADER ==========
        list_view.controls.append(
            ft.Row([
                ft.Text("Inventory Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
            ])
        )
        list_view.controls.append(ft.Container(height=15))
        
        # ========== STATS CARDS ==========
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("📦 Total Items", size=font_normal - 2, color="#CCCCCC"),
                    ft.Text(str(total_items), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text(f"{total_materials} Mat, {total_accessories} Acc", size=font_normal - 4, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Total Stock", size=font_normal - 2, color="#CCCCCC"),
                    ft.Text(str(total_stock), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Units in inventory", size=font_normal - 4, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.success_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("⚠️ Low Stock", size=font_normal - 2, color="#CCCCCC"),
                    ft.Text(str(len(low_items)), size=font_stats, weight=ft.FontWeight.BOLD, color=self.danger_color),
                    ft.Text("Items below 10 units", size=font_normal - 4, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
        ], spacing=int(15 * scale))
        
        list_view.controls.append(stats_row)
        list_view.controls.append(ft.Container(height=20))
        
        # ========== FILTER SECTION ==========
        # Type Filter
        type_filter = ft.Dropdown(
            label="Filter by Type",
            width=int(180 * scale),
            options=[
                ft.dropdown.Option("All", "📦 All Items"),
                ft.dropdown.Option("Material", "📦 Materials Only"),
                ft.dropdown.Option("Accessory", "🔧 Accessories Only"),
            ],
            value="All",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
        )
        
        # Quality Filter
        quality_filter = ft.Dropdown(
            label="Filter by Quality",
            width=int(160 * scale),
            options=[
                ft.dropdown.Option("All", "All Qualities"),
                ft.dropdown.Option("New", "🟢 New"),
                ft.dropdown.Option("Used", "🟠 Used"),
                ft.dropdown.Option("Damaged", "🔴 Damaged"),
                ft.dropdown.Option("Repaired", "🔵 Repaired"),
            ],
            value="All",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
        )
        
        filter_count_text = ft.Text("", size=font_small - 1, color="#888888")
        
        # Variable to store filtered items
        current_filtered_items = inventory_items.copy()
        
        # Function to update inventory display
        def update_inventory_display():
            nonlocal current_filtered_items
            # Clear existing inventory rows (keep header)
            while len(inventory_list.controls) > 1:
                inventory_list.controls.pop()
            
            if current_filtered_items:
                for i, item in enumerate(current_filtered_items[:100]):
                    quality_color = self.get_quality_color(item['quality'])
                    row_color = "#2C2C2C" if i % 2 == 0 else "#1E1E1E"
                    
                    inventory_list.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Container(
                                    content=ft.Row([
                                        ft.Text("📦" if item['type'] == '📦 Material' else "🔧", size=font_small),
                                        ft.Text(item['type'][:4], size=font_small - 1, weight=ft.FontWeight.BOLD),
                                    ], spacing=4),
                                    bgcolor=self.accent_color if item['type'] == '📦 Material' else self.warning_color,
                                    border_radius=12,
                                    padding=ft.padding.symmetric(horizontal=int(10 * scale), vertical=int(4 * scale)),
                                    width=int(90 * scale),
                                ),
                                ft.Container(
                                    ft.Text(item['name'], size=font_small, weight=ft.FontWeight.BOLD),
                                    expand=True,
                                ),
                                ft.Container(
                                    ft.Text(item['code'], size=font_small - 2),
                                    width=int(110 * scale),
                                ),
                                ft.Container(
                                    ft.Text(str(item['quantity']), size=font_small, 
                                            weight=ft.FontWeight.BOLD if item['quantity'] < 10 else None,
                                            color=self.danger_color if item['quantity'] < 10 else self.text_color),
                                    width=int(60 * scale),
                                    alignment=ft.alignment.center,
                                ),
                                ft.Container(
                                    content=ft.Text(item['quality'], size=font_small - 2, color="white", text_align=ft.TextAlign.CENTER),
                                    bgcolor=quality_color,
                                    border_radius=12,
                                    padding=ft.padding.symmetric(horizontal=int(10 * scale), vertical=int(4 * scale)),
                                    width=int(90 * scale),
                                ),
                                ft.Container(
                                    ft.Text(item['location'], size=font_small - 2),
                                    width=int(140 * scale),
                                ),
                            ], spacing=int(10 * scale), alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=ft.padding.symmetric(vertical=int(10 * scale), horizontal=int(12 * scale)),
                            bgcolor=row_color,
                            border_radius=8,
                        )
                    )
            else:
                inventory_list.controls.append(
                    ft.Container(
                        content=ft.Text("No items found matching filters.", size=font_small, color="#888888"),
                        padding=int(40 * scale),
                        alignment=ft.alignment.center,
                    )
                )
            page.update()
        
        def apply_filters(e=None):
            nonlocal current_filtered_items
            selected_type = type_filter.value
            selected_quality = quality_filter.value
            
            filtered = inventory_items.copy()
            
            if selected_type != "All":
                filtered = [item for item in filtered if selected_type in item['type']]
            
            if selected_quality != "All":
                filtered = [item for item in filtered if item['quality'] == selected_quality]
            
            current_filtered_items = filtered
            filter_count_text.value = f"Showing {len(filtered)} of {len(inventory_items)} items"
            filter_count_text.color = self.accent_color if len(filtered) != len(inventory_items) else "#888888"
            
            update_inventory_display()
        
        def reset_filters(e):
            type_filter.value = "All"
            quality_filter.value = "All"
            apply_filters()
        
        type_filter.on_change = apply_filters
        quality_filter.on_change = apply_filters
        
        # Filter bar
        filter_bar = ft.Container(
            content=ft.Row([
                ft.Row([type_filter, quality_filter], spacing=int(10 * scale)),
                ft.Row([
                    ft.OutlinedButton("Reset", on_click=reset_filters, style=ft.ButtonStyle(color=self.warning_color), height=int(40 * scale)),
                    filter_count_text,
                ], spacing=int(10 * scale)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(vertical=int(8 * scale), horizontal=int(12 * scale)),
            bgcolor="#2C2C2C",
            border_radius=8,
        )
        
        list_view.controls.append(filter_bar)
        list_view.controls.append(ft.Container(height=10))
        
        # ========== INVENTORY TABLE HEADER ==========
        table_header = ft.Container(
            content=ft.Row([
                ft.Text("Type", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(90 * scale)),
                ft.Text("Name", size=font_small - 1, weight=ft.FontWeight.BOLD, expand=True),
                ft.Text("Code", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Qty", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(55 * scale)),
                ft.Text("Quality", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(85 * scale)),
                ft.Text("Location", size=font_small - 1, weight=ft.FontWeight.BOLD, width=int(130 * scale)),
            ], spacing=int(10 * scale)),
            padding=ft.padding.symmetric(vertical=int(12 * scale), horizontal=int(12 * scale)),
            bgcolor="#3C3C3C",
            border_radius=8,
        )
        
        # ========== INVENTORY LIST CONTAINER ==========
        inventory_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=int(450 * scale))
        
        # Add header first
        inventory_list.controls.append(table_header)
        
        # Add initial data
        for i, item in enumerate(inventory_items[:100]):
            quality_color = self.get_quality_color(item['quality'])
            row_color = "#2C2C2C" if i % 2 == 0 else "#1E1E1E"
            
            inventory_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Row([
                                ft.Text("📦" if item['type'] == '📦 Material' else "🔧", size=font_small),
                                ft.Text(item['type'][:4], size=font_small - 1, weight=ft.FontWeight.BOLD),
                            ], spacing=4),
                            bgcolor=self.accent_color if item['type'] == '📦 Material' else self.warning_color,
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=int(10 * scale), vertical=int(4 * scale)),
                            width=int(90 * scale),
                        ),
                        ft.Container(
                            ft.Text(item['name'], size=font_small, weight=ft.FontWeight.BOLD),
                            expand=True,
                        ),
                        ft.Container(
                            ft.Text(item['code'], size=font_small - 2),
                            width=int(110 * scale),
                        ),
                        ft.Container(
                            ft.Text(str(item['quantity']), size=font_small, 
                                    weight=ft.FontWeight.BOLD if item['quantity'] < 10 else None,
                                    color=self.danger_color if item['quantity'] < 10 else self.text_color),
                            width=int(60 * scale),
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Text(item['quality'], size=font_small - 2, color="white", text_align=ft.TextAlign.CENTER),
                            bgcolor=quality_color,
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=int(10 * scale), vertical=int(4 * scale)),
                            width=int(90 * scale),
                        ),
                        ft.Container(
                            ft.Text(item['location'], size=font_small - 2),
                            width=int(140 * scale),
                        ),
                    ], spacing=int(10 * scale), alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=int(10 * scale), horizontal=int(12 * scale)),
                    bgcolor=row_color,
                    border_radius=8,
                )
            )
        
        list_view.controls.append(inventory_list)
        list_view.controls.append(ft.Container(height=15))
        
        # ========== EXPORT BUTTONS ==========
        list_view.controls.append(
            ft.Row([
                ft.ElevatedButton("📊 Export CSV", on_click=lambda e: None, 
                                style=ft.ButtonStyle(bgcolor=self.accent_color, padding=int(12 * scale))),
                ft.ElevatedButton("📄 Export PDF", on_click=lambda e: None,
                                style=ft.ButtonStyle(bgcolor=self.warning_color, padding=int(12 * scale))),
                ft.ElevatedButton("🔄 Refresh", on_click=lambda e: self.show_inventory(page),
                                style=ft.ButtonStyle(bgcolor=self.success_color, padding=int(12 * scale))),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=int(15 * scale))
        )
        
        list_view.controls.append(ft.Container(height=30))
        
        # ========== FINAL LAYOUT ==========
        page.add(ft.Row([sidebar, list_view], spacing=0, expand=True))
        
        self.current_view = "inventory"
        page.update()
    
    def show_users(self, page: ft.Page):
        """Show users screen - WITH INCREASED FONT SIZES FOR BETTER READABILITY"""
        page.controls.clear()
        
        users = self.dict_list(UserManager.get_all())
        sidebar = self.create_sidebar(page)
        is_admin = self.current_user.get('role') == 'admin' if self.current_user else False
        
        # Get scale for responsive sizing - INCREASED FONT SIZES
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(28 * scale)  # Increased from 24
        font_normal = int(16 * scale)  # Increased from 14
        font_small = int(14 * scale)   # Increased from 12
        font_stats = int(32 * scale)   # Increased from 28
        
        # Stats
        admin_count = len([u for u in users if u.get('role') == 'admin'])
        manager_count = len([u for u in users if u.get('role') == 'manager'])
        user_count = len([u for u in users if u.get('role') == 'user'])
        
        # ========== STATS CARDS ==========
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("👥 Total", size=font_small, color="#CCCCCC"),
                    ft.Text(str(len(users)), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Users", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👑 Admins", size=font_small, color="#CCCCCC"),
                    ft.Text(str(admin_count), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Administrators", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.danger_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Managers", size=font_small, color="#CCCCCC"),
                    ft.Text(str(manager_count), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Management", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 Users", size=font_small, color="#CCCCCC"),
                    ft.Text(str(user_count), size=font_stats, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Regular users", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=int(15 * scale), bgcolor=self.success_color, border_radius=10, expand=True,
            ),
        ], spacing=int(15 * scale))
        
        # ========== ADD BUTTON ==========
        add_button = ft.FilledButton(
            "➕ Add New User",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color, padding=int(12 * scale)),
            on_click=lambda e: self.open_add_user_modal(page),
            visible=is_admin,
        )
        
        # ========== USER TABLE WITH LARGER FONTS ==========
        # Table Header - INCREASED FONT SIZE
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("ID", size=font_small, weight=ft.FontWeight.BOLD, width=int(50 * scale)),
                ft.Text("Name", size=font_small, weight=ft.FontWeight.BOLD, width=int(180 * scale)),
                ft.Text("Email", size=font_small, weight=ft.FontWeight.BOLD, width=int(220 * scale)),
                ft.Text("Role", size=font_small, weight=ft.FontWeight.BOLD, width=int(100 * scale)),
                ft.Text("Created", size=font_small, weight=ft.FontWeight.BOLD, width=int(120 * scale)),
                ft.Text("Actions", size=font_small, weight=ft.FontWeight.BOLD, width=int(120 * scale)),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=int(12 * scale), horizontal=int(15 * scale)),
            bgcolor="#3C3C3C",
            border_radius=8,
        )
        
        # Table Rows - INCREASED FONT SIZE
        table_rows = ft.Column(spacing=int(4 * scale), scroll=ft.ScrollMode.AUTO, height=int(450 * scale))
        
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
                        ft.Text(str(u.get('id', '')), size=font_small - 1, width=int(50 * scale)),
                        ft.Text(u.get('name', 'N/A'), size=font_small, weight=ft.FontWeight.BOLD, width=int(180 * scale)),
                        ft.Text(u.get('email', 'N/A'), size=font_small - 1, width=int(220 * scale), color="#CCCCCC"),
                        ft.Container(
                            content=ft.Text(role_display, size=font_small - 2, color="white", weight=ft.FontWeight.BOLD),
                            bgcolor=role_color,
                            border_radius=12,
                            padding=ft.padding.symmetric(horizontal=int(12 * scale), vertical=int(6 * scale)),
                            width=int(100 * scale),
                            alignment=ft.alignment.center,
                        ),
                        ft.Text(created_date, size=font_small - 2, width=int(120 * scale), color="#888888"),
                        ft.Row([
                            ft.IconButton(icon=ft.icons.EDIT, icon_size=int(22 * scale), 
                                        on_click=lambda e, uid=u.get('id'): self.open_edit_user_modal(page, uid),
                                        tooltip="Edit User"),
                            ft.IconButton(icon=ft.icons.DELETE, icon_size=int(22 * scale),
                                        on_click=lambda e, uid=u.get('id'), name=u.get('name'): self.open_delete_user_modal(page, uid, name),
                                        tooltip="Delete User"),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=int(12 * scale), horizontal=int(15 * scale)),
                    bgcolor="#2C2C2C",
                    border_radius=6,
                )
            )
        
        users_panel = ft.Container(
            content=ft.Column([header_row, table_rows], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=12,
            padding=int(5 * scale),
        )
        
        # ========== MAIN CONTENT ==========
        content = ft.Column([
            ft.Row([
                ft.Text("Users Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                add_button,
            ]),
            ft.Container(height=int(20 * scale)),
            stats_row,
            ft.Container(height=int(25 * scale)),
            ft.Text("📋 User List", size=font_normal + 2, weight=ft.FontWeight.BOLD),
            ft.Container(height=int(10 * scale)),
            users_panel,
        ], expand=True)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # ========== FINAL LAYOUT ==========
        page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "users"
        page.update()
    
    def show_settings(self, page: ft.Page):
        """Show settings screen - PROFESSIONAL SETTINGS INTERFACE"""
        page.controls.clear()
        
        sidebar = self.create_sidebar(page)
        
        # Get scale for responsive sizing
        scale = self.scale_helper.scale if self.scale_helper else 1.0
        padding_size = int(20 * scale)
        font_title = int(28 * scale)
        font_normal = int(16 * scale)
        font_small = int(14 * scale)
        
        # Get current user info
        current_user = self.current_user
        is_admin = current_user.get('role') == 'admin' if current_user else False
        
        # Create ListView for scrolling
        list_view = ft.ListView(expand=True, spacing=0, padding=padding_size)
        
        # ========== HEADER ==========
        list_view.controls.append(
            ft.Row([
                ft.Text("Settings", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.Text(f"Logged in as: {current_user.get('name', 'User')}", size=font_small - 2, color="#888888"),
            ])
        )
        list_view.controls.append(ft.Container(height=20))
        
        # ========== SETTINGS TABS ==========
        selected_tab = "profile"  # Default selected tab
        
        # Tab buttons
        tab_buttons = ft.Row(
            [
                ft.Container(
                    content=ft.Text("👤 Profile", size=font_small, weight=ft.FontWeight.BOLD, 
                                color=self.text_color if selected_tab == "profile" else "#888888"),
                    padding=ft.padding.symmetric(horizontal=int(20 * scale), vertical=int(12 * scale)),
                    bgcolor=self.accent_color if selected_tab == "profile" else self.card_color,
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: switch_tab("profile"),
                ),
                ft.Container(
                    content=ft.Text("🔐 Security", size=font_small, weight=ft.FontWeight.BOLD,
                                color=self.text_color if selected_tab == "security" else "#888888"),
                    padding=ft.padding.symmetric(horizontal=int(20 * scale), vertical=int(12 * scale)),
                    bgcolor=self.accent_color if selected_tab == "security" else self.card_color,
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: switch_tab("security"),
                ),
                ft.Container(
                    content=ft.Text("🏢 Company", size=font_small, weight=ft.FontWeight.BOLD,
                                color=self.text_color if selected_tab == "company" else "#888888"),
                    padding=ft.padding.symmetric(horizontal=int(20 * scale), vertical=int(12 * scale)),
                    bgcolor=self.accent_color if selected_tab == "company" else self.card_color,
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: switch_tab("company"),
                ),
                ft.Container(
                    content=ft.Text("💾 Database", size=font_small, weight=ft.FontWeight.BOLD,
                                color=self.text_color if selected_tab == "database" else "#888888"),
                    padding=ft.padding.symmetric(horizontal=int(20 * scale), vertical=int(12 * scale)),
                    bgcolor=self.accent_color if selected_tab == "database" else self.card_color,
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: switch_tab("database"),
                ),
                ft.Container(
                    content=ft.Text("🎨 Appearance", size=font_small, weight=ft.FontWeight.BOLD,
                                color=self.text_color if selected_tab == "appearance" else "#888888"),
                    padding=ft.padding.symmetric(horizontal=int(20 * scale), vertical=int(12 * scale)),
                    bgcolor=self.accent_color if selected_tab == "appearance" else self.card_color,
                    border_radius=10,
                    ink=True,
                    on_click=lambda e: switch_tab("appearance"),
                ),
            ],
            spacing=int(10 * scale),
            wrap=True,
        )
        
        list_view.controls.append(tab_buttons)
        list_view.controls.append(ft.Container(height=20))
        
        # Content container that will be updated when tabs change
        content_container = ft.Container()
        list_view.controls.append(content_container)
        
        # ========== PROFILE TAB ==========
        def create_profile_tab():
            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.CircleAvatar(
                                content=ft.Text(current_user.get('name', 'U')[0].upper(), size=24),
                                radius=40,
                                bgcolor=self.accent_color,
                            ),
                            ft.Column([
                                ft.Text(current_user.get('name', 'User'), size=font_normal + 2, weight=ft.FontWeight.BOLD),
                                ft.Text(current_user.get('email', 'N/A'), size=font_small, color="#888888"),
                                ft.Text(f"Role: {current_user.get('role', 'user').upper()}", size=font_small - 1, 
                                    color=self.success_color if current_user.get('role') == 'admin' else self.warning_color),
                            ], spacing=5),
                        ], spacing=20),
                        ft.Divider(),
                        ft.Text("Profile Information", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.TextField(label="Full Name", value=current_user.get('name', ''), 
                                width=int(350 * scale), bgcolor=self.card_color),
                        ft.TextField(label="Email", value=current_user.get('email', ''), 
                                width=int(350 * scale), bgcolor=self.card_color, read_only=True),
                        ft.TextField(label="Role", value=current_user.get('role', 'user').upper(), 
                                width=int(350 * scale), bgcolor=self.card_color, read_only=True),
                        ft.Container(height=15),
                        ft.ElevatedButton("💾 Save Changes", on_click=lambda e: None, 
                                        style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ], spacing=12),
                    padding=int(20 * scale),
                    bgcolor=self.card_color,
                    border_radius=15,
                ),
            ])
        
        # ========== SECURITY TAB ==========
        def create_security_tab():
            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Change Password", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Container(height=10),
                        ft.TextField(label="Current Password", password=True, can_reveal_password=True,
                                width=int(350 * scale), bgcolor=self.card_color),
                        ft.TextField(label="New Password", password=True, can_reveal_password=True,
                                width=int(350 * scale), bgcolor=self.card_color),
                        ft.TextField(label="Confirm New Password", password=True, can_reveal_password=True,
                                width=int(350 * scale), bgcolor=self.card_color),
                        ft.Container(height=15),
                        ft.ElevatedButton("🔑 Update Password", on_click=lambda e: None,
                                        style=ft.ButtonStyle(bgcolor=self.warning_color)),
                        ft.Container(height=20),
                        ft.Text("Two-Factor Authentication", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            ft.Text("Enable 2FA for additional security", size=font_small, color="#888888"),
                            ft.Switch(value=False, on_change=lambda e: None),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ], spacing=12),
                    padding=int(20 * scale),
                    bgcolor=self.card_color,
                    border_radius=15,
                ),
            ])
        
        # ========== COMPANY TAB ==========
        def create_company_tab():
            # Load company info
            company_info = self.get_company_info()
            
            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Company Information", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Container(height=10),
                        ft.TextField(label="Company Name", value=company_info.get('company_name', ''),
                                width=int(400 * scale), bgcolor=self.card_color),
                        ft.Row([
                            ft.TextField(label="Phone", value=company_info.get('phone', ''),
                                    width=int(190 * scale), bgcolor=self.card_color),
                            ft.TextField(label="Email", value=company_info.get('email', ''),
                                    width=int(190 * scale), bgcolor=self.card_color),
                        ], spacing=int(10 * scale)),
                        ft.TextField(label="Website", value=company_info.get('website', ''),
                                width=int(400 * scale), bgcolor=self.card_color),
                        ft.TextField(label="Address", value=company_info.get('address', ''),
                                width=int(400 * scale), bgcolor=self.card_color, multiline=True),
                        ft.Row([
                            ft.TextField(label="City", value=company_info.get('city', ''),
                                    width=int(190 * scale), bgcolor=self.card_color),
                            ft.TextField(label="Tax ID / VAT", value=company_info.get('tax_id', ''),
                                    width=int(190 * scale), bgcolor=self.card_color),
                        ], spacing=int(10 * scale)),
                        ft.Container(height=15),
                        ft.ElevatedButton("💾 Save Company Info", on_click=lambda e: None,
                                        style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ], spacing=12),
                    padding=int(20 * scale),
                    bgcolor=self.card_color,
                    border_radius=15,
                ),
            ])
        
        # ========== DATABASE TAB ==========
        def create_database_tab():
            # Get database size
            db_size = "N/A"
            if os.path.exists("store_management.db"):
                size_bytes = os.path.getsize("store_management.db")
                if size_bytes < 1024:
                    db_size = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    db_size = f"{size_bytes / 1024:.1f} KB"
                else:
                    db_size = f"{size_bytes / (1024 * 1024):.1f} MB"
            
            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Database Information", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            ft.Icon(ft.icons.DATABASE, size=40, color=self.accent_color),
                            ft.Column([
                                ft.Text("Database Size", size=font_small, color="#888888"),
                                ft.Text(db_size, size=font_normal + 2, weight=ft.FontWeight.BOLD),
                            ]),
                        ], spacing=15),
                        ft.Container(height=15),
                        ft.Text("Backup & Restore", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            ft.ElevatedButton("📥 Backup Database", on_click=lambda e: None,
                                            style=ft.ButtonStyle(bgcolor=self.accent_color), expand=True),
                            ft.ElevatedButton("🔄 Restore Database", on_click=lambda e: None,
                                            style=ft.ButtonStyle(bgcolor=self.warning_color), expand=True),
                        ], spacing=int(10 * scale)),
                        ft.Container(height=15),
                        ft.Text("Data Management", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            ft.ElevatedButton("📊 Export All Data", on_click=lambda e: None,
                                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
                            ft.ElevatedButton("🗑️ Clear Logs", on_click=lambda e: None,
                                            style=ft.ButtonStyle(bgcolor=self.danger_color), expand=True),
                        ], spacing=int(10 * scale)),
                        ft.Container(height=15),
                        ft.Text("⚠️ Danger Zone", size=font_normal, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Divider(),
                        ft.Container(
                            content=ft.Row([
                                ft.Text("Reset all data - This action cannot be undone!", size=font_small, color="#888888"),
                                ft.ElevatedButton("Reset Database", on_click=lambda e: None,
                                                style=ft.ButtonStyle(bgcolor=self.danger_color)),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=12,
                            bgcolor="#3C2121",
                            border_radius=8,
                        ),
                    ], spacing=12),
                    padding=int(20 * scale),
                    bgcolor=self.card_color,
                    border_radius=15,
                ),
            ])
        
        # ========== APPEARANCE TAB ==========
        def create_appearance_tab():
            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Theme Settings", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.icons.DARK_MODE, size=32),
                                    ft.Text("Dark Mode", size=font_small),
                                    ft.Radio(value="dark", label=""),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=15,
                                bgcolor=self.card_color,
                                border_radius=10,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Icon(ft.icons.LIGHT_MODE, size=32),
                                    ft.Text("Light Mode", size=font_small),
                                    ft.Radio(value="light", label=""),
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                padding=15,
                                bgcolor=self.card_color,
                                border_radius=10,
                                expand=True,
                            ),
                        ], spacing=15),
                        ft.Container(height=15),
                        ft.Text("Accent Color", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            ft.Container(width=30, height=30, bgcolor="#1976D2", border_radius=15, on_click=lambda e: None, ink=True),
                            ft.Container(width=30, height=30, bgcolor="#4CAF50", border_radius=15, on_click=lambda e: None, ink=True),
                            ft.Container(width=30, height=30, bgcolor="#9C27B0", border_radius=15, on_click=lambda e: None, ink=True),
                            ft.Container(width=30, height=30, bgcolor="#FF9800", border_radius=15, on_click=lambda e: None, ink=True),
                            ft.Container(width=30, height=30, bgcolor="#E91E63", border_radius=15, on_click=lambda e: None, ink=True),
                            ft.Container(width=30, height=30, bgcolor="#00BCD4", border_radius=15, on_click=lambda e: None, ink=True),
                            ft.Container(width=30, height=30, bgcolor="#F44336", border_radius=15, on_click=lambda e: None, ink=True),
                        ], spacing=10),
                        ft.Container(height=15),
                        ft.Text("Font Size", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Row([
                            ft.ElevatedButton("Small", on_click=lambda e: None),
                            ft.ElevatedButton("Medium", on_click=lambda e: None),
                            ft.ElevatedButton("Large", on_click=lambda e: None),
                        ], spacing=10),
                        ft.Container(height=15),
                        ft.ElevatedButton("💾 Apply Settings", on_click=lambda e: None,
                                        style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ], spacing=12),
                    padding=int(20 * scale),
                    bgcolor=self.card_color,
                    border_radius=15,
                ),
            ])
        
        # Dictionary mapping tabs to their content creation functions
        tabs = {
            "profile": create_profile_tab,
            "security": create_security_tab,
            "company": create_company_tab,
            "database": create_database_tab,
            "appearance": create_appearance_tab,
        }
        
        # Function to switch tabs
        def switch_tab(tab_name):
            nonlocal selected_tab
            selected_tab = tab_name
            
            # Update tab button colors
            for i, btn in enumerate(tab_buttons.controls):
                if btn.data == tab_name:
                    btn.bgcolor = self.accent_color
                    btn.content.color = self.text_color
                else:
                    btn.bgcolor = self.card_color
                    if hasattr(btn.content, 'color'):
                        btn.content.color = "#888888"
            
            # Update content
            if tab_name in tabs:
                content_container.content = tabs[tab_name]()
            page.update()
        
        # Store tab names on buttons for identification
        tab_names = ["profile", "security", "company", "database", "appearance"]
        for i, btn in enumerate(tab_buttons.controls):
            btn.data = tab_names[i]
        
        # Initialize with profile tab
        content_container.content = create_profile_tab()
        
        # ========== ADD TO PAGE ==========
        page.add(ft.Row([sidebar, list_view], spacing=0, expand=True))
        
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
