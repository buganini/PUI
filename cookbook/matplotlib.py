from .config import *

class MatplotlibCanvasExample(PUIView):
    def content(self):
        data = [(0,0), (1,3), (2,2)]
        MatplotlibCanvas(self.plot, data).layout(weight=1)

    @staticmethod
    def plot(figure, data):
        figure.clear()
        sp = figure.add_subplot(111)
        sp.axes.plot([d[0] for d in data], [d[1] for d in data])
