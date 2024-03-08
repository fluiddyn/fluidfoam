import warnings

from fluidfoam.readof import readscalar, readvector, readtensor
from fluidfoam.readof import readsymmtensor, readfield, readmesh, getVolumes
from fluidfoam.readof import typefield, OpenFoamFile
from fluidfoam.processing1d import create1dprofil, read1dprofil
from fluidfoam.processing1d import create1dprofil_spe, plot1dprofil
from fluidfoam.processing1d import create1dprofilDFSEM, read1dprofilDFSEM
from fluidfoam.meshdesign import getgz, getdzs
from fluidfoam.readpostpro import readforce, readprobes
from fluidfoam.meshvisu import MeshVisu
from fluidfoam.openfoamsimu import OpenFoamSimu
from fluidfoam._version import __version__

warnings.simplefilter("always", category=DeprecationWarning)


def readarray(*args, **kargs):
    warnings.warn(
        "The function readarray is deprecated. " "Please use readvector instead.",
        DeprecationWarning,
    )
    return readvector(*args, **kargs)
