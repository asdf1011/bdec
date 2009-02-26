## vim:set syntax=mako:
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

#include <stdio.h>
#include <stdlib.h>

#include "${protocol.name |filename}.h"

void usage(char* program)
{
    fprintf(stderr, "Usage:\n");
    fprintf(stderr, "\t%s <binary file>\n", program);
}

int main(int argc, char* argv[])
{
    if (argc != 2)
    {
        /* Bad number of arguments */
        fprintf(stderr, "Bad number of arguments!\n");
        usage(argv[0]);
        return 1;
    }
    char* filename = argv[1];
    FILE* datafile = fopen(filename, "rb");
    if (datafile == 0)
    {
        /* Failed to open file */
        fprintf(stderr, "Failed to open file!\n");
        return 2;
    }
    fseek(datafile, 0, SEEK_END);
    long int length = ftell(datafile);
    fseek(datafile, 0, SEEK_SET);

    /* Load the data file into memory */
    unsigned char* data = (unsigned char*)malloc(length);
    fread(data, length, 1, datafile);
    fclose(datafile);

    /* Attempt to decode the file */
    BitBuffer buffer = {data, 0, length * 8};
  %if contains_data(protocol):
    ${settings.ctype(protocol)} result;
    if (!${settings.decode_name(protocol)}(&buffer, &result))
  %else:
    if (!${settings.decode_name(protocol)}(&buffer))
  %endif
    {
        /* Decode failed! */
        fprintf(stderr, "Decode failed!\n");
        free(data);
        return 3;
    }

    /* Print the decoded data */
  %if contains_data(protocol):
    ${settings.print_name(protocol)}(&result, 0, "${protocol.name | xmlname}");
    ${settings.free_name(protocol)}(&result);
  %else:
    ${settings.print_name(protocol)}(0, "${protocol.name | xmlname}");
  %endif:
    free(data);
    return 0;
}

