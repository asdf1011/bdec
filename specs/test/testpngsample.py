#   Copyright (C) 2008 Henry Ludemann
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.

import os.path
import shutil
import unittest

from bdec.spec.xmlspec import load
from bdec.test.decoders import generate, compile_and_run, _CDecoder

class TestPngSample(unittest.TestCase):
    """Class to test the png decoding sample from the documentation."""

    def test_png_sample(self):
        test_dir = os.path.dirname(__file__)
        spec_filename = os.path.join(test_dir, '..', 'png.xml')
        main_filename = os.path.join(test_dir, '..', '..', 'docs', 'files', 'main.c')
        png_filename = os.path.join(test_dir, 'png', 'white.png')

        (spec, common, lookup) = load(spec_filename)
        generate(spec, common.itervalues(), _CDecoder)
        shutil.copy(main_filename, _CDecoder.TEST_DIR)
        exit_code, output = compile_and_run(open(png_filename, 'rb'), _CDecoder)
        self.assertEqual(0, exit_code)
        self.assertEqual("Image width = 5\nImage height = 5\nComment = I'm an image comment!\n", output)

