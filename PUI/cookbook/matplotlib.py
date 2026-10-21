from .config import *
class MatplotlibCanvasExample(PUIView):
    def content(self):
        data = [(0,0), (1,3), (2,2)]
        MatplotlibCanvas(self.plot, data).layout(weight=1)

    @classmethod
    def plot(cls, figure, data):
        figure.clear()
        figure.set_facecolor('#1c2a30')
        sp = figure.add_subplot(111)
        sp.set_facecolor('#1c2a30')
        sp.plot([d[0] for d in data], [d[1] for d in data], color='#d3b98b')
        sp.tick_params(colors='#fff7e6')
        for spine in sp.spines.values():
            spine.set_color('#366c91')
        sp.grid(color='#244b5a')
