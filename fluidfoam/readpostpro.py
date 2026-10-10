"""Read OpenFoam PostProcessing Files for Python
=======================================================================
This module provides functions to list and read OpenFoam PostProcessing Files:

.. autofunction:: readforce
.. autofunction:: readprobes
"""

import os
import numpy as np

# from glob import glob


def _list_times(path):
    """Names of the time directories of path, sorted by value."""
    time_list = []
    for directory in os.listdir(path):
        try:
            float(directory)
            time_list.append(directory)
        except ValueError:
            pass
    time_list.sort(key=float)
    return time_list


def _find_latesttime(path):
    return _list_times(path)[-1]


def _postprocessing_path(path, dirname):
    """Directory of a postProcessing function object: path/dirname if it
    exists, else path/postProcessing/dirname."""
    if os.path.exists(os.path.join(path, dirname)):
        return os.path.join(path, dirname)
    return os.path.join(path, "postProcessing", dirname)


def _first_new_row(time_merge, time_new):
    """Index of the first row of time_new that is later than the last time
    already merged; None if there is no such row."""
    if time_merge.size == 0:
        return 0 if time_new.size > 0 else None
    new_rows = np.flatnonzero(time_new > time_merge[-1])
    return int(new_rows[0]) if new_rows.size > 0 else None


def _data_rows(lines):
    """Data lines: the comment lines (#) and the empty lines are skipped."""
    return [line for line in lines if b"#" not in line and line.strip()]


def _strip_parentheses(line):
    return line.replace(b"(", b" ").replace(b")", b" ")


def readforce(path, namepatch="forces", time_name="0", name="forces"):
    """read the data contained in the force file .
    create the forces variables in the Forcesfile object

    Args:
        path: str\n
        namepatch: str\n
        time_name: str ('latestTime' and 'mergeTime' are supported)\n
        name: str

    Returns:
        array: array of force field; size of the array is the size of the
        time (an empty array if the file contains no data)

    A way you might use me is:\n
        force = readforce(path='path_of_OpenFoam_case', namepatch='forces',
                          time_name='0', name='forces')

    """

    # path_namepatch = glob(f'{path}/**/'+namepatch, recursive=True)[0]
    path_namepatch = _postprocessing_path(path, namepatch)
    if time_name == "latestTime":
        time_name = _find_latesttime(path_namepatch)
    elif time_name == "mergeTime":
        tab_merge = None
        for timename in _list_times(path_namepatch):
            try:
                tab = readforce(path, namepatch, timename, name + "_" + timename)
            except Exception:
                try:
                    tab = readforce(path, namepatch, timename, name)
                except Exception as error:
                    print("An exception occurred:", error)
                    continue
            if tab.ndim < 2:  # no data in this time directory
                continue
            if tab_merge is None:
                tab_merge = tab
                continue
            first = _first_new_row(tab_merge[:, 0], tab[:, 0])
            if first is not None:
                tab_merge = np.concatenate([tab_merge, tab[first:, :]])
        return np.array([]) if tab_merge is None else tab_merge

    with open(os.path.join(path_namepatch, time_name, name + ".dat"), "rb") as f:
        content = f.read()
    # the last line is ignored if it is not terminated (it may be being
    # written)
    rows = _data_rows(content.split(b"\n")[:-1])
    if not rows:
        return np.array([])
    ncols = len(_strip_parentheses(rows[0]).split())
    values = np.array(_strip_parentheses(b"\n".join(rows)).split(), dtype=float)
    if values.size != len(rows) * ncols:
        raise ValueError(
            "The lines of the file do not have the same number of columns"
        )
    return values.reshape(len(rows), ncols)


def readprobes(
    path, probes_name="probes", time_name="0", name="U", verbose=True
):
    """read the data contained in the probes file.

    Args:
        path: str\n
        probes_name: str\n
        time_name: str ('latestTime' and 'mergeTime' are supported)\n
        name: str\n
        verbose: bool (default: True)

    Returns:
        tuple: array of the probes locations, shape (number of probes, 3);
        array of the time values; array of the probes data, shape
        (number of times, number of probes, number of components)

    A way you might use me is:\n
        probes_loc, time_vect, data = readprobes(
            path='path_of_OpenFoam_case', probes_name='probes',
            time_name='0', name='U')

    """

    # path_probes_name = glob(f'{path}/**/'+probes_name, recursive=True)[0]
    path_probes_name = _postprocessing_path(path, probes_name)
    if time_name == "latestTime":
        time_name = _find_latesttime(path_probes_name)
    elif time_name == "mergeTime":
        probes_loc = None
        timevect_merge = np.array([])
        tab_merge = np.array([])
        for timename in _list_times(path_probes_name):
            probes_loc, time_vect, tab = readprobes(
                path, probes_name, timename, name, verbose
            )
            first = _first_new_row(timevect_merge, time_vect)
            if first is not None:
                if timevect_merge.size == 0:
                    timevect_merge, tab_merge = time_vect, tab
                else:
                    timevect_merge = np.concatenate(
                        [timevect_merge, time_vect[first:]]
                    )
                    tab_merge = np.concatenate([tab_merge, tab[first:, :]])
        return probes_loc, timevect_merge, tab_merge

    with open(os.path.join(path_probes_name, time_name, name), "rb") as f:
        content = f.read().split(b"\n")

    # header: the comment lines
    j = 0
    for line in content:
        if b"#" in line:
            j += 1
        else:
            break
    # probe lines are the header lines holding the coordinates "(x y z)"
    probe_lines = [line for line in content[:j] if b"(" in line]
    probes_loc = np.zeros([len(probe_lines), 3], dtype=float)
    for ip, line in enumerate(probe_lines):
        for k in range(3):
            probes_loc[ip, k] = line.split(b"(")[1].split(b")")[0].split()[k]

    # data: one line per time, with parentheses around the vectors:
    #   time (u0 v0 w0) (u1 v1 w1) ...   or   time p0 p1 ... for a scalar
    rows = _data_rows(content[j:])
    if not rows:
        return probes_loc, np.array([]), np.array([])
    first_row = rows[0].replace(b")", b"").split(b"(")
    if len(first_row) > 1:  # vector or tensor
        dim = len(first_row[1].split())
        n_probes = len(first_row) - 1
    else:  # scalar
        dim = 1
        n_probes = len(first_row[0].split()) - 1
    ncols = 1 + n_probes * dim
    # an incomplete last line (being written) is ignored
    if len(_strip_parentheses(rows[-1]).split()) != ncols:
        rows = rows[:-1]
        if not rows:
            return probes_loc, np.array([]), np.array([])

    if verbose:
        print("Reading file " + os.path.join(path_probes_name, time_name, name))
        print(str(n_probes) + " probes over " + str(len(rows)) + " timesteps")

    values = np.array(_strip_parentheses(b"\n".join(rows)).split(), dtype=float)
    if values.size != len(rows) * ncols:
        raise ValueError(
            "The lines of the file do not have the same number of values"
        )
    values = values.reshape(len(rows), ncols)
    time_vect = values[:, 0].copy()
    tab = np.ascontiguousarray(values[:, 1:]).reshape(len(rows), n_probes, dim)
    return probes_loc, time_vect, tab


if __name__ == "__main__":

    rep = "../output_samples/ascii"
    probes_loc, time_vect, dummy = readprobes(rep, time_name="latestTime")
