
.. _format-reference:

=================
Reference entries
=================

Reference entries are used to reference a
:ref:`top level entry <common-elements>` at the current location in the
specification. This allows parts of the specification to be re-used in multiple
locations, and also allows the specification to be broken up into logical
boundaries.

References are identified by name, and cannot include modifications to the top
level entry (eg: no changing the type of fields, changing the children of a 
sequence, adding an end-entry, ...).

It is possible however to give the referenced entry another name, and this can
help in defining common types (such as defining a default integer encoding).

The top level entry doesn't need to be specified in the file before it is
referenced (although it must be specified before the specification has finished
loading). Referenced entries can be used to decode specifications with
recursive data structures (eg: pdf).


Specification
=============

A bdec reference can have one or two attributes;

  * name_ (optional)
  * type_ (optional)

Either a name or a type must be specified for a reference.

.. _name: `Reference name`_
.. _type: `Reference type`_


Reference name
--------------

The name attribute specifies the name to be used for this entry. If no type_
is specified, this is assumed to be the name of the common entry.


Reference type
--------------

If specified, identifies the name of common entry to be referenced. If it is
not specified, the reference name is used to find the referenced entry.


Examples
========

Reuse a 'dword' type and a null terminating string type::

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

