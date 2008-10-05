
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

It is possible to give the referenced entry another name, and this can help in
defining common types (such as defining a default integer encoding).

The referenced entry doesn't need to be specified at the time it is referenced
(although it must be specified by the time the specification finishes loading).
Referenced entries can be used to enable recursive specifications (eg: pdf).


Specification
=============

A bdec reference can have one or two attributes;

  * name -- The name to use for the referenced entry.
  * type -- If specified, identifies the name of entry to be referenced. If it
        is not specified, the reference name is used to find the referenced
        entry.



Examples
========

Reuse a null terminating string::

  <common>
    <field name="dword" length="32" encoding="little endian" />

    <sequenceof name="null terminating string">
      <choice name="entry">
        <field name="null" length="8" value="0x0" ><end-sequenceof /></field>
        <field name="char" length="8" type="text" />
      </choice>
    </sequenceof>

    <sequence name="address">
      <reference name="flat number" type="dword" />
      <reference name="street number" type="dword" />
      <reference name="street" type="null terminating string" />
      <reference name="city" type="null terminating string" />
    </sequence>
  </common>

