
.. _bdec-specification:

===================
Bdec specifications
===================

The bdec specification is machine readable, and is capable of describing
multiple existing binary formats.

The bdec decoder is capable of loading the specification, and creates a
decoder that can produce either python instances or xml output representing
the data encoded in the binary files.

The four types of objects in a specification are;

.. toctree::
    :maxdepth: 2

    field
    sequence
    sequenceof
    choice
    expressions

