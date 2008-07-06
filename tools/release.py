#!/usr/bin/env python

""" A script for automatically preparing a new release """

import os.path
import sys

root_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(root_path)

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
    text = raw_input('What is the new revision? [%s] ' % version_text)
    if not text:
        text = version_text
    return text

def get_focus():
    for id, text in _RELEASE_FOCUS.iteritems():
        print id, text
    default = [4,6]
    focus = raw_input('What is the release focus? %s ' % default)
    if focus:
        items = [int(text.strip()) for text in focus.split(',')]
    else:
        items = default
    return items

def update_bdec_version(version):
    filename = os.path.join(root_path, 'bdec', '__init__.py')
    init_file = file(filename, 'r')
    contents = init_file.read()
    init_file.close()

    init_file = file(filename, 'w')
    found_version = False
    for line in contents.splitlines(True):
        if line.startswith('__version__'):
            init_file.write('__version__ = "%s"\n' % version)
            found_version = True
        else:
            init_file.write(line)
    init_file.close()
    if not found_version:
        sys.exit('Failed to update version text in %s!' % filename)

if __name__ == '__main__':
    version = get_version()
    focus = get_focus()

    print 'Creating new version %s with focus %s' % (version, ", ".join(_RELEASE_FOCUS[i] for i in focus))
    update_bdec_version(version)

