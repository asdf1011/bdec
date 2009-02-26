
.. _bdec-constraints:


===========
Constraints
===========

We can place contraints on what values are considered valid for a given entry.
The constraints are;

  * An `expected value`_
  * A `minimum or maximum`_ value

.. _expected value: `Expected values`_
.. _minimum or maximum: `Value ranges`_

Expected values
===============

Entries can have an expected value, and will fail to decode if the data found
doesn't match the expected value.

The expected value attribute can be either in hex (eg: value="0xf3"), or in the
type of the entry::

  <field name="null" length="8" value="0x0" />
  <field name="identifier" length="16" type="integer" value="18" />
  <field name="name" length="120" value="expected string" />


Value ranges
============

Entries that can be converted to integers can have a minimum and a maximum
value. For example, you may want a field that decodes all numerical text
entries '0' to '9'.

Both min and max are inclusive; ie::

    min <= value <= max

If the decoded value falls outside the minimum or maximum, the entry fails to
decode. eg::

   <field name="digit" length="8" type="text" min="48" max="57" />

will fail to decode bytes with value 0-47, and 58-255.


Advanced usage
==============

Usually constraints will only ever be used with fields, but they can also be
used with other entries (that have a value, such as sequences with a 'value'
attribute, or choices where all options are of the same type). In these cases
the expected value attribute must be named 'expected', not 'value').

