"""Backend-independent native ownership during virtual subtree removal."""
import unittest

from PUI import PUINode, PUIView
from PUI.dom import recur_delete


class DomLifecycleTests(unittest.TestCase):
    def test_virtual_subtrees_destroy_native_roots_once(self):
        for replacement in (False, True):
            with self.subTest(replacement=replacement):
                destroyed = []

                class Native(PUINode):
                    def destroy(self, direct):
                        destroyed.append((self._id, direct))
                        super().destroy(direct)

                class Nested(PUIView):
                    def content(self):
                        Native().id('nested-native')

                class Fragment(PUIView):
                    def content(self):
                        Nested()
                        with Native().id('native-owner'):
                            Nested()
                        Native().id('sibling-native')

                class Example(PUIView):
                    show = True

                    def content(self):
                        with Native():
                            Native().id('retained')
                            if self.show:
                                Fragment()
                            elif replacement:
                                Native().id('replacement')

                root = Example()
                try:
                    root.sync()
                    root.show = False
                    root.sync()
                    # Each native root below virtual fragments owns its cleanup.
                    # Descendants of an actual native owner defer to that owner.
                    self.assertEqual(destroyed, [
                        ('nested-native', True),
                        ('nested-native', False),
                        ('native-owner', True),
                        ('sibling-native', True),
                    ])
                finally:
                    recur_delete(root, root, True)


if __name__ == '__main__':
    unittest.main()
