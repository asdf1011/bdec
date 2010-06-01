
Tutorial
========

If you haven't read the :ref:`format documents <bdec-specification>` yet, now
is a good time to do so. This document will discuss writing a bdec 
specification for a format you have documention of, and sample data files to
test with.


Preparation
-----------

First we need to find a specification for the file type we want to decode. Try
searching on google (eg: 'jpeg specification', 'png file format'), or on a site
like wotsit_.

These documents can be very large and difficult to understand; they include 
information on not only the file format, but also how the data should be
interpretted. For the purpose of decoding the file, we only care about how the 
data is represented on disk, so search through the document until you find the 
section about the on disk format. Finding the section on the header (the first 
part of the file) is an excellent place to start.

In this tutorial we will write a rudimentary `png`_ file format specification
(a common image file format).

.. _png: http://www.libpng.org/pub/png/spec/1.1/PNG-Contents.html
.. _wotsit: http://www.wotsit.org


Getting started
---------------

To start, it is an excellent idea to attempt decoding of a small and simple
file in the target format. If you have access to an editor capable of creating
files in the format, create (and save) an empty document. For this tutorial, I
created a small 5x5 white png image.

We start by creating a new xml document, named png.xml::

  <protocol>
     <sequence name="png">
     </sequence>
  </protocol>

Now we can try running 'decode', giving the specification and the file to 
decode. ::

  bdecode -f white.png png.xml

Which gives the results::

  <png>
  </png>
  Over 8 bytes undecoded!
  hex (8 bytes): 89504e470d0a1a0a
  656 bytes undecoded!

We have now started to decode the file, which is the first step in writing a
working specification!


Writing the specification
-------------------------

We'll start by decoding the header; for example, the png specification has a 
section 'File structure', where we find out that all png files start with an 8 
byte signature. ::

  <protocol>
     <sequence name="png">
        <field name="signature" length="64" type="hex" value="0x89504e470d0a1a0a" />
     </sequence>
  </protocol>

Note that the length is 64, not 8! This is because all lengths in a 
specification are in bits, not bytes (so we need to multiply by eight). This 
decodes to::

  <png>
    <signature />
  </png>
  Over 8 bytes undecoded!
  hex (8 bytes): 0000000d49484452
  592 bytes undecoded!

We have now started to decode the file! Files that aren't png will no longer
decode, as they won't start with the required signature.


Updating the specification
--------------------------

Writing a new specification is an iterative process; ie: continually updating
the specification while decoding a sample file. Ideally we'll do this with as
few updates of the specification as possible before decoding again, as this 
will give us quick feedback necessary for not only error checking, but also
inspiration to decode 'just a little more...'.

The next part of the png specification defines a 'Chunk' structure, which 
makes up the rest of the file. Each chunk has a length, a type, data, and a 
crc. ::

  <protocol>
     <sequence name="png">
        <field name="signature" length="64" type="hex" value="0x89504e470d0a1a0a" />
        <sequenceof name="chunks">
          <reference name="unknown chunk" />
        </sequenceof>
     </sequence>

     <common>
       <sequence name="unknown chunk">
          <field name="data length:" length="32" type="integer" />
          <field name="type" length="32" type="hex" />
          <field name="data" length="${data length:} * 8" type="hex" />
          <field name="crc" length="32" type="hex" />
       </sequence>
     </common>
  </protocol>

A few things to note:

  * We've put the 'unknown chunk' in the common section; it is a good
    idea to separate logical constructs in different parts of the
    specification.
  * The entry 'data' is a variable length field
  * The name of the 'data length:' field has a trailing ':'. This acts as a
    hint to hide the output of 'data length:' field, so it will not be
    displayed.

Running the decode, we successfully get four chunks decoding, before we run
out of data with the error::

   ...
        </unknown-chunk>
        <unknown-chunk>
   png.xml[11]: integer 'data length:' (big endian) - Asked for 32 bits, but only have 0 bits available!

This is because the sequenceof entry doesn't know when to stop decoding; ie: 
there isn't a count, a length, or an end-entry. From reading the specification,
we find that a png file is supposed to end with an 'IEND' chunk. Lets add it! ::

  <protocol>
     <sequence name="png">
        <field name="signature" length="64" type="hex" value="0x89504e470d0a1a0a" />
        <sequenceof name="chunks">
          <choice name="chunk">
              <reference name="unknown chunk" />
              <sequence name="end">
                 <reference name="end chunk" />
                 <end-sequenceof />
              </sequence>
           </choice>
        </sequenceof>
     </sequence>

     <common>
       <sequence name="unknown chunk">
          <field name="data length:" length="32" type="integer" />
          <field name="type" length="32" type="hex" />
          <field name="data" length="${data length:} * 8" type="hex" />
          <field name="crc" length="32" type="hex" />
       </sequence>

       <sequence name="end chunk">
          <field name="data length:" length="32" type="integer" />
          <field name="type" length="32" type="text" value="IEND" />
          <field name="data" length="${data length:} * 8" type="hex" />
          <field name="crc" length="32" type="hex" />
       </sequence>
     </common>
  </protocol>

Things to note:
   
 * We've added an 'end chunk' common entry
 * We've added a choice chunk, allowing a chunk to be either an 'unknown chunk'
   or an 'end chunk'.

Attempting to decode still has the out of data error! Wait; look at the choice;
the 'unknown chunk' is before the 'end chunk'! The 'unknown chunk' will always
be attempted first (and succeed), so the 'end chunk' is never attempted. We 
need to swap them around, like so::

          <choice name="chunk">
              <sequence name="end">
                 <reference name="end chunk" />
                 <end-sequenceof />
              </sequence>
              <reference name="unknown chunk" />
           </choice>

This causes the file to successfully decode!


Simplifying the specification using named references
----------------------------------------------------

In the specification so far, we have had to re-type the integer type several
times. While this isn't too difficult, having more text can make it harder to
read. We can use :ref:`references <format-reference>` to only specify these once::

  <protocol>
     ...skipping...

    <common>
       <field name="dword" type="integer" length="32" />

       <sequence name="unknown chunk">
          <reference name="data length:" type="dword" />
          <field name="type" length="32" type="hex" />

     ...skipping...

       <sequence name="end chunk">
          <reference name="data length:" type="dword" />
          <field name="type" length="32" type="text" value="IEND" />

Even in this simple case, it has made the code easier to read. In more
complicated situations, where complex encodings are used (eg: textual integers,
big endian integers, ...) it can make your specification far easier to
read and maintain.


Refining the specification
--------------------------

Of course, while we are successfully decoding the file, there are still many
sections in the file that have been left undecoded. Lets flesh some of them 
out. 


Header
......

The spec states that a png file must start with an IHDR chunk. This chunk 
includes information about image height, width, the encoding, etc. ::

  <sequence name="png">
    <field name="signature" length="64" type="hex" value="0x89504e470d0a1a0a" />
    <reference name="begin chunk" />
    <sequenceof name="chunks">
    ...

  <common>
    <sequence name="begin chunk">
      <field name="data length:" length="32" type="integer" />
      <field name="type" length="32" type="text" value="IHDR" />
      <sequence name="header" length="${data length:} * 8">
         <field name="width" length="32" type="integer" />
         <field name="height" length="32" type="integer" />
         <field name="bit depth" length="8" type="integer" />
         <choice name="colour type">
            <field name="greyscale" length="8" value="0x0" />
            <field name="rgb" length="8" value="0x2" />
            <field name="palette" length="8" value="0x3" />
            <field name="greyscale and alpha" length="8" value="0x4" />
            <field name="rgba" length="8" value="0x6" />
            <field name="unknown" length="8" />
         </choice>
         <choice name="compression method">
            <field name="deflate" length="8" value="0x0" />
            <field name="unknown" length="8" />
         </choice>
         <choice name="filter method">
            <field name="adaptive" length="8" value="0x0" />
            <field name="unknown" length="8" />
         </choice>
         <choice name="interlace method">
            <field name="none" length="8" value="0x0" />
            <field name="adam 7" length="8" value="0x1" />
            <field name="unknown" length="8" />
         </choice>
      </sequence>
      <field name="crc" length="32" type="hex" />
    </sequence>
    ...

Note that when decoding the header, we have used a choice of fields to 
represent an enumeration. Also note that we validate the data length of the
packet by setting a length on the header sequence (we could also have set an
expected value on the 'data length' field).


Image data
..........

Of course, the rest of the information isn't very useful without the image 
data. In the case of png, the image data is compressed. As the bdec 
specification is only concerned with representing the on disk structure,
decoding this data is beyond the scope of bdec (it is up to the code using bdec
to decode this data). That said, we can identify the image data chunk. ::

  ...
  <choice name="chunk">
    <reference name="image data" />
    <sequence name="end">
      <reference name="end chunk" />
      <end-sequenceof />
    </sequence>
    <reference name="unknown chunk" />
  </choice>
  ...

  <sequence name="image data">
     <field name="data length:" length="32" type="integer" />
     <field name="type" length="32" type="text" value="IDAT" />
     <field name="data" length="${data length:} * 8" type="hex" />
     <field name="crc" length="32" type="hex" />
  </sequence>

 
Text entries
............

Text entries are used to hold things such as author, description, comments, 
etc. The png specification defines the data as being in the format::

   Keyword:        1-79 bytes (character string)
   Null separator: 1 byte
   Text:           n bytes (character string)

This is a little difficult, as we have a variable length field whose length we
don't know. We can use the 'end-sequenceof' to detect the end of the keyword, 
and a variable length text string to read the value. eg::

  ...
  <sequenceof name="chunks">
    <choice name="chunk">
       <reference name="image data" />
       <reference name="text chunk" />
  ...
  <sequence name="text chunk">
     <field name="data length:" length="32" type="integer" />
     <field name="type" length="32" type="text" value="tEXt" />
     <sequenceof name="keyword">
        <choice name="char">
           <field name="null" length="8" value="0x0"><end-sequenceof /></field>
           <field name="character" length="8" type="text" />
        </choice>
     </sequenceof>
     <field name="value" type="text" length="${data length:} * 8 - len{keyword}" />
     <field name="crc" length="32" type="hex" />
  </sequence>

Note that we use the 'len{...}' entry to reference the length of another field
that has been decoded.


Using the specification
-----------------------

While the specification is interesting, and decoding to xml can be useful in
certain situations, native libraries are the preferred way of accessing the
decoded data. As such, bdec supports either :ref:`generating C language
decoders <compiling-to-c>` or using the specification from :ref:`within python
code <instance-decoder>`.


Where to go from here
---------------------

There are many other chunk types in the png specification; try decoding sRGB
(very easy) or PLTE (more difficult; use the 'length' attribute of a sequenceof).
Read the :ref:`tips <format-tips>` section for useful tips on improving your
specification.

One thing to realise is that the bdec specification will only take you so far;
except for trival file formats, code will still need to be written before you
have a fully functional decoder (for example, decompression). The important
fact is that this is exactly the non-trivial code that you have to think about;
all the drudgery of normal loading and validation is already taken care of. 

Offload as much possible into the specification, and it will make your code
easier to read, and future maintenance much more pleasant.

Have fun!

