#   Copyright (C) 2008-2009 Henry Ludemann
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
Set of classes for examining entries to determine the dependencies between them.

Is able to represent these dependencies as a 'parameters' passed between the
entries, and the types (and where valid, the valid ranges of values) of those
entries.
"""


import bdec
import bdec.choice as chc
from bdec.constraints import Equals
import bdec.entry as ent
import bdec.field as fld
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.expression as expr
from bdec.inspect.type import VariableType, IntegerType, MultiSourceType, \
        EntryType, EntryValueType, EntryLengthType, ShouldEndType


class BadReferenceError(bdec.DecodeError):
    def __init__(self, entry):
        bdec.DecodeError.__init__(self, entry)

    def __str__(self):
        return "Can't reference %s" % (self.entry)

class BadReferenceTypeError(bdec.DecodeError):
    def __init__(self, entry):
        bdec.DecodeError.__init__(self, entry)

    def __str__(self):
        return "Cannot reference non integer field '%s'" % self.entry

class UnknownReferenceError(BadReferenceError):
    def __init__(self, entry, name):
        bdec.DecodeError.__init__(self, entry)
        self.name = name

    def __str__(self):
        return "%s references unknown entry '%s'!" % (self.entry, self.name)

class _FailedToResolveError(Exception):
    def __init__(self, name):
        self.name = name

class Param(object):
    """Class to represent parameters passed into and out of decodes. """
    IN = "in"
    OUT = "out"

    def __init__(self, name, direction, type):
        self.name = name
        self.direction = direction

        assert isinstance(type, VariableType)
        self.type = type

    def __eq__(self, other):
        return self.name == other.name and self.direction == other.direction \
                and self.type == other.type

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "%s %s '%s'" % (self.type, self.direction, self.name)


class Local(object):
    """Object representing a local instance."""
    def __init__(self, name, type):
        self.name = name
        assert isinstance(type, VariableType)
        self.type = type

    def __eq__(self, other):
        return self.type == other.type and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "%s '%s'" % (self.type, self.name)


class _Parameters:
    """Interface for querying information about passed parameters"""
    def get_locals(self, entry):
        """Return an iterable of Local instances. """
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
                result.append(Local('should end', ShouldEndType()))
        return result

    def get_params(self, entry):
        """
        If an item is between a sequenceof and an end-sequenceof entry, it
        should pass an output 'should_end' context item.
        """
        if self._has_context_lookup[entry]:
            return set([Param('should end', Param.OUT,  ShouldEndType())])
        return set()

    def get_passed_variables(self, entry, child):
        # The passed parameter names don't change for 'should end' variables;
        # the name is the same in both parent & child.
        return self.get_params(child.entry)

    def is_end_sequenceof(self, entry):
        return entry in self._end_sequenceof_entries


def _get_reference_name(reference):
    if isinstance(reference, expr.ValueResult):
        return reference.name
    elif isinstance(reference, expr.LengthResult):
        return reference.name + ' length'
    raise Exception("Unknown reference type '%s'" % reference)


class _VariableParam:
    def __init__(self, reference, direction, type):
        assert isinstance(reference, expr.ValueResult) or isinstance(reference, expr.LengthResult)
        self.reference = reference
        self.direction = direction
        self.types = set()
        if type is not None:
            self.types.add(type)

    def __hash__(self):
        return hash(self.reference.name)

    def __eq__(self, other):
        return type(self.reference) == type(other.reference) and self.reference.name == other.reference.name and self.direction == other.direction

    def __str__(self):
        return "%s %s" % (self.direction, self.reference)

    def get_type(self):
        if len(self.types) > 1:
            type = MultiSourceType(self.types)
        elif len(self.types) == 1:
            type = iter(self.types).next()
        else:
            raise _FailedToResolveError(self.reference.name)
        return type

    def get_param(self):
        """Construct a parameter from this internal parameter type."""
        return Param(_get_reference_name(self.reference), self.direction, self.get_type())


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

        for entry, references in unreferenced_entries.iteritems():
            for param in self._params[entry]:
                if not param.types:
                    raise UnknownReferenceError(entry, iter(references).next().name)

    def _collect_references(self, expression):
        """
        Walk an expression object, collecting all named references.
        
        Returns a list of ValueResult / LengthResult instances.
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
        if isinstance(entry, sof.SequenceOf) and entry.count is not None:
            unreferenced_entries[entry].update(self._collect_references(entry.count))

        # Store the names the child doesn't know about (ie: names that must be
        # resolved for this entry to decode)
        child_unknowns = set()
        for child in entry.children:
            child_unknowns.update(unreferenced_entries[child.entry])

        if isinstance(entry, seq.Sequence) and entry.value is not None:
            child_unknowns.update(self._collect_references(entry.value))
        for constraint in entry.constraints:
            child_unknowns.update(self._collect_references(constraint.limit))

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
                param_type = self._add_out_params(entry, unknown)
                self._populate_child_input_parameter_type(entry, unknown.name, param_type)

        for reference in unreferenced_entries[entry]:
            self._params[entry].add(_VariableParam(reference, Param.IN, None))

    def _populate_child_input_parameter_type(self, entry, name, param_type):
        """ Set the input parameter type of any of children that use the named
        parameter."""
        for child in entry.children:
            for param in self._params[child.entry]:
                if param.reference.name == name and param.direction == Param.IN:
                    param.types.add(param_type)
                    self._populate_child_input_parameter_type(child.entry, name, param_type)

    def _get_local_reference(self, entry, child, param):
        """Get the local of a parameter used by a child entry.

        Return either a bdec.expression.ValueResult or a
        bdec.expression.LengthResult.
        """
        try:
            name = self._local_child_param_name[entry][child][param.reference.name]
        except KeyError:
            name = param.reference.name

        # Create a new instance of the expression reference, using the new name
        return type(param.reference)(name)

    def _add_reference(self, entry, reference):
        param_type = EntryValueType(entry)
        self._params[entry].add(_VariableParam(reference, Param.OUT, param_type))
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
                raise BadReferenceError(entry)
        elif isinstance(entry, chc.Choice):
            # When referencing a choice, we want to attempt to reference each
            # of its children.
            child_params = self._local_child_param_name.setdefault(entry, {})
            for child in entry.children:
                child_reference = type(reference)(child.entry.name)
                self._add_reference(child.entry, child_reference)

                local_names = child_params.setdefault(child, {})
                local_names[child_reference.name] = reference.name
        else:
            raise BadReferenceError(entry)
        return param_type

    def _add_out_params(self, entry, reference):
        """
        Drill down into the children of 'entry', adding output params to 'name'.

        entry -- An instance of bdec.entry.Entry
        reference -- An instance of either bdec.expression.ValueResult or
            bdec.expression.LengthResult.
        return -- A VariableType instance representing the type being referenced.
        """
        if isinstance(entry, chc.Choice):
            # The option names aren't specified in a choice expression
            option_types = []
            for child in entry.children:
                child_type = self._add_out_params(child.entry, reference)
                self._params[child.entry].add(_VariableParam(reference, Param.OUT, child_type))
                option_types.append(child_type)
            result =  MultiSourceType(option_types)
        elif isinstance(entry, seq.Sequence):
            child_params = self._local_child_param_name.setdefault(entry, {})

            # Detect the child name, and the name of the reference under that child.
            names = reference.name.split('.')
            child_name = names[0]
            sub_name = ".".join(names[1:])

            for child in entry.children:
                local_names = child_params.setdefault(child, {})
                if child.name == reference.name:
                    # This parameter references the value / length of the child
                    # item. As the name might be different between parent and
                    # child, use the childs name.
                    child_reference = type(reference)(child.entry.name)
                    local_names[child.entry.name] = reference.name
                    if isinstance(child_reference, expr.ValueResult):
                        result = self._add_reference(child.entry, child_reference)
                    else:
                        result = EntryLengthType(child.entry)
                        self._params[child.entry].add(_VariableParam(child_reference, Param.OUT, result))
                        self._referenced_lengths.add(child.entry)
                    break
                elif child.name == child_name:
                    # We found a child item that knows about this parameter
                    local_names[sub_name] = reference.name
                    child_reference = type(reference)(sub_name)

                    result = self._add_out_params(child.entry, child_reference)
                    self._params[child.entry].add(_VariableParam(child_reference, Param.OUT, result))
                    break
            else:
                raise ent.MissingExpressionReferenceError(entry, reference.name)
        else:
            # We don't know how to resolve a reference to this type of entry!
            raise BadReferenceError(entry)
        return result

    def get_locals(self, entry):
        """
        Get the names of local variables used when decoding an entry.

        Local variables are all child outputs that aren't an output of the
        entry.
        """
        params = self._params[entry]
        locals = {}
        for child in entry.children:
            for child_param in self._params[child.entry]:
                if child_param.direction == Param.OUT:
                    local = self._get_local_reference(entry, child, child_param)
                    if _VariableParam(local, child_param.direction, None) not in params:
                        name = _get_reference_name(local)
                        locals.setdefault(name, []).append(child_param.get_type())
        result = []
        for name, types in locals.items():
            if len(types) == 1:
                type = types[0]
            else:
                type = MultiSourceType(types)
            result.append(Local(name, type))
        result.sort(key=lambda a:a.name)
        return result

    def get_params(self, entry):
        """
        Get an iterator to all parameters passed to an entry due to value references.
        """
        assert isinstance(entry, bdec.entry.Entry)
        params = list(self._params[entry])
        params.sort(key=lambda a:a.reference.name)
        try:
            return [param.get_param() for param in params]
        except _FailedToResolveError, ex:
            raise UnknownReferenceError(entry, ex.name)

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
            yield Param(_get_reference_name(local), param.direction, param.get_type())

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
        self._common = entries[:]
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

        # This entry isn't yet calculated; do so now.
        self._has_data[entry] = not entry.is_hidden()
        stack.append(entry)
        for child in entry.children:
             self._populate(child.entry, stack, intermediates)
        stack.remove(entry)

        if not isinstance(entry, chc.Choice) and not entry.is_hidden():
            # We are visible; check to see if either we (or any of our
            # children) contain data.
            for child in entry.children:
                if self._has_data[child.entry]:
                    break
            else:
                # None of the children contain data; this entry will only contain
                # data if implicitly has data itself.
                if isinstance(entry, fld.Field) or \
                        (isinstance(entry, seq.Sequence) and entry.value is not None):
                    # This entry's children don't contain data, but it appears to
                    # have some implicit data.
                    for constraint in entry.constraints:
                        if isinstance(constraint, Equals):
                            # The 'implicit' data has an expected value, so it
                            # isn't considered as new data.
                            self._has_data[entry] = False
                            break
                elif isinstance(entry, sof.SequenceOf) and \
                        not ent.is_hidden(entry.children[0].name):
                    self._has_data[entry] = True
                else:
                    self._has_data[entry] = False

        if not self._has_data[entry]:
            self._hide_children(entry)

    def _hide_children(self, entry):
        """Hide all of the non-common children of an entry.

        If an entry doesn't contain data, nor should any of its non common
        children. This can happen when a parent entry is hidden, but the
        child entries are visible.
        """
        self._has_data[entry] = False
        for child in entry.children:
            if child.entry not in self._common:
                self._hide_children(child.entry)

    def contains_data(self, entry):
        """Does an entry contain data."""
        return not ent.is_hidden(entry.name) and self._has_data[entry]

    def child_has_data(self, child):
        """Does a bdec.entry.Child instance contain data.

        This is different from contains_data when a referenced entry has been
        hidden."""
        return not ent.is_hidden(child.name) and self._has_data[child.entry]


class ResultParameters(_Parameters):
    """
    A class that generates the parameters used when passing the decode result
    out of the decode function as a parameter.
    """
    def __init__(self, entries):
        self._checker = DataChecker(entries)

    def get_locals(self, entry):
        locals = []
        for child in entry.children:
            if self._checker.contains_data(child.entry) and not self._checker.child_has_data(child):
                # There is a common entry that appears visible, but has been
                # hidden locally. We store this entry as a local.
                locals.append(Local('unused %s' % child.name, EntryType(child.entry)))
        return locals

    def get_params(self, entry):
        if not self._checker.contains_data(entry):
            return []
        return [Param('result', Param.OUT, EntryType(entry))]

    def get_passed_variables(self, entry, child):
        if not self._checker.contains_data(child.entry):
            return []
        if not self._checker.child_has_data(child):
            # A visible common entry has been hidden locally.
            return [Param('unused %s' % child.name, Param.OUT, EntryType(child.entry))]
        return [Param('unknown', Param.OUT, EntryType(child.entry))]


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

