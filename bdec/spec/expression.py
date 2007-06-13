import bdec.spec
import operator

class ExpressionError(bdec.spec.LoadError):
    def __init__(self, ex):
        self.error = ex

    def __str__(self):
        return str(self.error)

def _half(op):
    """
    Create a handler to handle half of a binary expression.

    The handler returns a callable object that takes the second half
    of the binary expression.
    """
    def handler(s,l,t):
        return lambda left: op(left, t[1])
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

def compile(text):
    """
    Compile a length text into an integer convertible object.
    """
    try:
        return int(text)
    except ValueError:
        pass

    # We have a complicated expression; we'll have to parse it.
    from pyparsing import Word, nums, Forward, StringEnd, ZeroOrMore, ParseException
    integer = Word(nums).addParseAction(lambda s,l,t: [int(t[0])])
    expression = Forward()
    factor = integer | ('(' + expression + ')').addParseAction(lambda s,l,t:t[1])

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
