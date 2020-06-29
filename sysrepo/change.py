# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

from typing import Any, Optional

from _sysrepo import lib
from .value import Value


# ------------------------------------------------------------------------------
class Change:
    @staticmethod
    def parse(operation: int, old=None, new=None) -> "Change":
        """
        Parse an operation code and values from libsysrepo.so and return a Change
        subclass instance.

        :arg operation:
            The operation code.
        :arg "sr_value_t *" old:
            The old value C pointer returned by libsysrepo.so. Can be ffi.NULL.
        :arg "sr_value_t *" new:
            The new value C pointer returned by libsysrepo.so. Can be ffi.NULL.
        """
        old = Value.parse(old)
        new = Value.parse(new)
        if operation == lib.SR_OP_CREATED:
            return ChangeCreated(new)
        if operation == lib.SR_OP_MODIFIED:
            return ChangeModified(old, new)
        if operation == lib.SR_OP_DELETED:
            return ChangeDeleted(old)
        if operation == lib.SR_OP_MOVED:
            return ChangeMoved(new, after=old)
        raise ValueError("unknown change operation: %s" % operation)

    def xpath(self) -> str:
        raise NotImplementedError()

    def __repr__(self) -> str:
        return "%s(%s)" % (type(self).__name__, self)


# ------------------------------------------------------------------------------
class ChangeCreated(Change):

    operation = lib.SR_OP_CREATED
    __slots__ = ("value",)

    def __init__(self, value: Value):
        self.value = value

    def xpath(self) -> str:
        return self.value.xpath

    def __hash__(self) -> int:
        return hash((self.operation, self.value))

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, type(self)) and other.value == self.value

    def __str__(self) -> str:
        return repr(self.value)


# ------------------------------------------------------------------------------
class ChangeModified(Change):

    operation = lib.SR_OP_MODIFIED
    __slots__ = ("old", "new")

    def __init__(self, old: Value, new: Value):
        self.old = old
        self.new = new

    def xpath(self) -> str:
        return self.new.xpath

    def __hash__(self) -> int:
        return hash((self.operation, self.old, self.new))

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self))
            and other.old == self.old
            and other.new == self.new
        )

    def __str__(self) -> str:
        return "%r -> %s" % (self.old, self.new)


# ------------------------------------------------------------------------------
class ChangeDeleted(Change):

    operation = lib.SR_OP_DELETED
    __slots__ = ("value",)

    def __init__(self, value: Value):
        self.value = value

    def xpath(self) -> str:
        return self.value.xpath

    def __hash__(self) -> int:
        return hash((self.operation, self.value))

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, type(self)) and other.value == self.value

    def __str__(self) -> str:
        return repr(self.value)


# ------------------------------------------------------------------------------
class ChangeMoved(Change):

    operation = lib.SR_OP_MOVED
    __slots__ = ("value", "after")

    def __init__(self, value: Value, after: Optional[Value] = None):
        self.value = value
        self.after = after

    def xpath(self) -> str:
        return self.value.xpath

    def __hash__(self) -> int:
        return hash((self.operation, self.value, self.after))

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, type(self))
            and other.value == self.value
            and other.after == self.after
        )

    def __str__(self) -> str:
        if self.after is not None:
            where = "AFTER %r" % self.after
        else:
            where = "FIRST"
        return "%r: %s" % (self.value, where)
