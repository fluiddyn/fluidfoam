"""Readers for the other tools (Ofpp, PyFoam): reconstructed cases only."""
import os

import numpy as np

READERS = {}
READERS_DECOMPOSED = {}
USER_CODE = {}
USER_CODE_DECOMPOSED = {}

try:
    import ofpp

    def read_ofpp(case, time, name):
        return ofpp.parse_field(os.path.join(case, time, name))

    READERS["Ofpp"] = read_ofpp
    USER_CODE["Ofpp"] = [read_ofpp]
except ImportError:
    pass

try:
    from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

    def read_pyfoam(case, time, name):
        f = ParsedParameterFile(os.path.join(case, time, name))
        # non-uniform List<scalar> payload
        val = f.content["internalField"] if isinstance(
            f.content, dict
        ) else None
        if val is None:
            raise RuntimeError("PyFoam: unexpected content structure")
        arr = np.asarray(val)
        if arr.ndim == 0:
            # e.g. binary payload not parsed into a list: the timing would
            # not measure the reading of the field, so refuse to report it
            raise RuntimeError(
                "PyFoam did not return a list of values (binary payload?)"
            )
        return arr

    READERS["PyFoam"] = read_pyfoam
    USER_CODE["PyFoam"] = [read_pyfoam]
except ImportError:
    pass
