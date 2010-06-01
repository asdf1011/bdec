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
    pass

class LoadErrorWithLocation(LoadError):
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


class ReferenceError(LoadErrorWithLocation):
    """Exception thrown when a problem is found with one of the expression
    references."""
    def __init__(self, ex, entry, lookup, context=[]):
        filename, lineno, colno = lookup.get(entry, ('unknown', 0, 0))
        LoadErrorWithLocation.__init__(self, filename, _Locator(lineno, colno))
        self.ex = ex
        self.context = context

    def __str__(self):
        result = self._src() + str(self.ex)
        if self.context:
            result += '\n' + '\n'.join('  %s%s' % (self._src(c[0], c[1]), c[3]) for c in self.context)
        return result

class UnspecifiedMainEntry(LoadError):
    """Exception thrown when the main entry is not specified."""
    def __init__(self, names):
        self.names = names

    def __str__(self):
        result = 'No main entry specified! Entry must be one of:'
        return '\n  '.join([result] + self.names)


def _validate_parameters(entries, lookup):
    import bdec.inspect.param as prm
    try:
        # Validate all of the parameters in use
        prm.CompoundParameters([prm.EndEntryParameters(entries),
            prm.ExpressionParameters(entries)])
    except prm.BadReferenceError, ex:
        context = [(lookup[e] + (str(e),)) for e in ex.context if ex.entry in lookup]
        raise ReferenceError(ex, ex.entry, lookup, context)

def _walk(entry, entries):
    if entry in entries:
        return
    entries.add(entry)
    for child in entry.children:
        _walk(child.entry, entries)

def _resolve(decoder, references, lookup, should_remove_unused):
    from bdec.spec.references import MissingReferenceError

    # Resolve all references
    references.add_common(decoder)
    try:
        common = references.resolve()
    except MissingReferenceError, ex:
        raise ReferenceError(ex, ex.reference, lookup)
    decoder = common.pop()

    if should_remove_unused:
        # Remove any entries that are unused
        referenced = set()
        _walk(decoder, referenced)
        common = [c for c in common if c in referenced]

    _validate_parameters([decoder] + common, lookup)
    return decoder, common

def _load_spec(filename, contents, format, references):
    import bdec.spec.asn1 as asn1
    import bdec.spec.xmlspec as xmlspec
    loaders = {'xml':xmlspec, 'asn1':asn1}
    try:
        loader = loaders[format]
    except KeyError:
        raise LoadError("Unknown specification format '%s'!" % filename)

    decoder, lookup = loader.load(filename, contents, references)
    return decoder, lookup

def load_specs(specs, main_name=None, should_remove_unused=False):
    """Load a specification from disk.

    When more than one specification is passed in, the entries from each
    specification are loaded. Entries from one specification can be used as
    references in the other specifications.

    Raises LoadError on error.

    specs -- A list of specifications to load. Each item in the listen is a
      tuple containing;
        * A tuple containing (filename, contents, format)
      Where 'contents' is a string or file object containing the contents
      of the specification (if None, the file is opened from disk), and
      'format' is the type of the specification, such as 'xml' or 'asn1'
      (if None, it is taken from the filename extension).
    main_name -- The name of the entry to use as the main decoder. If None,
      there must a single main decoder from the specs loaded (otherwise
      a UnspecifiedMainDecoderError will be thrown).
    should_remove_unused -- Should the loader remove any entries that are
      unused by the main decoder.
    return -- (decoder, common, lookup)
    """
    from bdec.spec.references import References

    references = References()
    decoders = []
    lookup = {}
    for filename, contents, format in specs:
        if contents is None:
            contents = open(filename, 'r')
        elif isinstance(contents, basestring):
            contents = StringIO(contents)

        if format is None:
            format = os.path.splitext(filename)[1][1:]
        d, l = _load_spec(filename, contents, format, references)
        if d:
            decoders.append(d)
        lookup.update(l)

    decoder = None
    if main_name:
        # The user has a specific entry they would like to use as the main
        # decoder.
        for decoder in decoders:
            if decoder.name == main_name:
                # The requested decoder is one of the top level main entries
                break
        else:
            # The requested decoder is one of the common entries. If not, it
            # will simply fail to resolve.
            decoder = references.get_common(main_name)
    else:
        if len(decoders) != 1:
            # There isn't a single main decoders available from the spec; the
            # user must choose what entry will be the 'main' decoder.
            raise UnspecifiedMainEntry([d.name for d in decoders] + references.get_names())
        decoder = decoders[0]

    decoder, common = _resolve(decoder, references, lookup, should_remove_unused)
    return decoder, common, lookup

