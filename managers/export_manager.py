"""
Export Manager - Complete version
"""

import csv
import json
import os
from datetime import datetime

class ExportManager:
    
    @staticmethod
    def ensure_export_folder():
        import os
        folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'exports')
        if not os.path.exists(folder):
            os.makedirs(folder)
        return folder
    
    @staticmethod
    def get_connection():
        import os
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from database import get_db_connection
        return get_db_connection()
    
    @staticmethod
    def export_low_stock_report(threshold=10):
        folder = ExportManager.ensure_export_folder()
        conn = ExportManager.get_connection()
        
        materials = conn.execute('SELECT * FROM materials WHERE quantity <= ?', (threshold,)).fetchall()
        accessories = conn.execute('SELECT * FROM accessories WHERE quantity <= ?', (threshold,)).fetchall()
        conn.close()
        
        filename = f"low_stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(folder, filename)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'threshold': threshold,
            'materials': [dict(m) for m in materials],
            'accessories': [dict(a) for a in accessories],
            'summary': {
                'total_materials': len(materials),
                'total_accessories': len(accessories),
                'total_low_stock': len(materials) + len(accessories)
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filepath
    
    @staticmethod
    def export_full_inventory():
        folder = ExportManager.ensure_export_folder()
        conn = ExportManager.get_connection()
        
        materials = conn.execute('SELECT * FROM materials ORDER BY name').fetchall()
        accessories = conn.execute('SELECT * FROM accessories ORDER BY name').fetchall()
        
        material_stats = conn.execute('SELECT COUNT(*) as total, SUM(quantity) as total_qty FROM materials').fetchone()
        accessory_stats = conn.execute('SELECT COUNT(*) as total, SUM(quantity) as total_qty FROM accessories').fetchone()
        conn.close()
        
        filename = f"full_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(folder, filename)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'materials': {
                    'total_items': material_stats[0] or 0,
                    'total_quantity': material_stats[1] or 0
                },
                'accessories': {
                    'total_items': accessory_stats[0] or 0,
                    'total_quantity': accessory_stats[1] or 0
                },
                'total_items': (material_stats[0] or 0) + (accessory_stats[0] or 0),
                'total_quantity': (material_stats[1] or 0) + (accessory_stats[1] or 0)
            },
            'materials': [dict(m) for m in materials],
            'accessories': [dict(a) for a in accessories]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filepath