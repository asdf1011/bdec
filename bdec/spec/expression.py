
def compile(text):
    """
    Compile a length text into an integer convertible object.
    """
    try:
        return int(text)
    except ValueError:
        pass

    # We have a complicated expression; we'll have to parse it.
    from pyparsing import Word, nums, Optional, Literal, Forward
    integer = Word(nums).addParseAction(lambda s,l,t: [int(t[0])])
    expression = Forward()
    factor = integer | ('(' + expression + ')')
    expression << (factor + '+' + factor).addParseAction(lambda s,l,t: [t[0] + t[2]])
    return expression.parseString(text)[0]
