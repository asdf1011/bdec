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
from StringIO import StringIO

class LoadError(Exception):
    """Base class for all loading errors."""
    def __init__(self, filename, locator):
        self.filename = filename
        self.line = locator.getLineNumber()
        self.column = locator.getColumnNumber()

    def _src(self, filename=None, line=None):
        filename = filename or self.filename
        line = line or self.line
        return "%s[%s]: " % (filename, line)


class _Locator:
    def __init__(self, lineno, colno):
        self._lineno = lineno
        self._colno = colno

    def getLineNumber(self):
        return self._lineno

    def getColumnNumber(self):
        return self._colno


class ReferenceError(LoadError):
    """Exception thrown when a problem is found with one of the expression
    references."""
    def __init__(self, ex, entry, lookup, context=[]):
        filename, lineno, colno = lookup.get(entry, ('unknown', 0, 0))
        LoadError.__init__(self, filename, _Locator(lineno, colno))
        self.ex = ex
        self.context = context

    def __str__(self):
        result = self._src() + str(self.ex)
        if self.context:
            result += '\n' + '\n'.join('  %s%s' % (self._src(c[0], c[1]), c[3]) for c in self.context)
        return result

def _validate_parameters(entries, lookup):
    import bdec.inspect.param as prm
    try:
        # Validate all of the parameters in use
        prm.CompoundParameters([prm.EndEntryParameters(entries),
            prm.ExpressionParameters(entries)])
    except prm.BadReferenceError, ex:
        context = [(lookup[e] + (str(e),)) for e in ex.context if ex.entry in lookup]
        raise ReferenceError(ex, ex.entry, lookup, context)

def _resolve(decoder, references, lookup):
    from bdec.spec.references import MissingReferenceError

    # Resolve all references
    references.add_common(decoder)
    try:
        common = references.resolve()
    except MissingReferenceError, ex:
        raise ReferenceError(ex, ex.reference, lookup)
    decoder = common.pop()

    _validate_parameters([decoder] + common, lookup)
    return decoder, common

def load(filename, contents=None, format=None):
    """Load a specification from disk.

    Raises LoadError on error.

    filename -- The filename of the specification.
    contents -- String or file object of the specification to load. If None,
        it will load the spec from disk.
    format -- The type of the specification; eg: xml, asn1. If None, the name
        will be taken from the extension of the filename.
    return -- (decoder, common, lookup)
    """
    import bdec.spec.asn1 as asn1
    from bdec.spec.references import References
    import bdec.spec.xmlspec as xmlspec

    if contents is None:
        contents = open(filename, 'r')
    elif isinstance(contents, basestring):
        contents = StringIO(contents)

    if format is None:
        format = os.path.splitext(filename)[1][1:]

    loaders = {'xml':xmlspec, 'asn1':asn1}
    try:
        loader = loaders[format]
    except KeyError:
        raise LoadError("Unknown specification format '%s'!" % filename)

    references = References()
    decoder, lookup = loader.load(filename, contents, references)
    decoder, common = _resolve(decoder, references, lookup)
    return decoder, common, lookup

