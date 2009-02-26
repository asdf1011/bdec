
.. _bdec-expressions:

===========
Expressions
===========

Expressions are used to represent an integral value; for example, the length
of a :ref:`field <format-field>`. Expressions can contain numbers_, `perform 
numerical operations`_, `reference the value`_ of previously decoded fields,
and `reference the length`_ of a previous decoded entry.

.. _perform numerical operations: `Numerical operations`_
.. _reference the value: `Value references`_
.. _reference the length: `Length references`_


Numbers
=======

The simplest expression is just a decimal number. For example, a field that is
one byte long can have an length expression of "8" (ie: 8 bits).


Value references
================

Many fields in a data file need to reference the values of other fields. For
example, variable length fields are typically stored as a length field,
followed by a data field. Expressions can reference the value of the previously
decoded length field by referring to it by name_::

    <field name="data length" length="8" />
    <field name="variable length data" length="${data length}" />

.. _name: `Resolving names`_

Numerical operations
====================

It is often necessary to perform simple numerical operations in an expression.
In the `previous example`_ the length was stored in bits, but it will often be
stored in bytes::

    length="${data length} * 8"

Supported numerical operations include the use of brackets, addition, 
subtraction, multiplication, and division.

.. _previous example: `Value references`_


Length references
=================

It is sometimes necessary to refer to the length of a previously decoded item.
For example, the length value may include a header, followed by a variable 
length data field. The length of the data field is the total length minus the
length of the header entry. The length of the header can be referenced by
name_::

   length="${data length} * 8 - len{header}"


Resolving names
===============

Names are resolved by looking for a previously defined entry with the given 
name.::
    
    <sequence name="data">
       <field name="length" length="16" type="integer" />
       <field name="value" length="${length} * 8" type="text" />
       ...

If there isn't an entry with the matching name, the parent entry will be
checked.::

    <field name="length" length="16" type="integer" />
    <sequence name="data">
       <field name="value" length="${length} * 8" type="text" />
       ...

It is possible to look inside entries by seperating names with the '.' 
character.::

    <sequence name="header"
       <field name="length" length="16" type="integer" />
       ...
    </sequence>
    <field name="data" length="${header.length}" />


Examples
========

A variable length string::

    <field name="length" length="32" type="integer" />
    <field name="text" length="${length} * 8" type="text" />

A variable length data object with a header::

    <sequence name="header">
       <field length="8" value="0x38" />
       <field name="index" length="32" type="integer" />
       <field name="length" length="32" type="integer" />
       ...
    </sequence>
    <field name="data" length="${header.length} * 8 - len{header}" />

A variable length sequence of entries::

    <field name="num items" length="8" />
    <sequenceof name="items" count="${num items}">
       <sequence name="item">
          ...
       </sequence>
    </sequenceof>


.. _boolean-expression:

Boolean expressions
===================

All entries can use an optional 'if' attribute; this attribute contains a
boolean expression. If that expression evaluates to true, the entry will be
decoded, if not, it will be skipped. Boolean expressions can contain all
standard expressions (such as `value references`_, `numerical operations`_,
etc), as well as boolean comparisons (>, ==, &&, ||, etc).

Optional entries can be very useful when the presence of an entry depends on
values that came signifantly before it in the specification, such as flags
indicating the presence of a footer::

    <sequence name="packet">
       <sequence name="header">
          ...
          <field name="has footer:" length="8" />
          ...
       </sequence>
       <sequence name="body">
          ...
       </sequence>
       <sequence name="footer" if="${has footer:}">
          ...
       </sequence>
    </sequence>

When it is possible to use either a :ref:`choice <format-choice>` or several
optional entries, always prefer the choice; it will result in a clearer spec,
and will generate nicer code. For example::

   <!-- This is the bad way to do it -->
   <field name="type:" length="8" />
   <sequence name="a" if="${type:} == 1">
      ...
   </sequence>
   <sequence name="b" if="${type:} == 2">
      ...
   </sequence>
   <sequence name="c" if="${type:} == 3">
      ...
   </sequence>

can be much better specified with a :ref:`choice <format-choice>`::

   <!-- This is the good way to do it -->
   <choice name="packet">
      <sequence name="a">
          <field name="type:" length="8" value="1" />
          ...
      </sequence>
      <sequence name="b">
          <field name="type:" length="8" value="2" />
          ...
      </sequence>
      <sequence name="c">
          <field name="type:" length="8" value="3" />
          ...
      </sequence>
   </choice>


