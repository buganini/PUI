from .config import *

class WidgetExample(PUIView):
    def setup(self):
        self.embedded_widget = QtWidgets.QCalendarWidget()

    def content(self):
        QtWrapper(self.embedded_widget)
