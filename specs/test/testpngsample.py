#   Copyright (C) 2010 Henry Ludemann
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
#  
# This file incorporates work covered by the following copyright and  
# permission notice:  
#  
#   Copyright (c) 2010, PRESENSE Technologies GmbH
#   All rights reserved.
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#       * Redistributions of source code must retain the above copyright
#         notice, this list of conditions and the following disclaimer.
#       * Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#       * Neither the name of the PRESENSE Technologies GmbH nor the
#         names of its contributors may be used to endorse or promote products
#         derived from this software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os.path
import shutil
import unittest

from bdec.spec import load_specs
from bdec.test.decoders import generate, compile_and_run, _CDecoder

class TestPngSample(unittest.TestCase):
    """Class to test the png decoding sample from the documentation."""

    def test_png_sample(self):
        test_dir = os.path.dirname(__file__)
        spec_filename = os.path.join(test_dir, '..', 'png.xml')
        main_filename = os.path.join(test_dir, '..', '..', 'docs', 'files', 'main.c')
        png_filename = os.path.join(test_dir, 'png', 'white.png')

        (spec, common, lookup) = load_specs([(spec_filename, None, None)])
        generate(spec, common, _CDecoder, False)
        shutil.copy(main_filename, _CDecoder.TEST_DIR)
        output = compile_and_run(open(png_filename, 'rb'), _CDecoder)
        self.assertEqual("Image width = 5\nImage height = 5\nComment = I'm an image comment!\n", output)

