import IPython.display
import numpy

from . import taxonomy

def list_code(filename):
    return IPython.display.Code(filename=filename)


def cdf(values, bin_size=0.01):
    bins = numpy.arange(values.min(), values.max(), bin_size)
    hist, x = numpy.histogram(values, bins=bins, density=1)
    if len(x) < 2:
        return numpy.array([]), numpy.array([])
    dx = x[1] - x[0]
    return x[1:], (numpy.cumsum(hist) * dx)


def plot_cdf(axs, df, label, style={}, bin_size=0.01):
    x, y = cdf(df, bin_size=bin_size)
    for ax in axs:
        ax.plot(x, y, label=label, **style)