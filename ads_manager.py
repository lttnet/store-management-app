"""
Ads Manager - Google AdMob integration
Banner + interstitial ads
"""

import flet as ft
import flet_ads as fta


# ============================================================
# REPLACE WITH YOUR REAL ADMOB IDs
# ============================================================
# While testing, keep TEST IDs below — they don't earn money
# but they work without a real AdMob account.
#
# After testing and before publishing:
#   1. Get your real IDs from https://admob.google.com
#   2. Replace the two lines below
#   3. Rebuild APK

# TEST IDs (safe to use during development)
BANNER_ID = "ca-app-pub-3940256099942544/6300978111"
INTERSTITIAL_ID = "ca-app-pub-3940256099942544/1033173712"

# REAL IDs (uncomment and fill when ready for production)
# BANNER_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111"
# INTERSTITIAL_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222"


class AdsManager:
    """Manages AdMob banner + interstitial ads"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.banner_ad = None
        self.interstitial_ad = None
        self.ads_enabled = True
        self.interstitial_counter = 0
        self.interstitial_frequency = 5  # every 5 nav taps

        self._init_ads()

    def _init_ads(self):
        try:
            # ---- Banner ----
            try:
                self.banner_ad = fta.BannerAd(
                    unit_id=BANNER_ID,
                    on_error=lambda e: print(f"Banner error: {e.data}"),
                )
                print("✅ Banner ad ready")
            except Exception as e:
                print(f"Banner init error: {e}")
                self.banner_ad = None

            # ---- Interstitial ----
            try:
                self.interstitial_ad = fta.InterstitialAd(
                    unit_id=INTERSTITIAL_ID,
                    on_error=lambda e: print(f"Interstitial error: {e.data}"),
                    on_load=lambda e: print("Interstitial loaded"),
                    on_close=lambda e: self._on_inter_close(),
                )
                self.interstitial_ad.load()
                print("✅ Interstitial ad ready")
            except Exception as e:
                print(f"Interstitial init error: {e}")
                self.interstitial_ad = None

        except Exception as e:
            print(f"⚠️ Ads init failed: {e}")
            self.ads_enabled = False

    def _on_inter_close(self):
        try:
            if self.interstitial_ad:
                self.interstitial_ad.load()
        except:
            pass

    def show_interstitial(self):
        """Call on every navigation tap"""
        if not self.ads_enabled or not self.interstitial_ad:
            return

        self.interstitial_counter += 1
        if self.interstitial_counter >= self.interstitial_frequency:
            self.interstitial_counter = 0
            try:
                self.interstitial_ad.show()
                print("📺 Interstitial shown")
            except Exception as e:
                print(f"Interstitial show error: {e}")

    def banner_widget(self):
        """Returns banner widget or empty container"""
        if not self.ads_enabled or not self.banner_ad:
            return ft.Container(height=0)
        return ft.Container(
            content=self.banner_ad,
            alignment=ft.Alignment.CENTER,
            height=50,
        )