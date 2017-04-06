
import warnings

from .readof import readscalar, readvector, readtensor, readsymmtensor, readmesh

warnings.simplefilter('always', category=DeprecationWarning)


def readarray(*args, **kargs):
    warnings.warn('The function readarray is deprecated. '
                  'Please use readvector instead.', DeprecationWarning)
    return readvector(*args, **kargs)
