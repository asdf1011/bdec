/*  Copyright (C) 2008 Henry Ludemann

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
    int length;
}Buffer;

#endif
