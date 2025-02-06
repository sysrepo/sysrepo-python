/*
 * Copyright (c) 2020 6WIND S.A.
 * SPDX-License-Identifier: BSD-3-Clause
 */

typedef enum sr_error_e {
    SR_ERR_OK,
    SR_ERR_INVAL_ARG,
    SR_ERR_LY,
    SR_ERR_SYS,
    SR_ERR_NO_MEMORY,
    SR_ERR_NOT_FOUND,
    SR_ERR_EXISTS,
    SR_ERR_INTERNAL,
    SR_ERR_UNSUPPORTED,
    SR_ERR_VALIDATION_FAILED,
    SR_ERR_OPERATION_FAILED,
    SR_ERR_UNAUTHORIZED,
    SR_ERR_LOCKED,
    SR_ERR_TIME_OUT,
    SR_ERR_CALLBACK_FAILED,
    SR_ERR_CALLBACK_SHELVE,
    ...
} sr_error_t;

const char *sr_strerror(int);

typedef enum {
    SR_LL_NONE,
    SR_LL_ERR,
    SR_LL_WRN,
    SR_LL_INF,
    SR_LL_DBG,
    ...
} sr_log_level_t;

extern "Python" void srpy_log_cb(sr_log_level_t, const char *);
void sr_log_set_cb(void (*)(sr_log_level_t, const char *));
void sr_log_stderr(sr_log_level_t);
void sr_log_syslog(const char *app_name, sr_log_level_t);
sr_log_level_t sr_log_get_stderr(void);
sr_log_level_t sr_log_get_syslog(void);

typedef struct sr_conn_ctx_s sr_conn_ctx_t;
typedef struct sr_session_ctx_s sr_session_ctx_t;
typedef enum sr_conn_flag_e {
	SR_CONN_CACHE_RUNNING,
	SR_CONN_CTX_SET_PRIV_PARSED,
	...
} sr_conn_flag_t;
typedef uint32_t sr_conn_options_t;
typedef enum sr_datastore_e {
	SR_DS_STARTUP,
	SR_DS_RUNNING,
	SR_DS_CANDIDATE,
	SR_DS_OPERATIONAL,
	...
} sr_datastore_t;
typedef struct sr_error_info_err_s {
	sr_error_t err_code;
	char *message;
	char *error_format;
	void *error_data;
} sr_error_info_err_t;
typedef struct sr_error_info_s {
	sr_error_info_err_t *err;
	uint32_t err_count;
} sr_error_info_t;

/* forward declarations from libyang */
struct ly_ctx;
struct lyd_node;
typedef int... time_t;
struct timespec {
    time_t tv_sec;
    long tv_nsec;
};

int sr_connect(const sr_conn_options_t, sr_conn_ctx_t **);
int sr_disconnect(sr_conn_ctx_t *);
const struct ly_ctx *sr_acquire_context(sr_conn_ctx_t *);
void sr_release_context(sr_conn_ctx_t *);
int sr_install_module(sr_conn_ctx_t *, const char *, const char *, const char **);
int sr_install_modules(sr_conn_ctx_t *conn, const char **, const char *, const char ***);
int sr_remove_module(sr_conn_ctx_t *, const char *, int);
int sr_remove_modules(sr_conn_ctx_t *conn, const char **, int);
int sr_update_module(sr_conn_ctx_t *, const char *, const char *);
int sr_update_modules(sr_conn_ctx_t *, const char **, const char *);
int sr_enable_module_feature(sr_conn_ctx_t *, const char *, const char *);
int sr_disable_module_feature(sr_conn_ctx_t *, const char *, const char *);

int sr_session_start(sr_conn_ctx_t *, const sr_datastore_t, sr_session_ctx_t **);
int sr_session_stop(sr_session_ctx_t *);
int sr_session_switch_ds(sr_session_ctx_t *, sr_datastore_t);
sr_datastore_t sr_session_get_ds(sr_session_ctx_t *);
sr_conn_ctx_t *sr_session_get_connection(sr_session_ctx_t *);
int sr_session_get_error(sr_session_ctx_t *, const sr_error_info_t **);
int sr_session_set_error(sr_session_ctx_t *, const char *, sr_error_t, const char *, ...);
const char *sr_session_get_orig_name(sr_session_ctx_t *session);
int sr_session_set_orig_name(sr_session_ctx_t *session, const char *);
int sr_session_get_orig_data(sr_session_ctx_t *session, uint32_t idx, uint32_t *size, const void **data);
int sr_session_push_orig_data(sr_session_ctx_t * session, uint32_t size, const void *data);

int sr_lock(sr_session_ctx_t *session, const char *module_name, uint32_t timeout_ms);
int sr_unlock(sr_session_ctx_t *session, const char *module_name);

typedef enum sr_val_type_e {
	SR_UNKNOWN_T,
	SR_LIST_T,
	SR_CONTAINER_T,
	SR_CONTAINER_PRESENCE_T,
	SR_LEAF_EMPTY_T,
	SR_BINARY_T,
	SR_BITS_T,
	SR_BOOL_T,
	SR_DECIMAL64_T,
	SR_ENUM_T,
	SR_IDENTITYREF_T,
	SR_INSTANCEID_T,
	SR_INT8_T,
	SR_INT16_T,
	SR_INT32_T,
	SR_INT64_T,
	SR_STRING_T,
	SR_UINT8_T,
	SR_UINT16_T,
	SR_UINT32_T,
	SR_UINT64_T,
	SR_ANYXML_T,
	SR_ANYDATA_T,
	...
} sr_val_type_t;
typedef union sr_val_data_u {
	char *binary_val;
	char *bits_val;
	int bool_val;
	double decimal64_val;
	char *enum_val;
	char *identityref_val;
	char *instanceid_val;
	int8_t int8_val;
	int16_t int16_val;
	int32_t int32_val;
	int64_t int64_val;
	char *string_val;
	uint8_t uint8_val;
	uint16_t uint16_val;
	uint32_t uint32_val;
	uint64_t uint64_val;
	char *anyxml_val;
	char *anydata_val;
	...;
} sr_val_data_t;
typedef struct sr_val_s {
    char *xpath;
    sr_val_type_t type;
    sr_val_data_t data;
    ...;
} sr_val_t;
typedef enum sr_edit_flag_e {
	SR_EDIT_NON_RECURSIVE,
	SR_EDIT_STRICT,
	SR_EDIT_ISOLATE,
	...
} sr_edit_flag_t;
typedef uint32_t sr_edit_options_t;
typedef enum sr_get_oper_flag_e {
	SR_OPER_NO_STATE,
	SR_OPER_NO_CONFIG,
	SR_OPER_NO_SUBS,
	SR_OPER_NO_STORED,
	...
} sr_get_oper_flag_t;
typedef uint32_t sr_get_oper_options_t;

struct sr_data_s {
    const sr_conn_ctx_t *conn;
    struct lyd_node *tree;
};
typedef struct sr_data_s sr_data_t;

void sr_free_val(sr_val_t *);
void sr_free_values(sr_val_t *, size_t);

int sr_get_item(sr_session_ctx_t *, const char *, uint32_t, sr_val_t **);
int sr_get_items(sr_session_ctx_t *, const char *, uint32_t,
	const sr_get_oper_options_t, sr_val_t **, size_t *);
int sr_get_data(sr_session_ctx_t *, const char *, uint32_t, uint32_t,
	const sr_get_oper_options_t, sr_data_t **);
void sr_release_data(sr_data_t *);
int sr_rpc_send_tree(sr_session_ctx_t *, struct lyd_node *, uint32_t, sr_data_t **);

int sr_set_item_str(sr_session_ctx_t *, const char *, const char *, const char *, const sr_edit_options_t);
int sr_discard_items(sr_session_ctx_t *, const char *);
int sr_delete_item(sr_session_ctx_t *, const char *, const sr_edit_options_t);
int sr_oper_delete_item_str(sr_session_ctx_t *, const char *, const char *, const sr_edit_options_t);
int sr_edit_batch(sr_session_ctx_t *, const struct lyd_node *, const char *);
int sr_copy_config(sr_session_ctx_t *, const char *, sr_datastore_t, uint32_t);
int sr_replace_config(sr_session_ctx_t *, const char *, struct lyd_node *, uint32_t);
int sr_validate(sr_session_ctx_t *, const char *, uint32_t);
int sr_apply_changes(sr_session_ctx_t *, uint32_t);
int sr_discard_changes(sr_session_ctx_t *);

typedef enum sr_subscr_flag_e {
	SR_SUBSCR_NO_THREAD,
	SR_SUBSCR_PASSIVE,
	SR_SUBSCR_DONE_ONLY,
	SR_SUBSCR_ENABLED,
	SR_SUBSCR_UPDATE,
	SR_SUBSCR_OPER_MERGE,
	SR_SUBSCR_THREAD_SUSPEND,
	SR_SUBSCR_OPER_POLL_DIFF,
	SR_SUBSCR_FILTER_ORIG,
	...
} sr_subscr_flag_t;

typedef struct sr_subscription_ctx_s sr_subscription_ctx_t;
typedef uint32_t sr_subscr_options_t;

int sr_get_event_pipe(sr_subscription_ctx_t *, int *);
int sr_subscription_process_events(sr_subscription_ctx_t *, sr_session_ctx_t *, struct timespec *);
int sr_unsubscribe(sr_subscription_ctx_t *);

typedef enum sr_event_e {
	SR_EV_UPDATE,
	SR_EV_CHANGE,
	SR_EV_DONE,
	SR_EV_ABORT,
	SR_EV_ENABLED,
	SR_EV_RPC,
	...
} sr_event_t;
typedef enum sr_change_oper_e {
	SR_OP_CREATED,
	SR_OP_MODIFIED,
	SR_OP_DELETED,
	SR_OP_MOVED,
	...
} sr_change_oper_t;
typedef struct sr_change_iter_s sr_change_iter_t;
int sr_get_changes_iter(sr_session_ctx_t *, const char *, sr_change_iter_t **);
int sr_get_change_next(
	sr_session_ctx_t *, sr_change_iter_t *, sr_change_oper_t *,
	sr_val_t **, sr_val_t **);
int sr_get_change_tree_next(
	sr_session_ctx_t *, sr_change_iter_t *, sr_change_oper_t *,
	const struct lyd_node **, const char **prev_val,
	const char **prev_list, int *prev_dflt);
void sr_free_change_iter(sr_change_iter_t *);


extern "Python" int srpy_module_change_cb(
	sr_session_ctx_t *, uint32_t sub_id, const char *module, const char *xpath,
	sr_event_t, uint32_t req_id, void *priv);
int sr_module_change_subscribe(
	sr_session_ctx_t *, const char *module, const char *xpath,
	int (*)(sr_session_ctx_t *, uint32_t, const char *, const char *, sr_event_t, uint32_t, void *),
	void *priv, uint32_t priority, sr_subscr_options_t, sr_subscription_ctx_t **);

extern "Python" int srpy_rpc_tree_cb(
	sr_session_ctx_t *, uint32_t sub_id, const char *, const struct lyd_node *input,
	sr_event_t, uint32_t req_id, struct lyd_node *output, void *priv);
int sr_rpc_subscribe_tree(
	sr_session_ctx_t *, const char *xpath,
	int (*)(sr_session_ctx_t *, uint32_t, const char *, const struct lyd_node *, sr_event_t, uint32_t, struct lyd_node *, void *),
	void *priv, uint32_t priority, sr_subscr_options_t, sr_subscription_ctx_t **);

extern "Python" int srpy_oper_data_cb(
	sr_session_ctx_t *, uint32_t sub_id, const char *module, const char *xpath,
	const char *req_xpath, uint32_t req_id, struct lyd_node **, void *priv);
int sr_oper_get_subscribe(
	sr_session_ctx_t *, const char *module, const char *xpath,
	int (*)(sr_session_ctx_t *, uint32_t, const char *, const char *, const char *, uint32_t, struct lyd_node **, void *),
	void *priv, sr_subscr_options_t, sr_subscription_ctx_t **);

typedef enum sr_ev_notif_type_e {
	SR_EV_NOTIF_REALTIME,
	SR_EV_NOTIF_REPLAY,
	SR_EV_NOTIF_REPLAY_COMPLETE,
	SR_EV_NOTIF_TERMINATED,
	SR_EV_NOTIF_SUSPENDED,
	SR_EV_NOTIF_RESUMED,
	...
} sr_ev_notif_type_t;

extern "Python" void srpy_event_notif_tree_cb(
	sr_session_ctx_t *, uint32_t sub_id, const sr_ev_notif_type_t notif_type, const struct lyd_node *notif,
	struct timespec* timestamp, void *priv);

int sr_notif_subscribe_tree(sr_session_ctx_t *, const char *module_name, const char *xpath, struct timespec *start_time, struct timespec *stop_time,
	void (*)(sr_session_ctx_t *, uint32_t, const sr_ev_notif_type_t, const struct lyd_node*, struct timespec*, void*),
	void *priv, sr_subscr_options_t, sr_subscription_ctx_t **);

int sr_notif_send_tree(sr_session_ctx_t *, struct lyd_node *notif, uint32_t timeout_ms, int wait);

typedef int... mode_t;
int sr_get_module_ds_access(sr_conn_ctx_t *conn, const char *module_name, int mod_ds, char **owner, char **group, mode_t *perm);
