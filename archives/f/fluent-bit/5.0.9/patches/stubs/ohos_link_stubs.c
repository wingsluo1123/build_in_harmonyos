/* HarmonyOS link-time stubs for symbols referenced when
   FLB_TLS=Off, FLB_HTTP_SERVER=Off, FLB_SQLDB=Off, etc.

   These symbols are called from unconditionally-compiled source files
   even when the corresponding subsystem is disabled. The real
   implementations (tls/flb_tls.c, flb_oauth2.c, flb_oauth2_jwt.c,
   http_server/*) are excluded from the OHOS build because they pull in
   openssl / unavailable deps; stub symbols only satisfy the linker,
   the disabled subsystems are never exercised at runtime. */

#include <stdlib.h>
#include <stddef.h>

/* Forward declarations for fluent-bit types (stub file compiles without
   the project headers; only the linker needs the symbol names). */
struct flb_config;
struct flb_tls;
struct flb_tls_session;
struct flb_connection;
struct flb_coro;
struct mk_list;
struct flb_http_server;
struct flb_http_server_config;

/* --- SQLDB stubs (FLB_SQLDB=Off) --- */
void *flb_sqldb_open(void *config, const char *path, void *cb) { return NULL; }
void flb_sqldb_close(void *db) {}
int flb_sqldb_query(void *db, const char *sql, int (*cb)(void*,int,char**,char**), void *data) { return -1; }
int flb_sqldb_execute(void *db, const char *sql) { return -1; }
long long flb_sqldb_last_id(void *db) { return 0; }

/* --- HTTP Server stubs (FLB_HTTP_SERVER=Off) --- */
int flb_http_server_init(struct flb_http_server *session,
                         int protocol_version,
                         unsigned long long flags,
                         void *request_callback,
                         char *address,
                         unsigned short port,
                         struct flb_tls *tls_provider,
                         int networking_flags,
                         void *networking_setup,
                         void *event_loop,
                         struct flb_config *system_context,
                         void *user_data) { return -1; }
int flb_http_server_start(struct flb_http_server *session) { return -1; }
int flb_http_server_stop(struct flb_http_server *session) { return -1; }
int flb_http_server_destroy(struct flb_http_server *session) { return -1; }
void flb_http_server_config_init(struct flb_http_server_config *config) {}
struct mk_list *flb_http_server_get_config_map(struct flb_config *config) { return NULL; }
int flb_http_server_property_is_allowed(const char *property_name) { return 0; }

/* --- TLS stubs (FLB_TLS=Off; tls/flb_tls.c excluded) --- */
int flb_tls_init() { return 0; }
struct flb_tls *flb_tls_create(int mode, int verify, int debug,
                               const char *vhost, const char *ca_path,
                               const char *ca_file, const char *crt_file,
                               const char *key_file, const char *key_passwd)
{ return NULL; }
int flb_tls_destroy(struct flb_tls *tls) { return 0; }
int flb_tls_set_verify_client(struct flb_tls *tls, int verify_client) { return 0; }
int flb_tls_set_verify_hostname(struct flb_tls *tls, int verify_hostname) { return 0; }
int flb_tls_set_minmax_proto(struct flb_tls *tls,
                             const char *min_version, const char *max_version) { return 0; }
int flb_tls_set_ciphers(struct flb_tls *tls, const char *ciphers) { return 0; }
struct mk_list *flb_tls_get_config_map(struct flb_config *config) { return NULL; }
int flb_tls_session_destroy(struct flb_tls_session *session) { return 0; }
int flb_tls_session_invalidate(struct flb_tls_session *session) { return 0; }
int flb_tls_session_create(struct flb_tls *tls,
                           struct flb_connection *connection,
                           struct flb_coro *co) { return -1; }
int flb_tls_net_read(struct flb_tls_session *session, void *buf, size_t len) { return -1; }
int flb_tls_net_read_async(struct flb_coro *th,
                           struct flb_tls_session *session,
                           void *buf, size_t len) { return -1; }
int flb_tls_net_write(struct flb_tls_session *session,
                      const void *data, size_t len, size_t *out_len) { return -1; }
int flb_tls_net_write_async(struct flb_coro *th,
                            struct flb_tls_session *session,
                            const void *data, size_t len, size_t *out_len) { return -1; }

int flb_tls_load_system_certificates(struct flb_tls *tls) { return 0; }
int flb_tls_set_alpn(struct flb_tls *tls, const char *alpn) { return 0; }
const char *flb_tls_session_get_alpn(struct flb_tls_session *session) { return NULL; }

/* --- OAuth2 stubs (FLB_TLS=Off; flb_oauth2*.c excluded) --- */
struct mk_list *flb_oauth2_get_config_map(struct flb_config *config) { return NULL; }
struct mk_list *flb_oauth2_jwt_get_config_map(struct flb_config *config) { return NULL; }

/* --- pthread_cancel stub (musl may define it) --- */
#ifndef HAVE_PTHREAD_CANCEL
int pthread_cancel(void *thread) { return 0; }
#endif
