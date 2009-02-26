
.. _format-sequence:

================
Sequence entries
================

Sequence entries are simple containers for other entries (see the 
`object composition`_ entry in wikipedia_). Type are similar in
function to structs in C.

.. _object composition: http://en.wikipedia.org/wiki/Object_composition
.. _wikipedia: http://wikipedia.org/


Specification
=============

Bdec sequence entries can have 3 attributes;

  * A name (optional)
  * A length_ (optional)
  * A value_ (optional)
  * An :ref:`if <boolean-expression>` (optional)

Sequence attributes can contain any other type of entry (ie: 
:ref:`fields <format-field>`, sequences, :ref:`sequenceofs <format-sequenceof>`,
:ref:`choices <format-choice>`, and :ref:`references <format-reference>`).

.. _length: `Sequence length`_
.. _value: `Sequence value`_


Sequence length
===============

The sequence length is an optional :ref:`expression <bdec-expressions>` 
that sets the length of the sequence in bits. It is used to validate the
combined length of all of the items contained within the seqeuence.


Sequence value
==============

A sequence can be assigned a value that can be referenced in expressions. The
value itself is an :ref:`expression <bdec-expressions>` that can reference
entries contained within the sequence.

Sequence values can be used for several purposes, including:

  * Converting text lengths to referencable lengths
  * Joining non-adjacent numeric fields into one value
  * Adding custom integer encodings

If a sequence has a value, that value can be limited using :ref:`constraints <bdec-constraints>`.


Examples
========

A simple sequence of fields::

  <sequence name="data">
    <field name="a" length="8" type="integer" />
    <field name="b" length="64" type="text" />
  </sequence>

Validation of the length of child fields using :ref:`expressions <bdec-expressions>`::

  <field name="total length" length="32" encoding="little endian" />
  <sequence name="payload" length="${total length} * 8">
     <field name="a" length="8" />
     ...
     <field name="data length" length="32" encoding="little endian" />
     <field name="data" length="${data length} * 8" />
  </sequence>
