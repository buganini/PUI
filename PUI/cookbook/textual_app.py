"""Native app export for textual-dev; launch with PUI_BACKEND=textual."""
from .app import Cookbook

app = Cookbook().ui
