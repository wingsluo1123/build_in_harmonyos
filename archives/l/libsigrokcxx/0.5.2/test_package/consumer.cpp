/**
 * @file consumer.cpp
 * @brief Installed-package consumer probe for libsigrokcxx/0.5.2 on OHOS PC.
 *
 * Upstream ships no test suite for bindings/cxx (that directory has neither a
 * Makefile.am nor any test source), so this probe covers the installed package:
 *
 *   1. C++11 API surface — the enum object graph generated into enums.cpp
 *      (LogLevel / PacketType / Quantity) parses, links and resolves.
 *   2. Library-backed behaviour — EnumValue::values() reads the exported
 *      std::map instantiation that only exists inside libsigrokcxx.so.0, so a
 *      correct count proves the shared object was linked, not just the header.
 *
 * OHOS-specific, non-assertion check (rule12):
 *   3. Shared-library closure load — dlopen() with RTLD_NOW forces the OHOS
 *      loader to resolve every DT_NEEDED entry of libsigrokcxx.so.0
 *      (libsigrok.so.4, libglibmm-2.4.so.1, libgiomm-2.4.so.1,
 *      libglib-2.0.so.0, libsigc-2.0.so.0) plus every symbol referenced by it.
 *      The observed load result is reported; no value is asserted.
 *
 * The shared object to load can be overridden with argv[1]; by default the
 * probe loads it by SONAME, which is how a real OHOS consumer resolves it.
 */

#include <dlfcn.h>

#include <cstdio>
#include <string>
#include <vector>

#include <libsigrokcxx/libsigrokcxx.hpp>

int main(int argc, char **argv)
{
	/* ---- 1. C++ API surface ------------------------------------------- */
	const sigrok::LogLevel *lvl = sigrok::LogLevel::NONE;
	const sigrok::PacketType *pkt = sigrok::PacketType::LOGIC;
	const sigrok::Quantity *qty = sigrok::Quantity::VOLTAGE;

	std::printf("api: LogLevel=%s(%d) PacketType=%s(%d) Quantity=%s(%d)\n",
		    lvl->name().c_str(), lvl->id(),
		    pkt->name().c_str(), pkt->id(),
		    qty->name().c_str(), qty->id());

	/* ---- 2. Library-backed behaviour ---------------------------------- */
	/* values() walks the sigrok::EnumValue<...>::_values map, whose only
	 * definition lives in the shared object. */
	std::vector<const sigrok::Quantity *> quantities =
		sigrok::Quantity::values();
	std::printf("enum: Quantity::values() -> %zu entries\n",
		    quantities.size());
	if (quantities.empty()) {
		std::printf("api: FAILED (empty enum registry)\n");
		return 1;
	}

	/* ---- 3. OHOS shared-library closure load (non-assertion) ---------- */
	const char *soname = (argc > 1) ? argv[1] : "libsigrokcxx.so.0";
	void *handle = dlopen(soname, RTLD_NOW | RTLD_LOCAL);
	if (!handle) {
		std::printf("closure: LOAD FAILED for %s (%s)\n", soname,
			    dlerror());
		return 1;
	}
	std::printf("closure: loaded %s -> %p\n", soname, handle);
	dlclose(handle);

	std::printf("libsigrokcxx consumer probe: OK\n");
	return 0;
}
