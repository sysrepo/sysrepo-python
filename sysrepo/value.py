# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

from typing import Any, Optional

from _sysrepo import lib
from .util import c2str


# ------------------------------------------------------------------------------
class Value:
    """
    Abstract class for sysrepo value containing the xpath.
    """

    sr_type = None
    xpath = None
    value_field = None

    def __new__(cls, *args):
        """
        Take 2 arguments by default: ``(python_value, xpath)``.

        If the class holds no value (Container, ContainerPresence & List),
        only take 1 argument: ``xpath``.

        For all cases, xpath is optional. If not specified, it is initialized
        to ``None``.
        """
        if cls is Value:
            raise TypeError("Value cannot be instanciated directly, use subclasses")
        i = 0
        new_args = [cls]
        if cls.value_field is not None:
            try:
                new_args.append(args[i])
                i += 1
            except IndexError:
                raise TypeError("Unspecified value") from None

        self = super().__new__(*new_args)
        try:
            self.xpath = args[i]
        except IndexError:
            pass

        return self

    def __repr__(self) -> str:
        if self.value_field is not None:
            if self.xpath is not None:
                s = "%s: %s" % (self.xpath, self)
            else:
                s = str(self)
        else:
            s = self.xpath or ""
        return "%s(%s)" % (type(self).__name__, s)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self))
            and other.xpath == self.xpath
            and other.value == self.value
        )

    def __hash__(self) -> int:
        return hash((type(self), self.xpath, self.value))

    @property
    def value(self) -> Any:
        if self.value_field is not None:
            return type(self).__bases__[-1](self)
        return None

    SR_TYPE_CLASSES = {}

    @staticmethod
    def register(subclass):
        Value.SR_TYPE_CLASSES[subclass.sr_type] = subclass
        return subclass

    @staticmethod
    def parse(cdata) -> Optional["Value"]:
        """
        Parse a 'sr_value_t *' returned by libsysrepo.so and return an instance
        of the correct Value subclass.
        """
        if not cdata:
            return None
        if cdata.type not in Value.SR_TYPE_CLASSES:
            raise TypeError("unknown value type: %r" % cdata.type)
        value_cls = Value.SR_TYPE_CLASSES[cdata.type]
        xpath = c2str(cdata.xpath)
        if value_cls.value_field is not None:
            val = getattr(cdata.data, value_cls.value_field)
            if issubclass(value_cls, str):
                val = c2str(val)
            return value_cls(val, xpath)
        return value_cls(xpath)


# ------------------------------------------------------------------------------
@Value.register
class List(Value):
    sr_type = lib.SR_LIST_T


@Value.register
class Container(Value):
    sr_type = lib.SR_CONTAINER_T


@Value.register
class ContainerPresence(Value):
    sr_type = lib.SR_CONTAINER_PRESENCE_T


@Value.register
class LeafEmpty(Value):
    sr_type = lib.SR_LEAF_EMPTY_T


@Value.register
class Int8(Value, int):
    sr_type = lib.SR_INT8_T
    value_field = "int8_val"


@Value.register
class Int16(Value, int):
    sr_type = lib.SR_INT16_T
    value_field = "int16_val"


@Value.register
class Int32(Value, int):
    sr_type = lib.SR_INT32_T
    value_field = "int32_val"


@Value.register
class Int64(Value, int):
    sr_type = lib.SR_INT64_T
    value_field = "int64_val"


@Value.register
class UInt8(Value, int):
    sr_type = lib.SR_UINT8_T
    value_field = "uint8_val"


@Value.register
class UInt16(Value, int):
    sr_type = lib.SR_UINT16_T
    value_field = "uint16_val"


@Value.register
class UInt32(Value, int):
    sr_type = lib.SR_UINT32_T
    value_field = "uint32_val"


@Value.register
class UInt64(Value, int):
    sr_type = lib.SR_UINT64_T
    value_field = "uint64_val"


@Value.register
class String(Value, str):
    sr_type = lib.SR_STRING_T
    value_field = "string_val"


@Value.register
class Bits(Value, str):
    sr_type = lib.SR_BITS_T
    value_field = "bits_val"


@Value.register
class Enum(Value, str):
    sr_type = lib.SR_ENUM_T
    value_field = "enum_val"


@Value.register
class Binary(Value, str):
    sr_type = lib.SR_BINARY_T
    value_field = "binary_val"


@Value.register
class AnyXML(Value, str):
    sr_type = lib.SR_ANYXML_T
    value_field = "anyxml_val"


@Value.register
class AnyData(Value, str):
    sr_type = lib.SR_ANYDATA_T
    value_field = "anydata_val"


@Value.register
class IdentityRef(Value, str):
    sr_type = lib.SR_IDENTITYREF_T
    value_field = "identityref_val"


@Value.register
class InstanceId(Value, str):
    sr_type = lib.SR_INSTANCEID_T
    value_field = "instanceid_val"


@Value.register
class Decimal64(Value, float):
    sr_type = lib.SR_DECIMAL64_T
    value_field = "decimal64_val"


@Value.register
class Bool(Value, int):  # bool cannot be subclassed...
    sr_type = lib.SR_BOOL_T
    value_field = "bool_val"

    @property
    def value(self) -> bool:
        return bool(self)

    def __str__(self) -> str:
        return "True" if self else "False"
