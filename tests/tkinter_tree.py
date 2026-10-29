"""Native Tk tree input regressions (GUI required)."""
import unittest
import tkinter_views
from PUI.tkinter import Application, Window, Tree, TreeNode


class TkTreeTests(unittest.TestCase):
    setUp = tkinter_views.TkViewsTests.setUp
    tearDown = tkinter_views.TkViewsTests.tearDown
    sync = tkinter_views.TkViewsTests.sync
    pump = tkinter_views.TkViewsTests.pump
    mount = tkinter_views.TkViewsTests.mount

    def create(self):
        self.calls = calls = []
        class Example(Application):
            def content(self):
                with Window(size=(600, 400)):
                    with Tree():
                        for text in ('a', 'b'):
                            with (TreeNode(text).expand(calls.append, ('open', text))
                                  .collapse(calls.append, ('close', text))
                                  .click(lambda e, t=text: calls.append(('click',t)))
                                  .dblclick(lambda e, t=text: calls.append(('double',t)))):
                                TreeNode(text+' child')
        self.mount(Example())
        return self.root.children[0].children[0]

    def point(self, tree, key, indicator):
        x,y,w,h = tree.ui.bbox(str(key))
        y += h//2
        for x in range(x,x+w):
            element = tree.ui.identify_element(x,y)
            if ('indicator' in element if indicator else 'text' in element):
                return x,y
        self.fail('No native indicator/text hit target')

    def click(self, tree, point, time):
        x,y=point
        tree.ui.event_generate('<ButtonPress-1>',x=x,y=y,time=time)
        tree.ui.event_generate('<ButtonRelease-1>',x=x,y=y,time=time+20)
        self.pump()

    def test_indicator_targets_clicked_item_not_previous_focus(self):
        tree=self.create()
        a,b = tree.tree_state.entries[0].children
        self.click(tree,self.point(tree,a,False),1000)
        self.calls.clear()
        for index, opened in enumerate((True,False,True,False)):
            self.click(tree,self.point(tree,b,True),2000+index*1000)
            self.assertEqual(bool(tree.ui.item(str(b),'open')),opened)
            self.assertEqual(b in tree.tree_state.expanded,opened)
            self.assertNotIn(a,tree.tree_state.expanded)
        self.assertEqual(self.calls,[('open','b'),('close','b'),('open','b'),('close','b')])
        tree.expandable(False)
        self.click(tree,self.point(tree,b,True),7000)
        self.assertFalse(tree.ui.item(str(b),'open'))
        self.assertNotIn(b,tree.tree_state.expanded)

    def test_double_click_does_not_dispatch_a_third_click(self):
        tree=self.create()
        a=tree.tree_state.entries[0].children[0]
        point=self.point(tree,a,False)
        self.click(tree,point,1000)
        self.assertFalse(tree.ui.item(str(a), 'open'))
        self.click(tree,point,1100)
        self.assertTrue(tree.ui.item(str(a), 'open'))
        self.assertEqual([e for e in self.calls if e[0] in ('click','double')],
                         [('click','a'),('double','a')])
        self.click(tree,point,3000)
        self.assertEqual(self.calls[-1],('click','a'))

    def test_disabled_pointer_and_keyboard_preserve_expansion(self):
        tree = self.create()
        a = tree.tree_state.entries[0].children[0]
        tree.expandable(False)
        stamp = 10000
        for opened in (False, True, False):
            (tree.expandAll if opened else tree.collapseAll)()
            self.pump()
            for indicator in (True, False):
                point = self.point(tree, a, indicator)
                self.click(tree, point, stamp)
                self.click(tree, point, stamp+100)
                stamp += 2000
                self.assertEqual(bool(tree.ui.item(str(a), 'open')), opened)
            self.assertEqual(tree.tree_state.selected, a)
            tree.ui.focus_force()
            for key in ('Right', 'Left', 'plus', 'minus', 'space', 'Return'):
                tree.ui.focus(str(a))
                tree.ui.event_generate('<KeyPress-'+key+'>')
                self.pump()
                self.assertEqual(bool(tree.ui.item(str(a), 'open')), opened, key)
                self.assertEqual(a in tree.tree_state.expanded, opened)
        tree.expandable(True)
        self.click(tree, self.point(tree,a,True), stamp)
        self.assertTrue(tree.ui.item(str(a), 'open'))
