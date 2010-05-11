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

import bdec.inspect.param
import os.path

class LoadError(Exception):
    pass

class UnknownInputParameter(LoadError):
    def __init__(self, entry, param_name, lookup):
        self._entry = entry
        self._param_name = param_name
        self._lookup = lookup

    def __str__(self):
        (filename, line_number, column_number) = self._lookup[self._entry]
        return "%s[%i]: '%s' references unknown parameter '%s'" % (filename,
                line_number, self._entry, self._param_name)

def _get_entry_that_uses_param(inspect, entry, param):
    """Drill down into an entry until we find the entry that uses 'param."""
    while 1:
        for child in entry.children:
            found_param = False
            for var in inspect.get_passed_variables(entry, child):
                if var.name == param:
                    found_param = True
                    entry = child.entry
                    break
            if found_param:
                break
        else:
            # This entry doesn't have a child that uses the given parameter, so
            # it must be the end-user.
            return entry

def validate_no_input_params(entry, lookup):
    """ Make sure the decoder doesn't have any unknown references."""

    end_entry_params = bdec.inspect.param.EndEntryParameters([entry])
    expression_params = bdec.inspect.param.ExpressionParameters([entry])
    params = bdec.inspect.param.CompoundParameters([end_entry_params, expression_params])

    # We need to raise an error as to missing parameters
    for param in params.get_params(entry):
        if param.direction is param.IN:
            # TODO: We should instead raise the error from the context of the
            # child that needs the data.
            user = _get_entry_that_uses_param(params, entry, param.name)
            raise UnknownInputParameter(user, param.name, lookup)

def load(filename, allow_inputs=False):
    """Load a specification from disk.

    Raises LoadError on error.

    filename -- Filename of the specification to load.
    allow_inputs -- Allow the main specification entry to have inputs (ie: with
        inputs it won't be able to decode).
    """
    import bdec.spec.asn1 as asn1
    import bdec.spec.xmlspec as xmlspec
    loaders = {'.xml':xmlspec, '.asn1':asn1}
    try:
        loader = loaders[os.path.splitext(filename)[1]]
    except KeyError:
        raise LoadError("Unknown specification format '%s'!" % filename)

    decoder, lookup, common = loader.load(filename)
    if not allow_inputs:
        validate_no_input_params(decoder, lookup)
    return decoder, lookup, common
