#!/bin/bash

# A simple bash script to update the copyright year of the source code by
# inspecting the git history
#YEAR=`date +%Y`
git ls-files | while read filename; do
echo $filename
    if grep -q 'Copyright.*Henry Ludemann' $filename; then
        YEAR=`git log --not --grep 'Update copyright dates' -1 --format=%cD $filename | awk '{print $4}'`
        if ! grep -q "Copyright.*$YEAR Henry Ludemann" $filename; then
            sed -i "s/\(Copyright.* \)\([0-9]*\)-*[0-9]* Henry Ludemann/\1\2-$YEAR Henry Ludemann/" $filename;
        fi
    fi
done
