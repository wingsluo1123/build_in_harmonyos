# Fork sox.sf.net

## Tickets

Here is the correspondence between the tickets on [`sox.sf.net`](http://sox.sf.net) and `sox_ng`'s issues.

    Legend
    -      Not required in `sox_ng`
    42b355 Only present in sox.sf.net, not 14.4.2 or sox_ng

### Patches

| Patch | Issue |
| :---- | :---: |
| [129](https://sourceforge.net/p/sox/patches/129) a sane build system | #271 |
| [128](https://sourceforge.net/p/sox/patches/128) Division by zero at `wav.c:967` | `42b355` |
| [127](https://sourceforge.net/p/sox/patches/127) Division by zero at `voc.c:334` | #247 |
| [126](https://sourceforge.net/p/sox/patches/126) Global-buffer-overflow at `adpcms.c:58` | #262 |
| [125](https://sourceforge.net/p/sox/patches/125) Fix `property_size = sizeof(name)` | #167 |
| [124](https://sourceforge.net/p/sox/patches/124) low-latency pulseaudio pipeline using --input-buffer | #185 |
| [123](https://sourceforge.net/p/sox/patches/123) configure.ac: fix static linking with id3tag | `42b355` |
| [122](https://sourceforge.net/p/sox/patches/122) configure.ac: put back --disable-protector | #254 |
| [121](https://sourceforge.net/p/sox/patches/121) Full RF64 support | #253 |
| [120](https://sourceforge.net/p/sox/patches/120) Initialize channel map for pulseaudio | #252 |
| [116](https://sourceforge.net/p/sox/patches/116) [PATCH] Adding FFTW support speeds up spectrogram by factor of ten | #109 |
| [108](https://sourceforge.net/p/sox/patches/108) Fix multi-channel LADSPA effects + draining for all LADSPA effects | #245 |
| [107](https://sourceforge.net/p/sox/patches/107) Win32 Progress Flush Fix | #244 |
| [106](https://sourceforge.net/p/sox/patches/106) Support for "DynAudNorm" Effect | #164 |
| [105](https://sourceforge.net/p/sox/patches/105) Win32 Unicode (UTF-8) support | #203 |
| [104](https://sourceforge.net/p/sox/patches/104) missing version number in sox --version output | #159 |
| [103](https://sourceforge.net/p/sox/patches/103) ignore SIGPIPE so stop callbacks may fire | #243 |
| [102](https://sourceforge.net/p/sox/patches/102) [PATCH] modified spectrogram hh:mm:ss in X-axis | #242 |
| [94](https://sourceforge.net/p/sox/patches/94) libmpg123 support for mp3 decoding | #150 |
| [93](https://sourceforge.net/p/sox/patches/93) flac (decoder): simplify EOF state and fix MD5 check | - |
| [89](https://sourceforge.net/p/sox/patches/89) Docs: libsox.3 update | - |
| [65](https://sourceforge.net/p/sox/patches/65) Enable SoX to be built as a Windows DLL | #251 |
| [41](https://sourceforge.net/p/sox/patches/41) MIDI Sample Dump Module | #157 |
| [35](https://sourceforge.net/p/sox/patches/35) Amiga Module support | #158 |

### Merge requests

| #  | Description | Issue |
| -: | :---------- | :---: |
| [1](https://sourceforge.net/p/sox/code/merge-requests/1) | Fix bit-depth calculation | #273 |
| [2](https://sourceforge.net/p/sox/code/merge-requests/2) | make it read Alaw Sphere file | #186 |
| [3](https://sourceforge.net/p/sox/code/merge-requests/3) | Release holds on stdin/stdout when we have finished with them | #696 |
| [4](https://sourceforge.net/p/sox/code/merge-requests/4) | Rudimentary support for NSP format | #272 |
| [5](https://sourceforge.net/p/sox/code/merge-requests/5) | Add 192kHz support to RIAA EQ deemphasis biquad effect | #173 |
| [6](https://sourceforge.net/p/sox/code/merge-requests/6) | Fix memory buffer rewinding for format detection | f4c709a |
| [8](https://sourceforge.net/p/sox/code/merge-requests/8) | coreaudio: add a way to choose devices with number | 220795d |
| [9](https://sourceforge.net/p/sox/code/merge-requests/9) | Patch for Ticket 327 | 47eeef2 |
| [10](https://sourceforge.net/p/sox/code/merge-requests/10) | Fixing ticket 325, possible integer overflow (addition) in sox-fmt.c function startread | #20 |
| [13](https://sourceforge.net/p/sox/code/merge-requests/13) | rewrite the manpages in mdoc(7) | No thanks |
| [14](https://sourceforge.net/p/sox/code/merge-requests/14) | sox spectrogram: remove arbitrary size limits, add normalize flag, use fftw3 | Done |
| [15](https://sourceforge.net/p/sox/code/merge-requests/15) | more channels for dat files | #412 |
| [16](https://sourceforge.net/p/sox/code/merge-requests/16) | remove the test suite | Done |
| [17](https://sourceforge.net/p/sox/code/merge-requests/17) | don't leak comments on failed open_{read,write} | Done |
| [18](https://sourceforge.net/p/sox/code/merge-requests/18) | hcom: validate dicsize, don't leak dictionary | afd9cdb<BR>db7a256 |
| [19](https://sourceforge.net/p/sox/code/merge-requests/19) | voc validate bits per word | 366f186 |
| [20](https://sourceforge.net/p/sox/code/merge-requests/20) | wav: bits per sample cannot be zero | d84c38c |
| [21](https://sourceforge.net/p/sox/code/merge-requests/21) | aiff: don't write a silly number of channels | 263f885 |
| [22](https://sourceforge.net/p/sox/code/merge-requests/22) | validate channels and rate | 263f885 |
| [23](https://sourceforge.net/p/sox/code/merge-requests/23) | sphere: do not underflow | 31e6b04 |
| [24](https://sourceforge.net/p/sox/code/merge-requests/24) | get device name properly on macOS | c5aa611 |
| [25](https://sourceforge.net/p/sox/code/merge-requests/25) | macOS build is like any other | 1e59d84 |

### Open bugs

[Open bugs](https://sourceforge.net/p/sox/bugs/?limit=100) created since 14.4.2

    Legend
    -       Not an issue
    42b355  Only present in sox.sf.net, not 14.4.2 or sox_ng

| BUG | Issue |
| :-- | :---: |
| [377](https://sourceforge.net/p/sox/bugs/377) silence -l does not work correctly  | #258 |
| [375](https://sourceforge.net/p/sox/bugs/375) 'pipe' STDIN input broken | `42b355` |
| [374](https://sourceforge.net/p/sox/bugs/374) autoreconf overwrites INSTALL | - |
| [373](https://sourceforge.net/p/sox/bugs/373) .VOC text not processed  | #563 |
| [372](https://sourceforge.net/p/sox/bugs/372) threshold parameter for "silence" filter isn't handled correctly.  | #395 |
| [371](https://sourceforge.net/p/sox/bugs/371) Need a way to specify the directory for temporary files.  | - |
| [370](https://sourceforge.net/p/sox/bugs/370) FPE in SoX 14.4.3git (src/​aiff.c:622:58 in lsx_aiffstartwrite)  | - |
| [369](https://sourceforge.net/p/sox/bugs/369) FPE in SoX 14.4.3git（src/​voc.c:334:18 in read_samples)  | `42b355` |
| [368](https://sourceforge.net/p/sox/bugs/368) heap-buffer-overflow in SoX 14.4.3git (hcom.c:160:41 in startread)  | `42b355` |
| [367](https://sourceforge.net/p/sox/bugs/367) heap-buffer-overflow in SoX 14.4.3git (formats_i.c:98:16)  | `42b355` |
| [366](https://sourceforge.net/p/sox/bugs/366) html and pdf generation is broken  | - |
| [365](https://sourceforge.net/p/sox/bugs/365) sox: Soory, there is no default audio device configured  | #396 |
| [364](https://sourceforge.net/p/sox/bugs/364) sox spectrogram title option breaks when using keyword  | #163 |
| [363](https://sourceforge.net/p/sox/bugs/363) sox segfaults when parsing CLI options | `42b355` |
| [362](https://sourceforge.net/p/sox/bugs/362) CVE-2021-40426 sphere.c start_read() heap-based buffer overflow vulnerability  | #27 |
| [361](https://sourceforge.net/p/sox/bugs/361) sox not fading as expected  | - |
| [360](https://sourceforge.net/p/sox/bugs/360) [BUG] two bugs in sox  | `14.4.2`<BR>`42b355` |
| [359](https://sourceforge.net/p/sox/bugs/359) DAT text file format broken on large number channel data files.  | #412 |
| [358](https://sourceforge.net/p/sox/bugs/358) Segmentation fault when creating a spectrogram with 3kHz limit  | `42b355` |
| [356](https://sourceforge.net/p/sox/bugs/356) SoX handles 32bit float files with volume over 0 dBFS incorrectly  | #422 |
| [355](https://sourceforge.net/p/sox/bugs/355) File Length Error for specific combination of reverb and tremolo  | #425 |
| [354](https://sourceforge.net/p/sox/bugs/354) Device enumeration duplicates ->Coreaudio.c needs updating to modern APIs | #167 fixes property_size<BR>#183 for updating |
| [352](https://sourceforge.net/p/sox/bugs/352) heap-overflow in formats_i.c  | `CVE-2021-23159`<BR>`14.4.2`<BR>`42b355` |
| [351](https://sourceforge.net/p/sox/bugs/351) div zero in voc.c  | `CVE-2021-3643`<BR>`42b355`<BR>#247 |
| [350](https://sourceforge.net/p/sox/bugs/350) Heap overflow in hcom.c  | `CVE-2021-23172`<BR>`42b355` |
| [349](https://sourceforge.net/p/sox/bugs/349) div zero crash in wav.c  | `CVE-2021-33844`<BR>`42b355` |
| [346](https://sourceforge.net/p/sox/bugs/346) sox noisered dies with segv  | `CVE-2021-33844`<BR>`42b355`<BR>#26 |
| [345](https://sourceforge.net/p/sox/bugs/345) Sox should preserve all aiff headers  | #441 #446 |
| [343](https://sourceforge.net/p/sox/bugs/343) speed effect not effective using soxlib APIs | #442 |
| [329](https://sourceforge.net/p/sox/bugs/329) Outputting ogg/​vorbis via the output effect is extremely slow  | #545 |
| [323](https://sourceforge.net/p/sox/bugs/323) divided by zero issue in flanger.c  | #536 |
| [322](https://sourceforge.net/p/sox/bugs/322) sox FAIL noisered: multi-channel effect drained asymmetrically! error | #548 |
| [314](https://sourceforge.net/p/sox/bugs/314) Incorrect work of sox_read function with In-memory output buffers | #241 |
| [313](https://sourceforge.net/p/sox/bugs/313) libsox.dylib generated incorrectly on OS X 10.10 and later (pending-fixed) | - |
| [309](https://sourceforge.net/p/sox/bugs/309) Preventing division by zero in src/ao.c  | #537 |
| [307](https://sourceforge.net/p/sox/bugs/307) Filename with Special Characters fail  | #203 |
| [304](https://sourceforge.net/p/sox/bugs/304) Incorrect ByteRate and Non-Integer SampleRates  | #552 |
| [295](https://sourceforge.net/p/sox/bugs/295) clipping warning even with guard  | #256 |
| [293](https://sourceforge.net/p/sox/bugs/293) stats effect returns -inf if window is set to 0.36 seconds  | #561 |
| [276](https://sourceforge.net/p/sox/bugs/276) 'gain -n' causes SoX v14.4.2 to not delete tmp file  | #468 |
| [274](https://sourceforge.net/p/sox/bugs/274) Codec bug in IMA and OKI ADPCM algorithms. | #562 |
| [263](https://sourceforge.net/p/sox/bugs/263) FAIL sox: Sorry, there is no default audio device configured | #396 |
| [262](https://sourceforge.net/p/sox/bugs/262) Double free when applying a LADSPA plugin with 2 input channels and 3 output channels | #245 |

### Closed bugs

[Closed bugs](https://sourceforge.net/p/sox/bugs/search/?q=status%3Aclosed-invalid+or+status%3Aclosed-accepted+or+status%3Aclosed-rejected+or+status%3Aclosed-out-of-date+or+status%3Aclosed-duplicate+or+status%3Aclosed-works-for-me+or+status%3Aclosed+or+status%3Aclosed-wont-fix+or+status%3Aclosed-fixed&limit=250) created since 14.4.2

| BUG | Status | Issue/commit |
| :-- | :----- | :---: |
| [376](https://sourceforge.net/p/sox/bugs/376) mailing lists not working | closed | - |
| [353](https://sourceforge.net/p/sox/bugs/353) Recording 24/32 bits audio not in proper wave format | closed | cb1945e |
| [348](https://sourceforge.net/p/sox/bugs/348) syntax error near unexpected token `-fstack-protector-strong' | closed-invalid | - |
| [347](https://sourceforge.net/p/sox/bugs/347) error metadata.cpp, Line 636 Expression: is_valid() | closed-invalid | - |
| [344](https://sourceforge.net/p/sox/bugs/344) invalid option "-w" error | closed | #210 |
| [342](https://sourceforge.net/p/sox/bugs/342) sox has exited with error code 2 with Google Speech API | closed | - |
| [341](https://sourceforge.net/p/sox/bugs/341) help text hides option parsing error message | closed-invalid | 8527195 |
| [340](https://sourceforge.net/p/sox/bugs/340) Documentation mismatch for -A /​ -U | closed-out-of-date | - |
| [339](https://sourceforge.net/p/sox/bugs/339) trim nr samples different behavior from nr seconds | closed-invalid | - |
| [338](https://sourceforge.net/p/sox/bugs/338) Spectrogram of very BIG file | closed-invalid | #530 |
| [337](https://sourceforge.net/p/sox/bugs/337) Output wav file >4gb corrupted from Sox remix of 3 wav files nto one wav file | closed-invalid | #530 |
| [334](https://sourceforge.net/p/sox/bugs/334) Segmentation fault in rate.c:504:30 | closed-fixed | #56 |
| [333](https://sourceforge.net/p/sox/bugs/333) Assertion fail in rate.c:303 | closed-fixed | #532 |
| [332](https://sourceforge.net/p/sox/bugs/332) configure fails: syntax error near unexpected token `-Wl,--as-needed' | closed | #278 |
| [331](https://sourceforge.net/p/sox/bugs/331) A Floating point exception in wav.c:950:80 | closed-invalid | #7 |
| [330](https://sourceforge.net/p/sox/bugs/330) Playing file through SoX | closed-invalid | - |
| [328](https://sourceforge.net/p/sox/bugs/328) Error code 2 with Google Speech API on EC2 instance | closed-invalid | - |
| [327](https://sourceforge.net/p/sox/bugs/327) Memcpy-param-overlap in mp3-util.h | closed-fixed | #533 |
| [326](https://sourceforge.net/p/sox/bugs/326) sox_sample_test.h needs math.h for fabs() | closed-fixed | 837d101 |
| [325](https://sourceforge.net/p/sox/bugs/325) Integer Overflow in sox-fmt.c | closed-fixed | #20 |
| [324](https://sourceforge.net/p/sox/bugs/324) Fix broken URLs in man page | closed-fixed | Done |
| [321](https://sourceforge.net/p/sox/bugs/321) Stack-Buffer-Overflow in fft4g.c | closed-fixed | #18 |
| [320](https://sourceforge.net/p/sox/bugs/320) Integer Overflow in xmalloc.h | closed-fixed | #17 |
| [319](https://sourceforge.net/p/sox/bugs/319) Integer Overflow resulting in Heap-Buffer-Overflow in effect_i_dsp.c | closed-fixed | #15 |
| [318](https://sourceforge.net/p/sox/bugs/318) NULL pointer dereference in effect_i_dsp.c | closed-fixed | #19 |
| [317](https://sourceforge.net/p/sox/bugs/317) sox cannot handle true 32 bit | closed-fixed | - |
| [316](https://sourceforge.net/p/sox/bugs/316) sox command | closed-invalid | - |
| [315](https://sourceforge.net/p/sox/bugs/315) Converting the same wav file twice throws different output | closed-invalid | - |
| [312](https://sourceforge.net/p/sox/bugs/312) Null byte at the end of gsrt files causes a click in playback | closed-fixed | #538 |
| [311](https://sourceforge.net/p/sox/bugs/311) Unexpected display behavior when less than 80 columns | closed-fixed | #540 |
| [310](https://sourceforge.net/p/sox/bugs/310) Parsing 0-frame aiff file fails with error: Missing SSND chunk in AIFF file | closed-fixed | #541 |
| [308](https://sourceforge.net/p/sox/bugs/308) [PATCH] assertion failed (core dumped) while converting wav to hcom on 64 bit big endian machine | closed-fixed | #42 |
| [306](https://sourceforge.net/p/sox/bugs/306) Version info not displayed | closed-fixed | #159 |
| [305](https://sourceforge.net/p/sox/bugs/305) Sox blocking in an infinite loop when decoding AMR files | closed-fixed | #542 |
| [303](https://sourceforge.net/p/sox/bugs/303) Sox/​play WAV playing in double speed | closed-duplicate | #543 |
| [302](https://sourceforge.net/p/sox/bugs/302) Missing $(DESTDIR) before ${bindir} in src/​Makefile.am installcheck | closed-fixed | e4dcfe3 |
| [301](https://sourceforge.net/p/sox/bugs/301) Bad FSF address in src/​ladspa.h | closed-fixed | 126779c |
| [300](https://sourceforge.net/p/sox/bugs/300) sox v14.4.2 segmentation violation when playing some wav files generated by Audacity | closed-fixed | 03eb5e9<BR>38ea5cf |
| [299](https://sourceforge.net/p/sox/bugs/299) Invalid memory read via crafted .xa file | closed-fixed | #14 |
| [298](https://sourceforge.net/p/sox/bugs/298) Use-after-free while feeding malformed aiff file | closed-fixed | - |
| [297](https://sourceforge.net/p/sox/bugs/297) SoX v14.4.2 vulnerable to a heap use-after-free condition after parsing AIFF file and calling sox_append_comments() | closed-fixed | - |
| [296](https://sourceforge.net/p/sox/bugs/296) CVE-2017-11332, CVE-2017-11332, CVE-2017-11359 | closed-fixed | 8a441b1 |
| [294](https://sourceforge.net/p/sox/bugs/294) Wrong conversion from 8 bit to 16 bit | closed-rejected | #564 |
| [292](https://sourceforge.net/p/sox/bugs/292) Precision of 32-bit float appears incorrect | closed-invalid | - |
| [291](https://sourceforge.net/p/sox/bugs/291) Support ID3 tags version 2.4 | closed-invalid | - |
| [290](https://sourceforge.net/p/sox/bugs/290) sox_open_mem_write() on windows not worked | closed-wont-fix | #693 |
| [286](https://sourceforge.net/p/sox/bugs/286) Skipped AIFF chunks fail to account for pad byte. | closed-fixed | 8a441b1 |
| [285](https://sourceforge.net/p/sox/bugs/285) pipe decoded audio from ffmpeg to sox | closed-wont-fix | - |
| [284](https://sourceforge.net/p/sox/bugs/284) Please update LibFlac.vcxproj to work with flac 1.3 | closed | - |
| [283](https://sourceforge.net/p/sox/bugs/283) Z_SOLO macro in LibZLib.vcxproj | closed | - |
| [282](https://sourceforge.net/p/sox/bugs/282) Compiler error C2039 in VS 2015 | closed-fixed | - |
| [281](https://sourceforge.net/p/sox/bugs/281) repeat not working in a chain of effects | closed-invalid | - |
| [278](https://sourceforge.net/p/sox/bugs/278) Infinite loop, info command and verbose output for corrupt WAV file | closed-fixed | #698 |
| [277](https://sourceforge.net/p/sox/bugs/277) pulseaudio sound handler is buggy/inconsistent | closed-fixed | 26dea6c |
| [275](https://sourceforge.net/p/sox/bugs/275) Different output length from trim if source is AIFF file | closed-unreproducible | #695 |
| [273](https://sourceforge.net/p/sox/bugs/273) stdin/stdout not released when lsx_close called | closed-fixed | #696 |
| [272](https://sourceforge.net/p/sox/bugs/272) sox_formats_quit does not properly clean things up | closed-fixed | #697 |
| [271](https://sourceforge.net/p/sox/bugs/271) Can't open files which contains foreign characters | closed-duplicate | #203 |
| [270](https://sourceforge.net/p/sox/bugs/270) Current git fails to build debian package on Debian and Ubuntu | closed-fixed | - |
| [269](https://sourceforge.net/p/sox/bugs/269) sox play fails following Ubuntu 14.04 upgrade (3.13.0-65-generic) | closed-invalid | - |
| [268](https://sourceforge.net/p/sox/bugs/268) Permission denied | closed-invalid | - |
| [267](https://sourceforge.net/p/sox/bugs/267) "Bit-depth" stats result changes when signal is inverted | closed-fixed | #273 |
| [266](https://sourceforge.net/p/sox/bugs/266) sox-14.4.2/src/mp3.c:407: undefined reference to `lsx_error' | closed-fixed | . |
| [265](https://sourceforge.net/p/sox/bugs/265) Multiple memory corruption vulnerabilities in SoX 14.4.2 | closed-fixed | - |
| [264](https://sourceforge.net/p/sox/bugs/264) sox is losing frames when trimming | closed-out-of-date | - |
| [261](https://sourceforge.net/p/sox/bugs/261) absurd docs bug - PDF is doubled 14.4.1 and 14.4.2 | closed-fixed | #261 |
| [260](https://sourceforge.net/p/sox/bugs/260) Reading from memory files depends upon uninitialized value read | closed-fixed | #699 |
| [259](https://sourceforge.net/p/sox/bugs/259) sox WARN formats: can't set sample rate X; using Y | closed-invalid | - |
| [258](https://sourceforge.net/p/sox/bugs/258) Sox produces non-deterministic /​ non-reproducible output when resampling! | closed-invalid | - |
| [257](https://sourceforge.net/p/sox/bugs/257) ./sox monkey.wav -r 12500 -2 -s monkey.xxx FAILS in currents snapshot | closed-fixed | 3280a0c |
| [214](https://sourceforge.net/p/sox/bugs/214) sox does not respond to SIGINT over ssh | closed-fixed | #540 |

## TODO

`sox_ng` stems from `sox-14.4.2`, not from a more recent `sox.sf.net` commit,
because the first `sox_ng` release (micro) concentrates on bug fixes and
* patches in the distros, mostly based on 14.4.2, are more likely to apply cleanly
* sox.sf.net since 14.4.2 has 184 commits: a mixture of bug fixes, new features, build system fixes, code reformatting and refactoring and who knows what else
* the regression test suite shows that 42b355 fails on some CVEs that 14.4.2 doesn't, so it has more bugs as well as less. See [Testing](Testing).

### Fix bug 321

[Bug 321](https://sourceforge.net/p/sox/bugs/321): Stack-Buffer-Overflow in fft4g.c
is addressed by [patch b7883ae](https://sourceforge.net/p/sox/code/ci/b7883ae),
imported by Debian, but on the test case it makes sox loop for 6 seconds
consuming gigabytes of memory and creates a 127MB audio file of random noise
just over an hour long. See issue #18: CVE-2017-8356.

This is because the check against `FFT4G_MAX_SIZE` makes the functions
in `fft4g.c` `return` instead of failing. The solution is to turn each

    if (n > FFT4G_MAX_SIZE)
        return;

into

    if (n > FFT4G_MAX_SIZE) {
        lsx_fail("FFT size is too large");
        exit(2);
    }

### Add `README` to the repository

SoX's `README` file is generated by `README.sh` and is not included
in the repository. As a consequence, code browsed at `sox.sf.net`
shows at the bottom of the page `README.osx` or `README.win32`
which are irrelevant.

It would be better to run `README.sh` and add the generated `README`
to the repository. People editing `README.sh` or `FEATURES.in`
will have to remember to update `README` too and commit it,
unless this can be automated.

### Import patches

If `sox.sf.net` maintainers wish to import patches from `sox_ng`
and make a `sox-14.4.3` release, that is of course fine.
After all, it's where everyone goes to get the latest `sox`
and where semiautomatic distros update from.

The easiest way to do this is to make a branch from 14.4.2,
import sox_ng's 14.4.X branch and undo the first post-14,4.2 commit
that changes all "sox" to "sox_ng" and adds `configure --enable-replace`,
then grep everything for `_ng` to make sure.
