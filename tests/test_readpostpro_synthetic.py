"""Tests of readprobes and readforce on small synthetic postProcessing files.

The files are written in a temporary directory, so no OpenFoam case is needed.
The values are chosen so that each of them tells where it comes from:
    value(time, column) = 100 * time + column
"""

import contextlib
import io
import os
import shutil
import tempfile
import unittest

import numpy as np

from fluidfoam import readforce, readprobes

N_PROBES = 3
TIMES = [0.0, 0.25, 0.5, 0.75]


def quiet(function, *args, **kwargs):
    """Call function without the messages it prints."""
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(text.encode())


def _probes_text(times, vector, header_extra=False, eol="\n"):
    lines = []
    if header_extra:
        lines.append("# a comment line")
    lines += ["# Probe %d (%d 0 0)" % (i, i) for i in range(N_PROBES)]
    if header_extra:
        lines.append("#")
    lines.append("#       Time")
    for t in times:
        if vector:
            probes = [
                "(%s)" % " ".join(repr(100 * t + 10 * i + c) for c in range(3))
                for i in range(N_PROBES)
            ]
        else:
            probes = [repr(100 * t + i) for i in range(N_PROBES)]
        lines.append(repr(t) + "\t" + " ".join(probes))
    return eol.join(lines) + eol


def _expected_probes(times, vector):
    times = np.array(times)
    if vector:
        tab = [
            [[100 * t + 10 * i + c for c in range(3)] for i in range(N_PROBES)]
            for t in times
        ]
    else:
        tab = [[[100 * t + i] for i in range(N_PROBES)] for t in times]
    return times, np.array(tab)


def _force_line(t, eol="\n"):
    a = [100 * t + k for k in range(18)]
    groups = [
        "(%s)" % " ".join(repr(x) for x in a[3 * g : 3 * g + 3]) for g in range(6)
    ]
    return "%r\t((%s) (%s) (%s)) ((%s) (%s) (%s))%s" % (
        (t,) + tuple(groups) + (eol,)
    )


def _forces_text(times, eol="\n"):
    header = "# Forces\n# CofR : (0 0 0)\n# Time forces moment\n".replace(
        "\n", eol
    )
    return header + "".join(_force_line(t, eol) for t in times)


def _expected_forces(times):
    return np.array([[t] + [100 * t + k for k in range(18)] for t in times])


class ReadProbesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fluidfoam_probes_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, time_name, text, name="U"):
        path = os.path.join(
            self.root, "postProcessing", "probes", time_name, name
        )
        _write(path, text)
        return path

    def read(self, time_name="0", name="U", path=None):
        return quiet(readprobes, path or self.root, "probes", time_name, name)

    def check(self, result, times, vector=True):
        loc, time_vect, tab = result
        np.testing.assert_array_equal(loc, [[i, 0, 0] for i in range(N_PROBES)])
        expected_times, expected_tab = _expected_probes(times, vector)
        np.testing.assert_array_equal(time_vect, expected_times)
        self.assertEqual(tab.shape, expected_tab.shape)
        np.testing.assert_array_equal(tab, expected_tab)

    def test_vector(self):
        self.write("0", _probes_text(TIMES, vector=True))
        self.check(self.read(), TIMES)

    def test_scalar(self):
        self.write("0", _probes_text(TIMES, vector=False), name="p")
        self.check(self.read(name="p"), TIMES, vector=False)

    def test_header_with_additional_comment_lines(self):
        self.write("0", _probes_text(TIMES, vector=True, header_extra=True))
        self.check(self.read(), TIMES)

    def test_windows_line_endings(self):
        self.write("0", _probes_text(TIMES, vector=True, eol="\r\n"))
        self.check(self.read(), TIMES)

    def test_comment_line_inside_the_data_is_ignored(self):
        lines = _probes_text(TIMES, vector=True).split("\n")
        lines.insert(len(lines) - 3, "# Probe 0 (9 9 9)")
        self.write("0", "\n".join(lines))
        self.check(self.read(), TIMES)

    def test_incomplete_last_line_is_ignored(self):
        # the file may be read while it is being written
        self.write("0", _probes_text(TIMES, vector=True) + "1.0\t(1 2 3) (4 5")
        self.check(self.read(), TIMES)

    def test_file_without_data(self):
        self.write("0", _probes_text([], vector=True))
        loc, time_vect, tab = self.read()
        self.assertEqual(loc.shape, (N_PROBES, 3))
        self.assertEqual(time_vect.size, 0)
        self.assertEqual(tab.size, 0)

    def test_latest_time(self):
        self.write("0", _probes_text(TIMES, vector=True))
        later = [10.0, 10.25]
        self.write("10", _probes_text(later, vector=True))
        self.check(self.read("latestTime"), later)

    def test_merge_time(self):
        self.write("0", _probes_text([0.0, 0.25, 0.5, 0.75, 1.0], vector=True))
        # restart: the times already written are written again; this
        # directory brings one new time (1.25)
        self.write("0.75", _probes_text([0.75, 1.0, 1.25], vector=True))
        self.check(self.read("mergeTime"), [0.0, 0.25, 0.5, 0.75, 1.0, 1.25])
        self.write("1.25", _probes_text([1.25, 1.5, 1.75, 2.0], vector=True))
        self.check(
            self.read("mergeTime"),
            [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        )

    def test_path_with_or_without_trailing_slash(self):
        self.write("0", _probes_text(TIMES, vector=True))
        for path in (
            self.root,
            self.root + os.sep,
            os.path.join(self.root, "postProcessing"),
            os.path.join(self.root, "postProcessing") + os.sep,
        ):
            with self.subTest(path=path):
                self.check(self.read(path=path), TIMES)


class ReadForceTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fluidfoam_forces_")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def write(self, time_name, text, name="forces.dat"):
        _write(
            os.path.join(self.root, "postProcessing", "forces", time_name, name),
            text,
        )

    def read(self, time_name="0", path=None):
        return quiet(readforce, path or self.root, "forces", time_name, "forces")

    def test_forces(self):
        self.write("0", _forces_text(TIMES))
        tab = self.read()
        self.assertEqual(tab.shape, (len(TIMES), 19))
        np.testing.assert_array_equal(tab, _expected_forces(TIMES))

    def test_windows_line_endings(self):
        self.write("0", _forces_text(TIMES, eol="\r\n"))
        np.testing.assert_array_equal(self.read(), _expected_forces(TIMES))

    def test_last_line_without_end_of_line_is_ignored(self):
        # the file may be read while it is being written
        text = _forces_text(TIMES)
        self.write("0", text[:-1])
        np.testing.assert_array_equal(self.read(), _expected_forces(TIMES[:-1]))

    def test_file_without_data(self):
        self.write("0", _forces_text([]))
        self.assertEqual(self.read().size, 0)

    def test_latest_time(self):
        self.write("0", _forces_text(TIMES))
        self.write("10", _forces_text([10.0, 10.25]))
        np.testing.assert_array_equal(
            self.read("latestTime"), _expected_forces([10.0, 10.25])
        )

    def test_merge_time(self):
        self.write("0", _forces_text([0.0, 0.25, 0.5, 0.75, 1.0]))
        self.write("0.75", _forces_text([0.75, 1.0, 1.25]))  # one new time
        np.testing.assert_array_equal(
            self.read("mergeTime"),
            _expected_forces([0.0, 0.25, 0.5, 0.75, 1.0, 1.25]),
        )

    def test_merge_time_with_a_directory_without_file(self):
        os.makedirs(os.path.join(self.root, "postProcessing", "forces", "0"))
        self.write("1", _forces_text([1.0, 1.25]))
        np.testing.assert_array_equal(
            self.read("mergeTime"), _expected_forces([1.0, 1.25])
        )

    def test_path_with_or_without_trailing_slash(self):
        self.write("0", _forces_text(TIMES))
        for path in (
            self.root,
            self.root + os.sep,
            os.path.join(self.root, "postProcessing"),
        ):
            with self.subTest(path=path):
                np.testing.assert_array_equal(
                    self.read(path=path), _expected_forces(TIMES)
                )


if __name__ == "__main__":
    unittest.main()
