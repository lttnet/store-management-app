"""
Store Management App - Free Local Version
All features free. Local SQLite only. No trial, no purchase.
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
try:
    from ads_manager import AdsManager
    ADS_AVAILABLE = True
except ImportError as e:
    ADS_AVAILABLE = False
    print(f"⚠️ ads_manager.py not found: {e}")

from database import init_database
from managers.material_manager import MaterialManager
from managers.accessory_manager import AccessoryManager
from managers.user_manager import UserManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, 'images', 'Logo-store.png')
background_path = os.path.join(BASE_DIR, 'images', 'backgound_storemgt.png')

class StoreApp:
    def __init__(self):
        self.current_user = None
        self.current_view = "dashboard"
        self.page_ref = None
        self.ads = None

        # Free app - always activated
        self.is_activated = True
        self.is_free_version = True

        # Colors
        self.bg_color = "#101010"
        self.sidebar_color = "#1E1E1E"
        self.card_color = "#2C2C2C"
        self.accent_color = "#1976D2"
        self.success_color = "#2E7D32"
        self.warning_color = "#F57C00"
        self.danger_color = "#FF5252"
        self.text_color = "#FFFFFF"

        self.quality_colors = {
            "New": "#2E7D32",
            "Used": "#F57C00",
            "Damaged": "#FF5252",
            "Repaired": "#1976D2",
        }

        self.image_picker = None
        self.current_filtered_items = []

    # ---------- HELPERS ----------

    def dict_list(self, rows):
        if rows is None:
            return []
        result = []
        for row in rows:
            row_dict = {}
            for key in row.keys():
                row_dict[key] = row[key]
            result.append(row_dict)
        return result

    def get_quality_color(self, quality):
        return {
            "New": "#2E7D32",
            "Used": "#F57C00",
            "Damaged": "#FF5252",
            "Repaired": "#1976D2",
        }.get(quality, "#888888")

    def get_quality_icon(self, quality):
        return {
            "New": "🟢",
            "Used": "🟠",
            "Damaged": "🔴",
            "Repaired": "🔵",
        }.get(quality, "⚪")

    # ---------- PERMISSIONS (always full for free app) ----------

    def has_full_access(self):
        return True

    def can_edit_delete(self):
        return True

    def can_manage_users(self):
        return True

    # ---------- FIRST LAUNCH ----------

    def is_first_launch(self):
        settings_file = os.path.join(BASE_DIR, "app_settings.json")
        return not os.path.exists(settings_file)

    def mark_as_launched(self):
        try:
            settings_file = os.path.join(BASE_DIR, "app_settings.json")
            settings = {
                'first_launch': False,
                'launch_date': datetime.now().isoformat(),
            }
            with open(settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Settings save error: {e}")

        # ---------- MAIN ----------

    def main(self, page: ft.Page):
        try:
            self.page_ref = page

            page.title = "Store Management"
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = self.bg_color
                    # ---- Initialize ads ----
            if ADS_AVAILABLE:
                try:
                    self.ads = AdsManager(page)
                except Exception as e:
                    print(f"Ads init error: {e}")
                    self.ads = None
                    
            page.padding = 0
            page.spacing = 0

            try:
                init_database()
                self.ensure_admin_user()
            except Exception as e:
                print(f"DB init error: {e}")

            # First launch -> welcome screen
            if self.is_first_launch():
                self.show_welcome(page)
                return

            # Always logged in as store manager
            self.current_user = {
                'id': 1,
                'name': 'Store Manager',
                'email': 'user@store.com',
                'role': 'admin',
                'activated': True,
            }
            self.show_dashboard(page)
            page.update()
            print("✅ App started - Free version")

        except Exception as e:
            print(f"❌ Startup error: {e}")
            traceback.print_exc()
            try:
                page.controls.clear()
                page.add(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("❌ App Error", size=24, color="red"),
                            ft.Text(str(e), size=14, color="white"),
                            ft.ElevatedButton("Retry", on_click=lambda e: self.main(page)),
                        ], horizontal_alignment=ft.CrossAxisalignment.CENTER, spacing=15),
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                )
                page.update()
            except:
                pass

    def ensure_admin_user(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                conn.close()
                return

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] > 0:
                conn.close()
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

            hashed = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('Administrator', 'admin@store.com', hashed, 'admin', company_id,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()
            print("✅ Created admin user")
        except Exception as e:
            print(f"Error ensuring admin user: {e}")

    # ---------- WELCOME SCREEN ----------

    def show_welcome(self, page: ft.Page):
        page.controls.clear()
        is_mobile = page.width < 800 if page.width else False

        def start_using(e):
            self.mark_as_launched()
            self.current_user = {
                'id': 1,
                'name': 'Store Manager',
                'email': 'user@store.com',
                'role': 'admin',
                'activated': True,
            }
            self.show_dashboard(page)

        logo_exists = os.path.exists(logo_path)
        logo = ft.Image(src=logo_path, width=100, height=100, fit=ft.ImageFit.CONTAIN) \
            if logo_exists else ft.Text("🏪", size=70)

        features = ft.Column([
            ft.Row([ft.Text("📦", size=22), ft.Text("Materials & Accessories", size=13)], spacing=10),
            ft.Row([ft.Text("📷", size=22), ft.Text("Barcode scanning", size=13)], spacing=10),
            ft.Row([ft.Text("📊", size=22), ft.Text("Inventory tracking", size=13)], spacing=10),
            ft.Row([ft.Text("👥", size=22), ft.Text("User management", size=13)], spacing=10),
            ft.Row([ft.Text("💾", size=22), ft.Text("Local backup & restore", size=13)], spacing=10),
        ], spacing=12)

        content = ft.Column([
            ft.Container(height=30),
            logo,
            ft.Container(height=20),
            ft.Text("Store Management", size=26 if is_mobile else 30,
                    weight=ft.FontWeight.BOLD, color=self.text_color,
                    text_align=ft.TextAlign.CENTER),
            ft.Text("Free forever. No signup.", size=13, color="#AAAAAA",
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=30),
            ft.Container(
                content=features,
                padding=20,
                bgcolor=self.card_color,
                border_radius=12,
            ),
            ft.Container(height=20),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color="#4CAF50", size=16),
                    ft.Text("100% Free", size=12, color="#4CAF50"),
                ], spacing=6),
                padding=10,
                bgcolor="#1A3A1A",
                border_radius=8,
            ),
            ft.Container(height=20),
            ft.ElevatedButton(
                "🚀 Get Started",
                on_click=start_using,
                width=250, height=50,
                style=ft.ButtonStyle(bgcolor="#4CAF50", color="white", padding=15),
            ),
            ft.Container(height=10),
            ft.Text("Your data stays on your device", size=10, color="#888888"),
            ft.Container(height=30),
        ], horizontal_alignment=ft.CrossAxisalignment.CENTER,
           spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        page.add(ft.Container(content=content, padding=20, expand=True,
                              alignment=ft.alignment.center))
        self.current_view = "welcome"
        page.update()

        # ---------- SIDEBAR ----------

    def create_sidebar(self, page: ft.Page):
        nav_items = [
            ("📊", "Dashboard", "dashboard"),
            ("📦", "Materials", "materials"),
            ("🔧", "Accessories", "accessories"),
            ("📷", "Barcode Scan", "barcode_scanner"),
            ("📋", "Inventory", "inventory"),
            ("⚙️", "Settings", "settings"),
        ]

        nav_buttons = []

        def navigate(e, view):
            if self.ads:
                self.ads.show_interstitial()
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
            elif view == "settings":
                self.show_settings(page)

        for emoji, label, view in nav_items:
            nav_buttons.append(ft.Container(
                content=ft.Row([
                    ft.Text(emoji, size=22),
                    ft.Text(label, size=15, color=self.text_color)
                ], spacing=12),
                padding=ft.padding.symmetric(horizontal=18, vertical=14),
                border_radius=10, ink=True,
                on_click=lambda e, v=view: navigate(e, v),
            ))

        def logout(e):
            self.confirm_logout(page)

        logout_btn = ft.Container(
            content=ft.Row([
                ft.Text("🚪", size=22),
                ft.Text("Logout", size=15, color="#FF5252")
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=18, vertical=14),
            border_radius=10, ink=True,
            on_click=logout,
        )

        logo_exists = os.path.exists(logo_path)
        sidebar_logo = ft.Image(src=logo_path, width=35, height=35,
                                fit=ft.ImageFit.CONTAIN) \
            if logo_exists else ft.Text("🏪", size=28)

        title = ft.Row(
            [sidebar_logo,
             ft.Text("Store Manager", size=20, weight=ft.FontWeight.BOLD,
                     color=self.text_color)],
            alignment=ft.MainAxisAlignment.CENTER, spacing=8,
        )

        role = (self.current_user or {}).get('role', 'guest')
        free_badge = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color="#4CAF50"),
                ft.Text("✅ Free Version", size=12, color="#4CAF50",
                        weight=ft.FontWeight.BOLD),
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor="#1A3A1A", border_radius=20,
        )

        return ft.Container(
            content=ft.Column([
                ft.Container(content=title, padding=25),
                ft.Divider(),
                ft.Column(nav_buttons, spacing=8),
                ft.Container(expand=True),
                ft.Divider(),
                free_badge,
                ft.Container(height=5),
                logout_btn,
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"User: {(self.current_user or {}).get('name', 'Guest')}",
                                size=12, color="#888888"),
                        ft.Text(role.upper(), size=12, weight=ft.FontWeight.BOLD,
                                color=self.text_color),
                    ], spacing=5,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=15,
                ),
            ], spacing=0),
            width=260,
            bgcolor=self.sidebar_color,
        )

    # ---------- BOTTOM NAV ----------

    def create_bottom_nav(self, page: ft.Page):
        """Bottom nav bar for mobile - no Users, no Logout"""
        nav_items = [
            (ft.Icons.DASHBOARD, "Home", "dashboard"),
            (ft.Icons.INVENTORY, "Materials", "materials"),
            (ft.Icons.BUILD, "Parts", "accessories"),
            (ft.Icons.QR_CODE_SCANNER, "Scan", "barcode_scanner"),
            (ft.Icons.LIST_ALT, "Inventory", "inventory"),
            (ft.Icons.SETTINGS, "Settings", "settings"),
        ]

        def navigate(e):
            if self.ads:
                self.ads.show_interstitial()
            idx = e.control.selected_index
            if idx < len(nav_items):
                view = nav_items[idx][2]
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
                elif view == "settings":
                    self.show_settings(page)

        return ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(icon=icon, label=label)
                for icon, label, _ in nav_items
            ],
            on_change=navigate,
            height=62,
            bgcolor=self.sidebar_color,
        )
    # ---------- LOGOUT ----------

    def confirm_logout(self, page: ft.Page):
        def do_logout(e):
            page.dialog.open = False
            self.current_user = {
                'id': 1, 'name': 'Store Manager',
                'email': 'user@store.com', 'role': 'admin',
                'activated': True,
            }
            self.show_dashboard(page)

        def cancel(e):
            page.dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Logout"),
            content=ft.Container(content=ft.Column([
                ft.Text("Are you sure you want to logout?", size=14),
                ft.Container(height=15),
                ft.Row([
                    ft.TextButton("Cancel", on_click=cancel),
                    ft.FilledButton("Logout", on_click=do_logout,
                                    style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ], alignment=ft.MainAxisalignment.CENTER, spacing=15),
            ], spacing=12), width=350, padding=20),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_dashboard(self, page: ft.Page):
        """Dashboard - mobile friendly with top nav strip on mobile"""
        page.controls.clear()

        screen_w = page.width or 800
        is_mobile = screen_w < 800
        is_narrow = screen_w < 500

        # Load data safely
        try:
            materials = self.dict_list(MaterialManager.get_all())
        except Exception as e:
            print(f"Materials load error: {e}")
            materials = []

        try:
            accessories = self.dict_list(AccessoryManager.get_all())
        except Exception as e:
            print(f"Accessories load error: {e}")
            accessories = []

        total_items = len(materials) + len(accessories)
        total_stock = sum(m.get('quantity', 0) or 0 for m in materials) + \
                      sum(a.get('quantity', 0) or 0 for a in accessories)

        # ============ CONTENT COLUMN ============
        main_column = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # Header
        main_column.controls.append(ft.Row([
            ft.Text(
                "📊 Dashboard",
                size=20 if is_narrow else (24 if is_mobile else 28),
                weight=ft.FontWeight.BOLD,
                color=self.text_color,
            ),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_size=20 if is_mobile else 24,
                icon_color="#888888",
                on_click=lambda e: self.show_dashboard(page),
            ),
        ]))
        main_column.controls.append(ft.Divider(height=1, color="#3C3C3C"))

        # ============ STATS ============
        if is_mobile:
            main_column.controls.append(ft.Row([
                self._create_stat_card("📦", str(total_items), "Items"),
                self._create_stat_card("📊", str(total_stock), "Stock"),
            ], spacing=8))
            main_column.controls.append(ft.Row([
                self._create_stat_card("📈", str(len(materials)), "Materials"),
                self._create_stat_card("🔧", str(len(accessories)), "Accessories"),
            ], spacing=8))
        else:
            main_column.controls.append(ft.Row([
                self._create_stat_card("📦", str(total_items), "Items"),
                self._create_stat_card("📊", str(total_stock), "Stock"),
                self._create_stat_card("📈", str(len(materials)), "Materials"),
            ], spacing=10))

        main_column.controls.append(ft.Container(height=5))

        # ============ QUICK ACTIONS ============
        main_column.controls.append(
            ft.Text("⚡ Quick Actions",
                    size=16 if is_mobile else 18,
                    weight=ft.FontWeight.BOLD))

        main_column.controls.append(ft.Row([
            ft.ElevatedButton(
                "📦 Add",
                on_click=lambda e: self.open_add_modal(page),
                expand=True, height=44,
                style=ft.ButtonStyle(padding=8),
            ),
            ft.ElevatedButton(
                "🔧 Add",
                on_click=lambda e: self.open_add_accessory_modal(page),
                expand=True, height=44,
                style=ft.ButtonStyle(padding=8),
            ),
        ], spacing=8))

        main_column.controls.append(ft.Row([
            ft.ElevatedButton(
                "📷 Scan",
                on_click=lambda e: self.show_barcode_scanner(page),
                expand=True, height=44,
                style=ft.ButtonStyle(padding=8),
            ),
            ft.ElevatedButton(
                "📊 Inventory",
                on_click=lambda e: self.show_inventory(page),
                expand=True, height=44,
                style=ft.ButtonStyle(padding=8),
            ),
        ], spacing=8))

        main_column.controls.append(ft.Container(height=8))

        # ============ RECENT MATERIALS ============
        main_column.controls.append(
            ft.Text("📦 Recent Materials",
                    size=14 if is_mobile else 16,
                    weight=ft.FontWeight.BOLD))

        if materials:
            for m in materials[:5]:
                main_column.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text("📦", size=16),
                        ft.Text((m.get('name') or 'N/A')[:24],
                                size=13, expand=True),
                        ft.Text(f"Qty: {m.get('quantity', 0) or 0}",
                                size=13),
                    ]),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                ))
        else:
            main_column.controls.append(ft.Container(
                content=ft.Text("No materials yet", size=12, color="#888888"),
                padding=12, bgcolor="#2C2C2C", border_radius=8,
            ))

        main_column.controls.append(ft.Container(height=8))

        # ============ RECENT ACCESSORIES ============
        main_column.controls.append(
            ft.Text("🔧 Recent Accessories",
                    size=14 if is_mobile else 16,
                    weight=ft.FontWeight.BOLD))

        if accessories:
            for a in accessories[:5]:
                price = a.get('price', 0) or 0
                price_text = f"${price:.2f}" if price > 0 else ""
                main_column.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text("🔧", size=16),
                        ft.Text((a.get('name') or 'N/A')[:20],
                                size=13, expand=True),
                        ft.Text(f"Qty: {a.get('quantity', 0) or 0}",
                                size=13),
                        ft.Text(price_text, size=11, color="#4CAF50"),
                    ]),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                ))
        else:
            main_column.controls.append(ft.Container(
                content=ft.Text("No accessories yet", size=12, color="#888888"),
                padding=12, bgcolor="#2C2C2C", border_radius=8,
            ))

        # Footer
        main_column.controls.append(ft.Divider())
        main_column.controls.append(ft.Row([
            ft.Text("✅ Free Version", size=10, color="#4CAF50"),
            ft.Container(expand=True),
            ft.Text("v2.0.0", size=10, color="#888888"),
        ]))
        main_column.controls.append(ft.Container(height=20))

        # ============ LAYOUT ============
        if is_mobile:
            bottom_nav = self.create_bottom_nav(page)
            banner = self.ads.banner_widget() if self.ads else ft.Container(height=0)
            page.add(ft.Column([
                ft.Container,
                banner,          # ← NEW LINE
                bottom_nav,
            ], spacing=0, expand=True))
        else:
            # Desktop: sidebar + content
            sidebar = self.create_sidebar(page)
            page.add(ft.Row([
                sidebar,
                ft.Container(content=main_column, expand=True, padding=20),
            ], spacing=0, expand=True))

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
            padding=10, bgcolor=color, border_radius=10, expand=True,
        )
    def show_categories_dialog(self, page: ft.Page, refresh_callback=None):
        """Categories dialog with add/delete functionality"""
        from datetime import datetime

        current_user_id = (self.current_user or {}).get('id') or 1

        # Check if categories table has user_id column
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
        categories_list = ft.Column(spacing=5,
                                    scroll=ft.ScrollMode.AUTO,
                                    height=250)

        def confirm_delete_category(cat_id, cat_name):
            def do_delete(e):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE materials SET category_id = NULL WHERE category_id = ?",
                        (cat_id,))
                    cursor.execute(
                        "UPDATE accessories SET category_id = NULL WHERE category_id = ?",
                        (cat_id,))
                    cursor.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
                    conn.commit()
                    conn.close()

                    confirm_dialog.open = False
                    status_text.value = f"✓ Deleted: {cat_name}"
                    status_text.color = "green"
                    load_categories()
                    if refresh_callback:
                        refresh_callback()
                    page.update()
                except Exception as ex:
                    status_text.value = f"Error: {ex}"
                    status_text.color = "red"
                    page.update()

            def cancel_delete(e):
                confirm_dialog.open = False
                page.update()

            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Delete Category", size=18,
                              weight=ft.FontWeight.BOLD,
                              color=self.danger_color),
                content=ft.Container(content=ft.Column([
                    ft.Text(f"Delete '{cat_name}'?", size=14),
                    ft.Text("Items using this category will become uncategorized.",
                            size=11, color="#888888"),
                    ft.Text("This cannot be undone!", size=11,
                            color=self.danger_color),
                ], spacing=8), width=300, padding=20),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_delete),
                    ft.ElevatedButton("Delete", on_click=do_delete,
                                      style=ft.ButtonStyle(
                                          bgcolor=self.danger_color)),
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
                    cursor.execute(
                        "SELECT id, name, icon FROM categories "
                        "WHERE user_id = ? ORDER BY name",
                        (current_user_id,))
                else:
                    cursor.execute(
                        "SELECT id, name, icon FROM categories ORDER BY name")
                cats = cursor.fetchall()
                conn.close()

                if cats:
                    for cat in cats:
                        icon = cat['icon'] if cat['icon'] else "📁"
                        categories_list.controls.append(ft.Container(
                            content=ft.Row([
                                ft.Text(icon, size=22),
                                ft.Text(cat['name'], size=14, expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_size=18,
                                    icon_color=self.danger_color,
                                    tooltip="Delete Category",
                                    on_click=lambda e, cid=cat['id'],
                                                     cname=cat['name']:
                                        confirm_delete_category(cid, cname),
                                ),
                            ]),
                            padding=10, bgcolor="#2C2C2C", border_radius=8,
                            margin=ft.margin.only(bottom=5),
                        ))
                else:
                    defaults = [
                        ("📦", "Raw Material"), ("🔩", "Hardware"),
                        ("🔧", "Tools"), ("⚡", "Electrical"),
                        ("💧", "Plumbing"), ("⚙️", "Metal"),
                        ("📁", "Other"),
                    ]
                    for icon, name in defaults:
                        categories_list.controls.append(ft.Container(
                            content=ft.Row([
                                ft.Text(icon, size=22),
                                ft.Text(name, size=14, expand=True),
                                ft.Text("System", size=10, color="#888888"),
                            ]),
                            padding=10, bgcolor="#2C2C2C", border_radius=8,
                            margin=ft.margin.only(bottom=5),
                        ))
                page.update()
            except Exception as ex:
                print(f"Error loading categories: {ex}")
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
                    cursor.execute(
                        "SELECT id FROM categories WHERE name = ? AND user_id = ?",
                        (name, current_user_id))
                else:
                    cursor.execute(
                        "SELECT id FROM categories WHERE name = ?", (name,))

                if cursor.fetchone():
                    status_text.value = "❌ Already exists!"
                    status_text.color = "red"
                    page.update()
                    conn.close()
                    return

                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if has_user_id:
                    cursor.execute(
                        "INSERT INTO categories (name, icon, user_id, created_at) "
                        "VALUES (?, ?, ?, ?)",
                        (name, icon_select.value, current_user_id, now))
                else:
                    cursor.execute(
                        "INSERT INTO categories (name, icon, created_at) "
                        "VALUES (?, ?, ?)",
                        (name, icon_select.value, now))
                conn.commit()
                conn.close()

                name_input.value = ""
                status_text.value = f"✓ Added: {name}"
                status_text.color = "green"
                load_categories()
                if refresh_callback:
                    refresh_callback()
            except Exception as ex:
                status_text.value = f"Error: {ex}"
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
                ft.Text("Categories", size=18,
                        weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=20,
                              on_click=lambda e: close_dlg()),
            ]),
            ft.Divider(),
            ft.Text("Add New Category", size=14, weight=ft.FontWeight.BOLD),
            name_input,
            icon_select,
            ft.ElevatedButton("➕ Add", on_click=add_category,
                              style=ft.ButtonStyle(bgcolor=self.success_color)),
            status_text,
            ft.Divider(),
            ft.Text("My Categories", size=14, weight=ft.FontWeight.BOLD),
            categories_list,
        ], spacing=10, scroll=ft.ScrollMode.AUTO)

        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=content, width=400, height=600,
                                 padding=15),
            actions=[ft.TextButton("Close", on_click=lambda e: close_dlg())],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def show_settings(self, page: ft.Page):
        """Settings screen + banner ad + mobile bottom nav"""
        page.controls.clear()

        is_mobile = (page.width or 800) < 800
        font_title = 22 if is_mobile else 28
        font_normal = 15 if is_mobile else 18
        font_small = 13 if is_mobile else 14
        padding_size = 12 if is_mobile else 20

        current_user = self.current_user or {}

        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        # Header
        scroll_content.controls.append(ft.Row([
            ft.Text("⚙️ Settings", size=font_title,
                    weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(expand=True),
        ]))
        scroll_content.controls.append(ft.Container(height=12))

        # Profile card
        profile_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("👤 Profile", size=font_normal,
                            weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(
                                (current_user.get('name') or 'G')[0].upper(),
                                size=16),
                            radius=30, bgcolor=self.accent_color,
                        ),
                        ft.Column([
                            ft.Text(current_user.get('name', 'Store Manager'),
                                    size=font_normal, weight=ft.FontWeight.BOLD),
                            ft.Text(current_user.get('email', 'N/A'),
                                    size=font_small - 1, color="#888888"),
                            ft.Text(f"Role: {current_user.get('role', 'admin').upper()}",
                                    size=font_small - 2, color=self.success_color),
                        ], spacing=3, expand=True),
                    ], spacing=12),
                    ft.ElevatedButton(
                        "✏️ Edit Profile",
                        on_click=lambda e: self.edit_profile_dialog(page),
                        style=ft.ButtonStyle(bgcolor=self.accent_color),
                        icon=ft.Icons.EDIT,
                    ),
                ], spacing=12),
                padding=15,
            ),
            elevation=2, margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(profile_card)

        # Data management
        data_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("💾 Data Management", size=font_normal,
                            weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BACKUP, color=self.accent_color),
                        title=ft.Text("Backup Database"),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                        on_click=lambda e: self.backup_database(page),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.RESTORE, color=self.accent_color),
                        title=ft.Text("Restore Database"),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                        on_click=lambda e: self.restore_database(page),
                    ),
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.DELETE_FOREVER,
                                        color=self.danger_color),
                        title=ft.Text("Reset All Data",
                                      color=self.danger_color),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT,
                                         color=self.danger_color),
                        on_click=lambda e: self.reset_database_confirm(page),
                    ),
                ], spacing=8),
                padding=15,
            ),
            elevation=2, margin=ft.margin.only(bottom=12),
        )
        scroll_content.controls.append(data_card)

        # About
        about_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("ℹ️ About", size=font_normal,
                            weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Divider(),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🏪", size=50),
                            ft.Text("Store Management",
                                    size=font_normal + 2,
                                    weight=ft.FontWeight.BOLD),
                            ft.Text("Version 2.0.0", size=font_small - 1,
                                    color="#888888"),
                            ft.Container(height=5),
                            ft.Text("© 2024 Store Management",
                                    size=font_small - 2, color="#888888"),
                            ft.Text("Made with ❤️ using Flet",
                                    size=font_small - 2, color="#888888"),
                            ft.Container(height=5),
                            ft.Text("Status: ✅ Free Version",
                                    size=font_small - 1, color="#4CAF50"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                           spacing=5),
                        margin=ft.margin.only(bottom=10),
                    ),
                ], spacing=10,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
            ),
            elevation=2,
        )
        scroll_content.controls.append(about_card)
        scroll_content.controls.append(ft.Container(height=20))

        main_container = ft.Container(
            content=scroll_content, expand=True, padding=padding_size,
        )

        # ===== BANNER AD (safe for desktop) =====
        try:
            banner = self.ads.banner_widget() if self.ads else ft.Container(height=0)
        except Exception:
            banner = ft.Container(height=0)

        # Layout
        if is_mobile:
            bottom_nav = self.create_bottom_nav(page)
            page.add(ft.Column([
                main_container,
                banner,
                bottom_nav,
            ], spacing=0, expand=True))
        else:
            sidebar = self.create_sidebar(page)
            page.add(ft.Column([
                ft.Row([sidebar, main_container], spacing=0, expand=True),
                banner,
            ], spacing=0, expand=True))

        self.current_view = "settings"
        page.update()

    def edit_profile_dialog(self, page: ft.Page):
        current_user = self.current_user or {}
        if not current_user.get('id'):
            return

        name_field = ft.TextField(label="Full Name", value=current_user.get('name', ''),
                                  width=300, bgcolor=self.card_color)
        email_field = ft.TextField(label="Email", value=current_user.get('email', ''),
                                   width=300, bgcolor=self.card_color, read_only=True)

        def close(e):
            page.dialog.open = False
            page.update()

        def save(e):
            new_name = name_field.value.strip()
            if not new_name:
                return
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("UPDATE users SET name = ? WHERE id = ?",
                            (new_name, current_user['id']))
                conn.commit()
                conn.close()
                self.current_user['name'] = new_name
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text("✓ Profile updated!"),
                                             bgcolor=self.success_color)
                page.snack_bar.open = True
                self.show_settings(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Edit Profile"),
            content=ft.Container(content=ft.Column([
                name_field, email_field, ft.Container(height=10),
                ft.Row([
                    ft.TextButton("Cancel", on_click=close),
                    ft.FilledButton("Save", on_click=save,
                                    style=ft.ButtonStyle(bgcolor=self.success_color)),
                ], alignment=ft.MainAxisalignment.END, spacing=10),
            ], spacing=12), width=400, height=300, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def change_password_dialog(self, page: ft.Page):
        current_user = self.current_user or {}
        if not current_user.get('id'):
            return

        cur_pwd = ft.TextField(label="Current Password", password=True,
                               width=300, bgcolor=self.card_color)
        new_pwd = ft.TextField(label="New Password", password=True,
                               width=300, bgcolor=self.card_color)
        conf_pwd = ft.TextField(label="Confirm Password", password=True,
                                width=300, bgcolor=self.card_color)
        status = ft.Text("", size=12, color="#888888")

        def close(e):
            page.dialog.open = False
            page.update()

        def update(e):
            if not cur_pwd.value or not new_pwd.value or not conf_pwd.value:
                status.value = "❌ Fill all fields"
                status.color = self.danger_color
                page.update()
                return
            if new_pwd.value != conf_pwd.value:
                status.value = "❌ Passwords don't match"
                status.color = self.danger_color
                page.update()
                return
            if len(new_pwd.value) < 4:
                status.value = "❌ Min 4 characters"
                status.color = self.danger_color
                page.update()
                return
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                h_cur = hashlib.sha256(cur_pwd.value.encode()).hexdigest()
                cur.execute("SELECT id FROM users WHERE id = ? AND password_hash = ?",
                            (current_user['id'], h_cur))
                if not cur.fetchone():
                    status.value = "❌ Current password incorrect"
                    status.color = self.danger_color
                    conn.close()
                    page.update()
                    return
                h_new = hashlib.sha256(new_pwd.value.encode()).hexdigest()
                cur.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                            (h_new, current_user['id']))
                conn.commit()
                conn.close()
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text("✓ Password changed!"),
                                             bgcolor=self.success_color)
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                status.value = f"❌ {ex}"
                status.color = self.danger_color
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Change Password"),
            content=ft.Container(content=ft.Column([
                cur_pwd, new_pwd, conf_pwd, status, ft.Container(height=10),
                ft.Row([
                    ft.TextButton("Cancel", on_click=close),
                    ft.FilledButton("Update Password", on_click=update,
                                    style=ft.ButtonStyle(bgcolor=self.warning_color)),
                ], alignment=ft.MainAxisalignment.END, spacing=10),
            ], spacing=12), width=400, height=420, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def backup_database(self, page: ft.Page):
        import shutil
        try:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            backup_dir = os.path.join(app_dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "store_management.db")
            if not os.path.exists(db_path):
                page.snack_bar = ft.SnackBar(ft.Text("No database to backup!"),
                                             bgcolor=self.warning_color)
                page.snack_bar.open = True
                page.update()
                return
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f"backup_{ts}.db")
            shutil.copy2(db_path, backup_path)
            size = os.path.getsize(backup_path)
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Backup saved! ({size_str})"),
                                         bgcolor=self.success_color)
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Backup failed: {ex}"),
                                         bgcolor=self.danger_color)
            page.snack_bar.open = True
            page.update()

    def restore_database(self, page: ft.Page):
        import shutil
        app_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(app_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')],
                         reverse=True)

        if not backups:
            page.snack_bar = ft.SnackBar(ft.Text("No backups found!"),
                                         bgcolor=self.warning_color)
            page.snack_bar.open = True
            page.update()
            return

        def close(e):
            page.dialog.open = False
            page.update()

        def confirm_restore(backup_file):
            def do_restore(e):
                try:
                    src = os.path.join(backup_dir, backup_file)
                    dst = os.path.join(app_dir, "store_management.db")
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.copy2(src, dst)
                    confirm_dialog.open = False
                    close(None)
                    page.snack_bar = ft.SnackBar(ft.Text("✓ Database restored!"),
                                                 bgcolor=self.success_color)
                    page.snack_bar.open = True
                    self.show_dashboard(page)
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Restore failed: {ex}"),
                                                 bgcolor=self.danger_color)
                    page.snack_bar.open = True
                    page.update()

            def cancel(e):
                confirm_dialog.open = False
                page.update()

            confirm_dialog = ft.AlertDialog(
                title=ft.Text("Confirm Restore", color=self.danger_color),
                content=ft.Container(content=ft.Column([
                    ft.Text(f"Restore from '{backup_file}'?", size=13),
                    ft.Text("⚠️ Overwrites current data!", size=12,
                            color=self.danger_color),
                ], spacing=8), width=320, padding=20),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel),
                    ft.ElevatedButton("Restore", on_click=do_restore,
                                      style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ],
            )
            page.dialog = confirm_dialog
            confirm_dialog.open = True
            page.update()

        items = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, height=300)
        for b in backups:
            size = os.path.getsize(os.path.join(backup_dir, b))
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
            items.controls.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.STORAGE, size=20, color=self.accent_color),
                    ft.Column([
                        ft.Text(b, size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(size_str, size=10, color="#888888"),
                    ], spacing=2, expand=True),
                    ft.ElevatedButton("Restore",
                                      on_click=lambda e, bf=b: confirm_restore(bf),
                                      style=ft.ButtonStyle(bgcolor=self.success_color,
                                                           color="white")),
                ]),
                padding=8, bgcolor="#2C2C2C", border_radius=8,
                margin=ft.margin.only(bottom=5),
            ))

        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("Restore Database", weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=20,
                              on_click=lambda e: close(e)),
            ]),
            content=ft.Container(content=ft.Column([
                ft.Text(f"Select backup ({len(backups)} available):", size=13),
                ft.Container(height=5), items,
            ], spacing=10), width=450, height=450, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def reset_database_confirm(self, page: ft.Page):
        def do_reset(e):
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("DELETE FROM materials")
                cur.execute("DELETE FROM accessories")
                cur.execute("DELETE FROM users WHERE id > 1")
                conn.commit()
                conn.close()
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text("✓ Database reset!"),
                                             bgcolor=self.success_color)
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"Reset failed: {ex}"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()

        def close(e):
            page.dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Reset Database"),
            content=ft.Container(content=ft.Column([
                ft.Text("⚠️ This deletes ALL data:", size=14,
                        color=self.danger_color, weight=ft.FontWeight.BOLD),
                ft.Text("• All materials", size=13),
                ft.Text("• All accessories", size=13),
                ft.Text("• All users (except admin)", size=13),
                ft.Text("Cannot be undone!", size=13, color=self.danger_color),
                ft.Container(height=10),
                ft.Row([
                    ft.TextButton("Cancel", on_click=close),
                    ft.FilledButton("Reset", on_click=do_reset,
                                    style=ft.ButtonStyle(bgcolor=self.danger_color)),
                ], alignment=ft.MainAxisalignment.END, spacing=10),
            ], spacing=10), width=400, height=380, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

        # ============ BARCODE SCANNER ============
    def show_barcode_scanner(self, page: ft.Page):
        """Barcode scanner - manual input + clipboard paste"""
        page.controls.clear()

        is_mobile = (page.width or 800) < 800
        font_title = 22 if is_mobile else 28
        font_normal = 15 if is_mobile else 18
        font_small = 13 if is_mobile else 14
        padding_size = 12 if is_mobile else 20

        barcode_input = ft.TextField(
            label="Barcode Number",
            hint_text="Enter or paste barcode here",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            prefix_icon=ft.Icons.QR_CODE,
            autofocus=True,
        )

        status_text = ft.Text("", size=12, color="#888888")

        result_container = ft.Column(spacing=8)

        def do_search(barcode):
            if not barcode:
                status_text.value = "❌ Please enter a barcode"
                status_text.color = self.danger_color
                page.update()
                return

            status_text.value = f"🔍 Searching: {barcode}"
            status_text.color = self.accent_color
            page.update()

            # Search materials first
            item = MaterialManager.get_by_barcode(barcode)
            item_type = "Material"

            if not item:
                item = AccessoryManager.get_by_barcode(barcode)
                item_type = "Accessory"

            result_container.controls.clear()

            if item:
                item_dict = dict(item)
                status_text.value = f"✅ Found: {item_dict.get('name')}"
                status_text.color = self.success_color

                result_container.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text("📦" if item_type == "Material" else "🔧",
                                            size=24),
                                    ft.Column([
                                        ft.Text(item_dict.get('name', 'N/A'),
                                                size=16, weight=ft.FontWeight.BOLD),
                                        ft.Text(item_type, size=11,
                                                color="#888888"),
                                    ], spacing=2, expand=True),
                                ]),
                                ft.Divider(),
                                ft.Row([
                                    ft.Text("Qty:", size=13, color="#CCCCCC",
                                            width=60),
                                    ft.Text(str(item_dict.get('quantity', 0)),
                                            size=14, weight=ft.FontWeight.BOLD),
                                ]),
                                ft.Row([
                                    ft.Text("Quality:", size=13, color="#CCCCCC",
                                            width=60),
                                    ft.Text(item_dict.get('quality', 'Used'),
                                            size=13),
                                ]),
                                ft.Row([
                                    ft.Text("Location:", size=13, color="#CCCCCC",
                                            width=60),
                                    ft.Text(item_dict.get('location_ids') or
                                            item_dict.get('location') or 'N/A',
                                            size=13),
                                ]),
                                ft.Container(height=8),
                                ft.ElevatedButton(
                                    "👁️ View Details",
                                    on_click=lambda e, d=item_dict, t=item_type:
                                        self.show_material_detail_dialog(page, d)
                                        if t == "Material"
                                        else self.show_accessory_detail_dialog(page, d),
                                    style=ft.ButtonStyle(bgcolor=self.accent_color),
                                    icon=ft.Icons.VISIBILITY,
                                ),
                            ], spacing=8),
                            padding=15,
                        ),
                        elevation=2,
                    )
                )
            else:
                status_text.value = f"❌ No item found with barcode: {barcode}"
                status_text.color = self.danger_color

                result_container.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.SEARCH_OFF, size=50,
                                    color="#888888"),
                            ft.Text("Barcode not found", size=14,
                                    color="#888888"),
                            ft.Text(f"Barcode: {barcode}", size=11,
                                    color="#555555"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                           spacing=6),
                        padding=30,
                    )
                )

            page.update()

        def paste_from_clipboard(e):
            try:
                clip = page.get_clipboard()
                if clip:
                    barcode_input.value = clip
                    status_text.value = "✓ Pasted from clipboard"
                    status_text.color = self.success_color
                    page.update()
                else:
                    status_text.value = "❌ Clipboard is empty"
                    status_text.color = self.danger_color
                    page.update()
            except Exception as ex:
                status_text.value = f"❌ Error: {ex}"
                status_text.color = self.danger_color
                page.update()

        def search_click(e):
            do_search(barcode_input.value.strip())

        barcode_input.on_submit = lambda e: do_search(barcode_input.value.strip())

        # Main content
        main_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        main_column.controls.append(ft.Row([
            ft.Text("📷 Barcode Scanner", size=font_title,
                    weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(expand=True),
        ]))

        # Info banner
        main_column.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text("💡 How to use", size=14,
                            weight=ft.FontWeight.BOLD, color=self.accent_color),
                    ft.Text("1. Open your Camera app or Google Lens",
                            size=12, color="#CCCCCC"),
                    ft.Text("2. Point at the barcode and copy the number",
                            size=12, color="#CCCCCC"),
                    ft.Text("3. Come back and tap '📋 Paste' below",
                            size=12, color="#CCCCCC"),
                    ft.Text("4. Tap '🔍 Search' to find the item",
                            size=12, color="#CCCCCC"),
                ], spacing=4),
                padding=15,
                bgcolor=self.card_color,
                border_radius=10,
            )
        )

        main_column.controls.append(barcode_input)

        main_column.controls.append(ft.Row([
            ft.ElevatedButton(
                "📋 Paste",
                on_click=paste_from_clipboard,
                icon=ft.Icons.CONTENT_PASTE,
                expand=True,
                style=ft.ButtonStyle(bgcolor=self.accent_color),
            ),
            ft.ElevatedButton(
                "🔍 Search",
                on_click=search_click,
                icon=ft.Icons.SEARCH,
                expand=True,
                style=ft.ButtonStyle(bgcolor=self.success_color),
            ),
        ], spacing=10))

        main_column.controls.append(status_text)

        main_column.controls.append(ft.Divider())

        main_column.controls.append(result_container)

        main_column.controls.append(ft.Container(height=20))

        main_container = ft.Container(
            content=main_column, expand=True, padding=padding_size,
        )

        # Banner (mobile-safe)
        try:
            banner = self.ads.banner_widget() if self.ads else ft.Container(height=0)
        except Exception:
            banner = ft.Container(height=0)

        # Layout
        if is_mobile:
            bottom_nav = self.create_bottom_nav(page)
            page.add(ft.Column([
                main_container,
                banner,
                bottom_nav,
            ], spacing=0, expand=True))
        else:
            sidebar = self.create_sidebar(page)
            page.add(ft.Column([
                ft.Row([sidebar, main_container], spacing=0, expand=True),
                banner,
            ], spacing=0, expand=True))

        self.current_view = "barcode_scanner"
        page.update()

    def search_barcode_by_value(self, barcode_value, page):
        """Search for barcode and show result"""
        if not barcode_value:
            page.snack_bar = ft.SnackBar(ft.Text("Please enter a barcode!"),
                                         bgcolor=self.warning_color)
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
                bgcolor=self.success_color, duration=3000)
            page.snack_bar.open = True
            
            if item_type == 'material':
                self.show_material_detail_dialog(page, item_dict)
            else:
                self.show_accessory_detail_dialog(page, item_dict)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ No item found: {barcode_value}"),
                bgcolor=self.danger_color, duration=3000)
            page.snack_bar.open = True
        page.update()

        # ============ INVENTORY SCREEN ============
    def show_inventory(self, page: ft.Page):
        """Inventory screen + banner ad + mobile bottom nav"""
        page.controls.clear()

        is_mobile = (page.width or 800) < 800
        font_title = 22 if is_mobile else 28
        font_normal = 15 if is_mobile else 18
        font_small = 13 if is_mobile else 14
        padding_size = 12 if is_mobile else 20

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
        total_value = sum(i.get('quantity', 0) *
                          (i.get('price', 0) if i.get('price') else 10)
                          for i in inventory_items)

        self.current_filtered_items = inventory_items.copy()

        scroll_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

        # Header
        scroll_content.controls.append(ft.Row([
            ft.Text("Inventory", size=font_title,
                    weight=ft.FontWeight.BOLD, color=self.text_color),
            ft.Container(expand=True),
            ft.IconButton(icon=ft.Icons.REFRESH, icon_size=22,
                          icon_color=self.accent_color,
                          on_click=lambda e: self.show_inventory(page)),
        ]))
        scroll_content.controls.append(ft.Container(height=12))

        # Stats row 1
        scroll_content.controls.append(ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("📦 Items", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_items), size=font_title + 2,
                            weight=ft.FontWeight.BOLD),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=10, bgcolor=self.accent_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("📊 Stock", size=font_small, color="#CCCCCC"),
                    ft.Text(str(total_stock), size=font_title + 2,
                            weight=ft.FontWeight.BOLD),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=10, bgcolor=self.success_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("💰 Value", size=font_small, color="#CCCCCC"),
                    ft.Text(f"${total_value:,.0f}", size=font_title,
                            weight=ft.FontWeight.BOLD),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=10, bgcolor="#9C27B0", border_radius=10, expand=True,
            ),
        ], spacing=8))
        scroll_content.controls.append(ft.Container(height=8))

        # Stats row 2
        scroll_content.controls.append(ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WARNING, size=18, color=self.warning_color),
                    ft.Text(str(len(low_stock_items)), size=font_title,
                            weight=ft.FontWeight.BOLD, color=self.warning_color),
                    ft.Text("Low", size=font_small - 2, color="#888888"),
                ], spacing=6),
                padding=8, bgcolor=self.card_color, border_radius=10, expand=True,
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR, size=18, color=self.danger_color),
                    ft.Text(str(len(critical_stock)), size=font_title,
                            weight=ft.FontWeight.BOLD, color=self.danger_color),
                    ft.Text("Critical", size=font_small - 2, color="#888888"),
                ], spacing=6),
                padding=8, bgcolor=self.card_color, border_radius=10, expand=True,
            ),
        ], spacing=8))
        scroll_content.controls.append(ft.Container(height=10))

        # Filters
        type_filter = ft.Dropdown(
            label="Type", width=110,
            options=[
                ft.dropdown.Option("All", "All"),
                ft.dropdown.Option("material", "📦 Materials"),
                ft.dropdown.Option("accessory", "🔧 Accessories"),
            ],
            value="All", bgcolor=self.card_color,
        )
        quality_filter = ft.Dropdown(
            label="Quality", width=110,
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
            label="Stock", width=120,
            options=[
                ft.dropdown.Option("All", "All"),
                ft.dropdown.Option("Low", "⚠️ Low"),
                ft.dropdown.Option("Critical", "🔥 Critical"),
                ft.dropdown.Option("Normal", "✅ Normal"),
            ],
            value="All", bgcolor=self.card_color,
        )
        search_input = ft.TextField(
            hint_text="Search...", expand=True,
            bgcolor=self.card_color, prefix_icon=ft.Icons.SEARCH,
            dense=True,
        )

        scroll_content.controls.append(
            ft.Row([type_filter, quality_filter, stock_filter],
                   spacing=6, wrap=True))
        scroll_content.controls.append(ft.Container(height=6))
        scroll_content.controls.append(
            ft.Row([search_input,
                    ft.OutlinedButton("Reset",
                                      on_click=lambda e: self.show_inventory(page))],
                   spacing=8))
        scroll_content.controls.append(ft.Container(height=10))

        inventory_container = ft.Column(spacing=6)

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
                q = search_input.value.lower()
                filtered = [i for i in filtered
                            if q in i['name'].lower() or q in i['code'].lower()]

            self.current_filtered_items = filtered
            inventory_container.controls.append(
                ft.Text(f"{len(filtered)} of {len(inventory_items)} items",
                        size=font_small - 1, color="#888888"))

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

                inventory_container.controls.append(ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item['type_icon'], size=font_normal + 2),
                                ft.Column([
                                    ft.Text(item['name'], size=font_normal,
                                            weight=ft.FontWeight.BOLD),
                                    ft.Text(item['code'], size=font_small - 2,
                                            color="#888888"),
                                ], spacing=2, expand=True),
                                ft.Column([
                                    ft.Text(f"{item['quantity']}",
                                            size=font_normal,
                                            weight=ft.FontWeight.BOLD,
                                            color=stock_color),
                                    ft.Text(status_text, size=font_small - 3,
                                            color=stock_color),
                                ], horizontal_alignment=ft.CrossAxisAlignment.END),
                            ]),
                            ft.ProgressBar(value=pct / 100, color=stock_color,
                                           bgcolor="#3C3C3C", height=5),
                            ft.Row([
                                ft.Text(f"📍 {item['location']}",
                                        size=font_small - 1, expand=True),
                                ft.Container(
                                    content=ft.Text(item['quality'],
                                                    size=font_small - 2, color="white"),
                                    bgcolor=self.get_quality_color(item['quality']),
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_size=18,
                                              on_click=lambda e, it=item: self.quick_stock_change(page, it, '+')),
                                ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE, icon_size=18,
                                              on_click=lambda e, it=item: self.quick_stock_change(page, it, '-')),
                                ft.IconButton(icon=ft.Icons.EDIT, icon_size=18,
                                              on_click=lambda e, it=item: self.edit_inventory_item(page, it)),
                                ft.IconButton(icon=ft.Icons.QR_CODE, icon_size=18,
                                              on_click=lambda e, it=item: self.show_barcode_dialog(page, it)),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18,
                                              on_click=lambda e, it=item: self.delete_inventory_item(page, it)),
                            ], spacing=0),
                        ], spacing=4),
                        padding=10,
                    ),
                    elevation=1,
                ))
            page.update()

        type_filter.on_change = lambda e: update_display()
        quality_filter.on_change = lambda e: update_display()
        stock_filter.on_change = lambda e: update_display()
        search_input.on_change = lambda e: update_display()
        update_display()

        scroll_content.controls.append(inventory_container)
        scroll_content.controls.append(ft.Container(height=20))

        main_container = ft.Container(
            content=scroll_content, expand=True, padding=padding_size,
        )

        # ===== BANNER AD =====
        banner = self.ads.banner_widget() if self.ads else ft.Container(height=0)

        if is_mobile:
            bottom_nav = self.create_bottom_nav(page)
            page.add(ft.Column([
                main_container,
                banner,
                bottom_nav,
            ], spacing=0, expand=True))
        else:
            sidebar = self.create_sidebar(page)
            page.add(ft.Column([
                ft.Row([sidebar, main_container], spacing=0, expand=True),
                banner,
            ], spacing=0, expand=True))

        self.current_view = "inventory"
        page.update()

    def quick_stock_change(self, page: ft.Page, item, operation):
        current_qty = item.get('quantity', 0)
        new_qty = current_qty + 1 if operation == '+' else max(current_qty - 1, 0)
        update_data = {'quantity': new_qty}
        if item['type'] == 'material':
            MaterialManager.update(item['id'], update_data)
        else:
            AccessoryManager.update(item['id'], update_data)
        page.snack_bar = ft.SnackBar(
            ft.Text(f"✓ {'Added' if operation == '+' else 'Removed'} 1 unit. New: {new_qty}"),
            bgcolor=self.success_color, duration=1500)
        page.snack_bar.open = True
        self.show_inventory(page)

    def edit_inventory_item(self, page: ft.Page, item):
        if item['type'] == 'material':
            self.open_edit_modal(page, item['id'])
        else:
            self.open_edit_accessory_modal(page, item['id'])

    def delete_inventory_item(self, page: ft.Page, item):
        def do_delete(e):
            if item['type'] == 'material':
                MaterialManager.delete(item['id'])
            else:
                AccessoryManager.delete(item['id'])
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Deleted: {item['name']}"),
                                         bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_inventory(page)

        def close(e):
            page.dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete", color=self.danger_color),
            content=ft.Text(f"Delete '{item['name']}'?", size=14),
            actions=[
                ft.TextButton("Cancel", on_click=close),
                ft.FilledButton("Delete", on_click=do_delete,
                                style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    # 1) DELETE MATERIAL
    def open_delete_modal(self, page, material_id):
        material = MaterialManager.get_by_id(material_id)
        if not material:
            return
        name = dict(material).get('name', 'this item')

        def close(e):
            page.dialog.open = False
            page.update()

        def confirm(e):
            MaterialManager.delete(material_id)
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Deleted: {name}"),
                                        bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_materials_screen(page)

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete", color=self.danger_color),
            content=ft.Text(f"Delete '{name}'?", size=14),
            actions=[
                ft.TextButton("Cancel", on_click=close),
                ft.FilledButton("Delete", on_click=confirm,
                                style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()


    # 2) DELETE ACCESSORY
    def open_delete_accessory_modal(self, page, accessory_id):
        accessory = AccessoryManager.get_by_id(accessory_id)
        if not accessory:
            return
        name = dict(accessory).get('name', 'this item')

        def close(e):
            page.dialog.open = False
            page.update()

        def confirm(e):
            AccessoryManager.delete(accessory_id)
            page.dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✓ Deleted: {name}"),
                                        bgcolor=self.danger_color)
            page.snack_bar.open = True
            self.show_accessories(page)

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete", color=self.danger_color),
            content=ft.Text(f"Delete '{name}'?", size=14),
            actions=[
                ft.TextButton("Cancel", on_click=close),
                ft.FilledButton("Delete", on_click=confirm,
                                style=ft.ButtonStyle(bgcolor=self.danger_color)),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
    
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
        length_display = 'N/A'
        if length:
            try:
                lf = float(length)
                length_display = f"{lf:.2f}" if lf % 1 != 0 else str(int(lf))
            except:
                length_display = str(length)

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
                rel = os.path.join(base_dir, image_path)
                if os.path.exists(rel):
                    has_image = True
                    full_image_path = rel
                else:
                    img_p = os.path.join(base_dir, "images", os.path.basename(image_path))
                    if os.path.exists(img_p):
                        has_image = True
                        full_image_path = img_p

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
            def close_fs():
                page.overlay.clear()
                page.update()
            sw = page.width if page.width else 400
            sh = page.height if page.height else 600
            fs = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(expand=True),
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_size=30,
                                      on_click=lambda e: close_fs()),
                    ]),
                    ft.Container(
                        content=ft.Image(src=full_image_path, fit=ft.ImageFit.CONTAIN,
                                         width=sw - 40, height=sh - 100),
                        expand=True, alignment=ft.alignment.center,
                    ),
                ], spacing=10),
                expand=True, bgcolor="#000000CC",
            )
            page.overlay.append(fs)
            page.update()

        items = []

        if has_image:
            items.append(ft.Container(
                content=ft.Stack([
                    ft.Container(
                        content=ft.Image(src=full_image_path, fit=ft.ImageFit.CONTAIN,
                                         width=200, height=150),
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=ft.Icon(ft.Icons.ZOOM_IN, size=20, color="white"),
                        bgcolor="#00000099", border_radius=20, padding=5,
                        right=5, top=5, on_click=show_fullscreen, ink=True,
                    ),
                ]),
                alignment=ft.alignment.center,
                margin=ft.margin.only(bottom=10),
            ))
        else:
            items.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color="#888888"),
                    ft.Text("No Image", size=12, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                margin=ft.margin.only(bottom=10),
            ))

        items.append(ft.Divider())
        items.append(ft.Row([
            ft.Text("📁 Category:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{category_icon} {category_name}", size=13,
                    color=self.accent_color, weight=ft.FontWeight.BOLD),
        ], spacing=8))
        items.append(ft.Row([
            ft.Text("🔢 Barcode:", size=13, color="#CCCCCC", width=100),
            ft.Text(barcode, size=12, color="#888888"),
        ], spacing=8))
        items.append(ft.Row([
            ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                              style=ft.ButtonStyle(bgcolor=self.warning_color,
                                                   color=self.text_color)),
        ], spacing=10))
        items.append(ft.Divider())
        items.append(ft.Row([
            ft.Text("🏷️ Quality:", size=13, color="#CCCCCC", width=100),
            ft.Container(
                content=ft.Text(quality, size=12, color="white"),
                bgcolor=self.get_quality_color(quality), border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            ),
        ], spacing=8))
        qty_color = self.danger_color if quantity < 10 else self.text_color
        items.append(ft.Row([
            ft.Text("🔢 Quantity:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{quantity} units", size=14, weight=ft.FontWeight.BOLD,
                    color=qty_color),
        ], spacing=8))
        items.append(ft.Row([
            ft.Text("📍 Location:", size=13, color="#CCCCCC", width=100),
            ft.Text(location, size=13, color=self.text_color),
        ], spacing=8))

        if size_display != 'N/A' or length_display != 'N/A':
            items.append(ft.Divider())
            items.append(ft.Text("📏 Dimensions", size=14,
                                 weight=ft.FontWeight.BOLD, color=self.accent_color))
            if size_display != 'N/A':
                items.append(ft.Row([
                    ft.Text("📏 Size:", size=13, color="#CCCCCC", width=100),
                    ft.Text(size_display, size=13, color=self.text_color),
                ], spacing=8))
            if length_display != 'N/A':
                items.append(ft.Row([
                    ft.Text("📐 Length:", size=13, color="#CCCCCC", width=100),
                    ft.Text(length_display, size=13, color=self.text_color),
                ], spacing=8))

        if colors_display != 'N/A':
            items.append(ft.Divider())
            items.append(ft.Row([
                ft.Text("🎨 Colors:", size=13, color="#CCCCCC", width=100),
                ft.Text(colors_display, size=13, color=self.text_color),
            ], spacing=8))

        items.append(ft.Divider())
        items.append(ft.Row([
            ft.Text("📅 Created:", size=13, color="#CCCCCC", width=100),
            ft.Text(created, size=12, color="#888888"),
        ], spacing=8))
        items.append(ft.Row([
            ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=100),
            ft.Text(updated, size=12, color="#888888"),
        ], spacing=8))

        if notes_display != 'No notes':
            items.append(ft.Divider())
            items.append(ft.Text("📝 Notes", size=14,
                                 weight=ft.FontWeight.BOLD, color=self.accent_color))
            items.append(ft.Container(
                content=ft.Text(notes_display, size=12, color="#888888"),
                padding=10, bgcolor="#2C2C2C", border_radius=8,
                margin=ft.margin.only(top=5, bottom=10),
            ))

        items.append(ft.Divider())
        items.append(ft.Row([
            ft.ElevatedButton("✏️ EDIT", on_click=edit_material, expand=True,
                              style=ft.ButtonStyle(bgcolor=self.accent_color,
                                                   color=self.text_color)),
            ft.ElevatedButton("🗑️ DELETE", on_click=delete_material, expand=True,
                              style=ft.ButtonStyle(bgcolor=self.danger_color,
                                                   color=self.text_color)),
        ], spacing=10))

        scrollable = ft.Column(items, spacing=8, scroll=ft.ScrollMode.AUTO, height=500)

        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable, width=dialog_width, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_materials_screen(self, page: ft.Page):
        """Materials screen with full CRUD + banner ad + mobile bottom nav"""
        page.controls.clear()

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

        is_mobile = (page.width or 800) < 800

        main_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        main_column.controls.append(
            ft.Text("Materials", size=22 if is_mobile else 28,
                    weight=ft.FontWeight.BOLD, color=self.text_color))

        search_field = ft.TextField(
            hint_text="Search materials...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
        )
        main_column.controls.append(search_field)

        cat_options = [ft.dropdown.Option("All", "📁 All Categories")]
        for c in categories:
            icon = c['icon'] if c['icon'] else "📁"
            cat_options.append(ft.dropdown.Option(str(c["id"]), f"{icon} {c['name']}"))

        category_filter = ft.Dropdown(
            label="Category",
            width=150 if is_mobile else 170,
            options=cat_options,
            value="All",
            bgcolor=self.card_color,
            dense=True,
        )

        quality_filter = ft.Dropdown(
            label="Quality",
            width=130 if is_mobile else 150,
            value="All",
            bgcolor=self.card_color,
            dense=True,
            options=[
                ft.dropdown.Option("All", "[A] All"),
                ft.dropdown.Option("New", "[N] New"),
                ft.dropdown.Option("Used", "[U] Used"),
                ft.dropdown.Option("Damaged", "[D] Damaged"),
                ft.dropdown.Option("Repaired", "[R] Repaired"),
            ],
        )

        add_category_btn = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            icon_size=24,
            icon_color=self.success_color,
            tooltip="Manage Categories",
            on_click=lambda e: self.show_categories_dialog(
                page, lambda: self.show_materials_screen(page)),
        )

        main_column.controls.append(
            ft.Row([category_filter, quality_filter, add_category_btn],
                   spacing=8, wrap=True))
        main_column.controls.append(ft.Container(height=5))

        cards_container = ft.Column(spacing=8)
        main_column.controls.append(cards_container)

        def update_cards():
            cards_container.controls.clear()
            query = (search_field.value or "").lower()
            sel_cat = category_filter.value
            sel_q = quality_filter.value
            count = 0

            for m in materials:
                if query and query not in (m["name"] or "").lower():
                    continue
                if sel_cat != "All" and str(m["category_id"]) != sel_cat:
                    continue
                if sel_q != "All" and m["quality"] != sel_q:
                    continue

                count += 1
                cat_name = m["category_name"] if m["category_name"] else "Other"
                cat_icon = m["category_icon"] if m["category_icon"] else "📁"
                qty = m["quantity"] or 0
                q = m["quality"] or "Used"

                q_color = {
                    "New": "#4CAF50", "Used": "#FF9800",
                    "Damaged": "#F44336", "Repaired": "#2196F3"
                }.get(q, "#888888")

                q_display = {
                    "New": "[N] New", "Used": "[U] Used",
                    "Damaged": "[D] Damaged", "Repaired": "[R] Repaired"
                }.get(q, q)

                cards_container.controls.append(ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(m["name"], size=15,
                                        weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=self.danger_color if qty < 10 else self.text_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=11,
                                        color=self.accent_color, expand=True),
                                ft.Container(
                                    content=ft.Text(q_display, size=9, color="white"),
                                    bgcolor=q_color, border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.Text(f"📍 {m['location_ids'] or 'N/A'}",
                                        size=10, color="#888888", expand=True),
                                ft.Text(f"📏 {m['size'] or 'N/A'}",
                                        size=10, color="#888888"),
                            ]),
                        ], spacing=4),
                        padding=10,
                        on_click=lambda e, mat=dict(m): self.show_material_detail_dialog(page, mat),
                    ),
                    elevation=1,
                ))

            if count == 0:
                cards_container.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX, size=50, color="#888888"),
                        ft.Text("No materials found", size=13, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30))
            else:
                cards_container.controls.insert(
                    0, ft.Text(f"{count} of {len(materials)}",
                               size=10, color="#888888"))
            page.update()

        search_field.on_change = lambda e: update_cards()
        category_filter.on_change = lambda e: update_cards()
        quality_filter.on_change = lambda e: update_cards()
        update_cards()

        add_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_modal(page),
            mini=is_mobile,
        )

        main_container = ft.Container(
            content=main_column, expand=True,
            padding=12 if is_mobile else 20,
        )

        # ===== BANNER AD =====
        banner = self.ads.banner_widget() if self.ads else ft.Container(height=0)

        if is_mobile:
            bottom_nav = self.create_bottom_nav(page)
            page.add(
                ft.Column([
                    ft.Stack([
                        ft.Container(content=main_container, expand=True),
                        ft.Container(content=add_button, right=16, bottom=16),
                    ], expand=True),
                    banner,
                    bottom_nav,
                ], spacing=0, expand=True)
            )
        else:
            sidebar = self.create_sidebar(page)
            page.add(
                ft.Column([
                    ft.Stack([
                        ft.Row([sidebar, main_container], spacing=0, expand=True),
                        ft.Container(content=add_button, right=16, bottom=70),
                    ], expand=True),
                    banner,
                ], spacing=0, expand=True)
            )

        self.current_view = "materials"
        page.update()

    def open_add_accessory_modal(self, page: ft.Page):
        """Add new accessory"""
        import os
        from datetime import datetime

        def generate_barcode():
            prefix = "890"
            rand = ''.join(random.choices(string.digits, k=9))
            base = prefix + rand
            total = 0
            for i, d in enumerate(base):
                total += int(d) * (1 if i % 2 == 0 else 3)
            check = (10 - (total % 10)) % 10
            return base + str(check)

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

        cat_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}")
                       for c in categories]

        name_field = ft.TextField(label="Name *", width=field_width,
                                  bgcolor=self.card_color, autofocus=True)
        cat_field = ft.Dropdown(label="Category", width=field_width,
                                options=cat_options,
                                value=str(categories[0]['id']) if categories else "1",
                                bgcolor=self.card_color)
        qty_field = ft.TextField(label="Quantity", width=field_width,
                                 bgcolor=self.card_color, value="0")
        price_field = ft.TextField(label="Price", width=field_width,
                                   bgcolor=self.card_color, value="0.00")
        quality_field = ft.Dropdown(
            label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"),
                     ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value="New", bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", width=field_width,
                                      bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", width=field_width,
                                   bgcolor=self.card_color,
                                   multiline=True, min_lines=2, max_lines=3)

        barcode_field = ft.TextField(label="Barcode", width=field_width - 80,
                                     bgcolor=self.card_color,
                                     value=generate_barcode(), read_only=True)
        regen_btn = ft.TextButton(
            "🔄 New Barcode",
            on_click=lambda e: setattr(barcode_field, 'value', generate_barcode()) or page.update())
        barcode_row = ft.Row([barcode_field, regen_btn], spacing=8)

        img_status = ft.Text("No image", size=10, color="#888888")
        img_data = {"data": None}

        def on_pick(e: ft.FilePickerResultEvent):
            if e.files:
                f = e.files[0]
                try:
                    with open(f.path, 'rb') as fp:
                        img_data["data"] = {'name': f.name, 'bytes': fp.read(), 'size': f.size}
                    img_status.value = f"✓ {f.name[:20]} ({f.size/1024:.0f}KB)"
                    img_status.color = self.success_color
                except:
                    img_status.value = "❌ Error reading image"
                    img_status.color = self.danger_color
                page.update()

        picker = ft.FilePicker(on_result=on_pick)
        page.overlay.append(picker)

        def upload_img(e):
            picker.pick_files(allow_multiple=False,
                              allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])

        upload_btn = ft.ElevatedButton(
            "📁 Upload Image", on_click=upload_img, icon=ft.Icons.UPLOAD_FILE,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        img_row = ft.Row([upload_btn, img_status], spacing=8,
                         vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)

        def save_img():
            if img_data["data"]:
                try:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = os.path.splitext(img_data["data"]['name'])[1].lower()
                    fn = f"acc_{ts}{ext}"
                    path = os.path.join(images_folder, fn)
                    with open(path, 'wb') as fp:
                        fp.write(img_data["data"]['bytes'])
                    return f"images/{fn}"
                except:
                    return None
            return None

        scroll_fields = ft.Column([
            name_field, cat_field, qty_field, price_field,
            quality_field, location_field, img_row, barcode_row, notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)

        def close_dialog():
            page.dialog.open = False
            page.update()

        def save_accessory():
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return

            img_path = save_img() if img_data["data"] else None
            cat_id = int(cat_field.value)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            company_id = (self.current_user or {}).get('company_id', 1)

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO accessories
                    (name, category_id, quantity, price, quality, location,
                     notes, barcode_value, image_path, company_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name_field.value, cat_id,
                    int(qty_field.value) if qty_field.value else 0,
                    float(price_field.value) if price_field.value else 0,
                    quality_field.value, location_field.value,
                    notes_field.value, barcode_field.value,
                    img_path, company_id, now, now
                ))
                conn.commit()
                conn.close()
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value}"),
                                             bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_accessories(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()

        content = ft.Column([
            ft.Row([
                ft.Text("Add New Accessory", size=16,
                        weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=18,
                              on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Save", on_click=lambda e: save_accessory(),
                                style=ft.ButtonStyle(bgcolor=self.success_color),
                                expand=True),
            ], spacing=8),
        ], spacing=8)

        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=content, width=dialog_width, padding=10),
            modal=True,
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def open_add_modal(self, page: ft.Page):
        """Add new material"""
        import os
        from datetime import datetime

        def generate_barcode():
            prefix = "890"
            rand = ''.join(random.choices(string.digits, k=9))
            base = prefix + rand
            total = 0
            for i, d in enumerate(base):
                total += int(d) * (1 if i % 2 == 0 else 3)
            check = (10 - (total % 10)) % 10
            return base + str(check)

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

        cat_options = [ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}")
                       for c in categories]

        name_field = ft.TextField(label="Name *", width=field_width,
                                  bgcolor=self.card_color, autofocus=True)
        cat_field = ft.Dropdown(label="Category", width=field_width,
                                options=cat_options,
                                value=str(categories[0]['id']) if categories else "1",
                                bgcolor=self.card_color)
        qty_field = ft.TextField(label="Quantity", width=field_width,
                                 bgcolor=self.card_color, value="0")
        size_field = ft.TextField(label="Size", width=field_width,
                                  bgcolor=self.card_color, hint_text="e.g., 34 1/2")
        length_field = ft.TextField(label="Length (auto)", width=field_width,
                                    bgcolor=self.card_color, read_only=True)
        quality_field = ft.Dropdown(
            label="Quality", width=field_width,
            options=[ft.dropdown.Option("New"), ft.dropdown.Option("Used"),
                     ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired")],
            value="New", bgcolor=self.card_color)
        location_field = ft.TextField(label="Location", width=field_width,
                                      bgcolor=self.card_color)
        color_field = ft.TextField(label="Colors", width=field_width,
                                   bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes", width=field_width,
                                   bgcolor=self.card_color,
                                   multiline=True, min_lines=2, max_lines=3)

        barcode_field = ft.TextField(label="Barcode", width=field_width - 80,
                                     bgcolor=self.card_color,
                                     value=generate_barcode(), read_only=True)
        regen_btn = ft.TextButton(
            "🔄 New Barcode",
            on_click=lambda e: setattr(barcode_field, 'value', generate_barcode()) or page.update())
        barcode_row = ft.Row([barcode_field, regen_btn], spacing=8)

        img_status = ft.Text("No image", size=10, color="#888888")
        img_data = {"data": None}

        def on_pick(e: ft.FilePickerResultEvent):
            if e.files:
                f = e.files[0]
                try:
                    with open(f.path, 'rb') as fp:
                        img_data["data"] = {'name': f.name, 'bytes': fp.read(), 'size': f.size}
                    img_status.value = f"✓ {f.name[:20]} ({f.size/1024:.0f}KB)"
                    img_status.color = self.success_color
                except:
                    img_status.value = "❌ Error reading image"
                    img_status.color = self.danger_color
                page.update()

        picker = ft.FilePicker(on_result=on_pick)
        page.overlay.append(picker)

        def upload_img(e):
            picker.pick_files(allow_multiple=False,
                              allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])

        upload_btn = ft.ElevatedButton(
            "📁 Upload Image", on_click=upload_img, icon=ft.Icons.UPLOAD_FILE,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        img_row = ft.Row([upload_btn, img_status], spacing=8,
                         vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)

        def save_img():
            if img_data["data"]:
                try:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = os.path.splitext(img_data["data"]['name'])[1].lower()
                    fn = f"img_{ts}{ext}"
                    path = os.path.join(images_folder, fn)
                    with open(path, 'wb') as fp:
                        fp.write(img_data["data"]['bytes'])
                    return f"images/{fn}"
                except:
                    return None
            return None

        def update_length(e):
            sv = size_field.value
            if sv:
                try:
                    if ' ' in sv and '/' in sv:
                        p = sv.split()
                        w = float(p[0]); fr = p[1].split('/')
                        length_field.value = f"{w + float(fr[0])/float(fr[1]):.2f}"
                    elif '/' in sv:
                        fr = sv.split('/')
                        length_field.value = f"{float(fr[0])/float(fr[1]):.2f}"
                    else:
                        length_field.value = f"{float(sv):.2f}"
                except:
                    length_field.value = sv
            else:
                length_field.value = ""
            page.update()

        size_field.on_change = update_length

        scroll_fields = ft.Column([
            name_field, cat_field, qty_field, size_field, length_field,
            quality_field, location_field, color_field, img_row, barcode_row, notes_field,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, height=scroll_height)

        def close_dialog():
            page.dialog.open = False
            page.update()

        def save_material():
            if not name_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return

            img_path = save_img() if img_data["data"] else None
            cat_id = int(cat_field.value)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            company_id = (self.current_user or {}).get('company_id', 1)

            sv = size_field.value
            length_val = None
            if sv:
                try:
                    if ' ' in sv and '/' in sv:
                        p = sv.split()
                        w = float(p[0]); fr = p[1].split('/')
                        length_val = w + float(fr[0])/float(fr[1])
                    elif '/' in sv:
                        fr = sv.split('/')
                        length_val = float(fr[0])/float(fr[1])
                    else:
                        length_val = float(sv)
                except:
                    length_val = None

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO materials
                    (name, category_id, quantity, quality, location_ids,
                     size, length, colors, notes, barcode_value, image_path,
                     company_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name_field.value, cat_id,
                    int(qty_field.value) if qty_field.value else 0,
                    quality_field.value, location_field.value,
                    size_field.value, length_val,
                    color_field.value, notes_field.value,
                    barcode_field.value, img_path, company_id, now, now
                ))
                conn.commit()
                conn.close()
                close_dialog()
                page.snack_bar = ft.SnackBar(ft.Text(f"✓ Added: {name_field.value}"),
                                             bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_materials_screen(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()

        content = ft.Column([
            ft.Row([
                ft.Text("Add New Material", size=18,
                        weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=20,
                              on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(), expand=True),
                ft.FilledButton("Save", on_click=lambda e: save_material(),
                                style=ft.ButtonStyle(bgcolor=self.success_color),
                                expand=True),
            ], spacing=10),
        ], spacing=10)

        dialog = ft.AlertDialog(
            title=ft.Text(""),
            content=ft.Container(content=content, width=dialog_width, padding=10),
            modal=True,
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

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
                rel = os.path.join(base_dir, image_path)
                if os.path.exists(rel):
                    has_image = True
                    full_image_path = rel
                else:
                    img_p = os.path.join(base_dir, "images", os.path.basename(image_path))
                    if os.path.exists(img_p):
                        has_image = True
                        full_image_path = img_p

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
            def close_fs():
                page.overlay.clear()
                page.update()
            sw = page.width if page.width else 400
            sh = page.height if page.height else 600
            fs = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(expand=True),
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_size=30,
                                      on_click=lambda e: close_fs()),
                    ]),
                    ft.Container(
                        content=ft.Image(src=full_image_path, fit=ft.ImageFit.CONTAIN,
                                         width=sw - 40, height=sh - 100),
                        expand=True, alignment=ft.alignment.center,
                    ),
                ], spacing=10),
                expand=True, bgcolor="#000000CC",
            )
            page.overlay.append(fs)
            page.update()

        items = []

        if has_image:
            items.append(ft.Container(
                content=ft.Stack([
                    ft.Container(
                        content=ft.Image(src=full_image_path, fit=ft.ImageFit.CONTAIN,
                                         width=200, height=150),
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(
                        content=ft.Icon(ft.Icons.ZOOM_IN, size=20, color="white"),
                        bgcolor="#00000099", border_radius=20, padding=5,
                        right=5, top=5, on_click=show_fullscreen, ink=True,
                    ),
                ]),
                alignment=ft.alignment.center,
                margin=ft.margin.only(bottom=10),
            ))
        else:
            items.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color="#888888"),
                    ft.Text("No Image", size=12, color="#888888"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                margin=ft.margin.only(bottom=10),
            ))

        items.append(ft.Divider())
        items.append(ft.Row([
            ft.Text("📁 Category:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{category_icon} {category_name}", size=13,
                    color=self.accent_color, weight=ft.FontWeight.BOLD),
        ], spacing=8))
        items.append(ft.Row([
            ft.Text("🔢 Barcode:", size=13, color="#CCCCCC", width=100),
            ft.Text(barcode, size=12, color="#888888"),
        ], spacing=8))
        items.append(ft.Row([
            ft.ElevatedButton("📱 SHOW BARCODE", on_click=show_barcode, expand=True,
                              style=ft.ButtonStyle(bgcolor=self.warning_color,
                                                   color=self.text_color)),
        ], spacing=10))
        items.append(ft.Divider())
        items.append(ft.Row([
            ft.Text("🏷️ Quality:", size=13, color="#CCCCCC", width=100),
            ft.Container(
                content=ft.Text(quality, size=12, color="white"),
                bgcolor=self.get_quality_color(quality), border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
            ),
        ], spacing=8))
        qty_color = self.danger_color if quantity < 10 else self.text_color
        items.append(ft.Row([
            ft.Text("🔢 Quantity:", size=13, color="#CCCCCC", width=100),
            ft.Text(f"{quantity} units", size=14, weight=ft.FontWeight.BOLD,
                    color=qty_color),
        ], spacing=8))
        items.append(ft.Row([
            ft.Text("💰 Price:", size=13, color="#CCCCCC", width=100),
            ft.Text(price_text, size=13, color="#4CAF50", weight=ft.FontWeight.BOLD),
        ], spacing=8))
        items.append(ft.Row([
            ft.Text("📍 Location:", size=13, color="#CCCCCC", width=100),
            ft.Text(location, size=13, color=self.text_color),
        ], spacing=8))

        items.append(ft.Divider())
        items.append(ft.Row([
            ft.Text("📅 Created:", size=13, color="#CCCCCC", width=100),
            ft.Text(created, size=12, color="#888888"),
        ], spacing=8))
        items.append(ft.Row([
            ft.Text("🔄 Updated:", size=13, color="#CCCCCC", width=100),
            ft.Text(updated, size=12, color="#888888"),
        ], spacing=8))

        if notes and notes != 'No notes':
            items.append(ft.Divider())
            items.append(ft.Text("📝 Notes", size=14,
                                 weight=ft.FontWeight.BOLD, color=self.accent_color))
            items.append(ft.Container(
                content=ft.Text(notes, size=12, color="#888888"),
                padding=10, bgcolor="#2C2C2C", border_radius=8,
                margin=ft.margin.only(top=5, bottom=10),
            ))

        items.append(ft.Divider())
        items.append(ft.Row([
            ft.ElevatedButton("✏️ EDIT", on_click=edit_accessory, expand=True,
                              style=ft.ButtonStyle(bgcolor=self.accent_color,
                                                   color=self.text_color)),
            ft.ElevatedButton("🗑️ DELETE", on_click=delete_accessory, expand=True,
                              style=ft.ButtonStyle(bgcolor=self.danger_color,
                                                   color=self.text_color)),
        ], spacing=10))

        scrollable = ft.Column(items, spacing=8, scroll=ft.ScrollMode.AUTO, height=500)

        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text(name, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=20, on_click=close_dialog),
            ], spacing=0),
            content=ft.Container(content=scrollable, width=dialog_width, padding=15),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def show_accessories(self, page: ft.Page):
        """Accessories screen with full CRUD + banner ad + mobile bottom nav"""
        page.controls.clear()

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

        is_mobile = (page.width or 800) < 800

        main_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        main_column.controls.append(
            ft.Text("Accessories", size=22 if is_mobile else 28,
                    weight=ft.FontWeight.BOLD, color=self.text_color))

        search_field = ft.TextField(
            hint_text="Search accessories...",
            bgcolor=self.card_color,
            border_color=self.accent_color,
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
        )
        main_column.controls.append(search_field)

        cat_options = [ft.dropdown.Option("All", "📁 All Categories")]
        for c in categories:
            icon = c['icon'] if c['icon'] else "📁"
            cat_options.append(ft.dropdown.Option(str(c["id"]), f"{icon} {c['name']}"))

        category_filter = ft.Dropdown(
            label="Category",
            width=150 if is_mobile else 170,
            options=cat_options,
            value="All",
            bgcolor=self.card_color,
            dense=True,
        )

        quality_filter = ft.Dropdown(
            label="Quality",
            width=130 if is_mobile else 150,
            value="All",
            bgcolor=self.card_color,
            dense=True,
            options=[
                ft.dropdown.Option("All", "[A] All"),
                ft.dropdown.Option("New", "[N] New"),
                ft.dropdown.Option("Used", "[U] Used"),
                ft.dropdown.Option("Damaged", "[D] Damaged"),
                ft.dropdown.Option("Repaired", "[R] Repaired"),
            ],
        )

        add_category_btn = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            icon_size=24,
            icon_color=self.success_color,
            tooltip="Manage Categories",
            on_click=lambda e: self.show_categories_dialog(
                page, lambda: self.show_accessories(page)),
        )

        main_column.controls.append(
            ft.Row([category_filter, quality_filter, add_category_btn],
                   spacing=8, wrap=True))
        main_column.controls.append(ft.Container(height=5))

        cards_container = ft.Column(spacing=8)
        main_column.controls.append(cards_container)

        def update_cards():
            cards_container.controls.clear()
            query = (search_field.value or "").lower()
            sel_cat = category_filter.value
            sel_q = quality_filter.value
            count = 0

            for a in accessories:
                if query and query not in (a["name"] or "").lower():
                    continue
                if sel_cat != "All" and str(a["category_id"]) != sel_cat:
                    continue
                if sel_q != "All" and a["quality"] != sel_q:
                    continue

                count += 1
                cat_name = a["category_name"] if a["category_name"] else "Other"
                cat_icon = a["category_icon"] if a["category_icon"] else "📁"
                qty = a["quantity"] or 0
                q = a["quality"] or "Used"
                price = a["price"] or 0
                price_text = f"${price:.2f}" if price > 0 else ""

                q_color = {
                    "New": "#4CAF50", "Used": "#FF9800",
                    "Damaged": "#F44336", "Repaired": "#2196F3"
                }.get(q, "#888888")

                q_display = {
                    "New": "[N] New", "Used": "[U] Used",
                    "Damaged": "[D] Damaged", "Repaired": "[R] Repaired"
                }.get(q, q)

                cards_container.controls.append(ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(a["name"], size=15,
                                        weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Qty: {qty}", size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=self.danger_color if qty < 10 else self.text_color),
                            ]),
                            ft.Row([
                                ft.Text(f"{cat_icon} {cat_name}", size=11,
                                        color=self.accent_color, expand=True),
                                ft.Container(
                                    content=ft.Text(q_display, size=9, color="white"),
                                    bgcolor=q_color, border_radius=6,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                ),
                            ]),
                            ft.Row([
                                ft.Text(f"📍 {a['location'] or 'N/A'}",
                                        size=10, color="#888888", expand=True),
                                ft.Text(price_text, size=10, color="#4CAF50"),
                            ]),
                        ], spacing=4),
                        padding=10,
                        on_click=lambda e, acc=dict(a): self.show_accessory_detail_dialog(page, acc),
                    ),
                    elevation=1,
                ))

            if count == 0:
                cards_container.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INBOX, size=50, color="#888888"),
                        ft.Text("No accessories found", size=13, color="#888888"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30))
            else:
                cards_container.controls.insert(
                    0, ft.Text(f"{count} of {len(accessories)}",
                               size=10, color="#888888"))
            page.update()

        search_field.on_change = lambda e: update_cards()
        category_filter.on_change = lambda e: update_cards()
        quality_filter.on_change = lambda e: update_cards()
        update_cards()

        add_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            bgcolor=self.success_color,
            on_click=lambda e: self.open_add_accessory_modal(page),
            mini=is_mobile,
        )

        main_container = ft.Container(
            content=main_column, expand=True,
            padding=12 if is_mobile else 20,
        )

        # ===== BANNER AD =====
        banner = self.ads.banner_widget() if self.ads else ft.Container(height=0)

        if is_mobile:
            bottom_nav = self.create_bottom_nav(page)
            page.add(
                ft.Column([
                    ft.Stack([
                        ft.Container(content=main_container, expand=True),
                        ft.Container(content=add_button, right=16, bottom=16),
                    ], expand=True),
                    banner,
                    bottom_nav,
                ], spacing=0, expand=True)
            )
        else:
            sidebar = self.create_sidebar(page)
            page.add(
                ft.Column([
                    ft.Stack([
                        ft.Row([sidebar, main_container], spacing=0, expand=True),
                        ft.Container(content=add_button, right=16, bottom=70),
                    ], expand=True),
                    banner,
                ], spacing=0, expand=True)
            )

        self.current_view = "accessories"
        page.update()

    def open_edit_accessory_modal(self, page: ft.Page, accessory_id):
        """Edit accessory with image upload"""
        import os
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
            page.snack_bar = ft.SnackBar(ft.Text("Accessory not found!"),
                                         bgcolor=self.danger_color)
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

        category_options = [
            ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}")
            for c in categories
        ]

        name_field = ft.TextField(label="Name *", value=accessory['name'],
                                  width=field_width, bgcolor=self.card_color)
        category_field = ft.Dropdown(
            label="Category", width=field_width, options=category_options,
            value=str(accessory['category_id']), bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity",
                                      value=str(accessory['quantity']),
                                      width=field_width, bgcolor=self.card_color)
        price_field = ft.TextField(label="Price",
                                   value=str(accessory['price']),
                                   width=field_width, bgcolor=self.card_color)
        quality_field = ft.Dropdown(
            label="Quality", width=field_width,
            options=[
                ft.dropdown.Option("New"), ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired"),
            ],
            value=accessory['quality'], bgcolor=self.card_color)
        location_field = ft.TextField(label="Location",
                                      value=accessory['location'] or "",
                                      width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes",
                                   value=accessory['notes'] or "",
                                   width=field_width, bgcolor=self.card_color,
                                   multiline=True, min_lines=2, max_lines=3)

        current_image_path = accessory['image_path'] if accessory['image_path'] else None
        has_current = current_image_path and os.path.exists(current_image_path) \
            if current_image_path else False

        image_status_text = ft.Text(
            "✓ Current image saved" if has_current else "No image",
            size=10, color=self.success_color if has_current else "#888888")
        selected_image_data = None

        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    selected_image_data = {'name': file.name,
                                           'data': file_data,
                                           'size': file.size}
                    image_status_text.value = f"✓ {file.name[:20]} ({file.size/1024:.0f}KB)"
                    image_status_text.color = self.success_color
                except:
                    image_status_text.value = "❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()

        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)

        def upload_image(e):
            image_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])

        upload_btn = ft.ElevatedButton(
            "📁 Upload New", on_click=upload_image, icon=ft.Icons.UPLOAD_FILE,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        image_row = ft.Row([upload_btn, image_status_text], spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)

        def save_uploaded_image():
            if selected_image_data:
                try:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"acc_{accessory_id}_{ts}{ext}"
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
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return

            final_image_path = current_image_path
            if selected_image_data:
                final_image_path = save_uploaded_image()

            selected_cat_id = int(category_field.value)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accessories
                    SET name=?, category_id=?, quantity=?, price=?, quality=?,
                        location=?, notes=?, image_path=?, updated_at=?
                    WHERE id=?
                ''', (
                    name_field.value, selected_cat_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    float(price_field.value) if price_field.value else 0,
                    quality_field.value, location_field.value,
                    notes_field.value, final_image_path,
                    now, accessory_id
                ))
                conn.commit()
                conn.close()
                close_dialog()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Updated: {name_field.value}"),
                    bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_accessories(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()

        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Accessory", size=16,
                        weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=18,
                              on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(),
                              expand=True),
                ft.FilledButton("Update", on_click=lambda e: update_accessory(),
                                style=ft.ButtonStyle(bgcolor=self.success_color),
                                expand=True),
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

    def open_edit_modal(self, page: ft.Page, material_id):
        """Edit material with image upload"""
        import os
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
            page.snack_bar = ft.SnackBar(ft.Text("Material not found!"),
                                         bgcolor=self.danger_color)
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

        category_options = [
            ft.dropdown.Option(str(c['id']), f"{c['icon']} {c['name']}")
            for c in categories
        ]

        name_field = ft.TextField(label="Name *", value=material['name'],
                                  width=field_width, bgcolor=self.card_color)
        category_field = ft.Dropdown(
            label="Category", width=field_width, options=category_options,
            value=str(material['category_id']), bgcolor=self.card_color)
        quantity_field = ft.TextField(label="Quantity",
                                      value=str(material['quantity']),
                                      width=field_width, bgcolor=self.card_color)
        size_field = ft.TextField(label="Size", value=material['size'] or "",
                                  width=field_width, bgcolor=self.card_color)
        length_field = ft.TextField(
            label="Length",
            value=str(material['length']) if material['length'] else "",
            width=field_width, bgcolor=self.card_color)
        quality_field = ft.Dropdown(
            label="Quality", width=field_width,
            options=[
                ft.dropdown.Option("New"), ft.dropdown.Option("Used"),
                ft.dropdown.Option("Damaged"), ft.dropdown.Option("Repaired"),
            ],
            value=material['quality'], bgcolor=self.card_color)
        location_field = ft.TextField(label="Location",
                                      value=material['location_ids'] or "",
                                      width=field_width, bgcolor=self.card_color)
        color_field = ft.TextField(label="Colors",
                                   value=material['colors'] or "",
                                   width=field_width, bgcolor=self.card_color)
        notes_field = ft.TextField(label="Notes",
                                   value=material['notes'] or "",
                                   width=field_width, bgcolor=self.card_color,
                                   multiline=True, min_lines=2, max_lines=3)

        def update_length(e):
            sv = size_field.value
            if sv:
                try:
                    if ' ' in sv and '/' in sv:
                        parts = sv.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_field.value = f"{whole + float(frac[0]) / float(frac[1]):.2f}"
                    elif '/' in sv:
                        frac = sv.split('/')
                        length_field.value = f"{float(frac[0]) / float(frac[1]):.2f}"
                    else:
                        length_field.value = f"{float(sv):.2f}"
                except:
                    length_field.value = sv
            else:
                length_field.value = ""
            page.update()

        size_field.on_change = update_length

        current_image_path = material['image_path'] if material['image_path'] else None
        has_current = current_image_path and os.path.exists(current_image_path) \
            if current_image_path else False

        image_status_text = ft.Text(
            "✓ Current image saved" if has_current else "No image",
            size=10, color=self.success_color if has_current else "#888888")
        selected_image_data = None

        def on_image_picked(e: ft.FilePickerResultEvent):
            nonlocal selected_image_data
            if e.files:
                file = e.files[0]
                try:
                    with open(file.path, 'rb') as f:
                        file_data = f.read()
                    selected_image_data = {'name': file.name,
                                           'data': file_data,
                                           'size': file.size}
                    image_status_text.value = f"✓ {file.name[:20]} ({file.size/1024:.0f}KB)"
                    image_status_text.color = self.success_color
                except:
                    image_status_text.value = "❌ Error reading image"
                    image_status_text.color = self.danger_color
                page.update()

        image_picker = ft.FilePicker(on_result=on_image_picked)
        page.overlay.append(image_picker)

        def upload_image(e):
            image_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp", "webp"])

        upload_btn = ft.ElevatedButton(
            "📁 Upload New", on_click=upload_image, icon=ft.Icons.UPLOAD_FILE,
            style=ft.ButtonStyle(bgcolor=self.accent_color, color=self.text_color))
        image_row = ft.Row([upload_btn, image_status_text], spacing=8,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)

        def save_uploaded_image():
            if selected_image_data:
                try:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    ext = os.path.splitext(selected_image_data['name'])[1].lower()
                    new_filename = f"img_{material_id}_{ts}{ext}"
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
                page.snack_bar = ft.SnackBar(ft.Text("Please enter a name!"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()
                return

            final_image_path = current_image_path
            if selected_image_data:
                final_image_path = save_uploaded_image()

            selected_cat_id = int(category_field.value)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            sv = size_field.value
            length_val = None
            if sv:
                try:
                    if ' ' in sv and '/' in sv:
                        parts = sv.split()
                        whole = float(parts[0])
                        frac = parts[1].split('/')
                        length_val = whole + float(frac[0]) / float(frac[1])
                    elif '/' in sv:
                        frac = sv.split('/')
                        length_val = float(frac[0]) / float(frac[1])
                    else:
                        length_val = float(sv)
                except:
                    length_val = None

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE materials
                    SET name=?, category_id=?, quantity=?, quality=?, location_ids=?,
                        size=?, length=?, colors=?, notes=?, image_path=?, updated_at=?
                    WHERE id=?
                ''', (
                    name_field.value, selected_cat_id,
                    int(quantity_field.value) if quantity_field.value else 0,
                    quality_field.value, location_field.value,
                    size_field.value, length_val,
                    color_field.value, notes_field.value,
                    final_image_path, now, material_id
                ))
                conn.commit()
                conn.close()
                close_dialog()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Updated: {name_field.value}"),
                    bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                self.show_materials_screen(page)
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"),
                                             bgcolor=self.danger_color)
                page.snack_bar.open = True
                page.update()

        dialog_content = ft.Column([
            ft.Row([
                ft.Text("Edit Material", size=16,
                        weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=18,
                              on_click=lambda e: close_dialog()),
            ]),
            ft.Divider(height=1),
            scroll_fields,
            ft.Divider(height=1),
            ft.Row([
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(),
                              expand=True),
                ft.FilledButton("Update", on_click=lambda e: update_material(),
                                style=ft.ButtonStyle(bgcolor=self.success_color),
                                expand=True),
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

    def show_barcode_dialog(self, page: ft.Page, item):
        """Show barcode dialog with copy + print buttons"""
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
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✓ Barcode copied: {barcode_text}"),
                    bgcolor=self.success_color, duration=2000)
                page.snack_bar.open = True
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Failed to copy: {str(ex)}"),
                    bgcolor=self.danger_color, duration=2000)
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
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html',
                                                    delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            webbrowser.open(f'file://{temp_file.name}')
            close_dialog(e)

        dialog_content = ft.Column([
            ft.Text(item_name, size=16, weight=ft.FontWeight.BOLD),
            ft.Text(item_type, size=12, color="#888888"),
            ft.Container(height=10),
            ft.Image(src=barcode_url, width=300, height=100,
                     fit=ft.ImageFit.CONTAIN),
            ft.Text(barcode_text, size=16, weight=ft.FontWeight.BOLD,
                    color=self.accent_color),
            ft.Text("Scan this barcode with your camera", size=10, color="#888888"),
        ], spacing=8, horizontal_alignment=ft.CrossAxisalignment.CENTER)

        dialog = ft.AlertDialog(
            title=ft.Text("Barcode", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(content=dialog_content,
                                 width=350, height=380, padding=15),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
                ft.TextButton("📋 Copy", on_click=copy_to_clipboard),
                ft.FilledButton("🖨️ Print", on_click=print_barcode,
                                style=ft.ButtonStyle(bgcolor=self.accent_color)),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()


if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
