
from bdec.choice import Choice
from bdec.constraints import Equals
from bdec.data import Data
from bdec.entry import is_hidden
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

class ParserElement:
    def __init__(self, entry):
        self.entry = entry

    def parseString(self, text):
        #list(self.entry.decode(Data(text)))
        stack = []
        tokens = []
        data = Data(text)
        for is_starting, name, entry, data, value in self.entry.decode(data):
            if is_starting:
                stack.append(tokens)
                tokens = []
            else:
                if name and not is_hidden(name) and value is not None:
                    tokens.append(value)

                action = None
                try:
                    action = entry.action
                except AttributeError:
                    pass

                if action:
                    print 'got an action!'
                    tokens = action(tokens)
                    print tokens

                # Extend the current tokens list with the child tokens
                stack[-1].extend(tokens)
                tokens = stack.pop()
        assert len(stack) == 0
        return tokens

class Word(ParserElement):
    def __init__(self, chars):
        options = [Field('char', length=8, format=Field.TEXT, constraints=[Equals(c)]) for c in chars]
        options.append(Sequence(None, []))
        entry = SequenceOf('word', Choice('chars', options), count=None, end_entries=[options[-1]])
        entry.action = lambda t: [''.join(t)]
        ParserElement.__init__(self, entry)

