#include <errno.h>
#include <i2c/smbus.h>
#include <stdio.h>

static int report_error(const char *name, int result)
{
	if (result != -EBADF || errno != EBADF) {
		fprintf(stderr, "FAIL %s: result=%d errno=%d\n", name, result, errno);
		return 1;
	}
	printf("PASS %s\n", name);
	return 0;
}

int main(void)
{
	int failures = 0;
	unsigned char block[32];

	errno = 0;
	failures += report_error("read_byte_returns_ebadf",
				 i2c_smbus_read_byte(-1));
	errno = 0;
	failures += report_error("write_byte_data_returns_ebadf",
				 i2c_smbus_write_byte_data(-1, 0x00, 0x00));
	errno = 0;
	failures += report_error("read_block_data_returns_ebadf",
				 i2c_smbus_read_block_data(-1, 0x00, block));

	return failures == 0 ? 0 : 1;
}
