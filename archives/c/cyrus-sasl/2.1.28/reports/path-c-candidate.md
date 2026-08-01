# Cyrus SASL 2.1.28 Path C Candidate Evidence

## Application Boundary

This document requests Path C candidate assessment for the initial Cyrus SASL
2.1.28 core-library archive. It does not claim a Path C score, final acceptance,
package publication, or an OpenHarmony runtime result.

## Why This Is A High-Difficulty Candidate

1. **Protocol negotiation and mechanism behavior**: SASL is a client/server
   authentication framework. Meaningful validation covers mechanism discovery,
   challenge-response negotiation, credential handling, and protocol-service
   behavior rather than a single library call.
2. **Plugin and backend closure**: the upstream project combines static and
   dynamic mechanisms with PAM, LDAP, SQL, Kerberos/GSSAPI, database, and
   daemon-backed authentication paths. Those paths have separate runtime
   configuration, service, and credential-store requirements.
3. **Platform integration boundary**: the OpenHarmony cross-build path must
   handle generated Autotools files, build-machine helper tools, install layout,
   and plugin discovery without treating unavailable Linux services as supported.

## Implemented Adaptation Scope

- Packages the core `libsasl2` public library and headers with static mechanism
  support for the first pass.
- Disables sample programs, daemon integration, and PAM, LDAP, SQL, database,
  Kerberos/GSSAPI, OpenSSL, and other external authentication closures.
- Applies two tracked source patches for the OpenHarmony temporary-directory
  and static-archive link-source handling paths.
- Provides a C consumer test for version reporting, client initialization,
  connection creation, mechanism listing, disposal, and shutdown.

## Evidence And Boundaries

| Evidence | Current result |
| --- | --- |
| Source integrity | `conandata.yml` uses the official 2.1.28 release URL and SHA256 `7ccfc6abd01ed67c1a0924b353e526f1b766b21f42d4562ee635a8ebfc5bb38c`. |
| Review discussions | The PR shows 13 of 13 review discussions resolved. |
| Remote CI | PR CI build #11317 initially failed in `source()` because patch files were not exported before `apply_conandata_patches()`. Subsequent CI build #11333 passed the Conan `test_package` and L0/L1 gates on recipe commit `65f19f2b`. |
| Current head boundary | Later commits change Path C compliance documentation only and have no separate CI result. The passing CI applies to the unchanged recipe and consumer-test code at `65f19f2b`. |
| Local execution | No local Conan build or Cyrus consumer test is claimed here. The official source download attempted for host validation was reset by the remote before extraction. |
| OpenHarmony runtime | No target device or runtime execution has been performed. Plugin, backend, and service behavior remain out of scope for this first pass. |

## Proposed Acceptance Items

1. Run the packaged consumer binary on a runnable OpenHarmony target.
2. Add separate evidence before enabling dynamic plugin discovery, external
   authentication backends, or service/credential-store integrations.
3. Obtain a separate CI result for later non-documentation changes before
   extending the stated CI evidence beyond recipe commit `65f19f2b`.

## Review Questions

1. Does the documented core-library scope and explicit backend exclusion meet
   the Path C candidate threshold for the SASL protocol and integration surface?
2. Which target-side client/server mechanism negotiation is required before the
   candidate can be considered complete?
3. Should dynamic plugin and external-backend support remain separate follow-up
   candidates with their own service and credential handling evidence?

## Related Issue

Issue [#1718](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1718)
records the same candidate-only scope, actual validation boundary, acceptance
items, and review questions, and links both this document and PR #3400.
