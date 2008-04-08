
===================
Binary file formats
===================

Binary files contain data encoded in binary form; that is, a format which is
typically easy for a computer to read and write, but contains no textual
information that is directly accessible by a human reader.

Some binary formats include jpg pictures, mp3 audio files, or pdf documents.

The bdec library allows machine readable :ref:`specifications <bdec-specification>`
to be written for existing binary formats, allowing high quality decoders to
be automatically generated.


Why specifications are needed
=============================

Most binary file formats do not use a standardised format for specifying
the data layout in the file; instead, the format specification is usually a
human readable document describing what data is present in the file, and the
layout in which that data is encoded.

If a file format is not intended for data exchange between programs, often
a specification document for the format will not exist; there will instead be 
a single implementation capable of reading and writing to the file.


Manually created decoders
=========================

To create a decoder, a software developer will have to read the specification,
and write software capable of loading that data into memory in a form that
will be able to be processed. This is a labourous job, fraught with
difficulties;

    * The specification may be incomplete, inaccurate, or missing.
    * Validating all the loaded data is very time consuming, and requires
      a lot of code. Failure to validate the data can result in the program
      crashing, potentially allowing malicous data files to execute code
      through buffer overflows.
    * Parts of the specification that aren't commonly found in data files
      may be coded incorrectly, but not found during testing.
    * Writing decoders often involves a large amount of repetition, which
      can frustrate the developer.

These problems make it difficult to read and write decoders.


Existing binary specifications
==============================

There are existing specifications for binary formats, such as `ASN.1`_ and
`CSN.1`_. These specifications have the problem that they cannot be retrofitted
to existing binary formats.

.. _ASN.1: www.asn1.org
.. _CSN.1: www.csn1.info


