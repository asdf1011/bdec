import bdec.field as fld
from bdec.spec.expression import Delayed, ValueResult, LengthResult, Constant
import operator

keywords=['char', 'int', 'float', 'if', 'then', 'else', 'struct', 'for']

def ctype(entry):
    """Return the c type name for an entry"""
    if isinstance(entry, fld.Field):
        if entry.format == fld.Field.INTEGER:
            return 'int'
        if entry.format == fld.Field.TEXT:
            return 'char*'
        elif entry.format == fld.Field.HEX:
            return 'Buffer'
        elif entry.format == fld.Field.BINARY:
            return 'BitBuffer'
        else:
            raise Exception("Unhandled field format '%s'!" % entry)
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

