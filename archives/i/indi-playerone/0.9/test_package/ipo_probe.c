/* ipo_probe.c — downstream-consumption probe for indi-playerone's functional
 * core (the vendor POA SDK delivered by the libplayerone dependency).
 *
 * Includes the packaged PlayerOneCamera.h, references the core public API
 * (POAGetAPIVersion / POAGetCameraCount / POAOpenCamera /
 * POAGetCameraProperties — the exact entry points the driver calls) and
 * links against libPlayerOneCamera.so.3 — proving the vendor SDK is usable
 * by a real OHOS aarch64 downstream build (R34, HC-3).
 *
 * Not executed: the vendor .so needs a connected POA camera over USB and the
 * CI sandbox does not allow dlopen of foreign .so files. The link step is
 * the downstream-usability proof.
 */
#include <PlayerOneCamera.h>

int ipo_probe_version(void)
{
	return POAGetAPIVersion();
}

int ipo_probe_camera_count(void)
{
	return POAGetCameraCount();
}

POAErrors ipo_probe_open(int camera_id)
{
	return POAOpenCamera(camera_id);
}

POAErrors ipo_probe_properties(int camera_id, POACameraProperties *props)
{
	return POAGetCameraProperties(camera_id, props);
}
