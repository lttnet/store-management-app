import flet as ft

def main(page: ft.Page):
    page.title = "Test App"
    page.add(ft.Text("This is a test - if you see this, the build works!"))

ft.app(target=main)
