#   Copyright (C) 2008 Henry Ludemann
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.

"""
Library to generate source code in various languages for decoding specifications.
"""

import mako.lookup
import mako.template
import mako.runtime
import os
import os.path
import pkg_resources
import sys

import bdec.choice as chc
import bdec.entry as ent
import bdec.inspect.param as prm
import bdec.output.xmlout

class TemplateDir:
    """Class representing a template directory."""
    def listdir(self, dir):
        raise NotImplementedError()

    def read(self, filename):
        raise NotImplementedError()


class BuiltinTemplate(TemplateDir):
    """Class to read a builtin template using pkg_resources."""
    def __init__(self, name):
        self.directory = os.path.join('templates', name)

    def listdir(self):
        return pkg_resources.resource_listdir('bdec', self.directory)

    def read(self, filename):
        return pkg_resources.resource_string('bdec',
                os.path.join(self.directory, filename))

class FilesystemTemplate(TemplateDir):
    def __init__(self, directory):
        self.directory = directory

    def listdir(self):
        return os.listdir(self.directory)

    def read(self, filename):
        input = open(os.path.join(self.directory, filename), 'r')
        contents = input.read()
        input.close()
        return contents


class SettingsError(Exception):
    "An error raised when the settings file is incorrect."
    pass

class Templates:
    def __init__(self, common, entries, settings):
        self.common = common
        self.entries = entries
        self.settings = settings

_SETTINGS = "settings.py"

def is_template(filename):
    # We ignore all 'hidden' files, and the setting files, when looking for templates.
    return not filename.startswith('.') and not filename.endswith('.pyc') \
        and filename != _SETTINGS

def load_templates(template_dir):
    """
    Load all file templates for a given specification.

    Returns a tuple containing (common file templates, entry specific templates),
    where every template is a tuple containing (name, mako template).
    """
    common_templates  = []
    entry_templates = []
    for filename in template_dir.listdir():
        if is_template(filename):
            text = template_dir.read(filename)
            template = mako.template.Template(text, uri=filename)
            if 'source' in filename:
                entry_templates.append((filename, template))
            else:
                common_templates.append((filename, template))

    config_file = template_dir.read(_SETTINGS)
    return Templates(common_templates, entry_templates, config_file)

def _generate_template(output_dir, filename, lookup, template):
    output = file(os.path.join(output_dir, filename), 'w')
    try:
        context = mako.runtime.Context(output, **lookup)
        template.render_context(context)
    except:
        raise Exception(mako.exceptions.text_error_template().render())
    finally:
        output.close()


class _EscapedParameters(prm.CompoundParameters):
    def __init__(self, utils, params):
        self._utils = utils
        prm.CompoundParameters.__init__(self, params)

    def _get_name_map(self, entry):
        """Map an unescaped name to an escaped 'local' name."""
        # We escape the parameter names first to give them the first change of
        # getting the name they want.
        param_names = [param.name for param in prm.CompoundParameters.get_params(self, entry)]
        local_names = [local.name for local in prm.CompoundParameters.get_locals(self, entry)]
        param_escaped = self._utils.esc_names(param_names, self._utils.variable_name)
        local_escaped = self._utils.esc_names(local_names, self._utils.variable_name, param_escaped)

        result = dict(zip(param_names + local_names, param_escaped + local_escaped))

        if entry.name not in result:
            # FIXME: This is a nasty hack. Add the name of the entry itself
            # (for the solver expression). This is necessary if the sequence
            # isn't explicitly referenced.
            result[entry.name] = '*value'
        return result

    def get_local_name(self, entry, name):
        """Map an unescaped name to the 'local' variable name.

        This may be stored as a local or a variable."""
        return self._get_name_map(entry)[name]

    def get_locals(self, entry):
        # We don't to have a local that has the same name as the parent, so we
        # escape the name with respect to the parameter names. We can get
        # similar names for references with constraints (see the 060 sequence
        # with constraint xml regression test).
        names = self._get_name_map(entry)
        for local in prm.CompoundParameters.get_locals(self, entry):
            yield prm.Local(names[local.name], local.type)

    def get_params(self, entry):
        names = self._get_name_map(entry)
        for param in prm.CompoundParameters.get_params(self, entry):
            yield prm.Param(names[param.name], param.direction, param.type)
            
    def get_passed_variables(self, entry, child):
        names = self._get_name_map(entry)
        for param in prm.CompoundParameters.get_passed_variables(self, entry, child):
            if param.name == prm.MAGIC_UNKNOWN_NAME:
                name = param.name
            else:
                name = names[param.name]
            yield prm.Param(name, param.direction, param.type)


class _Settings:
    _REQUIRED_SETTINGS = ['keywords']

    @staticmethod
    def load(config_file, globals):
        code = compile(config_file, _SETTINGS, 'exec')
        eval(code, globals)
        settings = _Settings()
        for key in globals:
            setattr(settings, key, globals[key])

        for keyword in _Settings._REQUIRED_SETTINGS:
            try:
                getattr(settings, keyword)
            except AttributeError:
                raise SettingsError("'%s' must have a '%s' entry!" % (config_file, keyword))
        return settings

class _Utils:
    def __init__(self, common, settings):
        self._common = common
        self._entries = self._detect_entries()
        self._settings = settings

        self._reachable_entries = {}
        for entry in self._entries:
            reachable = set()
            self._update_reachable(entry, reachable)
            self._reachable_entries[entry] = reachable

    def _update_reachable(self, entry, reached):
        if entry in reached:
            return
        reached.add(entry)

        for child in entry.children:
            try:
                reached.update(self._reachable_entries[child.entry])
            except KeyError:
                self._update_reachable(child.entry, reached)

    def is_recursive(self, parent, child):
        "Is the parent entry reachable from the given child."
        return parent in self._reachable_entries[child]

    def _detect_recursive(self, parent, child, parents):
        pass

    def _detect_entries(self):
        """
        Return a list of all entries.
        """
        entries = []
        for entry in self._common:
            entries.extend(self.iter_inner_entries(entry))
        return entries

    def iter_inner_entries(self, entry):
        """
        Iterate over all non-common entries.
        
        Note that entry is also returned, even if it is a common entry.
        """
        for child in entry.children:
           if child.entry not in self._common:
              for sub_child in self.iter_inner_entries(child.entry):
                  yield sub_child
        yield entry

    def iter_entries(self):
        return self._entries

    def iter_required_common(self, entry):
        items = set()
        for child in entry.children:
            if child.entry in self._common:
                if not isinstance(entry, chc.Choice) or not self.is_recursive(entry, child.entry):
                    items.add(child.entry)
            else:
                for e in self.iter_required_common(child.entry):
                    items.add(e)
        result = list(items)
        result.sort(key=lambda a:a.name)
        return result

    def iter_optional_common(self, entry):
        for child in entry.children:
            if child.entry in self._common:
                if isinstance(entry, chc.Choice):
                    yield child.entry
            else:
                for entry in self.iter_optional_common(child.entry):
                    yield entry

    def esc_names(self, names, escape, forbidden=[]):
        """Return a list of unique escaped names.

        names -- The names to escape.
        escape -- A function to call to escape the name.
        forbidden -- A list of names that shouldn't be used.
        return -- A list of unique names (of the same size as the input names).
        """
        names = list(self.esc_name(name) for name in names)

        # Get a simple count of the escaped names, to test if we are expecting
        # collisions for a given name. If we are expecting collisions, we will
        # postfix the name with a number.
        name_count = {}
        for name in names:
            name = escape(name)
            name_count[name] = name_count.get(name, 0) + 1

        result = []
        for name in names:
            count = None if name_count[escape(name)] == 1 else 0
            while 1:
                if count is None:
                    # We aren't expecting collisions, but may get them anyway,
                    # so set the 'count' to zero.
                    escaped = escape(name)
                    count = 0
                else:
                    escaped = escape('%s %i' % (name, count))
                    count += 1
                if escaped not in result and escaped not in forbidden:
                    # We found a unique escaped name
                    result.append(escaped)
                    break
        assert len(result) == len(names)
        return result

    def esc_name(self, name):
        """Escape a name so it doesn't include invalid characters."""
        if not name:
            return "_hidden"
        result = "".join(char for char in name if char in _VALID_CHARS)
        if result[0] in _NUMBERS:
            result = '_' + result
        return result

    def _check_keywords(self, name):
        if name in self._settings.keywords:
            return '%s_' % name
        return name

    def _camelcase(self, name):
        words = self.esc_name(name).split()
        result = "".join(word[0].upper() + word[1:].lower() for word in words)
        return self._check_keywords(result)

    def _delimiter(self, name, delim):
        words = self.esc_name(name).split()
        result = delim.join(words)
        return self._check_keywords(result)

    def variable_name(self, name):
        name = self._delimiter(name, ' ')
        return name[0].lower() + self._camelcase(name)[1:]

    def filename(self, name):
        basename, extension = os.path.splitext(name)
        return self._delimiter(basename, '').lower() + extension

    def type_name(self, name):
        result= self._camelcase(name)
        return result

    def constant_name(self, name):
        return self._delimiter(name, '_').upper()

def _crange(start, end):
    return [chr(i) for i in range(ord(start), ord(end)+1)]
_NUMBERS = _crange('0', '9')
_VALID_CHARS = _NUMBERS + _crange('a', 'z') + _crange('A', 'Z') + ['_', ' ']


def _whitespace(offset):
    """Create a filter for adding leading whitespace"""
    def filter(text):
        if not text:
            return text

        result = ""
        for line in text.splitlines(True):
            result += ' ' * offset + line
        return result
    return filter

def generate_code(spec, templates, output_dir, common_entries=[], options={}):
    """
    Generate code to decode the given specification.
    """
    entries = set(common_entries)
    entries.add(spec)
    
    # We want the entries to be in a consistent order, otherwise the name
    # escaping might choose different names for the same entry across multiple
    # runs.
    entries = list(entries)
    entries.sort(key=lambda a:a.name)

    lookup = options.copy()
    data_checker = prm.DataChecker(entries)
    lookup['settings'] = _Settings.load(templates.settings, lookup)
    utils = _Utils(entries, lookup['settings'])

    params = prm.CompoundParameters([
        prm.ResultParameters(entries),
        prm.ExpressionParameters(entries),
        prm.EndEntryParameters(entries),
        ])
    info = _EscapedParameters(utils, [params])

    lookup['protocol'] = spec
    lookup['common'] = entries
    lookup['esc_name'] = utils.esc_name
    lookup['esc_names'] = utils.esc_names
    lookup['get_params'] = info.get_params
    lookup['raw_params'] = params
    lookup['get_passed_variables'] = info.get_passed_variables
    lookup['is_end_sequenceof'] = info.is_end_sequenceof
    lookup['is_hidden'] = ent.is_hidden
    lookup['is_value_referenced'] = info.is_value_referenced
    lookup['is_length_referenced'] = info.is_length_referenced
    lookup['is_recursive'] = utils.is_recursive
    lookup['child_contains_data'] = data_checker.child_has_data
    lookup['contains_data'] = data_checker.contains_data
    lookup['iter_inner_entries'] = utils.iter_inner_entries
    lookup['iter_required_common'] = utils.iter_required_common
    lookup['iter_optional_common'] = utils.iter_optional_common
    lookup['iter_entries'] = utils.iter_entries
    lookup['local_vars'] = info.get_locals
    lookup['local_name'] = info.get_local_name
    lookup['constant'] = utils.constant_name
    lookup['filename'] = utils.filename
    lookup['function'] = utils.variable_name
    lookup['typename'] = utils.type_name
    lookup['variable'] = utils.variable_name
    lookup['ws'] = _whitespace
    lookup['xmlname'] = bdec.output.xmlout.escape_name

    lookup['decode_params'] = info
    lookup['raw_decode_params'] = params
    lookup['raw_encode_params'] = prm.EncodeParameters(entries)
    lookup['encode_params'] = _EscapedParameters(utils, [lookup['raw_encode_params']])

    for filename, template in templates.common:
        _generate_template(output_dir, filename, lookup, template)
    for filename, template in templates.entries:
        for entry in entries:
            lookup['entry'] = entry
            extension = os.path.splitext(filename)[1]
            _generate_template(output_dir, utils.filename(entry.name) + extension, lookup, template)

