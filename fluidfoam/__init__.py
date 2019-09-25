import warnings

from fluidfoam.readof import readscalar, readvector, readtensor
from fluidfoam.readof import readsymmtensor, readfield, readmesh
from fluidfoam.readof import typefield
from fluidfoam.processing1d import create1dprofil, read1dprofil
from fluidfoam.processing1d import create1dprofil_spe, plot1dprofil
from fluidfoam.meshdesign import getgz,getdzs
from fluidfoam.readpostpro import readforce, readprobes
from fluidfoam._version import __version__

warnings.simplefilter('always', category=DeprecationWarning)


def readarray(*args, **kargs):
    warnings.warn('The function readarray is deprecated. '
                  'Please use readvector instead.', DeprecationWarning)
    return readvector(*args, **kargs)
