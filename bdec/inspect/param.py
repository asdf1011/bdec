
import bdec.spec.expression as expr
import bdec.field as fld
import bdec.sequence as seq
import bdec.sequenceof as sof


class Param(object):
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

    def __repr__(self):
        return "%s param '%s'" % (self.direction, self.name)


class SequenceOfParamLookup:
    """
    Class to allow querying of paremeters used when decoding a sequence of.
    """
    def __init__(self, entries):
        self._has_context_lookup = {}

        self._end_sequenceof_entries = set()
        for entry in entries:
            self._populate_lookup(entry, [])

    def _populate_lookup(self, entry, intermediaries):
        if entry in self._has_context_lookup:
            return
        self._has_context_lookup.setdefault(entry, False)

        if isinstance(entry, sof.SequenceOf):
            self._end_sequenceof_entries.update(end for end, offset in entry.end_entries)
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

    def _walk(self, entry, visited, offset):
        if entry in visited:
            return
        visited.add(entry)
        for child in children:
            self._walk(child, visited, offset + 1)

    def get_locals(self, entry):
        result = []
        if isinstance(entry, sof.SequenceOf):
            if entry.end_entries:
                result.append('should end')
        return result

    def get_params(self, entry):
        """
        If an item is between a sequenceof and an end-sequenceof entry, it
        should pass an output 'should_end' context item.
        """
        if self._has_context_lookup[entry]:
            return set([Param('should end', Param.OUT)])
        return set()

    def is_end_sequenceof(self, entry):
        return entry in self._end_sequenceof_entries


class VariableReference:
    def __init__(self, entries):
        self._locals = {}
        self._params = {}

        self._referenced_values = set()
        self._referenced_lengths = set()
        unreferenced_entries = {}
        known_references = {}
        for entry in entries:
            self._populate_references(entry, unreferenced_entries, known_references)

    def _collect_references(self, expression):
        """
        Walk an expression object, collecting all named references.
        
        Returns a list of tuples of (entry instances, variable name).
        """
        result = []
        if isinstance(expression, int):
            pass
        elif isinstance(expression, expr.ValueResult):
            for reference, name in expression.entries:
                self._referenced_values.add(reference)
                result.append((reference, name))
        elif isinstance(expression, expr.LengthResult):
            for reference in expression.entries:
                self._referenced_lengths.add(reference)
                result.append((reference, reference.name + ' length'))
        elif isinstance(expression, expr.Delayed):
            result = self._collect_references(expression.left) + self._collect_references(expression.right)
        else:
            raise Exception("Unable to collect references from unhandled expression type '%s'!" % expression)
        return result

    def _populate_references(self, entry, unreferenced_entries, known_references):
        """
        Walk down the tree, populating the '_params', '_locals', and '_referenced_XXX' sets.

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
        if entry.length is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.length))
        elif isinstance(entry, sof.SequenceOf) and entry.count is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.count))

        child_unknowns = set()
        known_references[entry] = set([entry])
        for child in entry.children:
            known_references[entry].update(known_references[child])
            child_unknowns.update(unreferenced_entries[child])
        if isinstance(entry, seq.Sequence) and entry.value is not None:
            # A sequence's references are treated as child unknowns, as they
            # are resolved from within the entry (and not passed in).
            child_unknowns.update(self._collect_references(entry.value))

        # Our unknown list is all the unknowns in our children that aren't
        # present in our known references.
        unknown = ((child, name) for child, name in child_unknowns if child not in known_references[entry])
        unreferenced_entries[entry].update(unknown)

        # Local variables for this entry are all entries that our children
        # don't know about, but we do (eg: we can access it through another
        # of our children).
        self._locals[entry] = [(child, name) for child, name in child_unknowns if child in known_references[entry]]

        # Detect all parameters necessary to decode this entry.
        for item, name in unreferenced_entries[entry]:
            self._params[entry].add(Param(name, Param.IN))
        for local, name in self._locals[entry]:
            self._add_out_params(local, name, entry.children, known_references)

    def _add_out_params(self, entry, name, entries, known_references):
        """
        Drill down into entries looking for entry, adding output params.
        """
        for item in entries:
            if entry is item or entry in known_references[item]:
                self._params[item].add(Param(name, Param.OUT))
                for child in item.children:
                    if entry in known_references[child]:
                        self._add_out_params(entry, name, item.children, known_references)
                return

    def get_locals(self, entry):
        """
        Get locals used when decoding an entry.

        All child entries that reference another child reference, where the
        given entry is the nearest common ancestor.
        """
        return [name for item, name in self._locals[entry]]

    def get_params(self, entry):
        """
        Get all parameters passed to an entry due to value references.
        """
        return self._params[entry]

    def is_value_referenced(self, entry):
        """ Is the decoded value of an entry used elsewhere. """
        return entry in self._referenced_values

    def is_length_referenced(self, entry):
        """ Is the decoded length of an entry used elsewhere. """
        return entry in self._referenced_lengths


class ParamLookup:
    """
    Class to detect parameter information about all entries in a tree.
    """
    def __init__(self, entries):
        self._sequenceof_lookup = SequenceOfParamLookup(entries)
        self._variable_references = VariableReference(entries)

    def get_locals(self, entry):
        result = self._sequenceof_lookup.get_locals(entry)
        result.extend(self._variable_references.get_locals(entry))
        return result

    def get_params(self, entry):
        """
        Return an iterator to Param objects for the given entry.
        """
        result = self._sequenceof_lookup.get_params(entry).copy()
        result.update(self._variable_references.get_params(entry))
        return result

    def is_end_sequenceof(self, entry):
        return self._sequenceof_lookup.is_end_sequenceof(entry)

    def is_value_referenced(self, entry):
        return self._variable_references.is_value_referenced(entry)

    def is_length_referenced(self, entry):
        return self._variable_references.is_length_referenced(entry)

