
/*  Copyright (C) 2009 Henry Ludemann

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

#include <assert.h>

#include "buffer.h"
#include "variable_integer.h"

union FloatConversion
{
    unsigned char buffer[8];
    float floatValue;
    double doubleValue;
};

enum Encoding getMachineEncoding()
{
    union {
        long int l;
        unsigned char c[sizeof (long int)];
    } u;
    u.l = 1;

    // Derived from http://stackoverflow.com/questions/280162/is-there-a-way-to-do-a-c-style-compile-time-assertion-to-determine-machines-en
    return u.c[0] == 1 ? BDEC_LITTLE_ENDIAN : BDEC_BIG_ENDIAN;
}

static void convertEndian(enum Encoding encoding, unsigned char output[], BitBuffer* data)
{
    int numBytes = data->num_bits / 8;
    if (encoding == getMachineEncoding())
    {
        int i;
        for (i = 0; i < numBytes; ++i)
        {
            output[i] = decode_integer(data, 8);
        }
    }
    else
    {
        int i;
        for (i = 0; i < numBytes; ++i)
        {
            output[numBytes - 1 - i] = decode_integer(data, 8);
        }
    }
}

double decodeFloat(BitBuffer* data, enum Encoding encoding)
{
    assert(data->num_bits == 32);
    union FloatConversion conv;
    convertEndian(encoding, conv.buffer, data);
    return conv.floatValue;
}

double decodeDouble(BitBuffer* data, enum Encoding encoding)
{
    assert(data->num_bits == 64);
    union FloatConversion conv;
    convertEndian(encoding, conv.buffer, data);
    return conv.doubleValue;
}

