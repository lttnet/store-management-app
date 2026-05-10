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
            # Filter by quality
            if self.current_material_filter == "All":
                filtered = materials
            else:
                filtered = [m for m in materials if m.get('quality') == self.current_material_filter]
            
            # Filter by search
            if hasattr(self, 'material_search_query') and self.material_search_query:
                query = self.material_search_query.lower()
                filtered = [m for m in filtered if query in m.get('name', '').lower() or query in m.get('item_code', '').lower()]
            
            self.material_cards_container.controls.clear()
            
            for m in filtered:
                self.material_cards_container.controls.append(
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
                                ft.Row([
                                    ft.IconButton(icon=ft.icons.EDIT, icon_size=20, 
                                                on_click=lambda e, mat=m: self.open_edit_modal(page, mat['id']),
                                                tooltip="Edit"),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                                on_click=lambda e, mat=m: self.open_delete_modal(page, mat['id']),
                                                tooltip="Delete"),
                                    ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                                on_click=lambda e, mat=m: self.show_barcode_dialog(page, mat),
                                                tooltip="Barcode"),
                                ], spacing=0),
                            ]),
                            padding=12,
                        ),
                        elevation=2,
                        margin=ft.margin.only(bottom=8),
                    )
                )
            
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
            # Filter by quality
            if self.current_accessory_filter == "All":
                filtered = accessories
            else:
                filtered = [a for a in accessories if a.get('quality') == self.current_accessory_filter]
            
            # Filter by search
            if hasattr(self, 'accessory_search_query') and self.accessory_search_query:
                query = self.accessory_search_query.lower()
                filtered = [a for a in filtered if query in a.get('name', '').lower() or query in a.get('item_code', '').lower()]
            
            self.accessory_cards_container.controls.clear()
            
            for a in filtered:
                location = a.get('location') or a.get('location_ids') or 'N/A'
                price = a.get('price', 0)
                price_text = f"${price:.2f}" if price else ""
                
                self.accessory_cards_container.controls.append(
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
                                ft.Row([
                                    ft.Text(price_text, size=font_small, color="#4CAF50") if price_text else ft.Container(),
                                    ft.Container(expand=True),
                                    ft.IconButton(icon=ft.icons.EDIT, icon_size=20, 
                                                on_click=lambda e, acc=a: self.open_edit_accessory_modal(page, acc['id']),
                                                tooltip="Edit"),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                                on_click=lambda e, acc=a: self.open_delete_accessory_modal(page, acc['id']),
                                                tooltip="Delete"),
                                    ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                                on_click=lambda e, acc=a: self.show_barcode_dialog(page, acc),
                                                tooltip="Barcode"),
                                ], spacing=0),
                            ]),
                            padding=12,
                        ),
                        elevation=2,
                        margin=ft.margin.only(bottom=8),
                    )
                )
            
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
        """Show barcode dialog for material or accessory with real barcode image"""
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
        """Open modal for adding accessory with barcode generation"""
        
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
        
        # Initialize with a generated barcode
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
        
        # Form layout
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
        ], spacing=12, scroll=ft.ScrollMode.AUTO, height=600)
        
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
                    width=520,
                ),
            ),
            expand=True,
            bgcolor="#80000000",
        )
        
        page.overlay.append(modal)
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

    def open_add_modal(self, page: ft.Page):
        """Open a modal overlay for adding material with barcode generation"""
        
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
        
        # Initialize with a generated barcode
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
                    ft.Text(f"✓ Added: {name} | Barcode: {barcode_value}"),
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
        # ============ STUB METHODS ============
    def show_barcode_scanner(self, page: ft.Page):
        """Show barcode scanner - MOBILE OPTIMIZED"""
        page.controls.clear()
        
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
        
        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Header
        scroll_content.controls.append(
            ft.Text("📷 Barcode Scanner", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color)
        )
        scroll_content.controls.append(ft.Container(height=15))
        
        # Barcode input card
        barcode_input = ft.TextField(
            hint_text="Enter barcode number",
            width=page.width - 60 if is_mobile_device else 400,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_align=ft.TextAlign.CENTER,
            text_size=font_normal,
        )
        
        result_text = ft.Text("", size=font_normal, color="#888888")
        
        def scan_barcode(e):
            barcode = barcode_input.value.strip()
            if not barcode:
                return
            
            result_text.value = f"🔍 Searching for: {barcode}"
            result_text.color = self.warning_color
            page.update()
            
            # Search in accessories
            item = AccessoryManager.get_by_barcode(barcode)
            if not item:
                item = MaterialManager.get_by_barcode(barcode)
            
            if item:
                self.show_barcode_dialog(page, dict(item))
                result_text.value = "✅ Item found!"
                result_text.color = self.success_color
                barcode_input.value = ""
            else:
                result_text.value = f"❌ No item found with barcode: {barcode}"
                result_text.color = self.danger_color
            
            page.update()
        
        barcode_input.on_submit = scan_barcode
        
        scroll_content.controls.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Enter Barcode", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        barcode_input,
                        ft.Container(height=10),
                        ft.ElevatedButton("🔍 Scan", on_click=scan_barcode, width=200),
                        ft.Container(height=10),
                        result_text,
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    padding=20,
                ),
                elevation=2,
            )
        )
        
        scroll_content.controls.append(ft.Container(height=20))
        
        # Info card
        scroll_content.controls.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("💡 Tips", size=font_normal, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        ft.Text("• Enter a 13-digit barcode number", size=font_small, color="#888888"),
                        ft.Text("• Barcodes are auto-generated when adding items", size=font_small, color="#888888"),
                        ft.Text("• Click the barcode icon on any item to view/print", size=font_small, color="#888888"),
                    ], spacing=8),
                    padding=15,
                ),
                elevation=1,
            )
        )
        
        main_container = ft.Container(content=scroll_content, expand=True, padding=padding_size)
        
        # Layout
        if is_mobile_device and nav:
            page.add(ft.Column([main_container, nav], spacing=0, expand=True))
        else:
            page.add(ft.Row([sidebar, main_container], spacing=0, expand=True))
        
        self.current_view = "barcode_scanner"
        page.update()
    
    def show_inventory(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Inventory - Coming Soon", size=30)], expand=True))
        page.update()
    
    def show_users(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Users - Coming Soon", size=30)], expand=True))
        page.update()
    
    def show_settings(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Settings - Coming Soon", size=30)], expand=True))
        page.update()


if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
