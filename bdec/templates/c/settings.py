#   Copyright (C) 2010 Henry Ludemann
#   Copyright (C) 2010 PRESENSE Technologies GmbH
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
from bdec.constraints import Equals
from bdec.data import Data
from bdec.encode import get_encoder
from bdec.entry import Entry
from bdec.inspect.solver import solve_expression
import bdec.field as fld
import bdec.sequence as seq
from bdec.sequenceof import SequenceOf
from bdec.expression import ArithmeticExpression, ReferenceExpression, \
        Constant, UndecodedReferenceError, RoundUpDivisionExpression
from bdec.inspect.param import Local, Param, MAGIC_UNKNOWN_NAME
from bdec.inspect.type import EntryLengthType, EntryValueType, IntegerType, EntryType, expression_range

keywords=['char', 'int', 'short', 'long', 'float', 'if', 'then', 'else', 'struct', 'for', 'null', 'signed', 'true', 'false']

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
    return type_from_range(type.range(raw_params))

def type_from_range(range):
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

def _get_param_string(params):
    result = ""
    for param in params:
        if param.direction is param.IN:
            type = ctype(param.type)
            pointer = '*' if not is_numeric(type) else ''
            result += ", %s%s %s" % (type, pointer, param.name)
        else:
            result += ", %s* %s" % (ctype(param.type), param.name)
    return result

def define_params(entry):
    return _get_param_string(get_params(entry))

def encode_params(entry):
    return _get_param_string(encode_params.get_params(entry))

def option_output_temporaries(entry, child_index, params):
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
    params_and_locals = list(params.get_params(entry)) + list(params.get_locals(entry))
    names_and_types = set((p.name, ctype(p.type)) for p in params_and_locals)

    for param in params.get_passed_variables(entry, entry.children[child_index]):
        if param.direction == param.OUT and param.name != MAGIC_UNKNOWN_NAME and (param.name, ctype(param.type)) not in names_and_types:
            # We found a parameter that is output from the entry; to
            # avoid the possibility that this is a different type to
            # the parent output, we stash it in a temporary location.
            result[param.name] = '%s%i' % (param.name, child_index)
    return result

def _locals(entry, params):
    for local in params.get_locals(entry):
        yield local
    if isinstance(entry, chc.Choice):
        for i, child in enumerate(entry.children):
            lookup = option_output_temporaries(entry, i, params)
            for param in get_passed_variables(entry, entry.children[i]):
                try:
                    # Create a temporary local for this parameter...
                    yield Local(lookup[param.name], param.type)
                except KeyError:
                    # This variable isn't output from the choice...
                    pass

def local_variables(entry):
    return _locals(entry, decode_params)

def encode_local_variables(entry):
    return _locals(entry, encode_params)

def _passed_variables(entry, child_index, params):
    temp = {}
    if isinstance(entry, chc.Choice):
        temp = option_output_temporaries(entry, child_index, params)

    for param in params.get_passed_variables(entry, entry.children[child_index]):
        try:
            # First check to see if the parameter is one that we map locally...
            yield Param(temp[param.name], param.OUT, param.type)
        except KeyError:
            yield param

def is_pointer(name, entry, params):
    """Check to see if a local variable or a parameter is a pointer.

    name -- The name of the local variable / parameter
    entry -- The entry containing the variable / parameter
    params -- A _Parameters instance.
    """
    # If the parameter is an output parameter, it must be a pointer.
    if name in (p.name for p in params.get_params(entry) if p.direction == p.OUT):
        return True
    # If it's an input (but is of a complex type), it's also passed as a
    # pointer.
    complex_types = list(p.name for p in params.get_params(entry) if not is_numeric(ctype(p.type)))
    return name in complex_types

def _value_ref(name, entry, params):
    if is_pointer(name, entry, params):
        return '*%s' % name
    return name

def local_reference_name(entry, ref, params):
    return False, _value_ref(local_name(entry, ref.param_name()), entry, params)

def get_reference_stack(entries, names):
    """Get the new stack pointing to a given referenced.

    entries -- The stack of (entry, name) tuples, it will starting searching
        at the end for the referenced entry.
    names -- A list of named entries to find.
    return -- The new stack of (entry,  name) tuples."""
    # TODO: At the moment it only walks down the reference stack; it should also
    # attempt to walk up it.
    entry_stack = list(entries)
    entry_stack += _get_child_entries(entries[-1][0], names)
    return entry_stack

def relative_reference_name(entries, ref, local_name):
    """Return the name of the referenced entry relative to the top of the entries stack."""
    if ':' in ref.name:
        # This entry is hidden, so we should store it locally.
        return True, variable('temp ' + ref.name)
    entry_stack = get_reference_stack(entries, ref.name.split('.'))
    return False, '%s.%s' % (local_name, _get_child_reference(entry_stack[1:]))

def _call_params(parent, i, result_name, params):
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
    for param in _passed_variables(parent, i, params):
        if param.direction == param.OUT:
            expects_pointer = True
        else:
            # In parameters expect a pointer for complex types...
            expects_pointer = not is_numeric(ctype(param.type))

        is_local_pointer = is_pointer(param.name, parent, params)
        local_name = param.name
        if param.name == MAGIC_UNKNOWN_NAME:
            # All 'magic' parameters (ie: those that represent the child's
            # value, not just references it will use) are pointers.
            is_local_pointer = True
            local_name = result_name

        if expects_pointer == is_local_pointer:
            # If both us & the child are the same, just pass it through
            result += ', %s' % local_name
        elif expects_pointer:
            result += ', &%s' % local_name
        else:
            result += ', *%s' % local_name
    return result

def decode_passed_params(parent, i, result_name):
    return _call_params(parent, i, result_name, decode_params)

def encode_passed_params(parent, i, result_name):
    return _call_params(parent, i, result_name, encode_params)

_OPERATORS = {
        operator.__div__ : '/', 
        operator.__mod__ : '%',
        operator.__mul__ : '*',
        operator.__sub__ : '-',
        operator.__add__ : '+',
        operator.lshift : '<<',
        operator.rshift : '>>',
        }

def value(entry, expr, params=None, magic_expression=None, magic_name=None, ref_name=None):
  """
  Convert an expression object to a valid C expression.

  entry -- The entry that will use this value.
  expr -- The bdec.expression.Expression instance to represent in C code.
  params -- The parameters to use for finding variables. If None, it will use
    the decode parameters (decode_params).
  magic_expression -- If the 'magic_expression' is found it will be replaced
    with the 'magic_name'.
  magic_name -- The 'magic' name to use when 'magic_expression' is found.
  """
  ref_name = ref_name or local_reference_name
  if params is None:
      params = decode_params
  if expr is magic_expression:
      return magic_name
  elif isinstance(expr, int):
      return str(expr)
  elif isinstance(expr, Constant):
      if expr.value >= (1 << 32):
          return "%iLL" % expr.value
      elif expr.value > (1 << 31):
          return "%iL" % expr.value
      return int(expr.value)
  elif isinstance(expr, ReferenceExpression):
      return ref_name(entry, expr, params)[1]
  elif isinstance(expr, ArithmeticExpression):
      left = value(entry, expr.left, params, magic_expression, magic_name, ref_name)
      right = value(entry, expr.right, params, magic_expression, magic_name, ref_name)

      cast = ""
      left_type = type_from_range(expression_range(expr.left, entry, raw_params))
      right_type = type_from_range(expression_range(expr.right, entry, raw_params))
      result_type = type_from_range(expression_range(expr, entry, raw_params))

      types = unsigned_types.copy()
      types.update(signed_types)
      if types[result_type][0] > max(types[left_type][0], types[right_type][0]):
          # If the result will be bigger than both left and right, we will
          # explicitly cast to make sure the operation is valid. For example,
          # '1 << 63' is invalid, but '(long long)1 << 63' is ok.
          cast = "(%s)" % result_type
      return "(%s%s %s %s)" % (cast, left, _OPERATORS[expr.op], right)
  elif isinstance(expr, RoundUpDivisionExpression):
      left = value(entry, expr.numerator, params, magic_expression, magic_name, ref_name)
      right = value(entry, expr.denominator, params, magic_expression, magic_name, ref_name)
      rounding = '1' if expr.should_round_up else '0'
      return function('divide with rounding') + '(%s, %s, %s)' % (left, right, rounding)
  else:
      raise Exception('Unknown length value', expr)

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

def encode_name(entry):
    return function('encode ' + escaped_type(entry))

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
    if char == '\\':
        return '\\\\'
    if char in _PRINTABLE:
        return char
    return '\\%03o' % ord(char)

def c_string(data):
    """Return a correctly quoted c-style string for an arbitrary binary string."""
    return '"%s"' % ''.join(_c_repr(char) for char in data)

def _get_equals(entry):
    for constraint in entry.constraints:
        if isinstance(constraint, Equals):
            return constraint.limit

def _are_expression_inputs_available(expr, entry):
    """Check to see if all of the inputs to an expression are available."""
    names = [p.name for p in encode_params.get_params(entry) if p.direction == p.IN]

    result = ReferenceExpression('result')
    inputs = [p.name for p in encode_params.get_params(entry) if p.direction == p.IN]
    constant, components = solve_expression(result, expr, entry, raw_decode_params, inputs)
    for ref, expr, inverted in components:
        if variable(ref.name) not in names:
            # The expression references an item that isn't being passed in.
            return False
    return True

def get_sequence_value(entry):
    """Get a sequences value when encoding.

    Returns a (value, should_solve) tuple."""
    # When we have an expected value, we should using that as the value to solve...
    should_solve = True
    in_params = [p.name for p in encode_params.get_params(entry) if p.direction == p.IN]
    if contains_data(entry):
        # This entry is visible; use its 'value' input.
        value_name = 'value' if is_numeric(ctype(entry)) else 'value->value'
    elif variable(entry.name) in in_params:
        # This entry has been referenced elsewhere, and it's value is
        # being passed as an exression.
        value_name = variable(entry.name)
    elif _are_expression_inputs_available(entry.value, entry):
        # All of the components of this entrie's value are being passed in (ie:
        # we can determine its value)
        value_name = value(entry, entry.value)
    elif _get_equals(entry) is not None:
        # This entry has an expected value
        value_name = value(entry, _get_equals(entry))
    else:
        # We cannot determine the value of this entry! It's probably being
        # derived from child values.
        # This isn't being passed in an input parameter! Presumably
        # it is has a fixed value, or is derived from other values...
        should_solve = False
        value_name = value(entry, entry.value)
    return value_name, should_solve

def get_expected(entry):
    expected = _get_equals(entry)
    if expected is not None:
        if settings.is_numeric(settings.ctype(entry)):
            return value(entry, expected)
        elif entry.format == fld.Field.TEXT:
            return '{%s, %i}' % (c_string(expected.value), len(expected.value))
        elif entry.format == fld.Field.BINARY:
            # This is a bitbuffer type; add leading null bytes so we can
            # represent it in bytes.
            null = Data('\x00', 0, 8 - (len(expected.value) % 8))
            data = null + expected.value
            result = '{(unsigned char*)%s, %i, %i}' % (
                    c_string(data.bytes()), len(null),
                    len(data) - len(null))
            return result
        elif entry.format == fld.Field.HEX:
            result = '{(unsigned char*)%s, %i}' % (
                    c_string(expected.value.bytes()), len(expected.value) / 8)
            return result
        else:
            raise Exception("Don't know how to define a constant for %s!" % entry)

def _is_length_known(entry):
    inputs = [p.name for p in raw_encode_params.get_params(entry) if p.direction == p.IN]
    constant, components = solve_expression(entry.length, entry.length, entry, raw_decode_params, inputs)
    return len(components) == 0

def get_null_mock_value(entry):
    """Get a mock value for the given entry.

    Returns a (mock string, should_free_buffer) tuple."""
    should_free_buffer = False
    if settings.is_numeric(settings.ctype(entry)):
        return 0, should_free_buffer

    try:
        # If this entry has a fixed (known) length, just allocate a null
        # buffer on the stack.
        length = entry.length.evaluate({})
        data = '"\\000"' * ((length + 7) / 8)
    except UndecodedReferenceError:
        if _is_length_known(entry):
            # There is an explicit length for this entry.
            length = value(entry, entry.length, encode_params)
            data = "calloc((%s) / 8, 1)" % length
            should_free_buffer = True
        else:
            # The length isn't known; just default it to zero.
            length = 0
            data = '""'
    if entry.format == fld.Field.TEXT:
        value_text = '{%s, (%s) / 8}' % (data, length)
    elif entry.format == fld.Field.HEX:
        value_text = '{(unsigned char*)%s, (%s) / 8}' % (data, length)
    elif entry.format == fld.Field.BINARY:
        value_text = '{(unsigned char*)%s, 0, %s}' % (data, length)
    else:
        raise Exception("Don't know how to define a constant for %s!" % entry)
    return value_text, should_free_buffer


def is_empty_sequenceof(entry):
    return isinstance(entry, SequenceOf) and not contains_data(entry)

def _get_child_entries(entry, child_names):
    """Get an iterable to the list of entries from entry to the items defined by names."""
    if child_names:
        child_name = child_names.pop(0)
        for child in entry.children:
            if child.name == child_name:
                break
        else:
            raise Exception('Failed to find child named %s in %s' % (child_name, entry))

        yield child.entry, variable(child.name)
        for entry, name in _get_child_entries(child.entry, child_names):
            yield entry, name

def _get_child_reference(entries):
    """Get the c-style reference to the entry specified in 'entries'.

    For example, ${header.data length} would be return 'header.dataLength'.
    """
    assert len(entries) != 0
    entry, result = entries.pop(0)
    if not entries:
        # This is the referenced item.
        if is_numeric(ctype(entry)):
            pass
        elif isinstance(entry, seq.Sequence) and entry.value is not None:
            result = '%s.value' % result
        else:
            raise NotImplementedError("Mocking %s is currently not supported" % entry)
    else:
        # We are referencing a child of this entry
        if isinstance(entry, seq.Sequence):
            result = '%s.%s' % (result, _get_child_reference(entries))
        else:
            raise NotImplementedError('Mock references under %s not supported' % entry)
    return result

def get_child_variable(entry, i, param, child_variable):
    """Return the variable referenced by the parameter pass to the i-th child of entry."""
    child = entry.children[i]
    return _get_child_reference([(child.entry, child_variable)] +
            list(_get_child_entries(child.entry, param.name.split('.')[1:])))

def sequence_encoder_order(entry):
    """Return the order we should be encoding the child entries in a sequence.

    Returns a iterable of (child_offset, start_temp_buffer, buffer_name, end_temp_buffers)
    tuples."""
    result_offset = 0
    temp_buffers = []
    encoder = get_encoder(entry, raw_encode_expression_params)
    for child_encoder in encoder.order():
        child = child_encoder.child
        i = entry.children.index(child)

        start_temp_buffer = None
        if i == result_offset:
            # We can encode this entry directly into the result buffer
            buffer_name = 'result'
            result_offset += 1
        else:
            # This entry must be buffered (it cannot be directly appended onto result)
            for b in  temp_buffers:
                if b['end'] == i:
                    # We found an existing temporary buffer we can append to
                    temp_buffer = b
                    break
            else:
                # There isn't an existing temporary buffer we can reuse; create a new one.
                temp_buffer = {'name':'tempBuffer%i' % len(temp_buffers), 'start':i, 'end':i}
                temp_buffers.append(temp_buffer)
            temp_buffer['end'] += 1
            buffer_name = '&%s' % temp_buffer['name']

            if temp_buffer['start'] == i:
                # We found a temporary buffer that starts here
                start_temp_buffer = temp_buffer['name']

        # Check for temporary buffers that start here; not that there can be
        # several temp buffers that need to be chained together (see the
        # xml/089_length_reference regression test).
        end_temp_buffers = []
        should_stop = False
        while not should_stop:
            for temp_buffer in temp_buffers:
                if temp_buffer['start'] == result_offset:
                    # We found a temporary buffer that ends here
                    end_temp_buffers.append(temp_buffer['name'])
                    result_offset = temp_buffer['end']
                    break
            else:
                should_stop = True
        yield i, start_temp_buffer, buffer_name, end_temp_buffers

def breakup_expression(expression, entry):
   inputs = [p.name for p in raw_encode_params.get_params(entry) if p.direction == p.IN]
   constant, components = solve_expression(expression, expression, entry, raw_decode_params, inputs)
   try:
      constant = constant.evaluate({})
   except UndecodedReferenceError:
       pass
   return constant, components

