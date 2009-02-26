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

import operator
import string

import bdec.choice as chc
from bdec.entry import Entry
import bdec.field as fld
import bdec.sequence as seq
from bdec.expression import Delayed, ValueResult, LengthResult, Constant
from bdec.inspect.param import Local, Param
from bdec.inspect.type import EntryLengthType, EntryValueType, IntegerType, EntryType, expression_range

keywords=['char', 'int', 'short', 'long', 'float', 'if', 'then', 'else', 'struct', 'for', 'null', 'value', 'signed', 'true', 'false']

# Also define our types as keywords, as we don't want the generated names to
# clash with our types.
keywords += ['Buffer', 'Text', 'BitBuffer']

unsigned_types = {'unsigned int':(32, '%u'), 'unsigned long long':(64, '%llu')}
signed_types = {'int':(32, '%i'), 'long long':(64, '%lli')}

def is_numeric(type):
    if type == 'unsigned char':
        # We have an explicit unsigned char for short bitfields
        return True
    return type in signed_types or type in unsigned_types

def printf_format(type):
    a = unsigned_types.copy()
    a.update(signed_types)
    return a[type][1]

_escaped_types = {}
def escaped_type(entry):
    if not _escaped_types:
        # Create a cache of names to types (this function is called many times).
        embedded = [e for e in iter_entries() if e not in common]
        entries = common + embedded

        common_names = [e.name for e in common]
        embedded_names = [e.name for e in embedded]

        # We escape the 'common' entries first, so they can get as close a name
        # as possible to their unescaped name.
        names = esc_names(common_names, esc_name)
        names += esc_names(embedded_names, esc_name, names)
        _escaped_types.update(zip(entries, names))
    return _escaped_types[entry]

def _int_types():
    possible = [(name, -1 << (info[0] - 1), (1 << (info[0] - 1)) - 1) for name, info in signed_types.items()]
    possible.extend((name, 0, (1 << info[0]) - 1) for name, info in unsigned_types.items())
    possible.sort(key=lambda a:a[2])
    for name, minimum, maximum in possible:
        yield name, minimum, maximum

def _biggest(types):
    """ Return the biggest possible type."""
    return reduce(lambda a, b: a if a[1][0] > b[1][0] else b, types.items())[0]

def _integer_type(type):
    """Choose an appropriate integral type for the given type."""
    return _type_from_range(type.range(raw_params))

def _type_from_range(range):
    if range.min is None:
        # This number doesn't have a minimum value; choose the type that can
        # represent the most negative number.
        return _biggest(signed_types)
    if range.max is None:
        # This number doesn't have a maximum valuea; choose the type that can
        # represent the largest number.
        return _biggest(unsigned_types)

    for name, minimum, maximum in _int_types():
        if range.min >= minimum and range.max <= maximum:
            return name

    # We don't have big enough type for this number...
    return _biggest(signed_types)

def get_integer(entry):
    """ Choose either the 'int' or the 'long long' decoder.

    entry -- The entry we are decoding. Looks at it's possible length when
        deciding which decode function to use.
    """
    if EntryValueType(entry).range(raw_params).max <= 0xffffffff:
        return 'get_integer'
    else:
        return 'get_long_integer'

def children_contain_data(entry):
    for child in entry.children:
        if child_contains_data(child):
            return True
    return False

def _entry_type(entry):
    assert isinstance(entry, Entry), "Expected an Entry instance, got '%s'!" % entry
    if isinstance(entry, fld.Field):
        if entry.format == fld.Field.INTEGER:
            return _integer_type(EntryValueType(entry))
        if entry.format == fld.Field.TEXT:
            return 'Text'
        elif entry.format == fld.Field.HEX:
            return 'Buffer'
        elif entry.format == fld.Field.BINARY:
            range = EntryLengthType(entry).range(raw_params)
            if range.min is not None and range.min == range.max and range.min <= 8:
                # If we have a fixed size buffer, stash it in an integer. We
                # only allow bitstrings under a 'char', otherwise we start
                # getting endian issues....
                return 'unsigned char'
            return 'BitBuffer'
        elif entry.format == fld.Field.FLOAT:
            range = EntryLengthType(entry).range(raw_params)
            if range.max is not None and range.max == 32:
                return 'float'
            else:
                return 'double'
        else:
            raise Exception("Unhandled field format '%s'!" % entry)
    elif isinstance(entry, seq.Sequence) and entry.value is not None and \
            not children_contain_data(entry):
        # This sequence has hidden children and a value; we can treat this as
        # an integer.
        return _integer_type(EntryValueType(entry))
    elif isinstance(entry, chc.Choice) and not children_contain_data(entry):
        return 'enum %s' % enum_type_name(entry)
    else:
        return "struct " + typename(escaped_type(entry))

def ctype(variable):
    """Return the c type name for an entry"""
    if isinstance(variable, Entry):
        return _entry_type(variable)
    elif isinstance(variable, EntryType):
        return _entry_type(variable.entry)
    elif isinstance(variable, IntegerType):
        return _integer_type(variable)
    else:
        raise Exception("Unknown parameter type '%s'!" % variable)

def define_params(entry):
    result = ""
    for param in get_params(entry):
        if param.direction is param.IN:
            result += ", %s %s" % (ctype(param.type), param.name)
        else:
            result += ", %s* %s" % (ctype(param.type), param.name)
    return result

def option_output_temporaries(entry, child_index):
    """Return a dictionary of {name : temp_name}.

    This maps the option entries name to a local's name. This is done because
    each of the options may have a different type for the same named output
    (for example, the different options may be of type int, unsigned char,
    long long...) meaning we cannot pass the choice's output directly by
    pointer.
    """
    # If we are a choice entry, a single output parameter of the choice
    # may come from one of multiple types of children, each of which might
    # have a different integer type (eg: byte, int, long long). To handle this
    # we use local variables for all outputs from a choice, before assigning
    # them to the 'real' output at the end.
    assert isinstance(entry, chc.Choice)
    result = {}
    params = [param.name for param in get_params(entry)]
    params.extend(local.name for local in local_vars(entry))

    for param in get_passed_variables(entry, entry.children[child_index]):
        if param.direction == param.OUT and param.name in params:
            # We found a parameter that is output from the entry; to
            # avoid the possibility that this is a different type to
            # the parent output, we stash it in a temporary location.
            result[param.name] = '%s%i' % (param.name, child_index)
    return result

def local_variables(entry):
    for local in local_vars(entry):
        yield local
    if isinstance(entry, chc.Choice):
        for i, child in enumerate(entry.children):
            lookup = option_output_temporaries(entry, i)
            for param in get_passed_variables(entry, entry.children[i]):
                try:
                    # Create a temporary local for this parameter...
                    yield Local(lookup[param.name], param.type)
                except KeyError:
                    # This variable isn't output from the choice...
                    pass

def _passed_variables(entry, child_index):
    temp = {}
    if isinstance(entry, chc.Choice):
        temp = option_output_temporaries(entry, child_index)

    for param in get_passed_variables(entry, entry.children[child_index]):
        try:
            # First check to see if the parameter is one that we map locally...
            yield Param(temp[param.name], param.OUT, param.type)
        except KeyError:
            yield param

def call_params(parent, i, result_name):
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
    locals = list(local.name for local in local_variables(parent))
    params = dict((param.name, param.direction) for param in get_params(parent))
    for param in _passed_variables(parent, i):
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
        operator.lshift : '<<',
        operator.rshift : '>>',
        }

def value(entry, expr):
  """
  Convert an expression object to a valid C expression.

  entry -- The entry that will use this value.
  expr -- The bdec.expression.Expression instance to represent in C code.
  """
  if isinstance(expr, int):
      return str(expr)
  elif isinstance(expr, Constant):
      if expr.value >= (1 << 32):
          return "%iLL" % expr.value
      elif expr.value > (1 << 31):
          return "%iL" % expr.value
      return int(expr.value)
  elif isinstance(expr, ValueResult):
      return local_name(entry, expr.name)
  elif isinstance(expr, LengthResult):
      return local_name(entry, expr.name + ' length')
  elif isinstance(expr, Delayed):
      left = value(entry, expr.left)
      right = value(entry, expr.right)

      cast = ""
      left_type = _type_from_range(expression_range(expr.left, entry, raw_params))
      right_type = _type_from_range(expression_range(expr.right, entry, raw_params))
      result_type = _type_from_range(expression_range(expr, entry, raw_params))

      types = unsigned_types.copy()
      types.update(signed_types)
      if types[result_type][0] > max(types[left_type][0], types[right_type][0]):
          # If the result will be bigger than both left and right, we will
          # explicitly cast to make sure the operation is valid. For example,
          # '1 << 63' is invalid, but '(long long)1 << 63' is ok.
          cast = "(%s)" % result_type
      return "(%s%s %s %s)" % (cast, left, _OPERATORS[expr.op], right)
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

