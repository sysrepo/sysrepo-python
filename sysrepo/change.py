# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

from typing import Any, Dict, List, Optional

import libyang

from _sysrepo import lib


# ------------------------------------------------------------------------------
class Change:

    __slots__ = ("xpath",)

    def __init__(self, xpath: str):
        self.xpath = xpath

    class Skip(Exception):
        """
        Risen when a change should be skipped.
        """

        pass

    @staticmethod
    def parse(
        operation: int,
        node: libyang.DNode,
        prev_val: str,
        prev_list: str,
        prev_dflt: bool,
        include_implicit_defaults: bool = True,
    ) -> "Change":
        """
        Parse an operation code and values from libsysrepo.so and return a Change
        subclass instance.

        Meaning of parameters varies based on the operation:

        SR_OP_CREATED
            node is the created node, for user-ordered lists either prev_value or
            prev_list is always set with meaning similar to SR_OP_MOVED.
        SR_OP_MODIFIED
            node is the modified node, prev_value is set to the previous value of the
            leaf, prev_dflt is set if the previous leaf value was the default.
        SR_OP_DELETED
            node is the deleted node.
        SR_OP_MOVED
            node is the moved (leaf-)list instance, for user-ordered lists either
            prev_value (leaf-list) or prev_list (list) is set to the preceding instance
            unless the node is the first, when they are set to "" (empty string).

        :arg operation:
            The operation code.
        :arg node:
            Affected data node always with all parents, depends on the operation.
        :arg prev_val:
            Previous value, depends on the operation.
        :arg prev_list:
            Previous list keys predicate (`[key1="val1"][key2="val2"]...`), depends on
            the operation.
        :arg prev_dflt:
            Previous value default flag, depends on the operation.
        :arg include_implicit_defaults:
            Include implicit default values into the data dictionaries.
        """
        if operation == lib.SR_OP_CREATED:
            if not node.should_print(
                include_implicit_defaults=include_implicit_defaults
            ):
                raise Change.Skip()
            return ChangeCreated(
                node.path(),
                _node_value(node, include_implicit_defaults),
                after=_after_key(node, prev_val, prev_list),
            )
        if operation == lib.SR_OP_MODIFIED:
            return ChangeModified(
                node.path(),
                _node_value(node, include_implicit_defaults),
                prev_val=prev_val,
                prev_dflt=prev_dflt,
            )
        if operation == lib.SR_OP_DELETED:
            return ChangeDeleted(node.path())
        if operation == lib.SR_OP_MOVED:
            return ChangeMoved(
                node.path(),
                after=_after_key(node, prev_val, prev_list),
            )
        raise ValueError("unknown change operation: %s" % operation)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, type(self)) and self.xpath == other.xpath

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    __hash__ = None  # not hashable

    def __repr__(self) -> str:
        return "%s(%s)" % (type(self).__name__, self)

    def __str__(self) -> str:
        return self.xpath


# ------------------------------------------------------------------------------
class ChangeCreated(Change):

    __slots__ = Change.__slots__ + ("value", "after")

    def __init__(self, xpath: str, value: Any, after: Optional[str] = None):
        super().__init__(xpath)
        self.value = value
        self.after = after

    def __eq__(self, other: Any) -> bool:
        return (
            super().__eq__(other)
            and other.after == self.after
            and other.value == self.value
        )

    def __str__(self) -> str:
        if self.after == ():
            return "%s: %r: FIRST" % (self.xpath, self.value)
        if self.after is not None:
            return "%s: %r: AFTER %r" % (self.xpath, self.value, self.after)
        return "%s: %r" % (self.xpath, self.value)


# ------------------------------------------------------------------------------
class ChangeModified(Change):

    __slots__ = Change.__slots__ + ("value", "prev_val", "prev_dflt")

    def __init__(self, xpath: str, value: Any, prev_val: str, prev_dflt: bool = False):
        super().__init__(xpath)
        self.value = value
        self.prev_val = prev_val
        self.prev_dflt = prev_dflt

    def __eq__(self, other: Any) -> bool:
        return (
            super().__eq__(other)
            and other.prev_dflt == self.prev_dflt
            and other.prev_val == self.prev_val
            and other.value == self.value
        )

    def __str__(self) -> str:
        return "%s: %r -> %r" % (self.xpath, self.prev_val, self.value)


# ------------------------------------------------------------------------------
class ChangeDeleted(Change):
    pass


# ------------------------------------------------------------------------------
class ChangeMoved(Change):

    __slots__ = Change.__slots__ + ("after",)

    def __init__(self, xpath: str, after: str):
        super().__init__(xpath)
        self.after = after

    def __eq__(self, other: Any) -> bool:
        return super().__eq__(other) and other.after == self.after

    def __str__(self) -> str:
        if self.after:
            where = "AFTER %r" % (self.after,)
        else:
            where = "FIRST"
        return "%s: %s" % (self.xpath, where)


# -------------------------------------------------------------------------------------
def update_config_cache(conf: Dict, changes: List[Change]) -> None:
    """
    Maintain a configuration dict from a list of Change objects.

    This function is intended to be used in module change callbacks if they want to
    preserve a full view of all the configuration without asking sysrepo everytime the
    callback is invoked.

    :arg conf:
        The cached config dict to update.
    :arg changes:
        The list of changes passed to module change callbacks.
    """
    for c in changes:
        if isinstance(c, ChangeCreated):
            libyang.xpath_set(conf, c.xpath, c.value, after=c.after)
        elif isinstance(c, ChangeModified):
            libyang.xpath_set(conf, c.xpath, c.value)
        elif isinstance(c, ChangeMoved):
            libyang.xpath_move(conf, c.xpath, c.after)
        elif isinstance(c, ChangeDeleted):
            libyang.xpath_del(conf, c.xpath)


# -------------------------------------------------------------------------------------
def _node_value(node: libyang.DNode, include_implicit_defaults: bool = True) -> Any:
    """
    Extract a python value from a libyang.DNode.
    """
    if isinstance(node, (libyang.DLeaf, libyang.DLeafList)):
        return node.value()
    dic = node.print_dict(
        absolute=False, include_implicit_defaults=include_implicit_defaults
    )
    if not dic:
        return dic
    dic = next(iter(dic.values()))  # trim first level of dict with only key name
    if isinstance(node, libyang.DList):
        dic = next(iter(dic))  # only preserve the list element dict
    return dic


# -------------------------------------------------------------------------------------
def _after_key(
    node: libyang.DNode, prev_val: Optional[str], prev_list: Optional[str]
) -> Optional[str]:
    """
    Get the proper `after` key value based on the node type.
    """
    if isinstance(node, libyang.DLeafList):
        return prev_val
    if isinstance(node, libyang.DList):
        return prev_list
    return None
