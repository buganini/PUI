from .config import *

class QtWidgetExample(PUIView):
    def setup(self):
        self.embedded_widget = QtWidgets.QCalendarWidget()

    def content(self):
        QtWrapper(self.embedded_widget)
