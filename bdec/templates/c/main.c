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

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "${protocol.name |filename}.h"

static void usage(char* program)
{
    printf("Usage: %s [options] <filename>\n", program);
    printf("Decode the ${protocol.name} file to xml.\n");
    printf("Options:\n");
%if generate_encoder:
    printf("   -e <filename>   Re-encode the decoded file, and save it to the given file.\n");
%endif
    printf("   -h    Display this help.\n");
}

int main(int argc, char* argv[])
{
    int i;
%if generate_encoder:
    char* encodeFilename = 0;
%endif
    for (i = 1; i < argc; ++i)
    {
        if (argv[i][0] == '-')
        {
            if (argv[i][1] == 'h')
            {
                usage(argv[0]);
                return 0;
            }
%if generate_encoder:
            else if (argv[i][1] == 'e')
            {
                if (i + 1 == argc || argv[i+1][0] == '-')
                {
                    fprintf(stderr, "Missing encode filename for option -e!\n");
                    return 1;
                }
                ++i;
                encodeFilename = argv[i];
            }
%endif
            else
            {
                fprintf(stderr, "Unknown option '%s'! See %s -h for more details.\n",
                        argv[i], argv[0]);
                return 1;
            }
        }
        else
        {
            // We've found the first argument
            break;
        }
    }

    if (i != argc - 1)
    {
        /* Bad number of arguments */
        fprintf(stderr, "Missing single filename to decode!\nRun %s -h for more details.\n", argv[0]);
        usage(argv[0]);
        return 1;
    }
    char* filename = argv[i];
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
  %else:
    ${settings.print_name(protocol)}(0, "${protocol.name | xmlname}");
  %endif:

  %if generate_encoder:
    if (encodeFilename != 0)
    {
        struct EncodedData encodedData = {0};
      %if contains_data(protocol):
        if (!${settings.encode_name(protocol)}(&result, &encodedData))
      %else:
        if (!${settings.encode_name(protocol)}(&encodedData))
      %endif
        {
            fprintf(stderr, "Failed to encode data!\n");
          %if contains_data(protocol):
            ${settings.free_name(protocol)}(&result);
          %endif
            free(data);
            return 4;
        }
        FILE* output = fopen(encodeFilename, "wb");
        if (!output)
        {
            fprintf(stderr, "Failed to open '%s'; %s\n", encodeFilename, strerror(errno));
          %if contains_data(protocol):
            ${settings.free_name(protocol)}(&result);
          %endif
            free(data);
            return 5;
        }
        fwrite(encodedData.buffer, (encodedData.num_bits + 7) / 8, 1, output);
        fclose(output);
        free(encodedData.buffer);
    }
  %endif
  %if contains_data(protocol):
    ${settings.free_name(protocol)}(&result);
  %endif
    free(data);
    return 0;
}

