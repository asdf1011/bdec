/*  Copyright (C) 2010 Henry Ludemann

    This file is part of the bdec decoder library.

    The bdec decoder library is free software; you can redistribute it
    and/or modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    The bdec decoder library is distributed in the hope that it will be
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty
    of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, see
    <http://www.gnu.org/licenses/>. */

#ifndef BIT_BUFFER_HEADER_FILE
#define BIT_BUFFER_HEADER_FILE

#ifdef __cplusplus
extern "C" {
#endif

// Structure to hold data to be decoded
typedef struct 
{
    unsigned char* buffer;
    // The start bit is the offset in buffer to start decoding at. It should
    // be in the range [0,8).
    unsigned int start_bit;
    unsigned int num_bits;
}BitBuffer;

// Structure to hold bit aligned data to be decoded.
typedef struct
{
    unsigned char* buffer;
    unsigned int length;
}Buffer;

typedef struct
{
    char* buffer;
    unsigned int length;
}Text;

enum Encoding
{
    BDEC_BIG_ENDIAN,
    BDEC_LITTLE_ENDIAN
};

struct EncodedData
{
    char* buffer;
    int num_bits;
    int allocated_length_bytes;
};
/**
 * Ensure there is appropriate space in the encode buffer.
 */
void ensureEncodeSpace(struct EncodedData* buffer, int numBits);
/**
 * Append a BitBuffer to an EncodedData.
 */
void appendBitBuffer(struct EncodedData* result, BitBuffer* data);
void appendText(struct EncodedData* result, Text* value);
void appendBuffer(struct EncodedData* result, Buffer* value);
void appendEncodedBuffer(struct EncodedData* result, struct EncodedData* value);

/**
 * Decode a data buffer to a float.
 *
 * data -- The buffer to decode. The data _MUST_ be 4 bytes long,
 *   or the code will assert.
 */
double decodeFloat(BitBuffer* data, enum Encoding encoding);
void appendFloat(float value, enum Encoding encoding, struct EncodedData* output);

/**
 * Decode a data buffer to a float.
 *
 * data -- The buffer to decode. The data _MUST_ be 8 bytes long,
 *   or the code will assert.
 */
double decodeDouble(BitBuffer* data, enum Encoding encoding);
void appendDouble(double value, enum Encoding encoding, struct EncodedData* output);

#ifdef __cplusplus
}
#endif

#endif

