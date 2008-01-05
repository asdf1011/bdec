<%namespace file="/type.tmpl" name="ctype" />

#include <stdio.h>
#include <stdlib.h>

#include "${protocol.name |filename}.h"

int main(int argc, char* argv[])
{
    if (argc != 2)
    {
        /* Bad number of arguments */
        return 1;
    }
    char* filename = argv[1];
    FILE* datafile = fopen(filename, "rb");
    if (datafile == 0)
    {
        /* Failed to open file */
        return 2;
    }
    fseek(datafile, 0, SEEK_END);
    long int length = ftell(datafile);
    fseek(datafile, 0, SEEK_SET);

    /* Load the data file into memory */
    unsigned char* data = malloc(length);
    fread(data, length, length, datafile);
    fclose(datafile);

    /* Attempt to decode the file */
    BitBuffer buffer = {data, 0, length * 8};
    ${ctype.ctype(protocol)} result;
    if (!${ctype.decode_name(protocol)}(&buffer, &result))
    {
        /* Decode failed! */
        return 3;
    }

    /* Print the decoded data */
    ${ctype.print_name(protocol)}(&result, 0);

    return 0;
}

