/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>
#include <openssl/x509v3.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    EVP_PKEY_CTX *generator = NULL;
    EVP_PKEY *key = NULL;
    X509 *certificate = NULL;
    X509_EXTENSION *extension = NULL;
    FILE *output = NULL;
    int result = 1;
    if(argc != 3)
        return 2;
    generator = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
    if(!generator || EVP_PKEY_keygen_init(generator) <= 0 ||
            EVP_PKEY_CTX_set_rsa_keygen_bits(generator, 2048) <= 0 ||
            EVP_PKEY_keygen(generator, &key) <= 0)
        goto done;
    certificate = X509_new();
    if(!certificate || !X509_set_version(certificate, 2) ||
            !ASN1_INTEGER_set(X509_get_serialNumber(certificate), 1) ||
            !X509_gmtime_adj(X509_getm_notBefore(certificate), -60) ||
            !X509_gmtime_adj(X509_getm_notAfter(certificate), 86400) ||
            !X509_set_pubkey(certificate, key))
        goto done;
    X509_NAME *name = X509_get_subject_name(certificate);
    if(!X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                (const unsigned char *)"localhost", -1, -1, 0) ||
            !X509_set_issuer_name(certificate, name))
        goto done;
    extension = X509V3_EXT_conf_nid(NULL, NULL, NID_subject_alt_name,
            "DNS:localhost,IP:127.0.0.1");
    if(!extension || !X509_add_ext(certificate, extension, -1) ||
            !X509_sign(certificate, key, EVP_sha256()))
        goto done;
    output = fopen(argv[1], "w");
    if(!output || !PEM_write_PrivateKey(output, key, NULL, NULL, 0, NULL, NULL))
        goto done;
    if(fclose(output) != 0) {
        output = NULL;
        goto done;
    }
    output = fopen(argv[2], "w");
    if(!output || !PEM_write_X509(output, certificate))
        goto done;
    result = 0;
done:
    if(output && fclose(output) != 0)
        result = 1;
    X509_EXTENSION_free(extension);
    X509_free(certificate);
    EVP_PKEY_free(key);
    EVP_PKEY_CTX_free(generator);
    return result;
}
