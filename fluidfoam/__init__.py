
import warnings

from fluidfoam.readof import readscalar, readvector, readtensor
from fluidfoam.readof import readsymmtensor, readmesh
from fluidfoam._version import __version__

warnings.simplefilter('always', category=DeprecationWarning)


def readarray(*args, **kargs):
    warnings.warn('The function readarray is deprecated. '
                  'Please use readvector instead.', DeprecationWarning)
    return readvector(*args, **kargs)
