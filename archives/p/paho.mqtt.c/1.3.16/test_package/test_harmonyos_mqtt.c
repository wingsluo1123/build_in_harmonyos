#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/utsname.h>
#include <unistd.h>

#include "MQTTClient.h"

#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
#include <openssl/ec.h>
#include <openssl/evp.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#endif

#define BODY_CAP 4096
#define TOPIC "paho/harmonyos/port-check"
#define PAYLOAD "mqtt-loopback-on-harmonyos"

struct broker {
    int listener;
    int peer;
    unsigned short port;
    int saw_publish;
    char error[160];
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    SSL_CTX *tls_context;
    SSL *tls_session;
    const char *expected_tls_version;
    char negotiated_tls_version[16];
#endif
};

static int socket_read_fully(int fd, unsigned char *out, size_t length)
{
    size_t done = 0;
    while (done < length) {
        ssize_t n = recv(fd, out + done, length - done, 0);
        if (n == 0)
            return -1;
        if (n < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        done += (size_t)n;
    }
    return 0;
}

static int socket_write_fully(int fd, const unsigned char *data, size_t length)
{
    size_t done = 0;
    while (done < length) {
        ssize_t n = send(fd, data + done, length - done, 0);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        done += (size_t)n;
    }
    return 0;
}

static int broker_read_fully(struct broker *b, unsigned char *out, size_t length)
{
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    if (b->tls_session != NULL) {
        size_t done = 0;
        while (done < length) {
            int n = SSL_read(b->tls_session, out + done,
                             (int)((length - done) > 0x7fffffff ? 0x7fffffff : length - done));
            if (n <= 0)
                return -1;
            done += (size_t)n;
        }
        return 0;
    }
#endif
    return socket_read_fully(b->peer, out, length);
}

static int broker_write_fully(struct broker *b, const unsigned char *data, size_t length)
{
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    if (b->tls_session != NULL) {
        size_t done = 0;
        while (done < length) {
            int n = SSL_write(b->tls_session, data + done,
                              (int)((length - done) > 0x7fffffff ? 0x7fffffff : length - done));
            if (n <= 0)
                return -1;
            done += (size_t)n;
        }
        return 0;
    }
#endif
    return socket_write_fully(b->peer, data, length);
}

static int read_packet(struct broker *b, unsigned char *header,
                       unsigned char *body, size_t capacity, size_t *length)
{
    unsigned char byte;
    size_t multiplier = 1;
    unsigned int count = 0;
    *length = 0;
    if (broker_read_fully(b, header, 1) != 0)
        return -1;
    do {
        if (broker_read_fully(b, &byte, 1) != 0 || count++ == 4)
            return -1;
        *length += (size_t)(byte & 0x7f) * multiplier;
        multiplier *= 128;
    } while ((byte & 0x80) != 0);
    if (*length > capacity)
        return -1;
    return broker_read_fully(b, body, *length);
}

static void fail_broker(struct broker *b, const char *why)
{
    (void)snprintf(b->error, sizeof(b->error), "%s", why);
}

static void *broker_main(void *arg)
{
    struct broker *b = (struct broker *)arg;
    struct timeval timeout = {15, 0};
    fd_set set;
    unsigned char header, body[BODY_CAP];
    size_t length;
    const unsigned char connack[] = {0x20, 0x02, 0x00, 0x00};

    FD_ZERO(&set);
    FD_SET(b->listener, &set);
    if (select(b->listener + 1, &set, NULL, NULL, &timeout) <= 0) {
        fail_broker(b, "timed out waiting for MQTT client");
        return NULL;
    }
    b->peer = accept(b->listener, NULL, NULL);
    if (b->peer < 0) {
        fail_broker(b, "accept failed");
        return NULL;
    }
    (void)setsockopt(b->peer, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    if (b->tls_context != NULL) {
        b->tls_session = SSL_new(b->tls_context);
        if (b->tls_session == NULL || SSL_set_fd(b->tls_session, b->peer) != 1 ||
            SSL_accept(b->tls_session) != 1) {
            fail_broker(b, "TLS server handshake failed");
            goto done;
        }
        (void)snprintf(b->negotiated_tls_version, sizeof(b->negotiated_tls_version),
                       "%s", SSL_get_version(b->tls_session));
        if (strcmp(b->negotiated_tls_version, b->expected_tls_version) != 0) {
            fail_broker(b, "TLS protocol version did not match the test case");
            goto done;
        }
    }
#endif

    if (read_packet(b, &header, body, sizeof(body), &length) != 0 ||
        header != 0x10 || length < 8 || memcmp(body, "\x00\x04MQTT\x04", 7) != 0) {
        fail_broker(b, "invalid MQTT 3.1.1 CONNECT");
        goto done;
    }
    if (broker_write_fully(b, connack, sizeof(connack)) != 0) {
        fail_broker(b, "failed to send CONNACK");
        goto done;
    }

    for (;;) {
        if (read_packet(b, &header, body, sizeof(body), &length) != 0) {
            fail_broker(b, "client closed before MQTT DISCONNECT");
            goto done;
        }
        if (header == 0xc0 && length == 0) {
            const unsigned char pingresp[] = {0xd0, 0x00};
            if (broker_write_fully(b, pingresp, sizeof(pingresp)) != 0) {
                fail_broker(b, "failed to send PINGRESP");
                goto done;
            }
            continue;
        }
        if (header == 0x30) {
            size_t topic_len;
            size_t payload_at;
            if (length < 2) {
                fail_broker(b, "PUBLISH packet omitted topic");
                goto done;
            }
            topic_len = ((size_t)body[0] << 8) | body[1];
            payload_at = 2 + topic_len;
            if (topic_len != sizeof(TOPIC) - 1 || length < payload_at ||
                memcmp(body + 2, TOPIC, sizeof(TOPIC) - 1) != 0 ||
                length - payload_at != sizeof(PAYLOAD) - 1 ||
                memcmp(body + payload_at, PAYLOAD, sizeof(PAYLOAD) - 1) != 0) {
                fail_broker(b, "PUBLISH topic/payload mismatch");
                goto done;
            }
            b->saw_publish = 1;
            continue;
        }
        if (header == 0xe0 && length == 0)
            goto done;
        fail_broker(b, "unexpected MQTT packet");
        goto done;
    }

done:
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    if (b->tls_session != NULL) {
        (void)SSL_shutdown(b->tls_session);
        SSL_free(b->tls_session);
        b->tls_session = NULL;
    }
#endif
    if (b->peer >= 0) {
        close(b->peer);
        b->peer = -1;
    }
    return NULL;
}

static int start_broker(struct broker *b)
{
    struct sockaddr_in address;
    socklen_t address_len = sizeof(address);
    int reuse = 1;
    memset(b, 0, sizeof(*b));
    b->listener = -1;
    b->peer = -1;
    b->listener = socket(AF_INET, SOCK_STREAM, 0);
    if (b->listener < 0)
        return -1;
    (void)setsockopt(b->listener, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = 0;
    if (bind(b->listener, (struct sockaddr *)&address, sizeof(address)) != 0 ||
        listen(b->listener, 1) != 0 ||
        getsockname(b->listener, (struct sockaddr *)&address, &address_len) != 0) {
        close(b->listener);
        b->listener = -1;
        return -1;
    }
    b->port = ntohs(address.sin_port);
    return 0;
}

#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
static SSL_CTX *create_tls_server_context(int protocol_version)
{
    SSL_CTX *context = NULL;
    EVP_PKEY_CTX *key_context = NULL;
    EVP_PKEY *key = NULL;
    X509 *certificate = NULL;
    X509_NAME *subject;

    context = SSL_CTX_new(TLS_server_method());
    if (context == NULL ||
        SSL_CTX_set_min_proto_version(context, protocol_version) != 1 ||
        SSL_CTX_set_max_proto_version(context, protocol_version) != 1)
        goto error;

    key_context = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (key_context == NULL || EVP_PKEY_keygen_init(key_context) <= 0 ||
        EVP_PKEY_CTX_set_ec_paramgen_curve_nid(key_context, NID_X9_62_prime256v1) <= 0 ||
        EVP_PKEY_keygen(key_context, &key) <= 0)
        goto error;

    certificate = X509_new();
    if (certificate == NULL || X509_set_version(certificate, 2) != 1 ||
        ASN1_INTEGER_set(X509_get_serialNumber(certificate), 1) != 1 ||
        X509_gmtime_adj(X509_get_notBefore(certificate), 0) == NULL ||
        X509_gmtime_adj(X509_get_notAfter(certificate), 3600) == NULL ||
        X509_set_pubkey(certificate, key) != 1)
        goto error;
    subject = X509_get_subject_name(certificate);
    if (subject == NULL ||
        X509_NAME_add_entry_by_txt(subject, "CN", MBSTRING_ASC,
                                   (const unsigned char *)"localhost", -1, -1, 0) != 1 ||
        X509_set_issuer_name(certificate, subject) != 1 ||
        X509_sign(certificate, key, EVP_sha256()) <= 0 ||
        SSL_CTX_use_certificate(context, certificate) != 1 ||
        SSL_CTX_use_PrivateKey(context, key) != 1 ||
        SSL_CTX_check_private_key(context) != 1)
        goto error;

    X509_free(certificate);
    EVP_PKEY_free(key);
    EVP_PKEY_CTX_free(key_context);
    return context;

error:
    X509_free(certificate);
    EVP_PKEY_free(key);
    EVP_PKEY_CTX_free(key_context);
    SSL_CTX_free(context);
    return NULL;
}
#endif

static int run_mqtt_roundtrip(const char *case_name
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
                              , SSL_CTX *tls_context, int ssl_version,
                              const char *expected_tls_version
#endif
                              )
{
    struct broker broker;
    pthread_t thread;
    MQTTClient client = NULL;
    MQTTClient_connectOptions options = MQTTClient_connectOptions_initializer;
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    MQTTClient_SSLOptions ssl_options = MQTTClient_SSLOptions_initializer;
#endif
    char uri[96];
    int thread_started = 0, connected = 0, result = EXIT_FAILURE;
    int rc;

    if (start_broker(&broker) != 0) {
        perror("start_broker");
        return EXIT_FAILURE;
    }
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    broker.tls_context = tls_context;
    broker.expected_tls_version = expected_tls_version;
#endif
    if (pthread_create(&thread, NULL, broker_main, &broker) != 0) {
        fprintf(stderr, "pthread_create failed\n");
        close(broker.listener);
        return EXIT_FAILURE;
    }
    thread_started = 1;
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    (void)snprintf(uri, sizeof(uri), "%s://127.0.0.1:%u",
                   tls_context == NULL ? "tcp" : "ssl", broker.port);
#else
    (void)snprintf(uri, sizeof(uri), "tcp://127.0.0.1:%u", broker.port);
#endif
    rc = MQTTClient_create(&client, uri, "paho_harmonyos_smoke",
                           MQTTCLIENT_PERSISTENCE_NONE, NULL);
    if (rc != MQTTCLIENT_SUCCESS) {
        fprintf(stderr, "%s: MQTTClient_create failed: %d\n", case_name, rc);
        goto done;
    }
    options.keepAliveInterval = 10;
    options.cleansession = 1;
    options.connectTimeout = 8;
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    if (tls_context != NULL) {
        ssl_options.struct_version = 5;
        ssl_options.enableServerCertAuth = 0;
        ssl_options.verify = 0;
        ssl_options.sslVersion = ssl_version;
        options.ssl = &ssl_options;
    }
#endif
    rc = MQTTClient_connect(client, &options);
    if (rc != MQTTCLIENT_SUCCESS) {
        fprintf(stderr, "%s: MQTTClient_connect failed: %d\n", case_name, rc);
        goto done;
    }
    connected = 1;
    rc = MQTTClient_publish(client, TOPIC, (int)(sizeof(PAYLOAD) - 1),
                            PAYLOAD, 0, 0, NULL);
    if (rc != MQTTCLIENT_SUCCESS) {
        fprintf(stderr, "%s: MQTTClient_publish failed: %d\n", case_name, rc);
        goto done;
    }
    rc = MQTTClient_disconnect(client, 2000);
    connected = 0;
    if (rc != MQTTCLIENT_SUCCESS) {
        fprintf(stderr, "%s: MQTTClient_disconnect failed: %d\n", case_name, rc);
        goto done;
    }
    result = EXIT_SUCCESS;

done:
    if (connected)
        (void)MQTTClient_disconnect(client, 1000);
    if (client != NULL)
        MQTTClient_destroy(&client);
    if (thread_started)
        (void)pthread_join(thread, NULL);
    close(broker.listener);
    if (result == EXIT_SUCCESS && broker.error[0] != '\0') {
        fprintf(stderr, "%s: embedded MQTT broker failed: %s\n",
                case_name, broker.error);
        result = EXIT_FAILURE;
    }
    if (result == EXIT_SUCCESS && !broker.saw_publish) {
        fprintf(stderr, "%s: broker did not observe MQTT PUBLISH\n", case_name);
        result = EXIT_FAILURE;
    }
    if (result == EXIT_SUCCESS) {
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
        if (tls_context != NULL)
            printf("%s: negotiated %s; MQTT CONNECT/PUBLISH/DISCONNECT passed\n",
                   case_name, broker.negotiated_tls_version);
        else
#endif
            printf("%s: MQTT CONNECT/PUBLISH/DISCONNECT passed\n", case_name);
    }
    return result;
}

int main(void)
{
    struct utsname info;
    if (uname(&info) != 0) {
        perror("uname");
        return EXIT_FAILURE;
    }
    printf("HarmonyOS platform probe: sysname=%s release=%s machine=%s\n",
           info.sysname, info.release, info.machine);
    if (strncmp(info.sysname, "HarmonyOS", 9) != 0 &&
        strstr(info.release, "HongMeng") == NULL) {
        fprintf(stderr, "HarmonyOS/HongMeng uname signature missing\n");
        return EXIT_FAILURE;
    }

    if (run_mqtt_roundtrip("plain MQTT"
#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
                           , NULL, MQTT_SSL_VERSION_DEFAULT, NULL
#endif
                           ) != EXIT_SUCCESS)
        return EXIT_FAILURE;

#if defined(PAHO_TEST_WITH_SSL) && PAHO_TEST_WITH_SSL
    {
        SSL_CTX *context = create_tls_server_context(TLS1_2_VERSION);
        int result;
        if (context == NULL) {
            fprintf(stderr, "could not create TLS 1.2 loopback certificate/context\n");
            return EXIT_FAILURE;
        }
        result = run_mqtt_roundtrip("Paho ssl:// with TLS 1.2", context,
                                    MQTT_SSL_VERSION_TLS_1_2, "TLSv1.2");
        SSL_CTX_free(context);
        if (result != EXIT_SUCCESS)
            return result;
    }
    {
        SSL_CTX *context = create_tls_server_context(TLS1_3_VERSION);
        int result;
        if (context == NULL) {
            fprintf(stderr, "could not create TLS 1.3 loopback certificate/context\n");
            return EXIT_FAILURE;
        }
        result = run_mqtt_roundtrip("Paho ssl:// with TLS 1.3", context,
                                    MQTT_SSL_VERSION_DEFAULT, "TLSv1.3");
        SSL_CTX_free(context);
        if (result != EXIT_SUCCESS)
            return result;
    }
#endif

    printf("HarmonyOS network/TLS integration test: passed\n");
    return EXIT_SUCCESS;
}
