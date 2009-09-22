/*
 * Copyright (C) 2008 Henry Ludemann
 *
 * License: GNU Lesser General Public License.
 */
#include <stdio.h>
#include <stdlib.h>

#include "png.h"
#include "textchunk.h"

int main(int argc, char* argv[])
{
    if (argc != 2)
    {
        fprintf(stderr, "Usage: %s <png filename>\n", argv[0]);
        return 1;
    }
    FILE* datafile = fopen(argv[1], "rb");
    if (datafile == 0)
    {
        fprintf(stderr, "Failed to open '%s'!\n", argv[1]);
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
    struct Png result;
    if (!decodePng(&buffer, &result))
    {
        fprintf(stderr, "Decode failed!\n");
        free(data);
        return 3;
    }

    /* Print the decoded data */
    printf("Image width = %i\n", result.beginChunk.header.width);
    printf("Image height = %i\n", result.beginChunk.header.height);

    /* Find all text chunks, and print them. */
    unsigned int i, j;
    for (i = 0; i < result.chunks.count; ++i)
    {
        if (result.chunks.items[i].option == TEXT_CHUNK)
        {
            struct TextChunk* text = &result.chunks.items[i].value.textChunk;

            // Print the 'name' of this chunk.
            for (j = 0; j < text->keyword.count; ++j)
            {
                if (text->keyword.items[j].option == CHARACTER)
                {
                    printf("%c", text->keyword.items[j].value.character.buffer[0]);
                }
            }
            printf(" = ");
            for (j = 0; j < text->value_.length; ++j)
            {
                printf("%c", text->value_.buffer[j]);
            }
            printf("\n");
        }
    }
    freePng(&result);
    free(data);
    return 0;
}

