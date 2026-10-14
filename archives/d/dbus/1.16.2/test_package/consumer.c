#include <dbus/dbus.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#define REQUIRE(x) do { if (!(x)) { fprintf(stderr,"failed line %d: %s\n",__LINE__,#x); return 1; } } while(0)
int main(int argc, char **argv)
{
  DBusError error; dbus_error_init(&error);
  if (argc == 2) {
    DBusConnection *conn=dbus_connection_open_private(argv[1],&error);
    REQUIRE(conn != NULL && !dbus_error_is_set(&error));
    dbus_connection_set_exit_on_disconnect(conn,FALSE);
    REQUIRE(dbus_bus_register(conn,&error) && !dbus_error_is_set(&error));
    unsigned long uid=dbus_bus_get_unix_user(conn,dbus_bus_get_unique_name(conn),&error);
    REQUIRE(!dbus_error_is_set(&error) && uid == (unsigned long)getuid());
    printf("ACTUAL_REGISTERED_UNIX_UID=%lu\n",uid);
    dbus_connection_close(conn); dbus_connection_unref(conn); dbus_shutdown(); return 0;
  }
  REQUIRE(dbus_validate_path("/consumer/ok",&error));
  REQUIRE(!dbus_validate_path("not/an/object/path",&error) && dbus_error_is_set(&error));
  dbus_error_free(&error); puts("CONSUMER_CASE_1_SYNTAX_PASS");
  DBusMessage *message=dbus_message_new_signal("/consumer","org.example.Consumer","Changed");
  REQUIRE(message != NULL); const char *text="real round trip";
  dbus_uint32_t number=42; REQUIRE(dbus_message_append_args(message,DBUS_TYPE_STRING,&text,DBUS_TYPE_UINT32,&number,DBUS_TYPE_INVALID));
  dbus_message_set_serial(message,1); char *blob=NULL; int bytes=0;
  REQUIRE(dbus_message_marshal(message,&blob,&bytes) && bytes>0);
  DBusMessage *decoded=dbus_message_demarshal(blob,bytes,&error); REQUIRE(decoded && !dbus_error_is_set(&error));
  const char *got=NULL; dbus_uint32_t actual=0;
  REQUIRE(dbus_message_get_args(decoded,&error,DBUS_TYPE_STRING,&got,DBUS_TYPE_UINT32,&actual,DBUS_TYPE_INVALID));
  REQUIRE(actual==42 && strcmp(got,text)==0); puts("CONSUMER_CASE_2_MARSHAL_PASS");
  REQUIRE(dbus_message_is_signal(decoded,"org.example.Consumer","Changed"));
  REQUIRE(dbus_message_has_path(decoded,"/consumer")); puts("CONSUMER_CASE_3_MESSAGE_METADATA_PASS");
  DBusServer *server=dbus_server_listen("tcp:host=127.0.0.1,port=0",&error);
  REQUIRE(server && !dbus_error_is_set(&error) && dbus_server_get_is_connected(server));
  char *address=dbus_server_get_address(server); REQUIRE(address && strstr(address,"tcp:"));
  dbus_server_disconnect(server); REQUIRE(!dbus_server_get_is_connected(server));
  dbus_free(address);dbus_server_unref(server); puts("CONSUMER_CASE_4_SERVER_LIFECYCLE_PASS");
  dbus_message_unref(decoded);dbus_message_unref(message);dbus_free(blob);dbus_shutdown();
  puts("CONSUMER_COUNT=4; 4/4 PASS"); return 0;
}
