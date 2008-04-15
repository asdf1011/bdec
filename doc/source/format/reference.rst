
.. _format-reference:

=================
Reference entries
=================

Reference entries are used to mark that a child entry is a reference to a 
:ref:`top level entry <common-elements>`. This allows the specification to be 
broken up into logical boundaries.

References are identified by name, and cannot include modifications to the top
level entry (eg: no changing the type of fields, changing the children of a 
sequence, adding an end-entry, ...).

The referenced entry doesn't need to be specified at the time it is referenced
(although it must be specified by the time the specification finishes loading).
Referenced entries can be used to enable recursive specifications (eg: pdf).


Specification
=============

A bdec reference can have one attribute;

  * A name


Examples
========

Reuse a null terminating string::

  <common>
    <sequenceof name="null terminating string">
      <choice name="entry">
        <field name="null" length="8" value="0x0" ><end-sequenceof /></field>
        <field name="char" length="8" type="text" />
      </choice>
    </sequenceof>

    <sequence name="address">
      <field name="street number" length="32" type="integer" />
      <sequence name="street">
        <reference name="null terminating string" />
      </sequence>
      <sequence name="city">
        <reference name="null terminating string" />
      </sequence>
    </sequence>
  </common>

