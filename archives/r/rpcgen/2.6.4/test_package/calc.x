/*
 * calc.x -- RPC interface used by the rpcgen consumer test.
 *
 * It exercises the parts of the Sun-RPC IDL that rpcgen has to turn into C:
 * a struct, a program/version pair and two procedures with different argument
 * and result shapes (struct in/out and scalar in/out).
 */

struct calc_request {
	int a;
	int b;
};

struct calc_result {
	int sum;
	int product;
};

program CALC_PROG {
	version CALC_VERS {
		calc_result CALC_ADD(calc_request) = 1;
		int CALC_SQUARE(int) = 2;
	} = 1;
} = 0x31234567;
