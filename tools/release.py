#!/usr/bin/env python

""" A script for automatically preparing a new release """

import datetime
import getpass
import os.path
import re
import shutil
import smtplib
import sys

root_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')
sys.path.append(root_path)

import bdec

def usage():
    print "A script to simplify deploying new releases."
    print
    print "Usage: %s" % sys.argv[0]
    print
    print "This script will;"
    print " 1. Check that all source files have copyright statements."
    print " 2. Get the changelog from the README."
    print " 3. If the changelog version matches the bdec version, will prompt "
    print "    to update the website documentation."
    print " 4. If the changelog version doesn't match the bdec version, it will;"
    print "    a) Update the bdec/__init__.py version."
    print "    b) Insert today's date into the README changelog."
    print "    c) Update the website bdec documentation."
    print "    d) Create a new tarball in the website 'files' folder."
    print "    e) Prompt if the user wants to upload and notify others of this"
    print "       release. If so, all changes will be automatically committed,"
    print "       the website will have the changes uploaded, and a new tag will"
    print "       be created in source control."
    print "    f) Prompt if user wants freshmeat & pypi to be notified. If so,"
    print "       README changlog will be used."

_RELEASE_FOCUS = {
        2: 'Documentation',
        3: 'Code cleanup',
        4: 'Minor feature enhancements',
        5: 'Major feature enhancements',
        6: 'Minor bugfixes', 
        7: 'Major bugfixes', 
        }

_README = filename = os.path.join(root_path, 'README')
website_dir = os.path.join(root_path, '..', 'website', 'website.integ')
project_dir = os.path.join(website_dir, 'html', 'projects', 'bdec')

def _check_copyright_statements(subdirs):
    is_missing_copyright = False
    for subdir in subdirs:
        for dir, subdirs, filenames in os.walk(os.path.join(root_path, subdir)):
            for filename in filenames:
                filename = os.path.join(dir, filename)
                if os.path.splitext(filename)[1] in ('.py', '.c', '.h'):
                    data = open(filename, 'r')
                    for i, line in enumerate(data):
                        if 'Copyright' in line:
                            break
                    else:
                        print "'%s' doesn't include copyright information!" % filename
                        is_missing_copyright = True
    if is_missing_copyright:
        sys.exit('Copyright issues must be resolved.')

def _read_changelog():
    readme = file(_README, 'r')
    contents = readme.read()
    readme.close()
    return contents

def get_changelog(contents=_read_changelog()):
    "Returns the a (offset, version, prevous_version, changelog) tuple"

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

    # Get the changelog, and strip off any trailing and leading whitespace.
    # Look at some the freshmeat main page to get examples of how the layout
    # should look (basically free flowing text).
    changelog = contents[changelog_offset:changelog_offset + match.start()]
    lines = []
    for line in changelog.splitlines():
        line = line.strip()
        while line.startswith('*'):
            line = line[1:].strip()
        if line:
            lines.append(line)
    changelog = " ".join(lines)
    return (changelog_offset, version, previous_version, changelog)

def get_focus():
    print 'Focus options are:'
    for id, text in _RELEASE_FOCUS.iteritems():
        print id, text
    default = 7
    focus = raw_input('What is the release focus? [%s] ' % default)
    if focus:
        item = int(focus.strip())
    else:
        item = default
    return _RELEASE_FOCUS[item]

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
    shutil.copytree("files", "tempdir/files")
    if os.path.exists(html_doc_dir):
        shutil.rmtree(html_doc_dir)
    os.rename('tempdir', html_doc_dir)
    if os.system('bzr add "%s"' % html_doc_dir) != 0:
        sys.exit('Failed to add the updated html_doc_dir')

def update_release(version):
    os.chdir(root_path)
    destination = os.path.join(project_dir, 'files', 'bdec-%s.tar.gz' % version)
    command = 'git archive --format=tar --prefix=bdec-%s/ HEAD | gzip > %s' % (version, destination)
    if os.system(command) != 0:
        sys.exit('Failed to export new tar.gz!')
    os.chdir(project_dir)
    if os.system('bzr add %s' % destination) != 0:
        sys.exit('Failed to add new tar.gz!')

def tag_changes(version):
    if os.system('git tag "bdec-%s"' % version) != 0:
        sys.exit('Failed to tag!')

def commit_bdec(version):
    # Commit the bdec changes
    os.chdir(root_path)
    if os.system('git commit -a --edit -m "Updated version to %s"' % version) != 0:
        sys.exit('Failed to commit!')

def commit_website(version):
    os.chdir(website_dir)
    if os.system('bzr diff | less') != 0:
        sys.exit('Stopped after reviewing changes.')
    text = raw_input('Commit website changes? [y]')
    if text and text != 'y':
        sys.exit('Not committed.')

    # Commit the website changes
    os.chdir(website_dir)
    data = file('.commitmsg', 'w')
    data.write('Updated bdec project to version %s' % version)
    data.close()
    if os.system('vi .commitmsg') != 0:
        sys.exit('Stopping due to edit commit message failure')
    if os.system('bzr commit -F .commitmsg') != 0:
        sys.exit('Failed to commit!')
    os.remove('.commitmsg')

def send_email(version, changelog):
    to_addr = 'bdec-project@yahoogroups.com'

    data = open('.emailmsg', 'w')
    data.write('To: %s\r\n' % to_addr)
    data.write('From: Henry Ludemann <lists@hl.id.au>\r\n')
    data.write('Reply-To: Henry Ludemann <lists@hl.id.au>\r\n')
    data.write('Subject: Bdec %s released\r\n' % version)
    data.write('\r\n')
    data.write('Version %s of the bdec decoder has been released. The changes in this version are;\r\n\r\n' % version)
    data.write(changelog)
    data.write('\r\n\r\nDownload: http://www.hl.id.au/projects/bdec/#download')
    data.close()
    if os.system('vi .emailmsg') != 0:
        sys.exit('Stopping due to edit email message failure')
    message = open('.emailmsg', 'r').read()
    os.remove('.emailmsg')

    while 1:
        try:
            user = raw_input('Enter gmail username:')
            password = getpass.getpass()

            print 'Sending email...'
            smtp = smtplib.SMTP('smtp.gmail.com', 587)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(user, password)
            smtp.sendmail('lists@hl.id.au', to_addr, message)
            smtp.quit()
            break
        except SMTPAuthenticationError, ex:
            print 'Authenticion error!', ex

def notify(version, changelog, get_focus=get_focus,  system=os.system, confirm=raw_input):
    # Notify freshmeat
    if confirm('Should freshmeat be notified? [y]') in ['', 'y', 'Y']:
        focus = get_focus()
        freshmeat = os.path.join(website_dir, 'build', 'freshmeat-submit-1.6', 'freshmeat-submit')
        command = '%s -n --project bdec --version %s --changes "%s" --release-focus "%s" --gzipped-tar-url http://www.hl.id.au/projects/bdec/files/bdec-%s.tar.gz' % (freshmeat, version, changelog, focus, version)
        if system(command) != 0:
            sys.exit('Failed to submit to freshmeat! (%s)' % command)
    else:
        print 'Not notifying freshmeat.'

    # Notify the python package index
    if confirm('Should pypi be notified? [y]') in ['', 'y', 'Y']:
        os.chdir(root_path)
        command = "./setup.py register"
        if system(command) != 0:
            sys.exit('Failed to update python package index!')
    else:
        print 'Not notifying pypi.'

    send_email(version, changelog)

def upload():
    print "Uploading to the server..."
    while 1:
        os.chdir(website_dir)
        command = "./upload ftp://ftp.hl.id.au"
        if os.system(command) == 0:
            break
        text = raw_input('Failed to upload to the server! Try again? [y]')
        if text and text != 'y':
            sys.exit('Not uploaded.')

if __name__ == '__main__':
    if len(sys.argv) != 1:
        usage()
        sys.exit(1)

    _check_copyright_statements(['bdec', 'templates'])
    offset, version, previous_version, changelog = get_changelog()

    if version != bdec.__version__:
        if previous_version != bdec.__version__:
            sys.exit("Neither the documented current version (%s) nor the previous version (%s) match the actual version (%s)!" % (version, previous_version, bdec.__version__))
        print "Next version will be", version
        print "Changes are;"
        print changelog
        print

        update_bdec_version(version)
        insert_date_into_changelog(offset)
        update_website()
        update_release(version)

        os.chdir(root_path)
        if os.system('git diff') != 0:
            sys.exit('Stopped after reviewing changes.')

        text = raw_input('Commit changes and tag release? [y]')
        if text and text != 'y':
            sys.exit('Not committed.')

        commit_bdec(version)
        tag_changes(version)
        commit_website(version)
        upload()
        notify(version, changelog)
    else:
        print "The version hasn't changed, so only updating documentation and uploading..."
        update_website()
        commit_website(version)
        upload()

