
========================
Xml specification format
========================

Bdec specifications are written in an xml markup format. The specification
allows for many of the common (and not so common) features found in most
binary file formats.


Protocol element
================

The protocol element is the outer element in a specification. No attributes can
be set within the protocol block. The protocol block can have two child 
elements;

    * A single `common element`_ (optional)
    * A single :ref:`protocol entry <bdec-entries>`

The single protocol entry will be the default entry used when decoding.


.. _common-elements:

Common element
==============

The common element can contain multiple :ref:`entries <bdec-entries>` that can be
referenced using :ref:`reference entries <format-reference>`.


Example
=======

An extremely simple protocol specification::

  <protocol>
    <sequence name="packet">
      <reference name="header" />
      <reference name="payload" />
    </sequence>

    <common>
      <sequence name="header">
        <field name="id" length="16" value="0x863f" />
        <field name="date" length="16" type="integer" />
      </sequence>

      <sequence name="init">
        <field name="id" length="8" value="0x0" />
        <field name="name length" length="16" />
        <field name="name" length="${name length} * 8" type="text" />
      </sequence>

      <sequence name="data message">
        <field name="id" length="8" value="0x1" />
        <field name="data length" length="16" />
        <field name="data" length="${data length} * 8" type="hex" />
        <field name="trailer" type="integer" length="32" />
      </sequence>

      <choice name="payload">
        <reference name="init" />
        <reference name="data message" />
      </choice>
    </common>
  </protocol>

