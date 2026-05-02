"""
Camera Barcode Scanner with proper close functionality
"""

import cv2
import time
from threading import Thread
from pyzbar.pyzbar import decode

class CameraScanner:
    def __init__(self):
        self.cap = None
        self.last_code = None
        self.running = False
        self.scanned_result = None
        self.callback = None
        self.detected_barcode = None
        self.scanning_complete = False
        
    def start_scanning(self, callback=None):
        """Start camera with live preview window"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            return False, "Cannot open camera. Please check your camera."
        
        # Set camera resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.callback = callback
        self.running = True
        self.scanned_result = None
        
        # Start scanning thread
        thread = Thread(target=self._scan_loop)
        thread.daemon = True
        thread.start()
        return True, "Camera started - Look for camera window"
    
    def _scan_loop(self):
        """Scan loop with live preview"""
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Create a copy for display
            display_frame = frame.copy()
            
            # Decode barcodes
            decoded_objects = decode(frame)
            
            for obj in decoded_objects:
                barcode_data = obj.data.decode('utf-8')
                
                # Draw green rectangle
                points = obj.rect
                (x, y, w, h) = (points.left, points.top, points.width, points.height)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                cv2.putText(display_frame, barcode_data, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Only trigger on new barcode
                if barcode_data != self.last_code:
                    self.last_code = barcode_data
                    self.scanned_result = barcode_data
                    
                    if self.callback:
                        self.callback(barcode_data)
                    
                    time.sleep(0.5)
            
            # Add instructions
            cv2.putText(display_frame, "Press 'Q' or 'ESC' to quit", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(display_frame, "Press 'S' to stop scanning", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            if self.last_code:
                cv2.putText(display_frame, f"Last: {self.last_code}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Show frame
            cv2.imshow('Barcode Scanner - Point camera at barcode', display_frame)
            
            # Check for quit key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # Q or ESC
                break
            elif key == ord('s'):  # S to stop
                break
        
        self.stop()
    
    def stop(self):
        """Stop camera and clean up"""
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
    
    def get_scanned_code(self):
        """Return the last scanned barcode"""
        return self.scanned_result