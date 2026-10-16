/* Independent consumer of the installed Pathrate sender protocol. */
#include <arpa/inet.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/utsname.h>
#include <unistd.h>

enum { TRAIN_LEN=1, GAME_OVER=3, ACK_TRAIN=4, PCK_LEN=5,
       MAX_PCK_LEN=6, SEND=7, TRAIN_SPACING=9, SENT_TRAIN=16 };

static void require(int ok, const char *what)
{
    if (!ok) {
        fprintf(stderr, "consumer failure: %s (errno=%d)\n", what, errno);
        exit(EXIT_FAILURE);
    }
}

static void control_send(int fd, uint32_t code)
{
    /* Upstream 2.4.1 transmits sizeof(long), including on AArch64. */
    long wire = (long)htonl(code);
    const char *p = (const char *)&wire;
    size_t left = sizeof(wire);
    while (left) {
        ssize_t n = send(fd, p, left, 0);
        if (n < 0 && errno == EINTR) continue;
        require(n > 0, "write TCP control frame");
        p += n;
        left -= (size_t)n;
    }
}

static uint32_t control_receive(int fd)
{
    long wire = 0;
    char *p = (char *)&wire;
    size_t left = sizeof(wire);
    while (left) {
        ssize_t n = recv(fd, p, left, 0);
        if (n < 0 && errno == EINTR) continue;
        require(n > 0, "read TCP control frame");
        p += n;
        left -= (size_t)n;
    }
    return ntohl((uint32_t)wire);
}

static uint32_t packet_field(const unsigned char *packet, size_t index)
{
    long value;
    memcpy(&value, packet + index * sizeof(long), sizeof(value));
    return ntohl((uint32_t)value);
}

int main(int argc, char **argv)
{
    const unsigned lengths[] = {4, 8};
    const unsigned sizes[] = {256, 1024};
    struct utsname system;
    struct sockaddr_in address;
    struct timeval timeout = {5, 0};
    unsigned total_packets = 0, total_bytes = 0;
    unsigned char packet[2048];
    FILE *report;
    int tcp, udp;

    require(argc == 2, "report path argument");
    require(uname(&system) == 0 && strcmp(system.sysname, "HarmonyOS") == 0,
            "run on actual HarmonyOS PC");
    udp = socket(AF_INET, SOCK_DGRAM, 0);
    tcp = socket(AF_INET, SOCK_STREAM, 0);
    require(udp >= 0 && tcp >= 0, "create real UDP and TCP sockets");
    require(setsockopt(udp, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0,
            "UDP receive deadline");
    require(setsockopt(tcp, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) == 0,
            "TCP receive deadline");
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = htons(48698);
    require(bind(udp, (struct sockaddr *)&address, sizeof(address)) == 0,
            "bind consumer UDP data endpoint");
    address.sin_port = htons(48699);
    require(connect(tcp, (struct sockaddr *)&address, sizeof(address)) == 0,
            "connect installed sender TCP control endpoint");

    for (unsigned i = 0; i < 10; ++i) {
        control_send(tcp, 0);
        require(control_receive(tcp) == 0, "round-trip echo handshake");
    }
    report = fopen(argv[1], "w");
    require(report != NULL, "create report in HarmonyOS user storage");
    require(fprintf(report, "pathrate-consumer-v1\nrtt_echoes=10\n") > 0,
            "write handshake result");
    control_send(tcp, MAX_PCK_LEN | (1024u << 8));
    control_send(tcp, TRAIN_SPACING | (20u << 8));
    for (unsigned train = 0; train < 2; ++train) {
        unsigned bytes = 0;
        unsigned round = 41 + train;
        control_send(tcp, PCK_LEN | (sizes[train] << 8));
        control_send(tcp, TRAIN_LEN | (lengths[train] << 8));
        control_send(tcp, SEND | (round << 8));
        for (unsigned id = 0; id <= lengths[train]; ++id) {
            ssize_t n = recv(udp, packet, sizeof(packet), 0);
            require(n == (ssize_t)sizes[train], "receive configured UDP packet length");
            require(packet_field(packet, 0) == id, "ordered packet id");
            require(packet_field(packet, 1) == train + 1, "sender train id");
            require(packet_field(packet, 2) == round, "requested round id");
            bytes += (unsigned)n;
            ++total_packets;
        }
        require(control_receive(tcp) == SENT_TRAIN, "sender completed packet train");
        control_send(tcp, ACK_TRAIN);
        require(fprintf(report, "round=%u train=%u packets=%u packet_bytes=%u received_bytes=%u\n",
                        round, train + 1, lengths[train] + 1, sizes[train], bytes) > 0,
                "write real transfer result");
        total_bytes += bytes;
    }
    control_send(tcp, GAME_OVER);
    require(fprintf(report, "trains=2 packets=%u received_bytes=%u\n",
                    total_packets, total_bytes) > 0, "write transfer totals");
    require(fclose(report) == 0, "persist consumer report");
    close(tcp);
    close(udp);
    printf("CONSUMER COMPLETE: 10 echoes, 2 trains, %u packets, %u bytes\n",
           total_packets, total_bytes);
    return EXIT_SUCCESS;
}
