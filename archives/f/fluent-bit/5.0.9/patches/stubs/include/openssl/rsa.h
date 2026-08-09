#ifndef OPENSSL_RSA_H_STUB
#define OPENSSL_RSA_H_STUB
#include <stddef.h>
/* HarmonyOS stub: FLB_TLS=Off */
typedef struct {} RSA;
#define RSA_PKCS1_PADDING 1
#define RSA_SSLV23_PADDING 2
#define RSA_NO_PADDING 3
#define RSA_PKCS1_OAEP_PADDING 4
#define RSA_X931_PADDING 5
#define RSA_PKCS1_PSS_PADDING 6
static inline void *RSA_new(void) { return NULL; }
static inline void RSA_free(void *r) {}
static inline int RSA_size(const void *r) { (void)r; return 256; }
static inline int RSA_public_encrypt(int flen, const unsigned char *from, unsigned char *to, void *rsa, int pad) { (void)flen;(void)from;(void)to;(void)rsa;(void)pad; return -1; }
static inline int RSA_private_decrypt(int flen, const unsigned char *from, unsigned char *to, void *rsa, int pad) { (void)flen;(void)from;(void)to;(void)rsa;(void)pad; return -1; }
static inline int RSA_generate_key_ex(void *rsa, int bits, void *e, void *cb) { (void)rsa;(void)bits;(void)e;(void)cb; return 1; }
static inline int RSA_check_key(void *rsa) { (void)rsa; return 1; }
static inline int RSA_set0_key(void *rsa, void *n, void *e, void *d) { (void)rsa;(void)n;(void)e;(void)d; return 1; }
static inline void RSA_get0_key(const void *rsa, const void **n, const void **e, const void **d) { (void)rsa;(void)n;(void)e;(void)d; }
#endif
