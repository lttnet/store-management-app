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
        try:
            self.page_ref = page
            
            page.title = "Store Management System"
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = self.bg_color
            page.padding = 0
            page.spacing = 0
            page.window_width = 1600
            page.window_height = 900
            page.window_min_width = 1200
            page.window_min_height = 700
            
            def on_keyboard(e):
                if e.ctrl:
                    if e.key == "+" or e.key == "=":
                        self.zoom_in(page)
                    elif e.key == "-":
                        self.zoom_out(page)
                    elif e.key == "0":
                        self.reset_zoom(page)
            page.on_keyboard_event = on_keyboard
            
            init_database()
            self.show_login(page)
            page.update()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
    
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
        
        zoom_percent = ft.Text(f"{int(self.zoom_level * 100)}%", size=12, color=self.text_color)
        
        zoom_section = ft.Column([
            ft.Divider(),
            ft.Text("🔍 Zoom", size=11, color="#888888", text_align=ft.TextAlign.CENTER),
            ft.Row([
                ft.IconButton(icon=ft.icons.ZOOM_OUT, icon_size=20, on_click=lambda e: self.zoom_out(page)),
                zoom_percent,
                ft.IconButton(icon=ft.icons.ZOOM_IN, icon_size=20, on_click=lambda e: self.zoom_in(page)),
                ft.IconButton(icon=ft.icons.ASPECT_RATIO, icon_size=20, on_click=lambda e: self.reset_zoom(page)),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
        ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        logo_exists = os.path.exists(logo_path)
        sidebar_logo = ft.Image(src=logo_path, width=30, height=30, fit=ft.ImageFit.CONTAIN) if logo_exists else ft.Text("🏪", size=24)
        
        title_content = ft.Row([sidebar_logo, ft.Text("Store Manager", size=18, weight=ft.FontWeight.BOLD, color=self.text_color)], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
        
        role = self.current_user.get('role', 'guest') if self.current_user else 'guest'
        role_display = role.upper()
        
        return ft.Container(
            content=ft.Column([
                ft.Container(content=title_content, padding=20),
                ft.Divider(),
                ft.Column(nav_buttons, spacing=5),
                ft.Container(expand=True),
                zoom_section,
                ft.Divider(),
                logout_btn,
                ft.Container(content=ft.Column([ft.Text(f"User: {self.current_user.get('name', 'User') if self.current_user else 'Guest'}", size=10, color="#888888"), ft.Text(role_display, size=10, color=self.text_color)], spacing=3, horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=10),
            ], spacing=0),
            width=250,
            bgcolor=self.sidebar_color,
        )
    
        # ============ DASHBOARD ============
    def show_dashboard(self, page: ft.Page):
        page.controls.clear()
        
        materials = self.dict_list(MaterialManager.get_all())
        accessories = self.dict_list(AccessoryManager.get_all())
        stats = MaterialManager.get_stats()
        accessory_stats = AccessoryManager.get_stats()
        low_stock = self.dict_list(MaterialManager.get_low_stock(10))
        
        # Add these lines - they were missing!
        low_stock_materials = [m for m in materials if m.get('quantity', 0) < 10]
        low_stock_accessories = [a for a in accessories if a.get('quantity', 0) < 10]
        
        sidebar = self.create_sidebar(page)
        
        # Stats cards row
        stats_row = ft.Row([
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
        ], spacing=15, expand=True)
        
        # Materials Table Panel
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
                ], alignment=ft.MainAxisAlignment.START)
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
        
        # Accessories Table Panel
        accessories_rows = []
        for a in accessories[:10]:
            accessories_rows.append(
                ft.Row([
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
                ], alignment=ft.MainAxisAlignment.START)
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
        
        # Low Stock Panel - Now using the defined variables
        low_stock_items = []
        for m in low_stock_materials[:10]:
            low_stock_items.append(
                ft.Row([
                    ft.Text("📦", size=14, width=35),
                    ft.Text(m.get('name', 'Unknown')[:20], size=12),
                    ft.Text(f"Stock: {m.get('quantity', 0)}", size=12, color=self.danger_color),
                ], alignment=ft.MainAxisAlignment.START)
            )
        for a in low_stock_accessories[:10]:
            low_stock_items.append(
                ft.Row([
                    ft.Text("🔧", size=14, width=35),
                    ft.Text(a.get('name', 'Unknown')[:20], size=12),
                    ft.Text(f"Stock: {a.get('quantity', 0)}", size=12, color=self.danger_color),
                ], alignment=ft.MainAxisAlignment.START)
            )
        
        if not low_stock_items:
            low_stock_items.append(ft.Text("No low stock items", size=12, color="#888888"))
        
        low_stock_panel = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("⚠️ Low Stock Items", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                    ft.Container(expand=True),
                    ft.Text(f"Total: {len(low_stock_materials) + len(low_stock_accessories)} items", size=11, color="#888888"),
                ]),
                ft.Divider(),
                ft.Column(low_stock_items, spacing=5, scroll=ft.ScrollMode.AUTO),
            ], spacing=8),
            padding=12,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Import/Export Panel
        import_panel = ft.Container(
            content=ft.Column([
                ft.Text("📁 Import/Export", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("Import", on_click=lambda e: None),
                    ft.ElevatedButton("Export", on_click=lambda e: None),
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                ft.Text("CSV format", size=10, color="#888888"),
            ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor=self.card_color,
            border_radius=10,
            expand=True,
        )
        
        # Users Panel
        users = self.dict_list(UserManager.get_all())
        users_panel = ft.Container(
            content=ft.Column([
                ft.Text("👥 Users", size=16, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Divider(),
            ] + [
                ft.Row([
                    ft.Text(u.get('name', 'N/A'), size=12, width=100),
                    ft.Text(u.get('role', 'user'), size=11, color="#4CAF50"),
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
            content=ft.Column([
                ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(height=15),
                stats_row,
                ft.Container(height=15),
                middle_row,
                ft.Container(height=15),
                bottom_row,
            ], spacing=5, expand=True),
            expand=True,
            padding=20,
        )
        
        layout = ft.Row([sidebar, main_content], spacing=0, expand=True)
        
        if self.zoom_level != 1.0:
            page.add(ft.Container(content=layout, scale=ft.Scale(self.zoom_level), expand=True, alignment=ft.alignment.center))
        else:
            page.add(layout)
        
        page.update()
    
    def show_materials_screen(self, page: ft.Page):
        """Show materials screen with working filters and clickable rows"""
        page.controls.clear()
        
        self.page_ref = page
        materials = self.dict_list(MaterialManager.get_all())
        sidebar = self.create_sidebar(page)
        
        # Initialize current filter if not exists
        if not hasattr(self, 'current_material_filter'):
            self.current_material_filter = "All"
        
        # Simple fixed sizes (no scale_helper needed)
        padding_size = 20
        font_title = 24
        font_small = 14
        
        # ========== SEARCH FIELD ==========
        search_field = ft.TextField(
            hint_text="Search materials...",
            width=220,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
            on_change=lambda e: self.filter_materials_table(page),
        )
        self.material_search_query = ""
        
        # ========== FILTER BUTTONS ==========
        self.material_filter_buttons = {}
        
        def create_filter_button(label, active_color, filter_type):
            is_active = (self.current_material_filter == filter_type)
            btn = ft.Container(
                content=ft.Text(label, size=font_small, weight=ft.FontWeight.BOLD, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=18, vertical=10),
                bgcolor=active_color if is_active else self.card_color,
                border_radius=25,
                ink=True,
                on_click=lambda e, f=filter_type: self.filter_materials_by_quality(page, f),
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
            spacing=10,
            wrap=True,
        )
        
        # ========== ADD BUTTON ==========
        add_button = ft.FilledButton(
            "➕ Add Material",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color, padding=12),
            on_click=lambda e: self.open_add_modal(page),
        )
        
        # ========== TABLE HEADER ==========
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Name", size=font_small, weight=ft.FontWeight.BOLD, width=180),
                ft.Text("Location", size=font_small, weight=ft.FontWeight.BOLD, width=120),
                ft.Text("Qty", size=font_small, weight=ft.FontWeight.BOLD, width=60),
                ft.Text("Quality", size=font_small, weight=ft.FontWeight.BOLD, width=90),
                ft.Text("Actions", size=font_small, weight=ft.FontWeight.BOLD, width=120),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=12, horizontal=12),
            bgcolor="#3C3C3C",
            border_radius=8,
        )
        
        # ========== TABLE ROWS CONTAINER ==========
        self.material_table_rows = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=450)
        
        # Function to update table based on filter and search
        def update_material_table():
            # Filter by quality
            if self.current_material_filter == "All":
                filtered = materials
            else:
                filtered = [m for m in materials if m.get('quality') == self.current_material_filter]
            
            # Filter by search query
            if hasattr(self, 'material_search_query') and self.material_search_query:
                query = self.material_search_query.lower()
                filtered = [m for m in filtered if query in m.get('name', '').lower() or query in m.get('item_code', '').lower()]
            
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
                                        on_click=lambda e, mat=m: self.open_edit_modal(page, mat['id']),
                                        tooltip="Edit"),
                            ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                        on_click=lambda e, mat=m: self.open_delete_modal(page, mat['id']),
                                        tooltip="Delete"),
                            ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                        on_click=lambda e, mat=m: self.show_barcode_dialog(page, mat),
                                        tooltip="Barcode"),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=10, horizontal=12),
                    bgcolor="#2C2C2C",
                    border_radius=6,
                    ink=True,
                    on_click=lambda e, mat=m: self.on_material_select(mat),
                )
                self.material_table_rows.controls.append(row)
            
            # Update detail panel if selected material is not in filtered list
            if self.selected_material_detail and self.selected_material_detail not in filtered:
                self.selected_material_detail = None
                if hasattr(self, 'material_detail_panel'):
                    self.material_detail_panel.content = self.create_detail_panel(None, page)
            
            page.update()
        
        # Store search handler
        def on_search(e):
            self.material_search_query = e.control.value
            update_material_table()
        
        search_field.on_change = on_search
        
        # Initial table population
        update_material_table()
        
        # Left Panel - Table
        left_panel = ft.Container(
            content=ft.Column([header_row, self.material_table_rows], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=12,
            padding=5,
        )
        
        # ========== DETAIL PANEL ==========
        self.material_detail_panel = ft.Container(
            content=self.create_detail_panel(self.selected_material_detail, page),
            width=350,
            bgcolor=self.card_color,
            border_radius=12,
            padding=15,
            height=500,
        )
        
        # ========== MAIN CONTENT ==========
        content = ft.Column([
            ft.Row([
                ft.Text("Materials", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.Row([ft.Icon(ft.icons.SEARCH, size=22), search_field], spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=12),
            ft.Row([filter_row], alignment=ft.MainAxisAlignment.START),
            ft.Container(height=12),
            ft.Row([add_button], alignment=ft.MainAxisAlignment.END),
            ft.Container(height=15),
            ft.Row([left_panel, ft.Container(width=15), self.material_detail_panel], expand=True),
        ], expand=True)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # Layout with zoom
        layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        
        if self.zoom_level != 1.0:
            zoomed = ft.Container(content=layout, scale=ft.Scale(self.zoom_level), expand=True, alignment=ft.alignment.center)
            page.add(zoomed)
        else:
            page.add(layout)
        
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
        """Show accessories screen with working filters and clickable rows"""
        page.controls.clear()
        
        self.page_ref = page
        accessories = self.dict_list(AccessoryManager.get_all())
        sidebar = self.create_sidebar(page)
        
        # Initialize current filter if not exists
        if not hasattr(self, 'current_accessory_filter'):
            self.current_accessory_filter = "All"
        
        # Simple fixed sizes
        padding_size = 20
        font_title = 24
        font_small = 14
        
        # ========== SEARCH FIELD ==========
        search_field = ft.TextField(
            hint_text="Search accessories...",
            width=220,
            bgcolor=self.card_color,
            border_color=self.accent_color,
            text_size=font_small,
            on_change=lambda e: self.filter_accessories_table(page),
        )
        self.accessory_search_query = ""
        
        # ========== FILTER BUTTONS ==========
        self.accessory_filter_buttons = {}
        
        def create_filter_button(label, active_color, filter_type):
            is_active = (self.current_accessory_filter == filter_type)
            btn = ft.Container(
                content=ft.Text(label, size=font_small, weight=ft.FontWeight.BOLD, color=self.text_color),
                padding=ft.padding.symmetric(horizontal=18, vertical=10),
                bgcolor=active_color if is_active else self.card_color,
                border_radius=25,
                ink=True,
                on_click=lambda e, f=filter_type: self.filter_accessories_by_quality(page, f),
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
            spacing=10,
            wrap=True,
        )
        
        # ========== ADD BUTTON ==========
        add_button = ft.FilledButton(
            "➕ Add Accessory",
            style=ft.ButtonStyle(bgcolor=self.success_color, color=self.text_color, padding=12),
            on_click=lambda e: self.open_add_accessory_modal(page),
        )
        
        # ========== TABLE HEADER ==========
        header_row = ft.Container(
            content=ft.Row([
                ft.Text("Name", size=font_small, weight=ft.FontWeight.BOLD, width=180),
                ft.Text("Code", size=font_small, weight=ft.FontWeight.BOLD, width=120),
                ft.Text("Qty", size=font_small, weight=ft.FontWeight.BOLD, width=60),
                ft.Text("Quality", size=font_small, weight=ft.FontWeight.BOLD, width=90),
                ft.Text("Location", size=font_small, weight=ft.FontWeight.BOLD, width=120),
                ft.Text("Actions", size=font_small, weight=ft.FontWeight.BOLD, width=120),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.padding.symmetric(vertical=12, horizontal=12),
            bgcolor="#3C3C3C",
            border_radius=8,
        )
        
        # ========== TABLE ROWS CONTAINER ==========
        self.accessory_table_rows = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=450)
        
        # Function to update table based on filter and search
        def update_accessory_table():
            # Filter by quality
            if self.current_accessory_filter == "All":
                filtered = accessories
            else:
                filtered = [a for a in accessories if a.get('quality') == self.current_accessory_filter]
            
            # Filter by search query
            if hasattr(self, 'accessory_search_query') and self.accessory_search_query:
                query = self.accessory_search_query.lower()
                filtered = [a for a in filtered if query in a.get('name', '').lower() or query in a.get('item_code', '').lower()]
            
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
                                        on_click=lambda e, acc=a: self.open_edit_accessory_modal(page, acc['id']),
                                        tooltip="Edit"),
                            ft.IconButton(icon=ft.icons.DELETE, icon_size=20,
                                        on_click=lambda e, acc=a: self.open_delete_accessory_modal(page, acc['id']),
                                        tooltip="Delete"),
                            ft.IconButton(icon=ft.icons.QR_CODE, icon_size=20,
                                        on_click=lambda e, acc=a: self.show_barcode_dialog(page, acc),
                                        tooltip="Barcode"),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=10, horizontal=12),
                    bgcolor="#2C2C2C",
                    border_radius=6,
                    ink=True,
                    on_click=lambda e, acc=a: self.on_accessory_select(acc),
                )
                self.accessory_table_rows.controls.append(row)
            
            # Update detail panel if selected accessory is not in filtered list
            if self.selected_accessory_detail and self.selected_accessory_detail not in filtered:
                self.selected_accessory_detail = None
                if hasattr(self, 'accessory_detail_panel'):
                    self.accessory_detail_panel.content = self.create_accessory_detail_panel(None, page)
            
            page.update()
        
        # Store search handler
        def on_search(e):
            self.accessory_search_query = e.control.value
            update_accessory_table()
        
        search_field.on_change = on_search
        
        # Initial table population
        update_accessory_table()
        
        # Left Panel - Table
        left_panel = ft.Container(
            content=ft.Column([header_row, self.accessory_table_rows], spacing=0),
            expand=True,
            bgcolor=self.card_color,
            border_radius=12,
            padding=5,
        )
        
        # ========== DETAIL PANEL ==========
        self.accessory_detail_panel = ft.Container(
            content=self.create_accessory_detail_panel(self.selected_accessory_detail, page),
            width=350,
            bgcolor=self.card_color,
            border_radius=12,
            padding=15,
            height=500,
        )
        
        # ========== MAIN CONTENT ==========
        content = ft.Column([
            ft.Row([
                ft.Text("Accessories & Parts", size=font_title, weight=ft.FontWeight.BOLD, color=self.text_color),
                ft.Container(expand=True),
                ft.Row([ft.Icon(ft.icons.SEARCH, size=22), search_field], spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=12),
            ft.Row([filter_row], alignment=ft.MainAxisAlignment.START),
            ft.Container(height=12),
            ft.Row([add_button], alignment=ft.MainAxisAlignment.END),
            ft.Container(height=15),
            ft.Row([left_panel, ft.Container(width=15), self.accessory_detail_panel], expand=True),
        ], expand=True)
        
        main_container = ft.Container(content=content, expand=True, padding=padding_size)
        
        # Layout with zoom
        layout = ft.Row([sidebar, main_container], spacing=0, expand=True)
        
        if self.zoom_level != 1.0:
            zoomed = ft.Container(content=layout, scale=ft.Scale(self.zoom_level), expand=True, alignment=ft.alignment.center)
            page.add(zoomed)
        else:
            page.add(layout)
        
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

    # ============ STUB METHODS ============
    def show_barcode_scanner(self, page: ft.Page):
        page.controls.clear()
        sidebar = self.create_sidebar(page)
        page.add(ft.Row([sidebar, ft.Text("Barcode Scanner - Coming Soon", size=30)], expand=True))
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
