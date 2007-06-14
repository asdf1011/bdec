import bdec.spec
import operator

class ExpressionError(bdec.spec.LoadError):
    def __init__(self, ex):
        self.error = ex

    def __str__(self):
        return str(self.error)

class _Delayed:
    """
    Class to delay the operation of an integer operation.

    This is because some parts of an expression may not be accessible until
    the expression is used (for example, an expression object that
    references the decoded value of another field).
    """
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __int__(self):
        return self.op(int(self.left), int(self.right))

def _half(op):
    """
    Create a handler to handle half of a binary expression.

    The handler returns a callable object that takes the second half
    of the binary expression.
    """
    def handler(s,l,t):
        return lambda left: _Delayed(op, left, t[1])
    return handler

def _collapse(s,l,t):
    """
    Collapse a series of half binary expressions into one.
    """
    # Note that here we are assuming the first item is complete, and
    # the rest of the items are 'half' expressions.
    result = t[0]
    for next in t[1:]:
        result = next(result)
    return result

def _no_named_lookups(name):
    raise NotImplementedError("Named lookups not supported")

def compile(text, name_lookup=_no_named_lookups):
    """
    Compile a length expression into an integer convertible object.

    :param name_lookup: A object to call to query a named integer 
        convertible object.
    """
    try:
        return int(text)
    except ValueError:
        pass

    # We have a complicated expression; we'll have to parse it.
    from pyparsing import Word, alphanums, nums, Forward, StringEnd, ZeroOrMore, ParseException
    integer = Word(nums).addParseAction(lambda s,l,t: [int(t[0])])
    named_reference = ('${' + Word(alphanums + ' _+:.') + '}').addParseAction(lambda s,l,t:name_lookup(t[1]))

    expression = Forward()
    factor = integer | named_reference | ('(' + expression + ')').addParseAction(lambda s,l,t:t[1])

    mul = ('*' + factor).addParseAction(_half(operator.mul))
    div = ('/' + factor).addParseAction(_half(operator.div))
    mod = ('%' + factor).addParseAction(_half(operator.mod))
    term = (factor + ZeroOrMore(mul | div | mod)).addParseAction(_collapse)

    add = ('+' + term).addParseAction(_half(operator.add))
    sub = ('-' + term).addParseAction(_half(operator.sub))
    expression << (term + ZeroOrMore(add | sub)).addParseAction(_collapse)

    complete = expression + StringEnd()
    try:
        return complete.parseString(text)[0]
    except ParseException, ex:
        raise ExpressionError(ex)
