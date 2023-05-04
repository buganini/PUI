import sys
sys.path.append("..")

import feedparser
import functools
from PUI import State
from PUI.PySide6 import *

feeds = [
    "http://rss.slashdot.org/Slashdot/slashdotMainatom",
    "https://hnrss.org/frontpage",
]

data = State()
data.selected_url = ""
data.loaded = feedparser.FeedParserDict({
    "feed": feedparser.FeedParserDict({
        "title": None
    }),
    "entries": []
})
data.selected = -1

def url_changed(url):
    print("url_changed", url)
    data.loaded = feedparser.parse(url)

data("selected_url", url_changed)

def entry_selected(index):
    data.selected = index

class Example(Application):
    def content(self):
        with Window(title="Feed Parser", size=(800,600)):
            with VBox():
                with QtComboBox(text_model=data("selected_url")):
                    for url in feeds:
                        QtComboBoxItem(url)

                Label(data.loaded.feed.title).qt(StyleSheet="font-weight:bold")

                with HBox():
                    with Scroll():
                        with VBox():
                            for i,e in enumerate(data.loaded.entries):
                                Label(e.title).click(functools.partial(entry_selected, i))
                            Spacer()

                    with Scroll():
                        if 0 <= data.selected and data.selected < len(data.loaded.entries):
                            Text(data.loaded.entries[data.selected].description).qt(StyleSheet="background-color:white; color:black")




root = Example()
root.run()
