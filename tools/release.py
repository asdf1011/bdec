#!/usr/bin/env python

""" A script for automatically preparing a new release """

import os.path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import bdec

_RELEASE_FOCUS = {
        2: 'Documentation',
        3: 'Code cleanup',
        4: 'Minor feature enhancements',
        5: 'Major feature enhancement',
        6: 'Minor bugfixes', 
        7: 'Major bugfixes', 
        }

def get_version():
    version = [int(number) for number in bdec.__version__.split('.')]
    version[-1] += 1
    version_text = '.'.join(str(number) for number in version)
    text = raw_input('What is the new revision? [%s]' % version_text)
    if not text:
        text = version_text
    return text

def get_focus():
    for id, text in _RELEASE_FOCUS.iteritems():
        print id, text
    default = [4,6]
    focus = raw_input('What is the release focus? %s' % default)
    if focus:
        items = [int(text.strip()) for text in focus.split(',')]
    else:
        items = default
    return items

if __name__ == '__main__':
    version = get_version()
    focus = get_focus()
    print 'Creating new version %s with focus %s' % (version, ", ".join(_RELEASE_FOCUS[i] for i in focus))

