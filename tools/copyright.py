#!/bin/bash

# A simple bash script to update the copyright year of the source code by
# inspecting the git history
YEAR=`date +%Y`
git log --stat --since=$YEAR-01-01 --until=$(( $YEAR + 1 )) | grep '|' | \
    while read filename pipe count blah; do
        if [ $count != Bin ] && [ $count -gt 2 ]; then
            echo $filename;
        fi;done |
     sort -u |
    while read filename; do
        if test -e $filename && grep -q 'Copyright.*Henry Ludemann' $filename; then
            sed -i "s/[0-9][0-9]* Henry Ludemann/$YEAR Henry Ludemann/" $filename;
        fi;
    done
