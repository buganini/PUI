import sys
sys.path.append("..")

import feedparser
import functools
from PUI import State
from PUI.PySide6 import *

feeds = [
    "https://hnrss.org/frontpage",
    "http://rss.slashdot.org/Slashdot/slashdotMainatom",
]




class Example(Application):
    def setup(self):
        self.data = State()
        self.data.selected_url = ""
        self.data.loaded = feedparser.FeedParserDict({
            "feed": feedparser.FeedParserDict({
                "title": None
            }),
            "entries": []
        })
        self.data("selected_url", self.url_changed)
        self.data.selected = -1

    def url_changed(self, url):
        print("url_changed", url)
        self.data.loaded = feedparser.parse(url)

    def entry_selected(self, index):
        self.data.selected = index

    def content(self):
        with Window(title="Feed Parser", size=(800,600)):
            with VBox():
                with QtComboBox(text_model=self.data("selected_url")):
                    for url in feeds:
                        QtComboBoxItem(url)

                Label(self.data.loaded.feed.title).qt(StyleSheet="font-weight:bold")

                with HBox():
                    with Scroll():
                        with VBox():
                            for i,e in enumerate(self.data.loaded.entries):
                                Label(e.title).click(functools.partial(self.entry_selected, i))
                            Spacer()

                    with Scroll().layout(weight=1):
                        if 0 <= self.data.selected and self.data.selected < len(self.data.loaded.entries):
                            Text(self.data.loaded.entries[self.data.selected].description).qt(StyleSheet="background-color:white; color:black")




root = Example()
root.run()
