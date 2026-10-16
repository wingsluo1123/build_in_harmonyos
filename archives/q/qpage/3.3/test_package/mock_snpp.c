/*
** mock_snpp.c - a minimal SNPP (RFC 1861) server used by the qpage consumer test.
**
** It listens on 127.0.0.1:<port>, accepts a single connection, answers the
** SNPP commands the qpage client sends and logs every received line to
** <logfile>.  This lets the test assert the exact on-the-wire command
** sequence (CALLerid/PAGEr/DATA/SEND/QUIT, plus HOLDuntil/COVErage/LEVEl).
**
** Usage: mock_snpp <port> <logfile>
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>

static int starts_with_ci(const char *s, const char *prefix)
{
    size_t i;
    for (i = 0; prefix[i]; i++) {
        char a = s[i];
        char b = prefix[i];
        if (a >= 'A' && a <= 'Z')
            a = (char)(a - 'A' + 'a');
        if (b >= 'A' && b <= 'Z')
            b = (char)(b - 'A' + 'a');
        if (a != b)
            return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    int port = (argc > 1) ? atoi(argv[1]) : 8444;
    const char *logpath = (argc > 2) ? argv[2] : "mock_snpp.log";
    FILE *log;
    int srv, cli, one = 1;
    struct sockaddr_in addr;
    FILE *io;
    char line[4096];

    log = fopen(logpath, "w");

    srv = socket(AF_INET, SOCK_STREAM, 0);
    if (srv < 0) {
        perror("socket");
        return 2;
    }
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons((unsigned short)port);

    if (bind(srv, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return 3;
    }
    if (listen(srv, 1) < 0) {
        perror("listen");
        return 4;
    }

    cli = accept(srv, NULL, NULL);
    if (cli < 0) {
        perror("accept");
        return 5;
    }

    io = fdopen(cli, "r+");
    if (io == NULL) {
        perror("fdopen");
        return 6;
    }
    setbuf(io, NULL);
    fprintf(io, "220 mock SNPP ready\r\n");

    while (fgets(line, sizeof(line), io) != NULL) {
        if (log) {
            fputs(line, log);
            fflush(log);
        }
        if (starts_with_ci(line, "CALL"))
            fprintf(io, "250 Callerid accepted\r\n");
        else if (starts_with_ci(line, "PAGE"))
            fprintf(io, "250 Pager accepted\r\n");
        else if (starts_with_ci(line, "LEVE"))
            fprintf(io, "250 Level accepted\r\n");
        else if (starts_with_ci(line, "COVE"))
            fprintf(io, "250 Coverage accepted\r\n");
        else if (starts_with_ci(line, "HOLD"))
            fprintf(io, "250 Hold accepted\r\n");
        else if (starts_with_ci(line, "DATA"))
            fprintf(io, "354 End data with <CR><LF>.<CR><LF>\r\n");
        else if (starts_with_ci(line, "MESS"))
            fprintf(io, "250 Message accepted\r\n");
        else if (starts_with_ci(line, "SEND"))
            fprintf(io, "250 Page sent\r\n");
        else if (starts_with_ci(line, "QUIT")) {
            fprintf(io, "221 Goodbye\r\n");
            break;
        }
        else if (line[0] == '.' && (line[1] == '\r' || line[1] == '\n'))
            fprintf(io, "250 Message accepted\r\n");
        else
            fprintf(io, "250 Ok\r\n");
    }

    fclose(io);
    close(srv);
    if (log)
        fclose(log);
    return 0;
}
