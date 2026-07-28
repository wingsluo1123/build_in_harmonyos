# memtool 2018.03.0

- The release archive contains Automake inputs but no generated `configure`
  script, so a small CMake build wrapper compiles the three upstream sources.
- Linux-only MDIO access is intentionally disabled; portable memory-mapped file
  access remains enabled.
- Upstream provides no automated tests. The consumer performs version/help
  checks and writes then reads a temporary file through the packaged binary.
- Official OHOS test and CI results remain pending.
