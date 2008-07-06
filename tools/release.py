#!/usr/bin/env python

""" A script for automatically preparing a new release """

import datetime
import os.path
import re
import shutil
import sys

root_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')
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
website_dir = os.path.join(root_path, '..', 'website', 'website.integ')

def _read_changelog():
    readme = file(_README, 'r')
    contents = readme.read()
    readme.close()

def get_changelog(contents=_read_changelog()):
    "Returns the a (offset, version, changelog) tuple"

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
        sys.exit("Previous version from README (%s) doesn't match bdec (%s)! Have you updated the README?" % (previous_version, bdec.__version__))

    # Get the changelog, and strip off any leading whitespace
    changelog = contents[changelog_offset:changelog_offset + match.start()]
    for line in changelog.splitlines():
        if line.strip():
            for i, char in enumerate(line):
                if char != ' ':
                    break
            break
    changelog = ''.join(line[i:] for line in changelog.splitlines(True)).strip()


    return (changelog_offset, version, changelog)

def get_focus():
    for id, text in _RELEASE_FOCUS.iteritems():
        print id, text
    default = [7]
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

def update_website():
    website_build = os.path.join(website_dir, 'build')
    rst2doc = os.path.join(website_build, 'rst2doc.py')
    project_dir = os.path.join(website_dir, 'html', 'projects', 'bdec')
    print 'Updating project index...'
    os.chdir(project_dir)
    command = "%s %s" % (rst2doc, _README)
    if os.system(command) != 0:
        sys.exit('Failed to update project html index!')

    print 'Updating project documentation...'
    html_doc_dir = os.path.join(project_dir, 'docs')
    os.chdir(os.path.join(root_path, 'docs'))
    command = 'PYTHONPATH=%s sphinx-build -a source tempdir' % (root_path) 
    if not os.path.exists('tempdir'):
        os.mkdir('tempdir')
    if os.system(command) != 0:
        sys.exit('Failed to update project html documentation!')
    if os.path.exists(html_doc_dir):
        shutil.rmtree(html_doc_dir)
    os.rename('tempdir', html_doc_dir)
    if os.system('bzr add "%s"' % html_doc_dir) != 0:
        sys.exit('Failed to add the updated html_doc_dir')

def commit_changes(version):
    # Commit the bdec changes
    os.chdir(root_path)
    if os.system('bzr commit -m "Updated version to %s"' % version) != 0:
        sys.exit('Failed to commit!')
    if os.system('bzr tag "bdec %s"' % version) != 0:
        sys.exit('Failed to tag!')

    # Commit the website changes
    os.chdir(website_dir)
    if os.system('bzr commit -m "Updated bdec project to version %s"' % version) != 0:
        sys.exit('Failed to commit!')

def notify(version, changelog, focus):
    # Notify freshmeat
    freshmeat = os.path.join(website_dir, 'build', 'freshmeat-submit')
    command = "%s -n --project bdec --version %s --changes %s  --release-focus %s --gzipped-tar-url http://www.hl.id.au/projects/bdec/files/bdec-%s.tar.gz" % (freshmeat, version, focus, version)
    if os.system(command) != 0:
        sys.exit('Failed to submit to freshmeat! (%s)' % command)

    # Notify the python package index
    os.chdir(root_path)
    command = "setup.py register"
    if os.system(command) != 0:
        sys.exit('Failed to update python package index!')

def upload():
    print "Uploading to the server..."
    command = "%s ftp://ftp.hl.id.au/" % os.path.join(website_dir, 'upload')
    if os.system(command) != 0:
        sys.exit('Failed to upload to the server!')

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
    update_website()
    os.chdir(root_path)
    os.system('bzr diff | less')
    os.chdir(website_dir)
    os.system('bzr diff | less')

    text = raw_input('Commit changes and tag release? [y]')
    if text and text != 'y':
        sys.exit('Not committed.')

    commit_changes(version)
    upload()
    notify(version, changelog, focus)

