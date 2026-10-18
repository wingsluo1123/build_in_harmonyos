# Functional test of the packaged gawkpn.so through GNU Awk.
# Upstream registers its functions in the "phonenumber" AWK namespace
# (dl_load_func(func_table, "phonenumber", "phonenumber")), hence the
# @namespace block below on GNU Awk 5.x.
@load "gawkpn"
@namespace "phonenumber"

BEGIN {
	failures = 0

	pn_set_country("FR")
	pn_set_format("e164")

	failures += check("pn_format FR e164", pn_format("0123456789"), "+33123456789")
	failures += check_number("pn_valid FR valid", pn_valid("0123456789"), 1)
	failures += check_number("pn_valid FR invalid", pn_valid("00 12 34 56 78"), 0)

	pn_info("02 96 48 46 98", infos)
	failures += check_number("pn_info prefix", infos["prefix"], 33)
	failures += check("pn_info country", infos["country"], "FR")
	failures += check_number("pn_info type (fixed line)", infos["type"], 0)

	pn_set_format("nat")
	failures += check("pn_format FR nat", pn_format("0123456789"), "01 23 45 67 89")

	pn_set_format("e164")
	delete found
	pn_find("call 01 23 45 67 89 or +1 202 555 0110", found)
	count = 0
	for (number in found)
		count++
	failures += check_number("pn_find hits", count, 2)
	failures += check("pn_find FR hit", (("+33123456789" in found) ? "yes" : "no"), "yes")
	failures += check("pn_find US hit", (("+12025550110" in found) ? "yes" : "no"), "yes")

	failures += check("pn_dialout US -> FR", pn_dialout("+33123456789", "US"),
	                  "011 33 1 23 45 67 89")

	printf("test_gawkpn: %d case(s), %d failure(s)\n", 11, failures)
	exit(failures == 0 ? 0 : 1)
}

function check(name, actual, expected) {
	if (actual == expected) {
		printf("  PASS: %s\n", name)
		return 0
	}
	printf("  FAIL: %s (got '%s', expected '%s')\n", name, actual, expected)
	return 1
}

function check_number(name, actual, expected) {
	return check(name, sprintf("%d", actual), sprintf("%d", expected))
}
