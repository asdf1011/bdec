
.. _compiling-to-c:

Compiling to C
==============

:ref:`Specifications <bdec-specification>` can be compiled to efficient,
readable C language decoders by running::

  bcompile png.xml

The generate source includes a sample 'main.c' that can be used as for
decoding png files to xml. See the alternate main.c_ that prints the image
width and height, and displays all png 'text' sections.

.. _main.c: files/main.c
