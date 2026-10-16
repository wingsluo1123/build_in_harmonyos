# E551 — Missing Qt data can look like a headless test-harness defect

## Symptom and trigger

A Qt library's non-GUI API aborts with `Cannot create a QWidget without
QApplication` under the original GUILESS tests. Replacing QCoreApplication
with QApplication changes the symptom to a headless timeout. This does not
necessarily mean the API requires a graphical test harness: an error path
may be trying to display a modal diagnostic.

## Root cause and repair

Follow the first widget creation back to the resource lookup. In this case,
KDefaultPropertyFactory calls setupPrivateIconsResourceWithMessage; a missing
RCC lookup opens a message box. The RCC was correctly installed under the
isolated Conan package's share directory, but that prefix was absent from
QStandardPaths' XDG_DATA_DIRS roots.

Expose the library-owned resource root in the package's runtime interface:

```python
self.runenv_info.prepend_path(
    "XDG_DATA_DIRS", os.path.join(self.package_folder, "share"))
```

Before package_info is available, give upstream tests the same installed
share root and preserve inherited XDG paths. Check that the actual expected
RCC exists and is non-empty; do not remove the resource registration/error
path. Restore the original GUILESS test main and all original assertions.
Consumers must activate the generated runtime environment too.

## Evidence

KProperty 3.2.0 r5: two original tests aborted on widget creation. r6/r7:
QApplication plus offscreen permits the modal dialog and both tests time out;
plugin logs show offscreen successfully loaded, so it was not a missing QPA
plugin. r8 restored original tests with the installed data root: all three
CTest entries pass. r9 also corrected the separate CMakeDeps/KF5 consumer
configuration, passed installed API assertions 5/5, and verified Qt5 loading
the Qt6-produced French QM. Full transaction: kproperty-w3-20261014-r9,
12 receipts, released W3_PASS. Log SHA256:
`0de754bbcc306f2bd21f8953da597db94b81a9e0282c5e85d6a7189fd60f41a0`.

## Deduplication and boundaries

E255 discusses packaging pure resource libraries, not a compiled library's
modal error fallback. DRAFT-cmakedeps-interface-defines-lost discusses missing
Qt interface macros and QTEST_MAIN dispatch; this case uses the explicitly
GUILESS macro and unchanged native Qt metadata for upstream tests. The new
increment is the abort-to-hang diagnostic pair, traced resource-error path,
and proof that resource lookup repair restores the original headless tests.
Do not generalize it to genuine GUI assertions. Headless unit and consumer
PASS does not prove native desktop window/input integration.
