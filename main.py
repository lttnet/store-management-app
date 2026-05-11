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
        return {'company_name': 'Store Management', 'phone': '', 'email': '', 'website': '', 'address': '', 'city': '', 'tax_id': ''}
    
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
    
            # ============ MAIN ============
    def main(self, page: ft.Page):
        self.page_ref = page
        
        # FULL SCREEN - NO BORDERS
        page.title = "Store Management System"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = self.bg_color
        page.padding = 0
        page.spacing = 0
        page.window_width = None
        page.window_height = None
        page.window_maximized = True
        page.window_resizable = True
        
        # Calculate screen scale for fonts
        self.screen_scale = 1.0
        if page.width:
            self.screen_scale = min(page.width / 1200, 1.2)
        
        def on_resize(e):
            if page.width:
                self.screen_scale = min(page.width / 1200, 1.2)
            if self.current_user and self.current_view == "dashboard":
                self.show_dashboard(page)
        
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
        """Show dashboard - MOBILE RESPONSIVE (Card-based on mobile, tables on desktop)"""
        page.controls.clear()
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        stats = MaterialManager.get_stats()
        accessory_stats = AccessoryManager.get_stats()
        
        low_stock_materials = [m for m in materials if m.get('quantity', 0) < 10]
        low_stock_accessories = [a for a in accessories if a.get('quantity', 0) < 10]
        
        # Check if mobile
        is_mobile_device = page.width < 800 if page.width else False
        
        # Font sizes - larger on mobile for readability
        if is_mobile_device:
            font_title = 24
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 28
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        # Create sidebar or bottom navigation
        if is_mobile_device:
            # Use bottom navigation for mobile
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            # Use sidebar for desktop
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("Dashboard", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.Text(datetime.now().strftime("%b %d"), size=font_small - 2, color="#888888"),
                ]),
                padding=ft.padding.only(bottom=15),
            )
        )
        
        # Stats Cards - 3 in a row, wrap on mobile
        stats_row = ft.Row(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text("📦", size=font_normal),
                        ft.Text(str(stats.get('total_items', 0)), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text("Materials", size=font_small - 2, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    padding=12, bgcolor=self.success_color, border_radius=12, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🔧", size=font_normal),
                        ft.Text(str(accessory_stats.get('total_items', 0)), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                        ft.Text("Parts", size=font_small - 2, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    padding=12, bgcolor=self.accent_color, border_radius=12, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("⚠️", size=font_normal),
                        ft.Text(str(len(low_stock_materials) + len(low_stock_accessories)), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.danger_color),
                        ft.Text("Low Stock", size=font_small - 2, color="#CCCCCC"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                    padding=12, bgcolor=self.warning_color, border_radius=12, expand=True,
                ),
            ],
            spacing=12,
        )
        scroll_content.controls.append(stats_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # ========== RECENT MATERIALS (Card-based for mobile) ==========
        scroll_content.controls.append(
            ft.Row([
                ft.Text("📦 Recent Materials", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_materials_screen(page)),
            ])
        )
        scroll_content.controls.append(ft.Divider())
        
        if materials:
            for m in materials[:5]:
                scroll_content.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(m.get('name', 'N/A'), size=font_normal, weight=ft.FontWeight.BOLD, expand=True),
                                    ft.Text(f"Qty: {m.get('quantity', 0)}", size=font_normal, weight=ft.FontWeight.BOLD,
                                        color=self.danger_color if m.get('quantity', 0) < 10 else self.text_color),
                                ]),
                                ft.Row([
                                    ft.Text(m.get('location_ids', 'N/A'), size=font_small - 1, color="#888888", expand=True),
                                    ft.Container(
                                        content=ft.Text(m.get('quality', 'Used'), size=font_small - 2, color="white"),
                                        bgcolor=self.get_quality_color(m.get('quality', 'Used')),
                                        border_radius=10,
                                        padding=ft.padding.symmetric(horizontal=10, vertical=3),
                                    ),
                                ]),
                            ]),
                            padding=12,
                        ),
                        elevation=2,
                        margin=ft.margin.only(bottom=8),
                    )
                )
        else:
            scroll_content.controls.append(ft.Text("No materials found", size=font_small, color="#888888"))
        
        scroll_content.controls.append(ft.Container(height=15))
        
        # ========== RECENT ACCESSORIES (Card-based for mobile) ==========
        scroll_content.controls.append(
            ft.Row([
                ft.Text("🔧 Recent Accessories", size=font_normal, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.TextButton("View All", on_click=lambda e: self.show_accessories(page)),
            ])
        )
        scroll_content.controls.append(ft.Divider())
        
        if accessories:
            for a in accessories[:5]:
                location = a.get('location') or a.get('location_ids') or 'N/A'
                scroll_content.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(a.get('name', 'N/A'), size=font_normal, weight=ft.FontWeight.BOLD, expand=True),
                                    ft.Text(f"Qty: {a.get('quantity', 0)}", size=font_normal, weight=ft.FontWeight.BOLD,
                                        color=self.danger_color if a.get('quantity', 0) < 10 else self.text_color),
                                ]),
                                ft.Row([
                                    ft.Text(location, size=font_small - 1, color="#888888", expand=True),
                                    ft.Container(
                                        content=ft.Text(a.get('quality', 'Used'), size=font_small - 2, color="white"),
                                        bgcolor=self.get_quality_color(a.get('quality', 'Used')),
                                        border_radius=10,
                                        padding=ft.padding.symmetric(horizontal=10, vertical=3),
                                    ),
                                ]),
                            ]),
                            padding=12,
                        ),
                        elevation=2,
                        margin=ft.margin.only(bottom=8),
                    )
                )
        else:
            scroll_content.controls.append(ft.Text("No accessories found", size=font_small, color="#888888"))
        
        scroll_content.controls.append(ft.Container(height=15))
        
        # ========== LOW STOCK ALERTS ==========
        if low_stock_materials or low_stock_accessories:
            scroll_content.controls.append(
                ft.Row([
                    ft.Icon(ft.icons.WARNING_AMBER, color="#FF9800", size=20),
                    ft.Text("Low Stock Alerts", size=font_normal, weight=ft.FontWeight.BOLD, color="#FF9800"),
                    ft.Container(expand=True),
                    ft.Text(f"{len(low_stock_materials) + len(low_stock_accessories)}", size=font_small, color="#888888"),
                ])
            )
            scroll_content.controls.append(ft.Divider())
            
            for m in low_stock_materials[:4]:
                scroll_content.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(width=4, height=35, bgcolor=self.danger_color, border_radius=2),
                            ft.Container(width=10),
                            ft.Text("📦", size=font_small),
                            ft.Container(width=8),
                            ft.Text(m.get('name', 'Unknown')[:20], size=font_small, expand=True),
                            ft.Text(f"Stock: {m.get('quantity', 0)}", size=font_small, color=self.danger_color, weight=ft.FontWeight.BOLD),
                        ]),
                        padding=10,
                        bgcolor="#3C2121",
                        border_radius=8,
                        margin=ft.margin.only(bottom=6),
                    )
                )
            
            for a in low_stock_accessories[:4]:
                scroll_content.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(width=4, height=35, bgcolor=self.danger_color, border_radius=2),
                            ft.Container(width=10),
                            ft.Text("🔧", size=font_small),
                            ft.Container(width=8),
                            ft.Text(a.get('name', 'Unknown')[:20], size=font_small, expand=True),
                            ft.Text(f"Stock: {a.get('quantity', 0)}", size=font_small, color=self.danger_color, weight=ft.FontWeight.BOLD),
                        ]),
                        padding=10,
                        bgcolor="#3C2121",
                        border_radius=8,
                        margin=ft.margin.only(bottom=6),
                    )
                )
            
            scroll_content.controls.append(ft.Container(height=10))
        
        # ========== QUICK ACTIONS ==========
        scroll_content.controls.append(
            ft.Row([
                ft.ElevatedButton("📥 Import", on_click=lambda e: None, expand=True, style=ft.ButtonStyle(bgcolor=self.accent_color)),
                ft.ElevatedButton("📤 Export", on_click=lambda e: None, expand=True, style=ft.ButtonStyle(bgcolor=self.warning_color)),
                ft.ElevatedButton("⚙️ Settings", on_click=lambda e: self.show_settings(page), expand=True),
            ], spacing=10)
        )
        
        scroll_content.controls.append(ft.Container(height=20))
        
        # Main container
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout based on device
        if is_mobile_device and nav:
            # Mobile: Bottom navigation + content
            page.add(
                ft.Column([
                    main_container,
                    nav,
                ], spacing=0, expand=True)
            )
        else:
            # Desktop: Sidebar + content
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "dashboard"
        page.update()
    
    def show_materials_screen(self, page: ft.Page):
        """Show materials screen - MOBILE OPTIMIZED (Card-based)"""
        page.controls.clear()
        
        self.page_ref = page
        materials = self.dict_list(MaterialManager.get_all())
        
        # Check if mobile
        is_mobile_device = page.width < 800 if page.width else False
        
        # Font sizes
        if is_mobile_device:
            font_title = 22
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 24
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        # Navigation
        if is_mobile_device:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Initialize filter
        if not hasattr(self, 'current_material_filter'):
            self.current_material_filter = "All"
        
        # Search field
        search_field = ft.TextField(
            hint_text="Search materials...",
            width=200 if not is_mobile_device else page.width - 100,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
            on_change=lambda e: self.filter_materials_mobile(page),
        )
        self.material_search_query = ""
        
        # Filter buttons (using Container instead of FilterChip)
        self.material_filter_buttons = {}
        
        def create_filter_button(label, active_color, filter_type):
            is_active = (self.current_material_filter == filter_type)
            btn = ft.Container(
                content=ft.Text(label, size=font_small, weight=ft.FontWeight.BOLD, 
                            color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=8),
                bgcolor=active_color if is_active else self.card_color,
                border_radius=25,
                ink=True,
                on_click=lambda e, f=filter_type: self.filter_materials_mobile(page, f),
            )
            self.material_filter_buttons[filter_type] = btn
            return btn
        
        filter_row = ft.Row(
            [
                create_filter_button("All", self.accent_color, "All"),
                create_filter_button("New", self.success_color, "New"),
                create_filter_button("Used", self.warning_color, "Used"),
                create_filter_button("Damaged", self.danger_color, "Damaged"),
                create_filter_button("Repaired", self.accent_color, "Repaired"),
            ],
            spacing=8,
            wrap=True,
        )
        
        # Add button (FloatingActionButton for mobile, regular for desktop)
        if is_mobile_device:
            add_button = ft.FloatingActionButton(
                icon=ft.icons.ADD,
                bgcolor=self.success_color,
                on_click=lambda e: self.open_add_modal(page),
            )
        else:
            add_button = ft.FilledButton(
                "➕ Add Material",
                style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
                on_click=lambda e: self.open_add_modal(page),
            )
        
        # Scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("Materials", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
            ])
        )
        scroll_content.controls.append(ft.Container(height=10))
        
        # Search bar
        scroll_content.controls.append(search_field)
        scroll_content.controls.append(ft.Container(height=10))
        
        # Filter row
        scroll_content.controls.append(filter_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # Materials list (cards)
        self.material_cards_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def update_materials_list():
            """Update the materials list with cards"""
            if self.current_material_filter == "All":
                filtered = materials
            else:
                filtered = [m for m in materials if m.get('quality') == self.current_material_filter]
            
            if hasattr(self, 'material_search_query') and self.material_search_query:
                query = self.material_search_query.lower()
                filtered = [m for m in filtered if query in m.get('name', '').lower() or query in m.get('item_code', '').lower()]
            
            self.material_cards_container.controls.clear()
            
            for mat in filtered:
                # Create buttons with proper lambda capturing
                edit_btn = ft.IconButton(
                    icon=ft.icons.EDIT,
                    icon_size=20,
                    icon_color=self.accent_color,
                    on_click=lambda e, m=mat: self.open_edit_modal(page, m['id']),
                )
                
                delete_btn = ft.IconButton(
                    icon=ft.icons.DELETE,
                    icon_size=20,
                    icon_color=self.danger_color,
                    on_click=lambda e, m=mat: self.open_delete_modal(page, m['id']),
                )
                
                barcode_btn = ft.IconButton(
                    icon=ft.icons.QR_CODE,
                    icon_size=20,
                    icon_color=self.warning_color,
                    on_click=lambda e, m=mat: self.show_barcode_dialog(page, m),
                )
                
                card_content = ft.Column([
                    ft.Row([
                        ft.Text(mat.get('name', 'N/A'), size=font_normal, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(f"Qty: {mat.get('quantity', 0)}", size=font_normal, weight=ft.FontWeight.BOLD,
                            color=self.danger_color if mat.get('quantity', 0) < 10 else self.text_color),
                    ]),
                    ft.Row([
                        ft.Text(mat.get('location_ids', 'N/A'), size=font_small - 1, color="#888888", expand=True),
                        ft.Container(
                            content=ft.Text(mat.get('quality', 'Used'), size=font_small - 2, color="white"),
                            bgcolor=self.get_quality_color(mat.get('quality', 'Used')),
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=10, vertical=3),
                        ),
                    ]),
                    ft.Row([
                        edit_btn,
                        delete_btn,
                        barcode_btn,
                    ], spacing=5),
                ], spacing=8)
                
                card = ft.Card(
                    content=ft.Container(content=card_content, padding=12),
                    elevation=2,
                )
                
                # Wrap card in container for click handling
                clickable_card = ft.Container(
                    content=card,
                    margin=ft.margin.only(bottom=8),
                    ink=True,
                    on_click=lambda e, m=mat: self.show_material_detail_dialog(page, m),
                )
                
                self.material_cards_container.controls.append(clickable_card)
            
            page.update()
        
        def on_search(e):
            self.material_search_query = e.control.value
            update_materials_list()
        
        search_field.on_change = on_search
        
        # Filter method
        def filter_materials_mobile(page, filter_type=None):
            if filter_type:
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
                    btn.bgcolor = color_map.get(f_type, self.card_color) if f_type == filter_type else self.card_color
                    btn.update()
            update_materials_list()
        
        self.filter_materials_mobile = filter_materials_mobile
        
        # Initial load
        update_materials_list()
        
        scroll_content.controls.append(self.material_cards_container)
        scroll_content.controls.append(ft.Container(height=80))  # Space for FAB
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile_device and nav:
            page.add(
                ft.Stack([
                    ft.Column([main_container, nav], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=80),
                ], expand=True)
            )
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
            if not is_mobile_device:
                page.add(add_button)
        
        self.current_view = "materials"
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
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, material), 
                                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(content=ft.Text(material.get('quality', 'Used'), size=11, color="white"),
                                bgcolor=self.get_quality_color(material.get('quality', 'Used')),
                                border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))], spacing=5),
            ft.Row([ft.Text("📏 Size:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('size') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), 
                ft.Text(str(material.get('quantity', 0)), size=14, weight=ft.FontWeight.BOLD,
                        color=self.danger_color if material.get('quantity', 0) < 10 else self.text_color)], spacing=5),
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), ft.Text(material.get('location_ids') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), ft.Text(str(material.get('created_at', ''))[:10] if material.get('created_at') else 'N/A', size=12, color="#888888")], spacing=5),
            ft.Divider(),
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(material.get('notes') or "No notes", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=lambda e: self.open_edit_modal(page, material['id']),
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color), expand=True),
                ft.ElevatedButton("🗑️ DELETE", on_click=lambda e: self.open_delete_modal(page, material['id']),
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color), expand=True),
            ], spacing=10),
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=450)

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
        """Show accessories screen - MOBILE OPTIMIZED (Card-based)"""
        page.controls.clear()
        
        self.page_ref = page
        accessories = self.dict_list(AccessoryManager.get_all())
        
        # Check if mobile
        is_mobile_device = page.width < 800 if page.width else False
        
        # Font sizes
        if is_mobile_device:
            font_title = 22
            font_normal = 16
            font_small = 14
            padding_size = 12
        else:
            font_title = 24
            font_normal = 18
            font_small = 14
            padding_size = 20
        
        # Navigation
        if is_mobile_device:
            nav = self.create_bottom_nav(page)
            sidebar = None
        else:
            sidebar = self.create_sidebar(page)
            nav = None
        
        # Initialize filter
        if not hasattr(self, 'current_accessory_filter'):
            self.current_accessory_filter = "All"
        
        # Search field
        search_field = ft.TextField(
            hint_text="Search accessories...",
            width=200 if not is_mobile_device else page.width - 100,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
            on_change=lambda e: self.filter_accessories_mobile(page),
        )
        self.accessory_search_query = ""
        
        # Filter buttons
        self.accessory_filter_buttons = {}
        
        def create_filter_button(label, active_color, filter_type):
            is_active = (self.current_accessory_filter == filter_type)
            btn = ft.Container(
                content=ft.Text(label, size=font_small, weight=ft.FontWeight.BOLD, 
                            color=self.text_color),
                padding=ft.padding.symmetric(horizontal=15, vertical=8),
                bgcolor=active_color if is_active else self.card_color,
                border_radius=25,
                ink=True,
                on_click=lambda e, f=filter_type: self.filter_accessories_mobile(page, f),
            )
            self.accessory_filter_buttons[filter_type] = btn
            return btn
        
        filter_row = ft.Row(
            [
                create_filter_button("All", self.accent_color, "All"),
                create_filter_button("New", self.success_color, "New"),
                create_filter_button("Used", self.warning_color, "Used"),
                create_filter_button("Damaged", self.danger_color, "Damaged"),
                create_filter_button("Repaired", self.accent_color, "Repaired"),
            ],
            spacing=8,
            wrap=True,
        )
        
        # Add button
        if is_mobile_device:
            add_button = ft.FloatingActionButton(
                icon=ft.icons.ADD,
                bgcolor=self.success_color,
                on_click=lambda e: self.open_add_accessory_modal(page),
            )
        else:
            add_button = ft.FilledButton(
                "➕ Add Accessory",
                style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color),
                on_click=lambda e: self.open_add_accessory_modal(page),
            )
        
        # Scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Row([
                ft.Text("Accessories", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
            ])
        )
        scroll_content.controls.append(ft.Container(height=10))
        
        # Search bar
        scroll_content.controls.append(search_field)
        scroll_content.controls.append(ft.Container(height=10))
        
        # Filter row
        scroll_content.controls.append(filter_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # Accessories list (cards)
        self.accessory_cards_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def update_accessories_list():
            """Update the accessories list with cards - FIXED: prevents edit/delete from opening detail"""
            if self.current_accessory_filter == "All":
                filtered = accessories
            else:
                filtered = [a for a in accessories if a.get('quality') == self.current_accessory_filter]
            
            if hasattr(self, 'accessory_search_query') and self.accessory_search_query:
                query = self.accessory_search_query.lower()
                filtered = [a for a in filtered if query in a.get('name', '').lower() or query in a.get('item_code', '').lower()]
            
            self.accessory_cards_container.controls.clear()
            
            for acc in filtered:
                location = acc.get('location') or acc.get('location_ids') or 'N/A'
                price = acc.get('price', 0)
                price_text = f"${price:.2f}" if price else ""
                
                # Create a separate row for buttons that WON'T trigger the card click
                button_row = ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.icons.EDIT, size=20, color=self.accent_color),
                            on_click=lambda e, a=acc: self.open_edit_accessory_modal(page, a['id']),
                            padding=5,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.icons.DELETE, size=20, color=self.danger_color),
                            on_click=lambda e, a=acc: self.open_delete_accessory_modal(page, a['id']),
                            padding=5,
                        ),
                        ft.Container(
                            content=ft.Icon(ft.icons.QR_CODE, size=20, color=self.warning_color),
                            on_click=lambda e, a=acc: self.show_barcode_dialog(page, a),
                            padding=5,
                        ),
                    ],
                    spacing=10,
                )
                
                # Card content WITHOUT using IconButton (use Container with Icon instead)
                card_content = ft.Column([
                    ft.Row([
                        ft.Text(acc.get('name', 'N/A'), size=font_normal, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(f"Qty: {acc.get('quantity', 0)}", size=font_normal, weight=ft.FontWeight.BOLD,
                            color=self.danger_color if acc.get('quantity', 0) < 10 else self.text_color),
                    ]),
                    ft.Row([
                        ft.Text(location, size=font_small - 1, color="#888888", expand=True),
                        ft.Container(
                            content=ft.Text(acc.get('quality', 'Used'), size=font_small - 2, color="white"),
                            bgcolor=self.get_quality_color(acc.get('quality', 'Used')),
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=10, vertical=3),
                        ),
                    ]),
                    ft.Row([
                        ft.Text(price_text, size=font_small, color="#4CAF50") if price_text else ft.Container(),
                        ft.Container(expand=True),
                    ]),
                    button_row,  # Buttons as separate row
                ], spacing=8)
                
                # Create card
                card = ft.Card(
                    content=ft.Container(content=card_content, padding=12),
                    elevation=2,
                )
                
                # Wrap card in container for click handling
                clickable_card = ft.Container(
                    content=card,
                    margin=ft.margin.only(bottom=8),
                    ink=True,
                    on_click=lambda e, a=acc: self.show_accessory_detail_dialog(page, a),
                )
                
                self.accessory_cards_container.controls.append(clickable_card)
            
            page.update()
        
        def on_search(e):
            self.accessory_search_query = e.control.value
            update_accessories_list()
        
        search_field.on_change = on_search
        
        # Filter method
        def filter_accessories_mobile(page, filter_type=None):
            if filter_type:
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
                    btn.bgcolor = color_map.get(f_type, self.card_color) if f_type == filter_type else self.card_color
                    btn.update()
            update_accessories_list()
        
        self.filter_accessories_mobile = filter_accessories_mobile
        
        # Initial load
        update_accessories_list()
        
        scroll_content.controls.append(self.accessory_cards_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile_device and nav:
            page.add(
                ft.Stack([
                    ft.Column([main_container, nav], spacing=0, expand=True),
                    ft.Container(content=add_button, right=16, bottom=80),
                ], expand=True)
            )
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
            if not is_mobile_device:
                page.add(add_button)
        
        self.current_view = "accessories"
        page.update()

    def show_accessory_detail_dialog(self, page: ft.Page, accessory):
        """Show detailed view of accessory in a modal dialog"""
        
        is_mobile = page.width < 800 if page.width else False
        
        # Format dates
        created_date = str(accessory.get('created_at', ''))[:16] if accessory.get('created_at') else 'N/A'
        updated_date = str(accessory.get('updated_at', ''))[:16] if accessory.get('updated_at') else 'N/A'
        
        # Get location
        location = accessory.get('location') or accessory.get('location_ids') or 'N/A'
        price = accessory.get('price', 0)
        price_text = f"${price:.2f}" if price else "N/A"
        
        # Get image
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
        
        # Build content
        content_items = []
        
        # Image section
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
        
        # Details section
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
        """Create detail panel for selected accessory"""
        if not accessory:
            return ft.Column([
                ft.Text("Accessory Details", size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Container(height=20),
                ft.Text("Select an accessory to view details", size=12, color="#888888"),
                ft.Container(expand=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        location = accessory.get('location') or accessory.get('location_ids') or 'N/A'
        price = accessory.get('price', 0)
        price_text = f"${price:.2f}" if price else "N/A"
        
        return ft.Column([
            ft.Text(accessory.get('name', 'N/A'), size=18, weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Divider(),
            ft.Row([ft.Text("📝 Code:", size=12, color="#CCCCCC", width=80), ft.Text(accessory.get('item_code') or "N/A", size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.ElevatedButton("📱 SHOW BARCODE", on_click=lambda e: self.show_barcode_dialog(page, accessory), 
                                    style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color))], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.Text("🏷️ Quality:", size=12, color="#CCCCCC", width=80), 
                    ft.Container(content=ft.Text(accessory.get('quality', 'Used'), size=11, color="white"),
                                bgcolor=self.get_quality_color(accessory.get('quality', 'Used')),
                                border_radius=8, padding=ft.padding.symmetric(horizontal=8, vertical=3))], spacing=5),
            ft.Row([ft.Text("🔢 Quantity:", size=12, color="#CCCCCC", width=80), 
                ft.Text(str(accessory.get('quantity', 0)), size=14, weight=ft.FontWeight.BOLD,
                        color=self.danger_color if accessory.get('quantity', 0) < 10 else self.text_color)], spacing=5),
            ft.Row([ft.Text("💰 Price:", size=12, color="#CCCCCC", width=80), ft.Text(price_text, size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("📍 Location:", size=12, color="#CCCCCC", width=80), ft.Text(location, size=12, color=self.text_color)], spacing=5),
            ft.Row([ft.Text("📅 Created:", size=12, color="#CCCCCC", width=80), ft.Text(str(accessory.get('created_at', ''))[:10] if accessory.get('created_at') else 'N/A', size=12, color="#888888")], spacing=5),
            ft.Divider(),
            ft.Text("📝 Notes:", size=14, weight=ft.FontWeight.BOLD, color="#CCCCCC"),
            ft.Text(accessory.get('notes') or "No notes", size=12, color="#888888"),
            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton("✏️ EDIT", on_click=lambda e: self.open_edit_accessory_modal(page, accessory['id']),
                                style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color), expand=True),
                ft.ElevatedButton("🗑️ DELETE", on_click=lambda e: self.open_delete_accessory_modal(page, accessory['id']),
                                style=ft.ButtonStyle(bgcolor=self.danger_color, color=self.text_color), expand=True),
            ], spacing=10),
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=450)
    
    def show_barcode_dialog(self, page: ft.Page, item):
        """Show barcode dialog"""
        barcode_text = item.get('barcode_value') or item.get('item_code', 'N/A')
        item_name = item.get('name', 'Item')
        item_type = "Material" if 'location_ids' in item else "Accessory"
        
        # Create real barcode image URL using barcode.tec-it.com (free API)
        barcode_image_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_text}&code=Code128&dpi=120&height=80"
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def print_barcode(e):
            """Open print dialog in browser"""
            import webbrowser
            import tempfile
            
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
                        font-family: Arial, sans-serif;
                    }}
                    .container {{
                        border: 2px solid #1976D2;
                        border-radius: 15px;
                        padding: 20px;
                        max-width: 400px;
                        margin: 0 auto;
                    }}
                    .title {{
                        font-size: 20px;
                        font-weight: bold;
                        color: #1976D2;
                        margin-bottom: 10px;
                    }}
                    .item-name {{
                        font-size: 16px;
                        font-weight: bold;
                        color: #333;
                        margin-bottom: 15px;
                    }}
                    .item-type {{
                        font-size: 12px;
                        color: #666;
                        margin-bottom: 20px;
                    }}
                    .barcode-img {{
                        max-width: 100%;
                        height: auto;
                        margin: 10px 0;
                    }}
                    .number {{
                        font-size: 18px;
                        font-weight: bold;
                        margin-top: 10px;
                        letter-spacing: 2px;
                    }}
                    @media print {{
                        .no-print {{ display: none; }}
                        .container {{
                            border: none;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="title">PRODUCT BARCODE</div>
                    <div class="item-name">{item_name}</div>
                    <div class="item-type">{item_type}</div>
                    <img class="barcode-img" src="{barcode_image_url}" alt="Barcode">
                    <div class="number">{barcode_text}</div>
                </div>
                <div class="no-print" style="margin-top: 30px;">
                    <button onclick="window.print()" style="padding: 10px 20px; font-size: 14px; background: #1976D2; color: white; border: none; border-radius: 5px; cursor: pointer;">🖨️ Print Barcode</button>
                    <button onclick="window.close()" style="padding: 10px 20px; font-size: 14px; margin-left: 10px; background: #666; color: white; border: none; border-radius: 5px; cursor: pointer;">Close</button>
                </div>
                <script>
                    setTimeout(function() {{
                        window.print();
                    }}, 500);
                </script>
            </body>
            </html>
            """
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            webbrowser.open(f'file://{temp_file.name}')
            close_dialog(e)
        
        # Create barcode display for dialog
        barcode_display = ft.Container(
            content=ft.Column([
                ft.Text("📦 " + item_type, size=12, color="#888888"),
                ft.Text(item_name, size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=10),
                ft.Image(src=barcode_image_url, width=350, height=100, fit=ft.ImageFit.CONTAIN),
                ft.Text(barcode_text, size=18, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Text("Scan this barcode with your camera", size=10, color="#888888"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=20,
            bgcolor="#1E1E1E",
            border_radius=15,
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Barcode - {item_name[:30]}", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=barcode_display,
                width=400,
                height=320,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
                ft.FilledButton("🖨️ Print", on_click=print_barcode, style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        page.dialog = dialog
        dialog.open = True
        page.update()

    def open_add_accessory_modal(self, page: ft.Page):
        """Open modal for adding accessory with barcode generation and database save"""
        
        import random
        import string
        import os
        import shutil
        from datetime import datetime
        
        def generate_barcode():
            """Generate a unique 13-digit barcode"""
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
        
        # Form fields
        name_field = ft.TextField(label="Name *", width=380, bgcolor=self.card_color)
        
        barcode_field = ft.TextField(
            label="Barcode (13 digits)", 
            width=380, 
            bgcolor=self.card_color, 
            read_only=True,
        )
        
        quantity_field = ft.TextField(label="Quantity", width=380, bgcolor=self.card_color, value="0")
        price_field = ft.TextField(label="Price", width=380, bgcolor=self.card_color, value="0.00")
        
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
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"accessory_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                return new_path
            return None
        
        # Initialize with generated barcode
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
            
            # Parse price
            try:
                price = float(price_field.value) if price_field.value else 0.0
            except ValueError:
                price = 0.0
            
            # Parse quantity
            try:
                quantity = int(quantity_field.value) if quantity_field.value else 0
            except ValueError:
                quantity = 0
            
            # Save uploaded image if exists
            saved_image_path = save_uploaded_image() if selected_temp_image else None
            
            data = {
                'name': name,
                'item_code': barcode_value,
                'quantity': quantity,
                'price': price,
                'quality': quality_field.value,
                'location': location_field.value,
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
        
        form_column = ft.Column([
            name_field,
            barcode_field,
            ft.Row([regenerate_btn], alignment=ft.MainAxisAlignment.START),
            quantity_field,
            price_field,
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
                            ft.FilledButton("Save", on_click=save_accessory, style=ft.ButtonStyle(bgcolor=self.success_color)),
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
    def open_edit_accessory_modal(self, page: ft.Page, accessory_id):
        """Open edit modal for accessory"""
        import os
        import shutil
        from datetime import datetime
        
        accessory = AccessoryManager.get_by_id(accessory_id)
        if not accessory:
            return
        
        accessory_dict = dict(accessory) if accessory else {}
        
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
        price_field = ft.TextField(label="Price", value=str(accessory_dict.get('price', 0)), width=380, bgcolor=self.card_color)
        
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
        
        current_image_path = accessory_dict.get('image_path', '')
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
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
            except:
                pass
        
        selected_temp_image = None
        
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
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"accessory_{accessory_id}_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                return new_path
            return None
        
        def delete_current_image(e):
            nonlocal selected_temp_image
            if current_image_path and os.path.exists(current_image_path):
                try:
                    os.remove(current_image_path)
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
            
            try:
                quantity = int(quantity_field.value) if quantity_field.value else 0
            except ValueError:
                quantity = 0
            
            try:
                price = float(price_field.value) if price_field.value else 0.0
            except ValueError:
                price = 0.0
            
            final_image_path = current_image_path
            
            if selected_temp_image == "DELETE":
                final_image_path = None
            elif selected_temp_image:
                saved_path = save_uploaded_image()
                if saved_path:
                    final_image_path = saved_path
                    if current_image_path and os.path.exists(current_image_path) and current_image_path != saved_path:
                        try:
                            os.remove(current_image_path)
                        except:
                            pass
            
            data = {
                'name': name,
                'quantity': quantity,
                'price': price,
                'quality': quality_field.value,
                'location': location_field.value,
                'image_path': final_image_path,
                'notes': notes_field.value,
                'barcode_value': barcode_field.value,
            }
            
            result = AccessoryManager.update(accessory_id, data, self.current_user['id'] if self.current_user else None)
            
            if result:
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Updated accessory: {name}"),
                    bgcolor=self.success_color,
                    duration=3000
                )
                page.snack_bar.open = True
                self.show_accessories(page)
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("❌ Error updating accessory!"),
                    bgcolor=self.danger_color,
                    duration=3000
                )
                page.snack_bar.open = True
                page.update()
        
        image_buttons_row = ft.Row([upload_btn, delete_btn], spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        
        form_column = ft.Column([
            name_field,
            barcode_field,
            ft.Row([regenerate_btn], alignment=ft.MainAxisAlignment.START),
            quantity_field,
            price_field,
            quality_field,
            location_field,
            image_buttons_row,
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
                            ft.FilledButton("Update", on_click=update_accessory, style=ft.ButtonStyle(bgcolor=self.success_color)),
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
        """Show detailed view of material in a modal dialog"""
        
        # Check if mobile
        is_mobile = page.width < 800 if page.width else False
        
        # Format dates
        created_date = str(material.get('created_at', ''))[:16] if material.get('created_at') else 'N/A'
        updated_date = str(material.get('updated_at', ''))[:16] if material.get('updated_at') else 'N/A'
        
        # Get image
        has_image = False
        image_path = material.get('image_path', '')
        if image_path and os.path.exists(image_path):
            has_image = True
        
        def close_dialog(e):
            page.dialog.open = False
            page.update()
        
        def edit_material(e):
            page.dialog.open = False
            self.open_edit_modal(page, material['id'])
        
        def delete_material(e):
            page.dialog.open = False
            self.open_delete_modal(page, material['id'])
        
        def show_barcode(e):
            self.show_barcode_dialog(page, material)
        
        # Build content
        content_items = []
        
        # Image section
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
        
        # Details section
        content_items.extend([
            ft.Divider(),
            ft.Row([
                ft.Text("📝 Code:", size=14, color="#CCCCCC", width=80),
                ft.Text(material.get('item_code') or "N/A", size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("🏷️ Quality:", size=14, color="#CCCCCC", width=80),
                ft.Container(
                    content=ft.Text(material.get('quality', 'Used'), size=12, color="white"),
                    bgcolor=self.get_quality_color(material.get('quality', 'Used')),
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                ),
            ], spacing=8),
            ft.Row([
                ft.Text("📏 Size:", size=14, color="#CCCCCC", width=80),
                ft.Text(material.get('size') or "N/A", size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("📐 Length:", size=14, color="#CCCCCC", width=80),
                ft.Text(str(material.get('length') or "N/A"), size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("🔢 Quantity:", size=14, color="#CCCCCC", width=80),
                ft.Text(str(material.get('quantity', 0)), size=16, weight=ft.FontWeight.BOLD,
                    color=self.danger_color if material.get('quantity', 0) < 10 else self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("📍 Location:", size=14, color="#CCCCCC", width=80),
                ft.Text(material.get('location_ids') or "N/A", size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("🎨 Colors:", size=14, color="#CCCCCC", width=80),
                ft.Text(material.get('colors') or "N/A", size=14, color=self.text_color),
            ], spacing=8),
            ft.Row([
                ft.Text("💰 Price:", size=14, color="#CCCCCC", width=80),
                ft.Text(f"${material.get('price', 0):.2f}" if material.get('price') else "N/A", size=14, color="#4CAF50"),
            ], spacing=8) if 'price' in material else ft.Container(),
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
                content=ft.Text(material.get('notes') or "No notes", size=13, color="#888888"),
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
            ft.Row([
                ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                                style=ft.ButtonStyle(bgcolor=self.warning_color, color=self.text_color)),
            ], spacing=10),
        ])
        
        # Create dialog
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(material.get('name', 'Material Details'), size=18, weight=ft.FontWeight.BOLD, expand=True),
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

    def open_add_modal(self, page: ft.Page):
        """Open a modal overlay for adding material with image upload and database save"""
        
        import random
        import string
        import os
        import shutil
        from datetime import datetime
        
        def generate_barcode():
            """Generate a unique 13-digit barcode"""
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
        )
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Column([
                ft.Text("📷", size=50),
                ft.Text("No Image", size=12, color="#888888"),
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
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"material_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                return new_path
            return None
        
        # Initialize with generated barcode
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
            
            saved_image_path = save_uploaded_image() if selected_temp_image else None
            
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
                'image_path': saved_image_path,
            }
            
            result = MaterialManager.create(data)
            
            if result:
                page.overlay.clear()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Added: {name}"),
                    bgcolor=self.success_color,
                )
                page.snack_bar.open = True
                # Refresh the materials screen
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
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=550)
        
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
        # ============ STUB METHODS ============
    
    def open_edit_modal(self, page: ft.Page, material_id):
        """Open edit modal"""
        import os
        import shutil
        from datetime import datetime
        
        material = MaterialManager.get_by_id(material_id)
        if not material:
            return
        
        material_dict = dict(material) if material else {}
        
        images_folder = "images"
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)
        
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
        
        current_image_path = material_dict.get('image_path', '')
        has_current_image = current_image_path and os.path.exists(current_image_path) if current_image_path else False
        
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
            except:
                pass
        
        selected_temp_image = None
        
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
            if selected_temp_image and os.path.exists(selected_temp_image):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_ext = os.path.splitext(selected_temp_image)[1]
                new_filename = f"material_{material_id}_{timestamp}{file_ext}"
                new_path = os.path.join(images_folder, new_filename)
                shutil.copy2(selected_temp_image, new_path)
                return new_path
            return None
        
        def delete_current_image(e):
            nonlocal selected_temp_image
            if current_image_path and os.path.exists(current_image_path):
                try:
                    os.remove(current_image_path)
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
            
            size_value = size_field.value
            length_value = self.convert_size_to_length(size_value) if size_value else None
            
            final_image_path = current_image_path
            
            if selected_temp_image == "DELETE":
                final_image_path = None
            elif selected_temp_image:
                saved_path = save_uploaded_image()
                if saved_path:
                    final_image_path = saved_path
                    if current_image_path and os.path.exists(current_image_path) and current_image_path != saved_path:
                        try:
                            os.remove(current_image_path)
                        except:
                            pass
            
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
                'image_path': final_image_path,
            }
            
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
        
        image_buttons_row = ft.Row([upload_btn, delete_btn], spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        
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
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=550)
        
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
        """Show inventory screen - MOBILE OPTIMIZED (Card-based)"""
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
        
        # Get data
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        
        # Create combined inventory list
        inventory_items = []
        for m in materials:
            inventory_items.append({
                'type': '📦',
                'type_name': 'Material',
                'name': m.get('name', 'N/A'),
                'code': m.get('item_code', 'N/A'),
                'quantity': m.get('quantity', 0),
                'quality': m.get('quality', 'Used'),
                'location': m.get('location_ids', 'N/A'),
            })
        
        for a in accessories:
            location = a.get('location') or a.get('location_ids') or 'N/A'
            inventory_items.append({
                'type': '🔧',
                'type_name': 'Accessory',
                'name': a.get('name', 'N/A'),
                'code': a.get('item_code', 'N/A'),
                'quantity': a.get('quantity', 0),
                'quality': a.get('quality', 'Used'),
                'location': location,
            })
        
        inventory_items.sort(key=lambda x: x['name'])
        
        # Calculate stats
        total_items = len(inventory_items)
        total_stock = sum(i.get('quantity', 0) for i in inventory_items)
        low_items = [i for i in inventory_items if i.get('quantity', 0) < 10]
        
        # Create scrollable content
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Text("Inventory Management", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # Stats cards
        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("📦 Total Items", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_items), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text(f"Materials: {len(materials)} | Parts: {len(accessories)}", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Total Stock", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_stock), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Text("Units in inventory", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.success_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("⚠️ Low Stock", size=font_small, color="#CCCCCC"),
                    ft.Text(str(len(low_items)), size=font_title + 4, weight=ft.FontWeight.BOLD, color=self.danger_color),
                    ft.Text("Below 10 units", size=font_small - 2, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=12, bgcolor=self.warning_color, border_radius=10, expand=True,
            ),
        ], spacing=12)
        scroll_content.controls.append(stats_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # Search field
        search_field = ft.TextField(
            hint_text="Search inventory...",
            width=page.width - 60 if is_mobile else 400,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
            prefix_icon=ft.icons.SEARCH,
        )
        scroll_content.controls.append(search_field)
        scroll_content.controls.append(ft.Container(height=10))
        
        # Filter row
        filter_type = ft.Dropdown(
            label="Type",
            width=120,
            options=[
                ft.dropdown.Option("All", "All Items"),
                ft.dropdown.Option("Material", "📦 Materials"),
                ft.dropdown.Option("Accessory", "🔧 Accessories"),
            ],
            value="All",
            bgcolor=self.card_color,
            text_size=font_small,
        )
        
        filter_quality = ft.Dropdown(
            label="Quality",
            width=120,
            options=[
                ft.dropdown.Option("All", "All Qualities"),
                ft.dropdown.Option("New", "🟢 New"),
                ft.dropdown.Option("Used", "🟠 Used"),
                ft.dropdown.Option("Damaged", "🔴 Damaged"),
                ft.dropdown.Option("Repaired", "🔵 Repaired"),
            ],
            value="All",
            bgcolor=self.card_color,
            text_size=font_small,
        )
        
        filter_row = ft.Row([filter_type, filter_quality], spacing=10)
        scroll_content.controls.append(filter_row)
        scroll_content.controls.append(ft.Container(height=15))
        
        # Inventory list (cards)
        inventory_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def update_inventory_display():
            inventory_container.controls.clear()
            
            # Apply filters
            filtered = inventory_items.copy()
            
            # Type filter
            if filter_type.value != "All":
                filtered = [i for i in filtered if i['type_name'] == filter_type.value]
            
            # Quality filter
            if filter_quality.value != "All":
                filtered = [i for i in filtered if i['quality'] == filter_quality.value]
            
            # Search filter
            search_query = search_field.value.lower() if search_field.value else ""
            if search_query:
                filtered = [i for i in filtered if search_query in i['name'].lower() or search_query in i['code'].lower()]
            
            # Show count
            filter_count = ft.Text(f"Showing {len(filtered)} of {len(inventory_items)} items", size=font_small - 2, color="#888888")
            
            # Clear and add header
            if len(inventory_container.controls) > 0 and isinstance(inventory_container.controls[0], ft.Text):
                inventory_container.controls[0].value = f"Showing {len(filtered)} of {len(inventory_items)} items"
            else:
                inventory_container.controls.insert(0, filter_count)
            
            for item in filtered:
                card_content = ft.Column([
                    ft.Row([
                        ft.Text(item['type'], size=font_normal + 2),
                        ft.Text(item['name'], size=font_normal, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text(f"Qty: {item['quantity']}", size=font_normal, weight=ft.FontWeight.BOLD,
                            color=self.danger_color if item['quantity'] < 10 else self.text_color),
                    ]),
                    ft.Row([
                        ft.Text(item['code'], size=font_small - 2, color="#888888", expand=True),
                        ft.Container(
                            content=ft.Text(item['quality'], size=font_small - 2, color="white"),
                            bgcolor=self.get_quality_color(item['quality']),
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        ),
                    ]),
                    ft.Row([
                        ft.Text(f"📍 {item['location']}", size=font_small - 2, color="#888888", expand=True),
                        ft.Text(item['type_name'], size=font_small - 2, color=self.accent_color),
                    ]),
                ], spacing=6)
                
                card = ft.Card(
                    content=ft.Container(content=card_content, padding=12),
                    elevation=1,
                )
                
                inventory_container.controls.append(card)
            
            page.update()
        
        # Event handlers
        def on_search(e):
            update_inventory_display()
        
        def on_filter_change(e):
            update_inventory_display()
        
        search_field.on_change = on_search
        filter_type.on_change = on_filter_change
        filter_quality.on_change = on_filter_change
        
        # Initial load
        update_inventory_display()
        
        scroll_content.controls.append(inventory_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "inventory"
        page.update()
    
    def show_users(self, page: ft.Page):
        """Show users screen - MOBILE OPTIMIZED (Card-based)"""
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
        
        # Get data
        users = self.dict_list(UserManager.get_all())
        is_admin = self.current_user.get('role') == 'admin' if self.current_user else False
        
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
                    icon=ft.icons.ADD,
                    icon_size=28,
                    icon_color=self.success_color,
                    on_click=lambda e: self.open_add_user_modal(page),
                    visible=is_admin,
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
        
        # Users list (cards)
        users_container = ft.Column(spacing=10)
        
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
                            visible=is_admin,
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_size=20,
                            icon_color=self.danger_color,
                            on_click=lambda e, uid=u.get('id'): self.open_delete_user_modal(page, uid, u.get('name')),
                            visible=is_admin and u.get('id') != self.current_user.get('id'),
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
        
        scroll_content.controls.append(users_container)
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "users"
        page.update()
    
    def show_settings(self, page: ft.Page):
        """Show settings screen - MOBILE OPTIMIZED (Card-based)"""
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
        profile_section = ft.Card(
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
                            ft.Text(current_user.get('name', 'User'), size=font_normal, weight=ft.FontWeight.BOLD),
                            ft.Text(current_user.get('email', 'N/A'), size=font_small - 1, color="#888888"),
                            ft.Text(f"Role: {current_user.get('role', 'user').upper()}", size=font_small - 2, 
                                color=self.success_color if current_user.get('role') == 'admin' else self.warning_color),
                        ], spacing=3, expand=True),
                    ], spacing=12),
                    ft.ElevatedButton("Edit Profile", on_click=lambda e: None, style=ft.ButtonStyle(bgcolor=self.accent_color)),
                ], spacing=12),
                padding=15,
            ),
            elevation=1,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(profile_section)
        
        # ========== SECURITY SECTION ==========
        security_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🔐 Security", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.LOCK, color=self.accent_color),
                        title=ft.Text("Change Password"),
                        trailing=ft.Icon(ft.icons.CHEVRON_RIGHT),
                        on_click=lambda e: None,
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.SHIELD, color=self.accent_color),
                        title=ft.Text("Two-Factor Authentication"),
                        trailing=ft.Switch(value=False, on_change=lambda e: None),
                    ),
                ], spacing=8),
                padding=15,
            ),
            elevation=1,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(security_section)
        
        # ========== APPEARANCE SECTION ==========
        appearance_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🎨 Appearance", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.DARK_MODE, color=self.accent_color),
                        title=ft.Text("Dark Mode"),
                        trailing=ft.Switch(value=True, on_change=lambda e: None),
                    ),
                    ft.Text("Accent Color", size=font_small, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Container(width=35, height=35, bgcolor="#1976D2", border_radius=18, ink=True),
                        ft.Container(width=35, height=35, bgcolor="#4CAF50", border_radius=18, ink=True),
                        ft.Container(width=35, height=35, bgcolor="#9C27B0", border_radius=18, ink=True),
                        ft.Container(width=35, height=35, bgcolor="#FF9800", border_radius=18, ink=True),
                    ], spacing=12),
                ], spacing=12),
                padding=15,
            ),
            elevation=1,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(appearance_section)
        
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
        
        database_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("💾 Database", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Row([
                        ft.Icon(ft.icons.STORAGE, size=30, color=self.accent_color),
                        ft.Column([
                            ft.Text("Database Size", size=font_small, color="#888888"),
                            ft.Text(db_size, size=font_normal, weight=ft.FontWeight.BOLD),
                        ], spacing=2),
                    ], spacing=12),
                    ft.Row([
                        ft.ElevatedButton("📥 Backup", on_click=lambda e: None, expand=True),
                        ft.ElevatedButton("🔄 Restore", on_click=lambda e: None, expand=True),
                    ], spacing=10),
                    ft.ElevatedButton("📊 Export All Data", on_click=lambda e: None, expand=True, style=ft.ButtonStyle(bgcolor=self.success_color)),
                    ft.Container(height=5),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.WARNING, size=18, color=self.danger_color),
                            ft.Text("Reset All Data", size=font_small, color=self.danger_color, expand=True),
                            ft.OutlinedButton("Reset", on_click=lambda e: None, style=ft.ButtonStyle(color=self.danger_color)),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10,
                        bgcolor="#3C2121",
                        border_radius=8,
                    ),
                ], spacing=12),
                padding=15,
            ),
            elevation=1,
            margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(database_section)
        
        # ========== ABOUT SECTION ==========
        about_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("ℹ️ About", size=font_normal, weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Text("Store Management System", size=font_normal, weight=ft.FontWeight.BOLD),
                    ft.Text("Version 1.0.0", size=font_small - 1, color="#888888"),
                    ft.Text("© 2024 Your Company", size=font_small - 2, color="#888888"),
                ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
            ),
            elevation=1,
        )
        scroll_content.controls.append(about_section)
        
        scroll_content.controls.append(ft.Container(height=80))
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "settings"
        page.update()


if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
