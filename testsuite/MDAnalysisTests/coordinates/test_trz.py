# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 fileencoding=utf-8
#
# MDAnalysis --- https://www.mdanalysis.org
# Copyright (c) 2006-2017 The MDAnalysis Development Team and contributors
# (see the file AUTHORS for the full list of names)
#
# Released under the GNU Public Licence, v2 or any higher version
#
# Please cite your use of MDAnalysis in published work:
#
# R. J. Gowers, M. Linke, J. Barnoud, T. J. E. Reddy, M. N. Melo, S. L. Seyler,
# D. L. Dotson, J. Domanski, S. Buchoux, I. M. Kenney, and O. Beckstein.
# MDAnalysis: A Python package for the rapid analysis of molecular dynamics
# simulations. In S. Benthall and S. Rostrup editors, Proceedings of the 15th
# Python in Science Conference, pages 102-109, Austin, TX, 2016. SciPy.
#
# N. Michaud-Agrawal, E. J. Denning, T. B. Woolf, and O. Beckstein.
# MDAnalysis: A Toolkit for the Analysis of Molecular Dynamics Simulations.
# J. Comput. Chem. 32 (2011), 2319--2327, doi:10.1002/jcc.21787
#
from __future__ import absolute_import

import pytest
from six.moves import zip
import MDAnalysis as mda
import os

from numpy.testing import (
    assert_equal,
    assert_almost_equal
)
import numpy as np

from MDAnalysisTests.coordinates.reference import RefTRZ
from MDAnalysisTests.datafiles import (TRZ_psf, TRZ, two_water_gro)
from MDAnalysisTests import tempdir


class TestTRZReader(RefTRZ):
    prec = 3

    @pytest.fixture()
    def universe(self):
        return mda.Universe(TRZ_psf, TRZ)

    def test_load_trz(self, universe):
        U = universe
        assert_equal(len(U.atoms), self.ref_n_atoms,
                     "load Universe from PSF and TRZ")

    def test_next_trz(self, universe):
        assert_equal(universe.trajectory.ts.frame, 0, "starts at first frame")
        universe.trajectory.next()
        assert_equal(universe.trajectory.ts.frame, 1,
                     "next returns frame index 1")

    def test_rewind_trz(self, universe):
        # move to different frame and rewind to get first frame back
        universe.trajectory[2]
        universe.trajectory.rewind()
        assert_equal(universe.trajectory.ts.frame, 0, "rewinding to frame 1")

    def test_n_frames(self, universe):
        assert_equal(universe.trajectory.n_frames, self.ref_n_frames,
                     "wrong number of frames in trz")

    def test_seeking(self, universe):
        universe.trajectory[3]
        assert_equal(universe.trajectory.ts.frame, 3, "loading frame 3")

        orig = universe.atoms[0:3].positions.copy()

        universe.trajectory[4]
        assert_equal(universe.trajectory.ts.frame, 4, "loading frame 4")
        universe.trajectory[3]

        assert_almost_equal(universe.atoms[0:3].positions, orig,
                            self.prec)

        universe.trajectory[0]
        assert_equal(universe.trajectory.ts.frame, 0, "loading frame 0")
        universe.trajectory[3]

        assert_almost_equal(universe.atoms[0:3].positions, orig,
                            self.prec)

    def test_volume(self, universe):
        # Lower precision here because errors seem to accumulate and
        # throw this off (is rounded value**3)
        assert_almost_equal(universe.trajectory.ts.volume, self.ref_volume, 1,
                            "wrong volume for trz")

    def test_unitcell(self, universe):
        assert_almost_equal(universe.trajectory.ts.dimensions,
                            self.ref_dimensions, self.prec,
                            "wrong dimensions for trz")

    def test_coordinates(self, universe):
        fortytwo = universe.atoms[41]  # 41 because is 0 based
        assert_almost_equal(fortytwo.position, self.ref_coordinates, self.prec,
                            "wrong coordinates in trz")

    def test_velocities(self, universe):
        fortytwo = universe.select_atoms('bynum 42')
        assert_almost_equal(fortytwo.velocities, self.ref_velocities,
                            self.prec, "wrong velocities in trz")

    def test_delta(self, universe):
        assert_almost_equal(universe.trajectory.delta, self.ref_delta,
                            self.prec,
                            "wrong time delta in trz")

    def test_time(self, universe):
        assert_almost_equal(universe.trajectory.time, self.ref_time, self.prec,
                            "wrong time value in trz")

    def test_title(self, universe):
        assert_equal(self.ref_title, universe.trajectory.title,
                     "wrong title in trz")

    def test_get_writer(self, universe):
        with tempdir.in_tempdir():
            self.outfile = 'test-trz-writer.trz'
            W = universe.trajectory.Writer(self.outfile)
            assert_equal(isinstance(W, mda.coordinates.TRZ.TRZWriter), True)
            assert_equal(W.n_atoms, universe.trajectory.n_atoms)
            try:
                os.unlink(self.outfile)
            except OSError:
                pass

    def test_get_writer_2(self, universe):
        with tempdir.in_tempdir():
            self.outfile = 'test-trz-writer-1.trz'
            W = universe.trajectory.Writer(self.outfile, n_atoms=100)
            assert_equal(isinstance(W, mda.coordinates.TRZ.TRZWriter), True)
            assert_equal(W.n_atoms, 100)
            try:
                os.unlink(self.outfile)
            except OSError:
                pass


class TestTRZWriter(RefTRZ):
    prec = 3
    writer = mda.coordinates.TRZ.TRZWriter
    title_to_write = 'Test title TRZ'

    @pytest.fixture()
    def universe(self):
        return mda.Universe(TRZ_psf, TRZ)

    @pytest.fixture()
    def outfile(self, tmpdir):
        return str(tmpdir.join('/test-trz-writer.trz'))

    def test_write_trajectory(self, universe, outfile):
        t = universe.trajectory
        W = self.writer(outfile, t.n_atoms, title=self.title_to_write)
        self._copy_traj(W, universe, outfile)

    def _copy_traj(self, writer, universe, outfile):
        for ts in universe.trajectory:
            writer.write_next_timestep(ts)
        writer.close()

        uw = mda.Universe(TRZ_psf, outfile)

        assert_equal(uw.trajectory.title, self.title_to_write,
                     "Title mismatch between original and written files.")

        for orig_ts, written_ts in zip(universe.trajectory,
                                       uw.trajectory):
            assert_almost_equal(orig_ts._pos, written_ts._pos, self.prec,
                                err_msg="Coordinate mismatch between "
                                        "orig and written at frame %d" %
                                        orig_ts.frame)
            assert_almost_equal(orig_ts._velocities,
                                written_ts._velocities, self.prec,
                                err_msg="Coordinate mismatch between "
                                        "orig and written at frame %d" %
                                        orig_ts.frame)
            assert_almost_equal(orig_ts._unitcell, written_ts._unitcell,
                                self.prec, err_msg="Unitcell mismatch "
                                                   "between orig and written at frame %d" %
                                                   orig_ts.frame)
            for att in orig_ts.data:
                assert_almost_equal(orig_ts.data[att],
                                    written_ts.data[att], self.prec,
                                    err_msg="TS equal failed for {0!s}".format(
                                        att))

    def test_long_title(self, outfile):
        title = '*' * 81
        with pytest.raises(ValueError):
            self.writer(outfile, self.ref_n_atoms, title=title)


class TestTRZWriter2(object):
    @pytest.fixture()
    def u(self):
        return mda.Universe(two_water_gro)

    def test_writer_trz_from_other(self, u):
        with tempdir.in_tempdir():
            outfile = 'trz-writer-2.trz'
            W = mda.coordinates.TRZ.TRZWriter(outfile,
                                              n_atoms=len(u.atoms))

            W.write(u.trajectory.ts)
            W.close()

            u2 = mda.Universe(two_water_gro, outfile)

            assert_almost_equal(u.atoms.positions,
                                u2.atoms.positions, 3)


class TestWrite_Partial_Timestep(object):
    """Test writing a partial timestep made by passing only an atomgroup to
    Writer. (Issue 163)

    The contents of the AtomGroup.ts are checked in test_atomgroup, this test
    just checks that Writer is receiving this information properly.

    """
    prec = 3

    @pytest.fixture()
    def universe(self):
        return mda.Universe(TRZ_psf, TRZ)

    def test_write_trajectory(self, universe, tmpdir):
        ag = universe.select_atoms('name N')
        outfile = str(tmpdir.join('/partial-write-test.pdb'))
        writer = mda.Writer(outfile, n_atoms=len(ag))
        writer.write(ag)
        writer.close()

        u_ag = mda.Universe(outfile)

        assert_almost_equal(ag.positions,
                            u_ag.atoms.positions,
                            self.prec,
                            err_msg="Writing AtomGroup timestep failed.")
