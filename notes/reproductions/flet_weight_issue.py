"""Reproduce unbounded ProgressBar width in a non-expanding Flet Column.

Run: python notes/reproductions/flet_weight_issue.py
Compare the five cases and resize the window. Native size-change reports show
which constraints are finite; ProgressBar's normal 4px height is not the issue.
"""
import flet as ft


def report_size(name):
    def changed(event):
        print(f'{name}: width={event.width}, height={event.height}', flush=True)
    return changed


def case(name, left_expand=None, right_expand=None, progress_width=None):
    return ft.Row(controls=[
        ft.Column(expand=left_expand, controls=[
            ft.Text('expand' if left_expand else 'non-expand'),
            ft.Text(name),
        ], on_size_change=report_size(f'{name}.left')),
        ft.Column(expand=right_expand, controls=[
            ft.Text('expand' if right_expand else 'non-expand'),
            ft.Text('ProgressBar'),
            ft.ProgressBar(value=0.26, width=progress_width,
                           on_size_change=report_size(f'{name}.progress')),
        ], on_size_change=report_size(f'{name}.right')),
    ], on_size_change=report_size(f'{name}.row'))


def main(page: ft.Page):
    page.title = 'Flet ProgressBar: width constraints'
    page.window.width = 800
    page.window.height = 700
    # Each case owns distinct controls; the old experiment added the first Row
    # twice, mixing control-identity problems into the layout reproduction.
    page.add(ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
        case('both expanded', left_expand=1, right_expand=1),
        ft.Divider(),
        case('right expanded', right_expand=1),
        ft.Divider(),
        case('left expanded', left_expand=1),
        ft.Divider(),
        case('neither expanded'),
        ft.Divider(),
        case('explicit width', progress_width=300),
    ]))


if __name__ == '__main__':
    ft.run(main)
