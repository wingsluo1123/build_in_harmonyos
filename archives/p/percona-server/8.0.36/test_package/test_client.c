#include <mysql.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>

int main(void)
{
    MYSQL *conn;

    /* Verify mysql_get_client_info() returns a valid version string */
    const char *client_info = mysql_get_client_info();
    assert(client_info != NULL);
    assert(strlen(client_info) > 0);
    printf("MySQL client version: %s\n", client_info);

    /* Verify mysql_init() succeeds */
    conn = mysql_init(NULL);
    assert(conn != NULL);

    /* Verify mysql_options() works */
    int opt_connect_timeout = 10;
    int rc = mysql_options(conn, MYSQL_OPT_CONNECT_TIMEOUT, &opt_connect_timeout);
    assert(rc == 0);

    mysql_close(conn);
    printf("percona-server client library loaded successfully\n");
    return 0;
}

