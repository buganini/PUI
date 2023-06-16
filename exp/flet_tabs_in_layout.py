import flet as ft

def main(page: ft.Page):
    r = ft.Row(expand=1)

    ####################

    r1 = ft.Row(expand=1)
    c1 = ft.Column(expand=1) # ! expanding

    tabs = ft.Tabs()
    tabs.tabs.append(ft.Tab(
            text="Tab 1",
            content=ft.Container(
                content=ft.Text("Content 1")
            ),
        ))
    tabs.tabs.append(ft.Tab(
            text="Tab 2",
            content=ft.Container(
                content=ft.Text("Content 2")
            ),
        ))

    c1.controls.append(ft.Text("OK"))
    c1.controls.append(tabs)
    r1.controls.append(c1)

    ####################
    r2 = ft.Row(expand=1)
    c2 = ft.Column() # ! non-expanding

    tabs = ft.Tabs()
    tabs.tabs.append(ft.Tab(
            text="Tab 3",
            content=ft.Container(
                content=ft.Text("Content 3")
            ),
        ))
    tabs.tabs.append(ft.Tab(
            text="Tab 4",
            content=ft.Container(
                content=ft.Text("Content 4")
            ),
        ))

    c2.controls.append(ft.Text("NG"))
    c2.controls.append(tabs)
    r2.controls.append(c2)

    ####################

    r.controls.append(r1)
    r.controls.append(r2)

    page.controls.append(r)

    page.update()

ft.app(target=main)