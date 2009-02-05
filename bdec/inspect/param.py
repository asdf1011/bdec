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

class BadReferenceTypeError(bdec.DecodeError):
    def __init__(self, entry):
        bdec.DecodeError.__init__(self, referenced)

    def __str__(self):
        return "Cannot reference non integer field '%s'" % self.entry

class Param(object):
    """Class to represent parameters passed into and out of decodes. """
    IN = "in"
    OUT = "out"

    def __init__(self, name, direction, type):
        self.name = name
        self.direction = direction
        self.type = type

    def __eq__(self, other):
        return self.name == other.name and self.direction == other.direction \
                and self.type == other.type

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "%s %s '%s'" % (self.type, self.direction, self.name)


class _Parameters:
    """Interface for querying information about passed parameters"""
    def get_locals(self, entry):
        raise NotImplementedError()

    def get_params(self, entry):
        """Return an iterable of Param instances."""
        raise NotImplementedError()

    def get_passed_variables(self, entry, child):
        """Return an iterable of Param instances."""
        raise NotImplementedError()

    def is_end_sequenceof(self, entry):
        return False

    def is_value_referenced(self, entry):
        return False

    def is_length_referenced(self, entry):
        return False


class EndEntryParameters(_Parameters):
    """
    Class to allow querying of parameters used when decoding a sequence of.
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
            self._populate_lookup(child.entry, intermediaries[:])

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
            return set([Param('should end', Param.OUT,  int)])
        return set()

    def get_passed_variables(self, entry, child):
        # The passed parameter names don't change for 'should end' variables;
        # the name is the same in both parent & child.
        return self.get_params(child.entry)

    def is_end_sequenceof(self, entry):
        return entry in self._end_sequenceof_entries

class _VariableParam:
    def __init__(self, reference, direction):
        assert isinstance(reference, expr.ValueResult) or isinstance(reference, expr.LengthResult)
        self.reference = reference
        self.direction = direction

    def __hash__(self):
        return hash(self.reference.name)

    def __eq__(self, other):
        return self.reference.name == other.reference.name and self.direction == other.direction

    def __str__(self):
        return "%s %s" % (self.direction, self.reference)


class ExpressionParameters(_Parameters):
    """
    A class to calculate parameters passed between entries.

    All entries that have expressions can reference other entries; this class
    is responsible for detecting the parameters that must be passed between
    those entries to supply the data the expression requires.
    """
    def __init__(self, entries):
        # A map of entry -> list of _VariableParam instances
        self._params = {}

        # A lookup of [entry][child][param.name] to get the 'local' name of the
        # child parameter.
        self._local_child_param_name = {}
        self._referenced_values = set()
        self._referenced_lengths = set()
        unreferenced_entries = {}
        for entry in entries:
            self._populate_references(entry, unreferenced_entries)

    def _collect_references(self, expression):
        """
        Walk an expression object, collecting all named references.
        
        Returns a list of tuples of (entry instances, variable name).
        """
        result = []
        if isinstance(expression, expr.Constant):
            pass
        elif isinstance(expression, expr.ValueResult):
            result.append(expression)
        elif isinstance(expression, expr.LengthResult):
            result.append(expression)
        elif isinstance(expression, expr.Delayed):
            result = self._collect_references(expression.left) + \
                     self._collect_references(expression.right)
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
            self._populate_references(child.entry, unreferenced_entries)

        # An entries unknown references are those referenced in any 
        # expressions, and those that are unknown in all of its children.
        if entry.length is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.length))
        elif isinstance(entry, sof.SequenceOf) and entry.count is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.count))

        # Store the names the child doesn't know about (ie: names that must be
        # resolved for this entry to decode)
        child_unknowns = set()
        for child in entry.children:
            child_unknowns.update(unreferenced_entries[child.entry])

        if isinstance(entry, seq.Sequence) and entry.value is not None:
            # A sequence's references are treated as child unknowns, as they
            # are resolved from within the entry (and not passed in).
            child_unknowns.update(self._collect_references(entry.value))

        # Our unknown list is all the unknowns in our children that aren't
        # present in our known references.
        child_names = [child.name for child in entry.children]
        for unknown in child_unknowns:
            name = unknown.name.split('.')[0]
            if name not in child_names:
                # This value is 'unknown' to the entry, and must be passed in.
                unreferenced_entries[entry].add(unknown)
            else:
                # This value comes from one of our child entries, so drill down
                # into it.
                self._add_out_params(entry, unknown)

        for reference in unreferenced_entries[entry]:
            self._params[entry].add(_VariableParam(reference, Param.IN))

    def _get_local_reference(self, entry, child, param):
        """Get the local of a parameter used by a child entry.

        Return either a bdec.spec.expression.ValueResult or a
        bdec.spec.expression.LengthResult.
        """
        try:
            name = self._local_child_param_name[entry][child][param.reference.name]
        except KeyError:
            name = param.reference.name

        # Create a new instance of the expression reference, using the new name
        return type(param.reference)(name)

    def _add_reference(self, entry, reference):
        self._params[entry].add(_VariableParam(reference, Param.OUT))
        if isinstance(entry, fld.Field):
            if entry.format not in [fld.Field.INTEGER, fld.Field.BINARY]:
                # We currently only allow integers and binary
                # strings in integer expressions.
                raise BadReferenceTypeError(entry)
            self._referenced_values.add(entry)
        elif isinstance(entry, seq.Sequence):
            if entry.value is not None:
                self._referenced_values.add(entry)
            else:
                # We can only reference sequences with a value
                raise BadReferenceError(entry, reference.name)
        elif isinstance(entry, chc.Choice):
            # When referencing a choice, we want to attempt to reference each
            # of its children.
            child_params = self._local_child_param_name.setdefault(entry, {})
            self._params[entry].add(_VariableParam(reference, Param.OUT))
            for child in entry.children:
                child_reference = type(reference)(child.entry.name)
                self._add_reference(child.entry, child_reference)

                local_names = child_params.setdefault(child, {})
                local_names[child_reference.name] = reference.name
        else:
            raise BadReferenceError(entry, name)

    def _add_out_params(self, entry, reference):
        """
        Drill down into the children of 'entry', adding output params to 'name'.

        entry -- An instance of bdec.entry.Entry
        reference -- An instance of either bdec.spec.expression.ValueResult or
            bdec.spec.expression.LengthResult.
        """
        if isinstance(entry, chc.Choice):
            # The option names aren't specified in a choice expression
            for child in entry.children:
                self._params[child.entry].add(_VariableParam(reference, Param.OUT))
                self._add_out_params(child.entry, reference)
        elif isinstance(entry, seq.Sequence):
            was_child_found = False
            child_params = self._local_child_param_name.setdefault(entry, {})
            for child in entry.children:
                local_names = child_params.setdefault(child, {})
                if child.name == reference.name:
                    # This parameter references the value / length of the child
                    # item. As the name might be different between parent and
                    # child, use the childs name.
                    child_reference = type(reference)(child.entry.name)
                    local_names[child.entry.name] = reference.name
                    was_child_found = True
                    if isinstance(child_reference, expr.ValueResult):
                        self._add_reference(child.entry, child_reference)
                    else:
                        self._params[child.entry].add(_VariableParam(child_reference, Param.OUT))
                        self._referenced_lengths.add(child.entry)
                else:
                    child_name = reference.name.split('.')[0]
                    if child.name == child_name:
                        sub_name = ".".join(reference.name.split('.')[1:])
                        local_names[sub_name] = reference.name
                        child_reference = type(reference)(sub_name)

                        # We found a child item that knows about this parameter
                        self._params[child.entry].add(_VariableParam(child_reference, Param.OUT))
                        self._add_out_params(child.entry, child_reference)
                        was_child_found = True
            if not was_child_found:
                raise ent.MissingExpressionReferenceError(entry, reference.name)
        else:
            raise BadReferenceError(entry, reference.name)

    def get_locals(self, entry):
        """
        Get the names of local variables used when decoding an entry.

        Local variables are all child outputs that aren't an output of the
        entry.
        """
        locals = set()
        params = self._params[entry]
        for child in entry.children:
            for child_param in self._params[child.entry]:
                if child_param.direction == Param.OUT:
                    local = self._get_local_reference(entry, child, child_param)
                    if _VariableParam(local, child_param.direction) not in params:
                        locals.add(self._get_reference_name(local))
        result = list(locals)
        result.sort()
        return result

    def get_params(self, entry):
        """
        Get an iterator to all parameters passed to an entry due to value references.
        """
        assert isinstance(entry, bdec.entry.Entry)
        params = list(self._params[entry])
        params.sort(key=lambda a:a.reference.name)
        result = list(Param(self._get_reference_name(param.reference), param.direction, int) for param in params)
        return result

    def _get_reference_name(self, reference):
        if isinstance(reference, expr.ValueResult):
            return reference.name
        elif isinstance(reference, expr.LengthResult):
            return reference.name + ' length'
        raise Exception("Unknown reference type '%s'" % reference)

    def get_passed_variables(self, entry, child):
        """
        Get an iterator to parameters passed from a parent to child entry.

        entry -- A bdec.entry.Entry instance
        child -- A bdec.entry.Child instance
        return -- An iterator to Param instances for variables passed from
            entry to child entry.
        """
        assert isinstance(entry, bdec.entry.Entry)
        assert isinstance(child, bdec.entry.Child)
        child_params = list(self._params[child.entry])
        child_params.sort(key=lambda a:a.reference.name)
        for param in child_params:
            local = self._get_local_reference(entry, child, param)
            yield Param(self._get_reference_name(local), param.direction, int)

    def is_value_referenced(self, entry):
        """ Is the decoded value of an entry used elsewhere. """
        return entry in self._referenced_values

    def is_length_referenced(self, entry):
        """ Is the decoded length of an entry used elsewhere. """
        return entry in self._referenced_lengths

class DataChecker:
    """A class to check whether an entry contains visible data."""
    def __init__(self, entries):
        """A list of entries to check for visibility.

        All other entries reachable by these entries can also be checked."""
        self._has_data = {}
        entries = set(entries)
        while entries:
            entry = entries.pop()
            intermediates = set()
            stack = []
            self._populate(entry, stack, intermediates)
            assert not stack
            for entry in intermediates:
                del self._has_data[entry]
            entries.update(intermediates)

    def _populate(self, entry, stack, intermediates):
        """Walk down all entries contained within this entry, checking for visibility."""
        if entry in stack:
            # An entry is within itself. This entry will be 'visible' either if
            # it itself is visible, or it contains a visible child, but at this
            # stage we don't know for sure (as all of its children haven't been
            # processed). If so, we'll mark all of its children to a list that 
            # requires them to be re-processed.
            if not self._has_data[entry]:
                for inter in stack[stack.index(entry)+1:]:
                    intermediates.add(inter)
            return

        if entry in self._has_data:
            return

        self._has_data[entry] = not entry.is_hidden()

        # This entry isn't yet calculated; do so now.
        stack.append(entry)
        for child in entry.children:
            self._populate(child.entry, stack, intermediates)
            self._has_data[entry] |= self._has_data[child.entry]
        stack.remove(entry)

    def contains_data(self, entry):
        return self._has_data[entry]


class ResultParameters(_Parameters):
    """
    A class that generates the parameters used when passing the decode result
    out of the decode function as a parameter.
    """
    def __init__(self, entries):
        self._checker = DataChecker(entries)

    def get_locals(self, entry):
        # Result items are never stored as locals; they are always passed out.
        return []

    def get_params(self, entry):
        if not self._checker.contains_data(entry):
            return []
        return [Param('result', Param.OUT, entry)]

    def get_passed_variables(self, entry, child):
        if not self._checker.contains_data(child.entry):
            return []
        return [Param('unknown', Param.OUT, child.entry)]


class CompoundParameters(_Parameters):
    """
    Class to return the results of several other parameter query classes
    through one instance.
    """
    def __init__(self, parameter_queries):
        self._queries = parameter_queries

    def get_locals(self, entry):
        for query in self._queries:
            for local in query.get_locals(entry):
                yield local

    def get_params(self, entry):
        for query in self._queries:
            for param in query.get_params(entry):
                yield param

    def get_passed_variables(self, entry, child):
        for query in self._queries:
            for param in query.get_passed_variables(entry, child):
                yield param

    def is_end_sequenceof(self, entry):
        for query in self._queries:
            if query.is_end_sequenceof(entry):
                return True
        return False

    def is_value_referenced(self, entry):
        for query in self._queries:
            if query.is_value_referenced(entry):
                return True
        return False

    def is_length_referenced(self, entry):
        for query in self._queries:
            if query.is_length_referenced(entry):
                return True
        return False

