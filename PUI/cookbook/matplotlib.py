from .config import *


class MatplotlibCanvasExample(PUIView):
    def content(self):
        MatplotlibCanvas(self.plot).layout(weight=1)

    @classmethod
    def plot(cls, figure):
        import numpy as np
        from matplotlib.path import Path
        from matplotlib.patches import PathPatch, Circle

        figure.clear()
        axes = figure.subplots(2, 3)
        figure.subplots_adjust(left=.07, right=.97, bottom=.09, top=.90, wspace=.4, hspace=.65)
        figure.suptitle(f'Matplotlib native {PUI_BACKEND} canvas'
                        if PUI_BACKEND in ('PySide6', 'wx', 'tkinter') else 'Matplotlib → PUI Canvas')

        ax = axes[0, 0]
        ax.plot([0, 1, 2, 3], [0, 2, 1, 3], label='Line')
        ax.scatter([.5, 1.5, 2.5], [1.5, .5, 2.5], color='tomato', label='Markers')
        ax.legend(fontsize=7)
        ax.set_title('Lines / markers / legend', fontsize=9)

        ax = axes[0, 1]
        ax.bar([0, 1, 2], [2, 3, 1], color='royalblue', alpha=.5)
        ax.bar([.3, 1.3, 2.3], [3, 1, 2], color='tomato', alpha=.5)
        ax.set_title('Overlapping alpha', fontsize=9)

        ax = axes[0, 2]
        # Opposite winding creates a hole under Matplotlib's nonzero rule.
        path = Path([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0),
                     (.3, .3), (.7, .3), (.7, .7), (.3, .7), (.3, .3)],
                    [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY,
                     Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY])
        ax.add_patch(PathPatch(path, facecolor='seagreen', edgecolor='black', alpha=.7))
        ax.set(xlim=(-.1, 1.1), ylim=(-.1, 1.1))
        ax.set_title('Bezier / compound path', fontsize=9)

        ax = axes[1, 0]
        ax.plot([-1, 2], [-1, 2], linewidth=8, color='tomato')
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.set_title('Rectangle clip' + (' (no-op)' if PUI_BACKEND == 'flet' else ''), fontsize=9)

        ax = axes[1, 1]
        # Unequal color bands make image orientation and alpha errors visible.
        image = np.zeros((40, 60, 4))
        image[:20, :, 0] = 1
        image[20:, :, 2] = 1
        image[:, :, 3] = np.linspace(.2, 1, 60)
        artist = ax.imshow(image, extent=(0, 1, 0, 1), origin='upper')
        artist.set_clip_path(Circle((.5, .5), .45, transform=ax.transData))
        ax.set_title('RGBA / circle clip' + (' (no-op)' if PUI_BACKEND == 'flet' else ''), fontsize=9)

        ax = axes[1, 2]
        ax.text(.5, .7, r'$\int_0^1 x^2 dx = \frac{1}{3}$', ha='center', fontsize=12)
        ax.text(.5, .3, 'Rotated text', rotation=25, ha='center')
        ax.set_title('Text paths / mathtext', fontsize=9)
        ax.set(xlim=(0, 1), ylim=(0, 1))
