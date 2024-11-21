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

"""


import os
import gzip
import struct
import numpy as np
import scipy.spatial as ss

# define color
W = '\033[0m'  # white (normal)
R = '\033[31m'  # red
G = '\033[32m'  # green
O = '\033[33m'  # orange
B = '\033[34m'  # blue
P = '\033[35m'  # purple


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
        except:
            pass
    time_list.sort(key=float)
    return time_list[-1]


class OpenFoamFile(object):
    """OpenFoam file parser."""

    def __init__(
        self,
        path,
        time_name=None,
        name=None,
        structured=False,
        boundary=None,
        sets=None,
        order="F",
        precision=15,
        datatype=None,
        verbose=True,
    ):

        self.pathcase = path
        if time_name == "latestTime":
            time_name = _find_latesttime(path)
        if sets is None:
            self.path = _make_path(path, time_name, name)
        else:
            self.path = _make_path(path, time_name, os.path.join(sets, name))
        self.verbose = verbose
        if self.verbose:
            print("Reading file " + self.path)

        if not os.path.exists(self.path) and os.path.exists(self.path + ".gz"):
            self.path += ".gz"

        self.is_compressed = self.path.endswith(".gz")
        if self.is_compressed:
            self._open = gzip.open
        else:
            self._open = open

        with self._open(self.path, "rb") as f:
            self.content = f.read()

        self.lines_stripped = [
            line.strip().replace(b'"', b"").replace(b";", b"")
            for line in self.content.split(b"\n")
        ]

        self.header = self._parse_session(b"FoamFile")

        try:
            self.is_ascii = self.header[b"format"] == b"ascii"
            self.noheader = False
        except KeyError:
            self.is_ascii = True
            self.noheader = True
        try:
            self.is_SP    = b"scalar=32" in self.header[b"arch"]
        except KeyError:
            self.is_SP    = False

        for line in self.lines_stripped:
            if line.startswith(b"dimensions"):
                tmp = (line.split(b"[")[1]).split(b"]")[0]
                self.dimensions = eval(b", ".join(tmp.split()))

        self.boundary = self._parse_session(b"boundaryField")

        if name is None:
            self._parse_data(boundary=boundary,
                             precision=precision,
                             datatype=datatype)
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
            self._parse_data(boundary=boundary,
                             precision=precision,
                             datatype=datatype)
        if structured:
            self._determine_order(boundary=boundary,
                                  order=order,
                                  precision=precision)

    def _parse_boundaryfile(self):

        dict_bounfile = {}
        in_section = False
        previous_line = ""
        level = 0
        for line in self.lines_stripped:
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
                previous_line = line

        return dict_bounfile

    def _parse_session(self, title):

        dict_session = {}
        in_section = False
        previous_line = ""
        level = 0
        for line in self.lines_stripped:
            if line == title:
                in_section = True
                continue
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

        import sys
        if boundary is not None:
            boun = str.encode(boundary)
            if (np.size(self.content.split(boun))<=2):
                iboun =1
            else:
                lines = self.content.split(b"\n")
                iboun = 0
                for line in lines:
                    if boun in line.strip():
                        iboun += 1
                    if boun == line.strip():
                        break

            if iboun >= np.size(self.content.split(boun)):
                print(R+"Error : No boundary/patch "+str(boun)+W)
                sys.exit(1)

            elif b"value" in self.content.split(boun)[iboun].split(b"}")[0]:
                data = self.content.split(boun)[iboun].split(b"value")[1]
            else:
                if self.verbose:
                    print(R+"Warning : No data on boundary/patch")
                    print("Using the values of the nearest cells"+W)
                self._nearest_data(boundary=boundary, precision=precision)
                return
        else:
            try:
                data = self.content.split(b"internalField")[1]
            except IndexError:
                data = self.content

        lines = data.split(b"\n")
        shortline = lines[0].split(b">")[-1]
        words = lines[0].split()

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

        if self.uniform:
            nb_pts = 1
            if not (self.type_data == "scalar"):
                data = shortline.split(b"(")[1]
                data = data.replace(b" ", b"\n")
                data = data.replace(b");", b"\n);")
            else:
                data = words[1].split(b";")[0]
            if self.verbose:
                print(R+"Warning : uniform field  of type "
                        + self.type_data + "!\n")
                print("Only constant field in output\n"+W)
        elif shortline.count(b";") >= 1:
            nb_pts = int(shortline.split(b"(")[0])
            data = shortline.split(b"(")[1]
            data = data.replace(b" ", b"\n")
            data = data.replace(b");", b"\n);")
        elif self.codestream:
            nb_pts = 0
            if self.verbose:
                print(R+"Warning : codeStream field! "
                        + "I can not read the source code!\n"+W)
        else:
            nb_pts = int(lines[1])
            data = b"\n(".join(data.split(b"\n(")[1:])

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
                self.values = np.array(
                    struct.unpack(
                        "{}f".format(nb_numbers),
                        data[: nb_numbers * struct.calcsize("f")],
                    )
                )
            else:
                self.values = np.array(
                    struct.unpack(
                        "{}d".format(nb_numbers),
                        data[: nb_numbers * struct.calcsize("d")],
                    )
                )
        else:
            if self.type_data == "scalar":
                self.values = np.array(
                    [float(s) for s in data.strip().split(b"\n")[:nb_pts]]
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
            verbose=self.verbose
        )
        ownerfile = OpenFoamFile(
            self.pathcase + "/constant/polyMesh/",
            name="owner",
            verbose=self.verbose
        )
        id0 = int(bounfile.boundaryface[str.encode(boundary)][b"startFace"])
        nfaces = int(bounfile.boundaryface[str.encode(boundary)][b"nFaces"])
        cell = np.empty(nfaces, dtype=int)
        for i in range(nfaces):
            cell[i] = ownerfile.values[id0 + i]
        data = self.content.split(b"internalField")[1]

        lines = data.split(b"\n")
        shortline = lines[0].split(b">")[-1]
        words = lines[0].split()

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

        if self.uniform:
            nb_pts = 1
            if not (self.type_data == "scalar"):
                data = shortline.split(b"(")[1]
                data = data.replace(b" ", b"\n")
                data = data.replace(b");", b"\n);")
            else:
                data = words[1].split(b";")[0]
            if self.verbose:
                print(R+"Warning : uniform field  of type "
                        + self.type_data + "!\n")
                print("Only constant field in output\n"+W)
        elif shortline.count(b";") >= 1:
            nb_pts = int(shortline.split(b"(")[0])
            data = shortline.split(b"(")[1]
            data = data.replace(b" ", b"\n")
            data = data.replace(b");", b"\n);")
        elif self.codestream:
            nb_pts = 0
            if self.verbose:
                print(R+"Warning : codeStream field! "
                        + "I can not read the source code!\n"+W)
        else:
            nb_pts = int(lines[1])
            data = b"\n(".join(data.split(b"\n(")[1:])

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
                values = np.array(
                    struct.unpack(
                        "{}f".format(nb_numbers),
                        data[: nb_numbers * struct.calcsize("f")],
                    )
                )
            else:
                values = np.array(
                    struct.unpack(
                        "{}d".format(nb_numbers),
                        data[: nb_numbers * struct.calcsize("d")],
                    )
                )
        else:
            if self.type_data == "scalar":
                values = np.array(
                    [float(s) for s in data.strip().split(b"\n")[:nb_pts]]
                )
            elif self.type_data in ("vector", "tensor", "symmtensor"):
                lines = data.split(b"\n(")
                lines = [line.split(b")")[0] for line in lines]
                data = b" ".join(lines).strip()
                values = np.array([float(s) for s in data.split()])
        values = np.around(values, decimals=precision)
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
            valuesbou = np.empty(nv * nfaces, dtype=float)
            for i in range(nfaces):
                valuesbou[i * nv: (i + 1) * nv] = values[
                    nv * cell[i]: nv * (cell[i] + 1)
                ]
            self.values = valuesbou
        if self.type_data == "vector":
            self.values_x = self.values[::3]
            self.values_y = self.values[1::3]
            self.values_z = self.values[2::3]

    def _parse_face(self):

        for line in self.lines_stripped:
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
        self.faces = {}

        if not self.is_ascii:
            nb_numbers = self.nfaces + 1
            self.pointsbyface = struct.unpack(
                "{}i".format(nb_numbers),
                data[0: nb_numbers * struct.calcsize("i")],
            )
            data = self.content.split(
                str.encode(str(self.pointsbyface[-1])))[1]
            data = b"\n(".join(data.split(b"\n(")[1:])

            for i in range(self.nfaces):
                self.faces[i] = {}
                self.faces[i]["npts"] = self.pointsbyface[i + 1] - \
                    self.pointsbyface[i]
                self.faces[i]["id_pts"] = np.array(
                    struct.unpack(
                        "{}i".format(self.faces[i]["npts"]),
                        data[
                            self.pointsbyface[i]
                            * struct.calcsize("i"): self.pointsbyface[i + 1]
                            * struct.calcsize("i")
                        ],
                    )
                )
        else:
            for i, line in enumerate(lines):
                if i == 0:
                    continue
                elif line == b")":
                    break
                else:
                    self.faces[i - 1] = {}
                    self.faces[i - 1]["npts"] = int(line.split(b"(")[0])
                    self.faces[i - 1]["id_pts"] = [int(s) for s in
                                                   (line.split(b"(")[1].split(b")")[0]).split()]

    def _parse_points(self, precision):

        for line in self.lines_stripped:
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        self.nb_pts = int(line)
        data = self.content.split(b'}', 1)[1]
        data = data.split(line, 1)[1]
        self.type_data = self.header[b"class"]

        if not self.is_ascii:
            nb_numbers = 3 * self.nb_pts
            data = b"\n(".join(data.split(b"\n(")[1:])
            if self.is_SP:
                self.values = np.array(
                    struct.unpack(
                        "{}f".format(nb_numbers),
                        data[: nb_numbers * struct.calcsize("f")],
                    )
                )
            else:
                self.values = np.array(
                    struct.unpack(
                        "{}d".format(nb_numbers),
                        data[: nb_numbers * struct.calcsize("d")],
                    )
                )
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

        for line in self.lines_stripped:
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        try:
            self.nb_faces = int(line)
            data = self.content.split(line, 2)[-1]
        # for mesh with number of cells <= 10 
        except ValueError:
            for line in self.lines_stripped:
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
            self.values = np.array(
                struct.unpack(
                    "{}i".format(nb_numbers),
                    data[: nb_numbers * struct.calcsize("i")],
                )
            )
        else:
            lines = data.split(b"\n(")[1:]
            lines = [line.split(b")")[0] for line in lines]
            data = b" ".join(lines).strip()
            self.values = np.array([int(s) for s in data.split()])
        if self.values.min() < 0:
            self.values = self.values[np.where(self.values>=0)[0]]
            self.nb_faces = self.values.size
        self.nb_cell = np.max(self.values) + 1

    def _parse_sets(self):

        for line in self.lines_stripped:
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
            self.values = np.array(
                struct.unpack(
                    "{}i".format(nb_numbers),
                    data[: nb_numbers * struct.calcsize("i")],
                )
            )
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
            verbose=self.verbose
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


def typefield(path, time_name=None, name=None, verbose=True):
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

    path = _make_path(path, time_name, name)

    field = OpenFoamFile(path, verbose=verbose)

    return field.type_data


def readfield(
    path,
    time_name=None,
    name=None,
    structured=False,
    boundary=None,
    sets=None,
    region=None,
    order="F",
    precision=15,
    datatype=None,
    verbose=True,
):
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


def readscalar(
    path,
    time_name=None,
    name=None,
    structured=False,
    boundary=None,
    sets=None,
    region=None,
    order="F",
    precision=15,
    mode=None,
    verbose=True,
):
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
    if mode == "parallel":
        raise ValueError("Not Implemented")
    else:
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


def readvector(
    path,
    time_name=None,
    name=None,
    structured=False,
    boundary=None,
    sets=None,
    region=None,
    order="F",
    precision=15,
    verbose=True,
):
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
            print("internalfield is uniform; so no reshape possible...")
        else:
            values[0:3, :] = values[0:3, vector.ind]
            shape = (3,) + tuple(vector.shape)
            values = np.reshape(values, shape, order=order)

    return values


def readsymmtensor(
    path,
    time_name=None,
    name=None,
    structured=False,
    boundary=None,
    sets=None,
    region=None,
    order="F",
    precision=15,
    verbose=True,
):
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
    scalar = OpenFoamFile(
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
    values = scalar.values

    if scalar.type_data != "symmtensor":  # pragma: no cover
        raise ValueError("This file does not contain a symmtensor.")

    shape = (6, values.size // 6)
    values = np.reshape(values, shape, order=order)
    if structured:
        if scalar.uniform and verbose:
            print("internalfield is uniform; so no reshape possible...")
        else:
            values[0:6, :] = values[0:6, scalar.ind]
            shape = (6,) + tuple(scalar.shape)
            values = np.reshape(values, shape, order=order)

    return values


def readtensor(
    path,
    time_name=None,
    name=None,
    structured=False,
    boundary=None,
    sets=None,
    region=None,
    order="F",
    precision=15,
    verbose=True,
):
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
    scalar = OpenFoamFile(
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

    values = scalar.values

    if scalar.type_data != "tensor":  # pragma: no cover
        raise ValueError("This file does not contstartFaceain a tensor.")

    shape = (9, values.size // 9)
    values = np.reshape(values, shape, order=order)
    if structured:
        if scalar.uniform and verbose:
            print("internalfield is uniform; so no reshape possible...")
        else:
            values[0:9, :] = values[0:9, scalar.ind]
            shape = (9,) + tuple(scalar.shape)
            values = np.reshape(values, shape, order=order)

    return values


def readmesh(
    path,
    time_name=None,
    structured=False,
    boundary=None,
    sets=None,
    region=None,
    order="F",
    precision=15,
    verbose=True
):
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
        meshpath = "/constant/"+region+"/polyMesh/"
    if not os.path.exists(path+meshpath):
        raise ValueError(
            "No ", meshpath, " directory in ",
            path,
            " Please verify the directory of your case.",
        )

    if boundary is not None:
        facefile = OpenFoamFile(
            path + meshpath, name="faces", verbose=verbose
        )
        if time_name is not None:
            pointfile = OpenFoamFile(
                path=path,
                time_name=time_name,
                name="polyMesh/points",
                precision=precision,
                verbose=verbose
            )
        else:
            pointfile = OpenFoamFile(
                path + meshpath,
                name="points",
                precision=precision,
                verbose=verbose
            )
        bounfile = OpenFoamFile(
            path + meshpath,
            name="boundary",
            verbose=verbose
        )
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
        if (time_name is None and region is None
                and os.path.exists(os.path.join(path, "constant/C"))):
            xs, ys, zs = readvector(
                path, "constant", "C", precision=precision, verbose=verbose
            )
            nmesh = np.size(xs)
        elif (time_name is not None and region is None
              and os.path.exists(_make_path(path, time_name, "C"))):
            xs, ys, zs = readvector(
                path, time_name, "C", precision=precision, verbose=verbose
            )
            nmesh = np.size(xs)
        else:
            owner = OpenFoamFile(
                path + meshpath, name="owner", verbose=verbose
            )
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
                    verbose=verbose
                )
            else:
                pointfile = OpenFoamFile(
                    path + meshpath,
                    name="points",
                    precision=precision,
                    verbose=verbose
                )
            neigh = OpenFoamFile(
                path + meshpath, name="neighbour", verbose=verbose
            )
            xs = np.empty(owner.nb_cell, dtype=float)
            ys = np.empty(owner.nb_cell, dtype=float)
            zs = np.empty(owner.nb_cell, dtype=float)
            face = {}
            for i in range(neigh.nb_faces):
                if not neigh.values[i] in face:
                    face[neigh.values[i]] = list()
                face[neigh.values[i]].append(facefile.faces[i]["id_pts"][:])
            for i in range(owner.nb_faces):
                if not owner.values[i] in face:
                    face[owner.values[i]] = list()
                face[owner.values[i]].append(facefile.faces[i]["id_pts"][:])
            for i in range(owner.nb_cell):
                xs[i] = np.mean(
                    pointfile.values_x[np.unique(np.concatenate(face[i])[:])]
                )
                ys[i] = np.mean(
                    pointfile.values_y[np.unique(np.concatenate(face[i])[:])]
                )
                zs[i] = np.mean(
                    pointfile.values_z[np.unique(np.concatenate(face[i])[:])]
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
            path=path+meshpath,
            name="sets/"+sets,
            precision=precision,
            verbose=verbose
        )
        xs = xs[setsfile.values]
        ys = ys[setsfile.values]
        zs = zs[setsfile.values]

    return xs, ys, zs





def getVolumes(
    path,
    time_name=None,
    structured=False,
    sets=None,
    region=None,
    order="F",
    precision=15,
    verbose=True,
    box=None
):
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
        meshpath = "/constant/"+region+"/polyMesh/"
    if not os.path.exists(path+meshpath):
        raise ValueError(
            "No ", meshpath, " directory in ",
            path,
            " Please verify the directory of your case.",
        )

    owner = OpenFoamFile(
        path + meshpath, name="owner", verbose=verbose
    )
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
            verbose=verbose
        )
    else:
        pointfile = OpenFoamFile(
            path + meshpath,
            name="points",
            precision=precision,
            verbose=verbose
        )
    neigh = OpenFoamFile(
        path + meshpath, name="neighbour", verbose=verbose
    )
    xs = np.empty(owner.nb_cell, dtype=float)
    ys = np.empty(owner.nb_cell, dtype=float)
    zs = np.empty(owner.nb_cell, dtype=float)
    face = {}
    for i in range(neigh.nb_faces):
        if not neigh.values[i] in face:
            face[neigh.values[i]] = list()
        face[neigh.values[i]].append(facefile.faces[i]["id_pts"][:])
    for i in range(owner.nb_faces):
        if not owner.values[i] in face:
            face[owner.values[i]] = list()
        face[owner.values[i]].append(facefile.faces[i]["id_pts"][:])

    if box != None:
        # box = ((xmin, ymin, zmin), (xmax, ymax, zmax))
        if len(box[0]) != 3 or len(box[1]) != 3:
            raise ValueError("box mins and maxs must be float tuples of lenght 3")
    else:
        minx = np.min(pointfile.values_x)
        miny = np.min(pointfile.values_y)
        minz = np.min(pointfile.values_z)
        maxx = np.max(pointfile.values_x)
        maxy = np.max(pointfile.values_y)
        maxz = np.max(pointfile.values_z)
        box = ((minx, miny, minz), (maxx, maxy, maxz))

    centroidCell = np.empty((0,3), dtype=float)
    VolCell_all = np.empty(owner.nb_cell, dtype=float)

    for i in range(owner.nb_cell):
        xs[i] = np.mean(
            pointfile.values_x[np.unique(np.concatenate(face[i])[:])]
        )
        ys[i] = np.mean(
            pointfile.values_y[np.unique(np.concatenate(face[i])[:])]
        )
        zs[i] = np.mean(
            pointfile.values_z[np.unique(np.concatenate(face[i])[:])]
        )

        if box[0][0] < xs[i] < box[1][0] and box[0][1] < ys[i] < box[1][1] and box[0][2] < zs[i] < box[1][2]:
            pointsCell=[]
            for k in zip(np.unique(np.concatenate(face[i])[:])):
                pointsCell.append([pointfile.values_x[k],pointfile.values_y[k],pointfile.values_z[k]])

            # Add 3D elements into the empty array
            element = np.array([xs[i], ys[i], zs[i]])
            centroidCell = np.append(centroidCell, [element], axis=0)
            VolCell_all[i]=ss.ConvexHull(pointsCell).volume
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
    return centroidCell,VolCell


if __name__ == "__main__":

    dirs = ["ascii", "asciigz", "bin", "bingz"]

    for d in dirs:
        rep = os.path.join(os.path.dirname(__file__), "../output_samples/", d)

        values = readscalar(rep, "0", "alpha")

        values = readsymmtensor(rep, "0", "sigma")

        values = readtensor(rep, "0", "Taus")

        values = readvector(rep, "0", "U")

        xs, ys, zs = readmesh(rep)
