# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import asyncio
import functools
import logging
from typing import Any, Callable

from libyang.data import DNode

from _sysrepo import ffi, lib
from .errors import SysrepoError, SysrepoNotFoundError, check_call
from .util import c2str, is_async_func, xpath_split


LOG = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
class Subscription:
    """
    Python representation of `sr_subscription_ctx_t *`.

    .. attention::

        Do not instantiate this class manually, use `SysrepoSession.subscribe_*`.
    """

    def __init__(
        self,
        callback: Callable,
        private_data: Any = None,
        asyncio_register: bool = False,
        strict: bool = False,
    ):
        """
        :arg callback:
            The python callback function or coroutine function used when subscribing.
        :arg private_data:
            Opaque data used when subscribing, will be passed to callback.
        :arg asyncio_register:
            Add this subscription event pipe into asyncio event loop monitored file
            descriptors. When the event pipe becomes readable, call process_events().
        :arg strict:
            If True, reject data with no schema definition from rpc output parameters
            and operational data callbacks. Otherwise, ignore unknown data and log a
            warning message.
        """
        if is_async_func(callback) and not asyncio_register:
            raise ValueError(
                "%s is an async function, asyncio_register is mandatory" % callback
            )
        self.callback = callback
        self.private_data = private_data
        self.asyncio_register = asyncio_register
        self.strict = strict
        if asyncio_register:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = None
        self.tasks = {}
        self.cdata = None
        self.fd = -1
        self.handle = ffi.new_handle(self)

    def init(self, cdata) -> None:
        """
        Initialization of this object is not complete after calling __init__. The
        sr_subscription_ctx_t object is allocated by sysrepo when calling one of
        sr_*_subscribe functions and we need to pass self.handle to these functions so
        that this subscription can be forwarded to C callbacks.

        Subscription.init() is called just after sr_*_subscribe functions to complete
        initialization. See SysrepoSession.subscribe_* functions for more details.

        if self.asyncio_register is  True, add this subscription event pipe to the
        monitored file descriptors for reading in asyncio event loop.

        :arg "sr_subscription_ctx_t *" cdata:
            The subscription pointer allocated by sysrepo.
        """
        if self.cdata is not None:
            raise RuntimeError("init was already called once")
        self.cdata = cdata
        if self.asyncio_register:
            self.fd = self.get_fd()
            self.loop.add_reader(self.fd, self.process_events)

    def get_fd(self) -> int:
        """
        Get the event pipe of a subscription. Event pipe can be used in `select()`,
        `poll()`, or similar functions to listen for new events. It will then be ready
        for reading.
        """
        fd_p = ffi.new("int *")
        check_call(lib.sr_get_event_pipe, self.cdata, fd_p)
        return fd_p[0]

    def unsubscribe(self) -> None:
        """
        Unsubscribes from a subscription acquired by any of sr_*_subscribe calls and
        releases all subscription-related data.

        Removes self.fd from asyncio event loop monitored file descriptors.
        """
        if self.cdata is None:
            return
        if self.asyncio_register and self.fd != -1:
            self.loop.remove_reader(self.fd)
        try:
            check_call(lib.sr_unsubscribe, self.cdata)
        finally:
            self.cdata = None
        for t in list(self.tasks.values()):
            t.cancel()
        self.tasks.clear()

    def process_events(self) -> None:
        """
        Called when self.fd becomes readable.
        """
        check_call(lib.sr_process_events, self.cdata, ffi.NULL, ffi.NULL)

    def task_done(self, task_id: Any, event: str, task: asyncio.Task) -> None:
        """
        Called when self.callback is an async function/method and it has finished. This
        calls self.process_events() so that the C callback is invoked again with the
        same arguments (request_id, event) and we can return the actual result.
        """
        if task.cancelled():
            self.tasks.pop(task_id, None)
            return
        try:
            if event in ("update", "change", "rpc", "oper"):
                # The task result will be evaluated in the C callback.
                # It will return the result to sysrepo.
                self.process_events()
            else:
                # Sysrepo does not care about the result of the callback.
                # This will raise the exception here if any occured in the task
                # and will be logged (i.e. not lost).
                self.tasks.pop(task_id, None)
                task.result()
        except Exception:
            LOG.exception("failure in task: %r", task)


# ------------------------------------------------------------------------------
EVENT_NAMES = {
    lib.SR_EV_UPDATE: "update",
    lib.SR_EV_CHANGE: "change",
    lib.SR_EV_DONE: "done",
    lib.SR_EV_ABORT: "abort",
    lib.SR_EV_ENABLED: "enabled",
    lib.SR_EV_RPC: "rpc",
}


# ------------------------------------------------------------------------------
@ffi.def_extern(name="srpy_module_change_cb")
def module_change_callback(session, module, xpath, event, req_id, priv):
    """
    Callback to be called on the event of changing datastore content of the specified
    module.

    This python function mapped to the C srpy_module_change_cb function. When the C
    srpy_module_change_cb function is called by libsysrepo.so, this function is called
    with the same arguments.

    :arg "sr_session_ctx_t *" session:
        Implicit session (do not stop) with information about the changed data.
    :arg "const char *" module:
        Name of the module where the change has occurred.
    :arg "const char *" xpath:
        XPath used when subscribing, NULL if the whole module was subscribed to.
    :arg "sr_event_t" event:
        Type of the callback event that has occurred.
    :arg "uint32_t" req_id:
        Request ID unique for the specific module_name. Connected events for one request
        (SR_EV_CHANGE and SR_EV_DONE, for example) have the same request ID.
    :arg "void *" priv:
        Private context opaque to sysrepo. Contains a CFFI handle to the Subscription
        python object.

    :returns:
        User error code (sr_error_t).
    :raises:
        IMPORTANT: This function *CANNOT* raise any exception. The C callstack does not
        handle that well and when it happens the outcome is undetermined. Make sure to
        catch all errors and log them so they are not lost.
    """
    try:
        # convert C arguments to python objects.
        from .session import SysrepoSession  # circular import

        session = SysrepoSession(session, True)
        module = c2str(module)
        xpath = c2str(xpath)
        root_xpath = ("/%s:*" % module) if xpath is None else xpath
        subscription = ffi.from_handle(priv)
        callback = subscription.callback
        private_data = subscription.private_data
        event_name = EVENT_NAMES[event]

        if is_async_func(callback):
            task_id = (event, req_id)

            if task_id not in subscription.tasks:
                # ATTENTION: the implicit session passed as argument will be
                # freed when this function returns. The async callback must NOT
                # keep a reference on it as it will be invalid. Config and
                # changes must be gathered and converted to python objects now.
                try:
                    config = session.get_data(
                        root_xpath, include_implicit_defaults=True
                    )
                except SysrepoNotFoundError:
                    config = {}
                changes = list(session.get_changes(root_xpath + "//."))
                task = subscription.loop.create_task(
                    callback(event_name, req_id, config, changes, private_data)
                )
                task.add_done_callback(
                    functools.partial(subscription.task_done, task_id, event_name)
                )
                subscription.tasks[task_id] = task
                if event not in (lib.SR_EV_UPDATE, lib.SR_EV_CHANGE):
                    # Return immediately, process_events will not be called in
                    # subscription.task_done. Sysrepo does not care about the
                    # result of the operation.
                    return lib.SR_ERR_OK

            task = subscription.tasks[task_id]

            if not task.done():
                return lib.SR_ERR_CALLBACK_SHELVE

            del subscription.tasks[task_id]
            task.result()  # raise error if any

        else:
            try:
                config = session.get_data(root_xpath, include_implicit_defaults=True)
            except SysrepoNotFoundError:
                config = {}
            changes = list(session.get_changes(root_xpath + "//."))
            callback(event_name, req_id, config, changes, private_data)

        return lib.SR_ERR_OK

    except SysrepoError as e:
        if (
            event in (lib.SR_EV_UPDATE, lib.SR_EV_CHANGE)
            and e.msg
            and isinstance(session, SysrepoSession)
            and isinstance(xpath, str)
        ):
            session.set_error(xpath, e.msg)
        return e.rc

    except BaseException as e:
        # ATTENTION: catch all exceptions!
        # including KeyboardInterrupt, CancelledError, etc.
        # We are in a C callback, we cannot let any error pass
        LOG.exception("%r callback failed", locals().get("callback", priv))
        if (
            event in (lib.SR_EV_UPDATE, lib.SR_EV_CHANGE)
            and isinstance(session, SysrepoSession)
            and isinstance(xpath, str)
        ):
            session.set_error(xpath, str(e))
        return lib.SR_ERR_CALLBACK_FAILED


# ------------------------------------------------------------------------------
@ffi.def_extern(name="srpy_oper_data_cb")
def oper_data_callback(session, module, xpath, req_xpath, req_id, parent, priv):
    """
    Callback to be called when operational data at the selected xpath are requested.

    :arg "sr_session_ctx_t *" session:
        Implicit session (do not stop).
    :arg "const char *" module:
        Name of the affected module.
    :arg "const char *" xpath:
        XPath identifying the subtree that is supposed to be provided, same as the one
        used for the subscription.
    :arg "const char *" req_xpath:
        XPath as requested by a client. Can be NULL.
    :arg "uint32_t" req_id:
        Request ID unique for the specific module name.
    :arg "struct lyd_node **" parent:
        Pointer to an existing parent of the requested nodes. Is NULL for top-level
        nodes. Callback is supposed to append the requested nodes to this data subtree
        and return either the original parent or a top-level node.
    :arg "void *" priv:
        Private context opaque to sysrepo. Contains a CFFI handle to the Subscription
        python object.

    :returns:
        User error code (sr_error_t).
    :raises:
        IMPORTANT: This function *CANNOT* raise any exception. The C callstack does not
        handle that well and when it happens the outcome is undetermined. Make sure to
        catch all errors and log them so they are not lost.
    """
    try:
        # convert C arguments to python objects.
        from .session import SysrepoSession  # circular import

        session = SysrepoSession(session, True)
        module = c2str(module)
        xpath = c2str(xpath)
        req_xpath = c2str(req_xpath)
        subscription = ffi.from_handle(priv)
        callback = subscription.callback
        private_data = subscription.private_data

        if is_async_func(callback):
            task_id = req_id

            if task_id not in subscription.tasks:
                task = subscription.loop.create_task(callback(req_xpath, private_data))
                task.add_done_callback(
                    functools.partial(subscription.task_done, task_id, "oper")
                )
                subscription.tasks[task_id] = task

            task = subscription.tasks[task_id]

            if not task.done():
                return lib.SR_ERR_CALLBACK_SHELVE

            del subscription.tasks[task_id]

            oper_data = task.result()

        else:
            oper_data = callback(req_xpath, private_data)

        if isinstance(oper_data, dict):
            # convert oper_data to a libyang.DNode object
            ly_ctx = session.get_ly_ctx()
            dnode = ly_ctx.get_module(module).parse_data_dict(
                oper_data, data=True, no_yanglib=True, strict=subscription.strict
            )
            if dnode is not None:
                if parent[0]:
                    root = DNode.new(ly_ctx, parent[0]).root()
                    root.merge(dnode, destruct=True)
                else:
                    # The FFI bindings of libyang and sysrepo are different.
                    # Casting is required.
                    parent[0] = ffi.cast("struct lyd_node *", dnode.cdata)
        elif oper_data is not None:
            raise TypeError(
                "bad return type from %s (expected dict or None)" % callback
            )

        return lib.SR_ERR_OK

    except SysrepoError as e:
        if e.msg and isinstance(session, SysrepoSession) and isinstance(xpath, str):
            session.set_error(xpath, e.msg)
        return e.rc

    except BaseException as e:
        # ATTENTION: catch all exceptions!
        # including KeyboardInterrupt, CancelledError, etc.
        # We are in a C callback, we cannot let any error pass
        LOG.exception("%r callback failed", locals().get("callback", priv))
        if isinstance(session, SysrepoSession) and isinstance(xpath, str):
            session.set_error(xpath, str(e))
        return lib.SR_ERR_CALLBACK_FAILED


# ------------------------------------------------------------------------------
@ffi.def_extern(name="srpy_rpc_tree_cb")
def rpc_callback(session, xpath, input_node, event, req_id, output_node, priv):
    """
    Callback to be called for the delivery of an RPC/action.

    :arg "sr_session_ctx_t *" session:
        Implicit session (do not stop).
    :arg "const char *" xpath:
        Simple operation path identifying the RPC/action.
    :arg "const struct lyd_node *" input_node:
        Data tree of input parameters.
    :arg "sr_event_t" event:
        Type of the callback event that has occurred.
    :arg "uint32_t" req_id:
        Request ID unique for the specific xpath.
    :arg "struct lyd_node *" output_node:
        Data tree of output parameters. Should be allocated on heap, will be freed by
        sysrepo after sending of the RPC response.
    :arg "void *" priv:
        Private context opaque to sysrepo. Contains a CFFI handle to the Subscription
        python object.

    :returns:
        User error code (sr_error_t).
    :raises:
        IMPORTANT: This function *CANNOT* raise any exception. The C callstack does not
        handle that well and when it happens the outcome is undetermined. Make sure to
        catch all errors and log them so they are not lost.
    """
    try:
        # convert C arguments to python objects.
        from .session import SysrepoSession  # circular import

        session = SysrepoSession(session, True)
        ly_ctx = session.get_ly_ctx()
        xpath = c2str(xpath)
        input_dict = DNode.new(ly_ctx, input_node).print_dict(
            include_implicit_defaults=True
        )
        subscription = ffi.from_handle(priv)
        callback = subscription.callback
        private_data = subscription.private_data
        event_name = EVENT_NAMES[event]

        if is_async_func(callback):
            task_id = (event, req_id)

            if task_id not in subscription.tasks:
                task = subscription.loop.create_task(
                    callback(input_dict, event_name, private_data)
                )
                task.add_done_callback(
                    functools.partial(subscription.task_done, task_id, event_name)
                )
                subscription.tasks[task_id] = task

            task = subscription.tasks[task_id]

            if not task.done():
                return lib.SR_ERR_CALLBACK_SHELVE

            del subscription.tasks[task_id]

            output_dict = task.result()

        else:
            output_dict = callback(input_dict, event_name, private_data)

        if event != lib.SR_EV_RPC:
            # May happen when there are multiple callback registered for the
            # same RPC. If one of the callbacks has failed, the other ones will
            # be called with SR_EV_ABORT. In that case, abort early and do
            # not return the RPC output data to sysrepo.
            return lib.SR_ERR_OK

        if isinstance(output_dict, dict):
            # update output_node with contents of output_dict
            # strip first level of output_dict with the rpc name
            prefix, name, _ = next(xpath_split(xpath))
            name_prefix = "%s:%s" % (prefix, name)
            if name in output_dict:
                output_dict = output_dict[name]
            elif name_prefix in output_dict:
                output_dict = output_dict[name_prefix]
            dnode = DNode.new(ly_ctx, output_node)
            dnode.merge_data_dict(
                output_dict, rpcreply=True, strict=subscription.strict
            )
        elif output_dict is not None:
            raise TypeError(
                "bad return type from %s (expected dict or None)" % callback
            )

        return lib.SR_ERR_OK

    except SysrepoError as e:
        if e.msg and isinstance(session, SysrepoSession) and isinstance(xpath, str):
            session.set_error(xpath, e.msg)
        return e.rc

    except BaseException as e:
        # ATTENTION: catch all exceptions!
        # including KeyboardInterrupt, CancelledError, etc.
        # We are in a C callback, we cannot let any error pass
        LOG.exception("%r callback failed", locals().get("callback", priv))
        if isinstance(session, SysrepoSession) and isinstance(xpath, str):
            session.set_error(xpath, str(e))
        return lib.SR_ERR_CALLBACK_FAILED
