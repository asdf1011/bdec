"""
Library to generate source code in various languages for decoding specifications.
"""

import mako.lookup
import mako.template
import mako.runtime
import os
import sys

import bdec.spec.expression as expr
import bdec.field as fld
import bdec.sequenceof as sof

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

class Param:
    """Class to represent parameters passed into and out of decodes. """
    IN = "in"
    OUT = "out"

    def __init__(self, name, direction):
        self.name = name
        self.direction = direction

    def __eq__(self, other):
        return self.name == other.name and self.direction == other.direction

    def __hash__(self):
        return hash(self.name)


class _SequenceOfParamLookup:
    """
    Class to allow querying of paremeters used when decoding a sequence of.
    """
    def __init__(self, spec):
        self._has_context_lookup = {}

        self._end_sequenceof_entries = set()
        self._populate_lookup(spec, [])

    def _populate_lookup(self, entry, intermediaries):
        if entry in self._has_context_lookup:
            return
        self._has_context_lookup.setdefault(entry, False)

        if isinstance(entry, sof.SequenceOf):
            self._end_sequenceof_entries.update(entry.end_entries)
            intermediaries = []
        else:
            intermediaries.append(entry)

        if entry in self._end_sequenceof_entries:
            # We found a 'end-sequenceof' entry. All the items between the end
            # entry and the sequenceof must be able to pass the 'end' context
            # back up to the sequenceof.
            for intermediary in intermediaries:
                self._has_context_lookup[intermediary] = True

        # Keep walking down the chain look for 'end-sequenceof' entries.
        for child in entry.children:
            self._populate_lookup(child, intermediaries[:])

    def get_params(self, entry):
        """
        If an item is between a sequenceof and an end-sequenceof entry, it
        should pass an output 'should_end' context item.
        """
        if self._has_context_lookup[entry]:
            return set([Param('should_end', Param.OUT)])
        return set()

    def is_end_sequenceof(self, entry):
        return entry in self._end_sequenceof_entries

class _VariableReference:
    def __init__(self, spec):
        self._locals = {}
        self._params = {}

        self._referenced_entries = set()
        self._populate_references(spec, {}, {})

    def _collect_references(self, expression):
        """ Walk an expression object, collecting all named references. """
        if isinstance(expression, int):
            return []
        elif isinstance(expression, expr.ValueResult):
            self._referenced_entries.add(expression.entries[0])
            return [expression.entries[0]]
        elif isinstance(expression, expr.Delayed):
            return self._collect_references(expression.left) + self._collect_references(expression.right)
        raise Exception("Unable to collect references from unhandled expression type '%s'!" % expression)

    def _populate_references(self, entry, unreferenced_entries, known_references):
        """
        Walk down the tree, populating the '_params', '_locals', and '_referenced_entries' sets.

        Handles recursive elements.
        """
        if entry in self._params:
            return
        self._params[entry] = set()

        for child in entry.children:
            self._populate_references(child, unreferenced_entries, known_references)

        # An entries unknown references are those referenced in any 
        # expressions, and those that are unknown in all of its children.
        unreferenced_entries[entry] = set()
        if isinstance(entry, fld.Field):
            unreferenced_entries[entry].update(self._collect_references(entry.length))
        elif isinstance(entry, sof.SequenceOf) and entry.count is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.count))

        child_unknowns = set()
        known_references[entry] = set([entry])
        for child in entry.children:
            known_references[entry].update(known_references[child])
            child_unknowns.update(unreferenced_entries[child])

        # Our unknown list is all the unknowns in our children that aren't
        # present in our known references.
        unknown = child_unknowns.difference(known_references[entry])
        unreferenced_entries[entry].update(unknown)

        # Local variables for this entry are all entries that our children
        # don't know about, but we do (eg: we can access it through another
        # of our children).
        self._locals[entry] = child_unknowns.intersection(known_references[entry])

        # Detect all parameters necessary to decode this entry.
        for item in unreferenced_entries[entry]:
            self._params[entry].add(Param(item.name, Param.IN))
        for local in self._locals[entry]:
            self._add_out_params(local, entry.children, known_references)

    def _add_out_params(self, entry, entries, known_references):
        """
        Drill down into entries looking for entry, adding output params.
        """
        for item in entries:
            if entry is item or entry in known_references[item]:
                self._params[item].add(Param(entry.name, Param.OUT))
                if entry in item.children:
                    self._add_out_params(entry, item.children, known_references)
                return

    def get_locals(self, entry):
        """
        Get locals used when decoding an entry.

        All child entries that reference another child reference, where the
        given entry is the nearest common ancestor.
        """
        return [local.name for local in self._locals[entry]]

    def get_params(self, entry):
        """
        Get all parameters passed to an entry due to value references.
        """
        return self._params[entry]

    def is_referenced(self, entry):
        """ Is the decoded value of an entry used elsewhere. """
        return entry in self._referenced_entries


class _EntryInfo:
    def __init__(self, spec):
        self._sequenceof_lookup = _SequenceOfParamLookup(spec)
        self._variable_references = _VariableReference(spec)

    def get_locals(self, entry):
        result = []
        if isinstance(entry, sof.SequenceOf):
            if entry.end_entries:
                result.append('should_end')
        result.extend(self._variable_references.get_locals(entry))
        return result

    def get_params(self, entry):
        result = self._sequenceof_lookup.get_params(entry).copy()
        result.update(self._variable_references.get_params(entry))
        return result

    def is_end_sequenceof(self, entry):
        return self._sequenceof_lookup.is_end_sequenceof(entry)

    def is_referenced(self, entry):
        return self._variable_references.is_referenced(entry)

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
    info = _EntryInfo(spec)
    for filename, template in entry_templates:
        for entry in entries:
            referenced_entries = set()
            common_items = entries.copy()
            common_items.remove(entry)
            _recursive_update(referenced_entries, common_items, entry)

            lookup['entry'] = entry
            lookup['common'] = referenced_entries
            lookup['get_params'] = info.get_params
            lookup['is_end_sequenceof'] = info.is_end_sequenceof
            lookup['is_referenced'] = info.is_referenced
            lookup['local_vars'] = info.get_locals
            _generate_template(output_dir, filename.replace('source', entry.name), lookup, template)

