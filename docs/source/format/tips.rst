
.. _format-tips:

====
Tips
====

Being able to effectively read and modify the specification is crucial to
maintability.


Hiding entries
==============

Some entries are useful to name in the specification, but aren't very useful
to see in the decoded output. For example;

* When using a choice, the options are often distinguished by the first few
  bytes found in each option. These bytes aren't 'interesting' to the user, as
  they are already known.
* When there is a variable length field, it is often represented as an entry
  containing a length, followed by the entry containing the data. The 'length'
  entry isn't interesting to the user.
* There are often sections of a file whose data contains nothing; essentially,
  filler sections of the file.

To hide these entries from the xml output, and from the compiled structures,
the names of these entries can be either left blank, or postfixed with a ':'
character. These entries will be hidden from output.

eg::

  <field name="length:" length="8" type="integer" />
  <field name="data" length="${length:} * 8" type="hex" />

or::

  <choice name="entry">
    <sequence name="triangle">
       <field length="8" value="0x13" />
       ...
    </sequence>
    <sequence name="rectangle">
       <field length="8" value="0x14" />
       ...
    </sequence>
  </choice>

While it is usually useful to hide these entries, when use the bdecode command
line decoder, the '--verbose' option can by used to print these hidden entries.


Named references
================

Specifications often contain entries with a consistent format. For example,
there might be a lot of 32 bit little endian integers. Insted of writing::

   <common>
     <sequence name="header">
       <field length="32" value="0x1234" />
       <field name="year" length="32" type="integer" encoding="little endian" />
       <field name="month" length="32" type="integer" encoding="little endian" />
       <field name="day" length="32" type="integer" encoding="little endian" />
       <field name="version" length="32" type="integer" encoding="little endian" />
     </sequence>
     ...
   </common>

use a common entry that defines types that are used regularly, such as::

   <common>
     <field name="dword" length="32" type="integer" encoding="little endian" />

     <sequence name="header">
       <field length="32" value="0x12345678" />
       <reference name="year" type="dword" />
       <reference name="month" type="dword" />
       <reference name="day" type="dword" />
       <reference name="version" type="dword" />
     </sequence>
     ...
   </common>


Optional entry flags
====================

Often the header of a format has a flag which indicates whether an optional
block of data is present. While it is possible to create a choice with the two
options, this isn't clear or convenient, eg::

  <choice name="header">
     <sequence name="header with footer">
        <field name="footer present" length="8" value="0x1" />
        ...
        <reference name="footer" />
     </sequence>
     <sequence name="header without footer">
        <field name="footer not present" length="8" value="0x0" />
        ...
     </sequence>
  </choice>

This is verbose and difficult to follow. It is possible instead to make the
entry conditional upon an :ref:`expression <boolean-expression>`::

  <sequence name="header">
     <field name="footer present:" length="8" />
     ...
     <sequence name="footer" if="${footer present:}">
        ...
     </sequence>
  </sequence>

As a rule of thumb, if an entry can be present zero or one times, and the
entry depends on a previous flag, use a conditional. If one of several
possibilites can be used (eg: differing payloads in a message, etc), use a
choice.

