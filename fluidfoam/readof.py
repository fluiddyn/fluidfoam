"""
Read OpenFoam files...

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


class OpenFoamFile(object):
    """OpenFoam file parser."""
    def __init__(self, path, time_name=None, name=None, boundary=None):

        self.pathcase = path
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
                tmp = b'[' + line.split(b'[')[1]
                self.dimensions = eval(b', '.join(tmp.split()))

        self.boundary = self._parse_session(b'boundaryField')

        if name is 'boundary':
            self.boundaryface = self._parse_boundaryfile()
        elif name is 'faces':
            self._parse_face()
        elif name is 'points':
            self._parse_points()
        elif name is 'owner':
            self._parse_owner()
        else:
            self._parse_data(boundary=boundary)

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

    def _parse_data(self, boundary):

        self.nb_pts = None
        if boundary is not None:
            boun = str.encode(boundary)
            if b'value' in self.content.split(boun)[1].split(b'}')[0]:
                data = self.content.split(boun)[1].split(b'value')[1]
            else:
                print('Warning : No data on patch')
                print('Nearest cells values use')
                self._nearest_data(boundary=boundary)
                return
        else:
            data = self.content.split(b'internalField')[1]

        lines = data.split(b'\n')
        shortline = (lines[0].split(b'>')[-1])
        words = lines[0].split()

        self.nonuniform = words[0] == b'nonuniform'
        self.uniform = words[0] == b'uniform'
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
            self.nb_pts = 1
            if not (self.type_data is 'scalar'):
                data = shortline.split(b'(')[1]
                data = data.replace(b' ', b'\n')
                data = data.replace(b');', b'\n);')
            else:
                data = words[1].split(b';')[0]
            print("Warning : uniform field  of type " + self.type_data + "!\n")
            print("Only constant field in output\n")
        elif shortline.count(b';') >= 1:
            self.nb_pts = int(shortline.split(b'(')[0])
            data = shortline.split(b'(')[1]
            data = data.replace(b' ', b'\n')
            data = data.replace(b');', b'\n);')
        else:
            self.nb_pts = int(lines[1])
            data = b'\n('.join(data.split(b'\n(')[1:])

        if not self.is_ascii and not self.uniform:
            if self.type_data == 'scalar':
                nb_numbers = self.nb_pts
            elif self.type_data == 'vector':
                nb_numbers = 3*self.nb_pts
            elif self.type_data == 'symmtensor':
                nb_numbers = 6*self.nb_pts
            elif self.type_data == 'tensor':
                nb_numbers = 9*self.nb_pts
            self.values = np.array(struct.unpack(
                '{}d'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('d')]))
        else:
            if self.type_data == 'scalar':
                self.values = np.array(
                    [float(s)
                     for s in data.strip().split(b'\n')[:self.nb_pts]])
            elif self.type_data in ('vector', 'tensor', 'symmtensor'):
                lines = data.split(b'\n(')
                lines = [line.split(b')')[0] for line in lines]
                data = b' '.join(lines).strip()
                self.values = np.array([float(s) for s in data.split()])

        if self.type_data == 'vector':
            self.values_x = self.values[::3]
            self.values_y = self.values[1::3]
            self.values_z = self.values[2::3]

    def _nearest_data(self, boundary):

        self.nb_pts = None
        #self._parse_data(boundary=None)
        bounfile = OpenFoamFile(self.pathcase + '/constant/polyMesh/',
                                name='boundary')
        #facefile = OpenFoamFile(self.pathcase + '/constant/polyMesh/',
        #                        name='faces')
        #pointfile = OpenFoamFile(self.pathcase + '/constant/polyMesh/',
        #                         name='points')
        ownerfile = OpenFoamFile(self.pathcase + '/constant/polyMesh/',
                                 name='owner')
        id0 = int(bounfile.boundaryface[str.encode(boundary)][b'startFace'])
        nfaces = int(bounfile.boundaryface[str.encode(boundary)][b'nFaces'])

        #xs = np.empty(nfaces, dtype=float)
        #ys = np.empty(nfaces, dtype=float)
        #zs = np.empty(nfaces, dtype=float)
        cell = np.empty(nfaces, dtype=int)
        for i in range(nfaces):
            #npts = int(facefile.faces[id0+i]['npts'])
            #id_pts = np.zeros(npts, dtype=int)
            #id_pts[0:npts] = facefile.faces[id0+i]['id_pts'][0:npts]
            #xs[i] = np.mean(pointfile.values_x[id_pts[0:npts]])
            #ys[i] = np.mean(pointfile.values_y[id_pts[0:npts]])
            #zs[i] = np.mean(pointfile.values_z[id_pts[0:npts]])
            cell[i] = ownerfile.values[id0+i]
        #boun = str.encode(boundary)
        data = self.content.split(b'internalField')[1]

        lines = data.split(b'\n')
        shortline = (lines[0].split(b'>')[-1])
        words = lines[0].split()

        self.nonuniform = words[0] == b'nonuniform'
        self.uniform = words[0] == b'uniform'
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
            self.nb_pts = 1
            if not (self.type_data is 'scalar'):
                data = shortline.split(b'(')[1]
                data = data.replace(b' ', b'\n')
                data = data.replace(b');', b'\n);')
            else:
                data = words[1].split(b';')[0]
            print("Warning : uniform field  of type " + self.type_data + "!\n")
            print("Only constant field in output\n")
        elif shortline.count(b';') >= 1:
            self.nb_pts = int(shortline.split(b'(')[0])
            data = shortline.split(b'(')[1]
            data = data.replace(b' ', b'\n')
            data = data.replace(b');', b'\n);')
        else:
            self.nb_pts = int(lines[1])
            data = b'\n('.join(data.split(b'\n(')[1:])

        if not self.is_ascii and not self.uniform:
            if self.type_data == 'scalar':
                nb_numbers = self.nb_pts
            elif self.type_data == 'vector':
                nb_numbers = 3*self.nb_pts
            elif self.type_data == 'symmtensor':
                nb_numbers = 6*self.nb_pts
            elif self.type_data == 'tensor':
                nb_numbers = 9*self.nb_pts
            values = np.array(struct.unpack(
                '{}d'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('d')]))
        else:
            if self.type_data == 'scalar':
                values = np.array(
                    [float(s)
                     for s in data.strip().split(b'\n')[:self.nb_pts]])
            elif self.type_data in ('vector', 'tensor', 'symmtensor'):
                lines = data.split(b'\n(')
                lines = [line.split(b')')[0] for line in lines]
                data = b' '.join(lines).strip()
                values = np.array([float(s) for s in data.split()])
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
        self.nfaces = int(line)-1
        data = self.content.split(line)[1]
        data = b'\n('.join(data.split(b'\n(')[1:])

        lines = data.split(b'\n')
        self.type_data = self.header[b'class']
        self.faces = {}

        if not self.is_ascii:
            nb_numbers = self.nfaces+1
            self.pointsbyface = struct.unpack(
                '{}i'.format(nb_numbers),
                data[0:nb_numbers*struct.calcsize('i')])
            data = self.content.split(str.encode(str(self.pointsbyface[-1])))[1]
            data = b'\n('.join(data.split(b'\n(')[1:])

            for i in range(self.nfaces):
                self.faces[i] = {}
                self.faces[i]['npts'] = (
                    self.pointsbyface[i+1] - self.pointsbyface[i])
                self.faces[i]['id_pts'] = np.array(struct.unpack(
                    '{}i'.format(self.faces[i]['npts']),
                    data[self.pointsbyface[i]*struct.calcsize('i'):self.pointsbyface[i+1]*struct.calcsize('i')]))
        else:
            for i, line in enumerate(lines):
                if i == 0:
                    continue
                elif line == b')':
                    break
                else:
                    self.faces[i-1] = {}
                    self.faces[i-1]['npts'] = line.split(b'(')[0]
                    self.faces[i-1]['id_pts'] = (
                            line.split(b'(')[1].split(b')')[0]).split()

    def _parse_points(self):

        for line in self.lines_stripped:
            try:
                int(line)
                break
            except ValueError:
                continue
            break
        self.nb_pts = int(line)-1
        data = self.content.split(line)[1]

        self.type_data = self.header[b'class']

        if not self.is_ascii:
            nb_numbers = 3*self.nb_pts
            self.values = np.array(struct.unpack(
                '{}d'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('d')]))
        else:
            lines = data.split(b'\n(')
            lines = [line.split(b')')[0] for line in lines]
            data = b' '.join(lines).strip()
            self.values = np.array([float(s) for s in data.split()])
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
        self.nb_pts = int(line)
        data = self.content.split(line)[2]

        self.type_data = self.header[b'class']

        if not self.is_ascii:
            nb_numbers = self.nb_pts
            data = b'\n('.join(data.split(b'\n(')[1:])
            self.values = np.array(struct.unpack(
                '{}i'.format(nb_numbers),
                data[:nb_numbers*struct.calcsize('i')]))
        else:
            lines = data.split(b'\n(')
            lines = [line.split(b')')[0] for line in lines]
            data = b' '.join(lines).strip()
            self.values = np.array([int(s) for s in data.split()])


def typefield(path, time_name=None, name=None):
    """Read OpenFoam field.

    Parameters
    ----------

    path : str

    time_name : str

    name : str

    """

    path = _make_path(path, time_name, name)

    field = OpenFoamFile(path)

    return field.type_data


def readfield(path, time_name=None, name=None, shape=None, boundary=None):
    """Read OpenFoam field.

    Parameters
    ----------

    path : str

    time_name : str

    name : str

    shape : None or iterable

    """

    field = OpenFoamFile(path, time_name, name, boundary)
    values = field.values

    if field.type_data == 'scalar':
        if shape is not None:
            values = np.reshape(values, shape, order="F")
    elif field.type_data == 'vector':
        if shape is None:
            shape = (3, values.size//3)
        else:
            shape = (3,) + tuple(shape)
        values = np.reshape(values, shape, order="F")
    elif field.type_data == 'symmtensor':
        if shape is None:
            shape = (6, values.size//6)
        else:
            shape = (6,) + tuple(shape)
        values = np.reshape(values, shape, order="F")
    elif field.type_data == 'tensor':
        if shape is None:
            shape = (9, values.size//9)
        else:
            shape = (9,) + tuple(shape)
        values = np.reshape(values, shape, order="F")

    return values


def readscalar(path, time_name=None, name=None, shape=None, boundary=None):
    """Read OpenFoam scalar.

    Parameters
    ----------

    path : str

    time_name : str

    name : str

    shape : None or iterable

    boundary : None or patch name

    """

    scalar = OpenFoamFile(path, time_name, name, boundary=boundary)
    values = scalar.values

    if scalar.type_data != 'scalar':  # pragma: no cover
        raise ValueError('This file does not contain a scalar.')

    if shape is not None:
        values = np.reshape(values, shape, order="F")

    return values


def readvector(path, time_name=None, name=None, shape=None, boundary=None):
    """Read OpenFoam vector.

    Parameters
    ----------

    path : str

    time_name : str

    name : str

    shape : None or iterable

    boundary : None or patch name

    """

    scalar = OpenFoamFile(path, time_name, name, boundary=boundary)
    values = scalar.values

    if scalar.type_data != 'vector':  # pragma: no cover
        raise ValueError('This file does not contain a vector.')

    if shape is None:
        shape = (3, values.size//3)
    else:
        shape = (3,) + tuple(shape)

    values = np.reshape(values, shape, order="F")

    return values


def readsymmtensor(path, time_name=None, name=None, shape=None,
                   boundary=None):
    """Read OpenFoam symmetrical tensor.

    Parameters
    ----------

    path : str

    time_name : str

    name : str

    shape : None or iterable

    boundary : None or patch name

    """

    scalar = OpenFoamFile(path, time_name, name, boundary=boundary)
    values = scalar.values

    if scalar.type_data != 'symmtensor':  # pragma: no cover
        raise ValueError('This file does not contain a symmtensor.')

    if shape is None:
        shape = (6, values.size//6)
    else:
        shape = (6,) + tuple(shape)

    values = np.reshape(values, shape, order="F")

    return values


def readtensor(path, time_name=None, name=None, shape=None, boundary=None):
    """Read OpenFoam tensor.

    Parameters
    ----------

    path : str

    time_name : str

    name : str

    shape : None or iterable

    boundary : None or patch name

    """

    scalar = OpenFoamFile(path, time_name, name, boundary=boundary)

    values = scalar.values

    if scalar.type_data != 'tensor':  # pragma: no cover
        raise ValueError('This file does not contstartFaceain a tensor.')

    if shape is None:
        shape = (9, values.size//9)
    else:
        shape = (9,) + tuple(shape)

    values = np.reshape(values, shape, order="F")

    return values


def readmesh(rep, shape=None, boundary=None):
    """Read OpenFoam Mesh.

    Parameters
    ----------

    rep : str

    shape : None or iterable

    boundary : None or str

    """

    if boundary is not None:
        bounfile = OpenFoamFile(rep + '/constant/polyMesh/', name='boundary')
        facefile = OpenFoamFile(rep + '/constant/polyMesh/', name='faces')
        pointfile = OpenFoamFile(rep + '/constant/polyMesh/', name='points')
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
        if not os.path.exists(os.path.join(rep, 'ccx')) and \
           not os.path.exists(os.path.join(rep, 'ccx.gz')):  # pragma: no cover
            raise ValueError('No ccx files in ', rep,
                             ' Run the command writeCellCentres.')

        ccx = OpenFoamFile(rep, 'ccx')
        xs = ccx.values

        if ccx.type_data != 'scalar':  # pragma: no cover
            raise ValueError('The file does not contain a scalar.')

        ccy = OpenFoamFile(rep, 'ccy')
        ys = ccy.values
        ccz = OpenFoamFile(rep, 'ccz')
        zs = ccz.values

        if shape is not None:
            xs = np.reshape(xs, shape, order="F")
            ys = np.reshape(ys, shape, order="F")
            zs = np.reshape(zs, shape, order="F")

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
        # print(xs, ys, zs)
