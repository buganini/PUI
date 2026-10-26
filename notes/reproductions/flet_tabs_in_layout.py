"""Compare Tabs under bounded and unbounded horizontal constraints in Flet 1.0.4.

Run: python notes/reproductions/flet_tabs_in_layout.py
Resize the window and inspect the native size-change reports in the terminal.
The non-expanding Column intentionally leaves its Tabs width unbounded.
"""
import flet as ft


def report_size(name):
    def changed(event):
        print(f'{name}: width={event.width}, height={event.height}', flush=True)
    return changed


def tabs(name):
    return ft.Tabs(
        length=2,
        expand=True,
        content=ft.Column(expand=True, controls=[
            ft.TabBar(tabs=[ft.Tab(label='First'), ft.Tab(label='Second')]),
            ft.TabBarView(expand=True, controls=[
                ft.Text('Content 1'),
                ft.Text('Content 2'),
            ]),
        ]),
        on_size_change=report_size(f'{name}.tabs'),
    )


def main(page: ft.Page):
    page.title = 'Flet Tabs: bounded vs unbounded width'
    page.window.width = 800
    page.window.height = 600
    # Both outer Rows get equal space. Only the left inner Column is expanded
    # horizontally; expanding Tabs inside a Column controls its vertical axis.
    page.add(ft.Row(expand=True, controls=[
        ft.Row(expand=1, controls=[
            ft.Column(expand=1, controls=[
                ft.Text('Column: expand=1'),
                tabs('bounded'),
            ], on_size_change=report_size('bounded.column')),
        ]),
        ft.Row(expand=1, controls=[
            ft.Column(controls=[
                ft.Text('Column: no expand'),
                tabs('unbounded'),
            ], on_size_change=report_size('unbounded.column')),
        ]),
    ]))


if __name__ == '__main__':
    ft.run(main)
