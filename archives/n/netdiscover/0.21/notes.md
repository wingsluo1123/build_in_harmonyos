# netdiscover 0.21

- The release contains Automake inputs but no generated `configure` script, so
  a CMake wrapper builds the exact upstream source list.
- The package uses the published `libpcap/1.10.6@ohpcd/stable` dependency and
  POSIX threads.
- Upstream provides no automated tests. The consumer exercises the help/version
  path without requiring root privileges or opening a network interface.
- Official OHOS test and CI results remain pending.
