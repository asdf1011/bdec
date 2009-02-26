
.. _format-field:

=============
Field entries
=============

Field entries are the core part of a specification; they represent all the
data that is found in the binary file (entries other than fields are
responsible for the ordering and repetition of the field entries). The
type of the field's data is specified in the field's attributes;

  * Type: The data on disk can be many types, such as text (in any encoding),
    integer (little endian / big endian), and raw binary data.
  * Length: The length of the data may be a fixed length, or it may be
    :ref:`variable length <bdec-expressions>`. The data's length may be less
    than a byte, and it may not be byte aligned.


Specification
=============

Bdec fields have the following attributes;

  * A name (optional)
  * A :ref:`length <bdec-expressions>` in bits
  * A type_ (optional)
  * An encoding (optional)
  * A value_ (optional)
  * :ref:`Constraint <bdec-constraints>` attributes (optional)
  * An :ref:`if <boolean-expression>` (optional)

.. _type: `Field types`_
.. _value: `Expected value`_


Field types
===========

There are currently four available field types. If the type is not specified,
it is assumed to be binary_.

Integer
-------

Integer fields represent numeric values. There are two types of encodings
supported, `little endian and big endian`_. The 'integer' type can be
prefixed with 'signed' to specify that the integer can be negative. eg::

  <!-- Unsigned big endian -->
  <field name="a" type="integer" length="32" />
   
  <!-- Unsigned big endian (note that 'unsigned' is redundant) -->
  <field name="a" type="unsigned integer" length="32" />
   
  <!-- Signed big endian (note that 'big endian' is rendundant) -->
  <field name="a" type="signed integer" encoding="big endian" length="16" />
   
  <!-- Signed little endian -->
  <field name="a" type="signed integer" encoding="little endian" length="64" />

The default encoding is unsigned big endian.

.. _little endian and big endian: http://en.wikipedia.org/wiki/Endianness 


Text
----

Text fields represent textual data in the binary file (ie: data that can be
printed). It can use any unicode encoding, and defaults to ascii.


Hex
---

Hex fields represent binary data whose length is a multiple of whole bytes. It
has no encoding.


Binary
------

Binary fields represent binary data of any length. It has no encoding.


Expected value
==============

The 'value' attribute is another name for the 'expected' :ref:`constraint <bdec-constraints>` .


Examples
========

A numeric field that is 2 bytes long, in big endian format::

   <field name="data" length="16" type="integer" encoding="big endian" />

A utf-16 text field that is 8 bytes long::

   <field name="name" length="64" type="text" encoding="utf16" />

A single bit boolean flag::

   <field name="is header present" length="1" />

A two byte field that has an expected value::

   <field name="id" length="16" value="0x00f3" />

A single numerical character (eg: characters '0'..'9')::

   <field name="number" length="8" min="48" max="57" />
