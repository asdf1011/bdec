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

import bdec.field as fld
import bdec.sequence as seq
from bdec.spec.expression import Delayed, ValueResult, LengthResult, Constant
import operator
import string

keywords=['char', 'int', 'float', 'if', 'then', 'else', 'struct', 'for']

def ctype(entry):
    """Return the c type name for an entry"""
    if isinstance(entry, fld.Field):
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
            not reduce(lambda a,b: a and b, (contains_data(child.entry) for child in entry.children)):
        # This sequence has hidden children and a value; we can treat this as
        # an integer.
        return 'int'
    else:
        return "struct " + typename(esc_name(iter_entries().index(entry), iter_entries()))

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
    result = ""
    locals = list(local_vars(parent))
    for param in get_passed_variables(parent, parent.children[i]):
        if param.direction is param.OUT and param.name == 'unknown':
            result += ', %s' % result_name
        elif param.direction is param.OUT and param.name in locals:
            result += ", &%s" % param.name
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

def decode_name(entry):
    return function('decode ' + esc_name(iter_entries().index(entry), iter_entries()))

def print_name(entry):
    return function('print xml ' + esc_name(iter_entries().index(entry), iter_entries()))

def var_name(i, other_vars):
    return variable(esc_name(i, other_vars))

def free_name(entry):
    return function('free ' + esc_name(iter_entries().index(entry), iter_entries()))

_PRINTABLE = string.ascii_letters + string.digits
def _c_repr(char):
    if char in _PRINTABLE:
        return char
    return '\\%03o' % ord(char)

def c_string(data):
    """Return a correctly quoted c-style string for an arbitrary binary string."""
    return '"%s"' % ''.join(_c_repr(char) for char in data)

