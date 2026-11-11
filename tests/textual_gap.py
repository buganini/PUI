import unittest
import PUI.textual as UI


class TextualGap(unittest.IsolatedAsyncioTestCase):
    async def test_box_grid_spans_and_updates(self):
        class App(UI.Application):
            gap = 2
            inverse = False
            def content(self):
                with UI.Window():
                    with UI.VBox(tGap=1):
                        with UI.HBox(gap=50,tGap=self.gap,inverse=self.inverse).tLayout(height=2):
                            self.a=UI.Label('A').tLayout(width=4,height=1)
                            UI.Label('Hidden').visible(False)
                            self.b=UI.Label('B').tLayout(width=4,height=1)
                        with UI.Grid(gap=50,tGap=(self.gap,self.gap+1)).tLayout(height=8):
                            self.c=UI.Label('C').grid(row=0,column=0).tLayout(width=4,height=1)
                            self.d=UI.Label('D').grid(row=0,column=1).tLayout(width=4,height=1)
                            self.e=UI.Label('Span').grid(row=1,column=0,columnspan=2).tLayout(width=8,height=1)
        app=App()
        async with app.ui.run_test(size=(80,30)) as pilot:
            for gap,inverse in ((2,False),(0,False),(3,True)):
                app.gap,app.inverse=gap,inverse
                app.sync();await pilot.pause()
                a,b=sorted((app.a.ui.region,app.b.ui.region),key=lambda r:r.x)
                self.assertEqual(b.x-a.right,gap)
                c,d,e=app.c.ui.region,app.d.ui.region,app.e.ui.region
                self.assertEqual(d.x-c.right,gap+1)
                self.assertEqual(e.y-c.bottom,gap)
