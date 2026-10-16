#include <srtp2/srtp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #expr); exit(1); } } while (0)

int main(void) {
    uint8_t key[30] = {0};
    const uint8_t plain[] = {0x80,0x60,0,1,0,0,0,1,0xca,0xfe,0xba,0xbe,1,2,3,0,255};
    _Alignas(4) uint8_t packet[256], encrypted[256], damaged[256], rtcp[256];
    const uint8_t plain_rtcp[] = {0x80,0xc8,0,3,0xca,0xfe,0xba,0xbe,0,1,2,3,4,5,6,7};
    int length = sizeof plain, encrypted_length, tampered_length, rtcp_length = sizeof plain_rtcp;
    srtp_policy_t policy;
    srtp_t tx = NULL, rx = NULL;
    memset(&policy, 0, sizeof policy);
    for (size_t i = 0; i < sizeof key; ++i) key[i] = (uint8_t)(i + 1);
    srtp_crypto_policy_set_rtp_default(&policy.rtp);
    srtp_crypto_policy_set_rtcp_default(&policy.rtcp);
    policy.ssrc.type = ssrc_specific;
    policy.ssrc.value = 0xcafebabe;
    policy.key = key;
    policy.window_size = 128;
    CHECK(srtp_init() == srtp_err_status_ok);
    CHECK(srtp_create(&tx, &policy) == srtp_err_status_ok);
    CHECK(srtp_create(&rx, &policy) == srtp_err_status_ok);
    memcpy(packet, plain, sizeof plain);
    CHECK(srtp_protect(tx, packet, &length) == srtp_err_status_ok);
    CHECK(length > (int)sizeof plain && length <= (int)sizeof packet);
    encrypted_length = length;
    memcpy(encrypted, packet, length);
    memcpy(damaged, packet, length);
    damaged[12] ^= 0x80;
    tampered_length = length;
    CHECK(srtp_unprotect(rx, damaged, &tampered_length) == srtp_err_status_auth_fail);
    CHECK(srtp_unprotect(rx, packet, &length) == srtp_err_status_ok);
    CHECK(length == (int)sizeof plain && memcmp(packet, plain, sizeof plain) == 0);
    memcpy(packet, encrypted, encrypted_length);
    length = encrypted_length;
    CHECK(srtp_unprotect(rx, packet, &length) == srtp_err_status_replay_fail);
    memcpy(rtcp, plain_rtcp, sizeof plain_rtcp);
    CHECK(srtp_protect_rtcp(tx, rtcp, &rtcp_length) == srtp_err_status_ok);
    CHECK(srtp_unprotect_rtcp(rx, rtcp, &rtcp_length) == srtp_err_status_ok);
    CHECK(rtcp_length == (int)sizeof plain_rtcp && memcmp(rtcp, plain_rtcp, sizeof plain_rtcp) == 0);
#ifdef __OHOS__
    const char *tmp = getenv("TMPDIR");
    char file_path[1024];
    CHECK(tmp != NULL && tmp[0] == '/' && strncmp(tmp, "/tmp/", 5) != 0);
    CHECK(snprintf(file_path, sizeof file_path, "%s/srtp-%ld.bin", tmp, (long)getpid()) < (int)sizeof file_path);
    FILE *file = fopen(file_path, "wx");
    CHECK(file != NULL);
    CHECK(fwrite(encrypted, 1, encrypted_length, file) == (size_t)encrypted_length && fclose(file) == 0);
    file = fopen(file_path, "rb");
    CHECK(file != NULL);
    CHECK(fread(damaged, 1, sizeof damaged, file) == (size_t)encrypted_length && fclose(file) == 0);
    CHECK(memcmp(damaged, encrypted, encrypted_length) == 0 && unlink(file_path) == 0);
    puts("OHOS_PRIVATE_ENCRYPTED_PACKET_FILE_ROUNDTRIP_PASS");
#endif
    CHECK(srtp_dealloc(tx) == srtp_err_status_ok && srtp_dealloc(rx) == srtp_err_status_ok);
    CHECK(srtp_shutdown() == srtp_err_status_ok);
    puts("SRTP_SRTCP_AUTHENTICATION_REPLAY_PASS");
    return 0;
}
