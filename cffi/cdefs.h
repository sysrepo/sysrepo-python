/*
 * Copyright (c) 2020 6WIND S.A.
 * SPDX-License-Identifier: BSD-3-Clause
 */

typedef enum sr_error_e {
    SR_ERR_OK,
    SR_ERR_INVAL_ARG,
    SR_ERR_LY,
    SR_ERR_SYS,
    SR_ERR_NOMEM,
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

typedef struct sr_conn_ctx_s sr_conn_ctx_t;
typedef struct sr_session_ctx_s sr_session_ctx_t;
typedef enum sr_conn_flag_e {
	SR_CONN_CACHE_RUNNING,
	SR_CONN_NO_SCHED_CHANGES,
	SR_CONN_ERR_ON_SCHED_FAIL,
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
typedef struct sr_error_info_msg_s {
	char *message;
	char *xpath;
} sr_error_info_msg_t;
typedef struct sr_error_info_s {
	sr_error_t err_code;
	sr_error_info_msg_t *err;
	size_t err_count;
} sr_error_info_t;

/* forward declarations from libyang */
struct ly_ctx;
struct lyd_node;

int sr_connect(const sr_conn_options_t, sr_conn_ctx_t **);
int sr_disconnect(sr_conn_ctx_t *);
const struct ly_ctx *sr_get_context(sr_conn_ctx_t *);
int sr_install_module(sr_conn_ctx_t *, const char *, const char *, const char **, int);
int sr_remove_module(sr_conn_ctx_t *, const char *);
int sr_update_module(sr_conn_ctx_t *, const char *, const char *);
int sr_enable_module_feature(sr_conn_ctx_t *, const char *, const char *);
int sr_disable_module_feature(sr_conn_ctx_t *, const char *, const char *);

int sr_session_start(sr_conn_ctx_t *, const sr_datastore_t, sr_session_ctx_t **);
int sr_session_stop(sr_session_ctx_t *);
int sr_session_switch_ds(sr_session_ctx_t *, sr_datastore_t);
sr_datastore_t sr_session_get_ds(sr_session_ctx_t *);
sr_conn_ctx_t *sr_session_get_connection(sr_session_ctx_t *);
int sr_get_error(sr_session_ctx_t *, const sr_error_info_t **);
int sr_set_error(sr_session_ctx_t *, const char *, const char *, ...);

typedef enum sr_type_e {
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
} sr_type_t;
typedef union sr_data_u {
	char *binary_val;
	char *bits_val;
	bool bool_val;
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
} sr_data_t;
typedef struct sr_val_s {
    char *xpath;
    sr_type_t type;
    sr_data_t data;
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

void sr_free_val(sr_val_t *);
void sr_free_values(sr_val_t *, size_t);

int sr_get_item(sr_session_ctx_t *, const char *, uint32_t, sr_val_t **);
int sr_get_items(sr_session_ctx_t *, const char *, uint32_t,
	const sr_get_oper_options_t, sr_val_t **, size_t *);
int sr_get_data(sr_session_ctx_t *, const char *, uint32_t, uint32_t,
	const sr_get_oper_options_t, struct lyd_node **);
int sr_rpc_send_tree(
	sr_session_ctx_t *, struct lyd_node *, uint32_t, struct lyd_node **);

int sr_set_item_str(sr_session_ctx_t *, const char *, const char *, const char *, const sr_edit_options_t);
int sr_delete_item(sr_session_ctx_t *, const char *, const sr_edit_options_t);
int sr_edit_batch(sr_session_ctx_t *, const struct lyd_node *, const char *);
int sr_replace_config(sr_session_ctx_t *, const char *, struct lyd_node *, uint32_t, int);
int sr_validate(sr_session_ctx_t *, const char *, uint32_t);
int sr_apply_changes(sr_session_ctx_t *, uint32_t, int);
int sr_discard_changes(sr_session_ctx_t *);

typedef enum sr_subscr_flag_e {
	SR_SUBSCR_CTX_REUSE,
	SR_SUBSCR_NO_THREAD,
	SR_SUBSCR_PASSIVE,
	SR_SUBSCR_DONE_ONLY,
	SR_SUBSCR_ENABLED,
	SR_SUBSCR_UPDATE,
	SR_SUBSCR_UNLOCKED,
	...
} sr_subscr_flag_t;

typedef struct sr_subscription_ctx_s sr_subscription_ctx_t;
typedef uint32_t sr_subscr_options_t;

int sr_get_event_pipe(sr_subscription_ctx_t *, int *);
typedef int... time_t;
int sr_process_events(sr_subscription_ctx_t *, sr_session_ctx_t *, time_t *);
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
	const char **prev_list, bool *prev_dflt);
void sr_free_change_iter(sr_change_iter_t *);


extern "Python" int srpy_module_change_cb(
	sr_session_ctx_t *, const char *module, const char *xpath,
	sr_event_t, uint32_t req_id, void *priv);
int sr_module_change_subscribe(
	sr_session_ctx_t *, const char *module, const char *xpath,
	int (*)(sr_session_ctx_t *, const char *, const char *, sr_event_t, uint32_t, void *),
	void *priv, uint32_t priority, sr_subscr_options_t, sr_subscription_ctx_t **);

extern "Python" int srpy_rpc_tree_cb(
	sr_session_ctx_t *, const char *, const struct lyd_node *input,
	sr_event_t, uint32_t req_id, struct lyd_node *output, void *priv);
int sr_rpc_subscribe_tree(
	sr_session_ctx_t *, const char *xpath,
	int (*)(sr_session_ctx_t *, const char *, const struct lyd_node *, sr_event_t, uint32_t, struct lyd_node *, void *),
	void *priv, uint32_t priority, sr_subscr_options_t, sr_subscription_ctx_t **);

extern "Python" int srpy_oper_data_cb(
	sr_session_ctx_t *, const char *module, const char *xpath,
	const char *req_xpath, uint32_t req_id, struct lyd_node **, void *priv);
int sr_oper_get_items_subscribe(
	sr_session_ctx_t *, const char *module, const char *xpath,
	int (*)(sr_session_ctx_t *, const char *, const char *, const char *, uint32_t, struct lyd_node **, void *),
	void *priv, sr_subscr_options_t, sr_subscription_ctx_t **);
