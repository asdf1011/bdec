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

import bdec.choice as chc
import bdec.field as fld
import bdec.sequence as seq
from bdec.expression import Delayed, ValueResult, LengthResult, Constant
import operator
import string

keywords=['char', 'int', 'float', 'if', 'then', 'else', 'struct', 'for', 'null']

_escaped_types = {}
def escaped_type(entry):
    if not _escaped_types:
        # Create a cache of names to types (this function is called many times).
        # We put the common entries at the start of the list, which will cause
        # them to have first chance at a unique name.
        entries = common + list(e for e in iter_entries() if e not in common)
        names = [e.name for e in entries]
        escaped = esc_names(names, esc_name)
        _escaped_types.update(zip(entries, escaped))
    return _escaped_types[entry]

def ctype(entry):
    """Return the c type name for an entry"""
    if entry is int:
        return 'int'
    elif isinstance(entry, fld.Field):
        if entry.format == fld.Field.INTEGER:
            return 'int'
        if entry.format == fld.Field.TEXT:
            return 'Buffer'
        elif entry.format == fld.Field.HEX:
            return 'Buffer'
        elif entry.format == fld.Field.BINARY:
            return 'BitBuffer'
        else:
            raise Exception("Unhandled field format '%s'!" % entry)
    elif isinstance(entry, seq.Sequence) and entry.value is not None and \
            not reduce(lambda a,b: a and b, (child_contains_data(child) for child in entry.children), True):
        # This sequence has hidden children and a value; we can treat this as
        # an integer.
        return 'int'
    else:
        return "struct " + typename(escaped_type(entry))

def _param_type(param):
    if param.type is int:
        return 'int'
    return ctype(param.type)

def define_params(entry):
    result = ""
    for param in get_params(entry):
        if param.direction is param.IN:
            result += ", %s %s" % (_param_type(param), param.name)
        else:
            result += ", %s* %s" % (_param_type(param), param.name)
    return result

def params(parent, i, result_name):
    # How we should reference the variable passed to the child is from the
    # following table;
    #
    #                        Child in   |   Child out
    #                       --------------------------
    # Local or input param |    name    |    &name    |
    #                      |--------------------------|
    #         Output param |   *name    |    name     |
    #                       --------------------------
    result = ""
    locals = list(local.name for local in local_vars(parent))
    params = dict((param.name, param.direction) for param in get_params(parent))
    for param in get_passed_variables(parent, parent.children[i]):
        if param.direction is param.OUT and param.name == 'unknown':
            result += ', %s' % result_name
        elif param.name in locals or params[param.name] == param.IN:
            if param.direction == param.IN:
                result += ", %s" % param.name
            else:
                result += ", &%s" % param.name
        else:
            if param.direction == param.IN:
                result += ", *%s" % param.name
            else:
                result += ", %s" % param.name
    return result


_OPERATORS = {
        operator.__div__ : '/', 
        operator.__mul__ : '*',
        operator.__sub__ : '-',
        operator.__add__ : '+',
        }

def value(expr):
  if isinstance(expr, int):
      return str(expr)
  elif isinstance(expr, Constant):
      return str(expr.value)
  elif isinstance(expr, ValueResult):
      return variable(expr.name)
  elif isinstance(expr, LengthResult):
      return variable(expr.name + ' length')
  elif isinstance(expr, Delayed):
      return "(%s %s %s)" % (value(expr.left), _OPERATORS[expr.op], value(expr.right)) 
  else:
      raise Exception('Unknown length value', expression)

def enum_type_name(entry):
    return typename(settings.escaped_type(entry) + ' option')

_enum_cache = {}
def enum_value(parent, child_index):
    if not _enum_cache:
        # For all global 'options', we need the enum item to be unique. To do
        # this we get all possible options, then get a unique name for that
        # option.
        options = []
        offsets = {}
        for e in iter_entries():
            if isinstance(e, chc.Choice):
                offsets[e] = range(len(options), len(options) + len(e.children))
                options.extend(c.name for c in e.children)
        names = esc_names(options, constant)
        for e in iter_entries():
            if isinstance(e, chc.Choice):
                _enum_cache[e] = list(names[i] for i in offsets[e])
    return _enum_cache[parent][child_index]

def decode_name(entry):
    return function('decode ' + escaped_type(entry))

def print_name(entry):
    return function('print xml ' + escaped_type(entry))

_var_name_cache = {}
def var_name(entry, child_index):
    try:
        names = _var_name_cache[entry]
    except KeyError:
        names = esc_names((c.name for c in entry.children), variable)
        _var_name_cache[entry] = names
    return names[child_index]

def free_name(entry):
    return function('free ' + escaped_type(entry))

_PRINTABLE = string.ascii_letters + string.digits
def _c_repr(char):
    if char in _PRINTABLE:
        return char
    return '\\%03o' % ord(char)

def c_string(data):
    """Return a correctly quoted c-style string for an arbitrary binary string."""
    return '"%s"' % ''.join(_c_repr(char) for char in data)

