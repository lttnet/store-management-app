"""
Ads Manager - Google AdMob integration
Banner + interstitial ads for flet-ads==0.1.0 (Flet 0.28.3)
"""

import flet as ft

try:
    from flet_ads import BannerAd, InterstitialAd
    ADS_OK = True
except ImportError as e:
    print(f"⚠️ flet_ads not available: {e}")
    ADS_OK = False

# TEST IDs (safe during development)
BANNER_ID = "ca-app-pub-3940256099942544/6300978111"
INTERSTITIAL_ID = "ca-app-pub-3940256099942544/1033173712"

# REAL IDs (uncomment when ready for production)
# BANNER_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/1111111111"
# INTERSTITIAL_ID = "ca-app-pub-XXXXXXXXXXXXXXXX/2222222222"


class AdsManager:
    def __init__(self, page: ft.Page):
        self.page = page
        self.banner_ad = None
        self.interstitial_ad = None
        self.ads_enabled = True
        self.interstitial_counter = 0
        self.interstitial_frequency = 5

        self._init_ads()

    def _init_ads(self):
        if not ADS_OK:
            self.ads_enabled = False
            return

        # ---- Banner ----
        try:
            self.banner_ad = BannerAd(
                unit_id=BANNER_ID,
                on_error=lambda e: print(f"Banner error: {e.data}"),
            )
            print("✅ Banner ad ready")
        except Exception as e:
            print(f"Banner init error: {e}")
            self.banner_ad = None

        # ---- Interstitial ----
        self._create_interstitial()

    def _create_interstitial(self):
        """Create a new interstitial ad and attach it to the page overlay."""
        try:
            self.interstitial_ad = InterstitialAd(
                unit_id=INTERSTITIAL_ID,
                on_error=lambda e: print(f"Interstitial error: {e.data}"),
                on_load=lambda e: print("Interstitial loaded"),
                on_close=self._on_inter_close,
            )
            # CRITICAL: Attach to overlay so .show() can work
            self.page.overlay.append(self.interstitial_ad)
            self.page.update()
            print("✅ Interstitial ad ready")
        except Exception as e:
            print(f"Interstitial init error: {e}")
            self.interstitial_ad = None

    def _on_inter_close(self):
        """When the ad is closed, remove it and create a fresh one for next time."""
        try:
            if self.interstitial_ad in self.page.overlay:
                self.page.overlay.remove(self.interstitial_ad)
            # Create a new instance for the next show
            self._create_interstitial()
        except Exception as e:
            print(f"Error handling interstitial close: {e}")

    def show_interstitial(self):
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
        if not self.ads_enabled or not self.banner_ad:
            return ft.Container(height=0)

        # Only render on mobile
        try:
            if self.page.platform not in (
                ft.PagePlatform.ANDROID,
                ft.PagePlatform.IOS,
            ):
                return ft.Container(height=0)
        except Exception:
            return ft.Container(height=0)

        try:
            return ft.Container(
                content=self.banner_ad,
                alignment=ft.alignment.center,
                height=50,
            )
        except Exception as e:
            print(f"Banner widget error: {e}")
            return ft.Container(height=0)
