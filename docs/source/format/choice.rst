
.. _format-choice:

==============
Choice entries
==============

Choice entries allow one of many options to be present in the data stream. If
the first option fails to decode, it will try the second (and so on). Only 
when all options have failed to decode will the choice entry fail.


Specification
=============

Choice entries can have up to two attributes.

  * A name (optional)
  * A length_ (optional)
  * An :ref:`if <boolean-expression>` (optional)

The choice must have multiple child entries specifying the different possible
options (ie: :ref:`fields <format-field>`, :ref:`sequences <format-sequence>`,
:ref:`sequenceofs <format-sequenceof>`, other choices, or 
:ref:`references <format-reference>`).

.. _length: `Choice length`_


.. _Choice length:

Choice length
-------------

The choice :ref:`length <bdec-expressions>` is an optional attribute that
specifies the number of bits the entry will contain. It is only used for
validation; if the amount of data decoded by the successful option doesn't
match the expected length the choice will fail to decode.

The length value can reference other entries using
:ref:`expressions <bdec-expressions>`.


Examples
========

Only allow fields with certain values::

  <choice name="whitespace">
      <field name="space" length="8" value="0x20" />
      <field name="tab" length="8" value="0x9" />
  </choice>

Choose between two entry types::
  
  <choice name="entry">
      <sequence name="text entry">
         <field length="8" value="0x0" />
         <field name="length" length="8" />
         <field name="value" length="${length} * 8" type="text" />
      </sequence>
      <sequence name="integer entry">
         <field length="8" value="0x1" />
         <field name="value" length="32" type="integer" />
      </sequence>
  </choice>

Allow only hex characters (eg: characters 'a' .. 'f', 'A' .. 'F', '0' .. '9')::

  <choice name="char">
      <field name="lowercase char" length="8" min="97" max="102" />
      <field name="uppercase char" length="8" min="65" max="70" />
      <field name="number" length="8" min="48" max="57" />
  </choice>
