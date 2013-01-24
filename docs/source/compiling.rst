
.. _compiling-to-c:

Compiling to C
==============

Specifications can be compiled to efficient, readable C language decoders by
running::

  bcompile png.xml

The generated source code includes a sample 'main.c' that can decode png files
to xml. See the alternate main.c_ that prints the image width and height, and
displays all png 'text' sections.

To generate the encoder source code, pass the '--encoder' flag::

  bcompile --encode png.xml

.. _main.c: files/main.c
