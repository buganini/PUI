from textual.app import App, ComposeResult
from textual.widgets import Label, Button
from textual import containers

CLICKABLE_LABEL_STYLES = "width: auto; height: auto; border-top: none; border-bottom: none;"

class LayoutExample(App):
    def compose(self) -> ComposeResult:
        yield containers.Horizontal(

            # menu
            containers.Vertical(
                Label("Menu"),

                containers.VerticalScroll(
                    containers.Vertical(
                        Button("One").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Two").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Three").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Four").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Five").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Six").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Seven").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Eight").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Nine").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Ten").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Eleven").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Twelve").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Thirteen").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Fourteen").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Fifteen").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Sixteen").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Seventeen").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Eighteen").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Nineteen").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Twenty").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentyOne").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentyTwo").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentyThree").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentyFour").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentyFive").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentySix").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentySeven").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentyEight").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("TwentyNine").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Thirty").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtyOne").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtyTwo").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtyThree").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtyFour").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtyFive").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtySix").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtySeven").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtyEight").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("ThirtyNine").set_styles(CLICKABLE_LABEL_STYLES),
                        Button("Forty").set_styles(CLICKABLE_LABEL_STYLES),
                    ).set_styles("width: auto; height: auto;"), # menu content
                ).set_styles("width: auto; height: 1fr; overflow-y: auto;"), # menu scroller # try to change width to 1fr
            ).set_styles("width: auto; height: 1fr;"), # menu vertical

            # right panel
            containers.Vertical(
                Label("Result"),
                containers.Vertical(
                    containers.Horizontal(
                        Button("-"),
                        Label("100"),
                        Button("+"),
                    ).set_styles("width: auto; height: auto;"), # right panel header
                    containers.VerticalScroll(
                        Label("Row 1"),
                        Label("Row 2"),
                        Label("Row 3"),
                        Label("Row 4"),
                        Label("Row 5"),
                        Label("Row 6"),
                        Label("Row 7"),
                        Label("Row 8"),
                        Label("Row 9"),
                        Label("Row 10"),
                        Label("Row 11"),
                        Label("Row 12"),
                        Label("Row 13"),
                        Label("Row 14"),
                        Label("Row 15"),
                        Label("Row 16"),
                        Label("Row 17"),
                        Label("Row 18"),
                        Label("Row 19"),
                        Label("Row 20"),
                        Label("Row 21"),
                        Label("Row 22"),
                        Label("Row 23"),
                        Label("Row 24"),
                        Label("Row 25"),
                        Label("Row 26"),
                        Label("Row 27"),
                        Label("Row 28"),
                        Label("Row 29"),
                        Label("Row 30"),
                        Label("Row 31"),
                        Label("Row 32"),
                        Label("Row 33"),
                        Label("Row 34"),
                        Label("Row 35"),
                        Label("Row 36"),
                        Label("Row 37"),
                        Label("Row 38"),
                        Label("Row 39"),
                        Label("Row 40"),
                        Label("Row 41"),
                        Label("Row 42"),
                        Label("Row 43"),
                        Label("Row 44"),
                        Label("Row 45"),
                        Label("Row 46"),
                        Label("Row 47"),
                        Label("Row 48"),
                        Label("Row 49"),
                        Label("Row 50"),
                    ).set_styles("width: 1fr; height: 1fr; overflow-y: auto;"), # right panel content
                ).set_styles("width: 1fr; height: 1fr;"), # right panel vertical
            ).set_styles("width: 1fr; height: 1fr;"), # right panel container

        ).set_styles("width: 1fr; height: 1fr;") # horizonal

if __name__ == "__main__":
    app = LayoutExample()
    app.run()