"""Install sv-ttk, then run: python -m PUI.examples.tkinter_sun_valley"""

import PUI.tkinter as UI
import sv_ttk


class Example(UI.Application):
    def setup(self):
        # The Tk root exists here, before content creates any controls.
        sv_ttk.set_theme("dark", root=self.ui)

    def content(self):
        with UI.Window(title="Sun Valley dark", size=(360, 180)):
            with UI.VBox().layout(padding=16):
                UI.Label("Sun Valley dark theme")
                with UI.ComboBox(editable=True):
                    UI.ComboBoxItem("First option")
                    UI.ComboBoxItem("Second option")
                UI.Button("Close").click(self.close)

    def close(self, event):
        self.quit()


if __name__ == "__main__":
    Example().run()
