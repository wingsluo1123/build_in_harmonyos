# Hosting

## Requirements

### Summary

    Legend
    OSE  Open Source Engine
    !JS  Web interface works without JavaScript
    IAPI You can manipulate the issues from a script
    WAPI You can manipulate the wiki from a script
    JSON ...using curl/wget with JSON
    git  ...using git

| Platform	| OSE | !JS | IAPI | WAPI |
| :-------	| :-: | :-: | :--: | :--: |
| sourceforge	|  N  |  Y  |      |      |
| github	|  N  |  Y  |      |      |
| gitlab	|  Y  |  N  |      |      |
| forgejo	|  Y  |  N  | JSON | git  |
| sourcehut	|  Y  |  Y  | JSON | git  |
| savannah	|  Y  |  Y  |      |      |
| launchpad	|  Y  |  Y  |      |      |

### Code Repository

A "master copy" of the git code base.

#### sourceforge.net

* the historic home of `sox`
* a closed-source platform that locks projects in
* all the existing links on the web point to it as SoX's home page
* is where users and automatic systems will look for new releases
* if we can admin the existing project, it's less stressful for distros
  and will update the 37,000 people (bots?) per week who download from there
* becoming admin on the existing project appears not to be possible 
* unreliable: you couldn't post to its mailing lists for a week this year
* old and crappy. Very '90s

On 2026-02-16 in cfarm-users, Jacob Bachmeyer writes:

> the GNU Ethical Repository Criteria (item (C2)):
> "Does not discriminate against classes of users, or against any country."
> Sourceforge infamously fails on this point by refusing service
> (including downloads) to network endpoints apparently in countries
> sanctioned by the US government.

#### github.com

* the home of most forks of `sox`
* commercial
* their engine is closed-source
* owned by Microsoft
* last year, they stopped me being able to push to my repositories
  by insisting on 2FA that I was unable to set up

#### gitlab.com

The most popular alternative for those running away from github
* interface looks like github
* their engine is open-source
* they seem ok but are still `.com`
* technically nothing special

#### forgejo instances

##### codeberg.org

* Version `8.0.3-plus-patches`
* managed by a large and stable non-profit association
* runs on a modern open-source platform [`forgejo`](forgejo.org)
* the org is also active in development of the platform
* support line is fast and helpful
* you can switch between two web users without logging out and logging in again
* you can do everything from the command line except create a new repository,
  a deliberate choice made to prevent overloading and people making backups
  of everything
* Allows you to attach any type of file and to `git push -f`
* Sometimes has unplanned downtime and problems

##### disroot.org

* Version `8.0.3+gitea-1.22.0`
* is managed by a non-profit organization "based on principles of
  freedom, privacy, federation and decentralization: No tracking,
  no ads, no profiling, no data mining"
* provides many free software services, not just repository hosting
* The support line does not answer
* You can't attach binary files to issues

##### git.pub.solar

* Version `7.0.9`
* The API does not work with username/password authentication saying
  `user's password isn't set [uid: 58, name: sox_ng]`

##### git.kaki87.net

* Version `8.0.3+gitea-1.22.0`
* Allows you to attach any type of file to issues

##### sij.ai

* Version `8.0.3+gitea-1.22.0`
* "A painless, self-hosted Git service"
* You can't attach binary files to issues

##### git.gay

* Version `8.0.3-gay+gitea-1.22.0`
* "Git hosting for the queers"
* [Uses a modified version of Forgejo.](https://codeberg.org/forgejo-contrib/delightful-forgejo#public-instances)
* Migration from disroot fails repeatedly:
  `Get "https://git.disroot.org/api/v1/version": read tcp 213.210.34.144:47682->178.21.23.200:443: read: connection reset by peer`
* You can't attach binary files to issues

#### sourcehut.org

* appears to be managed by a few individuals
* support line is helpful
* runs 100% open source software: for the repositories `forgeperf`
  which is lightweight and does not use javascript
* the software is alpha and "Payment will be required later:
  from the beta onwards, unpaid accounts will be limited to
  read-only access to their own projects" and
  "We can terminate service at any time"
* has had massive and complete outage due to a DDoS attack and
  had their servers stolen while relocating a datacenter so
  either someone hates them particularly or
  they are less capable than others
* You can't comment on commits
* A year after I had subscribed to support them (twice by mistake!)
  but then decided not to use it, they sent me an urgent action-required
  begging letter every day for weeks

#### savannah.nongnu.org

* managed by the Free Software Foundation
* high-visibility and a form of "grandad's approval" of your project
* support line seems irritable but is strong on legal issues
  and has pro-bono lawyers
* gives better accessibility for the blind or partially sighted
  according to Eric Wong
* project registration is laborious and slow but their
  stringent requirements can improve project quality.
  After over a month I have still been unable to test-drive it
* old and a bit crappy
* only hosts GPLv3-or-later projects; [`SoX` is GPLv2-only](Copyright)

#### launchpad.net

* Managed by Canonical "Trusted open source for enterprises" but Ubuntu-centric
* `sox_ng` needed to be private until its first release but
  to have a private repository you need a "commercial subscription"
  which expires within a few weeks unless you pay or are "approved"
  by Canonical
* Their "security" panels cross-site script to Google
* Usernames cannot contain an underscore

### Issue tracker

I think all the Code Repositories come with an issue tracker.
There may be some advantage in using the issue tracker of the
code base platform.

The real answer is to keep the issues in the code repo
so that code and its issues always accompany each other.

#### bugzilla

* You can't edit or delete your comments

#### sourceforge.net

* You can't edit or delete your comments

#### github.com

* You can edit and delete your comments

#### gitlab.com

* You can edit and delete your comments

#### forgejo instances

* You can edit and delete your comments
* There is a JSON API to perform all operations on the issues
* "migrating" a repository to another `forgejo` instance
  loses all the attachments to issues

#### sourcehut.org

* You can edit your tickets and comments on tickets
  but can only delete tickets, not comments
* There is a JSON API to perform all operations on the issues
* "you can send a plaintext email with your bug report,
  whether or not you have an account"

### Wiki

I think they all provide a wiki using a variant of markdown.

#### sourceforge.net

#### github.com

#### gitlab.com

#### forgejo instances

* user/repo's wiki is a separate git repository
  https://codeberg.org/user/repo.wiki
* The web interface saves pages with CRLF instead of LF so
  successive edits between web and command line also update all
  lines that ended in LF, making the git history useless
  (solution: only update it from the command line)
* The command line is the only way to upload images or attachments
* The landing page is `Home.md`

#### sourcehut.org

* Every wiki is either a orphan branch of some other repo
  or a separate repository
* It doesn't have a web-based editor; it's all command-line and git
* The landing page is `index.md`

### Mailing list

##### sourceforge.net

* does mailing lists
* is unreliable: you couldn't post to its mailing lists for a week this year

#### github.com

#### gitlab.com

#### codeberg.org

* does not provide mailing lists

#### disroot.org

* does not provide mailing lists

#### sourcehut.org

* provides mailing lists but you cannot subscribe to them without
  registering on sourcehut

#### savannah.nongnu.org

* provides mailing lists

#### freelists.org

* The mailing list was @freelists.org but they refuse to let
  anyone else archive it by rejecting subscriptions from known
  archive sites' addresses.
  A support request was opened about this and was rejected

#### groups.io

* Seems to work
* The support line is fast and helpful
* You can't have an underscore in a group's name, only a hyphen

### Secure email address

The recovery address for the above web services and
the address for confidential or certified-sender messages
to the SoX-ng admins and for key transfers and financial matters.

They seem to be of two kinds:

#### End-to-end JavaScript encryption

  * They claim to use end-to-end encryption but *they* send you the code to run
    so it would be easy to put something in it to send them your every thought
    as you type it if the NSA asked for it in their nice and irresistible ways
  * You probably only get E2E encryption between two accounts
    of the same provider
  * Asking someone else to do your privacy for you is like
    asking someone else to keep a secret for you

##### protonmail.com

* E2E encryption in JavaScript
* Free accounts but it begs for money a lot and persistently
* Support's replies are prompt
* If you open a personal account and a project account you have to
  pay two subscriptions to use IMAP. Already asked and refused.
* They seem to have immense amounts of money

##### tutamail.com

* Seems OK but has the same fundamental flaw

#### PGP on top of any email service

* Normal people can't set PGP up;
  even many seasoned hackers have a hard time

##### fastmail.com

* Seems OK
* The receipt they sent for sox_ng's subscription was headed as being for
  `Keen.tea6429@fastmail.com` so I have no proof that I paid them
* Their help line sends you a boilerplate reply the next day
  telling you to chat with their AI bot

##### disroot.org

* provides free email accounts
* You have to create a separate account from your `forgejo` one
  but I have been unable to do so because
  their password-strength meter on the registration webform
  refuses any password, even line noise, as "Too weak"

## Self hosting

An alternative to any these is self-hosting on a dedicated server
or on a rented VPS.

* You can choose whichever software seems best for each service
* It's more secure
* It's more work
* It's less reliable

## Conclusion

* The code repository is `https://codeberg.org/sox_ng/sox_ng`
  with `https://git.kaki87.net/sox_ng/sox_ng` as a hot mirror
* The issue tracker is the one on Codeberg.
  You can modify the issues with the web interface and
  make a local copy from the command line.
  You can update the web version from the local copy
  but any changes made via the web interface between when you run
  `getissues.sh` and `putissues.sh` will be lost.
* The wiki is on Codeberg with Kaki87 as a hot mirror
* The mailing list is on `groups.io`
  * email [`sox-ng@groups.io`](mailto:sox-ng@groups.io) to post,
  * email [`sox-ng+subscribe@groups.io`](mailto:sox-ng+subscribe@groups.io)
    to subscribe
  * web [`groups.io/g/sox-ng`](https://groups.io/g/sox-ng) for both
  * and is [archived on mail-archive.com](https://www.mail-archive.com/sox-ng@groups.io)
* The private mail address is `sox_ng@fastmail.com`.
  I naïvely started with `sox_ng@proton.me` and that is
  still the recovery address for some of the web resources
