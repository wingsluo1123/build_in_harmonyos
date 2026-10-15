# Releases

`sox_ng` has a time-based release cycle using Semantic Versioning.
Each of the versions has a new release every six months.

## Release levels

### Micro

Numbered X.Y.Z+1, micro releases include bug fixes, spelling errors
and very small enhancements to existing features but no new features.
Changes, apart from the bug fixes, are both forward- and backward-compatible.

Each six months, all the release series (currently 14.4.X, 14.5.X and 14.6.X)
get all the bug fixes applied in the main development branch since the last
micro release (well, the ones that apply to them).

So, there have been 173 commits to the main branch since the last micro release.

* Ones that introduce new features can be ignored
* Of the rest, if you're lucky there will be a text [issue #416] at the end of
  the first line of the commit message. From that, you can see what milestone
  the issue has and discard it if it is not micro or release.
  If you look through the closed issues in the Conclusion section
  there may be a seven-digit lowercase hex commit hash stem,
  giving you further correlation between commits and issues
  and hence their milestone.
* Now look at each of the remaining commits and decide which of them
  needs to be applied to which of the maintenance branches:
  + bug fixes
  * improvements to the documentation and error messages
  * speed/space improvements

The last micro releases were made on 2025-08-18 and
the next micro releases are scheduled for 2026-08-18.

### Minor

Numbered X.Y+1.0, minor releases add new features and functionality
in a backward-compatible manner but "not too many at once".

The next minor release, 14.9.0, is scheduled for 2026-11-18.

### Major

Major releases, numbered X+1.0.0 include changes that are
not backward-compatible and major new feature sets.

A major release is not planned.

## For each release

On the [Releases](http://codeberg.org/sox_ng/sox_ng/releases) page they will be ordered 
in reverse chronological order of the commit that the tag points to so,
if you are making several at once and want the most recent minor release first,
make the "Release 14.whatever" commits in order from the oldest to the newest.

- Run `make check` and, if you're feeling brave:
  - Make sure it compiles on the GCC Compile Farm
  - Make sure the Vindov builds build
  - Run the testsuite with `valgrind`
  - Run the Address Sanitizer and [`sox-mangler`](https://github.com/kernelslacker/sox-mangler)
- `V=14.4.3-rc1		# or whatever`
- `git checkout main`
- `git status 		# There should be nothing to do`
- If it's a first release candidate
  - Edit `README.md` and `wiki/Releases.md` to change the next release date
  - Change the milestone's description to reflect the next release date
- `git clone https://codeberg.org/sox_ng/sox_ng.wiki wiki`
- `(cd wiki && git push && sh makehtml.sh)`
- Copy in and commit the latest version of https://codeberg.org/sox_ng/issues
- Update ChangeLog from the git logs and fix the date
- Change `AC_INIT` in `configure.ac` to the new version
- Change `src/sox_ng.h`'s `SOX_LIB_VERSION_CODE` to the new version
- `git commit -m "Release $V" -a`
- `git tag -f sox_ng-$V`
- `git push origin $(git branch --show-current)`
- `git push --tags origin $(git branch --show-current)`
- `autoreconf -i`
- `./configure`
- `make txt pdf dist`
- `tar xf sox_ng-$V.tar.gz`
- `zip -rq sox_ng-$V.zip sox_ng-$V`
- `rm -r sox_ng-$V`
- Make the Windows executables
  - `rm -f win32.exe win64.exe`
  - `make win32.exe win64.exe`
  - `zip -jq sox_ng-$V-win32-exe.zip mxe/usr/i686-w64-*/bin/sox_ng.exe AUTHORS ChangeLog COPYING README{,.md,.win32} sox*.{txt,pdf}`
  - `zip -jq sox_ng-$V-win64-exe.zip mxe/usr/x86_64-w64-*/bin/sox_ng.exe AUTHORS ChangeLog COPYING README{,.md,.win32} sox*.{txt,pdf}`
- ``echo '```' ``
- `echo md5sums:`
- `md5sum sox_ng-$V.* sox_ng-$V-*.zip`
- `echo sha256sums:`
- `sha256sum sox_ng-$V.* sox_ng-$V-*.zip`
- ``echo '```' ``
- `firefox https://codeberg.org/sox_ng/sox_ng/releases`
- Poke "New release"
  - Tag name: sox_ng-$V
  - Release title: Release $V
  - Describe this release:
    - First micro release
    - Copy in ChangeLog
    - Add checksums of source tarballs.
  - Click here to upload and select sox_ng/sox_ng-$V.{tar.gz,zip}
  - Use the title and content of release as tag message: No
  - Mark as prerelease if it's not a stable release
  - Hide automatically generated archives: Yes
  - Poke "Publish release". This is the no-going-back point.
- Announce the release on sox-ng@groups.io
- For a first release candidate, contact the people who contributed to it
- Wait a week; if no problems are evident, it becomes the release;
  otherwise issue another release candidate for another week's testing,
  and so on
- When a release candidate is OK for a week, it becomes the release
- Announce the final release on [http://freshcode.club](http://freshcode.club)
- Announce release candidates on sox-ng@groups.io and sox-devel@lists.sourceforge.net
- Announce final releases on sox-ng@groups.io and sox-users@lists.sourceforge.net
- Change configure.ac's release number to $V+git, check in and push
  Historically it has been 14.4.3git where 14.4.3 is the next release
  but this conflicts with [semantic versioning](http://semver.org) and
  we don't know whether the release after 14.4.3.1 will be
  14.4.3.2, 14.4.4 or 14.5.0.

## Further reading

### Release management

- Karl Fogel's book [*Producing OSS*](http://producingoss.com) chapter 3: *Release management* and chapter 6: *Release Strategy*
- Michael Michlmayr's PhD theses [*Open Source Software Projects: Exploring the Impact of Release Management*](http://www.cyrius.com/publications/michlmayr-phd.pdf) on the merits of time-based released over "when it's ready" releases.
- [*Producing OSS*](http://producingoss.com) chapter 5: *Time Based Releases*

### Semantic versioning

- [*Producing OSS*'s section on semantic versioning](https://producingoss.com/en/development-cycle.html#semantic-versioning)
- The [*Semantic Versioning Specification*](http://semver.org)
