"""Compatibility exports for the shared browser widget classes."""
from .._browser.widgets import *
from .._browser.widgets import BrowserNode as WebNode
from .application import Application

from .dialog import Information, Warning, Critical, Confirm, Prompt, SaveFile
