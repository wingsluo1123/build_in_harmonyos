#ifndef OPENSSL_BIO_H_STUB
#define OPENSSL_BIO_H_STUB
#include <stddef.h>
/* HarmonyOS stub */
typedef struct {} BIO;
static inline void *BIO_new_socket(int fd, int c) { (void)fd;(void)c; return NULL; }
static inline int BIO_write(void *b, const void *d, int l) { (void)b;(void)d; (void)l; return l; }
static inline int BIO_read(void *b, void *d, int l) { (void)b;(void)d;(void)l; return 0; }
static inline int BIO_puts(void *b, const char *s) { (void)b;(void)s; return 0; }
static inline int BIO_free(void *b) { (void)b; return 0; }
static inline void BIO_free_all(void *b) { (void)b; }
static inline void *BIO_new_mem_buf(const void *buf, int len) { (void)buf;(void)len; return NULL; }
#endif
