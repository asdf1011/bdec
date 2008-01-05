"""
Library to generate source code in various languages for decoding specifications.
"""

import ConfigParser
import mako.lookup
import mako.template
import mako.runtime
import os
import os.path
import sys

import bdec.inspect.param as prm
import bdec.output.xmlout

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
        if not filename.endswith('.tmpl') and not filename.startswith('.'):
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

def _recursive_update(common_references, common, entry):
    if entry in common:
        common_references.add(entry)
    else:
        for child in entry.children:
            _recursive_update(common_references, common, child)


class _EntryInfo(prm.ParamLookup):
    def get_locals(self, entry):
        for local in prm.ParamLookup.get_locals(self, entry):
            yield _variable_name(local)

    def get_params(self, entry):
        for param in prm.ParamLookup.get_params(self, entry):
            yield prm.Param(_variable_name(param.name), param.direction)
            
    def get_invoked_params(self, entry, child):
        for param in prm.ParamLookup.get_invoked_params(self, entry, child):
            yield prm.Param(_variable_name(param.name), param.direction)

class _Utils:
    def __init__(self, common, template_path):
        self._common = common
        self._entries = self._detect_entries()

        config_file = os.path.join(template_path, '.settings')
        settings = ConfigParser.ConfigParser()
        settings.read([config_file])
        self._keywords = list(self._get_keywords(settings))

    def _detect_entries(self):
        """
        Return a list of all entries.
        """
        entries = []
        for entry in self._common:
            entries.extend(self.iter_inner_entries(entry))
        return entries

    def _get_keywords(self, config):
        text = config.get('general', 'keywords')
        keywords = text.split(',')
        for word in keywords:
            yield word.strip()

    def iter_inner_entries(self, entry):
        """
        Iterate over all non-common entries.
        
        Note that entry is also returned, even if it is a common entry.
        """
        for child in entry.children:
           if child not in self._common:
              for sub_child in self.iter_inner_entries(child):
                  yield sub_child
        yield entry

    def iter_entries(self):
        return self._entries

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

        if len(matching_entries) == 1 and name not in self._keywords:
            # No need to escape the name
            result = entry_name 
        else:
            result = "%s %i" % (entry_name, matching_index)
        return result

def _crange(start, end):
    return [chr(i) for i in range(ord(start), ord(end)+1)] 
_VALID_CHARS = _crange('0', '9') + _crange('a', 'z') + _crange('A', 'Z') + ['_', ' ']

def _escape_name(name):
    return "".join(char for char in name if char in _VALID_CHARS)

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

def generate_code(spec, template_path, output_dir, common_entries=[]):
    """
    Generate code to decode the given specification.
    """
    common_templates, entry_templates = _load_templates(template_path)

    lookup = {}
    for filename, template in common_templates:
        _generate_template(output_dir, filename, lookup, template)
    entries = set(common_entries)
    entries.add(spec)
    info = _EntryInfo(entries)
    utils = _Utils(entries, template_path)
    for filename, template in entry_templates:
        for entry in entries:
            referenced_entries = set()
            common_items = entries.copy()
            common_items.remove(entry)
            _recursive_update(referenced_entries, common_items, entry)

            lookup['entry'] = entry
            lookup['esc_name'] = utils.esc_name
            lookup['common'] = referenced_entries
            lookup['get_params'] = info.get_params
            lookup['get_invoked_params'] = info.get_invoked_params
            lookup['is_end_sequenceof'] = info.is_end_sequenceof
            lookup['is_value_referenced'] = info.is_value_referenced
            lookup['is_length_referenced'] = info.is_length_referenced
            lookup['iter_inner_entries'] = utils.iter_inner_entries
            lookup['iter_entries'] = utils.iter_entries
            lookup['local_vars'] = info.get_locals
            lookup['constant'] = _constant_name
            lookup['filename'] = _filename
            lookup['function'] = _variable_name
            lookup['typename'] = _type_name
            lookup['variable'] = _variable_name
            lookup['xmlname'] = bdec.output.xmlout.escape_name
            _generate_template(output_dir, _filename(filename.replace('source', entry.name)), lookup, template)

