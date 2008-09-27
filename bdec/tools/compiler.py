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
import sys

import bdec.choice as chc
import bdec.inspect.param as prm
import bdec.output.xmlout

class SettingsError(Exception):
    "An error raised when the settings file is incorrect."
    pass

_SETTINGS = "settings.py"

def is_template(filename):
    # We ignore all 'hidden' files, and the setting files, when looking for templates.
    return not filename.startswith('.') and filename != _SETTINGS

_template_cache = {}
def _load_templates(directory):
    """
    Load all file templates for a given specification.

    Returns a tuple containing (common file templates, entry specific templates),
    where every template is a tuple containing (name, mako template).
    """
    # We cache the results, as it sped up the tests by about 3x.
    if directory in _template_cache:
        return _template_cache[directory]

    common_templates  = []
    entry_templates = []
    for filename in os.listdir(directory):
        if is_template(filename):
            path = os.path.join(directory, filename)
            lookup = mako.lookup.TemplateLookup(directories=[directory])
            template = mako.template.Template(filename=path, lookup=lookup)
            if 'source' in filename:
                entry_templates.append((filename, template))
            else:
                common_templates.append((filename, template))
    _template_cache[directory] = (common_templates, entry_templates)
    return (common_templates, entry_templates)

def _generate_template(output_dir, filename, lookup, template):
    output = file(os.path.join(output_dir, filename), 'w')
    try:
        context = mako.runtime.Context(output, **lookup)
        template.render_context(context)
    except:
        raise Exception(mako.exceptions.text_error_template().render())
    finally:
        output.close()


class _EntryInfo(prm.CompoundParameters):
    def __init__(self, entries):
        queries = []
        queries.append(prm.ResultParameters(entries))
        queries.append(prm.ExpressionParameters(entries))
        queries.append(prm.EndEntryParameters(entries))
        prm.CompoundParameters.__init__(self, queries)

    def get_locals(self, entry):
        for local in prm.CompoundParameters.get_locals(self, entry):
            yield _variable_name(local)

    def get_params(self, entry):
        for param in prm.CompoundParameters.get_params(self, entry):
            yield prm.Param(_variable_name(param.name), param.direction, param.type)
            
    def get_passed_variables(self, entry, child):
        for param in prm.CompoundParameters.get_passed_variables(self, entry, child):
            yield prm.Param(_variable_name(param.name), param.direction, param.type)

class _Settings:
    _REQUIRED_SETTINGS = ['keywords']

    @staticmethod
    def load(filename, globals):
        execfile(filename, globals)
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
    def __init__(self, common, template_path, settings):
        self._common = common
        self._entries = self._detect_entries()
        self._settings = settings

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
        for child in entry.children:
            if child.entry in self._common:
                if not isinstance(entry, chc.Choice):
                    yield child.entry
            else:
                for e in self.iter_required_common(child.entry):
                    yield e

    def iter_optional_common(self, entry):
        for child in entry.children:
            if child.entry in self._common:
                if isinstance(entry, chc.Choice):
                    yield child
            else:
                for entry in self.iter_optional_common(child.entry):
                    yield entry

    def esc_name(self, index, iter_entries):
        # Find all entries that will have the same name as the entry at i
        entry_name = _escape_name(iter_entries[index].name)
        matching_entries = []
        matching_index = None
        for i, e in enumerate(iter_entries):
            name = _escape_name(e.name)
            if name == entry_name:
                matching_entries.append(e)
                if i == index:
                    matching_index = len(matching_entries)

        assert matching_index != None
        assert len(matching_entries) > 0

        if len(matching_entries) == 1 and name not in self._settings.keywords:
            # No need to escape the name
            result = entry_name 
        else:
            result = "%s %i" % (entry_name, matching_index)
        return result

def _crange(start, end):
    return [chr(i) for i in range(ord(start), ord(end)+1)] 
_NUMBERS = _crange('0', '9')
_VALID_CHARS = _NUMBERS + _crange('a', 'z') + _crange('A', 'Z') + ['_', ' ']

def _escape_name(name):
    if not name:
        return "_hidden"
    result = "".join(char for char in name if char in _VALID_CHARS)
    if result[0] in _NUMBERS:
        result = '_' + result
    return result

def _camelcase(name):
    words = _escape_name(name).split()
    return "".join(word[0].upper() + word[1:].lower() for word in words)

def _delimiter(name, delim):
    words = _escape_name(name).split()
    return delim.join(words)

def _variable_name(name):
    name = _delimiter(name, ' ')
    return name[0].lower() + _camelcase(name)[1:]

def _filename(name):
    basename, extension = os.path.splitext(name)
    return _delimiter(basename, '').lower() + extension

def _type_name(name):
    result= _camelcase(name)
    return result

def _constant_name(name):
    return _delimiter(name, '_').upper()

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

def generate_code(spec, template_path, output_dir, common_entries=[]):
    """
    Generate code to decode the given specification.
    """
    common_templates, entry_templates = _load_templates(template_path)
    entries = set(common_entries)
    entries.add(spec)
    info = _EntryInfo(entries)

    lookup = {}
    config_file = os.path.join(template_path, _SETTINGS)
    data_checker = prm.DataChecker(entries)
    lookup['settings'] = _Settings.load(config_file, lookup)
    utils = _Utils(entries, template_path, lookup['settings'])
    lookup['protocol'] = spec
    lookup['common'] = entries
    lookup['esc_name'] = utils.esc_name
    lookup['get_params'] = info.get_params
    lookup['get_passed_variables'] = info.get_passed_variables
    lookup['is_end_sequenceof'] = info.is_end_sequenceof
    lookup['is_value_referenced'] = info.is_value_referenced
    lookup['is_length_referenced'] = info.is_length_referenced
    lookup['contains_data'] = lambda entry: data_checker.contains_data(entry)
    lookup['iter_inner_entries'] = utils.iter_inner_entries
    lookup['iter_required_common'] = utils.iter_required_common
    lookup['iter_optional_common'] = utils.iter_optional_common
    lookup['iter_entries'] = utils.iter_entries
    lookup['local_vars'] = info.get_locals
    lookup['constant'] = _constant_name
    lookup['filename'] = _filename
    lookup['function'] = _variable_name
    lookup['typename'] = _type_name
    lookup['variable'] = _variable_name
    lookup['ws'] = _whitespace
    lookup['xmlname'] = bdec.output.xmlout.escape_name

    for filename, template in common_templates:
        _generate_template(output_dir, filename, lookup, template)
    for filename, template in entry_templates:
        for entry in entries:
            lookup['entry'] = entry
            _generate_template(output_dir, _filename(filename.replace('source', entry.name)), lookup, template)

