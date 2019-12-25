"""Read OpenFoam Files for Python
===========================================
This module provides functions to read OpenFoam Files:

.. autofunction:: readmesh

.. autofunction:: readfield

.. autofunction:: readscalar

.. autofunction:: readvector

.. autofunction:: readsymmtensor

.. autofunction:: readtensor

.. autofunction:: typefield

"""


import os
import gzip
import struct
import numpy as np


def _make_path(path, time_name=None, name=None):
    if time_name is not None and name is None:  # pragma: no cover
        path = os.path.join(path, time_name)
    elif name is not None and time_name is None:  # pragma: no cover
        path = os.path.join(path, name)
    elif name is not None and time_name is not None:
        path = os.path.join(path, time_name, name)
    if not os.path.exists(path) and os.path.exists(path + '.gz'):
        path += '.gz'

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
    return(time_list[-1])    


class OpenFoamFile(object):
    """OpenFoam file parser."""
    def __init__(self, path, time_name=None, name=None, structured=False,
                 boundary=None, order="F", precision=15):

        self.pathcase = path
        if time_name is 'latestTime':
            time_name = _find_latesttime(path)
        self.path = _make_path(path, time_name, name)
        print('Reading file ' + self.path)

        if not os.path.exists(self.path) and os.path.exists(self.path + '.gz'):
            self.path += '.gz'

        self.is_compressed = self.path.endswith('.gz')
        if self.is_compressed:
            self._open = gzip.open
        else:
            self._open = open

        with self._open(self.path, 'rb') as f:
            self.content = f.read()

        self.lines_stripped = [line.strip().replace(
            b'"', b'').replace(b';', b'')
            for line in self.content.split(b'\n')]

        self.header = self._parse_session(b'FoamFile')

        self.is_ascii = self.header[b'format'] == b'ascii'

        for line in self.lines_stripped:
            if line.startswith(b'dimensions'):
                tmp = (line.split(b'[')[1]).split(b']')[0]
                self.dimensions = eval(b', '.join(tmp.split()))

        self.boundary = self._parse_session(b'boundaryField')

        if name is 'boundary':
            self.boundaryface = self._parse_boundaryfile()
        elif name is 'faces':
            self._parse_face()
        elif name is 'points':
            self._parse_points(precision=precision)
        elif (name is 'owner') or (name is 'neighbour'):
            self._parse_owner()
        else:
            self._parse_data(boundary=boundary, precision=precision)
        if structured:
            self._determine_order(order=order, precision=precision)

    def _parse_boundaryfile(self):

        dict_bounfile = {}
        in_section = False
        previous_line = ''
        level = 0
        for line in self.lines_stripped:
            if line == b'(':
                in_section = True
                level += 1
                continue
            if in_section is True:
                if line == b'{':
                    level += 1
                    continue
                elif line == b'}' or line == b')':
                    level -= 1
                else:
                    tmp = line.replace(b'"', b'').split()
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
        previous_line = ''
        level = 0
        for line in self.lines_stripped:
            if line == title:
                in_section = True
                continue
            if in_section is True:
                if line == b'{':
                    level += 1
                    continue
                elif line == b'}':
                    level -= 1
                else:
                    tmp = line.replace(b'"', b'').split()
                    if len(tmp) > 1:
                        if level == 1:
                            dict_session[tmp[0]] = tmp[1]
                        elif level == 2:
                            if previous_line not in dict_session:
                                dict_session[previous_line] = {}
                            dict_session[previous_line][tmp[0]] = tmp[1]
                if level == 0:
                    break
                previous_line = line

        return dict_session

    def _parse_data(self, boundary, precision=15):

        if boundary is not None:
            boun = str.encode(boundary)
            if b'value' in self.content.split(boun)[1].split(b'}')[0]:
                data = self.content.split(boun)[1].split(b'value')[1]
            else:
                print('Warning : No data on patch')
                print('Nearest cells values use')
                self._nearest_data(boundary=boundary, precision=precision)
                return
        else:
            data = self.content.split(b'internalField')[1]

        lines = data.split(b'\n')
        shortline = (lines[0].split(b'>')[-1])
        words = lines[0].split()

        self.nonuniform = words[0] == b'nonuniform'
        self.uniform = words[0] == b'uniform'
        self.codestream = words[0] == b'#codeStream'
        self.short = shortline[-1] == b';'

        self.type_data = self.header[b'class']

        if b'ScalarField' in self.type_data:
            self.type_data = 'scalar'
        elif b'VectorField' in self.type_data:
            self.type_data = 'vector'
        elif b'SymmTensorField' in self.type_data:
            self.type_data = 'symmtensor'
        elif b'TensorField' in self.type_data:
            self.type_data = 'tensor'

        if self.uniform:
            nb_pts = 1
            if not (self.type_data is 'scalar'):
                data = shortline.split(b'(')[1]
                data = data.replace(b' ', b'\n')
                data = data.replace(b');', b'\n);')
            else:
                data = words[1].split(b';')[0]
            print("Warning : uniform field  of type " + self.type_data + "!\n")
            print("Only constant field in output\n")
        elif shortline.count(b';') >= 1:
            nb_pts = int(shortline.split(b'(')[0])
            data = shortline.split(b'(')[1]
            data = data.replace(b' ', b'\n')
            data = data.replace(b');', b'\n);')
        elif self.codestream:
            nb_pts = 0
            print("Warning : codeStream field! I can not read the source code!\n")
        else:
            nb_pts = int(lines[1])
            data = b'\n('.join(data.split(b'\n(')[1:])

        if not self.is_ascii and not self.uniform:
            if self.type_data == 'scalar':
                nb_numbers = nb_pts
            elif self.type_data == 'vector':
                nb_numbers = 3*nb_pts
            elif self.type_data == 'symmtensor':
                nb_numbers = 6*nb_pts
            elif self.type_data == 'tensor':
                nb_numbers = 9*nb_pts
            self.values = np.array(struct.unpack(
                '{}d'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('d')]))
        else:
            if self.type_data == 'scalar':
                self.values = np.array(
                    [float(s)
                     for s in data.strip().split(b'\n')[:nb_pts]])
            elif self.type_data in ('vector', 'tensor', 'symmtensor'):
                lines = data.split(b';')[0].split(b'\n(')
                lines = [line.split(b')')[0] for line in lines]
                data = b' '.join(lines).strip()
                self.values = np.array([float(s) for s in data.split()])

        self.values = np.around(self.values, decimals=precision)
        if self.type_data == 'vector':
            self.values_x = self.values[::3]
            self.values_y = self.values[1::3]
            self.values_z = self.values[2::3]

    def _nearest_data(self, boundary, precision):

        bounfile = OpenFoamFile(self.pathcase + '/constant/polyMesh/',
                                name='boundary')
        ownerfile = OpenFoamFile(self.pathcase + '/constant/polyMesh/',
                                 name='owner')
        id0 = int(bounfile.boundaryface[str.encode(boundary)][b'startFace'])
        nfaces = int(bounfile.boundaryface[str.encode(boundary)][b'nFaces'])
        cell = np.empty(nfaces, dtype=int)
        for i in range(nfaces):
            cell[i] = ownerfile.values[id0+i]
        data = self.content.split(b'internalField')[1]

        lines = data.split(b'\n')
        shortline = (lines[0].split(b'>')[-1])
        words = lines[0].split()

        self.nonuniform = words[0] == b'nonuniform'
        self.uniform = words[0] == b'uniform'
        self.codestream = words[0] == b'#codeStream'
        self.short = shortline[-1] == b';'

        self.type_data = self.header[b'class']

        if b'ScalarField' in self.type_data:
            self.type_data = 'scalar'
        elif b'VectorField' in self.type_data:
            self.type_data = 'vector'
        elif b'SymmTensorField' in self.type_data:
            self.type_data = 'symmtensor'
        elif b'TensorField' in self.type_data:
            self.type_data = 'tensor'

        if self.uniform:
            nb_pts = 1
            if not (self.type_data is 'scalar'):
                data = shortline.split(b'(')[1]
                data = data.replace(b' ', b'\n')
                data = data.replace(b');', b'\n);')
            else:
                data = words[1].split(b';')[0]
            print("Warning : uniform field  of type " + self.type_data + "!\n")
            print("Only constant field in output\n")
        elif shortline.count(b';') >= 1:
            nb_pts = int(shortline.split(b'(')[0])
            data = shortline.split(b'(')[1]
            data = data.replace(b' ', b'\n')
            data = data.replace(b');', b'\n);')
        elif self.codestream:
            nb_pts = 0
            print("Warning : codeStream field! I can not read the source code!\n")
        else:
            nb_pts = int(lines[1])
            data = b'\n('.join(data.split(b'\n(')[1:])

        if not self.is_ascii and not self.uniform:
            if self.type_data == 'scalar':
                nb_numbers = nb_pts
            elif self.type_data == 'vector':
                nb_numbers = 3*nb_pts
            elif self.type_data == 'symmtensor':
                nb_numbers = 6*nb_pts
            elif self.type_data == 'tensor':
                nb_numbers = 9*nb_pts
            values = np.array(struct.unpack(
                '{}d'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('d')]))
        else:
            if self.type_data == 'scalar':
                values = np.array(
                    [float(s)
                     for s in data.strip().split(b'\n')[:nb_pts]])
            elif self.type_data in ('vector', 'tensor', 'symmtensor'):
                lines = data.split(b'\n(')
                lines = [line.split(b')')[0] for line in lines]
                data = b' '.join(lines).strip()
                values = np.array([float(s) for s in data.split()])
        values = np.around(values, decimals=precision)
        if self.uniform:
            self.values = values
        else:
            if self.type_data == 'scalar':
                nv = 1
            elif self.type_data == 'vector':
                nv = 3
            elif self.type_data == 'symmtensor':
                nv = 6
            elif self.type_data == 'tensor':
                nv = 9
            valuesbou = np.empty(nv*nfaces, dtype=float)
            for i in range(nfaces):
                valuesbou[i*nv:(i+1)*nv] = values[nv*cell[i]:nv*(cell[i]+1)]
            self.values = valuesbou
        if self.type_data == 'vector':
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
            self.nfaces = int(line)-1
        else:
            self.nfaces = int(line)
        data = self.content.split(line, 1)[1]
        data = b'\n('.join(data.split(b'\n(')[1:])

        lines = data.split(b'\n')
        self.type_data = self.header[b'class']
        self.faces = {}

        if not self.is_ascii:
            nb_numbers = self.nfaces+1
            self.pointsbyface = struct.unpack(
                '{}i'.format(nb_numbers),
                data[0:nb_numbers*struct.calcsize('i')])
            data = self.content.split(
                str.encode(str(self.pointsbyface[-1])))[1]
            data = b'\n('.join(data.split(b'\n(')[1:])

            for i in range(self.nfaces):
                self.faces[i] = {}
                self.faces[i]['npts'] = (
                    self.pointsbyface[i+1] - self.pointsbyface[i])
                self.faces[i]['id_pts'] = np.array(struct.unpack(
                    '{}i'.format(self.faces[i]['npts']),
                    data[self.pointsbyface[i]*struct.calcsize('i'):
                         self.pointsbyface[i+1]*struct.calcsize('i')]))
        else:
            for i, line in enumerate(lines):
                if i == 0:
                    continue
                elif line == b')':
                    break
                else:
                    self.faces[i-1] = {}
                    self.faces[i-1]['npts'] = line.split(b'(')[0]
                    self.faces[i-1]['id_pts'] = [int(s) for s in ((
                        line.split(b'(')[1].split(b')')[0]).split())]

    def _parse_points(self, precision):

        for line in self.lines_stripped:
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        self.nb_pts = int(line)
        data = self.content.split(line, 1)[1]

        self.type_data = self.header[b'class']

        if not self.is_ascii:
            nb_numbers = 3*self.nb_pts
            data = b'\n('.join(data.split(b'\n(')[1:])
            self.values = np.array(struct.unpack(
                '{}d'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('d')]))
        else:
            lines = data.split(b'\n(')
            lines = [line.split(b')')[0] for line in lines]
            data = b' '.join(lines).strip()
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
        self.nb_faces = int(line)
        data = self.content.split(line, 2)[2]

        self.type_data = self.header[b'class']

        if not self.is_ascii:
            nb_numbers = self.nb_faces
            data = b'\n('.join(data.split(b'\n(')[1:])
            self.values = np.array(struct.unpack(
                '{}i'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('i')]))
        else:
            lines = data.split(b'\n(')
            lines = [line.split(b')')[0] for line in lines]
            data = b' '.join(lines).strip()
            self.values = np.array([int(s) for s in data.split()])
        self.nb_cell = np.max(self.values) + 1

    def _determine_order(self, order, precision):

        xs, ys, zs = readmesh(self.pathcase, precision=precision)
        nb_cell = xs.size
        nx = np.unique(xs).size
        ny = np.unique(ys).size
        nz = np.unique(zs).size
        if nx*ny*nz != nb_cell:
            raise ValueError('nx.ny.nz not equal to number of cells.'
                             'Are you sure that your mesh is cartesian?')

        self.ind = np.lexsort((xs, ys, zs))
        self.shape = (nx, ny, nz)


def typefield(path, time_name=None, name=None):
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

    field = OpenFoamFile(path)

    return field.type_data


def readfield(path, time_name=None, name=None, structured=False, boundary=None,
              order="F", precision=15):
    """
    Read OpenFoam field and reshape if necessary (structured mesh) and
    possible (not uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15).
        If decimals is negative, it specifies the number of positions to the
        left of the decimal point.

    Returns:
        array: array of type of the field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        field = fluidfoam.readfield('path_of_OpenFoam_case', '0', 'alpha')
    """

    field = OpenFoamFile(path, time_name, name, structured=structured,
                         boundary=boundary, order=order, precision=precision)
    values = field.values

    if field.type_data == 'scalar':
        if structured and not field.uniform:
            values = np.reshape(values[field.ind], field.shape, order = order)
    elif field.type_data == 'vector':
        shape = (3, values.size//3)
        values = np.reshape(values, shape, order = order)
        if structured and not field.uniform:
            values[0:3, :] = values[0:3, field.ind]
            shape = (3,) + tuple(field.shape)
            values = np.reshape(values, shape, order = order)
    elif field.type_data == 'symmtensor':
        shape = (6, values.size//6)
        values = np.reshape(values, shape, order = order)
        if structured and not field.uniform:
            values[0:6, :] = values[0:6, field.ind]
            shape = (6,) + tuple(field.shape)
            values = np.reshape(values, shape, order = order)
    elif field.type_data == 'tensor':
        shape = (9, values.size//9)
        values = np.reshape(values, shape, order = order)
        if structured and not field.uniform:
            values[0:9, :] = values[0:9, field.ind]
            shape = (9,) + tuple(field.shape)
            values = np.reshape(values, shape, order = order)

    return values


def readscalar(path, time_name=None, name=None, structured=False, boundary=None,
               order="F", precision=15, mode=None):
    """
    Read OpenFoam scalar field and reshape if necessary and possible (not
    uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15).
        If decimals is negative, it specifies the number of positions to the
        left of the decimal point.

    Returns:
        array: array of scalar field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        scalar_a = fluidfoam.readscalar('path_of_OpenFoam_case', '0', 'alpha')
    """
    if mode=='parallel':
        raise ValueError('Not Implemented')
    else:
        scalar = OpenFoamFile(path, time_name, name, structured=structured,
                              boundary=boundary, order=order,
                              precision=precision)
        values = scalar.values

        if scalar.type_data != 'scalar':  # pragma: no cover
            raise ValueError('This file does not contain a scalar.')

        if structured:
            values = values[scalar.ind].reshape(scalar.shape, order = order)

    return values


def readvector(path, time_name=None, name=None, structured=False, boundary=None,
               order="F", precision=15):
    """
    Read OpenFoam vector field and reshape if necessary and possible (not
    uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15).
        If decimals is negative, it specifies the number of positions to the
        left of the decimal point.

    Returns:
        array: array of vector field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        U = fluidfoam.readvector('path_of_OpenFoam_case', '0', 'U')
    """

    vector = OpenFoamFile(path, time_name, name, structured=structured,
                          boundary=boundary, order=order, precision=precision)
    values = vector.values

    if vector.type_data != 'vector':  # pragma: no cover
        raise ValueError('This file does not contain a vector.')

    shape = (3, values.size//3)
    values = np.reshape(values, shape, order = order)
    if structured:
        if vector.uniform:
            print("internalfield is uniform; so no reshape possible...")
        else:
            values[0:3, :] = values[0:3, vector.ind]
            shape = (3,) + tuple(vector.shape)
            values = np.reshape(values, shape, order = order)

    return values


def readsymmtensor(path, time_name=None, name=None, structured=False,
                   boundary=None, order="F", precision=15):
    """
    Read OpenFoam symmetrical tensor field and reshape if necessary and
    possible (not uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15).
        If decimals is negative, it specifies the number of positions to the
        left of the decimal point.

    Returns:
        array: array of symmetrical tensor field; size of the array is the size
        of the interior domain (or of the size of the boundary in case of not
        None boundary)

    A way you might use me is:\n
        sigma = fluidfoam.readsymmtensor('path_of_OpenFoam_case', '0', 'sigma')
    """

    scalar = OpenFoamFile(path, time_name, name, structured=structured,
                          boundary=boundary, order=order, precision=precision)
    values = scalar.values

    if scalar.type_data != 'symmtensor':  # pragma: no cover
        raise ValueError('This file does not contain a symmtensor.')

    shape = (6, values.size//6)
    values = np.reshape(values, shape, order = order)
    if structured:
        if scalar.uniform:
            print("internalfield is uniform; so no reshape possible...")
        else:
            values[0:6, :] = values[0:6, scalar.ind]
            shape = (6,) + tuple(scalar.shape)
            values = np.reshape(values, shape, order = order)

    return values


def readtensor(path, time_name=None, name=None, structured=False, boundary=None,
               order="F", precision=15):
    """
    Read OpenFoam tensor field and reshape if necessary and possible
    (not uniform field).

    Args:
        path: str\n
        time_name: str ('latestTime' is supported)\n
        name: str\n
        structured: False or True\n
        boundary: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15).
        If decimals is negative, it specifies the number of positions to the
        left of the decimal point.

    Returns:
        array: array of tensor field; size of the array is the size of the
        interior domain (or of the size of the boundary in case of not None
        boundary)

    A way you might use me is:\n
        tens = fluidfoam.readtensor('path_of_OpenFoam_case', '0', 'tens')
    """

    scalar = OpenFoamFile(path, time_name, name, structured=structured,
                          boundary=boundary, order=order, precision=precision)

    values = scalar.values

    if scalar.type_data != 'tensor':  # pragma: no cover
        raise ValueError('This file does not contstartFaceain a tensor.')

    shape = (9, values.size//9)
    values = np.reshape(values, shape, order = order)
    if structured:
        if scalar.uniform:
            print("internalfield is uniform; so no reshape possible...")
        else:
            values[0:9, :] = values[0:9, scalar.ind]
            shape = (9,) + tuple(scalar.shape)
            values = np.reshape(values, shape, order = order)

    return values


def readmesh(rep, structured=False, boundary=None, order="F", precision=15):
    """
    Read OpenFoam mesh and reshape if necessary (in cartesian structured mesh).

    Args:
        rep: str\n
        structured: False or True\n
        boundary: None or str\n
        order: "F" (default) or "C" \n
        precision : Number of decimal places to round to (default: 15).
        If decimals is negative, it specifies the number of positions to the
        left of the decimal point.

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

    """

# backward compatibility (when ccx/ccy/ccz need)!!
    if not os.path.exists(os.path.join(rep, 'constant/polyMesh')):
        rep = rep + '/..'

    if not os.path.exists(os.path.join(rep, 'constant/polyMesh')):
        raise ValueError('No constant/polyMesh directory in ', rep,
                         ' Please verify the directory of your case.')

    if boundary is not None:
        facefile = OpenFoamFile(rep + '/constant/polyMesh/', name='faces')
        pointfile = OpenFoamFile(rep + '/constant/polyMesh/', name='points',
                                 precision=precision)
        bounfile = OpenFoamFile(rep + '/constant/polyMesh/', name='boundary')
        id0 = int(bounfile.boundaryface[str.encode(boundary)][b'startFace'])
        nfaces = int(bounfile.boundaryface[str.encode(boundary)][b'nFaces'])

        xs = np.empty(nfaces, dtype=float)
        ys = np.empty(nfaces, dtype=float)
        zs = np.empty(nfaces, dtype=float)

        for i in range(nfaces):
            npts = int(facefile.faces[id0+i]['npts'])
            id_pts = np.zeros(npts, dtype=int)
            id_pts[0:npts] = facefile.faces[id0+i]['id_pts'][0:npts]
            xs[i] = np.mean(pointfile.values_x[id_pts[0:npts]])
            ys[i] = np.mean(pointfile.values_y[id_pts[0:npts]])
            zs[i] = np.mean(pointfile.values_z[id_pts[0:npts]])
    else:
        owner = OpenFoamFile(rep + '/constant/polyMesh/', name='owner')
        if os.path.exists(os.path.join(rep, 'constant/C')):
            xs, ys, zs = readvector(rep, 'constant', 'C', precision=precision)
        else:
            facefile = OpenFoamFile(rep + '/constant/polyMesh/', name='faces')
            pointfile = OpenFoamFile(rep + '/constant/polyMesh/', name='points',
                                     precision=precision)
            neigh = OpenFoamFile(rep + '/constant/polyMesh/', name='neighbour')
            xs = np.empty(owner.nb_cell, dtype=float)
            ys = np.empty(owner.nb_cell, dtype=float)
            zs = np.empty(owner.nb_cell, dtype=float)
            face = {}
            for i in range(neigh.nb_faces):
                if not neigh.values[i] in face:
                    face[neigh.values[i]] = list()
                face[neigh.values[i]].append(facefile.faces[i]['id_pts'][:])
            for i in range(owner.nb_faces):
                if not owner.values[i] in face:
                    face[owner.values[i]] = list()
                face[owner.values[i]].append(facefile.faces[i]['id_pts'][:])
            for i in range(owner.nb_cell):
                xs[i] = np.mean(
                        pointfile.values_x[np.unique(
                                np.concatenate(face[i])[:])])
                ys[i] = np.mean(
                        pointfile.values_y[np.unique(
                                np.concatenate(face[i])[:])])
                zs[i] = np.mean(
                        pointfile.values_z[np.unique(
                                np.concatenate(face[i])[:])])
        if structured:
            nx = np.unique(xs).size
            ny = np.unique(ys).size
            nz = np.unique(zs).size
            if nx*ny*nz != owner.nb_cell:
                raise ValueError('nx.ny.nz not equal to number of cells.'
                                 'Are you sure that your mesh is cartesian?')
            ind = np.lexsort((xs, ys, zs))
            shape = (nx, ny, nz)
            xs = xs[ind].reshape(shape, order = order)
            ys = ys[ind].reshape(shape, order = order)
            zs = zs[ind].reshape(shape, order = order)

    return xs, ys, zs


if __name__ == '__main__':

    dirs = ['0.ascii',
            '0.asciigz',
            '0.bin', '0.bingz']

    for d in dirs:
        rep = os.path.join(os.path.dirname(__file__), '../output_samples')

        values = readscalar(rep, d, 'alpha')

        values = readsymmtensor(rep, d, 'sigma')

        values = readtensor(rep, d, 'Taus')

        values = readvector(rep, d, 'U')

        path = os.path.join(rep, d)
        xs, ys, zs = readmesh(path)
