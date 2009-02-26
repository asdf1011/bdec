
.. _instance-decoder:

Python instance decoder
=======================

:ref:`Specifications <bdec-specification>` can be loaded directly from python
code, and can be used to decode directly to python instances::

  from bdec.data import Data
  from bdec import DecodeError
  from bdec.spec.xmlspec import load
  from bdec.output.instance import decode
  
  spec = load('test.xml')[0]
  data = Data(open('data.bin', 'rb').read())
  try:
      values = decode(spec, data)
  except DecodeError, err:
      print 'Oh oh...', err

The 'values' object now represents the decoded data in python instances;

* :ref:`Fields <format-field>` decode to their natural type; eg: integers,
  strings, or for 'binary' types, to a Data instance.
* :ref:`Sequences <format-sequence>` act as objects; access child entries with
  '.' (eg: a.b).
* :ref:`SequenceOf <format-sequenceof>` entries decode to a list.
* :ref:`Choice <format-choice>` entries are like a sequence, but only the
  child that was actually decoded will be present.

For example, given the following spec::

 <protocol>
    <sequence name="a">
       <field name="b" length="16" type="text" />
       <field name="count:" length="8" />
       <sequenceof name="values" count="${count:}">
          <field name="c" length="8" type="integer" />
       </sequenceof>
    </sequence>
 </protocol>

You can use the decoded instance like::

 result = decode(spec[0], data)
 print result.a.b
 for c in result.a.values:
     print c
