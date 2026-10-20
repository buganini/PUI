import re

from .config import *

state = State()
state.index = -1
state.text = ""
state.disabled_text = "Value 2"

class ComboboxExample(PUIView):
    destinations = (
        ("Amsterdam (AMS)", "AMS"),
        ("London Heathrow (LHR)", "LHR"),
        ("Paris Charles de Gaulle (CDG)", "CDG"),
        ("Seoul Incheon (ICN)", "ICN"),
        ("Singapore Changi (SIN)", "SIN"),
        ("Taipei Taoyuan (TPE)", "TPE"),
        ("Taipei Songshan (TSA)", "TSA"),
        ("Tokyo Haneda (HND)", "HND"),
        ("Tokyo Narita (NRT)", "NRT"),
    )

    def setup(self):
        self.autocomplete_state = State()
        self.autocomplete_state.destination = ""

    def clear_autocomplete(self, event):
        self.autocomplete_state.destination = ""

    def content(self):
        with VBox():
            Label(f"Index: {state.index}")
            Label(f"Text: {state.text}")

            with HBox():
                Label("Non-editable")
                with ComboBox(editable=False, text_model=state("text")):
                    ComboBoxItem("Item 1", "Value 1")
                    ComboBoxItem("Item 2", "Value 2")
                    ComboBoxItem("Item 3", "Value 3")
                Spacer()

            with HBox():
                Label("Editable")
                with ComboBox(editable=True, index_model=state("index"), text_model=state("text")):
                    ComboBoxItem("Item 1")
                    ComboBoxItem("Item 2")
                    ComboBoxItem("Item 3", "Value 3")
                Spacer()

            Divider()
            for editable in (False, True):
                with HBox():
                    Label("Disabled (editable)" if editable else "Disabled (non-editable)")
                    with ComboBox(editable=editable, text_model=state("disabled_text"), disabled=True):
                        ComboBoxItem("Item 1", "Value 1")
                        ComboBoxItem("Item 2", "Value 2")
                        ComboBoxItem("Item 3", "Value 3")
                    Spacer()

            Divider()
            Label("Autocomplete: type 'Tai Tok' to match either keyword (case-sensitive).")
            Label("Web: press Enter or leave the field to apply the filter.")
            with HBox():
                Label("Destination")
                # Web uses native input + datalist suggestions. Enter/blur commits;
                # selecting a label stores its code, unmatched text stays free text.
                with ComboBox(editable=True, text_model=self.autocomplete_state("destination")):
                    keywords = re.split(r"\s+", self.autocomplete_state.destination.strip())
                    for label, code in self.destinations:
                        if any(k in label for k in keywords):
                            ComboBoxItem(label, code)
                Button("Clear autocomplete").click(self.clear_autocomplete)
                Spacer()
            Label(f"Autocomplete value: {self.autocomplete_state.destination or '(empty)'}")

            Spacer()
