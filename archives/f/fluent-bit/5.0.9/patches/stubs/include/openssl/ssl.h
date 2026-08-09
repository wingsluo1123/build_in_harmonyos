#ifndef OPENSSL_SSL_H_STUB
#define OPENSSL_SSL_H_STUB
/* HarmonyOS stub: FLB_TLS=Off */
typedef struct {} SSL;
typedef struct {} SSL_CTX;
typedef struct {} SSL_METHOD;
typedef struct {} X509;
typedef struct {} X509_STORE;
typedef struct {} BIO;
typedef struct {} SSL_SESSION;
#define SSL_VERIFY_NONE 0
static inline void SSL_load_error_strings(void) {}
static inline int SSL_library_init(void) { return 1; }
static inline void *SSLv23_client_method(void) { return NULL; }
static inline void *TLS_client_method(void) { return NULL; }
static inline void *SSL_CTX_new(void *m) { return NULL; }
static inline void SSL_CTX_free(void *ctx) {}
static inline void *SSL_new(void *ctx) { return NULL; }
static inline void SSL_free(void *s) {}
static inline int SSL_set_fd(void *s, int fd) { return 1; }
static inline int SSL_connect(void *s) { return 1; }
static inline int SSL_write(void *s, const void *b, int n) { return n; }
static inline int SSL_read(void *s, void *b, int n) { return 0; }
static inline int SSL_get_error(void *s, int r) { return 0; }
static inline void *SSL_get_peer_certificate(void *s) { return NULL; }
static inline void X509_free(void *x) {}
static inline void *X509_get_subject_name(void *x) { return NULL; }
static inline int X509_NAME_get_text_by_NID(void *n, int nid, char *b, int l) { return 0; }
#endif
