
from bdec.data import Data
from bdec.output.instance import get_instance
from bdec.sequence import Sequence
from bdec.spec import load_specs
import os.path
import sys

def load_msword_spec():
    """ Load the msword specifcation.

    return -- (decoder, common, lookup)"""
    spec_dir = os.path.join(os.path.split(__file__)[0], '..', '..')
    filename = os.path.join(spec_dir, 'msword.xml')
    return load_specs([filename])

def decode(data, common):
    """ Decode a msword document.

    data -- A bdec.data.Data instance to decode.
    common -- The common elements returned from load_msword_spec.
    return -- An iterable of decoded elements, as returned by
            bdec.decode.entry.EntryDecoder.decode. """
    msword = Sequence('msword', [])
    yield True, msword.name, msword, Data(), None

    # We want to both yield the header items, and use it's decoded values.
    lookup = dict((e.name, e) for e in common)
    doc_items = list(lookup['document'].decode(data))
    for item in doc_items:
        yield item
    doc = get_instance(doc_items)

    # Decode the bbfat
    for sector in doc.sectors:
        for sect in sector.double_indirection_fat:
            raise NotImplementedError()

