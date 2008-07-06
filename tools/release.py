#!/usr/bin/env python

""" A script for automatically preparing a new release """

import datetime
import os.path
import re
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

_README = filename = os.path.join(root_path, 'README')

def get_changelog():
    "Returns the a (offset, version, changelog) tuple"
    readme = file(_README, 'r')
    contents = readme.read()
    readme.close()

    match = re.search('^Download', contents, re.M)
    if match is None:
        sys.exit('Failed to find download section in %s!' % filename)
    download_offset = match.end()

    # Get the current version
    version_regex = '^\* `Version (.*)`_$'
    match = re.search(version_regex, contents[download_offset:], re.M)
    if match is None:
        sys.exit('Failed to find version section')
    version = match.group(1)
    changelog_offset = download_offset + match.end()

    # Get the previous version
    match = re.search(version_regex, contents[changelog_offset:], re.M)
    if match is None:
        sys.exit('Failed to find previous version')
    previous_version = match.group(1)
    if previous_version != bdec.__version__:
        sys.exit("Previous version from README (%s) doesn't match bdec (%s)!" % (previous_version, bdec.__version__))

    # Get the changelog
    changelog = contents[changelog_offset:changelog_offset + match.start()]

    return (changelog_offset, version, changelog)

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

def insert_date_into_changelog(changelog_offset):
    readme = file(_README, 'r')
    contents = readme.read() 
    readme.close()

    readme = file(_README, 'w')
    readme.write(contents[:changelog_offset])
    readme.write("\n  %s\n" % (datetime.datetime.now().date()))
    readme.write(contents[changelog_offset:])
    readme.close()


if __name__ == '__main__':
    offset, version, changelog = get_changelog()
    print "Next version will be", version
    print "Changes are;"
    print changelog
    focus = get_focus()

    text = raw_input('Make new version %s with focus %s? [y]' % (version, ", ".join(_RELEASE_FOCUS[i] for i in focus)))
    if text and text != 'y':
        sys.exit('Not making new version.')

    update_bdec_version(version)
    insert_date_into_changelog(offset)
    os.system('bzr diff')

    text = raw_input('Commit changes and tag release? [y]')
    if text and text != 'y':
        sys.exit('Not committed.')
    os.system('bzr commit -m "Updated version to %s"' % version)
    os.system('bzr tag "bdec %s"' % version)

