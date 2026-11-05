"""foamlib readers.

foamlib reads one file at a time and has no reconstruction of decomposed
cases. The functions below are therefore the code a foamlib user has to
write (and maintain) to get a global array from a decomposed case.

  * read_foamlib            : reconstructed case, one file
  * read_foamlib_concat     : per-processor reading + concatenation. Only
                              correct for a contiguous decomposition.
  * read_foamlib_addressed  : per-processor reading + cellProcAddressing
                              reordering (correct on any decomposition). The
                              addressing files are read with foamlib itself,
                              FoamFile(path)[None] (list without keyword).
  * read_foamlib_addressed_parser : same, but the addressing files are read
                              with our own parser read_label_list(). It is a
                              cross-check, and a fallback for foamlib versions
                              that cannot read these files (see
                              check_foamlib_addressing.py). Its parser is NOT
                              counted as user code (in favour of foamlib).
"""
import gzip
import os
import re

import numpy as np

READERS = {}
READERS_DECOMPOSED = {}
USER_CODE = {}
USER_CODE_DECOMPOSED = {}


def read_label_list(path):
    """Read an OpenFOAM labelList file (ASCII or binary, optional .gz).

    Handles the FoamFile header, comments before the list, binary payloads
    (label size and byte order from the 'arch' entry) and the compact
    one-line ASCII layout.
    """
    if not os.path.exists(path) and os.path.exists(path + ".gz"):
        path += ".gz"
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as f:
        data = f.read()
    start = data.index(b"}") + 1  # end of the FoamFile header
    m = re.compile(rb"(?:\s|//[^\n]*\n|/\*.*?\*/)*(\d+)\s*\(", re.S).match(
        data, start
    )
    if m is None:
        raise ValueError(f"{path}: cannot find the list in the file")
    n, pos = int(m.group(1)), m.end()
    header = data[:start]
    fmt = re.search(rb"format\s+(\w+)\s*;", header)
    if fmt is not None and fmt.group(1) == b"binary":
        lab = re.search(rb"label=(\d+)", header)
        nbytes = int(lab.group(1)) // 8 if lab else 4
        endian = ">" if b"MSB" in header else "<"
        return np.frombuffer(
            data, dtype=f"{endian}i{nbytes}", count=n, offset=pos
        ).astype(np.int64)
    end = data.index(b")", pos)
    return np.array(data[pos:end].split()).astype(np.int64)


try:
    from foamlib import FoamFieldFile, FoamFile

    def read_foamlib(case, time, name):
        path = os.path.join(case, time, name)
        # foamlib needs the explicit .gz path when the file is compressed
        if not os.path.exists(path) and os.path.exists(path + ".gz"):
            path += ".gz"
        f = FoamFieldFile(path)
        arr = np.asarray(f.internal_field)
        del f
        return arr

    def _processor_dirs(case):
        return sorted(
            (d for d in os.listdir(case) if d.startswith("processor")),
            key=lambda d: int(d[len("processor"):] or 0),
        )

    def _read_processor_field(case, proc, time, name):
        path = os.path.join(case, proc, time, name)
        if not os.path.exists(path) and os.path.exists(path + ".gz"):
            path += ".gz"
        f = FoamFieldFile(path)
        arr = np.asarray(f.internal_field)
        del f
        return arr

    def read_foamlib_concat(case, time, name):
        parts = [
            _read_processor_field(case, p, time, name)
            for p in _processor_dirs(case)
        ]
        return np.concatenate(parts)

    def _read_addressing_native(path):
        if not os.path.exists(path) and os.path.exists(path + ".gz"):
            path += ".gz"
        with FoamFile(path) as f:
            return np.asarray(f[None])

    def _assemble(case, time, name, read_addressing):
        parts, addrs = [], []
        for p in _processor_dirs(case):
            parts.append(_read_processor_field(case, p, time, name))
            addrs.append(
                read_addressing(
                    os.path.join(case, p, "constant", "polyMesh",
                                 "cellProcAddressing")
                )
            )
        out = np.empty(sum(len(a) for a in addrs), dtype=parts[0].dtype)
        for part, addr in zip(parts, addrs):
            out[addr] = part
        return out

    def read_foamlib_addressed(case, time, name):
        return _assemble(case, time, name, _read_addressing_native)

    def read_foamlib_addressed_parser(case, time, name):
        return _assemble(case, time, name, read_label_list)

    READERS["foamlib"] = read_foamlib
    READERS_DECOMPOSED["foamlib(concat)"] = read_foamlib_concat
    READERS_DECOMPOSED["foamlib(addr)"] = read_foamlib_addressed
    READERS_DECOMPOSED["foamlib(addr+parser)"] = read_foamlib_addressed_parser
    USER_CODE["foamlib"] = [read_foamlib]
    USER_CODE_DECOMPOSED["foamlib(concat)"] = [
        read_foamlib_concat, _processor_dirs, _read_processor_field]
    USER_CODE_DECOMPOSED["foamlib(addr)"] = [
        read_foamlib_addressed, _assemble, _processor_dirs,
        _read_processor_field, _read_addressing_native]
    USER_CODE_DECOMPOSED["foamlib(addr+parser)"] = [
        read_foamlib_addressed_parser, _assemble, _processor_dirs,
        _read_processor_field]
except ImportError:
    pass
