"""Shared Matplotlib widget retention, repaint scheduling and browser transport."""
import asyncio
import unittest
from PUI.web import Application, Window, MatplotlibCanvas
from PUI.web.runtime import Runtime
from PUI.web.protocol import Codec


class MatplotlibLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_retained_figure_resize_draw_idle_and_removal(self):
        class Demo(Application):
            show=True
            version=1
            def content(self):
                with Window():
                    if self.show:self.chart=MatplotlibCanvas(self.plot,self.version)
            def plot(self,f,version):
                f.clear();ax=f.subplots();ax.plot([0,1],[0,version]);ax.set_title('State '+str(version))
        runtime=Runtime(asyncio.get_running_loop());self.addCleanup(runtime.close)
        app=runtime.app=Demo();app.sync()
        runtime.snapshot()
        chart=app.chart;figure=chart.figure;fc=chart.figure_canvas
        runtime.canvas_control('measure',dict(node_id=chart.ui.id,measure_rev=1,width=600,height=400,dpr=2,visible=True))
        first=runtime.snapshot()['canvases'][0]
        codec=Codec();envelope=dict(v=1,type='render',session='test',seq=1,body=first)
        decoded=codec.decode(codec.encode(envelope))
        self.assertEqual(decoded['body']['node_id'],chart.ui.id)
        self.assertTrue(any(c[0]=='vector' for c in decoded['body']['commands']))
        runtime.canvas_control('canvas_ack',{key:first[key] for key in ('node_id','frame_rev','measure_rev')}|{'status':'drawn'})
        fc.draw_idle()
        second=runtime.snapshot()['canvases'][0]
        self.assertGreater(second['frame_rev'],first['frame_rev'])
        runtime.canvas_control('canvas_ack',{key:second[key] for key in ('node_id','frame_rev','measure_rev')}|{'status':'drawn'})
        app.version=2;app.sync()
        self.assertIs(app.chart.figure,figure)
        self.assertIs(fc.owner,app.chart)
        runtime.canvas_control('measure',dict(node_id=app.chart.ui.id,measure_rev=2,width=800,height=500,dpr=1,visible=True))
        frame=runtime.snapshot()['canvases'][0]
        self.assertEqual((frame['width'],frame['height']),(800,500))
        self.assertEqual(tuple(figure.get_size_inches()),(8,5))
        app.show=False;app.sync()
        self.assertEqual(runtime.snapshot()['canvases'],[])
        self.assertIsNone(fc.owner)
        fc.draw_idle() # A retained external Figure cannot redraw a removed widget.
