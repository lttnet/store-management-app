"""
Store Management App - MOBILE FIXED VERSION
"""
import sys
import hashlib
import warnings
import traceback
import sqlite3
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
from database import init_database
from managers.material_manager import MaterialManager
from managers.accessory_manager import AccessoryManager
from managers.user_manager import UserManager

import requests
import os
import json
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
        
        self.quality_colors = {
            "New": "#2E7D32",
            "Used": "#F57C00",
            "Damaged": "#FF5252",
            "Repaired": "#1976D2",
        }
    
    # ============ REQUIRED METHODS FOR MOBILE ============
    
    def get_device_id(self):
        """Get a unique device ID for trial tracking"""
        import uuid
        import os
        
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            device_file = os.path.join(base_dir, ".device_id")
            
            if os.path.exists(device_file):
                with open(device_file, 'r') as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id
            
            device_id = str(uuid.uuid4())
            try:
                with open(device_file, 'w') as f:
                    f.write(device_id)
            except:
                pass
            
            return device_id
            
        except Exception as e:
            print(f"Error getting device ID: {e}")
            import time
            return f"device_{int(time.time())}"
    
    def get_saved_user(self):
        """Get saved user from session"""
        import json
        import os
        
        try:
            session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
            if not os.path.exists(session_file):
                return None
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            if not session_data:
                return None
            
            return {
                'email': session_data.get('email', 'trial@user.com'),
                'trial': session_data.get('trial', True),
                'activated': session_data.get('activated', False),
                'days_left': session_data.get('days_left', 30),
                'device_id': session_data.get('device_id', self.get_device_id())
            }
            
        except Exception as e:
            print(f"Error getting saved user: {e}")
            return None
    
    def has_used_app_before(self):
        """Check if user has used app before"""
        import os
        session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
        return os.path.exists(session_file)
    
    def save_user_session(self, user_dict):
        """Save user session for auto-login"""
        import json
        import os
        
        try:
            session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
            
            session_data = {
                'email': user_dict.get('email', 'trial@user.com'),
                'trial': user_dict.get('trial', True),
                'activated': user_dict.get('activated', False),
                'days_left': user_dict.get('days_left', 30),
                'device_id': user_dict.get('device_id', self.get_device_id())
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
            
            print(f"✅ Session saved for: {session_data['email']}")
            return True
            
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def save_trial_info(self, email):
        """Save trial info to database"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime, timedelta
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trial_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    trial_start TEXT,
                    trial_end TEXT,
                    activated INTEGER DEFAULT 0,
                    activation_code TEXT
                )
            ''')
            
            cursor.execute("DELETE FROM trial_info")
            
            trial_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            trial_end = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO trial_info (email, trial_start, trial_end)
                VALUES (?, ?, ?)
            ''', (email, trial_start, trial_end))
            
            conn.commit()
            conn.close()
            print(f"✅ Trial started for {email}")
            
        except Exception as e:
            print(f"Save trial error: {e}")
    
    def check_trial_status(self):
        """Check if trial is active and days left"""
        import sqlite3
        from database import DB_PATH
        from datetime import datetime
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT email, trial_start, trial_end FROM trial_info LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, 0
            
            email, trial_start, trial_end = result
            
            if not trial_end:
                return False, 0
            
            trial_end_date = datetime.strptime(trial_end, '%Y-%m-%d %H:%M:%S')
            days_left = (trial_end_date - datetime.now()).days
            
            if days_left <= 0:
                return False, 0
            
            return True, days_left
            
        except Exception as e:
            print(f"Check trial error: {e}")
            return False, 0
    
    def ensure_admin_user(self):
        """Ensure admin user exists"""
        import sqlite3
        import hashlib
        from database import DB_PATH
        from datetime import datetime
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                print("❌ Users table doesn't exist!")
                conn.close()
                return
            
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            if count > 0:
                conn.close()
                print(f"✅ Users exist: {count} users")
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
            
            hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, company_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('Administrator', 'admin@store.com', hashed_password, 'admin', company_id,
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            print("✅ Created admin user: admin@store.com / admin123")
            
        except Exception as e:
            print(f"Error ensuring admin user: {e}")
    
    def is_mobile(self, page: ft.Page):
        """Check if running on mobile device"""
        return page.width < 800 if page.width else False
    
    def dict_list(self, rows):
        """Convert sqlite3.Row to dict"""
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
        """Get color for quality badge"""
        colors = {
            "New": "#2E7D32",
            "Used": "#F57C00",
            "Damaged": "#FF5252",
            "Repaired": "#1976D2"
        }
        return colors.get(quality, "#888888")

    # ============ BOTTOM NAVIGATION ============
    
    def create_bottom_nav(self, page: ft.Page):
        """Create bottom navigation bar for mobile"""
        
        nav_items = [
            (ft.icons.DASHBOARD, "Home", "dashboard"),
            (ft.icons.INVENTORY, "Materials", "materials"),
            (ft.icons.BUILD, "Parts", "accessories"),
            (ft.icons.QR_CODE_SCANNER, "Scan", "barcode_scanner"),
            (ft.icons.LIST_ALT, "Inventory", "inventory"),
            (ft.icons.PEOPLE, "Users", "users"),
            (ft.icons.SETTINGS, "Settings", "settings"),
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
        
        return ft.NavigationBar(
            destinations=[
                ft.NavigationDestination(icon=icon, label=label)
                for icon, label, _ in nav_items
            ],
            on_change=navigate,
            height=65,
            bgcolor=self.sidebar_color,
        )

    # ============ DASHBOARD - FIXED FOR MOBILE ============
    
    def show_dashboard(self, page: ft.Page):
        """Dashboard with trial banner - FIXED FOR MOBILE"""
        try:
            page.controls.clear()
            
            is_mobile = self.is_mobile(page)
            
            # Get user info
            user = self.current_user or {}
            is_activated = user.get('activated', False)
            is_trial = user.get('trial', True)
            days_left = user.get('days_left', 30)
            
            # Check if trial expired
            if not is_activated:
                trial_active, days_left = self.check_trial_status()
                if not trial_active and not is_activated:
                    days_left = 0
            
            # Get data
            try:
                materials = self.dict_list(MaterialManager.get_all())
                accessories = self.dict_list(AccessoryManager.get_all())
            except:
                materials = []
                accessories = []
            
            total_materials = len(materials)
            total_accessories = len(accessories)
            total_items = total_materials + total_accessories
            total_stock = sum(m.get('quantity', 0) for m in materials) + sum(a.get('quantity', 0) for a in accessories)
            
            # Navigation
            if is_mobile:
                nav = self.create_bottom_nav(page)
                sidebar = None
            else:
                sidebar = self.create_sidebar(page)
                nav = None
            
            # Main column
            main_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
            
            # ===== TOP BANNER =====
            if is_activated:
                top_banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="#4CAF50", size=24),
                        ft.Text("✅ Full Version Activated", size=14, weight=ft.FontWeight.BOLD, color="#4CAF50"),
                    ], spacing=8),
                    padding=10,
                    bgcolor="#1A3A1A",
                    border_radius=8,
                )
            elif days_left > 0:
                days_color = self.danger_color if days_left <= 5 else "#FF9800"
                emoji = "⚠️" if days_left <= 5 else "🚀"
                top_banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.TIMER, color="#FF9800", size=24),
                        ft.Column([
                            ft.Text(f"{emoji} Free Trial: {days_left} days", size=14, weight=ft.FontWeight.BOLD, color="#FF9800"),
                            ft.Text("Full access for 30 days", size=10, color="#888888"),
                        ], spacing=1, expand=True),
                        ft.ElevatedButton(
                            "Activate",
                            on_click=lambda e: self.show_activation_dialog(page),
                            style=ft.ButtonStyle(bgcolor="#4CAF50", color="white"),
                            height=36,
                        ),
                    ], spacing=8),
                    padding=10,
                    bgcolor="#2C2C2C",
                    border_radius=8,
                )
            else:
                top_banner = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.WARNING, color=self.danger_color, size=24),
                        ft.Text("⚠️ Trial Expired - Activate Now", size=14, weight=ft.FontWeight.BOLD, color=self.danger_color, expand=True),
                        ft.ElevatedButton(
                            "Activate",
                            on_click=lambda e: self.show_activation_dialog(page),
                            style=ft.ButtonStyle(bgcolor="#FF9800", color="white"),
                            height=36,
                        ),
                    ], spacing=8),
                    padding=10,
                    bgcolor="#3A1A1A",
                    border_radius=8,
                )
            
            main_column.controls.append(top_banner)
            
            # ===== HEADER =====
            header_row = ft.Row([
                ft.Text("📊 Dashboard", size=20 if is_mobile else 24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(
                    icon=ft.icons.REFRESH,
                    icon_size=20,
                    icon_color="#888888",
                    on_click=lambda e: self.show_dashboard(page),
                ),
            ])
            main_column.controls.append(header_row)
            main_column.controls.append(ft.Divider(height=1, color="#3C3C3C"))
            main_column.controls.append(ft.Container(height=5))
            
            # ===== STATS CARDS =====
            stats_row = ft.Row([
                self._create_stat_card("📦", str(total_items), "Items"),
                self._create_stat_card("📊", str(total_stock), "Stock"),
                self._create_stat_card("📈", str(total_items), "Total"),
            ], spacing=8)
            main_column.controls.append(stats_row)
            main_column.controls.append(ft.Container(height=5))
            
            # ===== QUICK ACTIONS =====
            main_column.controls.append(ft.Text("⚡ Quick Actions", size=16, weight=ft.FontWeight.BOLD))
            
            main_column.controls.append(
                ft.Row([
                    ft.ElevatedButton("📦 Add Material", on_click=lambda e: self.open_add_modal(page), expand=True, height=40),
                    ft.ElevatedButton("🔧 Add Part", on_click=lambda e: self.open_add_accessory_modal(page), expand=True, height=40),
                ], spacing=8)
            )
            main_column.controls.append(
                ft.Row([
                    ft.ElevatedButton("📷 Scan", on_click=lambda e: self.show_barcode_scanner(page), expand=True, height=40),
                    ft.ElevatedButton("📊 Inventory", on_click=lambda e: self.show_inventory(page), expand=True, height=40),
                ], spacing=8)
            )
            
            # ===== ACTIVATION BUTTON (if not activated) =====
            if not is_activated:
                main_column.controls.append(
                    ft.ElevatedButton(
                        "🔑 Activate Full Version",
                        on_click=lambda e: self.show_activation_dialog(page),
                        expand=True,
                        style=ft.ButtonStyle(bgcolor="#FF9800", color="white"),
                        height=40,
                    )
                )
            
            main_column.controls.append(ft.Container(height=10))
            
            # ===== RECENT MATERIALS =====
            main_column.controls.append(ft.Text("📦 Recent Materials", size=15, weight=ft.FontWeight.BOLD))
            
            recent_mats = materials[:5] if materials else []
            if recent_mats:
                for m in recent_mats:
                    main_column.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text("📦", size=16),
                                ft.Text(m.get('name', 'N/A'), size=13, expand=True),
                                ft.Text(f"Qty: {m.get('quantity', 0)}", size=12),
                            ]),
                            padding=8,
                            bgcolor="#2C2C2C",
                            border_radius=6,
                            margin=ft.margin.only(bottom=3),
                        )
                    )
            else:
                main_column.controls.append(
                    ft.Container(
                        content=ft.Text("No materials yet. Click 'Add Material'!", size=11, color="#888888"),
                        padding=8,
                        bgcolor="#2C2C2C",
                        border_radius=6,
                    )
                )
            
            main_column.controls.append(ft.Container(height=10))
            
            # ===== RECENT ACCESSORIES =====
            main_column.controls.append(ft.Text("🔧 Recent Accessories", size=15, weight=ft.FontWeight.BOLD))
            
            recent_accs = accessories[:5] if accessories else []
            if recent_accs:
                for a in recent_accs:
                    price = a.get('price', 0)
                    price_text = f"${price:.2f}" if price else ""
                    main_column.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text("🔧", size=16),
                                ft.Text(a.get('name', 'N/A'), size=13, expand=True),
                                ft.Text(f"Qty: {a.get('quantity', 0)}", size=12),
                                ft.Text(price_text, size=11, color="#4CAF50") if price_text else ft.Container(),
                            ]),
                            padding=8,
                            bgcolor="#2C2C2C",
                            border_radius=6,
                            margin=ft.margin.only(bottom=3),
                        )
                    )
            else:
                main_column.controls.append(
                    ft.Container(
                        content=ft.Text("No accessories yet. Click 'Add Part'!", size=11, color="#888888"),
                        padding=8,
                        bgcolor="#2C2C2C",
                        border_radius=6,
                    )
                )
            
            # ===== FOOTER =====
            main_column.controls.append(ft.Divider())
            main_column.controls.append(ft.Container(height=5))
            
            status_text = "✅ Full Version" if is_activated else f"🚀 Trial: {days_left} days" if days_left > 0 else "⚠️ Expired"
            status_color = "#4CAF50" if is_activated else "#FF9800" if days_left > 0 else self.danger_color
            
            footer_row = ft.Row([
                ft.Text(f"📱 {status_text}", size=10, color=status_color),
                ft.Container(expand=True),
                ft.Text("v2.0.0", size=10, color="#888888"),
            ])
            main_column.controls.append(footer_row)
            
            # ===== BOTTOM SPACING =====
            if is_mobile:
                main_column.controls.append(ft.Container(height=70))
            
            # ===== WRAP AND DISPLAY =====
            scroll_container = ft.Container(
                content=main_column,
                expand=True,
                padding=12 if is_mobile else 20,
            )
            
            scrollable = ft.Container(
                content=ft.Column([scroll_container], scroll=ft.ScrollMode.AUTO, expand=True),
                expand=True,
            )
            
            if is_mobile and nav:
                page.add(ft.Column([scrollable, nav], spacing=0, expand=True))
            else:
                page.add(ft.Row([sidebar, scrollable], spacing=0, expand=True))
            
            self.current_view = "dashboard"
            page.update()
            
        except Exception as e:
            print(f"Dashboard error: {e}")
            import traceback
            traceback.print_exc()
            # Show error on screen
            page.controls.clear()
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Text("❌ Dashboard Error", size=20, color="red"),
                        ft.Text(str(e), size=12, color="white"),
                        ft.ElevatedButton("Retry", on_click=lambda e: self.show_dashboard(page)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
            page.update()

    def _create_stat_card(self, icon, value, label):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(icon, size=18),
                ft.Text(value, size=20, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=10, color="#CCCCCC"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            padding=8,
            bgcolor=self.accent_color,
            border_radius=8,
            expand=True,
        )

    # ============ PLACEHOLDER METHODS (to avoid errors) ============
    
    def show_activation_dialog(self, page):
        page.snack_bar = ft.SnackBar(ft.Text("Activation feature coming soon"), bgcolor=self.warning_color)
        page.snack_bar.open = True
        page.update()
    
    def open_add_modal(self, page):
        page.snack_bar = ft.SnackBar(ft.Text("Add Material feature coming soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()
    
    def open_add_accessory_modal(self, page):
        page.snack_bar = ft.SnackBar(ft.Text("Add Part feature coming soon"), bgcolor=self.accent_color)
        page.snack_bar.open = True
        page.update()
    
    def show_materials_screen(self, page):
        page.controls.clear()
        is_mobile = self.is_mobile(page)
        nav = self.create_bottom_nav(page) if is_mobile else None
        
        content = ft.Container(
            content=ft.Column([
                ft.Text("📦 Materials", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Materials management coming soon...", size=14, color="#888888"),
                ft.Container(height=20),
                ft.ElevatedButton("Back to Dashboard", on_click=lambda e: self.show_dashboard(page)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            alignment=ft.alignment.center,
        )
        
        if is_mobile and nav:
            page.add(ft.Column([content, nav], spacing=0, expand=True))
        else:
            page.add(content)
        page.update()
    
    def show_accessories(self, page):
        page.controls.clear()
        is_mobile = self.is_mobile(page)
        nav = self.create_bottom_nav(page) if is_mobile else None
        
        content = ft.Container(
            content=ft.Column([
                ft.Text("🔧 Accessories", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Accessories management coming soon...", size=14, color="#888888"),
                ft.Container(height=20),
                ft.ElevatedButton("Back to Dashboard", on_click=lambda e: self.show_dashboard(page)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            alignment=ft.alignment.center,
        )
        
        if is_mobile and nav:
            page.add(ft.Column([content, nav], spacing=0, expand=True))
        else:
            page.add(content)
        page.update()
    
    def show_barcode_scanner(self, page):
        page.controls.clear()
        is_mobile = self.is_mobile(page)
        nav = self.create_bottom_nav(page) if is_mobile else None
        
        content = ft.Container(
            content=ft.Column([
                ft.Text("📷 Barcode Scanner", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Scan barcodes with your camera", size=14),
                ft.Icon(ft.icons.QR_CODE_SCANNER, size=80, color=self.accent_color),
                ft.Text("Feature coming soon...", size=12, color="#888888"),
                ft.Container(height=20),
                ft.ElevatedButton("Back to Dashboard", on_click=lambda e: self.show_dashboard(page)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            alignment=ft.alignment.center,
        )
        
        if is_mobile and nav:
            page.add(ft.Column([content, nav], spacing=0, expand=True))
        else:
            page.add(content)
        page.update()
    
    def show_inventory(self, page):
        page.controls.clear()
        is_mobile = self.is_mobile(page)
        nav = self.create_bottom_nav(page) if is_mobile else None
        
        content = ft.Container(
            content=ft.Column([
                ft.Text("📋 Inventory", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Inventory management coming soon...", size=14, color="#888888"),
                ft.Container(height=20),
                ft.ElevatedButton("Back to Dashboard", on_click=lambda e: self.show_dashboard(page)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            alignment=ft.alignment.center,
        )
        
        if is_mobile and nav:
            page.add(ft.Column([content, nav], spacing=0, expand=True))
        else:
            page.add(content)
        page.update()
    
    def show_users(self, page):
        page.controls.clear()
        is_mobile = self.is_mobile(page)
        nav = self.create_bottom_nav(page) if is_mobile else None
        
        content = ft.Container(
            content=ft.Column([
                ft.Text("👥 Users", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("User management coming soon...", size=14, color="#888888"),
                ft.Container(height=20),
                ft.ElevatedButton("Back to Dashboard", on_click=lambda e: self.show_dashboard(page)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            alignment=ft.alignment.center,
        )
        
        if is_mobile and nav:
            page.add(ft.Column([content, nav], spacing=0, expand=True))
        else:
            page.add(content)
        page.update()
    
    def show_settings(self, page):
        page.controls.clear()
        is_mobile = self.is_mobile(page)
        nav = self.create_bottom_nav(page) if is_mobile else None
        
        content = ft.Container(
            content=ft.Column([
                ft.Text("⚙️ Settings", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Settings coming soon...", size=14, color="#888888"),
                ft.Container(height=20),
                ft.ElevatedButton("Back to Dashboard", on_click=lambda e: self.show_dashboard(page)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            alignment=ft.alignment.center,
        )
        
        if is_mobile and nav:
            page.add(ft.Column([content, nav], spacing=0, expand=True))
        else:
            page.add(content)
        page.update()
    
    def create_sidebar(self, page: ft.Page):
        """Create sidebar navigation for desktop"""
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([ft.Text("🏪", size=28), ft.Text("Store Manager", size=18, weight=ft.FontWeight.BOLD)], 
                                  alignment=ft.MainAxisAlignment.CENTER, spacing=8),
                    padding=20,
                ),
                ft.Divider(),
                ft.Column([
                    ft.Container(content=ft.Text("📊 Dashboard", size=14), padding=12, on_click=lambda e: self.show_dashboard(page)),
                    ft.Container(content=ft.Text("📦 Materials", size=14), padding=12, on_click=lambda e: self.show_materials_screen(page)),
                    ft.Container(content=ft.Text("🔧 Accessories", size=14), padding=12, on_click=lambda e: self.show_accessories(page)),
                    ft.Container(content=ft.Text("📷 Scan", size=14), padding=12, on_click=lambda e: self.show_barcode_scanner(page)),
                    ft.Container(content=ft.Text("📋 Inventory", size=14), padding=12, on_click=lambda e: self.show_inventory(page)),
                    ft.Container(content=ft.Text("👥 Users", size=14), padding=12, on_click=lambda e: self.show_users(page)),
                    ft.Container(content=ft.Text("⚙️ Settings", size=14), padding=12, on_click=lambda e: self.show_settings(page)),
                ], spacing=4),
                ft.Container(expand=True),
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        ft.Text("User: Admin", size=12, color="#888888"),
                        ft.Text("ADMIN", size=11, weight=ft.FontWeight.BOLD),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    padding=15,
                ),
            ], spacing=0),
            width=200,
            bgcolor=self.sidebar_color,
            border_radius=ft.border_radius.only(top_right=10, bottom_right=10),
        )

    # ============ MAIN ENTRY POINT ============
    
    def main(self, page: ft.Page):
        """Main entry point - Show dashboard directly"""
        try:
            # Page settings
            page.title = "Store Management System"
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = self.bg_color
            page.padding = 0
            page.spacing = 0
            
            self.page_ref = page
            
            # Initialize database
            init_database()
            
            # Ensure admin user exists
            self.ensure_admin_user()
            
            # Check for saved user
            saved_user = self.get_saved_user()
            
            if saved_user:
                print(f"🔐 Found saved user: {saved_user.get('email')}")
                self.current_user = saved_user
                self.show_dashboard(page)
                page.update()
                return
            
            # Check trial status
            trial_active, days_left = self.check_trial_status()
            
            if trial_active:
                print(f"🚀 Trial active: {days_left} days remaining")
                device_id = self.get_device_id()
                self.current_user = {
                    'email': 'trial@user.com',
                    'trial': True,
                    'activated': False,
                    'days_left': days_left,
                    'device_id': device_id
                }
                self.save_user_session(self.current_user)
                self.show_dashboard(page)
                page.update()
                return
            
            # First time user - start trial
            print("🆕 First time user - starting trial")
            device_id = self.get_device_id()
            self.current_user = {
                'email': 'trial@user.com',
                'trial': True,
                'activated': False,
                'days_left': 30,
                'device_id': device_id
            }
            self.save_user_session(self.current_user)
            self.save_trial_info('trial@user.com')
            
            # Show dashboard
            self.show_dashboard(page)
            page.update()
            print("✅ App started successfully")
            
        except Exception as e:
            print(f"❌ App startup error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                page.controls.clear()
                page.add(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("❌ App Error", size=24, color="red"),
                            ft.Text(str(e), size=14, color="white"),
                            ft.ElevatedButton("Retry", on_click=lambda e: self.main(page)),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                )
                page.update()
            except:
                pass


# ============ RUN APP ============
if __name__ == "__main__":
    app = StoreApp()
    ft.app(target=app.main)
