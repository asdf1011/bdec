#!/usr/bin/env python

""" A script for automatically preparing a new release """

import datetime
import getpass
import httplib
import json
import os.path
import re
import shutil
import smtplib
import subprocess
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

_README = os.path.join(root_path, 'README')
_CHANGELOG = os.path.join(root_path, 'CHANGELOG')

website_dir = os.path.join(root_path, '..', 'website', 'website.integ')
project_dir = os.path.join(root_path, '..', 'protocollogic', 'protocollogic.com', 'html')
freshmeat_pass = os.path.join(website_dir, 'freshmeat.txt')

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
    readme = file(_CHANGELOG, 'r')
    contents = readme.read()
    readme.close()
    return contents

def get_changelog(contents=_read_changelog()):
    "Returns a list of (version, date, notes) tuple"

    result = []
    version_regex = r'^([0-9.]*) \((.*)\)$'
    while contents:
        match = re.search(version_regex, contents, re.M)
        if match is None:
            break

        version = match.group(1)
        date = match.group(2)
        changelog_offset = match.end()

        match = re.search(version_regex, contents[changelog_offset:], re.M)
        if match:
            notes = contents[changelog_offset:changelog_offset + match.start()]
            contents = contents[changelog_offset + match.start():]
        else:
            notes = contents[changelog_offset:]
            contents = ""

        lines = notes.strip().splitlines()
        if set(lines[0]) != set('-') or lines[1].strip():
            sys.exit("The changelog section should be followed by a '---' line, got '%s'" % lines)
        notes = '\n'.join(lines[2:])
        result.append((version, date, notes))
    if not result:
        sys.exit('Failed to find version')
    return result

def shorten_changelog(changelog):
    """Make the changelog into a single paragraph suitable for freshmeat."""
    # Get the changelog, and strip off any trailing and leading whitespace.
    # Look at some the freshmeat main page to get examples of how the layout
    # should look (basically free flowing text).
    lines = []
    for line in changelog.splitlines():
        line = line.strip()
        while line.startswith('*'):
            line = line[1:].strip()
        if line:
            lines.append(line)
    return " ".join(lines)

def _get_link(version):
    return 'files/bdec-%s.tar.gz' % version

def _generate_html(contents):
    website_build = os.path.join(website_dir, 'build')
    rst2doc = os.path.join(website_build, 'rst2doc.py')

    generated_readme = os.path.join(root_path, 'readme.tmp')
    data = open(generated_readme, 'w')
    data.write(contents)
    data.close()
    command = "%s -t -m media %s" % (rst2doc, generated_readme)
    if os.system(command) != 0:
        sys.exit('Failed to update project html index!')
    os.remove(generated_readme)

def _create_changelog_html():
    # 1. Get all change log entries;
    # 2. Modify each of the headers to include the links to the downloads
    # 3. Convert them to a list starting with ' * '
    contents = ""
    links = ""
    for version, date, notes in get_changelog():
        contents += '\n* `Version %s`_ (%s)\n\n' % (version, date)
        contents += '\n'.join('  %s' % line for line in notes.splitlines())
        contents += '\n'
        links += '.. _Version %s: files/bdec-%s.tar.gz\n' % (version, version)
    contents += '\n\n%s' % links

    _generate_html(contents)
    os.rename('index.html', 'changelog.html')

def _create_index_file():
    # Create a temporary file that contains a modified readme
    version, date, notes = get_changelog()[0]
    notes = '\n  '.join(notes.splitlines())
    contents = open(_README, 'r').read()
    match = re.search('(.*)(See the CHANGELOG.*)', contents)
    if not match:
        sys.exit('Failed to find changelog section of readme!')

    # Update the index from the README
    contents = contents[:match.start(1)] + \
        '\n* `Version %s`_ (%s)\n\n  %s\n\n' % (version, date, notes) + \
        '.. _Version %s: %s\n\n' % (version, _get_link(version)) + \
        contents[match.start(1):]
    _generate_html(contents)

def update_website():
    print 'Updating project index...'
    os.chdir(project_dir)

    _create_changelog_html()
    _create_index_file()

    # Update the CHANGELOG

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

    if os.system('git add .;git add -u .') != 0:
        sys.exit('Failed to add the updated html_doc_dir')

def update_release_tarball(version):
    os.chdir(root_path)
    destination = os.path.join(project_dir, 'files', 'bdec-%s.tar.gz' % version)
    if os.path.exists(destination):
        text = raw_input("Archive '%s' exists! Overwrite? [y]" % destination)
        if text and text != 'y':
            print 'Not updated archiving...'
            return

    command = 'git archive --format=tar --prefix=bdec-%s/ HEAD | gzip > %s' % (version, destination)
    if os.system(command) != 0:
        sys.exit('Failed to export new tar.gz!')
    os.chdir(project_dir)
    if os.system('bzr add %s' % destination) != 0:
        sys.exit('Failed to add new tar.gz!')

def tag_changes(version):
    os.chdir(root_path)
    tag = 'bdec-%s' % version

    git = subprocess.Popen(['git', 'tag'], stdout=subprocess.PIPE)
    tags = git.stdout.read().splitlines()
    if git.wait() != 0:
        sys.exit('Failed to read git tags!')
    if tag not in tags:
        text = raw_input("Create new tag '%s'? [y]" % tag)
    else:
        text = raw_input("Tag '%s' exists! Overwrite? [y]" % tag)

    if text.strip() and text != 'y':
        print 'Not tagged.'
    elif os.system('git tag -f "%s"' % tag) != 0:
        sys.exit('Failed to tag!')

def _edit_message(message):
    filename = 'message.edit'
    data = file(filename, 'w')
    data.write(message)
    data.close()

    if os.system('vi %s' % filename) != 0:
        sys.exit('Stopping due to edit message failure!')

    data = file(filename, 'r')
    message = data.read()
    data.close()
    os.remove(filename)
    return message

def commit_website(version):
    os.chdir(project_dir)
    if os.system('git diff') != 0:
        sys.exit('Stopped after reviewing changes.')
    text = raw_input('Commit website changes? [y]')
    if text and text != 'y':
        print 'Not committed.'
        return False

    # Commit the website changes
    message = _edit_message('Updated bdec project to version %s' % version)
    data = file('.commitmsg', 'w')
    data.write(message)
    data.close()
    if os.system('git commit --template .commitmsg') != 0:
        sys.exit('Failed to commit!')
    os.remove('.commitmsg')
    return True

def send_email(version, changelog):
    # Emails display much more consistently when we use 'windows' newlines.
    changelog = "\r\n".join(changelog.splitlines())
    to_addr = 'bdec-project@yahoogroups.com'

    data = open('.emailmsg', 'w')
    data.write('To: %s\r\n' % to_addr)
    data.write('From: Henry Ludemann <henry@protocollogic.com>\r\n')
    data.write('Subject: Bdec %s released\r\n' % version)
    data.write('\r\n')
    data.write('Version %s of the bdec decoder has been released. The changes in this version are;\r\n\r\n' % version)
    data.write(changelog)
    data.write('\r\n\r\nDownload: http://www.protocollogic.com/#download')
    data.close()
    if os.system('vi .emailmsg') != 0:
        sys.exit('Stopping due to edit email message failure')
    message = open('.emailmsg', 'r').read()
    os.remove('.emailmsg')

    try:
        user = raw_input('Enter gmail username:')
        password = getpass.getpass()

        print 'Sending email...'
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(user, password)
        smtp.sendmail('henry@protocollogic.com', to_addr, message)
        smtp.quit()
    except smtplib.SMTPAuthenticationError, ex:
        print 'Authenticion error!', ex

def _get_freshmeat_auth_code():
    if os.path.exists(freshmeat_pass):
        print 'Reading freshmeat credentials from', freshmeat_pass
        data = file(freshmeat_pass, 'r')
        result = data.read()
        data.close()
    else:
        result = raw_input('Enter freshmeat auth token (from user page):')
        data = file(freshmeat_pass, 'w')
        data.write(result)
        data.close()
    result = result.strip()
    if not result:
        sys.exit('Failed to read freshmeat auth code!')
    return result

def _get_tags(connection, freshmeat_auth):
    "Get a comma separate list of freshmeat tags"
    # First get the available tags
    release = {
            'auth_code': freshmeat_auth(),
            }
    headers = {"Content-type": "application/json"}
    conn = connection("freshmeat.net")
    conn.request("GET", "/projects/bdec/releases.json", json.dumps(release), headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    if response.status >= 400:
        print response.status, response.reason
        sys.exit('Failed to query freshmeat tags! (%s)' % data)
    tags = set()
    for release in json.loads(data):
        tags.update(release['release']['tag_list'])
    tags = list(tags)
    tags.sort()
    tags = dict(enumerate(tags))

    # Ask the user what tags they want
    print 'Tags are:'
    for id, text in tags.iteritems():
        print '%i - %s' % (id, text)
    ids = [1,3]
    text = raw_input('What is the release focus? [1,3] ')
    if text.strip():
        ids = [int(id.strip()) for id in text.split(',')]
    return ', '.join(tags[id] for id in ids)

def notify(version, changelog, freshmeat_auth=_get_freshmeat_auth_code,
        connection=httplib.HTTPConnection, system=os.system, confirm=raw_input,
        should_send_email=True, tag_list=_get_tags):
    # This is a fresmeat limit
    MAX_CHARS = 600
    short_message = shorten_changelog(changelog)
    while len(short_message) > 600:
        print 'Changelog is too long (must be less then %i characters, is %i)' % (MAX_CHARS, len(short_message))
        text = raw_input('Edit changelog for submission? [y]')
        if text and text != 'y':
            print 'Servers not notified of release.'
            return

        short_message = _edit_message(short_message)

    # Notify freshmeat
    if confirm('Should freshmeat be notified? [y]') in ['', 'y', 'Y']:
        release = {
                'auth_code': freshmeat_auth(),
                'release':{
                    'tag_list':tag_list(connection, freshmeat_auth),
                    'version':str(version),
                    'changelog':short_message
                    },
                }
        headers = {"Content-type": "application/json"}
        conn = connection("freshmeat.net")
        conn.request("POST", "/projects/bdec/releases.json", json.dumps(release), headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        if response.status >= 400:
            print response.status, response.reason
            sys.exit('Failed to submit to freshmeat! (%s)' % data)
        print "Created release; %s %s\n%s" % (response.status, response.reason, data)

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

    if should_send_email:
        send_email(version, changelog)

def upload():
    print "Uploading to the server..."
    while 1:
        os.chdir(project_dir)
        command = "../../google_appengine/appcfg.py update ../"
        if os.system(command) == 0:
            break
        text = raw_input('Failed to upload to the server! Try again? [y]')
        if text.strip() and text != 'y':
            sys.exit('Not uploaded.')

if __name__ == '__main__':
    if len(sys.argv) != 1:
        usage()
        sys.exit(1)

    _check_copyright_statements(['bdec', 'templates'])
    version, date, changelog = get_changelog()[0]

    if version != bdec.__version__:
        sys.exit("Version mismatch! Changelog version is '%s', bdec version is '%s'" % (version, bdec.__version__))

    print "Preparing new bdec release", version
    print "Changes are;"
    print shorten_changelog(changelog)
    print

    update_website()
    update_release_tarball(version)

    os.chdir(root_path)
    if os.system('git status') == 0:
        # Git returns non-zero if 'git commit' would do nothing.
        sys.exit('Source tree has changes! Stopping.')

    if commit_website(version):
        upload()

    tag_changes(version)
    notify(version, changelog)

