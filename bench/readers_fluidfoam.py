"""fluidfoam readers: this is ALL the code a fluidfoam user has to write.

The same call reads a reconstructed case or a decomposed one (processor*/):
the reconstruction is done by the library.
"""
READERS = {}
READERS_DECOMPOSED = {}
USER_CODE = {}
USER_CODE_DECOMPOSED = {}
fluidfoam = None

try:
    import fluidfoam

    def read(case, time, name):
        return fluidfoam.readscalar(case, time, name)

    def read_decomposed(case, time, name):
        return fluidfoam.readscalar(case, time, name)

    READERS["fluidfoam"] = read
    READERS_DECOMPOSED["fluidfoam"] = read_decomposed
    USER_CODE["fluidfoam"] = [read]
    USER_CODE_DECOMPOSED["fluidfoam"] = [read_decomposed]
except ImportError:
    pass
