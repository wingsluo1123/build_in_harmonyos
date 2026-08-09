/* OHOS stub declaration header for the fluent-bit TLS API.
 *
 * With FLB_TLS=Off the real include/fluent-bit/tls/flb_tls.h hides every
 * declaration behind `#ifdef FLB_HAVE_TLS`, yet several unconditionally
 * compiled core sources (flb_help.c, flb_http_client.c, flb_output.c, ...)
 * still reference flb_tls_* functions. This stub declares those functions
 * (structs are only forward-declared); the symbols are provided at link
 * time by ohos_link_stubs.c.
 *
 * This header shadows the upstream one because the recipe adds
 * ${CMAKE_BINARY_DIR}/include/ to the include path BEFORE the source tree.
 */
#ifndef FLB_TLS_H
#define FLB_TLS_H

#include <stddef.h>

/* Constants copied from the upstream header (values must match) */
#define FLB_TLS_ALPN_MAX_LENGTH 16
#define FLB_TLS_CLIENT          "Fluent Bit"
#define FLB_TLS_WANT_READ       -0x7e4
#define FLB_TLS_WANT_WRITE      -0x7e6
#define FLB_TLS_CA_ROOT         1
#define FLB_TLS_CERT            2
#define FLB_TLS_PRIV_KEY        4
#define FLB_TLS_UNKNOWN_CONNECTION    0
#define FLB_TLS_UPSTREAM_CONNECTION   1
#define FLB_TLS_DOWNSTREAM_CONNECTION 2
#define FLB_TLS_CLIENT_MODE     0
#define FLB_TLS_SERVER_MODE     1

/* Forward declarations (pointers only; never dereferenced when TLS is off) */
struct flb_config;
struct flb_tls;
struct flb_tls_session;
struct flb_connection;
struct flb_coro;
struct mk_list;

int flb_tls_init();
struct flb_tls *flb_tls_create(int mode,
                               int verify,
                               int debug,
                               const char *vhost,
                               const char *ca_path,
                               const char *ca_file,
                               const char *crt_file,
                               const char *key_file,
                               const char *key_passwd);
int flb_tls_destroy(struct flb_tls *tls);
int flb_tls_set_alpn(struct flb_tls *tls, const char *alpn);
int flb_tls_set_verify_client(struct flb_tls *tls, int verify_client);
int flb_tls_set_verify_hostname(struct flb_tls *tls, int verify_hostname);
int flb_tls_load_system_certificates(struct flb_tls *tls);
int flb_tls_set_minmax_proto(struct flb_tls *tls,
                             const char *min_version, const char *max_version);
int flb_tls_set_ciphers(struct flb_tls *tls, const char *ciphers);
struct mk_list *flb_tls_get_config_map(struct flb_config *config);
int flb_tls_session_destroy(struct flb_tls_session *session);
int flb_tls_session_invalidate(struct flb_tls_session *session);
int flb_tls_session_create(struct flb_tls *tls,
                           struct flb_connection *connection,
                           struct flb_coro *co);
const char *flb_tls_session_get_alpn(struct flb_tls_session *session);
int flb_tls_net_read(struct flb_tls_session *session, void *buf, size_t len);
int flb_tls_net_read_async(struct flb_coro *th,
                           struct flb_tls_session *session,
                           void *buf, size_t len);
int flb_tls_net_write(struct flb_tls_session *session,
                      const void *data, size_t len, size_t *out_len);
int flb_tls_net_write_async(struct flb_coro *th,
                            struct flb_tls_session *session,
                            const void *data, size_t len, size_t *out_len);

#endif /* FLB_TLS_H */
