import unittest
from unittest.mock import Mock

from PUI import PUIView, TimelineView
from PUI.dom import recur_delete


class TimelineRegression(unittest.TestCase):
    def test_timer_follows_reconciled_node_and_stops_after_removal(self):
        class Example(PUIView):
            def content(self):
                TimelineView(60)
        root = Example()
        try:
            root.sync()
            old = root.children[0]
            timer = old.timer
            self.assertTrue(timer.daemon)
            root.sync()
            current = root.children[0]
            self.assertIs(old.get_node(), current)
            self.assertIs(current.timer, timer)
            timer.cancel()
            root.redraw = Mock()
            old.timer_cb()
            root.redraw.assert_called_once()
            self.assertIsNot(current.timer, timer)
            recur_delete(root, current, True)
            old.timer_cb()
            root.redraw.assert_called_once()
        finally:
            recur_delete(root, root, True)
