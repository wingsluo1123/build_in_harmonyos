# openobex 1.7.2

- Builds the static core library with the portable INET, custom, and
  file-descriptor transports.
- Bluetooth, IrDA, USB, Linux udev integration, applications, and
  documentation are disabled because they require optional host facilities.
- The legacy CMake 3.1 policy floor is raised to 3.5 for current CMake
  compatibility without changing project behavior.
- The release contains demonstration applications but no automated upstream
  test suite. A deterministic in-memory API consumer is provided.
- Official OHOS test and CI results remain pending.
