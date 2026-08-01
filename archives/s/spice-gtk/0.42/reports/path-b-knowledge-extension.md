# Path B Knowledge Extension Evidence

## Submission

- Path: B (knowledge extension)
- Linked Issue: [#1233](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1233)
- Linked PR: [#3134](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/3134)
- Knowledge entry: `knowledge/drafts/DRAFT-spice-gtk-remote-desktop-staging.kv`

This submission does not claim Path C or request a high-difficulty score.

## Reusable Rule

Remote-desktop GUI clients can combine a protocol client, GTK/GDK display and
input, GLib/GIO event handling, media pipelines, native-window integration, and
optional device-forwarding channels. Treating a successful cross build as proof
of all those runtime capabilities produces an unsafe conclusion.

The draft makes the following reusable rule explicit:

1. Build and validate the independently consumable core client library first.
2. Disable device and desktop-session side channels until their package and
   target-runtime dependencies are available.
3. Record the exact Meson boundary and the validation command.
4. Require live protocol-server and device evidence before saying a full remote
   desktop client is available.

For spice-gtk 0.42 the staged-off features are USB redirection, WebDAV,
SASL, smartcard, Wayland protocols, EGL, introspection, VAPI, documentation,
translations, man pages, and upstream build-tree tests. The default package is
`gtk=False`; GTK rendering is not claimed as available.

## Actual Evidence

| Check | Actual result | Interpretation |
|---|---:|---|
| Real OHOS Meson build steps | 69/69 | Build and package steps completed on the recorded precheck commit. This is not an upstream test count. |
| OHOS consumer test | 1/1 compile and link | Installed headers and libraries linked for the default `gtk=False` scope. Runtime execution was skipped. |
| Selected upstream Meson tests | 0/5 | Not run. No pass claim is made. |
| Latest remote CI | blocked before build | CI #11728 could not resolve `json-glib/1.6.6`; `gstreamer/1.28.3` and `gst-plugins-base/1.28.3` are also unpublished. |

The full upstream test set must be executed and recorded after the dependency
chain resolves. The PR must not request `/rebuild` while this condition remains.

## Review Questions

1. Does the draft's trigger/root-cause/recommendation/guardrail structure make
   the staged-adaptation rule reusable for other remote-desktop GUI clients?
2. Is the `gtk=False` and side-channel boundary sufficiently explicit to avoid
   suggesting unsupported display, USB, WebDAV, or smartcard runtime behavior?
3. After dependencies are published, are the five selected upstream Meson tests
   and a live SPICE-server scenario the right next validation milestones?
