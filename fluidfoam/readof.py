"""Reading OpenFoam Files with Python
=====================================
This module provides functions to read OpenFoam Files:

.. autofunction:: readmesh

.. autofunction:: readfield

.. autofunction:: readscalar

.. autofunction:: readvector

.. autofunction:: readsymmtensor

.. autofunction:: readtensor

.. autofunction:: getVolumes

.. autofunction:: typefield

Decomposed cases (``processor0``, ``processor1``... or collated
``processors<N>`` directories) are read transparently by the functions
above when the requested file is not available in the reconstructed case
(see ``_decomposed_fallback``).
The ``boundary`` option is supported (the faces of a patch are put back in the
order of the reconstructed case thanks to ``faceProcAddressing``).
``getVolumes`` also reads decomposed cases (without ``box`` or ``structured``
options; cells are put back in the global order thanks to
``cellProcAddressing``).
Not supported for decomposed cases: ``sets`` and ``region``.

Parallel reading of decomposed cases
------------------------------------

The processor directories of a decomposed case are read sequentially by
default. Parallel reading can be enabled either at import time with the
environment variable ``FLUIDFOAM_NTHREADS``, or at runtime with
:func:`set_nthreads`:

.. autofunction:: set_nthreads

- ``0`` or ``1`` (default): sequential reading;
- an integer ``> 1``: at most ``min(nthreads, number of processors)`` threads
  are used;
- a negative value (e.g. ``-1``): automatic, ``min(number of processors,
  2 * cpu_count())`` threads.

Since the reading is mostly I/O bound and relies on NumPy for the parsing,
the speed-up is significant for binary and gzipped cases, where the Global
Interpreter Lock (GIL) is released during file reads and buffer conversions.
For pure ASCII cases the gain is smaller because the parsing itself holds
the GIL.

Logging
-------

Progress and warning messages are emitted through the standard ``logging``
module, under the ``fluidfoam.readof`` logger. Nothing is printed by
default; to see the messages, configure logging in your script::

    import logging
    logging.basicConfig(level=logging.INFO)

The ``verbose`` keyword of the reading functions remains the simple
on/off switch (``verbose=False`` disables the messages).

Errors
------

A missing boundary/patch raises a ``ValueError`` (no longer calls
``sys.exit``), so the error can be caught and handled by the caller.

Precision of the read values
----------------------------

All read values are rounded to ``precision`` decimals (15 by default)
with ``np.around``. For binary cases this may seem surprising, but it is
intentional and needed for structured meshes: blockMesh sometimes shifts
mesh points by tiny arbitrary amounts, so exact coordinates would break
the detection of the structured grid (and the ``np.reshape`` of
``structured=True``). The rounding also cleans up the small errors of the
ascii decimal representation. Keep this in mind if you need more than 15
decimals: pass a larger ``precision`` to the reading functions.

"""

import os
import re
import gzip
import struct
import sys
import logging
import inspect
import tempfile
import functools
import numpy as np
import scipy.spatial as ss
from concurrent.futures import ThreadPoolExecutor

# Number of threads used to read decomposed cases (processor0, processor1...).
# 0 or 1 means sequential reading. Can be set with the environment variable
# FLUIDFOAM_NTHREADS at import time, or at runtime with set_nthreads().
NTHREADS = int(os.environ.get("FLUIDFOAM_NTHREADS", "0"))


def set_nthreads(nthreads: int) -> None:
    """Set the number of threads used to read decomposed cases.

    0 or 1 disables parallel reading (sequential). A value greater than 1
    enables it: at most min(nthreads, number of processors) threads are used.

    """
    global NTHREADS
    NTHREADS = int(nthreads)


def _effective_nthreads(nprocs):
    """Number of threads actually used to read nprocs processor directories."""
    if nprocs <= 1 or NTHREADS in (0, 1):
        return 1
    if NTHREADS < 0:  # -1 (or any negative): automatic
        return min(nprocs, (os.cpu_count() or 1) * 2)
    return min(nprocs, NTHREADS)


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _make_path(path, time_name=None, name=None):
    if time_name is not None and name is None:  # pragma: no cover
        path = os.path.join(path, time_name)
    elif name is not None and time_name is None:  # pragma: no cover
        path = os.path.join(path, name)
    elif name is not None and time_name is not None:
        path = os.path.join(path, time_name, name)
    if not os.path.exists(path) and os.path.exists(path + ".gz"):
        path += ".gz"

    return path


def _find_latesttime(path):
    dir_list = os.listdir(path)
    time_list = []

    for directory in dir_list:
        try:
            float(directory)
            time_list.append(directory)
        except ValueError:
            pass
    time_list.sort(key=float)
    return time_list[-1]


# --------------------------------------------------------------------------
# Decomposed cases: processor0, processor1, ... (uncollated) and
# processors<N> (collated: one decomposedBlockData file per field with one
# block per processor; also processors<N>_<first>-<last> with ioRanks)
# --------------------------------------------------------------------------
_COLLATED_RE = re.compile(r"processors\d+(_\d+-\d+)?")
_BLOCK_RE = re.compile(rb"// processor(\d+)\r?\n(\d+)\r?\n\(")


def _processor_dirs(path):
    """Sorted list of the processorN directories of a decomposed case."""
    try:
        entries = os.listdir(path)
    except OSError:
        return []
    procs = [
        d
        for d in entries
        if re.fullmatch(r"processor\d+", d)
        and os.path.isdir(os.path.join(path, d))
    ]
    procs.sort(key=lambda d: int(d[len("processor") :]))
    return [os.path.join(path, d) for d in procs]


def _collated_dirs(path):
    """Sorted list of the processors<N>[_a-b] directories (collated case)."""
    try:
        entries = os.listdir(path)
    except OSError:
        return []
    dirs = [
        d
        for d in entries
        if _COLLATED_RE.fullmatch(d) and os.path.isdir(os.path.join(path, d))
    ]
    dirs.sort()
    return [os.path.join(path, d) for d in dirs]


def _decomposition(path, time_name=None, name=None):
    """Return (layout, dirs); layout is "uncollated", "collated" or None."""
    procs = _processor_dirs(path)
    coll = _collated_dirs(path)
    if (
        procs
        and coll
        and time_name not in (None, "latestTime")
        and name is not None
    ):
        # both layouts present: take the one holding the requested file
        in_procs = any(
            os.path.exists(_make_path(d, time_name, name)) for d in procs
        )
        in_coll = any(
            os.path.exists(_make_path(d, time_name, name)) for d in coll
        )
        if in_coll and not in_procs:
            return "collated", coll
    if procs:
        return "uncollated", procs
    if coll:
        return "collated", coll
    return None, []


def _latest_time_or_none(path):
    try:
        return _find_latesttime(path)
    except (OSError, IndexError):
        return None


def _parse_label_list(content, name="labelList"):
    """Parse the bytes of an OpenFOAM labelList file (ascii or binary).

    Used for ``constant/polyMesh/cellProcAddressing`` of the processor
    directories: entry i is the global index of the local cell i.
    """
    m = re.search(rb"FoamFile\s*\{(.*?)\}", content, re.S)
    header = m.group(1) if m else b""
    body = content[m.end() :] if m else content

    fmt = re.search(rb"format\s+(\w+)\s*;", header)
    is_ascii = fmt is None or fmt.group(1) == b"ascii"
    label = re.search(rb"label=(\d+)", header)
    label_bytes = int(label.group(1)) // 8 if label else 4

    m = re.search(rb"^[ \t]*(\d+)\s*\(", body, re.M)
    if m is None:
        raise ValueError("Cannot parse labelList in " + name)
    nb_values = int(m.group(1))
    if is_ascii:
        end = body.index(b")", m.end())
        values = np.array(body[m.end() : end].split(), dtype=np.int64)
    else:
        values = np.frombuffer(
            body,
            dtype="<i%d" % label_bytes,
            count=nb_values,
            offset=m.end(),
        ).astype(np.int64)
    if values.size != nb_values:
        raise ValueError("Corrupted labelList in " + name)
    return values


def _read_file_bytes(filename):
    opener = gzip.open if filename.endswith(".gz") else open
    try:
        with opener(filename, "rb") as f:
            return f.read()
    except FileNotFoundError:
        if filename.endswith(".gz") or not os.path.exists(filename + ".gz"):
            raise
        with gzip.open(filename + ".gz", "rb") as f:
            return f.read()


def _read_label_list(filename):
    """Read an OpenFOAM labelList file (ascii or binary, optionally gzipped)."""
    return _parse_label_list(_read_file_bytes(filename), filename)


def _read_collated_blocks(filename):
    """Blocks of a collated (decomposedBlockData) file.

    Returns {processor rank: bytes of the block}. A block is the content of
    the file written by an uncollated run in processorN/; only the block of
    the first rank carries the FoamFile header (see _extract_collated).
    """
    content = _read_file_bytes(filename)
    blocks = {}
    pos = 0
    while True:
        m = _BLOCK_RE.search(content, pos)
        if m is None:
            break
        size = int(m.group(2))
        start = m.end()
        block = content[start : start + size]
        if len(block) != size or content[start + size : start + size + 1] != b")":
            raise ValueError("Corrupted decomposedBlockData file " + filename)
        blocks[int(m.group(1))] = block
        pos = start + size + 1
    if not blocks:
        raise ValueError("No processor block found in " + filename)
    return blocks


def _extract_collated(dirs, tmp, required, optional=()):
    """Write the blocks of collated files as tmp/processorN/<relative path>.

    required / optional: lists of paths relative to the processors<N>
    directories (e.g. "0.5/alpha", "constant/polyMesh/cellProcAddressing").
    """
    for rels, must in ((required, True), (optional, False)):
        for rel in rels:
            found = False
            for d in dirs:
                filename = _make_path(d, rel)
                if not os.path.exists(filename):
                    continue
                blocks = _read_collated_blocks(filename)
                # only the first block carries the FoamFile header
                h = re.match(
                    rb"\s*FoamFile\s*\{.*?\}\n", blocks[min(blocks)], re.S
                )
                header = h.group(0) if h else b""
                for rank, block in blocks.items():
                    if not block.lstrip().startswith(b"FoamFile"):
                        block = header + block
                    out = os.path.join(tmp, "processor%d" % rank, rel)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out, "wb") as f:
                        f.write(block)
                found = True
            if must and not found:
                raise FileNotFoundError(
                    "%s not found in %s" % (rel, ", ".join(dirs))
                )


def _use_processors(path, time_name, name, kind):
    """Tell whether the data must be read from a decomposed case.

    Returns (layout, time_name): layout is None (read the case directly),
    "uncollated" (processorN) or "collated" (processors<N>); time_name is the
    resolved time when "latestTime" has been requested and found in the
    decomposed directories.
    """
    layout, dirs = _decomposition(path, time_name, name)
    if layout is None:
        return None, time_name

    if time_name == "latestTime":
        t_dec = _latest_time_or_none(dirs[0])
        t_root = _latest_time_or_none(path)
        if t_dec is not None and (t_root is None or float(t_dec) > float(t_root)):
            return layout, t_dec
        return None, time_name

    if kind in ("mesh", "volumes"):
        if not os.path.exists(os.path.join(path, "constant", "polyMesh")):
            return layout, time_name
        if (
            time_name is not None
            and time_name != "0"
            and not os.path.exists(
                _make_path(path, time_name, os.path.join("polyMesh", "points"))
            )
        ):
            return layout, time_name  # dynamic mesh: points per processor
        return None, time_name

    if time_name is None or name is None:
        return None, time_name
    if os.path.exists(_make_path(path, time_name, name)):
        return None, time_name
    return layout, time_name


def _scatter_to_global(parts, ncells):
    """Put the processor arrays (last axis = cells) in global cell order."""
    out = np.empty(np.shape(parts[0][1])[:-1] + (ncells,), dtype=float)
    for addr, arr in parts:
        arr = np.asarray(arr, dtype=float)
        if arr.shape[-1] != addr.size:
            if arr.shape[-1] == 1:  # uniform field on this processor
                arr = np.broadcast_to(arr, arr.shape[:-1] + (addr.size,))
            else:
                raise ValueError(
                    "Field size (%d) differs from the number of cells (%d) "
                    "of the processor" % (arr.shape[-1], addr.size)
                )
        out[..., addr] = arr
    return out


def _cell_centroids(owner, neigh, facefile, pointfile, precision=15):
    """Vectorized cell centroid computation.

    For every cell the centroid is the mean of the coordinates of the
    unique vertices (points) shared by its faces.

    Parameters
    ----------
    owner, neigh : OpenFoamFile
        Parsed ``owner`` and ``neighbour`` files.
    facefile : OpenFoamFile
        Parsed ``faces`` file (must have ``_face_pts`` / ``_face_offsets``).
    pointfile : OpenFoamFile
        Parsed ``points`` file (must have ``values_x/y/z``).
    precision : int
        Number of decimal places to round the centroids to. Must match the
        precision used when parsing the points file, so that the structured
        mesh check (``np.unique``) is not broken by 1-ulp differences in
        the summation order.

    Returns
    -------
    xs, ys, zs : ndarray, shape (n_cells,)
        Centroid coordinates.
    up : ndarray, shape (n_unique_pts,)
        Flat array of unique point indices (grouped by cell order).
    up_starts : ndarray, shape (n_cells + 1,)
        CSR offsets: cell *i* unique points are ``up[up_starts[i]:
        up_starts[i + 1]]``.
    """
    n_faces = facefile.nfaces
    n_interior = neigh.nb_faces  # interior faces are contiguous in OpenFOAM
    face_offsets = facefile._face_offsets
    face_pts = facefile._face_pts
    face_npts = np.diff(face_offsets)

    # Map each point reference to its face index
    point_face_id = np.repeat(np.arange(n_faces), face_npts)

    # Owner side: every face contributes to its owner cell
    owner_cells = owner.values[point_face_id]

    # Neighbour side: interior faces only (first n_interior faces)
    n_interior_pts = int(face_offsets[n_interior])
    if n_interior_pts > 0:
        interior_mask = point_face_id < n_interior
        neigh_cells = neigh.values[point_face_id[interior_mask]]
        neigh_pts = face_pts[interior_mask]
        all_cells = np.concatenate([owner_cells, neigh_cells])
        all_pts = np.concatenate([face_pts, neigh_pts])
    else:
        all_cells = owner_cells
        all_pts = face_pts

    # Sort by (cell, point) and remove duplicate (cell, point) pairs
    order = np.lexsort((all_pts, all_cells))
    sc = all_cells[order]
    sp = all_pts[order]

    if sc.size > 1:
        dedup = np.empty(sc.size, dtype=bool)
        dedup[0] = True
        dedup[1:] = (sc[1:] != sc[:-1]) | (sp[1:] != sp[:-1])
    else:
        dedup = np.ones(sc.size, dtype=bool)
    uc = sc[dedup]
    up = sp[dedup]

    # Cell boundaries in the unique array (uc is sorted, so cell_ids is
    # 0, 1, ..., n_cells - 1)
    if uc.size > 1:
        change = np.empty(uc.size, dtype=bool)
        change[0] = True
        change[1:] = uc[1:] != uc[:-1]
    else:
        change = np.ones(uc.size, dtype=bool)
    cell_starts = np.flatnonzero(change)

    # Mean of coordinates per cell (reduceat over the unique points)
    pt_x = pointfile.values_x[up]
    pt_y = pointfile.values_y[up]
    pt_z = pointfile.values_z[up]

    x_sum = np.add.reduceat(pt_x, cell_starts)
    y_sum = np.add.reduceat(pt_y, cell_starts)
    z_sum = np.add.reduceat(pt_z, cell_starts)
    counts = np.diff(np.append(cell_starts, uc.size))

    n_cells = owner.nb_cell
    # cell_ids == 0..n_cells-1 (every cell owns at least one face, and uc
    # is sorted by cell id), so x_sum/counts is already in cell order
    xs = (x_sum / counts).astype(float)
    ys = (y_sum / counts).astype(float)
    zs = (z_sum / counts).astype(float)
    # Round to the input precision so that the structured-mesh check
    # (np.unique) is not broken by 1-ulp summation-order differences.
    np.around(xs, decimals=precision, out=xs)
    np.around(ys, decimals=precision, out=ys)
    np.around(zs, decimals=precision, out=zs)

    # CSR offsets for the unique points per cell
    up_starts = np.empty(n_cells + 1, dtype=np.int64)
    up_starts[:n_cells] = cell_starts
    up_starts[n_cells] = up.size

    return xs, ys, zs, up, up_starts


def _structured_index(xs, ys, zs):
    nx = np.unique(xs).size
    ny = np.unique(ys).size
    nz = np.unique(zs).size
    if nx * ny * nz != xs.size:
        raise ValueError(
            "nx.ny.nz not equal to number of cells."
            "Are you sure that your mesh is cartesian?"
        )
    return np.lexsort((xs, ys, zs)), (nx, ny, nz)


def _reconstruct(func, kind, args, time_name, data_path, layout):
    """Read each processorN of data_path and rebuild the global array(s)."""
    path = args["path"]
    procs = _processor_dirs(data_path)
    structured = args.get("structured", False)
    order = args.get("order", "F")
    verbose = args.get("verbose", True)
    if verbose:
        logger.info(
            "Reading %s decomposed case (%d processors)", layout, len(procs)
        )

    sub = dict(args)
    sub.update(structured=False, verbose=False, time_name=time_name)

    def read_one(procdir):
        local = dict(sub)
        local["path"] = procdir
        addr = _read_label_list(
            os.path.join(procdir, "constant", "polyMesh", "cellProcAddressing")
        )
        result = func(**local)
        if kind == "mesh":
            result = np.vstack(result)
        return addr, result

    nthreads = _effective_nthreads(len(procs))
    if nthreads > 1:
        with ThreadPoolExecutor(max_workers=nthreads) as executor:
            parts = list(executor.map(read_one, procs))
    else:
        parts = [read_one(procdir) for procdir in procs]

    ncells = sum(addr.size for addr, _ in parts)
    if max(addr.max() for addr, _ in parts) + 1 != ncells:
        raise ValueError("Inconsistent cellProcAddressing in " + path)

    if kind == "volumes":
        # func returned (centroids, volumes) per processor: scatter both
        centroids = np.empty((ncells, 3), dtype=float)
        volumes = np.empty(ncells, dtype=float)
        for addr, (cent, vol) in parts:
            if cent.shape[0] != addr.size or vol.shape[0] != addr.size:
                raise ValueError(
                    "getVolumes on a decomposed case requires all the "
                    "cells of each processor (box=None)."
                )
            centroids[addr] = cent
            volumes[addr] = vol
        return centroids, volumes

    values = _scatter_to_global(parts, ncells)

    if kind == "mesh":
        if structured:
            ind, shape = _structured_index(*values)
            return tuple(v[ind].reshape(shape, order=order) for v in values)
        return values[0], values[1], values[2]

    if structured:
        xs, ys, zs = readmesh(
            path, precision=args.get("precision", 15), verbose=False
        )
        ind, shape = _structured_index(xs, ys, zs)
        values = values[..., ind]
        values = values.reshape(values.shape[:-1] + shape, order=order)
    return values


def _patch_range(procdir, patch):
    """(startFace, nFaces) of a patch in the local mesh of a processor.

    None if the patch is not in the boundary file of the processor.
    """
    mesh = os.path.join(procdir, "constant", "polyMesh")
    boundary = OpenFoamFile(mesh, name="boundary", verbose=False).boundaryface
    key = str.encode(patch)
    if key not in boundary:
        return None
    return int(boundary[key][b"startFace"]), int(boundary[key][b"nFaces"])


def _reconstruct_boundary(func, kind, args, time_name, data_path, layout):
    """Read a patch on each processorN of data_path and rebuild it.

    The faces of the patch of a processor are the local faces
    startFace ... startFace + nFaces - 1; faceProcAddressing gives, for each
    local face, the index of the face in the global mesh (+ 1, the sign
    tells that the face is flipped). The faces of a patch are contiguous in
    the global mesh, so sorting their global indices gives the order of the
    reconstructed case.
    """
    path = args["path"]
    patch = args["boundary"]
    procs = _processor_dirs(data_path)
    structured = args.get("structured", False)
    order = args.get("order", "F")
    if args.get("verbose", True):
        logger.info(
            "Reading %s decomposed case (%d processors)", layout, len(procs)
        )

    sub = dict(args)
    sub.update(structured=False, verbose=False, time_name=time_name)
    ranges = {procdir: _patch_range(procdir, patch) for procdir in procs}
    active = [
        procdir
        for procdir in procs
        if ranges[procdir] is not None and ranges[procdir][1] > 0
    ]

    def read_one(procdir):
        local = dict(sub)
        local["path"] = procdir
        start, nfaces = ranges[procdir]
        face_addr = _read_label_list(
            os.path.join(procdir, "constant", "polyMesh", "faceProcAddressing")
        )
        result = func(**local)
        if kind == "mesh":
            result = np.vstack(result)
        result = np.asarray(result, dtype=float)
        if result.shape[-1] != nfaces:
            if result.shape[-1] != 1:  # a uniform value is allowed
                raise ValueError(
                    "%d values for the %d faces of the patch %s of %s"
                    % (result.shape[-1], nfaces, patch, os.path.basename(procdir))
                )
            result = np.broadcast_to(result, result.shape[:-1] + (nfaces,))
        return np.abs(face_addr[start : start + nfaces]) - 1, result

    nthreads = _effective_nthreads(len(active))
    if nthreads > 1:
        with ThreadPoolExecutor(max_workers=nthreads) as executor:
            results = list(executor.map(read_one, active))
    else:
        results = [read_one(procdir) for procdir in active]
    ids = [r[0] for r in results]
    parts = [r[1] for r in results]
    if not parts:
        raise ValueError("No face of the patch %s found in %s" % (patch, path))

    ids = np.concatenate(ids)
    sort = np.argsort(ids, kind="stable")
    if ids.size > 1 and np.any(np.diff(ids[sort]) != 1):
        raise ValueError("Inconsistent faceProcAddressing for the patch " + patch)
    values = np.concatenate(parts, axis=-1)[..., sort]

    if kind == "mesh":
        if structured:
            ind, shape = _structured_index(*values)
            return tuple(v[ind].reshape(shape, order=order) for v in values)
        return values[0], values[1], values[2]

    if structured:
        xs, ys, zs = readmesh(
            path,
            boundary=patch,
            precision=args.get("precision", 15),
            verbose=False,
        )
        ind, shape = _structured_index(xs, ys, zs)
        values = values[..., ind]
        values = values.reshape(values.shape[:-1] + shape, order=order)
    return values


def _read_decomposed(func, kind, args, time_name, layout):
    """Read a field or the mesh of a decomposed case and reconstruct it."""
    path = args["path"]
    for key in ("sets", "region"):
        if args.get(key) is not None:
            raise NotImplementedError(
                "Option '%s' is not supported for decomposed cases "
                "(reconstruct the case with reconstructPar)." % key
            )
    if kind == "volumes":
        if args.get("box") is not None:
            raise NotImplementedError(
                "Option 'box' is not supported for decomposed cases "
                "(reconstruct the case with reconstructPar)."
            )
        if args.get("structured"):
            raise NotImplementedError(
                "Option 'structured' is not supported for decomposed cases "
                "(reconstruct the case with reconstructPar)."
            )
    on_patch = args.get("boundary") is not None
    reconstruct = _reconstruct_boundary if on_patch else _reconstruct
    if layout == "uncollated":
        return reconstruct(func, kind, args, time_name, path, layout)

    # collated: extract the blocks in a temporary processorN/ tree
    mesh = os.path.join("constant", "polyMesh")
    if on_patch:
        required = [
            os.path.join(mesh, "boundary"),
            os.path.join(mesh, "faceProcAddressing"),
        ]
        optional = [os.path.join(mesh, "owner")]  # values of the nearest cells
    else:
        required = [os.path.join(mesh, "cellProcAddressing")]
        optional = []
    if kind == "field":
        required.append(os.path.join(time_name, args["name"]))
    else:
        if on_patch:
            required.append(os.path.join(mesh, "faces"))
        else:
            required += [
                os.path.join(mesh, f) for f in ("faces", "owner", "neighbour")
            ]
        points = os.path.join(mesh, "points")
        if time_name in (None, "0"):
            required.append(points)
        else:
            optional.append(points)
            required.append(os.path.join(time_name, "polyMesh", "points"))
    with tempfile.TemporaryDirectory(prefix="fluidfoam_") as tmp:
        _extract_collated(_collated_dirs(path), tmp, required, optional)
        return reconstruct(func, kind, args, time_name, tmp, layout)


def _decomposed_fallback(kind):
    """Decorator: read from processor* / processors<N> if not reconstructed.

    kind is "field" (readfield, readscalar...) or "mesh" (readmesh).
    """

    def decorator(func):
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            a = dict(bound.arguments)
            layout, time_name = _use_processors(
                a["path"], a.get("time_name"), a.get("name"), kind
            )
            if layout is not None:
                return _read_decomposed(func, kind, a, time_name, layout)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _iter_lines(content):
    """Lazy equivalent of ``content.split(b"\\n")``."""
    pos = 0
    while True:
        end = content.find(b"\n", pos)
        if end == -1:
            yield content[pos:]
            return
        yield content[pos:end]
        pos = end + 1


def _iter_dimensions_lines(content):
    """Lines starting with "dimensions" (stripped, without quotes and ";")."""
    pos = content.find(b"dimensions")
    while pos != -1:
        start = content.rfind(b"\n", 0, pos) + 1
        if not content[start:pos].strip():
            end = content.find(b"\n", pos)
            if end == -1:
                end = len(content)
            yield content[pos:end].strip().replace(b'"', b"").replace(b";", b"")
        pos = content.find(b"dimensions", pos + 1)


class OpenFoamFile(object):
    """OpenFoam file parser."""

    def __init__(
        self,
        path: str,
        time_name: str | None = None,
        name: str | None = None,
        structured: bool = False,
        boundary: str | None = None,
        sets: str | None = None,
        order: str = "F",
        precision: int = 15,
        datatype: str | None = None,
        verbose: bool = True,
    ) -> None:

        self.pathcase = path
        if time_name == "latestTime":
            time_name = _find_latesttime(path)
        if sets is None:
            self.path = _make_path(path, time_name, name)
        else:
            self.path = _make_path(path, time_name, os.path.join(sets, name))
        self.verbose = verbose
        if self.verbose:
            logger.info("Reading file %s", self.path)

        self.is_compressed = self.path.endswith(".gz")
        if self.is_compressed:
            self._open = gzip.open
        else:
            self._open = open

        try:
            with self._open(self.path, "rb") as f:
                self.content = f.read()
        except FileNotFoundError:
            if self.is_compressed or not os.path.exists(self.path + ".gz"):
                raise
            self.path += ".gz"
            self.is_compressed = True
            self._open = gzip.open
            with self._open(self.path, "rb") as f:
                self.content = f.read()

        # computed on demand (see the lines_stripped and boundary properties)
        self._lines_stripped = None
        self._boundary = None

        self.header = self._parse_session(b"FoamFile")

        try:
            self.is_ascii = self.header[b"format"] == b"ascii"
            self.noheader = False
        except KeyError:
            self.is_ascii = True
            self.noheader = True
        try:
            self.is_SP = b"scalar=32" in self.header[b"arch"]
            self.is_MSB = b"MSB" in self.header[b"arch"]
        except KeyError:
            self.is_SP = False
            self.is_MSB = sys.byteorder == "big"

        for line in _iter_dimensions_lines(self.content):
            tmp = (line.split(b"[")[1]).split(b"]")[0]
            self.dimensions = tuple(
                int(s) for s in tmp.replace(b"-", b" -").split()
            )

        if name is None:
            self._parse_data(
                boundary=boundary, precision=precision, datatype=datatype
            )
        elif name.endswith("boundary"):
            self.boundaryface = self._parse_boundaryfile()
        elif name.endswith("faces"):
            self._parse_face()
        elif name.endswith("points"):
            self._parse_points(precision=precision)
        elif name.endswith("owner") or name.endswith("neighbour"):
            self._parse_owner()
        elif name.startswith("sets/"):
            self._parse_sets()
        else:
            self._parse_data(
                boundary=boundary, precision=precision, datatype=datatype
            )
        if structured:
            self._determine_order(
                boundary=boundary, order=order, precision=precision
            )

    @property
    def lines_stripped(self):
        """All the lines of the file, stripped (computed on first access)."""
        if self._lines_stripped is None:
            self._lines_stripped = [
                line.strip().replace(b'"', b"").replace(b";", b"")
                for line in self.content.split(b"\n")
            ]
        return self._lines_stripped

    @lines_stripped.setter
    def lines_stripped(self, value):
        self._lines_stripped = value

    @property
    def boundary(self):
        """Content of the boundaryField section (computed on first access)."""
        if self._boundary is None:
            self._boundary = self._parse_session(b"boundaryField")
        return self._boundary

    @boundary.setter
    def boundary(self, value):
        self._boundary = value

    @property
    def faces(self):
        """Dict mapping face index to ``{"npts": int, "id_pts": ndarray}``.

        Built lazily from the flat CSR arrays (``_face_pts``,
        ``_face_offsets``) on first access, for backward compatibility.
        """
        if self._faces_dict is None:
            d = {}
            for i in range(self.nfaces):
                s = int(self._face_offsets[i])
                e = int(self._face_offsets[i + 1])
                d[i] = {"npts": e - s, "id_pts": self._face_pts[s:e]}
            self._faces_dict = d
        return self._faces_dict

    def _iter_lines_stripped(self):
        """Stripped lines, lazily: parsers that stop early do not pay for
        the whole file."""
        if self._lines_stripped is not None:
            return iter(self._lines_stripped)
        return (
            line.strip().replace(b'"', b"").replace(b";", b"")
            for line in _iter_lines(self.content)
        )

    def _parse_boundaryfile(self):

        dict_bounfile = {}
        in_section = False
        previous_line = ""
        level = 0
        for line in self._iter_lines_stripped():
            if line == b"(":
                in_section = True
                level += 1
                continue
            if in_section is True:
                if line == b"{":
                    level += 1
                    continue
                elif line == b"}" or line == b")":
                    level -= 1
                else:
                    tmp = line.replace(b'"', b"").split()
                    if len(tmp) == 1:
                        dict_bounfile[tmp[0]] = {}
                    elif len(tmp) > 1:
                        dict_bounfile[previous_line][tmp[0]] = tmp[1]
                        continue
                if level == 0:
                    break
                if line:
                    previous_line = line

        return dict_bounfile

    def _parse_session(self, title):

        dict_session = {}
        in_section = False
        previous_line = ""
        level = 0
        for line in self._iter_lines_stripped():
            if line == title:
                in_section = True
                continue
            if line.startswith(title + b" ") and b"{" in line:
                # compact one-line header, e.g. "FoamFile { version 2.0; ... }"
                in_section = True
                fields = line.replace(b"{", b" ").replace(b"}", b" ").split()
                for i in range(1, len(fields) - 1, 2):
                    dict_session[fields[i]] = fields[i + 1]
                break
            if in_section is True:
                if line == b"{":
                    level += 1
                    continue
                elif line == b"}":
                    level -= 1
                else:
                    tmp = line.replace(b'"', b"").split()
                    if len(tmp) > 1:
                        if level == 1:
                            dict_session[tmp[0]] = tmp[1]
                        elif level == 2:
                            if previous_line not in dict_session:
                                dict_session[previous_line] = {}
                            try:
                                dict_session[previous_line][tmp[0]] = tmp[1]
                            except TypeError:
                                pass
                if level == 0:
                    break
                previous_line = line

        return dict_session

    def _parse_data(self, boundary, datatype, precision=15):

        if boundary is not None:
            boun = str.encode(boundary)
            if np.size(self.content.split(boun)) <= 2:
                iboun = 1
            else:
                lines = self.content.split(b"\n")
                iboun = 0
                for line in lines:
                    if boun in line.strip():
                        iboun += 1
                    if boun == line.strip():
                        break

            if iboun >= np.size(self.content.split(boun)):
                raise ValueError(
                    "No boundary/patch " + boundary + " in " + self.path
                )

            elif b"value" in self.content.split(boun)[iboun].split(b"}")[0]:
                data = self.content.split(boun)[iboun].split(b"value")[1]
            else:
                if self.verbose:
                    logger.warning(
                        "No data on boundary/patch; "
                        "using the values of the nearest cells"
                    )
                self._nearest_data(boundary=boundary, precision=precision)
                return
        else:
            try:
                data = self.content.split(b"internalField", 2)[1]
            except IndexError:
                data = self.content

        self._parse_field_values(data, datatype=datatype)

    def _parse_field_values(self, data, datatype=None, precision=15):
        """Parse the values of a field (uniform or not, ascii or binary).

        Set self.nonuniform, self.uniform, self.codestream, self.short,
        self.type_data and self.values; return nothing.

        """
        lines = data.split(b"\n", 2)  # only the first two lines are used
        shortline = lines[0].split(b">")[-1]
        words = lines[0].split()
        if not shortline and len(lines) > 1:
            # e.g. "nonuniform List<vector>" alone on the first line
            shortline = lines[1].split(b">")[-1]

        if not self.noheader:
            self.nonuniform = words[0] == b"nonuniform"
            self.uniform = words[0] == b"uniform"
            self.codestream = words[0] == b"#codeStream"
            self.short = shortline[-1] == b";"

            self.type_data = self.header[b"class"]

            if b"ScalarField" in self.type_data:
                self.type_data = "scalar"
            elif b"VectorField" in self.type_data:
                self.type_data = "vector"
            elif b"SymmTensorField" in self.type_data:
                self.type_data = "symmtensor"
            elif b"TensorField" in self.type_data:
                self.type_data = "tensor"
        else:
            self.uniform = False
            self.codestream = False
            self.nonuniform = True
            shortline = lines[1].split(b">")[-1]
            self.short = shortline[-1] == b";"
            self.type_data = datatype

        payload_offset = 0  # start of the values in data (binary: no copy)
        if self.uniform:
            nb_pts = 1
            if not (self.type_data == "scalar"):
                data = shortline.split(b"(")[1]
                data = data.replace(b" ", b"\n")
                data = data.replace(b");", b"\n);")
            else:
                data = words[1].split(b";")[0]
            if self.verbose:
                logger.warning(
                    "uniform field of type %s! " "Only constant field in output",
                    self.type_data,
                )
        elif shortline.count(b";") >= 1:
            nb_pts = int(shortline.split(b"(")[0])
            data = shortline.split(b"(")[1]
            data = data.replace(b" ", b"\n")
            data = data.replace(b");", b"\n);")
        elif self.codestream:
            nb_pts = 0
            if self.verbose:
                logger.warning(
                    "codeStream field! I can not read the source code!"
                )
        else:
            nb_pts = int(lines[1])
            pos = data.find(b"\n(")
            payload_offset = pos + 2 if pos != -1 else len(data)
            if self.is_ascii:
                data = data[payload_offset:]
                payload_offset = 0

        if not self.is_ascii and not self.uniform:
            if self.type_data == "scalar":
                nb_numbers = nb_pts
            elif self.type_data == "vector":
                nb_numbers = 3 * nb_pts
            elif self.type_data == "symmtensor":
                nb_numbers = 6 * nb_pts
            elif self.type_data == "tensor":
                nb_numbers = 9 * nb_pts
            if self.is_SP:
                dtype = np.dtype(">f4" if self.is_MSB else "<f4")
            else:
                dtype = np.dtype(">f8" if self.is_MSB else "<f8")
            self.values = np.frombuffer(
                data, dtype=dtype, count=nb_numbers, offset=payload_offset
            ).astype(np.float64, copy=True)
        else:
            if self.type_data == "scalar":
                self.values = np.array(
                    [
                        float(s.replace(b")", b"").replace(b";", b""))
                        for s in data.strip().split(b"\n")[:nb_pts]
                    ]
                )
            elif self.type_data in ("vector", "tensor", "symmtensor"):
                lines = data.split(b";")[0].split(b"\n(")
                lines = [line.split(b")")[0] for line in lines]
                data = b" ".join(lines).strip()
                self.values = np.array([float(s) for s in data.split()])

        self.values = np.around(self.values, decimals=precision)
        if self.type_data == "vector":
            self.values_x = self.values[::3]
            self.values_y = self.values[1::3]
            self.values_z = self.values[2::3]

    def _nearest_data(self, boundary, precision):

        bounfile = OpenFoamFile(
            self.pathcase + "/constant/polyMesh/",
            name="boundary",
            verbose=self.verbose,
        )
        ownerfile = OpenFoamFile(
            self.pathcase + "/constant/polyMesh/",
            name="owner",
            verbose=self.verbose,
        )
        id0 = int(bounfile.boundaryface[str.encode(boundary)][b"startFace"])
        nfaces = int(bounfile.boundaryface[str.encode(boundary)][b"nFaces"])
        cell = np.empty(nfaces, dtype=int)
        for i in range(nfaces):
            cell[i] = ownerfile.values[id0 + i]
        data = self.content.split(b"internalField")[1]

        self._parse_field_values(data, precision=precision)
        values = self.values
        if self.uniform:
            self.values = values
        else:
            if self.type_data == "scalar":
                nv = 1
            elif self.type_data == "vector":
                nv = 3
            elif self.type_data == "symmtensor":
                nv = 6
            elif self.type_data == "tensor":
                nv = 9
            self.values = values.reshape(-1, nv)[cell].reshape(-1)
        if self.type_data == "vector":
            self.values_x = self.values[::3]
            self.values_y = self.values[1::3]
            self.values_z = self.values[2::3]

    def _parse_face(self):

        for line in self._iter_lines_stripped():
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        if not self.is_ascii:
            self.nfaces = int(line) - 1
        else:
            self.nfaces = int(line)
        data = self.content.split(line, 1)[1]
        data = b"\n(".join(data.split(b"\n(")[1:])

        lines = data.split(b"\n")
        self.type_data = self.header[b"class"]
        self._faces_dict = None  # lazy (see the faces property)

        if not self.is_ascii:
            nb_numbers = self.nfaces + 1
            dtype = np.dtype(">i4" if self.is_MSB else "<i4")
            nb_bytes = nb_numbers * dtype.itemsize
            self._face_offsets = np.frombuffer(
                data[:nb_bytes], dtype=dtype, count=nb_numbers
            ).astype(np.int64, copy=True)
            self.pointsbyface = self._face_offsets.tolist()
            data = self.content.split(str.encode(str(self.pointsbyface[-1])))[1]
            data = b"\n(".join(data.split(b"\n(")[1:])
            npts_total = int(self._face_offsets[-1])
            self._face_pts = np.frombuffer(
                data, dtype=dtype, count=npts_total
            ).astype(np.int64, copy=True)
        else:
            all_pts = []
            offsets = [0]
            for i, line in enumerate(lines):
                if i == 0:
                    continue
                elif line == b")":
                    break
                else:
                    parts = line.split(b"(")
                    pts = [int(s) for s in parts[1].split(b")")[0].split()]
                    all_pts.extend(pts)
                    offsets.append(len(all_pts))
            self._face_pts = np.array(all_pts, dtype=np.int64)
            self._face_offsets = np.array(offsets, dtype=np.int64)

    def _parse_points(self, precision):

        for line in self._iter_lines_stripped():
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        self.nb_pts = int(line)
        data = self.content.split(b"}", 1)[1]
        data = data.split(line, 1)[1]
        self.type_data = self.header[b"class"]

        if not self.is_ascii:
            nb_numbers = 3 * self.nb_pts
            data = b"\n(".join(data.split(b"\n(")[1:])
            if self.is_SP:
                dtype = np.dtype(">f4" if self.is_MSB else "<f4")
            else:
                dtype = np.dtype(">f8" if self.is_MSB else "<f8")
            nb_bytes = nb_numbers * dtype.itemsize
            self.values = np.frombuffer(
                data[:nb_bytes], dtype=dtype, count=nb_numbers
            ).astype(np.float64, copy=True)
        else:
            lines = data.split(b"\n(")
            lines = [line.split(b")")[0] for line in lines]
            data = b" ".join(lines).strip()
            self.values = np.array([float(s) for s in data.split()])

        self.values = np.around(self.values, decimals=precision)
        self.values_x = self.values[::3]
        self.values_y = self.values[1::3]
        self.values_z = self.values[2::3]

    def _parse_owner(self):

        for line in self._iter_lines_stripped():
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        try:
            self.nb_faces = int(line)
            # data starts after the first count line following the header
            # (the count may also appear in the header note or in the data)
            start = self.content.find(b"}") + 1
            data = self.content[self.content.find(line, start) + len(line) :]
        # for mesh with number of cells <= 10
        except ValueError:
            for line in self._iter_lines_stripped():
                try:
                    line.split(b"(")
                    int(line.split(b"(")[0])
                    break
                except ValueError or TypeError:
                    continue
                break
            self.nb_faces = int(line.split(b"(")[0])
            data = b"\n(" + line.split(b"(", 2)[-1]

        self.type_data = self.header[b"class"]

        if not self.is_ascii:
            nb_numbers = self.nb_faces
            data = b"\n(".join(data.split(b"\n(")[1:])
            dtype = np.dtype(">i4" if self.is_MSB else "<i4")
            nb_bytes = nb_numbers * dtype.itemsize
            self.values = np.frombuffer(
                data[:nb_bytes], dtype=dtype, count=nb_numbers
            ).astype(np.int64, copy=True)
        else:
            lines = data.split(b"\n(")[1:]
            lines = [line.split(b")")[0] for line in lines]
            data = b" ".join(lines).strip()
            self.values = np.array([int(s) for s in data.split()])
        if self.values.min() < 0:
            self.values = self.values[np.where(self.values >= 0)[0]]
            self.nb_faces = self.values.size
        self.nb_cell = np.max(self.values) + 1

    def _parse_sets(self):

        for line in self._iter_lines_stripped():
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        self.nb_cell = int(line)
        data = self.content.split(line, 2)[-1]

        self.type_data = self.header[b"class"]

        if not self.is_ascii:
            nb_numbers = self.nb_cell
            data = b"\n(".join(data.split(b"\n(")[1:])
            dtype = np.dtype(">i4" if self.is_MSB else "<i4")
            nb_bytes = nb_numbers * dtype.itemsize
            self.values = np.frombuffer(
                data[:nb_bytes], dtype=dtype, count=nb_numbers
            ).astype(np.int64, copy=True)
        else:
            lines = data.split(b"\n(")[1:]
            lines = [line.split(b")")[0] for line in lines]
            data = b" ".join(lines).strip()
            self.values = np.array([int(s) for s in data.split()])

    def _determine_order(self, boundary, order, precision):

        xs, ys, zs = readmesh(
            self.pathcase,
            boundary=boundary,
            precision=precision,
            verbose=self.verbose,
        )
        nb_cell = xs.size
        nx = np.unique(xs).size
        ny = np.unique(ys).size
        nz = np.unique(zs).size
        if nx * ny * nz != nb_cell:
            raise ValueError(
                "nx.ny.nz not equal to number of cells."
                "Are you sure that your mesh is cartesian?"
            )

        self.ind = np.lexsort((xs, ys, zs))
        self.shape = (nx, ny, nz)


def typefield(
    path: str,
    time_name: str | None = None,
    name: str | None = None,
    verbose: bool = True,
) -> str:
    """Read OpenFoam field and returns type of field.

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str

    Returns:
        str: type of field

    A way you might use me is:\n
        print("type of alpha field is",
        fluidfoam.typefield('path_of_OpenFoam_case', '0', 'alpha'))

    """

    layout, time_name = _use_processors(path, time_name, name, "field")
    if layout == "collated":
        with tempfile.TemporaryDirectory(prefix="fluidfoam_") as tmp:
            _extract_collated(
                _collated_dirs(path), tmp, [os.path.join(time_name, name)]
            )
            field = OpenFoamFile(
                _make_path(os.path.join(tmp, "processor0"), time_name, name),
                verbose=verbose,
            )
            return field.type_data
    if layout == "uncollated":
        path = _processor_dirs(path)[0]

    path = _make_path(path, time_name, name)

    field = OpenFoamFile(path, verbose=verbose)

    return field.type_data


@_decomposed_fallback("field")
def readfield(
    path: str,
    time_name: str | None = None,
    name: str | None = None,
    structured: bool = False,
    boundary: str | None = None,
    sets: str | None = None,
    region: str | None = None,
    order: str = "F",
    precision: int = 15,
    datatype: str | None = None,
    verbose: bool = True,
) -> np.ndarray:
    """
    Read OpenFoam field and reshape if necessary (structured mesh) and
    possible (not uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        sets: None or str\n
        region: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15)\n
        datatype: None (default) or str ("scalar", "vector"...) necessary in
        case of files without header\n
        verbose : True or False (default: True).

    Returns:
        array: array of type of the field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        field = fluidfoam.readfield('path_of_OpenFoam_case', '0', 'alpha')
    """

    if region is not None:
        sets = region
    field = OpenFoamFile(
        path,
        time_name,
        name,
        structured=structured,
        boundary=boundary,
        sets=sets,
        order=order,
        precision=precision,
        datatype=datatype,
        verbose=verbose,
    )
    values = field.values

    if field.type_data == "scalar":
        if structured and not field.uniform:
            values = np.reshape(values[field.ind], field.shape, order=order)
    elif field.type_data == "vector":
        shape = (3, values.size // 3)
        values = np.reshape(values, shape, order=order)
        if structured and not field.uniform:
            values[0:3, :] = values[0:3, field.ind]
            shape = (3,) + tuple(field.shape)
            values = np.reshape(values, shape, order=order)
    elif field.type_data == "symmtensor":
        shape = (6, values.size // 6)
        values = np.reshape(values, shape, order=order)
        if structured and not field.uniform:
            values[0:6, :] = values[0:6, field.ind]
            shape = (6,) + tuple(field.shape)
            values = np.reshape(values, shape, order=order)
    elif field.type_data == "tensor":
        shape = (9, values.size // 9)
        values = np.reshape(values, shape, order=order)
        if structured and not field.uniform:
            values[0:9, :] = values[0:9, field.ind]
            shape = (9,) + tuple(field.shape)
            values = np.reshape(values, shape, order=order)

    return values


@_decomposed_fallback("field")
def readscalar(
    path: str,
    time_name: str | None = None,
    name: str | None = None,
    structured: bool = False,
    boundary: str | None = None,
    sets: str | None = None,
    region: str | None = None,
    order: str = "F",
    precision: int = 15,
    verbose: bool = True,
) -> np.ndarray:
    """
    Read OpenFoam scalar field and reshape if necessary and possible (not
    uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        sets: None or str\n
        region: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15)\n
        verbose : True or False (default: True).

    Returns:
        array: array of scalar field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        scalar_a = fluidfoam.readscalar('path_of_OpenFoam_case', '0', 'alpha')
    """

    if region is not None:
        sets = region
    scalar = OpenFoamFile(
        path,
        time_name,
        name,
        structured=structured,
        boundary=boundary,
        sets=sets,
        order=order,
        precision=precision,
        datatype="scalar",
        verbose=verbose,
    )
    values = scalar.values

    if scalar.type_data != "scalar":  # pragma: no cover
        raise ValueError("This file does not contain a scalar.")

    if structured:
        values = values[scalar.ind].reshape(scalar.shape, order=order)

    return values


@_decomposed_fallback("field")
def readvector(
    path: str,
    time_name: str | None = None,
    name: str | None = None,
    structured: bool = False,
    boundary: str | None = None,
    sets: str | None = None,
    region: str | None = None,
    order: str = "F",
    precision: int = 15,
    verbose: bool = True,
) -> np.ndarray:
    """
    Read OpenFoam vector field and reshape if necessary and possible (not
    uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        sets: None or str\n
        region: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15)\n
        verbose : True or False (default: True).

    Returns:
        array: array of vector field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        U = fluidfoam.readvector('path_of_OpenFoam_case', '0', 'U')
    """

    if region is not None:
        sets = region
    vector = OpenFoamFile(
        path,
        time_name,
        name,
        structured=structured,
        boundary=boundary,
        sets=sets,
        order=order,
        precision=precision,
        datatype="vector",
        verbose=verbose,
    )
    values = vector.values

    if vector.type_data != "vector":  # pragma: no cover
        raise ValueError("This file does not contain a vector.")

    shape = (3, values.size // 3)
    values = np.reshape(values, shape, order=order)
    if structured:
        if vector.uniform and verbose:
            logger.warning("internalfield is uniform; so no reshape possible...")
        else:
            values[0:3, :] = values[0:3, vector.ind]
            shape = (3,) + tuple(vector.shape)
            values = np.reshape(values, shape, order=order)

    return values


@_decomposed_fallback("field")
def readsymmtensor(
    path: str,
    time_name: str | None = None,
    name: str | None = None,
    structured: bool = False,
    boundary: str | None = None,
    sets: str | None = None,
    region: str | None = None,
    order: str = "F",
    precision: int = 15,
    verbose: bool = True,
) -> np.ndarray:
    """
    Read OpenFoam symmetrical tensor field and reshape if necessary and
    possible (not uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        sets: None or str\n
        region: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15)\n
        verbose : True or False (default: True).

    Returns:
        array: array of symmetrical tensor field; size of the array is the size
        of the interior domain (or of the size of the boundary in case of not
        None boundary)

    A way you might use me is:\n
        sigma = fluidfoam.readsymmtensor('path_of_OpenFoam_case', '0', 'sigma')
    """

    if region is not None:
        sets = region
    symmtensor = OpenFoamFile(
        path,
        time_name,
        name,
        structured=structured,
        boundary=boundary,
        sets=sets,
        order=order,
        precision=precision,
        datatype="symmtensor",
        verbose=verbose,
    )
    values = symmtensor.values

    if symmtensor.type_data != "symmtensor":  # pragma: no cover
        raise ValueError("This file does not contain a symmtensor.")

    shape = (6, values.size // 6)
    values = np.reshape(values, shape, order=order)
    if structured:
        if symmtensor.uniform and verbose:
            logger.warning("internalfield is uniform; so no reshape possible...")
        else:
            values[0:6, :] = values[0:6, symmtensor.ind]
            shape = (6,) + tuple(symmtensor.shape)
            values = np.reshape(values, shape, order=order)

    return values


@_decomposed_fallback("field")
def readtensor(
    path: str,
    time_name: str | None = None,
    name: str | None = None,
    structured: bool = False,
    boundary: str | None = None,
    sets: str | None = None,
    region: str | None = None,
    order: str = "F",
    precision: int = 15,
    verbose: bool = True,
) -> np.ndarray:
    """
    Read OpenFoam tensor field and reshape if necessary and possible
    (not uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        sets: None or str\n
        region: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15)\n
        verbose : True or False (default: True).

    Returns:
        array: array of tensor field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        tens = fluidfoam.readtensor('path_of_OpenFoam_case', '0', 'tens')
    """

    if region is not None:
        sets = region
    tensor = OpenFoamFile(
        path,
        time_name,
        name,
        structured=structured,
        boundary=boundary,
        sets=sets,
        order=order,
        precision=precision,
        datatype="tensor",
        verbose=verbose,
    )

    values = tensor.values

    if tensor.type_data != "tensor":  # pragma: no cover
        raise ValueError("This file does not contain a tensor.")

    shape = (9, values.size // 9)
    values = np.reshape(values, shape, order=order)
    if structured:
        if tensor.uniform and verbose:
            logger.warning("internalfield is uniform; so no reshape possible...")
        else:
            values[0:9, :] = values[0:9, tensor.ind]
            shape = (9,) + tuple(tensor.shape)
            values = np.reshape(values, shape, order=order)

    return values


@_decomposed_fallback("mesh")
def readmesh(
    path: str,
    time_name: str | None = None,
    structured: bool = False,
    boundary: str | None = None,
    sets: str | None = None,
    region: str | None = None,
    order: str = "F",
    precision: int = 15,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Read OpenFoam mesh and reshape if necessary (in cartesian structured mesh).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        structured: False or True\n
        boundary: None or str\n
        sets: None or str\n
        region: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15)\n
        verbose : True or False (default: True).

    Returns:
        array: array of vector (Mesh X, Y, Z); size of the array is the size of
        the interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        X, Y, Z = fluidfoam.readmesh('path_of_OpenFoam_case')
        So X, Y and Z are 1D numpy array with size = nb_cell

    If you play with structured mesh you can shape the X, Y and Z output :\n
        X, Y, Z = fluidfoam.readmesh('path_of_OpenFoam_case', structured=True)
        So X, Y and Z are 3D numpy array with shape = (nx, ny, nz)

    And if you play with dynamic mesh the time_name option is for you

    """

    # hack
    # because in dynamic Mesh cases, no polyMesh directory for initial time
    if time_name == "0":
        time_name = None
    if region is None:
        meshpath = "/constant/polyMesh/"
    else:
        meshpath = "/constant/" + region + "/polyMesh/"
    if not os.path.exists(path + meshpath):
        raise ValueError(
            "No ",
            meshpath,
            " directory in ",
            path,
            " Please verify the directory of your case.",
        )

    if boundary is not None:
        facefile = OpenFoamFile(path + meshpath, name="faces", verbose=verbose)
        if time_name is not None:
            pointfile = OpenFoamFile(
                path=path,
                time_name=time_name,
                name="polyMesh/points",
                precision=precision,
                verbose=verbose,
            )
        else:
            pointfile = OpenFoamFile(
                path + meshpath,
                name="points",
                precision=precision,
                verbose=verbose,
            )
        bounfile = OpenFoamFile(path + meshpath, name="boundary", verbose=verbose)
        id0 = int(bounfile.boundaryface[str.encode(boundary)][b"startFace"])
        nmesh = int(bounfile.boundaryface[str.encode(boundary)][b"nFaces"])

        xs = np.empty(nmesh, dtype=float)
        ys = np.empty(nmesh, dtype=float)
        zs = np.empty(nmesh, dtype=float)

        for i in range(nmesh):
            npts = int(facefile.faces[id0 + i]["npts"])
            id_pts = np.zeros(npts, dtype=int)
            id_pts[0:npts] = facefile.faces[id0 + i]["id_pts"][0:npts]
            xs[i] = np.mean(pointfile.values_x[id_pts[0:npts]])
            ys[i] = np.mean(pointfile.values_y[id_pts[0:npts]])
            zs[i] = np.mean(pointfile.values_z[id_pts[0:npts]])
    else:
        if (
            time_name is None
            and region is None
            and os.path.exists(os.path.join(path, "constant/C"))
        ):
            xs, ys, zs = readvector(
                path, "constant", "C", precision=precision, verbose=verbose
            )
            nmesh = np.size(xs)
        elif (
            time_name is not None
            and region is None
            and os.path.exists(_make_path(path, time_name, "C"))
        ):
            xs, ys, zs = readvector(
                path, time_name, "C", precision=precision, verbose=verbose
            )
            nmesh = np.size(xs)
        else:
            owner = OpenFoamFile(path + meshpath, name="owner", verbose=verbose)
            nmesh = owner.nb_cell
            facefile = OpenFoamFile(
                path + meshpath, name="faces", verbose=verbose
            )
            if time_name is not None and region is None:
                pointfile = OpenFoamFile(
                    path=path,
                    time_name=time_name,
                    name="polyMesh/points",
                    precision=precision,
                    verbose=verbose,
                )
            else:
                pointfile = OpenFoamFile(
                    path + meshpath,
                    name="points",
                    precision=precision,
                    verbose=verbose,
                )
            neigh = OpenFoamFile(
                path + meshpath, name="neighbour", verbose=verbose
            )
            xs, ys, zs, _, _ = _cell_centroids(
                owner, neigh, facefile, pointfile, precision
            )
    if structured:
        nx = np.unique(xs).size
        ny = np.unique(ys).size
        nz = np.unique(zs).size
        if nx * ny * nz != nmesh:
            raise ValueError(
                "nx.ny.nz not equal to number of cells."
                "Are you sure that your mesh is cartesian?"
                "Maybe try to use precision option"
                "For example : "
                "fluidfoam.readmesh(case, True, precision=13)"
            )
        ind = np.lexsort((xs, ys, zs))
        shape = (nx, ny, nz)
        xs = xs[ind].reshape(shape, order=order)
        ys = ys[ind].reshape(shape, order=order)
        zs = zs[ind].reshape(shape, order=order)
    if sets is not None:
        setsfile = OpenFoamFile(
            path=path + meshpath,
            name="sets/" + sets,
            precision=precision,
            verbose=verbose,
        )
        xs = xs[setsfile.values]
        ys = ys[setsfile.values]
        zs = zs[setsfile.values]

    return xs, ys, zs


@_decomposed_fallback("volumes")
def getVolumes(
    path: str,
    time_name: str | None = None,
    structured: bool = False,
    sets: str | None = None,
    region: str | None = None,
    order: str = "F",
    precision: int = 15,
    verbose: bool = True,
    box: tuple | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Reads OpenFoam mesh and returns the cell centroids and cell volumes
    of a given box.

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        structured: False or True\n
        sets: None or str\n
        region: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15)\n
        verbose : True or False (default: True)
        box : tuple of box's dimension: ((xmin, ymin, zmin), (xmax, ymax, zmax))\n
               (if None, includes the whole mesh)\n

    Returns:
        array: two arrays that contain the cell centroids and cell volumes

    A way you might use me is:\n
        centroidList,vol = fluidfoam.getVolumes('path_of_OpenFoam_case')
        So centroidList and vol are the cell centroid and cell volume arrays.


    """

    if time_name == "0":
        time_name = None
    if region is None:
        meshpath = "/constant/polyMesh/"
    else:
        meshpath = "/constant/" + region + "/polyMesh/"
    if not os.path.exists(path + meshpath):
        raise ValueError(
            "No ",
            meshpath,
            " directory in ",
            path,
            " Please verify the directory of your case.",
        )

    owner = OpenFoamFile(path + meshpath, name="owner", verbose=verbose)
    nmesh = owner.nb_cell
    facefile = OpenFoamFile(path + meshpath, name="faces", verbose=verbose)
    if time_name is not None and region is None:
        pointfile = OpenFoamFile(
            path=path,
            time_name=time_name,
            name="polyMesh/points",
            precision=precision,
            verbose=verbose,
        )
    else:
        pointfile = OpenFoamFile(
            path + meshpath, name="points", precision=precision, verbose=verbose
        )
    neigh = OpenFoamFile(path + meshpath, name="neighbour", verbose=verbose)
    xs, ys, zs, up, up_starts = _cell_centroids(
        owner, neigh, facefile, pointfile, precision
    )

    if box is not None:
        # box = ((xmin, ymin, zmin), (xmax, ymax, zmax))
        if len(box[0]) != 3 or len(box[1]) != 3:
            raise ValueError("box mins and maxs must be float tuples of lenght 3")
    else:
        box = (
            (
                np.min(pointfile.values_x),
                np.min(pointfile.values_y),
                np.min(pointfile.values_z),
            ),
            (
                np.max(pointfile.values_x),
                np.max(pointfile.values_y),
                np.max(pointfile.values_z),
            ),
        )

    # Vectorized box check
    in_box = (
        (xs > box[0][0]) & (xs < box[1][0])
        & (ys > box[0][1]) & (ys < box[1][1])
        & (zs > box[0][2]) & (zs < box[1][2])
    )
    in_box_ids = np.flatnonzero(in_box)

    # Volumes: ConvexHull per cell in the box (cannot be vectorized)
    VolCell_all = np.zeros(owner.nb_cell, dtype=float)
    for i in in_box_ids:
        s, e = int(up_starts[i]), int(up_starts[i + 1])
        cell_pts = up[s:e]
        pointsCell = np.column_stack([
            pointfile.values_x[cell_pts],
            pointfile.values_y[cell_pts],
            pointfile.values_z[cell_pts],
        ])
        VolCell_all[i] = ss.ConvexHull(pointsCell).volume

    centroidCell = np.column_stack([xs[in_box], ys[in_box], zs[in_box]])
    VolCell = VolCell_all[VolCell_all != 0]
    if structured:
        nx = np.unique(xs).size
        ny = np.unique(ys).size
        nz = np.unique(zs).size
        if nx * ny * nz != nmesh:
            raise ValueError(
                "nx.ny.nz not equal to number of cells."
                "Are you sure that your mesh is cartesian?"
                "Maybe try to use precision option"
                "For example : "
                "fluidfoam.readmesh(case, True, precision=13)"
            )
        ind = np.lexsort((xs, ys, zs))
        shape = (nx, ny, nz)
        VolCell = VolCell[ind].reshape(shape, order=order)
    return centroidCell, VolCell


if __name__ == "__main__":

    dirs = ["ascii", "asciigz", "bin", "bingz"]

    for d in dirs:
        rep = os.path.join(os.path.dirname(__file__), "../output_samples/", d)

        values = readscalar(rep, "0", "alpha")

        values = readsymmtensor(rep, "0", "sigma")

        values = readtensor(rep, "0", "Taus")

        values = readvector(rep, "0", "U")

        xs, ys, zs = readmesh(rep)
