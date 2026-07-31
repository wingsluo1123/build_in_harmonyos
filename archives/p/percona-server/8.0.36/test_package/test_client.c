#include <mysql.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    MYSQL *conn;

    /* Verify mysql_get_client_info() returns a valid version string */
    const char *client_info = mysql_get_client_info();
    if (client_info == NULL) {
        fprintf(stderr, "mysql_get_client_info() returned NULL\n");
        return 1;
    }
    if (strlen(client_info) == 0) {
        fprintf(stderr, "mysql_get_client_info() returned an empty string\n");
        return 1;
    }
    printf("MySQL client version: %s\n", client_info);

    /* Verify mysql_init() succeeds */
    conn = mysql_init(NULL);
    if (conn == NULL) {
        fprintf(stderr, "mysql_init() returned NULL\n");
        return 1;
    }

    /* Verify mysql_options() works */
    int opt_connect_timeout = 10;
    int rc = mysql_options(conn, MYSQL_OPT_CONNECT_TIMEOUT, &opt_connect_timeout);
    if (rc != 0) {
        fprintf(stderr, "mysql_options(MYSQL_OPT_CONNECT_TIMEOUT) failed: %d\n", rc);
        mysql_close(conn);
        return 1;
    }

    mysql_close(conn);
    printf("percona-server client library loaded successfully\n");
    return 0;
}
