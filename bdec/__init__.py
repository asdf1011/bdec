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


"""
Bdec is a library for decoding binary files.

A decoder is made up of classes derived from bdec.entry.Entry. These
are:

 * bdec.field.Field
 * bdec.sequence.Sequence
 * bdec.choice.Choice
 * bdec.sequenceof.SequenceOf

A specification is a tree of entry objects, and can be used in multiple ways.
It can:

 * Decode and encode data at runtime (bdec.output)
 * Be compiled to a static decoder (bdec.tools.compiler)
 * Be defined in a textual format (bdec.spec)

Package Organization
====================
bdec contains the following subpackages and modules:

.. packagetree:: bdec regression specs tools
   :style: UML
"""

__version__ = "0.6.2"

class DecodeError(Exception):
    """ An error raise when decoding fails """
    def __init__(self, entry):
        import bdec.entry as ent
        assert isinstance(entry, ent.Entry), 'DecodeError exception constructed with a non entry! (%s)' % entry
        self.entry = entry

