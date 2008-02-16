
import bdec
import bdec.choice as chc
import bdec.entry as ent
import bdec.field as fld
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.spec.expression as expr


class BadReferenceError(bdec.DecodeError):
    def __init__(self, entry, name):
        bdec.DecodeError.__init__(self, entry)
        self.name = name

    def __str__(self):
        return "Cannot reference '%s' in %s" % (self.name, self.entry)


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
        self._params = {}
        self._locals = {}

        self._referenced_values = set()
        self._referenced_lengths = set()
        unreferenced_entries = {}
        for entry in entries:
            self._populate_references(entry, unreferenced_entries)
        self._detect_out_params()

    def _collect_references(self, expression):
        """
        Walk an expression object, collecting all named references.
        
        Returns a list of tuples of (entry instances, variable name).
        """
        result = []
        if isinstance(expression, int):
            pass
        elif isinstance(expression, expr.ValueResult):
            result.append(expression.name)
        elif isinstance(expression, expr.LengthResult):
            result.append(expression.name + ' length')
        elif isinstance(expression, expr.Delayed):
            result = self._collect_references(expression.left) + self._collect_references(expression.right)
        else:
            raise Exception("Unable to collect references from unhandled expression type '%s'!" % expression)
        return result

    def _populate_references(self, entry, unreferenced_entries):
        """
        Walk down the tree, populating the '_params', '_referenced_XXX' sets.

        Handles recursive elements.
        """
        if entry in self._params:
            return
        self._params[entry] = set()
        unreferenced_entries[entry] = set()

        for child in entry.children:
            self._populate_references(child, unreferenced_entries)

        # An entries unknown references are those referenced in any 
        # expressions, and those that are unknown in all of its children.
        if entry.length is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.length))
        elif isinstance(entry, sof.SequenceOf) and entry.count is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.count))

        # Store the names the child doesn't know about (ie: names that must be resolved for this entry to decode)
        child_unknowns = set()
        for child in entry.children:
            child_unknowns.update(unreferenced_entries[child])

        if isinstance(entry, seq.Sequence) and entry.value is not None:
            # A sequence's references are treated as child unknowns, as they
            # are resolved from within the entry (and not passed in).
            child_unknowns.update(self._collect_references(entry.value))

        # Our unknown list is all the unknowns in our children that aren't
        # present in our known references.
        self._locals[entry] = set()
        child_names = [child.name for child in entry.children]
        for fullname in child_unknowns:
            name = fullname.split('.')[0]
            if name in child_names or (name.endswith(' length') and name[:-7] in child_names):
                # This value is a local...
                self._locals[entry].add(fullname)
                pass
            else:
                # This value is 'unknown' to the entry, and must be passed in.
                unreferenced_entries[entry].add(fullname)

        for name in unreferenced_entries[entry]:
            self._params[entry].add(Param(name, Param.IN))

    def _get_local_name(self, entry, child, param):
        """Get the local name of a parameter used by a child entry. """
        if param.direction == Param.OUT and not self._is_named_entry(child, param.name) and not isinstance(entry, chc.Choice):
            local = "%s.%s" % (child.name, param.name)
        else:
            local = param.name
        return local

    def _detect_locals(self):
        """ Detect child parameters that aren't in the parent entries parameters """
        for entry, params in self._params.iteritems():
            names = [param.name for param in params]

            for child in entry.children:
                for param in self._params[child]:
                    local = self._get_local_name(entry, child, param)
                    if local not in names:
                        self._locals[entry].add(local)

    def _detect_out_params(self):
        """ Add output parameters for all entries. """
        # Now that we have the locals, drill down into the relevant children
        # to pass the params as outputs.
        for entry, locals in self._locals.iteritems():
            for name in locals:
                self._add_out_params(entry, name)

        # We re-run the local detection, to find detect any 'unused' output parameters
        self._detect_locals()

    def _is_named_entry(self, entry, name):
        return name in [entry.name, entry.name + ' length']

    def _add_out_params(self, entry, name):
        """
        Drill down into the children of 'entry', adding output params to 'name'.
        """
        if isinstance(entry, chc.Choice):
            # The option names aren't specified in a choice expression
            for child in entry.children:
                self._params[child].add(Param(name, Param.OUT))
                self._add_out_params(child, name)
        elif isinstance(entry, seq.Sequence):
            was_child_found = False
            for child in entry.children:
                if self._is_named_entry(child, name):
                    # This parameter references the value / length of the child item
                    self._params[child].add(Param(name, Param.OUT))
                    was_child_found = True
                    if name == child.name:
                        self._referenced_values.add(child)
                    else:
                        self._referenced_lengths.add(child)
                else:
                    child_name = name.split('.')[0]
                    sub_name = ".".join(name.split('.')[1:])
                    if child.name == child_name:
                        # We found a child item that knows about this parameter
                        self._params[child].add(Param(sub_name, Param.OUT))
                        self._add_out_params(child, sub_name)
                        was_child_found = True
            if not was_child_found:
                raise ent.MissingExpressionReferenceError(entry, name)
        else:
            raise BadReferenceError(entry, name)

    def get_locals(self, entry):
        """
        Get the names of local variables used when decoding an entry.

        Local variables are all child outputs that aren't an output of the
        entry.
        """
        result = list(self._locals[entry])
        result.sort()
        return result

    def get_params(self, entry):
        """
        Get an iterator to all parameters passed to an entry due to value references.
        """
        result = list(self._params[entry])
        result.sort(key=lambda a:a.name)
        return result

    def get_invoked_params(self, entry, child):
        """
        Get a iterator to all parameters passed from a parent to a child entry.
        """
        for param in self.get_params(child):
            local = self._get_local_name(entry, child, param)
            yield Param(local, param.direction)

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
        for param in self._sequenceof_lookup.get_params(entry):
            yield param
        for param in self._variable_references.get_params(entry):
            yield param

    def get_invoked_params(self, entry, child):
        for param in self._sequenceof_lookup.get_params(child):
            yield param
        for param in self._variable_references.get_invoked_params(entry, child):
            yield param

    def is_end_sequenceof(self, entry):
        return self._sequenceof_lookup.is_end_sequenceof(entry)

    def is_value_referenced(self, entry):
        return self._variable_references.is_value_referenced(entry)

    def is_length_referenced(self, entry):
        return self._variable_references.is_length_referenced(entry)

