# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import inspect
import logging
from typing import Any, Callable, Dict, Iterator, List, Optional

import libyang

from _sysrepo import ffi, lib
from .change import Change
from .errors import (
    SysrepoInternalError,
    SysrepoNotFoundError,
    SysrepoUnsupportedError,
    check_call,
)
from .subscription import Subscription
from .util import c2str, str2c
from .value import Value


LOG = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
class SysrepoSession:
    """
    Python representation of `sr_session_ctx_t *`.

    .. attention::

        Do not instantiate this class manually, use `SysrepoConnection.start_session`.
    """

    __slots__ = ("cdata", "is_implicit", "subscriptions")

    # begin: general
    def __init__(self, cdata, implicit: bool = False):
        """
        :arg "sr_session_ctx_t *" cdata:
            The session pointer allocated by :func:`SysrepoConnection.start_session`.
        :arg implicit:
            Used to identify sessions provided in subscription callbacks.
        """
        self.cdata = cdata
        self.is_implicit = implicit
        self.subscriptions = []

    def __enter__(self) -> "SysrepoSession":
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.stop()

    def stop(self) -> None:
        """
        Stop current session and releases resources tied to the session.

        Also releases any locks held and frees subscriptions created (only) by this
        session.
        """
        if self.cdata is None:
            return  # already stopped
        if self.is_implicit:
            raise SysrepoUnsupportedError("implicit sessions cannot be stopped")
        while self.subscriptions:
            sub = self.subscriptions.pop()
            try:
                sub.unsubscribe()
            except Exception:
                LOG.exception("Subscription.unsubscribe failed")
        try:
            check_call(lib.sr_session_stop, self.cdata)
        finally:
            self.cdata = None

    def get_datastore(self) -> str:
        """
        Get the datastore a session operates on.

        :returns str:
            The datastore name.
        """
        return datastore_name(lib.sr_session_get_ds(self.cdata))

    def switch_datastore(self, datastore: str) -> None:
        """
        Change datastore which the session operates on. All subsequent calls will be
        issued on the chosen datastore. Previous calls are not affected (previous
        subscriptions, for instance).

        :arg str datastore:
            New datastore that will be operated on. Can be one of `running`,
            `startup`, `operational` or `candidate`.
        """
        if self.is_implicit:
            raise SysrepoUnsupportedError(
                "cannot change datastore of implicit sessions"
            )
        ds = datastore_value(datastore)
        check_call(lib.sr_session_switch_ds, self.cdata, ds)

    def set_error(self, xpath: Optional[str], message: str):
        """
        Set detailed error information into provided session. Used to notify the client
        library about errors that occurred in the application code. Does not print the
        message.

        Intended for change, RPC/action, or operational callbacks to be used on the
        provided session.

        :arg str xpath:
            The path where the error occured. May be `None`.
        :arg str message:
            The detailed error message.
        """
        if not self.is_implicit:
            raise SysrepoUnsupportedError("can only report errors on implicit sessions")
        check_call(
            lib.sr_set_error, self.cdata, str2c(xpath), str2c("%s"), str2c(message)
        )

    def get_ly_ctx(self) -> libyang.Context:
        """
        :returns:
            The libyang context object associated with this session.
        """
        conn = lib.sr_session_get_connection(self.cdata)
        if not conn:
            raise SysrepoInternalError("sr_session_get_connection failed")
        ctx = lib.sr_get_context(conn)
        if not ctx:
            raise SysrepoInternalError("sr_get_context failed")
        return libyang.Context(cdata=ctx)

    # end: general

    # begin: subscription
    ModuleChangeCallbackType = Callable[[str, int, List[Change], Any], None]
    """
    Callback to be called when the change in the datastore occurs.

    :arg event:
        Type of the callback event that has occurred. Can be one of: "update", "change",
        "done", "abort", "enabled".
    :arg req_id:
        Request ID unique for the specific module name. Connected events for one request
        ("change" and "done" for example) have the same request ID.
    :arg changes:
        List of `sysrepo.Change` objects representing what parts of the configuration
        have changed.
    :arg private_data:
        Private context opaque to sysrepo used when subscribing.

    When event is one of ("update", "change"), if the callback raises an exception, the
    changes will be rejected and the error will be forwarded to the client that made the
    change. If the exception is a subclass of `SysrepoError`, the traceback will not be
    sent to the logging system. For consistency and to avoid confusion with unexpected
    errors, the callback should raise explicit `SysrepoValidationFailedError` exceptions
    to reject changes.
    """

    def subscribe_module_change(
        self,
        module: str,
        xpath: Optional[str],
        callback: ModuleChangeCallbackType,
        *,
        priority: int = 0,
        no_thread: bool = False,
        passive: bool = False,
        done_only: bool = False,
        enabled: bool = False,
        private_data: Any = None,
        asyncio_register: bool = False,
        include_implicit_defaults: bool = True
    ) -> None:
        """
        Subscribe for changes made in the specified module.

        :arg module:
            Name of the module of interest for change notifications.
        :arg xpath:
            Optional xpath further filtering the changes that will be handled
            by this subscription.
        :arg callback:
            Callback to be called when the change in the datastore occurs.
        :arg priority:
            Specifies the order in which the callbacks (**within module**) will
            be called.
        :arg no_thread:
            There will be no thread created for handling this subscription
            meaning no event will be processed! Default to `True` if
            asyncio_register is `True`.
        :arg passive:
            The subscriber is not the "owner" of the subscribed data tree, just
            a passive watcher for changes.
        :arg done_only:
            The subscriber does not support verification of the changes and
            wants to be notified only after the changes has been applied in the
            datastore, without the possibility to deny them.
        :arg enabled:
            The subscriber wants to be notified about the current configuration
            at the moment of subscribing.
        :arg private_data:
            Private context passed to the callback function, opaque to sysrepo.
        :arg asyncio_register:
            Add the created subscription event pipe into asyncio event loop
            monitored read file descriptors. Implies `no_thread=True`.
        :arg include_implicit_defaults:
            Include implicit default nodes in changes.
        """
        if self.is_implicit:
            raise SysrepoUnsupportedError("cannot subscribe with implicit sessions")
        _check_subscription_callback(callback, self.ModuleChangeCallbackType)

        sub = Subscription(
            callback,
            private_data,
            asyncio_register=asyncio_register,
            include_implicit_defaults=include_implicit_defaults,
        )
        sub_p = ffi.new("sr_subscription_ctx_t **")

        if asyncio_register:
            no_thread = True  # we manage our own event loop
        flags = _subscribe_flags(
            no_thread=no_thread, passive=passive, done_only=done_only, enabled=enabled
        )

        check_call(
            lib.sr_module_change_subscribe,
            self.cdata,
            str2c(module),
            str2c(xpath),
            lib.srpy_module_change_cb,
            sub.handle,
            priority,
            flags,
            sub_p,
        )
        sub.init(sub_p[0])

        self.subscriptions.append(sub)

    OperDataCallbackType = Callable[[str, Any], Optional[Dict]]
    """
    Callback to be called when the operational data are requested.

    :arg xpath:
        The XPath requested by a client. Can be None if the client requested for all the
        module operational data.
    :arg private_data:
        Private context opaque to sysrepo used when subscribing.

    The callback is expected to return a python dictionary containing the operational
    data. The dictionary should be in the libyang "dict" format. It will be parsed to a
    libyang lyd_node before returning to sysrepo using `libyang.Module.parse_data_dict`.
    If the callback returns `None`, nothing is returned to sysrepo. If the callback
    raises an exception, the error message is forwarded to the client that requested for
    data. If the exception is a subclass of `SysrepoError`, no traceback is sent to the
    logging system.
    """

    def subscribe_oper_data_request(
        self,
        module: str,
        xpath: str,
        callback: OperDataCallbackType,
        *,
        no_thread: bool = False,
        private_data: Any = None,
        asyncio_register: bool = False,
        strict: bool = False
    ) -> None:
        """
        Register for providing operational data at the given xpath.

        :arg module:
            Name of the affected module.
        :arg xpath:
            Xpath identifying the subtree which the provider is able to provide.
            Predicates can be used to provide only specific instances of nodes.
        :arg callback:
            Callback to be called when the operational data for the given xpath are
            requested.
        :arg no_thread:
            There will be no thread created for handling this subscription meaning no
            event will be processed! Default to `True` if asyncio_register is `True`.
        :arg private_data:
            Private context passed to the callback function, opaque to sysrepo.
        :arg asyncio_register:
            Add the created subscription event pipe into asyncio event loop monitored
            read file descriptors. Implies `no_thread=True`.
        :arg strict:
            Reject the whole data returned by callback if it contains elements without
            schema definition.
        """
        if self.is_implicit:
            raise SysrepoUnsupportedError("cannot subscribe with implicit sessions")
        _check_subscription_callback(callback, self.OperDataCallbackType)

        sub = Subscription(
            callback, private_data, asyncio_register=asyncio_register, strict=strict
        )
        sub_p = ffi.new("sr_subscription_ctx_t **")

        if asyncio_register:
            no_thread = True  # we manage our own event loop
        flags = _subscribe_flags(no_thread=no_thread)

        check_call(
            lib.sr_oper_get_items_subscribe,
            self.cdata,
            str2c(module),
            str2c(xpath),
            lib.srpy_oper_data_cb,
            sub.handle,
            flags,
            sub_p,
        )
        sub.init(sub_p[0])

        self.subscriptions.append(sub)

    RpcCallbackType = Callable[[str, Dict, str, Any], Optional[Dict]]
    """
    Callback to be called when the RPC/action is invoked.

    :arg xpath:
        The full data path to the invoked RPC/action. When it is an RPC, the form is
        `/prefix:rpc-name`. When it is an action, it is the full data path with all
        parent nodes: `/prefix:container/list[key="val"]/action-name`.
    :arg input_params:
        The input arguments in a python dictionary. The contents are limited to the
        children of the "input" node. For example, with a YANG rpc defined like this::

            rpc rpc-name {
              input {
                leaf param1 {
                  type uint32;
                }
                leaf param2 {
                  type string;
                }
              }
              output {
                leaf foo {
                  type int8;
                }
                leaf bar {
                  type string;
                }
              }
            }

        The input_params dict may look like this::

            {'param1': 42, 'param2': 'foobar'}

        If there are no input parameters provided by the client, the dict will be empty.

        For actions, the xpath argument allows to determine the parent node of the
        action input parameters.
    :arg event:
        In most cases, it is always 'rpc'. When multiple callbacks are registered for
        the same RPC and one of the callbacks failed. The remainder of the callbacks
        will be called with 'abort'.
    :arg private_data:
        Private context opaque to sysrepo used when subscribing.

    The callback is expected to return a python dictionary containing the RPC output
    data. The dictionary should be in the libyang "dict" format and must only contain
    the actual output parameters without any parents. Using the previous example::

        {'foo': 47, 'bar': 'baz'}

    It will be passed to libyang.DRpc.merge_data_dict() to return output data to
    sysrepo. If the callback returns None, nothing is returned to sysrepo. If the
    callback raises an exception, the error message is forwarded to the client that
    called the RPC. If the exception is a subclass of SysrepoError, no traceback is sent
    to the logging system.
    """

    def subscribe_rpc_call(
        self,
        xpath: str,
        callback: RpcCallbackType,
        *,
        priority: int = 0,
        no_thread: bool = False,
        private_data: Any = None,
        asyncio_register: bool = False,
        strict: bool = False,
        include_implicit_defaults: bool = True
    ) -> None:
        """
        Subscribe for the delivery of an RPC/action.

        :arg xpath:
            XPath identifying the RPC/action. Any predicates are allowed.
        :arg callback:
            Callback to be called when the RPC/action is invoked.
        :arg priority:
            Specifies the order in which the callbacks (**within RPC/action**) will be
            called.
        :arg no_thread:
            There will be no thread created for handling this subscription meaning no
            event will be processed! Default to True if asyncio_register is True.
        :arg private_data:
            Private context passed to the callback function, opaque to sysrepo.
        :arg asyncio_register:
            Add the created subscription event pipe into asyncio event loop monitored
            read file descriptors. Implies no_thread=True.
        :arg strict:
            Reject the whole data returned by callback if it contains elements without
            schema definition.
        :arg include_implicit_defaults:
            Include implicit defaults into input parameters passed to callbacks.
        """
        if self.is_implicit:
            raise SysrepoUnsupportedError("cannot subscribe with implicit sessions")
        _check_subscription_callback(callback, self.RpcCallbackType)

        sub = Subscription(
            callback,
            private_data,
            asyncio_register=asyncio_register,
            strict=strict,
            include_implicit_defaults=include_implicit_defaults,
        )
        sub_p = ffi.new("sr_subscription_ctx_t **")

        if asyncio_register:
            no_thread = True  # we manage our own event loop
        flags = _subscribe_flags(no_thread=no_thread)

        check_call(
            lib.sr_rpc_subscribe_tree,
            self.cdata,
            str2c(xpath),
            lib.srpy_rpc_tree_cb,
            sub.handle,
            priority,
            flags,
            sub_p,
        )
        sub.init(sub_p[0])

        self.subscriptions.append(sub)

    NotificationCallbackType = Callable[[str, str, Dict, int, Any], None]
    """
    Callback to be called when a notification is received.

    :arg xpath:
        The full xpath to the received notification.
    :arg notification_type:
        Type of the notification event. Can be one of: "realtime", "replay",
        "replay_complete", "stop", "suspended", "resumed".
    :arg notification:
        The notification as a python dictionary. For example, with a YANG notification
        defined like this::

            notification some-notification {
              leaf param1 {
                type uint32;
              }
              leaf param2 {
                type string;
              }
            }

        The notification dict may look like this::

            {'param1': 42, 'param2': 'foobar'}

    :arg timestamp:
        Timestamp of the notification as an unsigned 32-bits integer.
    :arg private_data:
        Private context opaque to sysrepo used when subscribing.
    """

    def subscribe_notification(
        self,
        module: str,
        xpath: str,
        callback: NotificationCallbackType,
        *,
        start_time: int = 0,
        stop_time: int = 0,
        no_thread: bool = False,
        asyncio_register: bool = False,
        private_data: Any = None
    ) -> None:
        """
        Subscribe for the delivery of a notification.

        :arg module:
            Name of the module whose notifications to subscribe to.
        :arg xpath:
            XPath identifying the notification.
        :arg callback:
            Callback to be called when the notification is received.
        :arg start_time:
            Optional start time of the subscription. Used for replaying stored
            notifications.
        :arg stop_time:
            Optional stop time ending the notification subscription.
        :arg no_thread:
            There will be no thread created for handling this subscription meaning no
            event will be processed! Default to True if asyncio_register is True.
        :arg asyncio_register:
            Add the created subscription event pipe into asyncio event loop monitored
            read file descriptors. Implies no_thread=True.
        :arg private_data:
            Private context passed to the callback function, opaque to sysrepo.
        """

        if self.is_implicit:
            raise SysrepoUnsupportedError("cannot subscribe with implicit sessions")
        _check_subscription_callback(callback, self.NotificationCallbackType)

        sub = Subscription(
            callback,
            private_data,
            asyncio_register=asyncio_register,
        )

        sub_p = ffi.new("sr_subscription_ctx_t **")

        if asyncio_register:
            no_thread = True  # we manage our own event loop

        flags = _subscribe_flags(no_thread=no_thread)

        check_call(
            lib.sr_event_notif_subscribe_tree,
            self.cdata,
            str2c(module),
            str2c(xpath),
            start_time,
            stop_time,
            lib.srpy_event_notif_tree_cb,
            sub.handle,
            flags,
            sub_p,
        )
        sub.init(sub_p[0])

        self.subscriptions.append(sub)

    # end: subscription

    # begin: changes
    def get_changes(
        self, xpath: str, include_implicit_defaults: bool = True
    ) -> Iterator[Change]:
        """
        Return an iterator that will yield all pending changes in the current session.

        :arg xpath:
            Xpath selecting the requested changes. Be careful, you must select all the
            changes, not just subtrees! To get a full change subtree `//.` can be
            appended to the XPath.
        :arg include_implicit_defaults:
            Include implicit default nodes.

        :returns:
            An iterator that will yield `sysrepo.Change` objects.
        """
        iter_p = ffi.new("sr_change_iter_t **")

        check_call(lib.sr_get_changes_iter, self.cdata, str2c(xpath), iter_p)

        op_p = ffi.new("sr_change_oper_t *")
        node_p = ffi.new("struct lyd_node **")
        prev_val_p = ffi.new("char **")
        prev_list_p = ffi.new("char **")
        prev_dflt_p = ffi.new("bool *")
        ctx = self.get_ly_ctx()

        try:
            ret = check_call(
                lib.sr_get_change_tree_next,
                self.cdata,
                iter_p[0],
                op_p,
                node_p,
                prev_val_p,
                prev_list_p,
                prev_dflt_p,
                valid_codes=(lib.SR_ERR_OK, lib.SR_ERR_NOT_FOUND),
            )
            while ret == lib.SR_ERR_OK:
                try:
                    yield Change.parse(
                        operation=op_p[0],
                        node=libyang.DNode.new(ctx, node_p[0]),
                        prev_val=c2str(prev_val_p[0]),
                        prev_list=c2str(prev_list_p[0]),
                        prev_dflt=bool(prev_dflt_p[0]),
                        include_implicit_defaults=include_implicit_defaults,
                    )
                except Change.Skip:
                    pass
                ret = check_call(
                    lib.sr_get_change_tree_next,
                    self.cdata,
                    iter_p[0],
                    op_p,
                    node_p,
                    prev_val_p,
                    prev_list_p,
                    prev_dflt_p,
                    valid_codes=(lib.SR_ERR_OK, lib.SR_ERR_NOT_FOUND),
                )
        finally:
            lib.sr_free_change_iter(iter_p[0])

    # end: changes

    # begin: get
    def get_item(self, xpath: str, timeout_ms: int = 0) -> Value:
        """
        Retrieve a single data element selected by the provided path.

        :arg xpath:
            Path of the data element to be retrieved.
        :arg timeout_ms:
            Operational callback timeout in milliseconds. If 0, default is used.

        :returns:
            A sysrepo.Value object.
        :raises SysrepoInvalArgError:
            If multiple nodes match the path.
        :raises SysrepoNotFoundError:
            If no nodes match the path.
        """
        val_p = ffi.new("sr_val_t **")
        check_call(lib.sr_get_item, self.cdata, str2c(xpath), timeout_ms, val_p)
        try:
            return Value.parse(val_p[0])
        finally:
            lib.sr_free_val(val_p[0])

    def get_items(
        self,
        xpath: str,
        timeout_ms: int = 0,
        no_state: bool = False,
        no_config: bool = False,
        no_subs: bool = False,
        no_stored: bool = False,
    ) -> Iterator[Value]:
        """
        Retrieve an array of data elements selected by the provided XPath.

        All data elements are transferred within one message from the datastore, which
        is more efficient than multiple get_item calls.

        :arg xpath:
            XPath of the data elements to be retrieved.
        :arg timeout_ms:
            Operational callback timeout in milliseconds. If 0, default is used.
        :arg no_state:
            Return only configuration data.
        :arg no_config:
            Return only state data. If there are some state subtrees with configuration
            these are also returned (with keys if lists).
        :arg no_subs:
            Return only stored operational data (push), do not call subscriber
            callbacks (pull).
        :arg no_stored:
            Do not merge with stored operational data (push).

        :returns:
            An iterator that yields sysrepo.Value objects.
        """
        flags = _get_oper_flags(
            no_state=no_state, no_config=no_config, no_subs=no_subs, no_stored=no_stored
        )
        val_p = ffi.new("sr_val_t **")
        count_p = ffi.new("size_t *")
        check_call(
            lib.sr_get_items,
            self.cdata,
            str2c(xpath),
            timeout_ms,
            flags,
            val_p,
            count_p,
        )
        try:
            for i in range(count_p[0]):
                yield Value.parse(val_p[0] + i)
        finally:
            lib.sr_free_values(val_p[0], count_p[0])

    def get_data_ly(
        self,
        xpath: str,
        max_depth: int = 0,
        timeout_ms: int = 0,
        no_state: bool = False,
        no_config: bool = False,
        no_subs: bool = False,
        no_stored: bool = False,
    ) -> libyang.DNode:
        """
        Retrieve a tree whose root nodes match the provided XPath.

        Top-level trees are always returned so if an inner node is selected, all of its
        descendants and its direct parents (lists also with keys) are returned.

        If the subtree selection process results in too many node overlaps, the cost of
        the operation may be unnecessarily big. As an example, a common XPath expression
        `//.` is normally used to select all nodes in a data tree, but for this
        operation it would result in an excessive duplication of data nodes. Since all
        the descendants of each matched node are returned implicitly, `//` in the XPath
        should never be used (i.e. `/*` is the correct XPath for all the nodes).

        :arg xpath:
            Path selecting the root nodes of subtrees to be retrieved.
        :arg max_depth:
            Maximum depth of the selected subtrees. 0 is unlimited, 1 will not return
            any descendant nodes. If a list should be returned, its keys are always
            returned as well.
        :arg timeout_ms:
            Operational callback timeout in milliseconds. If 0, default is used.
        :arg no_state:
            Return only configuration data.
        :arg no_config:
            Return only state data. If there are some state subtrees with configuration
            these are also returned (with keys if lists).
        :arg no_subs:
            Return only stored operational data (push), do not call subscriber callbacks
            (pull).
        :arg no_stored:
            Do not merge with stored operational data (push).

        :returns:
            A libyang.DNode object with all the requested data, allocated dynamically.
            It must be freed manually by the caller with the libyang.DNode.free()
            method.
        :raises SysrepoNotFoundError:
            If no nodes match the path.
        """
        flags = _get_oper_flags(
            no_state=no_state, no_config=no_config, no_subs=no_subs, no_stored=no_stored
        )
        if flags and lib.sr_session_get_ds(self.cdata) != lib.SR_DS_OPERATIONAL:
            raise ValueError(
                '"no_*" arguments are only valid for the "operational" datastore'
            )
        dnode_p = ffi.new("struct lyd_node **")
        check_call(
            lib.sr_get_data,
            self.cdata,
            str2c(xpath),
            max_depth,
            timeout_ms,
            flags,
            dnode_p,
        )
        if not dnode_p[0]:
            raise SysrepoNotFoundError(xpath)
        return libyang.DNode.new(self.get_ly_ctx(), dnode_p[0]).root()

    def get_data(
        self,
        xpath: str,
        max_depth: int = 0,
        timeout_ms: int = 0,
        no_state: bool = False,
        no_config: bool = False,
        no_subs: bool = False,
        no_stored: bool = False,
        strip_prefixes: bool = True,
        include_implicit_defaults: bool = False,
        trim_default_values: bool = False,
        keep_empty_containers: bool = False,
    ) -> Dict:
        """
        Same as `SysrepoSession.get_data_ly` but returns a python dictionary.

        :arg strip_prefixes:
            If True, remove YANG module prefixes from dictionary keys.
        :arg include_implicit_defaults:
            Include leaves with implicit default values in the retured dict.
        :arg trim_default_values:
            Exclude leaves when their value equals the default.
        :arg keep_empty_containers:
            Preserve empty non-presence containers.

        :returns:
            A python dictionary generated from the returned struct lyd_node.
        """
        data = self.get_data_ly(
            xpath,
            max_depth=max_depth,
            timeout_ms=timeout_ms,
            no_state=no_state,
            no_config=no_config,
            no_subs=no_subs,
            no_stored=no_stored,
        )
        try:
            return data.print_dict(
                with_siblings=True,
                absolute=True,
                strip_prefixes=strip_prefixes,
                include_implicit_defaults=include_implicit_defaults,
                trim_default_values=trim_default_values,
                keep_empty_containers=keep_empty_containers,
            )
        finally:
            data.free()

    # end: get

    # begin: edit
    def set_item(self, xpath: str, value: Any = None) -> None:
        """
        Prepare to set (create) the value of a leaf, leaf-list, list, or presence
        container. These changes are applied only after calling apply_changes().

        :arg xpath:
            Path identifier of the data element to be set.
        :arg value:
            Value to be set. It will be converted to string.
        """
        if value is not None and not isinstance(value, str):
            if isinstance(value, bool):
                value = str(value).lower()
            else:
                value = str(value)
        check_call(
            lib.sr_set_item_str, self.cdata, str2c(xpath), str2c(value), ffi.NULL, 0
        )

    def delete_item(self, xpath: str) -> None:
        """
        Prepare to delete the nodes matching the specified xpath. These changes
        are applied only after calling apply_changes().

        :arg xpath:
            Path identifier of the data element to be deleted.

        :raises SysrepoNotFoundError:
            If no nodes match the path.
        """
        check_call(lib.sr_delete_item, self.cdata, str2c(xpath), 0)

    def edit_batch_ly(
        self, edit: libyang.DNode, default_operation: str = "merge"
    ) -> None:
        """
        Provide a prepared edit data tree to be applied. These changes are
        applied only after calling apply_changes().

        :arg edit:
            Data tree holding the configuration. Similar semantics to
            https://tools.ietf.org/html/rfc6241#section-7.2. The given data tree is
            *NOT* spent and must be freed by the caller.
        :arg default_operation:
            Default operation for nodes without operation on themselves or any parent.
            Possible values are `merge`, `replace`, or `none`. See RFC 6241
            https://tools.ietf.org/html/rfc6241#page-39.
        """
        # libyang and sysrepo bindings are different, casting is required
        dnode = ffi.cast("struct lyd_node *", edit.cdata)
        check_call(lib.sr_edit_batch, self.cdata, dnode, str2c(default_operation))

    def edit_batch(
        self,
        edit: Dict,
        module_name: str,
        strict: bool = False,
        default_operation: str = "merge",
    ) -> None:
        """
        Same as `SysrepoSession.edit_batch_ly` but with a python dictionary.

        :arg edit:
            Python dictionary holding the configuration.
        :arg module_name:
            The YANG module name matching the data in the dictionary. It is used to
            convert the dictionary to a `libyang.DNode` object.
        :arg strict:
            If True, reject config if it contains elements without any schema
            definition.
        """
        ctx = self.get_ly_ctx()
        module = ctx.get_module(module_name)
        dnode = module.parse_data_dict(edit, edit=True, strict=strict, validate=False)
        if not dnode:
            raise ValueError("provided config dict is empty")
        try:
            self.edit_batch_ly(dnode, default_operation)
        finally:
            dnode.free()

    def replace_config_ly(
        self,
        config: Optional[libyang.DNode],
        module_name: Optional[str],
        timeout_ms: int = 0,
        wait: bool = False,
    ) -> None:
        """
        Replace a datastore with the contents of a data tree.

        :arg config:
            Source data to replace the datastore. Is ALWAYS spent and cannot be further
            used by the application! Can be None to completely reset the configuration.
        :arg module_name:
            The module for which to replace the configuration.
        :arg timeout_ms:
            Configuration callback timeout in milliseconds. If 0, default is used.
        :arg wait:
            Whether to wait until all callbacks on all events are finished.

        :raises SysrepoError:
            If the operation failed.
        """
        if isinstance(config, libyang.DNode):
            # libyang and sysrepo bindings are different, casting is required
            dnode = ffi.cast("struct lyd_node *", config.cdata)
        elif config is None:
            dnode = ffi.NULL
        else:
            raise TypeError("config must be either a libyang.DNode object or None")
        check_call(
            lib.sr_replace_config,
            self.cdata,
            str2c(module_name),
            dnode,
            timeout_ms,
            wait,
        )

    def replace_config(
        self,
        config: Optional[Dict],
        module_name: str,
        strict: bool = False,
        timeout_ms: int = 0,
        wait: bool = False,
    ) -> None:
        """
        Same as replace_config() but with a python dictionary.

        :arg config:
            The configuration dict.
        :arg strict:
            If True, reject config if it contains elements without any schema
            definition.
        """
        ctx = self.get_ly_ctx()
        module = ctx.get_module(module_name)
        dnode = module.parse_data_dict(config, edit=True, strict=strict, validate=False)
        self.replace_config_ly(dnode, module_name, timeout_ms=timeout_ms, wait=wait)

    def validate(self) -> None:
        """
        Perform the validation a datastore and any changes made in the current
        session, but do not apply nor discard them.

        Provides only YANG validation, apply-changes **subscribers will not be
        notified** in this case.

        :raises SysrepoError:
            If validation failed.
        """
        if self.is_implicit:
            raise SysrepoUnsupportedError("cannot validate with implicit sessions")
        check_call(lib.sr_validate, self.cdata, 0)

    def apply_changes(self, timeout_ms: int = 0, wait: bool = False) -> None:
        """
        Apply changes made in the current session. In case the changes could not be
        applied successfully for any reason, they remain intact in the session until
        discard_changes() is called.

        :arg timeout_ms:
            Configuration callback timeout in milliseconds. If 0, default is used.
        :arg wait:
            If True, wait until all callbacks on all events are finished (even "done" or
            "abort"). If not set, these events may not yet be processed after the
            function returns. Note that all "change" events are always waited for.

        :raises SysrepoError:
            If changes could not be applied.
        """
        if self.is_implicit:
            raise SysrepoUnsupportedError("cannot apply_changes with implicit sessions")
        check_call(lib.sr_apply_changes, self.cdata, timeout_ms, wait)

    def discard_changes(self) -> None:
        """
        Discard prepared changes made in the current session.
        """
        if self.is_implicit:
            raise SysrepoUnsupportedError(
                "cannot discard_changes with implicit sessions"
            )
        check_call(lib.sr_discard_changes, self.cdata)

    # end: edit

    def rpc_send_ly(
        self, rpc_input: libyang.DNode, timeout_ms: int = 0
    ) -> libyang.DNode:
        """
        Send an RPC/action and wait for the result.

        RPC/action must be valid in (is validated against) the operational datastore
        context.

        :arg rpc_input:
            The RPC/action input tree. It is *NOT* spent and must be freed by the
            caller.
        :arg timeout_ms:
            RPC/action callback timeout in milliseconds. If 0, default is used.

        :returns:
            The RPC/action output tree. Allocated dynamically and must be freed by the
            caller.
        :raises SysrepoError:
            If the RPC/action callback failed.
        """
        if not isinstance(rpc_input, libyang.DNode):
            raise TypeError("rpc_input must be a libyang.DNode")
        # libyang and sysrepo bindings are different, casting is required
        in_dnode = ffi.cast("struct lyd_node *", rpc_input.cdata)
        out_dnode_p = ffi.new("struct lyd_node **")
        check_call(lib.sr_rpc_send_tree, self.cdata, in_dnode, timeout_ms, out_dnode_p)
        if not out_dnode_p[0]:
            raise SysrepoInternalError("sr_rpc_send_tree returned NULL")
        return libyang.DNode.new(self.get_ly_ctx(), out_dnode_p[0])

    def rpc_send(
        self,
        xpath: str,
        input_dict: Dict,
        timeout_ms: int = 0,
        strict: bool = False,
        strip_prefixes: bool = True,
        include_implicit_defaults: bool = False,
        trim_default_values: bool = False,
        keep_empty_containers: bool = False,
    ) -> Dict:
        """
        Same as rpc_send_ly() but takes a python dictionary and a YANG module name as
        input arguments.

        :arg rpc_input:
            Input data tree. It is converted to a libyang struct lyd_node according to
            module_name.
        :arg module_name:
            The name of the YANG module used to convert the rpc input dict to a
            libyang.DNode object.
        :arg strict:
            If True, reject rpc_input if it contains elements without any schema
            definition.
        :arg strip_prefixes:
            If True, remove YANG module prefixes from dictionary keys.
        :arg include_implicit_defaults:
            Include leaves with implicit default values in the retured dict.
        :arg trim_default_values:
            Exclude leaves when their value equals the default.
        :arg keep_empty_containers:
            Include empty (non-presence) containers.

        :returns:
            A python dictionary with the RPC/action output tree.
        """
        ctx = self.get_ly_ctx()
        rpc = {}
        libyang.xpath_set(rpc, xpath, input_dict)
        module_name, _, _ = next(libyang.xpath_split(xpath))
        module = ctx.get_module(module_name)
        in_dnode = module.parse_data_dict(rpc, rpc=True, strict=strict, validate=False)
        try:
            out_dnode = self.rpc_send_ly(in_dnode, timeout_ms=timeout_ms)
        finally:
            in_dnode.free()
        try:
            out_dict = out_dnode.print_dict(
                strip_prefixes=strip_prefixes,
                absolute=False,
                with_siblings=False,
                include_implicit_defaults=include_implicit_defaults,
                trim_default_values=trim_default_values,
                keep_empty_containers=keep_empty_containers,
            )
            # strip first item with only RPC/action name
            return next(iter(out_dict.values()))
        finally:
            out_dnode.free()

    def notification_send_ly(self, notification: libyang.DNode) -> None:
        """
        Send a notification

        :arg notification:
            The notification tree. It is *NOT* spent and must be freed by the
            caller.

        :raises SysrepoError:
            If the notification callback failed.
        """
        if not isinstance(notification, libyang.DNode):
            raise TypeError("notification must be a libyang.DNode")
        # libyang and sysrepo bindings are different, casting is required
        in_dnode = ffi.cast("struct lyd_node *", notification.cdata)
        check_call(lib.sr_event_notif_send_tree, self.cdata, in_dnode)

    def notification_send(
        self, xpath: str, notification: Dict, strict: bool = False
    ) -> None:
        """
        Same as notification_send_ly() but takes a python dictionary as a notification.

        :arg xpath:
            The xpath corresponding to the notification
        :arg notification:
            The notification to send represented as a dictionary
        :arg strict:
            If True, reject notification if it contains elements without any schema
            definition.

        :raises SysrepoError:
            If the notification callback failed.
        """

        ctx = self.get_ly_ctx()
        full_notification = {}
        libyang.xpath_set(full_notification, xpath, notification)
        module_name, _, _ = next(libyang.xpath_split(xpath))
        module = ctx.get_module(module_name)
        dnode = module.parse_data_dict(
            full_notification, notification=True, strict=strict, validate=False
        )
        try:
            self.notification_send_ly(dnode)
        finally:
            dnode.free()


# -------------------------------------------------------------------------------------
DATASTORE_VALUES = {
    "running": lib.SR_DS_RUNNING,
    "operational": lib.SR_DS_OPERATIONAL,
    "startup": lib.SR_DS_STARTUP,
    "candidate": lib.SR_DS_CANDIDATE,
}


def datastore_value(name: str) -> int:
    if name not in DATASTORE_VALUES:
        raise ValueError("unknown datastore name: %r" % name)
    return DATASTORE_VALUES[name]


def datastore_name(value: int) -> str:
    for name, val in DATASTORE_VALUES.items():
        if val == value:
            return name
    raise ValueError("unknown datastore value: %r" % value)


# -------------------------------------------------------------------------------------
def _get_oper_flags(no_state=False, no_config=False, no_subs=False, no_stored=False):
    flags = 0
    if no_state:
        flags |= lib.SR_OPER_NO_STATE
    if no_config:
        flags |= lib.SR_OPER_NO_CONFIG
    if no_subs:
        flags |= lib.SR_OPER_NO_SUBS
    if no_stored:
        flags |= lib.SR_OPER_NO_STORED
    return flags


# -------------------------------------------------------------------------------------
def _subscribe_flags(no_thread=False, passive=False, done_only=False, enabled=False):
    flags = 0
    if no_thread:
        flags |= lib.SR_SUBSCR_NO_THREAD
    if passive:
        flags |= lib.SR_SUBSCR_PASSIVE
    if done_only:
        flags |= lib.SR_SUBSCR_DONE_ONLY
    if enabled:
        flags |= lib.SR_SUBSCR_ENABLED
    return flags


# -------------------------------------------------------------------------------------
def _check_subscription_callback(callback, expected_type):
    if not inspect.isroutine(callback):
        raise TypeError("callback must be a function")
    *arg_types, return_type = expected_type.__args__
    sig = inspect.signature(callback)
    callback_positional_args = tuple(
        p
        for p in sig.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    )
    if len(arg_types) != len(callback_positional_args):
        raise ValueError(
            "callback %s does not have required arguments: (%s) -> %s"
            % (callback, arg_types, return_type)
        )
