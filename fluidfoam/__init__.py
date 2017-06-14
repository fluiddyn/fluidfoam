
import warnings

from fluidfoam.readof import readscalar, readvector, readtensor
from fluidfoam.readof import readsymmtensor, readfield, readmesh
from fluidfoam.readof import typefield
from fluidfoam.create1dprofile import create1dprofil, read1dprofil
from fluidfoam.create1dprofile import plot1dprofil
from fluidfoam._version import __version__

warnings.simplefilter('always', category=DeprecationWarning)


def readarray(*args, **kargs):
    warnings.warn('The function readarray is deprecated. '
                  'Please use readvector instead.', DeprecationWarning)
    return readvector(*args, **kargs)
