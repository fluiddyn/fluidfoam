"""
Read OpenFoam files...

"""


import os
import gzip
import struct

import numpy as np


def _make_path(path, time_name=None, var_name=None):
    if time_name is not None and var_name is None: # pragma: no cover
        path = os.path.join(path, time_name)
    elif var_name is not None and time_name is None: # pragma: no cover
        path = os.path.join(path, var_name)
    elif var_name is not None and time_name is not None:
        path = os.path.join(path, time_name, var_name)

    if not os.path.exists(path) and os.path.exists(path + '.gz'):
        path += '.gz'

    return path


class OpenFoamFile(object):
    """OpenFoam file parser."""
    def __init__(self, path, name=None):

        if name is not None:
            path = os.path.join(path, name)
        self.path = path

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

        self._parse_data()

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

    def _parse_data(self):

        self.nb_pts = None

        data = self.content.split(b'internalField')[1]

        lines = data.split(b'\n')
        words = lines[0].split()
        self.nonuniform = words[0] == b'nonuniform'
        if not self.nonuniform: # pragma: no cover
            raise NotImplementedError 

        self.type_data = words[1]

        if self.type_data == b'List<scalar>':
            self.type_data = 'scalar'
        elif self.type_data == b'List<vector>':
            self.type_data = 'vector'
        elif self.type_data == b'List<symmTensor>':
            self.type_data = 'symmtensor'
        elif self.type_data == b'List<tensor>':
            self.type_data = 'tensor'

        self.nb_pts = int(lines[1])

        data = b'\n('.join(data.split(b'\n(')[1:])

        if not self.is_ascii:
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


def typefield(path, time_name=None, var_name=None):
    """Read OpenFoam field.

    Parameters
    ----------

    path : str

    time_name : str

    var_name : str

    """

    path = _make_path(path, time_name, var_name)

    field = OpenFoamFile(path)

    return field.type_data


def readfield(path, time_name=None, var_name=None, shape=None):
    """Read OpenFoam field.

    Parameters
    ----------

    path : str

    time_name : str

    var_name : str

    shape : None or iterable

    """

    path = _make_path(path, time_name, var_name)
    print('Reading file ' + path)

    field = OpenFoamFile(path)
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


def readscalar(path, time_name=None, var_name=None, shape=None):
    """Read OpenFoam scalar.

    Parameters
    ----------

    path : str

    time_name : str

    var_name : str

    shape : None or iterable

    """

    path = _make_path(path, time_name, var_name)
    print('Reading file ' + path)

    scalar = OpenFoamFile(path)
    values = scalar.values

    if scalar.type_data != 'scalar': # pragma: no cover
        raise ValueError('This file does not contain a scalar.')

    if shape is not None:
        values = np.reshape(values, shape, order="F")

    return values


def readvector(path, time_name=None, var_name=None, shape=None):
    """Read OpenFoam vector.

    Parameters
    ----------

    path : str

    time_name : str

    var_name : str

    shape : None or iterable

    """

    path = _make_path(path, time_name, var_name)
    print('Reading file ' + path)

    scalar = OpenFoamFile(path)
    values = scalar.values

    if scalar.type_data != 'vector': # pragma: no cover
        raise ValueError('This file does not contain a vector.')

    if shape is None:
        shape = (3, values.size//3)
    else:
        shape = (3,) + tuple(shape)

    values = np.reshape(values, shape, order="F")

    return values


def readsymmtensor(path, time_name=None, var_name=None, shape=None):
    """Read OpenFoam symmetrical tensor.

    Parameters
    ----------

    path : str

    time_name : str

    var_name : str

    shape : None or iterable

    """

    path = _make_path(path, time_name, var_name)
    print('Reading file ' + path)

    scalar = OpenFoamFile(path)
    values = scalar.values

    if scalar.type_data != 'symmtensor': # pragma: no cover
        raise ValueError('This file does not contain a symmtensor.')

    if shape is None:
        shape = (6, values.size//6)
    else:
        shape = (6,) + tuple(shape)

    values = np.reshape(values, shape, order="F")

    return values


def readtensor(path, time_name=None, var_name=None, shape=None):
    """Read OpenFoam tensor.

    Parameters
    ----------

    path : str

    time_name : str

    var_name : str

    shape : None or iterable

    """

    path = _make_path(path, time_name, var_name)
    print('Reading file ' + path)

    scalar = OpenFoamFile(path)
    values = scalar.values

    if scalar.type_data != 'tensor': # pragma: no cover
        raise ValueError('This file does not contain a tensor.')

    if shape is None:
        shape = (9, values.size//9)
    else:
        shape = (9,) + tuple(shape)

    values = np.reshape(values, shape, order="F")

    return values


def readmesh(rep, shape=None):
    """Read OpenFoam vector.

    Parameters
    ----------

    rep : str

    shape : None or iterable

    """

    if not os.path.exists(os.path.join(rep, 'ccx')) and \
       not os.path.exists(os.path.join(rep, 'ccx.gz')): # pragma: no cover
        raise ValueError('No ccx files. Run the command writeCellCentres.')

    ccx = OpenFoamFile(rep, 'ccx')
    xs = ccx.values

    if ccx.type_data != 'scalar': # pragma: no cover
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
        
        print(values)

        path = os.path.join(rep, d)
        xs, ys, zs = readmesh(path)
        # print(xs, ys, zs)
