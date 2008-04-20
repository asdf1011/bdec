
"""
Bdec is a library for decoding binary files.

A decoder is made up of classes derived from bdec.entry.Entry. These
are:

 * bdec.field.Field
 * bdec.sequence.Sequence
 * bdec.choice.Choice
 * bdec.sequenceof.SequenceOf

A specification is a tree of entry objects, and can be used in multiple ways.
It can:

 * Decode and encode data at runtime (bdec.output)
 * Be compiled to a static decoder (bdec.tools.compiler)
 * Be defined in a textual format (bdec.spec)
"""

__version__ = "0.3.1"

class DecodeError(Exception):
    """ An error raise when decoding fails """
    def __init__(self, entry):
        import bdec.entry as ent
        assert isinstance(entry, ent.Entry)
        self.entry = entry

