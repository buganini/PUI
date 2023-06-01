import flet as ft

def main(page: ft.Page):
    c = ft.Column()
    c.expand = True
    c.scroll = ft.ScrollMode.AUTO

    ####################

    r = ft.Row()

    c1 = ft.Column()
    c1.expand = 1
    c1.controls.append(ft.Text("expand"))
    c1.controls.append(ft.Text("test2"))

    r.controls.append(c1)

    c2 = ft.Column()
    c2.expand = 1
    c2.controls.append(ft.Text("expand"))
    c2.controls.append(ft.Text("pb auto width"))
    pb = ft.ProgressBar()
    pb.value = 0.26
    c2.controls.append(pb)
    r.controls.append(c2)
    c.controls.append(r)

    c.controls.append(r)
    c.controls.append(ft.Divider())

    ####################

    r = ft.Row()

    c1 = ft.Column()
    # c1.expand = 1
    c1.controls.append(ft.Text("non-expand"))
    c1.controls.append(ft.Text("test2"))

    r.controls.append(c1)

    c2 = ft.Column()
    c2.expand = 1
    c2.controls.append(ft.Text("expand"))
    c2.controls.append(ft.Text("pb auto width"))
    pb = ft.ProgressBar()
    pb.value = 0.26
    c2.controls.append(pb)
    r.controls.append(c2)
    c.controls.append(r)
    c.controls.append(ft.Divider())

    ####################

    r = ft.Row()

    c1 = ft.Column()
    c1.expand = 1
    c1.controls.append(ft.Text("expand"))
    c1.controls.append(ft.Text("test2"))

    r.controls.append(c1)

    c2 = ft.Column()
    # c2.expand = 1
    c2.controls.append(ft.Text("non-expand"))
    c2.controls.append(ft.Text("pb auto width"))
    pb = ft.ProgressBar()
    pb.value = 0.26
    c2.controls.append(pb)
    r.controls.append(c2)
    c.controls.append(r)
    c.controls.append(ft.Divider())

    ####################

    r = ft.Row()

    c1 = ft.Column()
    # c1.expand = 1
    c1.controls.append(ft.Text("non-expand"))
    c1.controls.append(ft.Text("test2"))

    r.controls.append(c1)

    c2 = ft.Column()
    # c2.expand = 1
    c2.controls.append(ft.Text("non-expand"))
    c2.controls.append(ft.Text("pb auto width"))
    pb = ft.ProgressBar()
    pb.value = 0.26
    c2.controls.append(pb)
    r.controls.append(c2)
    c.controls.append(r)
    c.controls.append(ft.Divider())

    ####################

    r = ft.Row()

    c1 = ft.Column()
    # c1.expand = 1
    c1.controls.append(ft.Text("non-expand"))
    c1.controls.append(ft.Text("test2"))

    r.controls.append(c1)

    c2 = ft.Column()
    # c2.expand = 1
    c2.controls.append(ft.Text("non-expand"))
    c2.controls.append(ft.Text("pb explicit width"))
    pb = ft.ProgressBar(width=300)
    pb.value = 0.26
    c2.controls.append(pb)
    r.controls.append(c2)
    c.controls.append(r)
    c.controls.append(ft.Divider())

    ####################

    page.controls.append(c)

    page.update()

ft.app(target=main)