
class DecodeError(Exception):
    """ An error raise when decoding fails """
    def __init__(self, entry):
        import bdec.entry as ent
        assert isinstance(entry, ent.Entry)
        self.entry = entry

__version__ = "0.3.0"
