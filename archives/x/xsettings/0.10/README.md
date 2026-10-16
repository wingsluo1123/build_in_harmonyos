# xsettings 0.10 — Xsettings protocol client C library

**Package**: `xsettings/0.10`
**Upstream**: https://matchbox-project.org/sources/optional-dependencies/
**License**: MIT (X11-style)
**Build system**: CMake (rewritten from upstream autotools)

## Description

libxsettings-client implements the XSETTINGS protocol — a mechanism for
inter-toolkit configuration settings propagation (theme names, font DPI,
double-click timeout, etc.) via the X11 window system.

## Dependencies

- `libx11/1.8.13.1` — the only dependency (X11 client library)

## Source Files

| File | Description |
|------|-------------|
| `src/xsettings-common.h` | Core types: XSettingsBuffer, XSettingsSetting, XSettingsList |
| `src/xsettings-common.c` | List operations, byte order detection, setting copy/equal |
| `src/xsettings-client.h` | Client API: XSettingsClient, notify/watch callbacks |
| `src/xsettings-client.c` | Client lifecycle, X11 property reading, event processing |

## API

```c
XSettingsClient* xsettings_client_new(Display *display, int screen,
                                      XSettingsNotifyFunc notify,
                                      XSettingsWatchFunc watch,
                                      void *cb_data);
void xsettings_client_destroy(XSettingsClient *client);
XSettingsResult xsettings_client_get_setting(XSettingsClient *client,
                                             const char *name,
                                             XSettingsSetting **setting);
Bool xsettings_client_process_event(XSettingsClient *client, XEvent *xev);

char xsettings_byte_order(void);
XSettingsSetting* xsettings_setting_copy(XSettingsSetting *setting);
int xsettings_setting_equal(XSettingsSetting *a, XSettingsSetting *b);
```

## Upstream Tests

None — Makefile.am has no `check` target, no test files, no test directory.

## Test Package

`test_xsettings.c` validates:
1. `xsettings_byte_order()` returns valid byte order
2. List operations (insert/lookup/delete) work correctly
3. Setting copy/equal functions work correctly
4. **HarmonyOS-specific (rule12)**: dlopen/dlsym symbol resolution
