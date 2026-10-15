# Distro Red Hat

[Fedora's source rpm](https://kojipkgs.fedoraproject.org//packages/sox/14.4.2.0/38.fc40/src/sox-14.4.2.0-38.fc40.src.rpm)
contains a modified version of sox-14.4.2 and some patches.

The modifications are:
* add a missing copyright statement for libgsm. 
  This has been be put back in sox_ng, thanks.
* remove lpc10, presumably for its doubtful copyright status.
  In sox_ng the copyright is fixed thanks to legal advice
  from the FSF leading to a new upstream version.

## [All bug reports](https://bugzilla.redhat.com/buglist.cgi?component=sox)

| Bug | Description | Issue |
| :-- | :---------- | :---: |
| [1931407](https://bugzilla.redhat.com/show_bug.cgi?id=1931407) | Add DSD processing of .dsf files to sox in Fedora 40 |  |
| [1978781](https://bugzilla.redhat.com/show_bug.cgi?id=1978781) | CVE-2021-33844 sox: divide by zero crash in wav.c [epel-8] |  |
| [1978783](https://bugzilla.redhat.com/show_bug.cgi?id=1978783) | CVE-2021-23172 sox: heap overflow in hcom.c [epel-8] |  |
| [1978788](https://bugzilla.redhat.com/show_bug.cgi?id=1978788) | CVE-2021-23159 sox: heap based overflow in formats_i.c [epel-8] |  |
| [1983088](https://bugzilla.redhat.com/show_bug.cgi?id=1983088) | CVE-2021-23210 sox: divide by zero in voc.c [epel-8] |  |
| [1993269](https://bugzilla.redhat.com/show_bug.cgi?id=1993269) | CVE-2021-3643 sox: buffer overflow read vulnerability [epel-8] |  |
| [2094686](https://bugzilla.redhat.com/show_bug.cgi?id=2094686) | CVE-2021-40426 sox: heap-based buffer overflow vulnerability exists in the sphere.c start_read() function [epel-8] |  |
| [2094698](https://bugzilla.redhat.com/show_bug.cgi?id=2094698) | CVE-2022-31650 sox: a floating-point exception in lsx_aiffstartwrite in aiff.c in libsox.a [epel-8] |  |
| [2094701](https://bugzilla.redhat.com/show_bug.cgi?id=2094701) | CVE-2022-31651 sox: an assertion failure in rate_init in rate.c in libsox.a [epel-8] |  |
| [2212281](https://bugzilla.redhat.com/show_bug.cgi?id=2212281) | sox: floating point exception in src/aiff.c:622:58 [epel-all] |  |
| [2212285](https://bugzilla.redhat.com/show_bug.cgi?id=2212285) | sox: heap-buffer-overflow in src/hcom.c [epel-all] |  |
| [2212287](https://bugzilla.redhat.com/show_bug.cgi?id=2212287) | sox: floating point exception in src/voc.c [epel-all] |  |
| [2212294](https://bugzilla.redhat.com/show_bug.cgi?id=2212294) | sox: heap-buffer-overflow in src/formats_i.c [epel-all] |  |
| [2367790](https://bugzilla.redhat.com/show_bug.cgi?id=2367790) | sox cannot open ladspa tap_deesser plugin after upgrading from fc41 to fc42 |  |
| [2383076](https://bugzilla.redhat.com/show_bug.cgi?id=2383076) | sox: STI tests will no longer be run in F43 |  |
| [152759](https://bugzilla.redhat.com/show_bug.cgi?id=152759) | CAN-2004-0557 sox buffer overflows |  |
| [636](https://bugzilla.redhat.com/show_bug.cgi?id=636) | play file.au doesn't work |  |
| [959](https://bugzilla.redhat.com/show_bug.cgi?id=959) | /usr/bin/play should use "$@" |  |
| [617334](https://bugzilla.redhat.com/show_bug.cgi?id=617334) | aiff read bug when mark chunk present |  |
| [880260](https://bugzilla.redhat.com/show_bug.cgi?id=880260) | sox mcompand: bad clipping due to overflow of band summing |  |
