#include <aws/mqtt/mqtt.h>
#include <aws/common/allocator.h>
#include <aws/common/byte_buf.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator returned NULL\n");
        return 1;
    }

    aws_mqtt_library_init(allocator);
    printf("PASS: aws_mqtt_library_init succeeded\n");

    /* Test topic validation API */
    struct aws_byte_cursor topic = aws_byte_cursor_from_c_str("sensors/temperature/room1");
    if (!aws_mqtt_is_valid_topic(&topic)) {
        fprintf(stderr, "FAIL: aws_mqtt_is_valid_topic returned false for valid topic\n");
        aws_mqtt_library_clean_up();
        return 1;
    }
    printf("PASS: aws_mqtt_is_valid_topic validated a valid MQTT topic\n");

    aws_mqtt_library_clean_up();
    printf("PASS: aws-c-mqtt 0.14.0 test completed successfully\n");
    return 0;
}
