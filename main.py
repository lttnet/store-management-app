"""Store Management App - ORIGINAL LAYOUT WITH ZOOM SUPPORT"""
import sys
import warnings
import traceback

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

import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, 'images', 'Logo-store.png')
background_path = os.path.join(BASE_DIR, 'images', 'backgound_storemgt.png')

class ScaleHelper:
    """Automatically scales desktop layout to fit any screen"""
    
    DESKTOP_WIDTH = 1600
    DESKTOP_HEIGHT = 900
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.scale = 1.0
        self.update_scale()
    
    def update_scale(self):
        """Calculate scale factor based on current window size"""
        if self.page.width and self.page.height:
            scale_w = self.page.width / self.DESKTOP_WIDTH
            scale_h = self.page.height / self.DESKTOP_HEIGHT
            # Use the smaller scale to ensure everything fits
            self.scale = min(scale_w, scale_h, 1.0)  # Max scale 1.0, never enlarge beyond original
        else:
            self.scale = 1.0
    
    def get_scaled_size(self, original_size):
        """Get scaled size for dimensions"""
        return original_size * self.scale
    
    def get_scaled_font(self, original_size):
        """Get scaled font size (minimum 8px)"""
        scaled = int(original_size * self.scale)
        return max(scaled, 8)
    
class StoreApp:
    def __init__(self):
        self.current_user = None
        self.current_view = "dashboard"
        self.selected_material_detail = None
        self.selected_accessory_detail = None
        self.current_material_filter = "All"
        self.current_accessory_filter = "All"
        self.page_ref = None
        self.zoom_level = 1.0
        self.scale_helper = None  # Will be initialized in main
        
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
    
    def dict_list(self, rows):
        if rows is None:
            return []
        return [dict(row) for row in rows]
    
    def get_quality_color(self, quality):
        return self.quality_colors.get(quality, "#CCCCCC")
    
    def has_permission(self, permission):
        if not self.current_user:
            return False
        return True
    
    def show_no_permission(self, page):
        page.snack_bar = ft.SnackBar(ft.Text("No permission"), bgcolor=self.danger_color)
        page.snack_bar.open = True
        page.update()
    
    def get_company_info(self):
        """Load company information from config file with error handling"""
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
                    content = f.read().strip()
                    if content:  # Check if file is not empty
                        data = json.loads(content)
                        default_info.update(data)
                        print(f"Loaded company info: {default_info}")  # Debug print
            except (json.JSONDecodeError, ValueError, IOError) as e:
                print(f"Error reading company config: {e}")
                # If file is corrupted, create a new valid one
                try:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(default_info, f, indent=4, ensure_ascii=False)
                except:
                    pass
        else:
            # Create default config file if it doesn't exist
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_info, f, indent=4, ensure_ascii=False)
                print(f"Created default company config at {config_file}")
            except:
                pass
        
        return default_info
    
    def save_company_info(self, page: ft.Page):
        """Save company information to config file"""
        import json
        import os
        
        # Find the company card and get values
        # Since we can't easily get the values from the card, we'll use a dialog approach
        
        def save_info(e):
            data = {
                'company_name': name_field.value,
                'phone': phone_field.value,
                'email': email_field.value,
                'website': website_field.value,
                'address': address_field.value,
                'city': city_field.value,
                'tax_id': tax_id_field.value,
            }
            
            try:
                config_file = os.path.join(BASE_DIR, "company_config.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Company information saved!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_settings(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Error saving: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
            page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        # Get current company info
        current = self.get_company_info()
        
        name_field = ft.TextField(label="Company Name", value=current.get('company_name', ''), width=350)
        phone_field = ft.TextField(label="Phone", value=current.get('phone', ''), width=350)
        email_field = ft.TextField(label="Email", value=current.get('email', ''), width=350)
        website_field = ft.TextField(label="Website", value=current.get('website', ''), width=350)
        address_field = ft.TextField(label="Address", value=current.get('address', ''), width=350, multiline=True)
        city_field = ft.TextField(label="City", value=current.get('city', ''), width=350)
        tax_id_field = ft.TextField(label="Tax ID / VAT", value=current.get('tax_id', ''), width=350)
        
        dialog_content = ft.Column([
            ft.Text("Edit Company Information", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Container(
                content=ft.Column([
                    name_field,
                    phone_field,
                    email_field,
                    website_field,
                    address_field,
                    city_field,
                    tax_id_field,
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
                height=400,
            ),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save", on_click=save_info, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Company Information"),
            content=ft.Container(content=dialog_content, width=450, height=550, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    # ============ ZOOM METHODS ============
    def zoom_in(self, page: ft.Page):
        self.zoom_level = min(self.zoom_level + 0.1, 2.0)
        self.apply_zoom(page)
    
    def zoom_out(self, page: ft.Page):
        self.zoom_level = max(self.zoom_level - 0.1, 0.5)
        self.apply_zoom(page)
    
    def reset_zoom(self, page: ft.Page):
        self.zoom_level = 1.0
        self.apply_zoom(page)
    
    def apply_zoom(self, page: ft.Page):
        if not self.current_user:
            return
        page.snack_bar = ft.SnackBar(ft.Text(f"Zoom: {int(self.zoom_level * 100)}%"), bgcolor=self.accent_color, duration=1000)
        page.snack_bar.open = True
        if self.current_view == "dashboard":
            self.show_dashboard(page)
        elif self.current_view == "materials":
            self.show_materials_screen(page)
        elif self.current_view == "accessories":
            self.show_accessories(page)
        page.update()
    
    def main(self, page: ft.Page):
        # Initialize scale helper
        self.scale_helper = ScaleHelper(page)
        self.page_ref = page
        
        # FORCE FULL SCREEN
        page.window_width = None
        page.window_height = None
        page.window_maximized = True
        page.window_resizable = True
        page.window_min_width = None
        page.window_min_height = None
        
        page.title = "Store Management System"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = self.bg_color
        page.padding = 0
        page.spacing = 0
        
        # Track zoom level
        self.zoom_level = 1.0
        
        # FORCE INITIAL PAGE UPDATE to get proper width
        page.update()
        
        # Now get width after update
        print(f"Initial page width: {page.width}")
        
        # Handle resize to update scale and refresh views
        def on_resize(e):
            self.scale_helper.update_scale()
            print(f"Resize - new width: {page.width}")
            if self.current_user:
                # Refresh current view with new size
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
        
        page.on_resize = on_resize
        
        init_database()
        self.show_login(page)
        page.update()

    def is_mobile(self, page: ft.Page):
        """Check if running on mobile device"""
        return page.width < 800 if page.width else False        
        def wrap_with_touch_zoom(self, content):
            """Wrap content to enable touch pinch-to-zoom"""
            return ft.Container(
                content=content,
                expand=True,
                on_gesture=self.on_pinch_zoom,
            )

    def on_pinch_zoom(self, e):
        """Handle pinch zoom gesture"""
        if e.type == ft.GestureType.PAN_UPDATE:
            # Detect pinch (when two fingers)
            if e.scale != 1.0:
                new_zoom = self.zoom_level * e.scale
                new_zoom = max(0.5, min(new_zoom, 3.0))
                if new_zoom != self.zoom_level:
                    self.zoom_level = new_zoom
                    self.apply_zoom_to_current_view(e.control.page)
    # ============ LOGIN ============
    def show_login(self, page: ft.Page):
        page.controls.clear()
        
        field_width = 280
        
        email_field = ft.TextField(label="Email", hint_text="your@email.com", width=field_width, bgcolor="#2C2C2C", border_color=self.accent_color)
        password_field = ft.TextField(label="Password", hint_text="••••••••", password=True, can_reveal_password=True, width=field_width, bgcolor="#2C2C2C", border_color=self.accent_color)
        status_text = ft.Text("", color="red", size=12)
        
        def on_login(e):
            user = UserManager.authenticate(email_field.value, password_field.value)
            if user:
                self.current_user = dict(user)
                self.show_dashboard(page)
            else:
                status_text.value = "Invalid email or password!"
                page.update()
        
        def on_guest_login(e):
            self.current_user = {'id': 0, 'name': 'Guest', 'email': 'guest@store.com', 'role': 'guest', 'guest_mode': True}
            self.show_dashboard(page)
        
        logo_exists = os.path.exists(logo_path)
        logo = ft.Image(src=logo_path, width=100, height=100, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=60)
        
        main_layout = ft.Column([
            ft.Text("Welcome", size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Text("Sign in to manage your inventory", size=13, color="#AAAAAA"),
            ft.Container(height=20),
            ft.Container(width=50, height=2, bgcolor=self.accent_color, border_radius=1),
            ft.Container(height=20),
            email_field, ft.Container(height=15),
            password_field, ft.Container(height=15),
            status_text, ft.Container(height=10),
            ft.Row([logo, ft.Container(width=20), ft.FilledButton("Sign In", width=140, height=45, on_click=on_login)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=20, color="#3C3C3C"),
            ft.OutlinedButton("Continue as Guest", width=field_width, height=40, on_click=on_guest_login),
            ft.TextButton("Forgot Password?", on_click=lambda e: None, style=ft.ButtonStyle(color="#888888")),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        
        login_card = ft.Container(content=main_layout, padding=40, bgcolor=None, border_radius=20, width=500)
        centered_login = ft.Container(content=login_card, alignment=ft.alignment.center, expand=True)
        bg_image = ft.Image(src=background_path, fit=ft.ImageFit.COVER) if os.path.exists(background_path) else None
        
        if bg_image:
            page.add(ft.Stack([bg_image, centered_login], expand=True))
        else:
            page.add(centered_login)
        page.update()
    
        # ============ SIDEBAR WITH ZOOM ============
    def create_sidebar(self, page: ft.Page):
        """Create sidebar navigation - NO ZOOM BUTTONS"""
        
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
            self.current_user = None
            self.show_login(page)
        
        logout_btn = ft.Container(
            content=ft.Row([ft.Text("🚪", size=22), ft.Text("Logout", size=15, color="#FF5252")], spacing=12),
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
        
        return ft.Container(
            content=ft.Column([
                ft.Container(content=title_content, padding=25),
                ft.Divider(),
                ft.Column(nav_buttons, spacing=8),
                ft.Container(expand=True),
                ft.Divider(),
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
        """Create bottom navigation bar for mobile devices"""
        
        nav_items = [
            (ft.icons.DASHBOARD, "Home", "dashboard"),
            (ft.icons.INVENTORY, "Materials", "materials"),
            (ft.icons.BUILD, "Parts", "accessories"),
            (ft.icons.QR_CODE_SCANNER, "Scan", "barcode_scanner"),
            (ft.icons.LIST_ALT, "Inventory", "inventory"),
            (ft.icons.PEOPLE, "Users", "users"),
            (ft.icons.SETTINGS, "Settings", "settings"),
            (ft.icons.LOGOUT, "Logout", "logout"),  # Added Logout
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
                # ============ DASHBOARD ============
    def show_dashboard(self, page: ft.Page):
        """Ultra-simple dashboard - GUARANTEED TO WORK"""
        page.controls.clear()
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Get data
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        users = self.dict_list(UserManager.get_all())
        
        # Calculate statistics
        total_materials = len(materials)
        total_accessories = len(accessories)
        total_items = total_materials + total_accessories
        total_stock = sum(m.get('quantity', 0) for m in materials) + sum(a.get('quantity', 0) for a in accessories)
        total_users = len(users)
        
        # Low stock items
        low_stock_materials = [m for m in materials if m.get('quantity', 0) < 10]
        low_stock_accessories = [a for a in accessories if a.get('quantity', 0) < 10]
        total_low_stock = len(low_stock_materials) + len(low_stock_accessories)
        
        # Quality counts
        quality_counts = {"New": 0, "Used": 0, "Damaged": 0, "Repaired": 0}
        for m in materials:
            q = m.get('quality', 'Used')
            quality_counts[q] = quality_counts.get(q, 0) + 1
        for a in accessories:
            q = a.get('quality', 'Used')
            quality_counts[q] = quality_counts.get(q, 0) + 1
        
        # Create a simple Column (NO ListView)
        main_column = ft.Column(spacing=15, expand=True)
        
        # ========== SECTION 1: HEADER ==========
        main_column.controls.append(
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        main_column.controls.append(ft.Text("Welcome back!", size=14, color="#888888"))
        
        # ========== SECTION 2: STATS CARDS ==========
        main_column.controls.append(
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("📦", size=20),
                        ft.Text(str(total_items), size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("Items", size=10, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12, bgcolor=self.accent_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊", size=20),
                        ft.Text(str(total_stock), size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("Stock", size=10, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12, bgcolor=self.success_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("⚠️", size=20),
                        ft.Text(str(total_low_stock), size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("Low", size=10, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12, bgcolor=self.warning_color, border_radius=10, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("👥", size=20),
                        ft.Text(str(total_users), size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("Users", size=10, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=12, bgcolor="#9C27B0", border_radius=10, expand=True,
                ),
            ], spacing=8)
        )
        
        # ========== SECTION 3: QUALITY DISTRIBUTION ==========
        main_column.controls.append(ft.Text("📊 Quality Distribution", size=16, weight=ft.FontWeight.BOLD))
        
        # Create quality cards as simple containers
        quality_container = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(f"🟢 New: {quality_counts.get('New', 0)}", size=14),
                    padding=8, bgcolor=self.card_color, border_radius=8, expand=True,
                ),
                ft.Container(
                    content=ft.Text(f"🟠 Used: {quality_counts.get('Used', 0)}", size=14),
                    padding=8, bgcolor=self.card_color, border_radius=8, expand=True,
                ),
            ], spacing=8),
            margin=ft.margin.only(bottom=5),
        )
        main_column.controls.append(quality_container)
        
        quality_container2 = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(f"🔴 Damaged: {quality_counts.get('Damaged', 0)}", size=14),
                    padding=8, bgcolor=self.card_color, border_radius=8, expand=True,
                ),
                ft.Container(
                    content=ft.Text(f"🔵 Repaired: {quality_counts.get('Repaired', 0)}", size=14),
                    padding=8, bgcolor=self.card_color, border_radius=8, expand=True,
                ),
            ], spacing=8),
        )
        main_column.controls.append(quality_container2)
        
        # ========== SECTION 4: STOCK HEALTH ==========
        healthy_percentage = int(((total_stock - total_low_stock * 10) / total_stock * 100) if total_stock > 0 else 100)
        healthy_percentage = max(0, min(healthy_percentage, 100))
        
        main_column.controls.append(ft.Text("💪 Stock Health", size=16, weight=ft.FontWeight.BOLD))
        main_column.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{healthy_percentage}%", size=24, weight=ft.FontWeight.BOLD, color=self.success_color),
                    ft.ProgressBar(value=healthy_percentage/100, color=self.success_color, bgcolor="#3C3C3C", height=6),
                    ft.Text(f"Low Stock: {total_low_stock} items", size=12, color=self.warning_color),
                ], spacing=5),
                padding=12, bgcolor=self.card_color, border_radius=10,
            )
        )
        
        # ========== SECTION 5: RECENT MATERIALS ==========
        main_column.controls.append(ft.Text("📦 Recent Materials", size=16, weight=ft.FontWeight.BOLD))
        
        if materials:
            for m in materials[:3]:
                main_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("📦", size=18),
                            ft.Text(m.get('name', 'N/A'), size=14, expand=True),
                            ft.Text(f"Qty: {m.get('quantity', 0)}", size=14),
                            ft.Container(
                                content=ft.Text(m.get('quality', 'Used'), size=10, color="white"),
                                bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                border_radius=8,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            ),
                        ]),
                        padding=10, bgcolor="#2C2C2C", border_radius=8,
                    )
                )
            main_column.controls.append(ft.TextButton("View All", on_click=lambda e: self.show_materials_screen(page)))
        else:
            main_column.controls.append(ft.Text("No materials", size=12, color="#888888"))
        
        # ========== SECTION 6: RECENT ACCESSORIES ==========
        main_column.controls.append(ft.Text("🔧 Recent Accessories", size=16, weight=ft.FontWeight.BOLD))
        
        if accessories:
            for a in accessories[:3]:
                main_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🔧", size=18),
                            ft.Text(a.get('name', 'N/A'), size=14, expand=True),
                            ft.Text(f"Qty: {a.get('quantity', 0)}", size=14),
                            ft.Container(
                                content=ft.Text(a.get('quality', 'Used'), size=10, color="white"),
                                bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                                border_radius=8,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            ),
                        ]),
                        padding=10, bgcolor="#2C2C2C", border_radius=8,
                    )
                )
            main_column.controls.append(ft.TextButton("View All", on_click=lambda e: self.show_accessories(page)))
        else:
            main_column.controls.append(ft.Text("No accessories", size=12, color="#888888"))
        
        # ========== SECTION 7: BUTTONS ==========
        main_column.controls.append(ft.Text("Quick Actions", size=16, weight=ft.FontWeight.BOLD))
        
        main_column.controls.append(
            ft.Row([
                ft.ElevatedButton("Add Material", on_click=lambda e: self.open_add_modal(page), expand=True),
                ft.ElevatedButton("Add Part", on_click=lambda e: self.open_add_accessory_modal(page), expand=True),
            ], spacing=8)
        )
        main_column.controls.append(
            ft.Row([
                ft.ElevatedButton("Scan", on_click=lambda e: self.show_barcode_scanner(page), expand=True),
                ft.ElevatedButton("Export", on_click=lambda e: self.export_all_data_simple(page), expand=True),
            ], spacing=8)
        )
        
        # ========== SECTION 8: IMPORT/EXPORT ==========
        main_column.controls.append(ft.Text("Import / Export", size=16, weight=ft.FontWeight.BOLD))
        
        main_column.controls.append(
            ft.Row([
                ft.ElevatedButton("Import CSV", on_click=lambda e: self.show_import_dialog(page), expand=True),
                ft.ElevatedButton("Export PDF",  on_click=lambda e: self.export_inventory_html(page), expand=True),
            ], spacing=8)
        )
        main_column.controls.append(
            ft.Row([
                ft.ElevatedButton("Low Stock PDF", on_click=lambda e: self.export_low_stock_html(page), expand=True,
                                style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], spacing=8)
        )
        
        # Wrap in a Container with Scroll
        main_container = ft.Container(
            content=main_column,
            expand=True,
            padding=15,
        )
        
        # Make it scrollable by wrapping in a Column with scroll
        scrollable_container = ft.Container(
            content=ft.Column([main_container], scroll=ft.ScrollMode.AUTO, expand=True),
            expand=True,
        )
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([scrollable_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, scrollable_container], spacing=0, expand=True))
        
        self.current_view = "dashboard"
        page.update()

    def export_inventory_html(self, page: ft.Page):
        """Export inventory to HTML and open in browser automatically"""
        from datetime import datetime
        import os
        import webbrowser
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            # Calculate totals
            total_materials = len(materials)
            total_accessories = len(accessories)
            total_items = total_materials + total_accessories
            total_stock = sum(m.get('quantity', 0) for m in materials) + sum(a.get('quantity', 0) for a in accessories)
            low_stock_count = len([m for m in materials if m.get('quantity', 0) < 10]) + len([a for a in accessories if a.get('quantity', 0) < 10])
            
            # Create HTML content
            html_content = self.generate_html_report(materials, accessories, total_items, total_stock, low_stock_count, total_materials, total_accessories)
            
            # Save to a temporary file or Downloads folder
            download_dir = self.get_download_path()
            
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(download_dir, f"inventory_report_{timestamp}.html")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Open in web browser immediately
            webbrowser.open(f'file://{os.path.abspath(filename)}')
            
            # Show success message
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Report opened in browser! Saved to: {filename}"),
                bgcolor=self.success_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    def get_download_path(self):
        """Get the appropriate download folder path for the device"""
        import os
        
        # Android devices
        if os.path.exists("/storage/emulated/0/Download"):
            return "/storage/emulated/0/Download/StoreManagement"
        
        # Windows/Mac/Linux desktop
        elif os.path.exists(os.path.expanduser("~/Downloads")):
            return os.path.expanduser("~/Downloads/StoreManagement")
        
        # Fallback to local folder
        else:
            return "exports"

    def generate_html_report(self, materials, accessories, total_items, total_stock, low_stock_count, total_materials, total_accessories):
        """Generate beautiful HTML report content"""
        from datetime import datetime
        
        quality_colors = {
            "New": "#4CAF50",
            "Used": "#FF9800", 
            "Damaged": "#F44336",
            "Repaired": "#2196F3"
        }
        
        html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Inventory Report - Store Management System</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 28px;
                margin-bottom: 10px;
            }}
            .header p {{
                opacity: 0.9;
                font-size: 14px;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                padding: 30px;
                background: #f8f9fa;
            }}
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            .stat-card .icon {{
                font-size: 32px;
                margin-bottom: 10px;
            }}
            .stat-card .value {{
                font-size: 28px;
                font-weight: bold;
                color: #1976D2;
            }}
            .stat-card .label {{
                color: #666;
                font-size: 12px;
                margin-top: 5px;
            }}
            .section {{
                padding: 20px 30px;
            }}
            .section h2 {{
                font-size: 20px;
                margin-bottom: 15px;
                color: #333;
                border-left: 4px solid #1976D2;
                padding-left: 15px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                overflow-x: auto;
                display: block;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
                font-size: 13px;
            }}
            th {{
                background-color: #1976D2;
                color: white;
                font-weight: 600;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: 600;
                color: white;
            }}
            .badge-new {{ background-color: #4CAF50; }}
            .badge-used {{ background-color: #FF9800; }}
            .badge-damaged {{ background-color: #F44336; }}
            .badge-repaired {{ background-color: #2196F3; }}
            .low-stock {{
                color: #F44336;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                background: #f8f9fa;
                color: #666;
                font-size: 12px;
                border-top: 1px solid #eee;
            }}
            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Store Management System</h1>
                <p>Inventory Report - Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="icon">📦</div>
                    <div class="value">{total_items}</div>
                    <div class="label">Total Items</div>
                    <div style="font-size: 11px; color: #888;">{total_materials} Materials, {total_accessories} Accessories</div>
                </div>
                <div class="stat-card">
                    <div class="icon">📊</div>
                    <div class="value">{total_stock}</div>
                    <div class="label">Total Stock Units</div>
                </div>
                <div class="stat-card">
                    <div class="icon">⚠️</div>
                    <div class="value" style="color: #F44336;">{low_stock_count}</div>
                    <div class="label">Low Stock Items</div>
                </div>
            </div>
            
            <div class="section">
                <h2>📦 Materials Inventory ({total_materials} items)</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Code</th>
                                <th>Quantity</th>
                                <th>Quality</th>
                                <th>Location</th>
                                <th>Size</th>
                            </tr>
                        </thead>
                        <tbody>
    """
        
        for m in materials[:200]:
            quantity = m.get('quantity', 0)
            quantity_class = 'low-stock' if quantity < 10 else ''
            quality = m.get('quality', 'Used')
            badge_class = f"badge-{quality.lower()}"
            
            html_content += f"""
                            <tr>
                                <td><strong>{m.get('name', 'N/A')}</strong></td>
                                <td>{m.get('item_code', 'N/A')}</td>
                                <td class="{quantity_class}">{quantity}</td>
                                <td><span class="badge {badge_class}">{quality}</span></td>
                                <td>{m.get('location_ids', 'N/A')}</td>
                                <td>{m.get('size', 'N/A')}</td>
                            </tr>"""
        
        html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="section">
                <h2>🔧 Accessories Inventory ({total_accessories} items)</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Code</th>
                                <th>Quantity</th>
                                <th>Quality</th>
                                <th>Location</th>
                                <th>Price</th>
                            </tr>
                        </thead>
                        <tbody>
    """
        
        for a in accessories[:200]:
            quantity = a.get('quantity', 0)
            quantity_class = 'low-stock' if quantity < 10 else ''
            quality = a.get('quality', 'Used')
            badge_class = f"badge-{quality.lower()}"
            location = a.get('location') or a.get('location_ids') or 'N/A'
            price = a.get('price', 0)
            price_text = f"${price:.2f}" if price else "N/A"
            
            html_content += f"""
                            <tr>
                                <td><strong>{a.get('name', 'N/A')}</strong></td>
                                <td>{a.get('item_code', 'N/A')}</td>
                                <td class="{quantity_class}">{quantity}</td>
                                <td><span class="badge {badge_class}">{quality}</span></td>
                                <td>{location}</td>
                                <td>{price_text}</td>
                            </tr>"""
        
        html_content += f"""
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="footer">
                <p>Generated by Store Management System v1.0</p>
                <p>© {datetime.now().year} All Rights Reserved</p>
            </div>
        </div>
    </body>
    </html>"""
        
        return html_content

    def export_low_stock_html(self, page: ft.Page):
        """Export low stock items to HTML and open in browser"""
        from datetime import datetime
        import os
        import webbrowser
        
        try:
            # Get data
            materials = self.dict_list(MaterialManager.get_all())
            accessories = self.dict_list(AccessoryManager.get_all())
            
            # Filter low stock items
            low_stock_items = []
            for m in materials:
                if m.get('quantity', 0) < 10:
                    low_stock_items.append({
                        'type': 'Material',
                        'name': m.get('name', 'N/A'),
                        'code': m.get('item_code', 'N/A'),
                        'quantity': m.get('quantity', 0),
                        'quality': m.get('quality', 'Used'),
                        'location': m.get('location_ids', 'N/A'),
                    })
            for a in accessories:
                if a.get('quantity', 0) < 10:
                    low_stock_items.append({
                        'type': 'Accessory',
                        'name': a.get('name', 'N/A'),
                        'code': a.get('item_code', 'N/A'),
                        'quantity': a.get('quantity', 0),
                        'quality': a.get('quality', 'Used'),
                        'location': a.get('location') or a.get('location_ids', 'N/A'),
                    })
            
            if not low_stock_items:
                page.snack_bar = ft.SnackBar(
                    ft.Text("No low stock items to export"),
                    bgcolor=self.warning_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
                return
            
            # Generate HTML content (simplified version)
            html_content = self.generate_low_stock_html(low_stock_items)
            
            # Save to Downloads
            download_dir = self.get_download_path()
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(download_dir, f"low_stock_report_{timestamp}.html")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Open in browser
            webbrowser.open(f'file://{os.path.abspath(filename)}')
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Low stock report opened in browser!"),
                bgcolor=self.success_color,
                duration=5000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def generate_low_stock_html(self, low_stock_items):
        """Generate low stock HTML report"""
        from datetime import datetime
        
        html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Low Stock Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; }}
            h1 {{ color: #F44336; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #F44336; color: white; }}
            .critical {{ background-color: #FFEBEE; }}
            .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            @media print {{
                body {{ background: white; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ Low Stock Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total low stock items: {len(low_stock_items)}</p>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Name</th>
                        <th>Code</th>
                        <th>Current Stock</th>
                        <th>Quality</th>
                        <th>Location</th>
                    </tr>
                </thead>
                <tbody>
    """
        
        for item in low_stock_items:
            critical_class = 'critical' if item['quantity'] < 5 else ''
            html_content += f"""
                    <tr class="{critical_class}">
                        <td>{item['type']}</td>
                        <td><strong>{item['name']}</strong></td>
                        <td>{item['code']}</td>
                        <td style="color: #F44336; font-weight: bold;">{item['quantity']}</td>
                        <td>{item['quality']}</td>
                        <td>{item['location']}</td>
                    </tr>"""
        
        html_content += f"""
                </tbody>
            </table>
            <div class="footer">
                <p>Generated by Store Management System</p>
            </div>
        </div>
    </body>
    </html>"""
        
        return html_content
    def create_recent_activity_card(self, recent_items, font_small, font_normal):
        """Create recent activity card"""
        
        activity_list = ft.Column(spacing=8)
        
        if recent_items:
            for item in recent_items[:5]:
                activity_list.controls.append(
                    ft.Row([
                        ft.Text(item['type'], size=18),
                        ft.Column([
                            ft.Text(item['name'], size=font_small, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Added on {item['date']}", size=font_small - 2, color="#888888"),
                        ], spacing=2, expand=True),
                    ], spacing=10)
                )
        else:
            activity_list.controls.append(ft.Text("No recent activity", size=font_small, color="#888888"))
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🕐 Recent Activity", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                activity_list,
            ], spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
            expand=True,
        )

    def create_recent_materials_card(self, page, materials, font_small, font_normal):
        """Create recent materials card"""
        
        materials_list = ft.Column(spacing=8)
        
        if materials:
            for m in materials[:6]:
                materials_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("📦", size=18),
                            ft.Column([
                                ft.Text(m.get('name', 'N/A'), size=font_small, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Stock: {m.get('quantity', 0)} | {m.get('location_ids', 'N/A')}", size=font_small - 2, color="#888888"),
                            ], spacing=2, expand=True),
                            ft.Container(
                                content=ft.Text(m.get('quality', 'Used'), size=font_small - 2, color="white"),
                                bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ], spacing=10),
                        padding=8,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                    )
                )
        else:
            materials_list.controls.append(ft.Text("No materials found", size=font_small, color="#888888"))
        
        materials_list.controls.append(
            ft.TextButton("View All Materials", on_click=lambda e: self.show_materials_screen(page))
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📦 Recent Materials", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                materials_list,
            ], spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
            expand=True,
        )

    def create_recent_accessories_card(self, page, accessories, font_small, font_normal):
        """Create recent accessories card"""
        
        accessories_list = ft.Column(spacing=8)
        
        if accessories:
            for a in accessories[:6]:
                location = a.get('location') or a.get('location_ids') or 'N/A'
                accessories_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🔧", size=18),
                            ft.Column([
                                ft.Text(a.get('name', 'N/A'), size=font_small, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Stock: {a.get('quantity', 0)} | {location}", size=font_small - 2, color="#888888"),
                            ], spacing=2, expand=True),
                            ft.Container(
                                content=ft.Text(a.get('quality', 'Used'), size=font_small - 2, color="white"),
                                bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                                border_radius=10,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ], spacing=10),
                        padding=8,
                        bgcolor="#2C2C2C",
                        border_radius=8,
                    )
                )
        else:
            accessories_list.controls.append(ft.Text("No accessories found", size=font_small, color="#888888"))
        
        accessories_list.controls.append(
            ft.TextButton("View All Accessories", on_click=lambda e: self.show_accessories(page))
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🔧 Recent Accessories", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                accessories_list,
            ], spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
            expand=True,
        )

    def create_import_export_panel(self, page, font_small, font_normal):
        """Create import/export panel"""
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📁 Import / Export", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("📥 Import CSV", on_click=lambda e: self.show_import_dialog(page), expand=True),
                    ft.ElevatedButton("📤 Export CSV", on_click=lambda e: self.export_all_data_simple(page), expand=True, style=ft.ButtonStyle(bgcolor=self.warning_color)),
                ], spacing=10),
                ft.Row([
                    ft.ElevatedButton("📄 Export PDF", on_click=lambda e: self.export_inventory_pdf_dashboard(page), expand=True),
                    ft.ElevatedButton("⚠️ Low Stock PDF", on_click=lambda e: self.export_low_stock_pdf_dashboard(page), expand=True, style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ], spacing=10),
                ft.Text("Supports CSV and PDF formats", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor=self.card_color,
            border_radius=15,
        )
    def show_materials_screen(self, page: ft.Page):
        """Materials screen - Click card to see details in dialog (mobile friendly)"""
        page.controls.clear()
        
        materials = self.dict_list(MaterialManager.get_all())
        nav = self.create_bottom_nav(page)
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Get categories
        categories = ["All"]
        for m in materials:
            cat = m.get('category', 'Uncategorized')
            if cat not in categories:
                categories.append(cat)
        categories.sort()
        
        # Create mutable filter state
        filter_state = {
            'current_quality': "All",
            'current_category': "All",
        }
        
        main_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Title
        main_column.controls.append(
            ft.Text("Materials", size=28, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        
        # Search Field
        search_field = ft.TextField(
            hint_text="Search materials...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
        )
        main_column.controls.append(search_field)
        main_column.controls.append(ft.Container(height=5))
        
        # Quality Filters
        quality_filter_row = ft.Row(spacing=8, wrap=True)
        quality_buttons = {}
        
        def create_quality_handler(label):
            def handler(e):
                filter_state['current_quality'] = label
                color_map = {
                    "All": self.accent_color,
                    "New": self.success_color,
                    "Used": self.warning_color,
                    "Damaged": self.danger_color,
                    "Repaired": self.accent_color,
                }
                for lbl, btn in quality_buttons.items():
                    btn.bgcolor = color_map.get(lbl, self.card_color) if lbl == label else self.card_color
                    btn.update()
                update_cards()
            return handler
        
        for label in ["All", "New", "Used", "Damaged", "Repaired"]:
            btn = ft.Container(
                content=ft.Text(label, size=12, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=12, vertical=5),
                bgcolor=self.accent_color if label == "All" else self.card_color,
                border_radius=20,
                ink=True,
                on_click=create_quality_handler(label),
            )
            quality_buttons[label] = btn
            quality_filter_row.controls.append(btn)
        
        main_column.controls.append(quality_filter_row)
        main_column.controls.append(ft.Container(height=5))
        
        # Category Filter
        category_row = ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        category_filter = ft.Dropdown(
            label="Category",
            width=150,
            options=[ft.dropdown.Option(cat, cat) for cat in categories],
            value="All",
            bgcolor=self.card_color,
        )
        category_row.controls.append(category_filter)
        
        # Category Manager Button
        category_manager_btn = ft.IconButton(
            icon=ft.icons.SETTINGS,
            icon_size=20,
            icon_color=self.accent_color,
            on_click=lambda e: self.show_category_manager(page),
        )
        category_row.controls.append(category_manager_btn)
        
        main_column.controls.append(category_row)
        main_column.controls.append(ft.Container(height=5))
        
        # Cards container
        cards_container = ft.Column(spacing=10)
        
        def update_cards():
            search_query = search_field.value.lower() if search_field.value else ""
            cards_container.controls.clear()
            
            for m in materials:
                # Quality filter
                if filter_state['current_quality'] != "All" and m.get('quality') != filter_state['current_quality']:
                    continue
                # Category filter
                if filter_state['current_category'] != "All" and m.get('category', 'Uncategorized') != filter_state['current_category']:
                    continue
                # Search filter
                if search_query and search_query not in m.get('name', '').lower():
                    continue
                
                cat_name = m.get('category', 'Uncategorized')
                cat_icon = self.get_category_icon(cat_name)
                qty = m.get('quantity', 0)
                qty_color = self.danger_color if qty < 10 else self.text_color
                
                # Store material for dialog
                material_data = m
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(m.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=14, weight=ft.FontWeight.BOLD, color=qty_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=12, color=self.accent_color, expand=True),
                                ft.Container(
                                    content=ft.Text(m.get('quality', 'Used'), size=10, color="white"),
                                    bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ]),
                            ft.Text(f"📍 {m.get('location_ids', 'N/A')}", size=12, color="#888888"),
                        ], spacing=5),
                        padding=15,
                        on_click=lambda e, mat=material_data: self.show_material_detail_dialog(page, mat),
                    ),
                    elevation=3,
                    margin=ft.margin.only(bottom=10),
                )
                cards_container.controls.append(card)
            page.update()
        
        # Category filter handler
        def on_category_change(e):
            filter_state['current_category'] = category_filter.value
            update_cards()
        
        category_filter.on_change = on_category_change
        search_field.on_change = lambda e: update_cards()
        
        # Initial load
        update_cards()
        
        main_column.controls.append(cards_container)
        
        # FAB Button for Add
        add_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_modal(page),
        )
        
        main_container = ft.Container(content=main_column, expand=True, padding=20)
        
        page.add(
            ft.Stack([
                ft.Column([main_container, nav], spacing=0, expand=True),
                ft.Container(content=add_button, right=16, bottom=80),
            ], expand=True)
        )
        
        page.update()
    
    def create_detail_panel(self, material, page):
        """Create the detail panel for selected material with image and category"""
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
        
        # Get category with icon
        category = material.get('category', 'Uncategorized')
        category_icon = self.get_category_icon(category)
        
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
        
        # Build the column with category included
        column_items = [
            ft.Text(material.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
        ]
        
        # Add image if it exists
        if image_display:
            column_items.append(ft.Row([image_display], alignment=ft.MainAxisAlignment.CENTER))
            column_items.append(ft.Container(height=10))
        
        # Add details with category and barcode button
        column_items.extend([
            # Category row
            ft.Row([ft.Text("📁 Category:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(f"{category_icon} {category}", size=12, color=self.accent_color)], spacing=5),
            
            # Code row
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # SHOW BARCODE BUTTON
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, material), 
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
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
            ft.Row([ft.Text("📏 Size:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('size') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Length
            ft.Row([ft.Text("📐 Length:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(str(material.get('length') or "N/A"), size=12, color=self.text_color)], spacing=5),
            
            # Quantity
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(str(material.get('quantity', 0)), size=12, color=self.text_color,
                        weight=ft.FontWeight.BOLD if material.get('quantity', 0) < 10 else None)], spacing=5),
            
            # Location
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('location_ids') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Colors
            ft.Row([ft.Text("🎨 Colors:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(material.get('colors') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # Created
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(created_date, size=12, color=self.text_color)], spacing=5),
            
            # Updated
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(updated_date, size=12, color=self.text_color)], spacing=5),
            
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
    def get_category_icon(self, category):
        """Get icon for category"""
        icons = {
            "Raw Material": "📦",
            "Hardware": "🔩",
            "Tools": "🔧",
            "Electrical": "⚡",
            "Plumbing": "💧",
            "Wood": "🪵",
            "Metal": "⚙️",
            "Plastic": "🧴",
            "Glass": "🔮",
            "Paint": "🎨",
            "Fasteners": "📎",
            "Safety Equipment": "🦺",
            "Packaging": "📦",
            "Office Supplies": "📎",
            "Other": "📁"
        }
        return icons.get(category, "📁")
    
    def filter_materials_by_quality(self, page: ft.Page, filter_type):
        """Filter materials by quality"""
        self.current_material_filter = filter_type
        
        # Update button colors
        color_map = {
            "All": self.accent_color,
            "New": self.success_color,
            "Used": self.warning_color,
            "Damaged": self.danger_color,
            "Repaired": self.accent_color,
        }
        
        for f_type, btn in self.material_filter_buttons.items():
            if f_type == filter_type:
                btn.bgcolor = color_map.get(f_type, self.card_color)
            else:
                btn.bgcolor = self.card_color
            btn.update()
        
        # Update the table
        materials = self.dict_list(MaterialManager.get_all())
        
        if filter_type == "All":
            filtered = materials
        else:
            filtered = [m for m in materials if m.get('quality') == filter_type]
        
        # Apply search if exists
        if hasattr(self, 'material_search_query') and self.material_search_query:
            query = self.material_search_query.lower()
            filtered = [m for m in filtered if query in m.get('name', '').lower() or query in m.get('item_code', '').lower()]
        
        # Update table rows
        self.material_table_rows.controls.clear()
        
        for m in filtered:
            row = ft.Container(
                content=ft.Row([
                    ft.Text(m.get('name', 'N/A'), size=13, weight=ft.FontWeight.BOLD, width=180),
                    ft.Text(m.get('location_ids') or "N/A", size=12, width=120, color="#CCCCCC"),
                    ft.Text(str(m.get('quantity', 0)), size=13, weight=ft.FontWeight.BOLD, width=60,
                        color=self.danger_color if m.get('quantity', 0) < 10 else self.text_color),
                    ft.Container(
                        content=ft.Text(m.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        width=90,
                    ),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.EDIT, icon_size=20, 
                                    on_click=lambda e, mat=m: self.open_edit_modal(page, mat['id'])),
                        ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                    on_click=lambda e, mat=m: self.open_delete_modal(page, mat['id'])),
                        ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                    on_click=lambda e, mat=m: self.show_barcode_dialog(page, mat)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.START),
                padding=ft.padding.symmetric(vertical=10, horizontal=12),
                bgcolor="#2C2C2C",
                border_radius=6,
                ink=True,
                on_click=lambda e, mat=m: self.on_material_select(mat),
            )
            self.material_table_rows.controls.append(row)
        
        # Update detail panel
        if self.selected_material_detail and self.selected_material_detail not in filtered:
            self.selected_material_detail = None
            self.material_detail_panel.content = self.create_detail_panel(None, page)
        
        page.update()

    def on_material_select(self, material):
        """Handle material selection from table"""
        self.selected_material_detail = material
        if hasattr(self, 'material_detail_panel'):
            self.material_detail_panel.content = self.create_detail_panel(material, self.page_ref)
            self.page_ref.update()

                    # ============ ACCESSORIES SCREEN ============
    def show_accessories(self, page: ft.Page):
        """Accessories screen - Click card to see details"""
        page.controls.clear()
        
        accessories = self.dict_list(AccessoryManager.get_all())
        nav = self.create_bottom_nav(page)
        
        # Get categories
        categories = ["All"]
        for a in accessories:
            cat = a.get('category', 'Uncategorized')
            if cat not in categories:
                categories.append(cat)
        categories.sort()
        
        # Create mutable variables using list or dictionary
        filter_state = {
            'current_quality': "All",
            'current_category': "All",
            'search_query': ""
        }
        
        main_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Title
        main_column.controls.append(
            ft.Text("Accessories", size=28, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        
        # Search Field
        search_field = ft.TextField(
            hint_text="Search accessories...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
        )
        main_column.controls.append(search_field)
        main_column.controls.append(ft.Container(height=5))
        
        # Quality Filters
        quality_filter_row = ft.Row(spacing=8, wrap=True)
        quality_buttons = {}
        
        def create_quality_handler(label):
            def handler(e):
                # Update filter state
                filter_state['current_quality'] = label
                # Update button colors
                color_map = {
                    "All": self.accent_color,
                    "New": self.success_color,
                    "Used": self.warning_color,
                    "Damaged": self.danger_color,
                    "Repaired": self.accent_color,
                }
                for lbl, btn in quality_buttons.items():
                    btn.bgcolor = color_map.get(lbl, self.card_color) if lbl == label else self.card_color
                    btn.update()
                update_cards()
            return handler
        
        for label in ["All", "New", "Used", "Damaged", "Repaired"]:
            btn = ft.Container(
                content=ft.Text(label, size=12, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=12, vertical=5),
                bgcolor=self.accent_color if label == "All" else self.card_color,
                border_radius=20,
                ink=True,
                on_click=create_quality_handler(label),
            )
            quality_buttons[label] = btn
            quality_filter_row.controls.append(btn)
        
        main_column.controls.append(quality_filter_row)
        main_column.controls.append(ft.Container(height=5))
        
        # Category Filter
        category_row = ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        category_filter = ft.Dropdown(
            label="Category",
            width=150,
            options=[ft.dropdown.Option(cat, cat) for cat in categories],
            value="All",
            bgcolor=self.card_color,
        )
        category_row.controls.append(category_filter)
        
        # Category Manager Button
        category_manager_btn = ft.IconButton(
            icon=ft.icons.SETTINGS,
            icon_size=20,
            icon_color=self.accent_color,
            on_click=lambda e: self.show_category_manager(page),
        )
        category_row.controls.append(category_manager_btn)
        
        main_column.controls.append(category_row)
        main_column.controls.append(ft.Container(height=5))
        
        # Cards container
        cards_container = ft.Column(spacing=10)
        
        def update_cards():
            search_query = search_field.value.lower() if search_field.value else ""
            cards_container.controls.clear()
            
            for a in accessories:
                # Quality filter
                if filter_state['current_quality'] != "All" and a.get('quality') != filter_state['current_quality']:
                    continue
                # Category filter
                if filter_state['current_category'] != "All" and a.get('category', 'Uncategorized') != filter_state['current_category']:
                    continue
                # Search filter
                if search_query and search_query not in a.get('name', '').lower():
                    continue
                
                cat_name = a.get('category', 'Uncategorized')
                cat_icon = self.get_category_icon(cat_name)
                qty = a.get('quantity', 0)
                qty_color = self.danger_color if qty < 10 else self.text_color
                location = a.get('location') or a.get('location_ids') or 'N/A'
                price = a.get('price', 0)
                price_text = f"${price:.2f}" if price else ""
                
                # Store accessory for dialog
                accessory_data = a
                
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(a.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=14, weight=ft.FontWeight.BOLD, color=qty_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=12, color=self.accent_color, expand=True),
                                ft.Container(
                                    content=ft.Text(a.get('quality', 'Used'), size=10, color="white"),
                                    bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.Text(f"📍 {location}", size=12, color="#888888", expand=True),
                                ft.Text(price_text, size=12, color="#4CAF50"),
                            ]),
                        ], spacing=5),
                        padding=15,
                        on_click=lambda e, acc=accessory_data: self.show_accessory_detail_dialog(page, acc),
                    ),
                    elevation=3,
                    margin=ft.margin.only(bottom=10),
                )
                cards_container.controls.append(card)
            page.update()
        
        # Category filter handler
        def on_category_change(e):
            filter_state['current_category'] = category_filter.value
            update_cards()
        
        category_filter.on_change = on_category_change
        
        # Search handler
        def on_search(e):
            update_cards()
        
        search_field.on_change = on_search
        
        # Initial load
        update_cards()
        
        main_column.controls.append(cards_container)
        
        # FAB Button for Add
        add_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_accessory_modal(page),
        )
        
        main_container = ft.Container(content=main_column, expand=True, padding=20)
        
        page.add(
            ft.Stack([
                ft.Column([main_container, nav], spacing=0, expand=True),
                ft.Container(content=add_button, right=16, bottom=80),
            ], expand=True)
        )
        
        page.update()

    def show_accessory_detail_dialog(self, page: ft.Page, accessory):
        """Show accessory details in a dialog with edit/delete options"""
        
        name = accessory.get('name', 'N/A')
        category = accessory.get('category', 'Uncategorized')
        cat_icon = self.get_category_icon(category)
        quality = accessory.get('quality', 'Used')
        quantity = accessory.get('quantity', 0)
        location = accessory.get('location') or accessory.get('location_ids') or 'N/A'
        price = accessory.get('price', 0)
        price_text = f"${price:.2f}" if price else "N/A"
        notes = accessory.get('notes', 'No notes')
        code = accessory.get('item_code', 'N/A')
        created = str(accessory.get('created_at', ''))[:16] if accessory.get('created_at') else 'N/A'
        updated = str(accessory.get('updated_at', ''))[:16] if accessory.get('updated_at') else 'N/A'
        
        # Get image
        image_path = accessory.get('image_path', '')
        has_image = image_path and os.path.exists(image_path) if image_path else False
        
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
        
        # Build content
        content_items = []
        
        # Image if exists
        if has_image:
            content_items.append(
                ft.Container(
                    content=ft.Image(src=image_path, width=200, height=150, fit=ft.ImageFit.CONTAIN),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        content_items.extend([
            ft.Row([
                ft.Text("📁 Category:", size=14, color="#CCCCCC", width=100),
                ft.Text(f"{cat_icon} {category}", size=14, color=self.accent_color),
            ], spacing=8),
            ft.Row([
                ft.Text("📝 Code:", size=14, color="#CCCCCC", width=100),
                ft.Text(code, size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("🏷️ Quality:", size=14, color="#CCCCCC", width=100),
                ft.Container(
                    content=ft.Text(quality, size=12, color="white"),
                    bgcolor=self.get_quality_color(quality),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                ),
            ], spacing=8),
            ft.Row([
                ft.Text("🔢 Quantity:", size=14, color="#CCCCCC", width=100),
                ft.Text(str(quantity), size=16, weight=ft.FontWeight.BOLD,
                    color=self.danger_color if quantity < 10 else self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("💰 Price:", size=14, color="#CCCCCC", width=100),
                ft.Text(price_text, size=14, color="#4CAF50", weight=ft.FontWeight.BOLD),
            ], spacing=8),
            ft.Row([
                ft.Text("📍 Location:", size=14, color="#CCCCCC", width=100),
                ft.Text(location, size=14, color=self.text_color),
            ], spacing=8),
            ft.Divider(),
            ft.Row([
                ft.Text("📅 Created:", size=13, color="#CCCCCC", width=100),
                ft.Text(created, size=13, color="#888888"),
            ], spacing=8),
            ft.Row([
                ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=100),
                ft.Text(updated, size=13, color="#888888"),
            ], spacing=8),
            ft.Divider(),
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Container(
                content=ft.Text(notes, size=13, color="#888888"),
                padding=10,
                bgcolor="#2C2C2C",
                border_radius=8,
                margin=ft.margin.only(top=5, bottom=10),
            ),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=edit_accessory, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=delete_accessory, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], spacing=10),
            ft.Row([
                ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color)),
            ], spacing=10),
        ])
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(
                content=ft.Column(content_items, spacing=10, scroll=ft.ScrollMode.AUTO),
                width=400,
                height=500,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def on_accessory_select(self, accessory):
        """Handle accessory selection from table"""
        self.selected_accessory_detail = accessory
        if hasattr(self, 'accessory_detail_panel'):
            self.accessory_detail_panel.content = self.create_accessory_detail_panel(accessory, self.page_ref)
            self.page_ref.update()

    def filter_accessories_by_quality(self, page: ft.Page, filter_type):
        """Filter accessories by quality"""
        self.current_accessory_filter = filter_type
        
        # Update button colors
        color_map = {
            "All": self.accent_color,
            "New": self.success_color,
            "Used": self.warning_color,
            "Damaged": self.danger_color,
            "Repaired": self.accent_color,
        }
        
        for f_type, btn in self.accessory_filter_buttons.items():
            if f_type == filter_type:
                btn.bgcolor = color_map.get(f_type, self.card_color)
            else:
                btn.bgcolor = self.card_color
            btn.update()
        
        # Update the table
        accessories = self.dict_list(AccessoryManager.get_all())
        
        if filter_type == "All":
            filtered = accessories
        else:
            filtered = [a for a in accessories if a.get('quality') == filter_type]
        
        # Apply search if exists
        if hasattr(self, 'accessory_search_query') and self.accessory_search_query:
            query = self.accessory_search_query.lower()
            filtered = [a for a in filtered if query in a.get('name', '').lower() or query in a.get('item_code', '').lower()]
        
        # Update table rows
        self.accessory_table_rows.controls.clear()
        
        for a in filtered:
            location = a.get('location') or a.get('location_ids') or 'N/A'
            row = ft.Container(
                content=ft.Row([
                    ft.Text(a.get('name', 'N/A'), size=13, weight=ft.FontWeight.BOLD, width=180),
                    ft.Text(a.get('item_code', 'N/A'), size=12, width=120, color="#CCCCCC"),
                    ft.Text(str(a.get('quantity', 0)), size=13, weight=ft.FontWeight.BOLD, width=60,
                        color=self.danger_color if a.get('quantity', 0) < 10 else self.text_color),
                    ft.Container(
                        content=ft.Text(a.get('quality', 'Used'), size=11, color="white"),
                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        width=90,
                    ),
                    ft.Text(location, size=12, width=120, color="#CCCCCC"),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.EDIT, icon_size=20, 
                                    on_click=lambda e, acc=a: self.open_edit_accessory_modal(page, acc['id'])),
                        ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                    on_click=lambda e, acc=a: self.open_delete_accessory_modal(page, acc['id'])),
                        ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                    on_click=lambda e, acc=a: self.show_barcode_dialog(page, acc)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.START),
                padding=ft.padding.symmetric(vertical=10, horizontal=12),
                bgcolor="#2C2C2C",
                border_radius=6,
                ink=True,
                on_click=lambda e, acc=a: self.on_accessory_select(acc),
            )
            self.accessory_table_rows.controls.append(row)
        
        # Update detail panel
        if self.selected_accessory_detail and self.selected_accessory_detail not in filtered:
            self.selected_accessory_detail = None
            self.accessory_detail_panel.content = self.create_accessory_detail_panel(None, page)
        
        page.update()

    def create_accessory_detail_panel(self, accessory, page):
        """Create the detail panel for selected accessory with image and category"""
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
        
        # Get location and price
        location = accessory.get('location') or accessory.get('location_ids') or "N/A"
        price_value = accessory.get('price', 0)
        price_text = f"${price_value:.2f}" if price_value else "N/A"
        
        # Get category with icon
        category = accessory.get('category', 'Uncategorized')
        category_icon = self.get_category_icon(category)
        
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
        
        # Add details with category
        column_items.extend([
            # Category row
            ft.Row([ft.Text("📁 Category:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(f"{category_icon} {category}", size=12, color=self.accent_color)], spacing=5),
            
            # Code row
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(accessory.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            
            # SHOW BARCODE BUTTON
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, accessory), 
                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
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
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(str(accessory.get('quantity', 0)), size=12, color=self.text_color,
                        weight=ft.FontWeight.BOLD if accessory.get('quantity', 0) < 10 else None)], spacing=5),
            
            # Price
            ft.Row([ft.Text("💰 Price:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(price_text, size=12, color="#4CAF50")], spacing=5),
            
            # Location
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(location, size=12, color=self.text_color)], spacing=5),
            
            # Created
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(created_date, size=12, color=self.text_color)], spacing=5),
            
            # Updated
            ft.Row([ft.Text("🔄 Updated:", size=12, color="#CCCCCC", width=80), 
                    ft.Text(updated_date, size=12, color=self.text_color)], spacing=5),
            
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
        """Open add accessory modal - Simplified working version"""
        
        def close_modal(e):
            page.dialog.open = False
            page.update()
        
        name_field = ft.TextField(label="Name", width=300, bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", width=300, bgcolor=self.card_color, value="0")
        price_field = ft.TextField(label="Price", width=300, bgcolor=self.card_color, value="0.00")
        quality_field = ft.Dropdown(
            label="Quality",
            width=300,
            options=[
                ft.dropdown.Option("New"),
                ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"),
                ft.dropdown.Option("Repaired"),
            ],
            value="New",
            bgcolor=self.card_color,
        )
        location_field = ft.TextField(label="Location", width=300, bgcolor=self.card_color)
        
        def save_accessory(e):
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            import random
            import string
            barcode = ''.join(random.choices(string.digits, k=13))
            
            data = {
                'name': name_field.value,
                'quantity': int(quantity_field.value) if quantity_field.value else 0,
                'price': float(price_field.value) if price_field.value else 0.0,
                'quality': quality_field.value,
                'location': location_field.value,
                'barcode_value': barcode,
                'category': 'Uncategorized',
            }
            
            result = AccessoryManager.create(data)
            
            if result:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_accessories(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error creating accessory!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Add New Accessory", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            quantity_field,
            price_field,
            quality_field,
            location_field,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_modal),
                ft.FilledButton("Save", on_click=save_accessory, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add Accessory"),
            content=ft.Container(content=dialog_content, width=400, height=500, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def open_edit_accessory_modal(self, page: ft.Page, accessory_id):
        """Open edit accessory modal - Simplified working version"""
        
        accessory = AccessoryManager.get_by_id(accessory_id)
        if not accessory:
            page.snack_bar = ft.SnackBar(ft.Text("Accessory not found!"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()
            return
        
        accessory_dict = dict(accessory)
        
        def close_modal(e):
            page.dialog.open = False
            page.update()
        
        name_field = ft.TextField(label="Name", value=accessory_dict.get('name', ''), width=300, bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", value=str(accessory_dict.get('quantity', 0)), width=300, bgcolor=self.card_color)
        price_field = ft.TextField(label="Price", value=str(accessory_dict.get('price', 0)), width=300, bgcolor=self.card_color)
        quality_field = ft.Dropdown(
            label="Quality",
            width=300,
            options=[
                ft.dropdown.Option("New"),
                ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"),
                ft.dropdown.Option("Repaired"),
            ],
            value=accessory_dict.get('quality', 'New'),
            bgcolor=self.card_color,
        )
        location_field = ft.TextField(label="Location", value=accessory_dict.get('location', ''), width=300, bgcolor=self.card_color)
        
        def update_accessory(e):
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            data = {
                'name': name_field.value,
                'quantity': int(quantity_field.value) if quantity_field.value else 0,
                'price': float(price_field.value) if price_field.value else 0.0,
                'quality': quality_field.value,
                'location': location_field.value,
            }
            
            result = AccessoryManager.update(accessory_id, data)
            
            if result:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Updated: {name_field.value}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_accessories(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error updating accessory!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Edit Accessory", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            quantity_field,
            price_field,
            quality_field,
            location_field,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_modal),
                ft.FilledButton("Update", on_click=update_accessory, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Accessory"),
            content=ft.Container(content=dialog_content, width=400, height=500, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def open_delete_accessory_modal(self, page: ft.Page, accessory_id):
        """Open delete modal for accessory"""
        accessory = AccessoryManager.get_by_id(accessory_id)
        if not accessory:
            return
        
        accessory_dict = dict(accessory)
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            # Delete the accessory from database
            AccessoryManager.delete(accessory_id)
            
            # Also delete image file if exists
            image_path = accessory_dict.get('image_path')
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
            
            page.overlay.clear()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Deleted: {accessory_dict.get('name', 'item')}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            self.show_accessories(page)
            page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Divider(),
                        ft.Text(f"Are you sure you want to delete:", size=14),
                        ft.Text(f"'{accessory_dict.get('name', 'item')}'?", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.Text("This action cannot be undone!", size=12, color="#888888"),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Yes, Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=15),
                    padding=20,
                    width=400,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()
    def show_accessory_detail_dialog(self, page: ft.Page, accessory):
        """Show detailed view of accessory in a modal dialog"""
        
        is_mobile = page.width < 800 if page.width else False
        
        created_date = str(accessory.get('created_at', ''))[:16] if accessory.get('created_at') else 'N/A'
        updated_date = str(accessory.get('updated_at', ''))[:16] if accessory.get('updated_at') else 'N/A'
        
        location = accessory.get('location') or accessory.get('location_ids') or 'N/A'
        price = accessory.get('price', 0)
        price_text = f"${price:.2f}" if price else "N/A"
        
        has_image = False
        image_path = accessory.get('image_path', '')
        if image_path and os.path.exists(image_path):
            has_image = True
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_accessory(e):
            page.dialog.open = False
            self.open_edit_accessory_modal(page, accessory['id'])
        
        def delete_accessory(e):
            page.dialog.open = False
            self.open_delete_accessory_modal(page, accessory['id'])
        
        def show_barcode(e):
            self.show_barcode_dialog(page, accessory)
        
        content_items = []
        
        if has_image:
            content_items.append(
                ft.Container(
                    content=ft.Image(src=image_path, width=200, height=150, fit=ft.ImageFit.CONTAIN),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        else:
            content_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.IMAGE, size=50, color="#888888"),
                        ft.Text("No Image", size=12, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        content_items.extend([
            ft.Divider(),
            ft.Row([
                ft.Text("📝 Code:", size=14, color="#CCCCCC", width=80),
                ft.Text(accessory.get('item_code') or "N/A", size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("🏷️ Quality:", size=14, color="#CCCCCC", width=80),
                ft.Container(
                    content=ft.Text(accessory.get('quality', 'Used'), size=12, color="white"),
                    bgcolor=self.get_quality_color(accessory.get('quality', 'Used')),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                ),
            ], spacing=8),
            ft.Row([
                ft.Text("🔢 Quantity:", size=14, color="#CCCCCC", width=80),
                ft.Text(str(accessory.get('quantity', 0)), size=16, weight=ft.FontWeight.BOLD,
                    color=self.danger_color if accessory.get('quantity', 0) < 10 else self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("💰 Price:", size=14, color="#CCCCCC", width=80),
                ft.Text(price_text, size=14, color="#4CAF50", weight=ft.FontWeight.BOLD),
            ], spacing=8),
            ft.Row([
                ft.Text("📍 Location:", size=14, color="#CCCCCC", width=80),
                ft.Text(location, size=14, color=self.text_color),
            ], spacing=8),
            ft.Divider(),
            ft.Row([
                ft.Text("📅 Created:", size=13, color="#CCCCCC", width=80),
                ft.Text(created_date, size=13, color="#888888"),
            ], spacing=8),
            ft.Row([
                ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=80),
                ft.Text(updated_date, size=13, color="#888888"),
            ], spacing=8),
            ft.Divider(),
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Container(
                content=ft.Text(accessory.get('notes') or "No notes", size=13, color="#888888"),
                padding=10,
                bgcolor="#2C2C2C",
                border_radius=8,
                margin=ft.margin.only(top=5, bottom=10),
            ),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=edit_accessory, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=delete_accessory, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], spacing=10),
            ft.Row([
                ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color)),
            ], spacing=10),
        ])
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(accessory.get('name', 'Accessory Details'), size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(
                content=ft.Column(content_items, spacing=10, scroll=ft.ScrollMode.AUTO),
                width=400 if not is_mobile else page.width - 40,
                height=550,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
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
    
    def show_material_detail_dialog(self, page: ft.Page, material):
        """Show material details in a dialog with edit/delete options (Like Accessories)"""
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Dialog dimensions
        if is_mobile:
            dialog_width = page.width - 40
            dialog_height = 550
        else:
            dialog_width = 450
            dialog_height = 550
        
        # Get material data
        name = material.get('name', 'N/A')
        category = material.get('category', 'Uncategorized')
        cat_icon = self.get_category_icon(category)
        quality = material.get('quality', 'Used')
        quantity = material.get('quantity', 0)
        location = material.get('location_ids', 'N/A')
        colors = material.get('colors', 'N/A')
        size = material.get('size', 'N/A')
        length = material.get('length', 'N/A')
        notes = material.get('notes', 'No notes')
        code = material.get('item_code', 'N/A')
        created = str(material.get('created_at', ''))[:16] if material.get('created_at') else 'N/A'
        updated = str(material.get('updated_at', ''))[:16] if material.get('updated_at') else 'N/A'
        
        # Get image
        image_path = material.get('image_path', '')
        has_image = False
        if image_path and os.path.exists(image_path):
            has_image = True
        
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
        
        # Build content items
        content_items = []
        
        # Image if exists
        if has_image:
            content_items.append(
                ft.Container(
                    content=ft.Image(src=image_path, width=200, height=150, fit=ft.ImageFit.CONTAIN),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        else:
            content_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.IMAGE, size=50, color="#888888"),
                        ft.Text("No Image", size=12, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=10),
                )
            )
        
        content_items.extend([
            ft.Divider(),
            ft.Row([
                ft.Text("📁 Category:", size=14, color="#CCCCCC", width=100),
                ft.Text(f"{cat_icon} {category}", size=14, color=self.accent_color),
            ], spacing=8),
            ft.Row([
                ft.Text("📝 Code:", size=14, color="#CCCCCC", width=100),
                ft.Text(code, size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color)),
            ], spacing=10),
            ft.Row([
                ft.Text("🏷️ Quality:", size=14, color="#CCCCCC", width=100),
                ft.Container(
                    content=ft.Text(quality, size=12, color="white"),
                    bgcolor=self.get_quality_color(quality),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                ),
            ], spacing=8),
            ft.Row([
                ft.Text("🔢 Quantity:", size=14, color="#CCCCCC", width=100),
                ft.Text(str(quantity), size=16, weight=ft.FontWeight.BOLD,
                    color=self.danger_color if quantity < 10 else self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("📍 Location:", size=14, color="#CCCCCC", width=100),
                ft.Text(location, size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("📏 Size:", size=14, color="#CCCCCC", width=100),
                ft.Text(size, size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("📐 Length:", size=14, color="#CCCCCC", width=100),
                ft.Text(str(length), size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("🎨 Colors:", size=14, color="#CCCCCC", width=100),
                ft.Text(colors, size=14, color=self.text_color),
            ], spacing=8),
            ft.Divider(),
            ft.Row([
                ft.Text("📅 Created:", size=13, color="#CCCCCC", width=100),
                ft.Text(created, size=13, color="#888888"),
            ], spacing=8),
            ft.Row([
                ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=100),
                ft.Text(updated, size=13, color="#888888"),
            ], spacing=8),
            ft.Divider(),
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Container(
                content=ft.Text(notes, size=13, color="#888888"),
                padding=10,
                bgcolor="#2C2C2C",
                border_radius=8,
                margin=ft.margin.only(top=5, bottom=10),
            ),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=edit_material, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color)),
                ft.ElevatedButton("🗑️ DELETE", on_click=delete_material, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
            ], spacing=10),
        ])
        
        # Create scrollable content
        scrollable_content = ft.Column(content_items, spacing=10, scroll=ft.ScrollMode.AUTO, height=dialog_height - 80)
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable_content, width=dialog_width, padding=15),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_barcode_dialog(self, page: ft.Page, item):
        """Show barcode dialog for material or accessory"""
        import webbrowser
        import tempfile
        
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        item_name = item.get('name', 'Item')
        item_type = "Material" if 'location_ids' in item else "Accessory"
        
        # Create barcode image URL
        barcode_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_text}&code=Code128&dpi=120"
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def print_barcode(e):
            # Create HTML content for printing
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
            content=ft.Container(content=dialog_content, width=350, height=320, padding=15),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
                ft.FilledButton("🖨️ Print", on_click=print_barcode, style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ],
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def open_add_modal(self, page: ft.Page):
        """STEP 5: Add Category button only - Test if button dialog works"""
        
        import random
        import string
        
        print("=" * 50)
        print("STEP 5: Testing Category Button")
        print("=" * 50)
        
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
        field_width = page.width - 60 if is_mobile and page.width else 350
        dialog_width = page.width - 40 if is_mobile and page.width else 450
        
        # Store selected category
        selected_category = "Raw Material"
        
        # Category Button
        category_button = ft.ElevatedButton(
            content=ft.Row([
                ft.Text("📦", size=16),
                ft.Text(selected_category, size=14),
                ft.Icon(ft.icons.ARROW_DROP_DOWN, size=18),
            ], spacing=8),
            style=ft.ButtonStyle(bgcolor=self.card_color, color=self.text_color),
        )
        
        def show_category_dialog(e):
            print("DEBUG: Category button clicked!")
            
            def select_category(name, icon):
                nonlocal selected_category
                selected_category = name
                category_button.content = ft.Row([
                    ft.Text(icon, size=16),
                    ft.Text(name, size=14),
                    ft.Icon(ft.icons.ARROW_DROP_DOWN, size=18),
                ], spacing=8)
                page.update()
                category_dialog.open = False
                page.update()
                print(f"DEBUG: Selected category: {name}")
            
            # Simple category list
            categories = [
                ("📦", "Raw Material"),
                ("🔩", "Hardware"),
                ("🔧", "Tools"),
                ("⚡", "Electrical"),
                ("💧", "Plumbing"),
                ("🪵", "Wood"),
                ("⚙️", "Metal"),
                ("📁", "Other"),
            ]
            
            category_items = []
            for icon, name in categories:
                is_selected = (name == selected_category)
                category_items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(icon, size=20),
                            ft.Text(name, size=14, expand=True),
                            ft.Icon(ft.icons.CHECK, size=16, color=self.success_color, visible=is_selected),
                        ], spacing=10),
                        padding=12,
                        on_click=lambda e, n=name, i=icon: select_category(n, i),
                        ink=True,
                    )
                )
            
            category_dialog = ft.AlertDialog(
                title=ft.Text("Select Category", size=16, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column(category_items, spacing=5, scroll=ft.ScrollMode.AUTO),
                    width=300,
                    height=400,
                    padding=10,
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda e: setattr(category_dialog, 'open', False)),
                ],
            )
            
            page.dialog = category_dialog
            category_dialog.open = True
            page.update()
        
        category_button.on_click = show_category_dialog
        
        # Simple form fields
        name_field = ft.TextField(label="Name *", width=field_width, bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity", width=field_width, bgcolor=self.card_color, value="0")
        location_field = ft.TextField(label="Location", width=field_width, bgcolor=self.card_color)
        barcode_field = ft.TextField(label="Barcode", width=field_width, bgcolor=self.card_color, value=generate_barcode(), read_only=True)
        
        def close_dialog(e):
            print("Cancel clicked")
            page.dialog.open = False
            page.update()
        
        def save_material(e):
            print("=" * 50)
            print(f"Save clicked!")
            print(f"  Name: {name_field.value}")
            print(f"  Category: {selected_category}")
            print(f"  Quantity: {quantity_field.value}")
            print(f"  Location: {location_field.value}")
            print("=" * 50)
            
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            data = {
                'name': name_field.value,
                'category': selected_category,
                'quantity': int(quantity_field.value) if quantity_field.value else 0,
                'location_ids': location_field.value,
                'barcode_value': barcode_field.value,
                'quality': 'New',
            }
            
            result = MaterialManager.create(data)
            
            if result:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value} (Category: {selected_category})"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_materials_screen(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error creating material!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        # Simple layout
        dialog_content = ft.Column([
            ft.Text("Add New Material", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            ft.Text("Category", size=12, color="#888888"),
            category_button,
            ft.Container(height=5),
            quantity_field,
            location_field,
            barcode_field,
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Save", on_click=save_material, 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=15),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def open_edit_modal(self, page: ft.Page, material_id):
        """Edit material using full-screen dialog - Best for mobile with many fields"""
        
        import os
        import shutil
        from datetime import datetime
        import sqlite3
        from database import DB_PATH
        
        material = MaterialManager.get_by_id(material_id)
        if not material:
            page.snack_bar = ft.SnackBar(ft.Text("Material not found!"), bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()
            return
        
        material_dict = dict(material)
        
        is_mobile = page.width < 800 if page.width else False
        
        # Full width on mobile
        if is_mobile:
            field_width = page.width - 40 if page.width else 340
            dialog_width = page.width - 20 if page.width else 380
            preview_size = 100
        else:
            field_width = 350
            dialog_width = 500
            preview_size = 120
        
        # Create images folder
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
        # Get categories
        current_user_id = self.current_user.get('id') if self.current_user else 0
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name, icon FROM custom_categories WHERE user_id = ? OR user_id IS NULL ORDER BY name", (current_user_id,))
        custom_cats = cursor.fetchall()
        conn.close()
        
        predefined_categories = [
            "Raw Material", "Hardware", "Tools", "Electrical", "Plumbing",
            "Wood", "Metal", "Plastic", "Glass", "Paint", "Fasteners",
            "Safety Equipment", "Packaging", "Office Supplies", "Other"
        ]
        
        all_categories = []
        for cat in predefined_categories:
            all_categories.append({"name": cat, "icon": self.get_category_icon(cat)})
        
        for cat in custom_cats:
            cat_name = cat[0]
            cat_icon = cat[1] if len(cat) > 1 else "📁"
            if cat_name not in [c["name"] for c in all_categories]:
                all_categories.append({"name": cat_name, "icon": cat_icon})
        
        all_categories.sort(key=lambda x: x["name"])
        
        # Form fields
        name_field = ft.TextField(label="Name *", value=material_dict.get('name', ''), width=field_width, bgcolor=self.card_color)
        
        category_dropdown = ft.Dropdown(
            label="Category",
            width=field_width,
            options=[ft.dropdown.Option(cat["name"], f"{cat['icon']} {cat['name']}") for cat in all_categories],
            value=material_dict.get('category', 'Raw Material'),
            bgcolor=self.card_color,
        )
        
        quantity_field = ft.TextField(label="Quantity", value=str(material_dict.get('quantity', 0)), width=field_width, bgcolor=self.card_color)
        
        size_field = ft.TextField(label="Size", value=material_dict.get('size') or "", width=field_width, bgcolor=self.card_color, hint_text="e.g., 34 1/2 or 24.5")
        length_field = ft.TextField(label="Length (auto)", value=str(material_dict.get('length') or ""), width=field_width, bgcolor=self.card_color, read_only=True)
        
        quality_field = ft.Dropdown(
            label="Quality", width=field_width,
            options=[
                ft.dropdown.Option("New"),
                ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"),
                ft.dropdown.Option("Repaired"),
            ],
            value=material_dict.get('quality', 'New'),
            bgcolor=self.card_color,
        )
        
        location_field = ft.TextField(label="Location", value=material_dict.get('location_ids') or "", width=field_width, bgcolor=self.card_color)
        color_field = ft.TextField(label="Colors", value=material_dict.get('colors') or "", width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", value=material_dict.get('notes', ''), width=field_width, bgcolor=self.card_color, multiline=True, min_lines=2)
        
        barcode_field = ft.TextField(label="Barcode", width=field_width, bgcolor=self.card_color, value=material_dict.get('barcode_value', ''), read_only=True)
        
        # Image handling
        current_image_path = material_dict.get('image_path', '')
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
        image_preview = ft.Container(
            content=ft.Column([
                ft.Text("📷", size=40),
                ft.Text("No Image", size=10, color="#888888"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            width=preview_size, height=preview_size - 20,
            bgcolor="#2C2C2C", border_radius=8,
        )
        
        if has_current_image:
            try:
                image_preview.content = ft.Column([
                    ft.Image(src=current_image_path, width=preview_size - 10, height=preview_size - 30, fit=ft.ImageFit.CONTAIN),
                    ft.Text("Current image", size=8, color=self.accent_color),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            except:
                pass
        
        selected_temp_image = None
        delete_current = False
        
        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_temp_image, delete_current
            if e.files:
                file = e.files[0]
                selected_temp_image = file.path
                delete_current = False
                try:
                    image_preview.content = ft.Column([
                        ft.Image(src=selected_temp_image, width=preview_size - 10, height=preview_size - 30, fit=ft.ImageFit.CONTAIN),
                        ft.Text("New image selected", size=8, color=self.success_color),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
                    page.update()
                except:
                    pass
        
        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)
        
        def upload_image(e):
            image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])
        
        def delete_image(e):
            nonlocal delete_current, selected_temp_image
            delete_current = True
            selected_temp_image = None
            image_preview.content = ft.Column([
                ft.Text("📷", size=40),
                ft.Text("Image will be deleted", size=10, color=self.danger_color),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
            page.update()
        
        upload_btn = ft.TextButton("📁 Upload New", on_click=upload_image)
        delete_btn = ft.TextButton("🗑️ Delete", on_click=delete_image, style=ft.ButtonStyle(color=self.danger_color))
        
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
            barcode_field.value = barcode_without_checksum + str(checksum)
            page.update()
        
        regenerate_btn = ft.TextButton("🔄 New Barcode", on_click=regenerate_barcode)
        
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
        update_length(None)
        
        def save_uploaded_image():
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"material_{material_id}_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                return new_path
            return None
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def update_material(e):
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            final_image_path = current_image_path if not delete_current else None
            
            if selected_temp_image:
                saved_path = save_uploaded_image()
                if saved_path:
                    final_image_path = saved_path
                    if current_image_path and os.path.exists(current_image_path) and not delete_current:
                        try:
                            os.remove(current_image_path)
                        except:
                            pass
            elif delete_current:
                if current_image_path and os.path.exists(current_image_path):
                    try:
                        os.remove(current_image_path)
                    except:
                        pass
            
            size_value = size_field.value
            length_value = self.convert_size_to_length(size_value) if size_value else None
            
            data = {
                'name': name_field.value,
                'category': category_dropdown.value,
                'quantity': int(quantity_field.value) if quantity_field.value else 0,
                'size': size_value,
                'length': length_value,
                'quality': quality_field.value,
                'location_ids': location_field.value,
                'colors': color_field.value,
                'notes': notes_field.value,
                'barcode_value': barcode_field.value,
                'image_path': final_image_path,
            }
            
            result = MaterialManager.update(material_id, data)
            
            if result:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Updated: {name_field.value}"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_materials_screen(page)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Error updating material!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        image_buttons_row = ft.Row([upload_btn, delete_btn], spacing=10)
        
        # Create scrollable content
        scroll_content = ft.Column([
            name_field,
            category_dropdown,
            quantity_field,
            size_field,
            length_field,
            quality_field,
            location_field,
            color_field,
            barcode_field,
            regenerate_btn,
            image_buttons_row,
            image_preview,
            notes_field,
        ], spacing=12, scroll=ft.ScrollMode.AUTO)
        
        # For mobile, use full height
        content_height = page.height - 100 if is_mobile and page.height else 500
        
        # Dialog content with proper layout
        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Material", size=20, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.icons.CLOSE, on_click=close_dialog),
            ]),
            ft.Divider(),
            ft.Container(
                content=scroll_content,
                height=content_height,
            ),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog, expand=True),
                ft.FilledButton("Update", on_click=update_material, 
                            style=ft.ButtonStyle(bgcolor=self.success_color), expand=True),
            ], spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=dialog_content, width=dialog_width, padding=15),
            modal=True,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def open_delete_modal(self, page: ft.Page, material_id):
        """Open delete modal"""
        material = MaterialManager.get_by_id(material_id)
        if not material:
            return
        
        material_dict = dict(material)
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            # Delete the material from database
            MaterialManager.delete(material_id)
            
            # Also delete image file if exists
            image_path = material_dict.get('image_path')
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
            
            page.overlay.clear()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Deleted: {material_dict.get('name', 'item')}"),
                bgcolor=self.danger_color,
                duration=3000
            )
            page.snack_bar.open = True
            # Refresh the materials screen
            self.show_materials_screen(page)
            page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("🗑️ Confirm Delete", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Divider(),
                        ft.Text(f"Are you sure you want to delete:", size=14),
                        ft.Text(f"'{material_dict.get('name', 'item')}'?", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.Text("This action cannot be undone!", size=12, color="#888888"),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Yes, Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color)),
                        ], alignment=ft.MainAxisAlignment.END, spacing=10),
                    ], spacing=15),
                    padding=20,
                    width=400,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
        page.update()

    def show_barcode_scanner(self, page: ft.Page):
        """Show barcode scanner - FULLY WORKING with camera support"""
        page.controls.clear()
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Font sizes
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
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Scanner state
        current_item = None
        current_item_type = None
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Text("📷 Barcode Scanner", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # ========== BARCODE INPUT CARD ==========
        barcode_input = ft.TextField(
            hint_text="Enter barcode number",
            width=page.width - 60 if is_mobile else 400,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_align=ft.TextAlign.CENTER,
            text_size=font_normal,
            prefix_icon=ft.icons.QR_CODE_SCANNER,
        )
        
        status_text = ft.Text("", size=font_small, color="#888888")
        
        # ========== CAMERA SCANNER BUTTON ==========
        # This uses the phone's built-in camera via URL scheme
        camera_button = ft.ElevatedButton(
            "📷 Scan with Camera",
            icon=ft.icons.CAMERA_ALT,
            on_click=lambda e: self.open_native_camera_scanner(page, barcode_input),
            style=ft.ButtonStyle(bgcolor=self.accent_color),
            width=250,
        )
        
        # ========== SEARCH RESULTS CARD ==========
        result_container = ft.Container(
            content=ft.Column([
                ft.Text("Scan Results", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Text("No item scanned yet", size=font_small, color="#888888", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=12,
            visible=False,
        )
        
        # ========== UPDATE STOCK CARD ==========
        update_container = ft.Container(
            content=ft.Column([
                ft.Text("✏️ Update Stock", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Divider(),
                ft.Row([
                    ft.Text("Current Quantity:", size=font_small, color="#CCCCCC", expand=True),
                    ft.Text("0", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ]),
                ft.Row([
                    ft.Text("Adjustment:", size=font_small, color="#CCCCCC", expand=True),
                    ft.TextField(
                        hint_text="+10 or -5",
                        width=120,
                        bgcolor=self.card_color,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ]),
                ft.Row([
                    ft.Text("New Quality:", size=font_small, color="#CCCCCC", expand=True),
                    ft.Dropdown(
                        width=120,
                        options=[
                            ft.dropdown.Option("New"),
                            ft.dropdown.Option("Used"),
                            ft.dropdown.Option("Damaged"),
                            ft.dropdown.Option("Repaired"),
                        ],
                        value="New",
                        bgcolor=self.card_color,
                    ),
                ]),
                ft.Row([
                    ft.ElevatedButton("✅ Apply Update", expand=True, style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ft.OutlinedButton("❌ Cancel", expand=True),
                ], spacing=10),
            ], spacing=10),
            padding=15,
            bgcolor=self.card_color,
            border_radius=12,
            visible=False,
            margin=ft.margin.only(top=15),
        )
        
        # Create input card
        input_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Enter Barcode", size=font_normal, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10),
                    barcode_input,
                    ft.Container(height=10),
                    ft.Row([
                        ft.ElevatedButton("🔍 Search", on_click=None, expand=True),
                        camera_button,
                    ], spacing=10),
                    ft.Container(height=5),
                    status_text,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                padding=20,
            ),
            elevation=2,
        )
        
        scroll_content.controls.append(input_card)
        scroll_content.controls.append(result_container)
        scroll_content.controls.append(update_container)
        
        # ========== SEARCH FUNCTION ==========
        def search_barcode(barcode_value):
            nonlocal current_item, current_item_type
            
            if not barcode_value:
                status_text.value = "⚠️ Please enter a barcode"
                status_text.color = self.warning_color
                page.update()
                return False
            
            status_text.value = f"🔍 Searching for: {barcode_value}"
            status_text.color = self.warning_color
            page.update()
            
            # Search in accessories first
            item = AccessoryManager.get_by_barcode(barcode_value)
            if item:
                current_item = dict(item)
                current_item_type = 'accessory'
                display_item_result(current_item, 'accessory')
                status_text.value = "✅ Item found!"
                status_text.color = self.success_color
                return True
            
            # Search in materials
            item = MaterialManager.get_by_barcode(barcode_value)
            if item:
                current_item = dict(item)
                current_item_type = 'material'
                display_item_result(current_item, 'material')
                status_text.value = "✅ Item found!"
                status_text.color = self.success_color
                return True
            
            # Not found
            status_text.value = f"❌ No item found"
            status_text.color = self.danger_color
            result_container.visible = True
            result_container.content = ft.Column([
                ft.Text("Scan Results", size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Icon(ft.icons.WARNING_AMBER, size=50, color=self.warning_color),
                ft.Text("Item Not Found", size=font_normal, weight=ft.FontWeight.BOLD, color=self.warning_color),
                ft.Text(f"Barcode: {barcode_value}", size=font_small, color="#888888"),
                ft.Container(height=10),
                ft.Row([
                    ft.ElevatedButton("Add New Item", on_click=lambda e: add_item_from_barcode(barcode_value), expand=True),
                ], spacing=10),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            update_container.visible = False
            page.update()
            return False
        
        # ========== DISPLAY ITEM RESULT ==========
        def display_item_result(item, item_type):
            is_accessory = (item_type == 'accessory')
            location = item.get('location', 'N/A') if is_accessory else item.get('location_ids', 'N/A')
            item_type_name = "🔧 Accessory" if is_accessory else "📦 Material"
            quality = item.get('quality', 'Used')
            quantity = item.get('quantity', 0)
            
            result_container.visible = True
            result_container.content = ft.Column([
                ft.Text("✅ Item Found", size=font_normal, weight=ft.FontWeight.BOLD, color=self.success_color),
                ft.Divider(),
                ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, size=30, color=self.success_color),
                    ft.Column([
                        ft.Text(item.get('name', 'N/A'), size=font_normal + 2, weight=ft.FontWeight.BOLD),
                        ft.Text(item_type_name, size=font_small, color="#888888"),
                    ], spacing=2),
                ], spacing=10),
                ft.Row([
                    ft.Text("📝 Code:", size=font_small, color="#CCCCCC", width=70),
                    ft.Text(item.get('item_code', 'N/A'), size=font_small, color=self.text_color),
                ]),
                ft.Row([
                    ft.Text("📍 Location:", size=font_small, color="#CCCCCC", width=70),
                    ft.Text(location, size=font_small, color=self.text_color),
                ]),
                ft.Row([
                    ft.Text("🏷️ Quality:", size=font_small, color="#CCCCCC", width=70),
                    ft.Container(
                        content=ft.Text(quality, size=font_small - 1, color="white"),
                        bgcolor=self.get_quality_color(quality),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    ),
                ]),
                ft.Row([
                    ft.Text("🔢 Quantity:", size=font_small, color="#CCCCCC", width=70),
                    ft.Text(str(quantity), size=font_normal, weight=ft.FontWeight.BOLD,
                        color=self.danger_color if quantity < 10 else self.text_color),
                ]),
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("📱 View Details", on_click=lambda e: view_item_detail(current_item, current_item_type), expand=True),
                    ft.ElevatedButton("🔄 Update Stock", on_click=lambda e: show_update_panel(), expand=True, style=ft.ButtonStyle(bgcolor=self.warning_color)),
                ], spacing=10),
            ], spacing=8)
            
            if is_accessory and item.get('price'):
                price_row = ft.Row([
                    ft.Text("💰 Price:", size=font_small, color="#CCCCCC", width=70),
                    ft.Text(f"${item.get('price', 0):.2f}", size=font_small, color="#4CAF50"),
                ])
                result_container.content.controls.insert(8, price_row)
            
            update_container.data = item
            update_container.visible = False
            page.update()
        
        # ========== SHOW UPDATE PANEL ==========
        def show_update_panel():
            if not current_item:
                return
            
            quantity = current_item.get('quantity', 0)
            quality = current_item.get('quality', 'New')
            
            adjustment_field = ft.TextField(
                hint_text="+10 or -5",
                width=120,
                bgcolor=self.card_color,
                text_align=ft.TextAlign.CENTER,
            )
            
            quality_dropdown = ft.Dropdown(
                width=120,
                options=[
                    ft.dropdown.Option("New"),
                    ft.dropdown.Option("Used"),
                    ft.dropdown.Option("Damaged"),
                    ft.dropdown.Option("Repaired"),
                ],
                value=quality,
                bgcolor=self.card_color,
            )
            
            def apply_update(e):
                nonlocal current_item
                adjustment_text = adjustment_field.value.strip()
                
                if not adjustment_text:
                    page.snack_bar = ft.SnackBar(ft.Text("Please enter adjustment amount!"), bgcolor=self.danger_color)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                try:
                    adjustment = int(adjustment_text)
                    new_quantity = quantity + adjustment
                    if new_quantity < 0:
                        new_quantity = 0
                except ValueError:
                    page.snack_bar = ft.SnackBar(ft.Text("Please enter a valid number!"), bgcolor=self.danger_color)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                new_quality = quality_dropdown.value
                
                update_data = {
                    'quantity': new_quantity,
                    'quality': new_quality,
                }
                
                if current_item_type == 'accessory':
                    result = AccessoryManager.update(current_item['id'], update_data)
                else:
                    result = MaterialManager.update(current_item['id'], update_data)
                
                if result:
                    current_item['quantity'] = new_quantity
                    current_item['quality'] = new_quality
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ Updated! New quantity: {new_quantity}, Quality: {new_quality}"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    display_item_result(current_item, current_item_type)
                    update_container.visible = False
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ Update failed!"), bgcolor=self.danger_color)
                    page.snack_bar.open = True
                
                page.update()
            
            def cancel_update(e):
                update_container.visible = False
                page.update()
            
            update_container.content = ft.Column([
                ft.Text("✏️ Update Stock", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Divider(),
                ft.Row([
                    ft.Text("Current Quantity:", size=font_small, color="#CCCCCC", expand=True),
                    ft.Text(str(quantity), size=font_normal, weight=ft.FontWeight.BOLD, color=self.text_color),
                ]),
                ft.Row([
                    ft.Text("Adjustment:", size=font_small, color="#CCCCCC", expand=True),
                    adjustment_field,
                ]),
                ft.Row([
                    ft.Text("New Quality:", size=font_small, color="#CCCCCC", expand=True),
                    quality_dropdown,
                ]),
                ft.Row([
                    ft.ElevatedButton("✅ Apply Update", on_click=apply_update, expand=True, style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ft.OutlinedButton("❌ Cancel", on_click=cancel_update, expand=True),
                ], spacing=10),
            ], spacing=10)
            
            update_container.visible = True
            page.update()
        
        # Set search button
        for control in input_card.content.content.controls:
            if isinstance(control, ft.Row):
                for btn in control.controls:
                    if isinstance(btn, ft.ElevatedButton) and btn.text == "🔍 Search":
                        btn.on_click = lambda e: search_barcode(barcode_input.value.strip())
                        break
        
        barcode_input.on_submit = lambda e: search_barcode(barcode_input.value.strip())
        
        # ========== ADD ITEM FROM BARCODE ==========
        def add_item_from_barcode(barcode):
            def close_dialog(e):
                page.dialog.open = False
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
                    page.dialog.open = False
                    page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added material: {name}"), bgcolor=self.success_color)
                    page.snack_bar.open = True
                    search_barcode(barcode)
                page.update()
            
            def add_accessory(e):
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
                    page.dialog.open = False
                    page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added accessory: {name}"), bgcolor=self.success_color)
                    page.snack_bar.open = True
                    search_barcode(barcode)
                page.update()
            
            name_field = ft.TextField(label="Name *", width=300, bgcolor=self.card_color)
            quantity_field = ft.TextField(label="Quantity", width=300, bgcolor=self.card_color, value="0")
            price_field = ft.TextField(label="Price", width=300, bgcolor=self.card_color, value="0.00")
            quality_field = ft.Dropdown(
                label="Quality", width=300,
                options=[
                    ft.dropdown.Option("New"),
                    ft.dropdown.Option("Used"),
                    ft.dropdown.Option("Damaged"),
                    ft.dropdown.Option("Repaired")
                ],
                value="New",
                bgcolor=self.card_color,
            )
            location_field = ft.TextField(label="Location", width=300, bgcolor=self.card_color)
            notes_field = ft.TextField(label="Notes", width=300, bgcolor=self.card_color, multiline=True, min_lines=2)
            
            dialog = ft.AlertDialog(
                title=ft.Text(f"Add New Item", size=18, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Barcode: {barcode}", size=12, color="#888888"),
                        ft.Divider(),
                        name_field,
                        ft.Row([quantity_field, price_field], spacing=10),
                        quality_field,
                        location_field,
                        notes_field,
                    ], spacing=10, scroll=ft.ScrollMode.AUTO),
                    width=400,
                    height=450,
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_dialog),
                    ft.FilledButton("Add as Material", on_click=add_material, style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ft.FilledButton("Add as Accessory", on_click=add_accessory, style=ft.ButtonStyle(bgcolor=self.accent_color)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.dialog = dialog
            dialog.open = True
            page.update()
        
        def view_item_detail(item, item_type):
            if item_type == 'accessory':
                self.show_accessory_detail_dialog(page, item)
            else:
                self.show_material_detail_dialog(page, item)
        
        # ========== NATIVE CAMERA SCANNER ==========
        def open_native_camera_scanner(page, barcode_field):
            """Opens the device's native camera app to scan barcode"""
            
            # For Android - using intent
            # For iOS - using native camera
            # Since Flet doesn't have direct camera access, we'll use a QR code approach
            
            # Create a popup with QR code that user can scan
            # This is a clever workaround: generate a QR code that contains a link back to the app
            
            import random
            import string
            
            # Generate a unique token for this scan session
            scan_token = ''.join(random.choices(string.digits, k=8))
            
            # Store the callback in a temporary variable
            self.pending_scan_token = scan_token
            self.pending_scan_callback = lambda barcode: self.handle_scanned_barcode(page, barcode_field, barcode)
            
            # For Android, we can use a deep link
            # But a simpler approach: show a dialog with instructions
            
            def close_scan_dialog(e):
                page.dialog.open = False
                page.update()
            
            def manual_entry(e):
                close_scan_dialog(e)
                # Focus on barcode input field
                page.update()
            
            scan_dialog_content = ft.Column([
                ft.Text("📷 Camera Scanner", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Icon(ft.icons.CAMERA_ALT, size=60, color=self.accent_color),
                ft.Text("To scan a barcode:", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Text("1. Open your phone's Camera app", size=font_small),
                ft.Text("2. Point it at the barcode", size=font_small),
                ft.Text("3. When a notification appears, tap 'Copy'", size=font_small),
                ft.Text("4. Come back here and paste the number", size=font_small),
                ft.Container(height=15),
                ft.Row([
                    ft.ElevatedButton("📋 I've Copied a Barcode", on_click=lambda e: self.show_paste_dialog(page, barcode_field), expand=True),
                    ft.OutlinedButton("✏️ Enter Manually", on_click=manual_entry, expand=True),
                ], spacing=10),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            scan_dialog = ft.AlertDialog(
                title=ft.Text("Scan Barcode", size=18, weight=ft.FontWeight.BOLD),
                content=ft.Container(content=scan_dialog_content, width=350, height=400, padding=20),
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            page.dialog = scan_dialog
            scan_dialog.open = True
            page.update()
        
        def show_paste_dialog(page, barcode_field):
            """Show dialog for pasting scanned barcode"""
            if page.dialog:
                page.dialog.open = False
            
            paste_field = ft.TextField(
                label="Paste Barcode Number",
                hint_text="Long press to paste",
                width=300,
                bgcolor=self.card_color,
                text_align=ft.TextAlign.CENTER,
            )
            
            def process_paste(e):
                barcode = paste_field.value.strip()
                if barcode:
                    page.dialog.open = False
                    barcode_field.value = barcode
                    page.update()
                    # Auto search
                    search_barcode(barcode)
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("Please paste a barcode number"), bgcolor=self.danger_color)
                    page.snack_bar.open = True
                    page.update()
            
            paste_dialog_content = ft.Column([
                ft.Text("📋 Paste Scanned Barcode", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                paste_field,
                ft.Text("Long press on the text field to paste", size=11, color="#888888"),
                ft.Container(height=10),
                ft.Row([
                    ft.ElevatedButton("Process", on_click=process_paste, expand=True),
                    ft.OutlinedButton("Cancel", on_click=lambda e: (setattr(page.dialog, 'open', False), page.update()), expand=True),
                ], spacing=10),
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            paste_dialog = ft.AlertDialog(
                title=ft.Text("Paste Barcode", size=16, weight=ft.FontWeight.BOLD),
                content=ft.Container(content=paste_dialog_content, width=350, height=250, padding=20),
            )
            
            page.dialog = paste_dialog
            paste_dialog.open = True
            page.update()
        
        def handle_scanned_barcode(page, barcode_field, barcode):
            """Handle the scanned barcode from camera"""
            barcode_field.value = barcode
            page.update()
            search_barcode(barcode)
        
        # Store the open_native_camera_scanner function for use in the button
        self.open_native_camera_scanner = open_native_camera_scanner
        
        # ========== TIPS CARD ==========
        scroll_content.controls.append(ft.Container(height=15))
        scroll_content.controls.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("💡 How to Scan Barcodes", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Text("1. Click 'Scan with Camera'", size=font_small, color="#888888"),
                        ft.Text("2. Use your phone's Camera app to scan the barcode", size=font_small, color="#888888"),
                        ft.Text("3. Tap 'Copy' when the notification appears", size=font_small, color="#888888"),
                        ft.Text("4. Come back and click 'I've Copied a Barcode'", size=font_small, color="#888888"),
                        ft.Text("5. Paste the number and click 'Process'", size=font_small, color="#888888"),
                    ], spacing=8),
                    padding=15,
                ),
                elevation=1,
            )
        )
        
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "barcode_scanner"
        page.update()
    
    def show_inventory(self, page: ft.Page):
        """Show advanced inventory management screen with bottom navigation for mobile"""
        page.controls.clear()
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Font sizes
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
        
        # Get data
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        
        # Create combined inventory list
        inventory_items = []
        for m in materials:
            inventory_items.append({
                'id': m.get('id'),
                'type': 'material',
                'type_icon': '📦',
                'type_name': 'Material',
                'name': m.get('name', 'N/A'),
                'code': m.get('item_code', 'N/A'),
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
                'code': a.get('item_code', 'N/A'),
                'quantity': a.get('quantity', 0),
                'quality': a.get('quality', 'Used'),
                'location': location,
                'price': a.get('price', 0),
                'last_updated': a.get('updated_at', a.get('created_at', '')),
            })
        
        inventory_items.sort(key=lambda x: x['name'])
        
        # Calculate stats
        total_items = len(inventory_items)
        total_stock = sum(i.get('quantity', 0) for i in inventory_items)
        low_stock_items = [i for i in inventory_items if i.get('quantity', 0) < 10]
        critical_stock = [i for i in inventory_items if i.get('quantity', 0) < 5]
        total_value = sum(i.get('quantity', 0) * (i.get('price', 0) if i.get('price') else 10) for i in inventory_items)
        
        # Store current filtered items
        self.current_filtered_items = inventory_items.copy()
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
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
        
        # Stats cards row 1
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
        
        # Stats row 2
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
        
        # Export buttons
        export_row = ft.Row([
            ft.ElevatedButton("📊 CSV", on_click=lambda e: self.export_inventory_csv(page), expand=True,
                            style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ft.ElevatedButton("📄 PDF", on_click=lambda e: self.export_inventory_pdf(page), expand=True,
                            style=ft.ButtonStyle(bgcolor=self.warning_color)),
            ft.ElevatedButton("⚠️ Low PDF", on_click=lambda e: self.export_low_stock_pdf(page), expand=True,
                            style=ft.ButtonStyle(bgcolor=self.danger_color)),
        ], spacing=10)
        scroll_content.controls.append(export_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # Quick adjust button
        scroll_content.controls.append(
            ft.ElevatedButton(
                "⚡ Quick Stock Adjustment", 
                on_click=lambda e: self.quick_adjust_stock(page, inventory_items),
                style=ft.ButtonStyle(bgcolor=self.warning_color),
            )
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # Filters
        scroll_content.controls.append(ft.Text("🔍 Filters", size=font_normal, weight=ft.FontWeight.BOLD))
        scroll_content.controls.append(ft.Container(height=5))
        
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
        
        # Inventory list container
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
        
        # ========== IMPORTANT: ADD BOTTOM NAVIGATION FOR MOBILE ==========
        if is_mobile:
            # Create bottom navigation bar
            bottom_nav = self.create_bottom_nav(page)
            # Stack: main content above bottom navigation
            page.add(
                ft.Column([
                    main_container,
                    bottom_nav,
                ], spacing=0, expand=True)
            )
        else:
            # Desktop: sidebar + content
            sidebar = self.create_sidebar(page)
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "inventory"
        page.update()

    def export_inventory_csv(self, page: ft.Page):
        """Export current filtered inventory items to CSV"""
        import csv
        from datetime import datetime
        
        try:
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_dir, f"inventory_export_{timestamp}.csv")
            
            items = getattr(self, 'current_filtered_items', [])
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Type', 'Name', 'Code', 'Quantity', 'Quality', 'Location', 'Stock Status'])
                
                for item in items:
                    if item['quantity'] < 5:
                        stock_status = "Critical"
                    elif item['quantity'] < 10:
                        stock_status = "Low"
                    else:
                        stock_status = "Normal"
                    
                    writer.writerow([
                        item['type_name'],
                        item['name'],
                        item['code'],
                        item['quantity'],
                        item['quality'],
                        item['location'],
                        stock_status,
                    ])
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Exported {len(items)} items to {filename}"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def export_inventory_pdf(self, page: ft.Page):
        """Export current filtered inventory items to PDF"""
        from datetime import datetime
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import landscape, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_dir, f"inventory_report_{timestamp}.pdf")
            
            items = getattr(self, 'current_filtered_items', [])
            
            doc = SimpleDocTemplate(filename, pagesize=landscape(A4), 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=40, bottomMargin=30)
            
            styles = getSampleStyleSheet()
            story = []
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1976D2'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            story.append(Paragraph("Store Management System - Inventory Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                styles['Normal']))
            story.append(Spacer(1, 20))
            
            total_items = len(items)
            total_quantity = sum(i.get('quantity', 0) for i in items)
            low_stock = len([i for i in items if i.get('quantity', 0) < 10])
            critical_stock = len([i for i in items if i.get('quantity', 0) < 5])
            
            summary_data = [
                ['Total Items', str(total_items)],
                ['Total Quantity', str(total_quantity)],
                ['Low Stock Items', str(low_stock)],
                ['Critical Stock', str(critical_stock)],
            ]
            
            summary_table = Table(summary_data, colWidths=[120, 80])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            table_data = [['#', 'Type', 'Name', 'Code', 'Quantity', 'Quality', 'Location', 'Status']]
            
            for i, item in enumerate(items[:200], 1):
                if item['quantity'] < 5:
                    status = "Critical"
                elif item['quantity'] < 10:
                    status = "Low"
                else:
                    status = "Normal"
                
                table_data.append([
                    str(i),
                    item['type_name'],
                    item['name'],
                    item['code'],
                    str(item['quantity']),
                    item['quality'],
                    item['location'],
                    status,
                ])
            
            table = Table(table_data, colWidths=[30, 60, 100, 70, 45, 60, 80, 50])
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
            doc.build(story)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ PDF exported to {filename}"),
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
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ PDF export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def export_low_stock_pdf(self, page: ft.Page):
        """Export low stock items to PDF"""
        from datetime import datetime
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_dir, f"low_stock_report_{timestamp}.pdf")
            
            items = getattr(self, 'current_filtered_items', [])
            low_stock_items = [i for i in items if i.get('quantity', 0) < 10]
            
            doc = SimpleDocTemplate(filename, pagesize=A4, 
                                    rightMargin=30, leftMargin=30,
                                    topMargin=30, bottomMargin=20)
            
            styles = getSampleStyleSheet()
            story = []
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#F44336'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            story.append(Paragraph("Low Stock Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                styles['Normal']))
            story.append(Spacer(1, 20))
            
            table_data = [['#', 'Type', 'Name', 'Code', 'Current Stock', 'Quality', 'Location']]
            
            for i, item in enumerate(low_stock_items, 1):
                table_data.append([
                    str(i),
                    item['type_name'],
                    item['name'],
                    item['code'],
                    str(item['quantity']),
                    item['quality'],
                    item['location'],
                ])
            
            table = Table(table_data, colWidths=[30, 50, 100, 70, 45, 60, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F44336')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ]))
            
            story.append(table)
            doc.build(story)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Low stock PDF exported to {filename}"),
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
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    def quick_adjust_stock(self, page: ft.Page, inventory_items):
        """Quickly adjust stock quantity from the quick adjustment panel"""
        
        def apply_adjustment(e):
            item_id = item_dropdown.value
            adjustment = adjustment_field.value.strip()
            
            if not item_id:
                page.snack_bar = ft.SnackBar(ft.Text("Please select an item!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            if not adjustment:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter adjustment amount!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            try:
                adj = int(adjustment)
                
                # Find item by ID
                item = MaterialManager.get_by_id(int(item_id))
                item_type = 'material'
                if not item:
                    item = AccessoryManager.get_by_id(int(item_id))
                    item_type = 'accessory'
                
                if not item:
                    page.snack_bar = ft.SnackBar(ft.Text("Item not found!"), bgcolor=self.danger_color)
                    page.snack_bar.open = True
                    page.update()
                    return
                
                current_qty = item.get('quantity', 0)
                new_qty = current_qty + adj
                if new_qty < 0:
                    new_qty = 0
                
                update_data = {'quantity': new_qty}
                
                if item_type == 'material':
                    MaterialManager.update(int(item_id), update_data)
                else:
                    AccessoryManager.update(int(item_id), update_data)
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Stock updated: {item.get('name')} from {current_qty} to {new_qty}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_inventory(page)
                
            except ValueError:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Invalid adjustment value! Use numbers like +10 or -5"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        # Build dropdown options
        dropdown_options = []
        for item in inventory_items[:50]:
            dropdown_options.append(ft.dropdown.Option(
                str(item['id']), 
                f"{item['type_icon']} {item['name']} (Stock: {item['quantity']})"
            ))
        
        item_dropdown = ft.Dropdown(
            label="Select Item",
            width=350,
            options=dropdown_options,
            bgcolor=self.card_color,
        )
        
        adjustment_field = ft.TextField(
            label="Adjustment Amount",
            width=200,
            hint_text="+10 or -5",
            bgcolor=self.card_color,
        )
        
        dialog_content = ft.Column([
            ft.Text("Quick Stock Adjustment", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            item_dropdown,
            adjustment_field,
            ft.Text("Example: +10 to add 10 units, -5 to remove 5 units", size=11, color="#888888"),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Apply Adjustment", on_click=apply_adjustment, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Quick Stock Adjustment"),
            content=ft.Container(content=dialog_content, width=450, height=380, padding=15),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
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

    def reset_inventory_filters(self, page: ft.Page):
        """Reset all inventory filters"""
        self.show_inventory(page)
    def show_users(self, page: ft.Page):
        """Show users screen - FULL CRUD with role-based permissions"""
        page.controls.clear()
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Font sizes
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
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Get current user info
        current_user_id = self.current_user.get('id') if self.current_user else None
        is_admin = self.current_user.get('role') == 'admin' if self.current_user else False
        
        # Get all users
        users = self.dict_list(UserManager.get_all())
        
        # Calculate stats
        admin_count = len([u for u in users if u.get('role') == 'admin'])
        manager_count = len([u for u in users if u.get('role') == 'manager'])
        user_count = len([u for u in users if u.get('role') == 'user'])
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("Users Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.ADD_CIRCLE,
                    icon_size=28,
                    icon_color=self.success_color,
                    on_click=lambda e: self.open_add_user_modal(page),
                    visible=is_admin,
                    tooltip="Add New User",
                ),
            ])
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # Stats cards
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
        
        # Search field
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
        
        # Users list container
        users_container = ft.Column(spacing=10)
        scroll_content.controls.append(users_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        def refresh_users_list():
            users_container.controls.clear()
            
            # Get fresh user data
            all_users = self.dict_list(UserManager.get_all())
            
            # Apply search filter
            search_query = search_field.value.lower() if search_field.value else ""
            if search_query:
                all_users = [u for u in all_users if search_query in u.get('name', '').lower() or search_query in u.get('email', '').lower()]
            
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
                
                card_content = ft.Column([
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(u.get('name', 'U')[0].upper(), size=14),
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
                                icon_color=self.accent_color,
                                on_click=lambda e, uid=u.get('id'): self.open_edit_user_modal(page, uid),
                                visible=can_edit,
                                tooltip="Edit User",
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                icon_size=20,
                                icon_color=self.danger_color,
                                on_click=lambda e, uid=u.get('id'), name=u.get('name'): self.open_delete_user_modal(page, uid, name),
                                visible=can_delete,
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
        
        # Event handlers
        def on_search(e):
            refresh_users_list()
        
        search_field.on_change = on_search
        
        # Initial load
        refresh_users_list()
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "users"
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
                ft.dropdown.Option("user", "👤 Regular User"),
                ft.dropdown.Option("manager", "📊 Manager"),
                ft.dropdown.Option("admin", "👑 Administrator"),
            ],
            value="user",
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def save_user(e):
            # Validation
            if not name_field.value:
                status_text.value = "❌ Please enter name!"
                status_text.color = self.danger_color
                page.update()
                return
            if not email_field.value:
                status_text.value = "❌ Please enter email!"
                status_text.color = self.danger_color
                page.update()
                return
            if not password_field.value:
                status_text.value = "❌ Please enter password!"
                status_text.color = self.danger_color
                page.update()
                return
            if password_field.value != confirm_password_field.value:
                status_text.value = "❌ Passwords do not match!"
                status_text.color = self.danger_color
                page.update()
                return
            if len(password_field.value) < 4:
                status_text.value = "❌ Password must be at least 4 characters!"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Create user
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
                status_text.value = "❌ Error: Email already exists!"
                status_text.color = self.danger_color
                page.update()
        
        modal = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Add New User", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Column([
                            name_field,
                            email_field,
                            password_field,
                            confirm_password_field,
                            role_field,
                            status_text,
                        ], spacing=12),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=close_modal),
                            ft.FilledButton("Create User", on_click=save_user, style=ft.ButtonStyle(bgcolor=self.success_color)),
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
        
        # Password reset fields (optional)
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
            
            # Validate password if provided
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
            
            import sqlite3
            import hashlib
            from database import DB_PATH
            
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
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ User {name_field.value} updated successfully!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                # Update current user info if editing self
                if is_current_user:
                    self.current_user['name'] = name_field.value
                    self.current_user['role'] = role_field.value
                self.show_users(page)
            else:
                status_text.value = "❌ Error updating user!"
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
        """Open modal for delete confirmation"""
        
        def close_modal(e):
            page.overlay.clear()
            page.update()
        
        def confirm_delete(e):
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                result = cursor.rowcount > 0
                conn.close()
                
                if result:
                    page.overlay.clear()
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✓ User '{user_name}' deleted successfully!"),
                        bgcolor=self.success_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    self.show_users(page)
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("❌ Error: Could not delete user!"),
                        bgcolor=self.danger_color,
                        duration=3000
                    )
                    page.snack_bar.open = True
                    page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Error: {str(ex)}"),
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
                            ft.FilledButton("Yes, Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
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

    def show_settings(self, page: ft.Page):
        """Show settings screen - COMPLETE WORKING VERSION"""
        page.controls.clear()
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Font sizes
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
        
        # Navigation
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        current_user = self.current_user
        is_admin = current_user.get('role') == 'admin' if current_user else False
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("Settings", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
            ])
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # ========== PROFILE SECTION ==========
        profile_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("👤 Profile", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(current_user.get('name', 'U')[0].upper(), size=18),
                            radius=35,
                            bgcolor=self.accent_color,
                        ),
                        ft.Column([
                            ft.Text(current_user.get('name', 'User'), size=font_normal + 2, weight=ft.FontWeight.BOLD),
                            ft.Text(current_user.get('email', 'N/A'), size=font_small - 1, color="#888888"),
                            ft.Text(f"Role: {current_user.get('role', 'user').upper()}", size=font_small - 2, 
                                color=self.success_color if current_user.get('role') == 'admin' else self.warning_color),
                        ], spacing=3, expand=True),
                    ], spacing=12),
                    ft.ElevatedButton(
                        "✏️ Edit Profile", 
                        on_click=lambda e: self.edit_profile_dialog(page),
                        style=ft.ButtonStyle(bgcolor=self.accent_color),
                    ),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(profile_card)
        
        # ========== SECURITY SECTION ==========
        security_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🔐 Security", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.LOCK, color=self.accent_color),
                        title=ft.Text("Change Password"),
                        trailing=ft.Icon(ft.icons.CHEVRON_RIGHT),
                        on_click=lambda e: self.change_password_dialog(page),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.SHIELD, color=self.accent_color),
                        title=ft.Text("Two-Factor Authentication"),
                        trailing=ft.Switch(value=False, on_change=lambda e: self.toggle_2fa(page, e)),
                    ),
                ], spacing=8),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(security_card)
        
        # ========== APPEARANCE SECTION ==========
        appearance_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🎨 Appearance", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.DARK_MODE, color=self.accent_color),
                        title=ft.Text("Dark Mode"),
                        trailing=ft.Switch(value=True, on_change=lambda e: self.toggle_theme(page, e)),
                    ),
                    ft.Text("Accent Color", size=font_small, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Container(width=35, height=35, bgcolor="#1976D2", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#1976D2")),
                        ft.Container(width=35, height=35, bgcolor="#4CAF50", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#4CAF50")),
                        ft.Container(width=35, height=35, bgcolor="#9C27B0", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#9C27B0")),
                        ft.Container(width=35, height=35, bgcolor="#FF9800", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#FF9800")),
                        ft.Container(width=35, height=35, bgcolor="#E91E63", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#E91E63")),
                        ft.Container(width=35, height=35, bgcolor="#00BCD4", border_radius=18, ink=True,
                                    on_click=lambda e: self.change_accent_color(page, "#00BCD4")),
                    ], spacing=12),
                    ft.Container(height=5),
                    ft.Text("Font Size", size=font_small, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Small", on_click=lambda e: self.change_font_size(page, "small"), expand=True),
                        ft.ElevatedButton("Medium", on_click=lambda e: self.change_font_size(page, "medium"), expand=True),
                        ft.ElevatedButton("Large", on_click=lambda e: self.change_font_size(page, "large"), expand=True),
                    ], spacing=10),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(appearance_card)
                
        # ========== COMPANY INFO SECTION ==========
        # Get company info
        company_info = self.get_company_info()

        # Store display widgets as instance variables for later update
        self.company_name_display = ft.Text(company_info.get('company_name', 'Not set'), size=font_normal, weight=ft.FontWeight.BOLD)
        self.company_phone_display = ft.Text(company_info.get('phone', 'Not set'), size=font_small)
        self.company_email_display = ft.Text(company_info.get('email', 'Not set'), size=font_small)
        self.company_website_display = ft.Text(company_info.get('website', 'Not set'), size=font_small)
        self.company_address_display = ft.Text(company_info.get('address', 'Not set'), size=font_small)
        self.company_city_display = ft.Text(company_info.get('city', 'Not set'), size=font_small)
        self.company_tax_display = ft.Text(company_info.get('tax_id', 'Not set'), size=font_small)

        company_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("🏢 Company Information", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "✏️ Edit",
                            on_click=lambda e: self.edit_company_info_dialog(page),
                            icon=ft.icons.EDIT,
                            style=ft.ButtonStyle(bgcolor=self.accent_color),
                        ),
                    ]),
                    ft.Divider(),
                    # Company Name - full width
                    ft.Row([
                        ft.Icon(ft.icons.BUSINESS, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text("Company Name", size=font_small - 2, color="#888888"),
                            self.company_name_display,
                        ], spacing=2, expand=True),
                    ], spacing=10),
                    # Phone and Email - side by side on tablet, stacked on mobile
                    ft.ResponsiveRow([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.PHONE, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("Phone", size=font_small - 2, color="#888888"),
                                    self.company_phone_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.EMAIL, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("Email", size=font_small - 2, color="#888888"),
                                    self.company_email_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                    ], spacing=10),
                    # Website - full width
                    ft.Row([
                        ft.Icon(ft.icons.LANGUAGE, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text("Website", size=font_small - 2, color="#888888"),
                            self.company_website_display,
                        ], spacing=2, expand=True),
                    ], spacing=10),
                    # Address - full width
                    ft.Row([
                        ft.Icon(ft.icons.LOCATION_ON, size=20, color=self.accent_color),
                        ft.Column([
                            ft.Text("Address", size=font_small - 2, color="#888888"),
                            self.company_address_display,
                        ], spacing=2, expand=True),
                    ], spacing=10),
                    # City and Tax ID - stacked on mobile, side by side on tablet
                    ft.ResponsiveRow([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.LOCATION_CITY, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("City", size=font_small - 2, color="#888888"),
                                    self.company_city_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.RECEIPT, size=18, color=self.accent_color),
                                ft.Column([
                                    ft.Text("Tax ID / VAT", size=font_small - 2, color="#888888"),
                                    self.company_tax_display,
                                ], spacing=2),
                            ], spacing=10),
                            col={"xs": 12, "md": 6},
                        ),
                    ], spacing=10),
                ], spacing=12),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(company_card)
        # ========== DATABASE SECTION ==========
        # Get database size
        db_size = "N/A"
        try:
            if os.path.exists("store_management.db"):
                size_bytes = os.path.getsize("store_management.db")
                if size_bytes < 1024:
                    db_size = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    db_size = f"{size_bytes / 1024:.1f} KB"
                else:
                    db_size = f"{size_bytes / (1024 * 1024):.1f} MB"
        except:
            db_size = "N/A"

        # Use simple Container instead of Card to avoid click issues
        database_section = ft.Container(
            content=ft.Column([
                ft.Text("💾 Database", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Divider(),
                ft.Row([
                    ft.Icon(ft.icons.STORAGE, size=30, color=self.accent_color),
                    ft.Column([
                        ft.Text("Database Size", size=font_small, color="#888888"),
                        ft.Text(db_size, size=font_normal, weight=ft.FontWeight.BOLD),
                    ], spacing=2),
                    ft.IconButton(icon=ft.icons.REFRESH, icon_size=20, on_click=lambda e: self.show_settings(page)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=10),
                ft.Row([
                    ft.ElevatedButton(
                        "📥 Backup", 
                        on_click=lambda e: self.backup_database(page), 
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=self.accent_color),
                    ),
                    ft.ElevatedButton(
                        "🔄 Restore", 
                        on_click=lambda e: self.restore_database(page), 
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=self.warning_color),
                    ),
                ], spacing=10),
                ft.Row([
                    ft.OutlinedButton(
                        "📁 View Backups", 
                        on_click=lambda e: self.show_backup_list(page), 
                        expand=True,
                    ),
                    ft.ElevatedButton(
                        "⚠️ Reset", 
                        on_click=lambda e: self.reset_database_confirm(page), 
                        expand=True,
                        style=ft.ButtonStyle(bgcolor=self.danger_color),
                    ),
                ], spacing=10),
                ft.ElevatedButton(
                    "📊 Export All Data", 
                    on_click=lambda e: self.export_all_data(page), 
                    style=ft.ButtonStyle(bgcolor=self.success_color),
                ),
            ], spacing=12),
            padding=15,
            bgcolor=self.card_color,
            border_radius=10,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(database_section)

                # ========== LOGOUT SECTION ==========
        logout_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.LOGOUT, size=24, color=self.danger_color),
                        ft.Text("Account", size=font_normal, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Container(expand=True),
                    ]),
                    ft.Divider(),
                    ft.Text("You are currently logged in as:", size=font_small, color="#888888"),
                    ft.Text(f"{self.current_user.get('name', 'User')}", size=font_normal, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{self.current_user.get('email', 'N/A')}", size=font_small - 1, color="#888888"),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "🚪 Logout",
                        on_click=lambda e: self.confirm_logout(page),
                        icon=ft.icons.LOGOUT,
                        style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color),
                    ),
                ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
            ),
            elevation=2,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(logout_card)

        # ========== ABOUT SECTION ==========
        about_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("ℹ️ About", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    
                    # App Logo/Icon
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🏪", size=60),
                            ft.Text("Store Management System", size=font_normal + 4, weight=ft.FontWeight.BOLD),
                            ft.Text("Version 2.0.0", size=font_small - 1, color="#888888"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        margin=ft.margin.only(bottom=10),
                    ),
                    
                    # Company Info (from company config)
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Developed By", size=font_small, weight=ft.FontWeight.BOLD, color="#888888"),
                            ft.Text("Your Company Name", size=font_small, color=self.accent_color),
                            ft.Container(height=5),
                            ft.Text("Contact", size=font_small, weight=ft.FontWeight.BOLD, color="#888888"),
                            ft.Text("support@storemanagement.com", size=font_small, color=self.accent_color),
                            ft.Text("+1 (555) 123-4567", size=font_small, color=self.accent_color),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                        margin=ft.margin.only(bottom=10),
                    ),
                    
                    ft.Divider(),
                    
                    # Features List
                    ft.Text("✨ Features", size=font_small, weight=ft.FontWeight.BOLD),
                    ft.Column([
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), ft.Text("Inventory Management", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), ft.Text("Barcode Scanning", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), ft.Text("User Management", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), ft.Text("Export Reports (CSV/PDF)", size=font_small - 1)], spacing=8),
                        ft.Row([ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=self.success_color), ft.Text("Database Backup & Restore", size=font_small - 1)], spacing=8),
                    ], spacing=6),
                    
                    ft.Container(height=10),
                    ft.Divider(),
                    
                    # Footer
                    ft.Text("© 2024 Store Management System", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
                    ft.Text("All Rights Reserved", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
                    ft.Text("Made with ❤️ using Flet", size=font_small - 2, color="#888888", text_align=ft.TextAlign.CENTER),
                    
                    # Action Buttons
                    ft.Container(height=10),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.PRIVACY_TIP, icon_size=20, on_click=lambda e: self.show_privacy_policy(page), tooltip="Privacy Policy"),
                        ft.IconButton(icon=ft.icons.HELP, icon_size=20, on_click=lambda e: self.show_help(page), tooltip="Help"),
                        ft.IconButton(icon=ft.icons.FEEDBACK, icon_size=20, on_click=lambda e: self.send_feedback(page), tooltip="Send Feedback"),
                        ft.IconButton(icon=ft.icons.SHARE, icon_size=20, on_click=lambda e: self.share_app(page), tooltip="Share App"),
                        ft.IconButton(icon=ft.icons.STAR, icon_size=20, on_click=lambda e: self.rate_app(page), tooltip="Rate App"),
                    ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
            ),
            elevation=2,
        )
        scroll_content.controls.append(about_card)
        
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "settings"
        page.update()
    def confirm_logout(self, page: ft.Page):
        """Show logout confirmation dialog"""
        
        def do_logout(e):
            page.dialog.open = False
            self.current_user = None
            self.show_login(page)
        
        def cancel_logout(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("🚪 Logout", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("Are you sure you want to logout?", size=14),
            ft.Text(f"You are currently logged in as:", size=12, color="#888888"),
            ft.Text(f"{self.current_user.get('name', 'User')}", size=14, weight=ft.FontWeight.BOLD),
            ft.Container(height=15),
            ft.Row([
                ft.TextButton("Cancel", on_click=cancel_logout),
                ft.FilledButton("Logout", on_click=do_logout, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Logout"),
            content=ft.Container(content=dialog_content, width=350, height=280, padding=20),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def show_privacy_policy(self, page: ft.Page):
        """Show privacy policy dialog"""
        
        policy_content = ft.Column([
            ft.Text("Privacy Policy", size=18, weight=ft.FontWeight.BOLD, color=self.accent_color),
            ft.Divider(),
            ft.Text("Last Updated: January 1, 2024", size=10, color="#888888"),
            ft.Container(height=10),
            ft.Text("Information Collection", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("We collect business inventory data that you enter into the app. This data is stored locally on your device.", size=12, color="#CCCCCC"),
            ft.Container(height=8),
            ft.Text("Data Security", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("All data is stored locally on your device. We do not transmit or share your data with any third parties.", size=12, color="#CCCCCC"),
            ft.Container(height=8),
            ft.Text("Contact Us", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("If you have questions about this policy, contact us at: privacy@storemanagement.com", size=12, color="#CCCCCC"),
        ], spacing=8, scroll=ft.ScrollMode.AUTO, height=400)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Privacy Policy"),
            content=ft.Container(content=policy_content, width=400, height=500, padding=15),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False))],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_help(self, page: ft.Page):
        """Show help dialog"""
        
        help_content = ft.Column([
            ft.Text("Help & Support", size=18, weight=ft.FontWeight.BOLD, color=self.accent_color),
            ft.Divider(),
            ft.Text("📖 Quick Guide", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("• Dashboard: View inventory overview and stats", size=12, color="#CCCCCC"),
            ft.Text("• Materials: Add, edit, delete materials", size=12, color="#CCCCCC"),
            ft.Text("• Accessories: Manage parts and accessories", size=12, color="#CCCCCC"),
            ft.Text("• Barcode Scanner: Scan or enter barcodes", size=12, color="#CCCCCC"),
            ft.Text("• Inventory: Filter and manage stock", size=12, color="#CCCCCC"),
            ft.Text("• Users: Manage user accounts and roles", size=12, color="#CCCCCC"),
            ft.Text("• Settings: Configure app preferences", size=12, color="#CCCCCC"),
            ft.Container(height=10),
            ft.Text("💡 Tips", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("• Use filters to find items quickly", size=12, color="#CCCCCC"),
            ft.Text("• Export data to CSV for backup", size=12, color="#CCCCCC"),
            ft.Text("• Regular backups are recommended", size=12, color="#CCCCCC"),
        ], spacing=8, scroll=ft.ScrollMode.AUTO, height=400)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Help"),
            content=ft.Container(content=help_content, width=400, height=500, padding=15),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(page.dialog, 'open', False))],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def send_feedback(self, page: ft.Page):
        """Send feedback dialog"""
        
        feedback_input = ft.TextField(
            label="Your Feedback",
            hint_text="Please share your thoughts, suggestions, or report issues...",
            multiline=True,
            min_lines=5,
            max_lines=8,
            width=350,
            bgcolor=self.card_color,
        )
        
        email_input = ft.TextField(
            label="Your Email (optional)",
            hint_text="We may contact you about your feedback",
            width=350,
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def submit_feedback(e):
            feedback = feedback_input.value.strip()
            if not feedback:
                status_text.value = "❌ Please enter your feedback"
                status_text.color = self.danger_color
                page.update()
                return
            
            # Here you can add code to send feedback to your email/server
            # For now, just show success message
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text("✓ Thank you for your feedback!"),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("Send Feedback", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            feedback_input,
            email_input,
            status_text,
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Submit", on_click=submit_feedback, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Feedback"),
            content=ft.Container(content=dialog_content, width=450, height=450, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def share_app(self, page: ft.Page):
        """Share app information"""
        
        share_text = "Check out Store Management App!\n\nEasily manage your inventory, track stock, scan barcodes, and more.\n\nDownload now!"
        
        # Copy to clipboard
        page.set_clipboard(share_text)
        
        page.snack_bar = ft.SnackBar(
            ft.Text("✓ App info copied to clipboard! You can now share it."),
            bgcolor=self.success_color,
            duration=3000
        )
        page.snack_bar.open = True
        page.update()

    def rate_app(self, page: ft.Page):
        """Rate app dialog"""
        
        rating_options = ft.Row([
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(1)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(2)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(3)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(4)),
            ft.IconButton(icon=ft.icons.STAR_BORDER, icon_size=40, on_click=lambda e: submit_rating(5)),
        ], spacing=5, alignment=ft.MainAxisAlignment.CENTER)
        
        rating_text = ft.Text("Tap a star to rate", size=14, color="#888888")
        
        def submit_rating(rating):
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Thank you for rating {rating} stars! ⭐"),
                bgcolor=self.success_color,
                duration=3000
            )
            page.snack_bar.open = True
            page.update()
        
        dialog_content = ft.Column([
            ft.Text("Rate This App", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("How would you rate your experience?", size=14),
            ft.Container(height=10),
            rating_options,
            rating_text,
            ft.Container(height=10),
            ft.TextButton("Maybe Later", on_click=lambda e: setattr(page.dialog, 'open', False)),
        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Rate Us"),
            content=ft.Container(content=dialog_content, width=350, height=300, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def edit_company_info_dialog(self, page: ft.Page):
        """Open dialog to edit company information with working cancel button"""
        
        # Get current company info
        current = self.get_company_info()
        
        # Use full width fields on mobile
        is_mobile = page.width < 800 if page.width else False
        field_width = page.width - 80 if is_mobile else 350
        
        name_field = ft.TextField(label="Company Name", value=current.get('company_name', ''), width=field_width, bgcolor=self.card_color)
        phone_field = ft.TextField(label="Phone", value=current.get('phone', ''), width=field_width, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", value=current.get('email', ''), width=field_width, bgcolor=self.card_color)
        website_field = ft.TextField(label="Website", value=current.get('website', ''), width=field_width, bgcolor=self.card_color)
        address_field = ft.TextField(label="Address", value=current.get('address', ''), width=field_width, bgcolor=self.card_color, multiline=True, min_lines=2)
        
        # City and Tax ID - stacked on mobile, side by side on desktop
        if is_mobile:
            city_field = ft.TextField(label="City", value=current.get('city', ''), width=field_width, bgcolor=self.card_color)
            tax_id_field = ft.TextField(label="Tax ID / VAT", value=current.get('tax_id', ''), width=field_width, bgcolor=self.card_color)
            city_tax_row = ft.Column([city_field, tax_id_field], spacing=10)
        else:
            city_field = ft.TextField(label="City", value=current.get('city', ''), width=170, bgcolor=self.card_color)
            tax_id_field = ft.TextField(label="Tax ID / VAT", value=current.get('tax_id', ''), width=170, bgcolor=self.card_color)
            city_tax_row = ft.Row([city_field, tax_id_field], spacing=10)
        
        status_text = ft.Text("", size=12, color="#888888")
        
        # Store reference to dialog
        dialog_ref = None
        
        def close_dialog(e):
            if dialog_ref:
                dialog_ref.open = False
                page.update()
        
        def save_info(e):
            import json
            import os
            
            if not name_field.value:
                status_text.value = "❌ Company name is required!"
                status_text.color = self.danger_color
                page.update()
                return
            
            data = {
                'company_name': name_field.value,
                'phone': phone_field.value or '',
                'email': email_field.value or '',
                'website': website_field.value or '',
                'address': address_field.value or '',
                'city': city_field.value or '',
                'tax_id': tax_id_field.value or '',
            }
            
            try:
                config_file = os.path.join(BASE_DIR, "company_config.json")
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                # Update the display widgets directly
                if hasattr(self, 'company_name_display'):
                    self.company_name_display.value = data['company_name']
                    self.company_phone_display.value = data['phone']
                    self.company_email_display.value = data['email']
                    self.company_website_display.value = data['website']
                    self.company_address_display.value = data['address']
                    self.company_city_display.value = data['city']
                    self.company_tax_display.value = data['tax_id']
                    page.update()
                
                close_dialog(None)
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Company information saved!"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                
            except Exception as ex:
                status_text.value = f"❌ Error saving: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Edit Company Information", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Container(
                content=ft.Column([
                    name_field,
                    phone_field,
                    email_field,
                    website_field,
                    address_field,
                    city_tax_row,
                    status_text,
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
                height=400,
            ),
            ft.Divider(),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save Changes", on_click=save_info, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Company Information"),
            content=ft.Container(content=dialog_content, width=450, height=550, padding=15),
        )
        
        dialog_ref = dialog
        page.dialog = dialog
        dialog.open = True
        page.update()
    
    def edit_profile_dialog(self, page: ft.Page):
        """Open dialog to edit user profile"""
        
        current_user = self.current_user
        
        name_field = ft.TextField(label="Full Name", value=current_user.get('name', ''), width=300, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", value=current_user.get('email', ''), width=300, bgcolor=self.card_color, read_only=True)
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def save_profile(e):
            new_name = name_field.value.strip()
            if not new_name:
                page.snack_bar = ft.SnackBar(ft.Text("Name cannot be empty!"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                return
            
            import sqlite3
            from database import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, current_user['id']))
            conn.commit()
            conn.close()
            
            self.current_user['name'] = new_name
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("✓ Profile updated!"), bgcolor=self.success_color)
            page.snack_bar.open = True
            self.show_settings(page)
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
        """Open dialog to change password"""
        
        import hashlib
        
        current_password = ft.TextField(label="Current Password", password=True, width=300, bgcolor=self.card_color)
        new_password = ft.TextField(label="New Password", password=True, width=300, bgcolor=self.card_color)
        confirm_password = ft.TextField(label="Confirm Password", password=True, width=300, bgcolor=self.card_color)
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
            
            # Verify current password
            import sqlite3
            from database import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            current_hash = hashlib.sha256(current.encode()).hexdigest()
            cursor.execute("SELECT id FROM users WHERE id = ? AND password_hash = ?", 
                        (self.current_user['id'], current_hash))
            if not cursor.fetchone():
                status_text.value = "❌ Current password is incorrect"
                status_text.color = self.danger_color
                conn.close()
                page.update()
                return
            
            # Update password
            new_hash = hashlib.sha256(new.encode()).hexdigest()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, self.current_user['id']))
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("✓ Password changed successfully!"), bgcolor=self.success_color)
            page.snack_bar.open = True
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

    def toggle_theme(self, page: ft.Page, e):
        """Toggle between dark and light theme"""
        if e.control.value:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = self.bg_color
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = "#F5F5F5"
        page.update()

    def toggle_2fa(self, page: ft.Page, e):
        """Toggle two-factor authentication"""
        if e.control.value:
            page.snack_bar = ft.SnackBar(ft.Text("2FA enabled - Feature coming soon"), bgcolor=self.accent_color)
        else:
            page.snack_bar = ft.SnackBar(ft.Text("2FA disabled"), bgcolor=self.warning_color)
        page.snack_bar.open = True
        page.update()

    def change_accent_color(self, page: ft.Page, color):
        """Change app accent color"""
        self.accent_color = color
        page.snack_bar = ft.SnackBar(ft.Text(f"Accent color changed"), bgcolor=color)
        page.snack_bar.open = True
        self.show_settings(page)

    def change_font_size(self, page: ft.Page, size):
        """Change font size preference"""
        if size == "small":
            self.font_scale = 0.8
        elif size == "large":
            self.font_scale = 1.2
        else:
            self.font_scale = 1.0
        
        page.snack_bar = ft.SnackBar(ft.Text(f"Font size changed to {size}"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        self.show_settings(page)

    def backup_database(self, page: ft.Page):
        """Backup database to file"""
        import shutil
        from datetime import datetime
        import os
        
        try:
            # Get the absolute path to the database
            db_path = os.path.abspath("store_management.db")
            
            # Create backups folder if not exists
            backup_dir = os.path.abspath("backups")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                print(f"Created backups folder: {backup_dir}")
            
            # Check if database exists
            if not os.path.exists(db_path):
                page.snack_bar = ft.SnackBar(
                    ft.Text("❌ Database file not found!"),
                    bgcolor=self.danger_color,
                    duration=4000
                )
                page.snack_bar.open = True
                page.update()
                return
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # Copy database file
            shutil.copy2(db_path, backup_path)
            
            # Get file size for display
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
            page.update()
            
            # Refresh settings to show updated backup list
            self.show_settings(page)
            
        except Exception as e:
            print(f"Backup error: {e}")
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Backup failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
    def restore_database(self, page: ft.Page):
        """Restore database from backup - shows dialog with available backups"""
        import os
        from datetime import datetime
        
        # Get available backups
        backup_dir = os.path.abspath("backups")
        backups = []
        
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            backups.sort(reverse=True)  # Newest first
        
        if not backups:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ No backups found. Create a backup first."),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_restore(e):
            import shutil
            
            selected_backup = backup_dropdown.value
            if not selected_backup:
                page.snack_bar = ft.SnackBar(ft.Text("Please select a backup file"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return
            
            try:
                backup_path = os.path.join(backup_dir, selected_backup)
                db_path = os.path.abspath("store_management.db")
                
                # Create a backup of current database before restore (just in case)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                pre_restore_backup = os.path.join(backup_dir, f"before_restore_{timestamp}.db")
                shutil.copy2(db_path, pre_restore_backup)
                
                # Restore the selected backup
                shutil.copy2(backup_path, db_path)
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Database restored from {selected_backup}. Pre-restore backup saved."),
                    bgcolor=self.success_color,
                    duration=5000
                )
                page.snack_bar.open = True
                page.update()
                
                # Refresh the current view
                self.show_settings(page)
                
            except Exception as e:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Restore failed: {str(e)}"),
                    bgcolor=self.danger_color,
                    duration=4000
                )
                page.snack_bar.open = True
                page.update()
        
        def on_backup_select(e):
            selected = backup_dropdown.value
            if selected:
                backup_path = os.path.join(backup_dir, selected)
                size_bytes = os.path.getsize(backup_path)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                
                # Update info text
                info_text.value = f"Size: {size_str} | Date: {selected.replace('backup_', '').replace('.db', '')}"
                page.update()
        
        # Create dropdown with backup files
        backup_dropdown = ft.Dropdown(
            label="Select Backup File",
            width=350,
            options=[ft.dropdown.Option(b, f"📁 {b}") for b in backups],
            bgcolor=self.card_color,
        )
        backup_dropdown.on_change = on_backup_select
        
        info_text = ft.Text("Select a backup to restore", size=12, color="#888888")
        
        dialog_content = ft.Column([
            ft.Text("⚠️ Restore Database", size=18, weight=ft.FontWeight.BOLD, color=self.warning_color),
            ft.Divider(),
            ft.Text("Select a backup file to restore:", size=14),
            backup_dropdown,
            info_text,
            ft.Container(height=5),
            ft.Text("⚠️ This will OVERWRITE your current data!", size=12, color=self.danger_color),
            ft.Text("A backup of your current data will be created before restore.", size=11, color="#888888"),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Restore Database", on_click=confirm_restore, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Restore Database"),
            content=ft.Container(content=dialog_content, width=450, height=400, padding=15),
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    # Add after the backup/restore buttons
    def show_backup_list(self, page: ft.Page):
        """Show list of available backups - COMPLETE WORKING VERSION"""
        import os
        from datetime import datetime
        
        backup_dir = os.path.abspath("backups")
        backups = []
        
        # Check if backups folder exists and get backups
        if os.path.exists(backup_dir):
            backups = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
            backups.sort(reverse=True)  # Newest first
        
        if not backups:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ No backups found. Create a backup first."),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            return
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def delete_backup(e, backup_file):
            """Delete selected backup file"""
            import os
            backup_path = os.path.join(backup_dir, backup_file)
            try:
                os.remove(backup_path)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Deleted: {backup_file}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.dialog.open = False
                self.show_backup_list(page)  # Refresh the list
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Delete failed: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
            page.update()
        
        def restore_backup(e, backup_file):
            """Restore selected backup"""
            import shutil
            
            try:
                backup_path = os.path.join(backup_dir, backup_file)
                db_path = os.path.abspath("store_management.db")
                
                # Create a backup of current database before restore
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                pre_restore_backup = os.path.join(backup_dir, f"before_restore_{timestamp}.db")
                shutil.copy2(db_path, pre_restore_backup)
                
                # Restore the selected backup
                shutil.copy2(backup_path, db_path)
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Database restored from {backup_file}"),
                    bgcolor=self.success_color,
                    duration=4000
                )
                page.snack_bar.open = True
                self.show_settings(page)
                
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Restore failed: {str(ex)}"),
                    bgcolor=self.danger_color,
                    duration=4000
                )
                page.snack_bar.open = True
            page.update()
        
        # Create backup list UI
        backup_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=400)
        
        for backup in backups[:30]:
            backup_path = os.path.join(backup_dir, backup)
            size_bytes = os.path.getsize(backup_path)
            
            # Format file size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            
            # Extract date from filename
            date_str = backup.replace('backup_', '').replace('.db', '')
            # Format date to be more readable
            if len(date_str) == 15:
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[9:11]}:{date_str[11:13]}:{date_str[13:15]}"
            else:
                formatted_date = date_str
            
            backup_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.FILE_PRESENT, size=24, color=self.accent_color),
                        ft.Column([
                            ft.Text(backup, size=13, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Size: {size_str} | Created: {formatted_date}", size=10, color="#888888"),
                        ], spacing=2, expand=True),
                        ft.IconButton(
                            icon=ft.icons.RESTORE,
                            icon_size=20,
                            icon_color=self.success_color,
                            on_click=lambda e, b=backup: restore_backup(e, b),
                            tooltip="Restore",
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_size=20,
                            icon_color=self.danger_color,
                            on_click=lambda e, b=backup: delete_backup(e, b),
                            tooltip="Delete",
                        ),
                    ]),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                )
            )
        
        # Add header with backup count
        header_text = ft.Text(f"📁 Available Backups ({len(backups)})", size=16, weight=ft.FontWeight.BOLD)
        
        dialog_content = ft.Column([
            header_text,
            ft.Divider(),
            backup_list,
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Close", on_click=close_dialog, expand=True),
            ]),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Backup Manager", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=dialog_content, width=500, height=500, padding=15),
            actions_alignment=ft.MainAxisAlignment.END,
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
                
                # Clear all tables
                cursor.execute("DELETE FROM materials")
                cursor.execute("DELETE FROM accessories")
                # Keep admin user (id=1), delete other users
                cursor.execute("DELETE FROM users WHERE id > 1")
                
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(
                    ft.Text("✓ Database reset successfully! Please restart the app."),
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
    def export_all_data(self, page: ft.Page):
        """Export all data to CSV files"""
        import csv
        from datetime import datetime
        
        try:
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
            
            # Export users
            users = self.dict_list(UserManager.get_all())
            if users:
                users_file = os.path.join(export_dir, f"users_{timestamp}.csv")
                with open(users_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=users[0].keys())
                    writer.writeheader()
                    writer.writerows(users)
            
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ All data exported to {export_dir}/"),
                bgcolor=self.success_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Export failed: {str(e)}"),
                bgcolor=self.danger_color,
                duration=4000
            )
            page.snack_bar.open = True
            page.update()

    def reset_database_confirm(self, page: ft.Page):
        """Confirm and reset database"""
        
        def confirm_reset(e):
            import sqlite3
            from database import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Clear all tables
            cursor.execute("DELETE FROM materials")
            cursor.execute("DELETE FROM accessories")
            cursor.execute("DELETE FROM users WHERE role != 'admin'")  # Keep admin user
            cursor.execute("DELETE FROM backups")
            
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text("✓ Database reset. Please restart the app."),
                bgcolor=self.success_color,
                duration=5000
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
            ft.Text("This action CANNOT be undone!", size=14, color=self.danger_color),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Yes, Reset", on_click=confirm_reset, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=10)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Reset Database"),
            content=ft.Container(content=dialog_content, width=400, height=380, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_category_manager(self, page: ft.Page):
        """Show category manager screen for mobile"""
        page.controls.clear()
        
        import sqlite3
        from database import DB_PATH
        
        is_mobile = page.width < 800 if page.width else False
        
        if is_mobile:
            nav = self.create_bottom_nav(page)
            sidebar = None
            padding_size = 12
        else:
            sidebar = self.create_sidebar(page)
            nav = None
            padding_size = 20
        
        # Get custom categories from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if custom_categories table exists, create if not
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '📁',
                color TEXT DEFAULT '#1976D2',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        
        cursor.execute("SELECT id, name, icon, color, created_at FROM custom_categories ORDER BY name")
        custom_categories = cursor.fetchall()
        
        # Get categories from materials (for counting)
        cursor.execute("PRAGMA table_info(materials)")
        material_columns = [col[1] for col in cursor.fetchall()]
        has_category_column = 'category' in material_columns
        
        # Predefined categories
        predefined_categories = [
            {"name": "Raw Material", "icon": "📦", "color": "#1976D2"},
            {"name": "Hardware", "icon": "🔩", "color": "#757575"},
            {"name": "Tools", "icon": "🔧", "color": "#FF9800"},
            {"name": "Electrical", "icon": "⚡", "color": "#FFC107"},
            {"name": "Plumbing", "icon": "💧", "color": "#00BCD4"},
            {"name": "Wood", "icon": "🪵", "color": "#8D6E63"},
            {"name": "Metal", "icon": "⚙️", "color": "#9E9E9E"},
            {"name": "Plastic", "icon": "🧴", "color": "#9C27B0"},
            {"name": "Glass", "icon": "🔮", "color": "#E91E63"},
            {"name": "Paint", "icon": "🎨", "color": "#FF5722"},
            {"name": "Fasteners", "icon": "📎", "color": "#4CAF50"},
            {"name": "Safety Equipment", "icon": "🦺", "color": "#F44336"},
            {"name": "Packaging", "icon": "📦", "color": "#009688"},
            {"name": "Office Supplies", "icon": "📎", "color": "#3F51B5"},
        ]
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("Category Manager", size=24, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.ADD_CIRCLE,
                    icon_size=28,
                    icon_color=self.success_color,
                    on_click=lambda e: self.add_custom_category_dialog(page),
                    tooltip="Add Category",
                ),
            ])
        )
        scroll_content.controls.append(ft.Container(height=10))
        scroll_content.controls.append(ft.Text("Manage your inventory categories", size=14, color="#888888"))
        scroll_content.controls.append(ft.Container(height=20))
        
        # Custom Categories Section
        if custom_categories:
            scroll_content.controls.append(
                ft.Text("🔒 My Custom Categories", size=18, weight=ft.FontWeight.BOLD, color=self.accent_color)
            )
            scroll_content.controls.append(ft.Divider())
            scroll_content.controls.append(ft.Container(height=10))
            
            for cat in custom_categories:
                cat_id, name, icon, color, created_at = cat
                
                # Count items in this category using category_id if available, otherwise category name
                materials_count = 0
                accessories_count = 0
                
                if has_category_column:
                    cursor.execute("SELECT COUNT(*) FROM materials WHERE category = ?", (name,))
                    materials_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM accessories WHERE category = ?", (name,))
                    accessories_count = cursor.fetchone()[0]
                else:
                    # Use category_id if available
                    try:
                        cursor.execute("SELECT COUNT(*) FROM materials WHERE category_id = ?", (cat_id,))
                        materials_count = cursor.fetchone()[0]
                    except:
                        pass
                    try:
                        cursor.execute("SELECT COUNT(*) FROM accessories WHERE category_id = ?", (cat_id,))
                        accessories_count = cursor.fetchone()[0]
                    except:
                        pass
                
                scroll_content.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Text(icon, size=30),
                                ft.Column([
                                    ft.Text(name, size=16, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"📦 {materials_count} materials, 🔧 {accessories_count} accessories", size=11, color="#888888"),
                                ], spacing=2, expand=True),
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.icons.EDIT,
                                        icon_size=20,
                                        icon_color=self.accent_color,
                                        on_click=lambda e, cid=cat_id: self.edit_custom_category_dialog(page, cid),
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE,
                                        icon_size=20,
                                        icon_color=self.danger_color,
                                        on_click=lambda e, cid=cat_id, n=name: self.delete_custom_category_dialog(page, cid, n),
                                    ),
                                ], spacing=0),
                            ]),
                            padding=12,
                        ),
                        elevation=2,
                        margin=ft.margin.only(bottom=8),
                    )
                )
            scroll_content.controls.append(ft.Container(height=15))
        
        # Predefined Categories Section
        scroll_content.controls.append(
            ft.Text("📁 Default Categories", size=18, weight=ft.FontWeight.BOLD, color="#888888")
        )
        scroll_content.controls.append(ft.Divider())
        scroll_content.controls.append(ft.Container(height=10))
        
        # Display predefined categories in a grid
        category_grid = ft.ResponsiveRow()
        for cat in predefined_categories:
            name = cat["name"]
            icon = cat["icon"]
            color = cat["color"]
            
            # Count items in this category
            materials_count = 0
            accessories_count = 0
            
            if has_category_column:
                cursor.execute("SELECT COUNT(*) FROM materials WHERE category = ?", (name,))
                materials_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM accessories WHERE category = ?", (name,))
                accessories_count = cursor.fetchone()[0]
            
            category_grid.controls.append(
                ft.Container(
                    content=ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text(icon, size=30),
                                ft.Text(name, size=14, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                                ft.Text(f"📦 {materials_count}", size=10, color="#888888"),
                                ft.Text(f"🔧 {accessories_count}", size=10, color="#888888"),
                                ft.Container(width=40, height=3, bgcolor=color, border_radius=2),
                            ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=12,
                        ),
                        elevation=1,
                    ),
                    col={"xs": 6, "sm": 4, "md": 3},
                    padding=5,
                )
            )
        scroll_content.controls.append(category_grid)
        
        conn.close()
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        page.update()

    def add_custom_category_dialog(self, page: ft.Page):
        """Dialog to add custom category"""
        
        name_field = ft.TextField(label="Category Name", width=300, bgcolor=self.card_color)
        
        icon_field = ft.Dropdown(
            label="Icon",
            width=120,
            options=[
                ft.dropdown.Option("📦", "📦 Box"),
                ft.dropdown.Option("🔩", "🔩 Screw"),
                ft.dropdown.Option("🔧", "🔧 Wrench"),
                ft.dropdown.Option("⚡", "⚡ Lightning"),
                ft.dropdown.Option("💧", "💧 Water"),
                ft.dropdown.Option("🪵", "🪵 Wood"),
                ft.dropdown.Option("⚙️", "⚙️ Gear"),
                ft.dropdown.Option("🧴", "🧴 Bottle"),
                ft.dropdown.Option("🔮", "🔮 Crystal"),
                ft.dropdown.Option("🎨", "🎨 Paint"),
                ft.dropdown.Option("📎", "📎 Paperclip"),
                ft.dropdown.Option("🦺", "🦺 Vest"),
                ft.dropdown.Option("📁", "📁 Folder"),
            ],
            value="📁",
            bgcolor=self.card_color,
        )
        
        color_field = ft.Dropdown(
            label="Color",
            width=120,
            options=[
                ft.dropdown.Option("#1976D2", "🔵 Blue"),
                ft.dropdown.Option("#4CAF50", "🟢 Green"),
                ft.dropdown.Option("#FF9800", "🟠 Orange"),
                ft.dropdown.Option("#F44336", "🔴 Red"),
                ft.dropdown.Option("#9C27B0", "🟣 Purple"),
                ft.dropdown.Option("#00BCD4", "🔷 Cyan"),
                ft.dropdown.Option("#757575", "⚫ Gray"),
            ],
            value="#1976D2",
            bgcolor=self.card_color,
        )
        
        status_text = ft.Text("", size=12, color="#888888")
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def save_category(e):
            name = name_field.value.strip()
            if not name:
                status_text.value = "❌ Please enter a category name"
                status_text.color = self.danger_color
                page.update()
                return
            
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO custom_categories (name, icon, color, created_by) VALUES (?, ?, ?, ?)",
                    (name, icon_field.value, color_field.value, self.current_user.get('name', 'User'))
                )
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Category '{name}' added!"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_category_manager(page)
                
            except sqlite3.IntegrityError:
                status_text.value = "❌ Category already exists!"
                status_text.color = self.danger_color
                page.update()
            except Exception as ex:
                status_text.value = f"❌ Error: {str(ex)}"
                status_text.color = self.danger_color
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Add Custom Category", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            ft.Row([icon_field, color_field], spacing=10),
            status_text,
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Save", on_click=save_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("New Category"),
            content=ft.Container(content=dialog_content, width=400, height=350, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def edit_custom_category(self, page: ft.Page, category_id):
        """Edit custom category"""
        
        import sqlite3
        from database import DB_PATH
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name, icon, color FROM custom_categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        conn.close()
        
        if not category:
            return
        
        name_field = ft.TextField(label="Category Name", value=category[0], width=300, bgcolor=self.card_color)
        
        icon_field = ft.Dropdown(
            label="Icon",
            width=100,
            options=[
                ft.dropdown.Option("📦", "📦"), ft.dropdown.Option("🔩", "🔩"), ft.dropdown.Option("🔧", "🔧"),
                ft.dropdown.Option("⚡", "⚡"), ft.dropdown.Option("💧", "💧"), ft.dropdown.Option("🪵", "🪵"),
                ft.dropdown.Option("⚙️", "⚙️"), ft.dropdown.Option("🧴", "🧴"), ft.dropdown.Option("🔮", "🔮"),
                ft.dropdown.Option("🎨", "🎨"), ft.dropdown.Option("📎", "📎"), ft.dropdown.Option("🦺", "🦺"),
                ft.dropdown.Option("📁", "📁"),
            ],
            value=category[1],
            bgcolor=self.card_color,
        )
        
        color_field = ft.Dropdown(
            label="Color",
            width=100,
            options=[
                ft.dropdown.Option("#1976D2", "🔵 Blue"), ft.dropdown.Option("#4CAF50", "🟢 Green"),
                ft.dropdown.Option("#FF9800", "🟠 Orange"), ft.dropdown.Option("#F44336", "🔴 Red"),
                ft.dropdown.Option("#9C27B0", "🟣 Purple"), ft.dropdown.Option("#00BCD4", "🔷 Cyan"),
                ft.dropdown.Option("#757575", "⚫ Gray"),
            ],
            value=category[2],
            bgcolor=self.card_color,
        )
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def update_category(e):
            name = name_field.value.strip()
            if not name:
                return
            
            import sqlite3
            from database import DB_PATH
            
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE custom_categories SET name = ?, icon = ?, color = ? WHERE id = ?",
                    (name, icon_field.value, color_field.value, category_id)
                )
                conn.commit()
                conn.close()
                
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Category updated!"), bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_category_manager(page)
                
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Error: {str(ex)}"), bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
        
        dialog_content = ft.Column([
            ft.Text("Edit Category", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            ft.Row([icon_field, color_field], spacing=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Update", on_click=update_category, style=ft.ButtonStyle(bgcolor=self.success_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Category"),
            content=ft.Container(content=dialog_content, width=400, height=320, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
    def delete_custom_category(self, page: ft.Page, category_id):
        """Delete custom category"""
        
        import sqlite3
        from database import DB_PATH
        
        # Check if category has items
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM materials WHERE category_id = ?", (category_id,))
        materials_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM accessories WHERE category_id = ?", (category_id,))
        accessories_count = cursor.fetchone()[0]
        conn.close()
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def confirm_delete(e):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Move items to 'Other' category or set to NULL
            if materials_count > 0 or accessories_count > 0:
                cursor.execute("UPDATE materials SET category_id = NULL WHERE category_id = ?", (category_id,))
                cursor.execute("UPDATE accessories SET category_id = NULL WHERE category_id = ?", (category_id,))
            
            cursor.execute("DELETE FROM custom_categories WHERE id = ?", (category_id,))
            conn.commit()
            conn.close()
            
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("✓ Category deleted!"), bgcolor=self.success_color)
            page.snack_bar.open = True
            self.show_category_manager(page)
        
        warning_text = ""
        if materials_count > 0 or accessories_count > 0:
            warning_text = f"⚠️ This category contains {materials_count} materials and {accessories_count} accessories. They will be moved to uncategorized."
        
        dialog_content = ft.Column([
            ft.Text("🗑️ Delete Category", size=18, weight=ft.FontWeight.BOLD, color=self.danger_color),
            ft.Divider(),
            ft.Text("Are you sure you want to delete this category?", size=14),
            ft.Text(warning_text, size=12, color=self.warning_color),
            ft.Container(height=10),
            ft.Row([
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.FilledButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ], spacing=12)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Container(content=dialog_content, width=400, height=250, padding=15),
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()
if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
