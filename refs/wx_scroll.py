import wx
import wx.lib.scrolledpanel as scrolled

app = wx.App()

window = wx.Frame(None)

hbox = wx.BoxSizer(wx.HORIZONTAL)

vbox1 = wx.BoxSizer(wx.VERTICAL)

label = wx.StaticText(window, label="Scrolled List")
vbox1.Add(label)

scroll = scrolled.ScrolledPanel(window)
scrolled_list = wx.BoxSizer(wx.VERTICAL)
scroll.SetSizer(scrolled_list)

for i in range(100):
    label = wx.StaticText(scroll, label=f"S{i}")
    scrolled_list.Insert(i, label, 0, wx.EXPAND|wx.ALL)

vbox1.Insert(1, scroll, 1, wx.EXPAND|wx.ALL)

hbox.Insert(0, vbox1, 0, wx.EXPAND|wx.ALL)

# scroll.Layout()
scroll.SetupScrolling()

vbox2 = wx.BoxSizer(wx.VERTICAL)

label = wx.StaticText(window, label="List2")
vbox2.Add(label)
for i in range(3):
    label = wx.StaticText(window, label=f"L{i}")
    vbox2.Add(label, 0, wx.EXPAND|wx.ALL)

hbox.Insert(1, vbox2, 0, wx.EXPAND|wx.ALL)

window.SetSizer(hbox)
window.Layout()
window.Show()

app.MainLoop()
