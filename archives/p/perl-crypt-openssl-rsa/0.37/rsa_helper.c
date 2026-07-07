/*
 * rsa_helper.c — HarmonyOS SELinux workaround for Crypt::OpenSSL::RSA
 *
 * Problem: OHOS SELinux (hishell_hap:s0) blocks dlopen() of .so files,
 *   making the Perl XS module RSA.so unloadable at runtime.
 * Solution: This standalone executable links libssl/libcrypto at compile
 *   time (loaded by the linker at startup, bypassing SELinux dlopen check).
 *   Perl communicates via command-line + stdin/stdout IPC.
 *
 * Build: clang -o rsa_helper rsa_helper.c -lssl -lcrypto -I<openssl_include>
 *
 * Usage:
 *   rsa_helper generate <bits>           → outputs PEM private key
 *   rsa_helper pubkey <pem_priv>         → extracts public key from private
 *   rsa_helper size <pem_key>            → outputs key size in bytes
 *   rsa_helper sign <hash> <pem_priv>    → reads message from stdin, outputs base64 sig
 *   rsa_helper verify <hash> <pem_pub> <b64_sig> → reads message from stdin, outputs OK/FAIL
 *   rsa_helper encrypt <pad> <pem_pub>   → reads plaintext from stdin, outputs base64 ciphertext
 *   rsa_helper decrypt <pad> <pem_priv>  → reads base64 ciphertext from stdin, outputs plaintext
 *
 * hash: md5|sha1|sha256|sha512
 * pad:  pkcs1|oaep|sslv23|none
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/rsa.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/bio.h>
#include <openssl/buffer.h>

/* ---- Base64 helpers ---- */
static char *b64_encode(const unsigned char *data, int len) {
    BIO *b64 = BIO_new(BIO_f_base64());
    BIO *mem = BIO_new(BIO_s_mem());
    b64 = BIO_push(b64, mem);
    BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);
    BIO_write(b64, data, len);
    BIO_flush(b64);
    BUF_MEM *bptr;
    BIO_get_mem_ptr(b64, &bptr);
    char *out = malloc(bptr->length + 1);
    if (!out) { BIO_free_all(b64); return NULL; }
    memcpy(out, bptr->data, bptr->length);
    out[bptr->length] = '\0';
    BIO_free_all(b64);
    return out;
}

static unsigned char *b64_decode(const char *input, int *out_len) {
    int len = strlen(input);
    unsigned char *buf = malloc(len);
    if (!buf) return NULL;
    BIO *b64 = BIO_new(BIO_f_base64());
    BIO *mem = BIO_new_mem_buf(input, len);
    b64 = BIO_push(b64, mem);
    BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);
    *out_len = BIO_read(b64, buf, len);
    BIO_free_all(b64);
    return buf;
}

/* ---- Read all stdin ---- */
static unsigned char *read_stdin(int *out_len) {
    int cap = 65536, len = 0;
    unsigned char *buf = malloc(cap);
    if (!buf) return NULL;
    int n;
    while ((n = fread(buf + len, 1, cap - len, stdin)) > 0) {
        len += n;
        if (len >= cap) {
            cap *= 2;
            unsigned char *tmp = realloc(buf, cap);
            if (!tmp) { free(buf); return NULL; }
            buf = tmp;
        }
    }
    if (ferror(stdin)) { free(buf); return NULL; }
    *out_len = len;
    return buf;
}

/* ---- PEM key parsing ---- */
static RSA *load_priv_key(const char *pem) {
    BIO *bio = BIO_new_mem_buf(pem, -1);
    RSA *rsa = PEM_read_bio_RSAPrivateKey(bio, NULL, NULL, NULL);
    BIO_free(bio);
    return rsa;
}

static RSA *load_pub_key(const char *pem) {
    BIO *bio = BIO_new_mem_buf(pem, -1);
    RSA *rsa = PEM_read_bio_RSA_PUBKEY(bio, NULL, NULL, NULL);
    if (!rsa) {
        BIO_reset(bio);
        rsa = PEM_read_bio_RSAPublicKey(bio, NULL, NULL, NULL);
    }
    BIO_free(bio);
    return rsa;
}

/* ---- Hash name to NID ---- */
static int hash_to_nid(const char *name) {
    if (strcmp(name, "md5") == 0) return NID_md5;
    if (strcmp(name, "sha1") == 0) return NID_sha1;
    if (strcmp(name, "sha256") == 0) return NID_sha256;
    if (strcmp(name, "sha512") == 0) return NID_sha512;
    if (strcmp(name, "sha384") == 0) return NID_sha384;
    return NID_sha256;
}

/* ---- Padding name to RSA padding constant ---- */
static int pad_to_const(const char *name) {
    if (strcmp(name, "pkcs1") == 0) return RSA_PKCS1_PADDING;
    if (strcmp(name, "oaep") == 0) return RSA_PKCS1_OAEP_PADDING;
    /* SSLv23 padding removed in OpenSSL 3.x */
    if (strcmp(name, "none") == 0) return RSA_NO_PADDING;
    return RSA_PKCS1_PADDING;
}

/* ---- Main dispatch ---- */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: rsa_helper <command> [args]\n");
        return 1;
    }

    const char *cmd = argv[1];
    ERR_load_crypto_strings();

    if (strcmp(cmd, "generate") == 0) {
        if (argc < 3) { fprintf(stderr, "Need bits\n"); return 1; }
        int bits = atoi(argv[2]);
        unsigned long e = RSA_F4;
        RSA *rsa = RSA_new();
        BIGNUM *bn = BN_new();
        BN_set_word(bn, e);
        if (RSA_generate_key_ex(rsa, bits, bn, NULL) != 1) {
            fprintf(stderr, "RSA_generate_key_ex failed: %s\n",
                    ERR_error_string(ERR_get_error(), NULL));
            RSA_free(rsa); BN_free(bn);
            return 1;
        }
        BN_free(bn);

        BIO *out = BIO_new(BIO_s_mem());
        PEM_write_bio_RSAPrivateKey(out, rsa, NULL, NULL, 0, NULL, NULL);
        BUF_MEM *bptr;
        BIO_get_mem_ptr(out, &bptr);
        fwrite(bptr->data, 1, bptr->length, stdout);
        BIO_free(out);
        RSA_free(rsa);
        return 0;
    }

    if (strcmp(cmd, "pubkey") == 0) {
        if (argc < 3) { fprintf(stderr, "Need PEM private key\n"); return 1; }
        RSA *rsa = load_priv_key(argv[2]);
        if (!rsa) { fprintf(stderr, "Bad private key: %s\n",
                            ERR_error_string(ERR_get_error(), NULL)); return 1; }
        BIO *out = BIO_new(BIO_s_mem());
        PEM_write_bio_RSA_PUBKEY(out, rsa);
        BUF_MEM *bptr;
        BIO_get_mem_ptr(out, &bptr);
        fwrite(bptr->data, 1, bptr->length, stdout);
        BIO_free(out);
        RSA_free(rsa);
        return 0;
    }

    if (strcmp(cmd, "size") == 0) {
        if (argc < 3) { fprintf(stderr, "Need PEM key\n"); return 1; }
        RSA *rsa = load_priv_key(argv[2]);
        if (!rsa) rsa = load_pub_key(argv[2]);
        if (!rsa) { fprintf(stderr, "Bad key: %s\n",
                            ERR_error_string(ERR_get_error(), NULL)); return 1; }
        printf("%d\n", RSA_size(rsa));
        RSA_free(rsa);
        return 0;
    }

    if (strcmp(cmd, "sign") == 0) {
        if (argc < 4) { fprintf(stderr, "Usage: sign <hash> <pem_priv>\n"); return 1; }
        const char *hash_name = argv[2];
        RSA *rsa = load_priv_key(argv[3]);
        if (!rsa) { fprintf(stderr, "Bad private key: %s\n",
                            ERR_error_string(ERR_get_error(), NULL)); return 1; }

        int msg_len;
        unsigned char *msg = read_stdin(&msg_len);

        /* Hash the message */
        const EVP_MD *md = EVP_get_digestbyname(hash_name);
        if (!md) { fprintf(stderr, "Unknown hash: %s\n", hash_name); free(msg); RSA_free(rsa); return 1; }
        unsigned char digest[EVP_MAX_MD_SIZE];
        unsigned int digest_len;
        EVP_Digest(msg, msg_len, digest, &digest_len, md, NULL);

        /* Sign */
        unsigned char *sig = malloc(RSA_size(rsa));
        if (!sig) { free(msg); RSA_free(rsa); return 1; }
        unsigned int sig_len;
        if (RSA_sign(hash_to_nid(hash_name), digest, digest_len,
                     sig, &sig_len, rsa) != 1) {
            fprintf(stderr, "RSA_sign failed: %s\n",
                    ERR_error_string(ERR_get_error(), NULL));
            free(sig); free(msg); RSA_free(rsa);
            return 1;
        }
        char *b64 = b64_encode(sig, sig_len);
        printf("%s\n", b64);
        free(b64); free(sig); free(msg);
        RSA_free(rsa);
        return 0;
    }

    if (strcmp(cmd, "verify") == 0) {
        if (argc < 5) { fprintf(stderr, "Usage: verify <hash> <pem_pub> <b64_sig>\n"); return 1; }
        const char *hash_name = argv[2];
        RSA *rsa = load_pub_key(argv[3]);
        if (!rsa) { fprintf(stderr, "Bad public key: %s\n",
                            ERR_error_string(ERR_get_error(), NULL)); return 1; }

        int sig_len;
        unsigned char *sig = b64_decode(argv[4], &sig_len);

        int msg_len;
        unsigned char *msg = read_stdin(&msg_len);

        const EVP_MD *md = EVP_get_digestbyname(hash_name);
        if (!md) { fprintf(stderr, "Unknown hash: %s\n", hash_name); free(sig); free(msg); RSA_free(rsa); return 1; }
        unsigned char digest[EVP_MAX_MD_SIZE];
        unsigned int digest_len;
        EVP_Digest(msg, msg_len, digest, &digest_len, md, NULL);

        int ok = RSA_verify(hash_to_nid(hash_name), digest, digest_len,
                            sig, sig_len, rsa);
        printf("%s\n", ok ? "OK" : "FAIL");
        free(sig); free(msg);
        RSA_free(rsa);
        return ok ? 0 : 1;
    }

    if (strcmp(cmd, "encrypt") == 0) {
        if (argc < 4) { fprintf(stderr, "Usage: encrypt <pad> <pem_pub>\n"); return 1; }
        int padding = pad_to_const(argv[2]);
        RSA *rsa = load_pub_key(argv[3]);
        if (!rsa) { fprintf(stderr, "Bad public key: %s\n",
                            ERR_error_string(ERR_get_error(), NULL)); return 1; }

        int pt_len;
        unsigned char *pt = read_stdin(&pt_len);

        unsigned char *ct = malloc(RSA_size(rsa));
        if (!ct) { free(pt); RSA_free(rsa); return 1; }
        int ct_len = RSA_public_encrypt(pt_len, pt, ct, rsa, padding);
        if (ct_len < 0) {
            fprintf(stderr, "RSA_public_encrypt failed: %s\n",
                    ERR_error_string(ERR_get_error(), NULL));
            free(ct); free(pt); RSA_free(rsa);
            return 1;
        }
        char *b64 = b64_encode(ct, ct_len);
        printf("%s\n", b64);
        free(b64); free(ct); free(pt);
        RSA_free(rsa);
        return 0;
    }

    if (strcmp(cmd, "decrypt") == 0) {
        if (argc < 4) { fprintf(stderr, "Usage: decrypt <pad> <pem_priv>\n"); return 1; }
        int padding = pad_to_const(argv[2]);
        RSA *rsa = load_priv_key(argv[3]);
        if (!rsa) { fprintf(stderr, "Bad private key: %s\n",
                            ERR_error_string(ERR_get_error(), NULL)); return 1; }

        int b64_len;
        unsigned char *b64_buf = read_stdin(&b64_len);
        /* Strip trailing newline */
        while (b64_len > 0 && (b64_buf[b64_len-1] == '\n' || b64_buf[b64_len-1] == '\r'))
            b64_buf[--b64_len] = '\0';

        int ct_len;
        unsigned char *ct = b64_decode((char *)b64_buf, &ct_len);

        unsigned char *pt = malloc(RSA_size(rsa));
        if (!pt) { free(ct); free(b64_buf); RSA_free(rsa); return 1; }
        int pt_len = RSA_private_decrypt(ct_len, ct, pt, rsa, padding);
        if (pt_len < 0) {
            fprintf(stderr, "RSA_private_decrypt failed: %s\n",
                    ERR_error_string(ERR_get_error(), NULL));
            free(pt); free(ct); free(b64_buf); RSA_free(rsa);
            return 1;
        }
        fwrite(pt, 1, pt_len, stdout);
        free(pt); free(ct); free(b64_buf);
        RSA_free(rsa);
        return 0;
    }

    fprintf(stderr, "Unknown command: %s\n", cmd);
    return 1;
}
