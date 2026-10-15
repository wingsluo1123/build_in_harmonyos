# Backups

## Repository

The repository has been migrated to

* [git.kaki87.net/sox_ng/sox_ng](https://git.kaki87.net/sox_ng/sox_ng)
* [v9.next.forgejo.org](https://v9.next.forgejo.org/sox_ng/sox_ng)

and cloned on

* sourcehut.org
  * [code](https://git.sr.ht/~sox_ng/sox_ng)
  * [wiki](https://git.sr.ht/~sox_ng/sox_ng.wiki) -> tree

### Access tokens

`sox_ng`'s read-everything Access Tokens for migrations from `codeberg.org` is:

    7b3e922513587437ba698e2fa3421f92a044a990

### Code

It's easy enough to make a backup of the code tree:

    git clone https://codeberg.org/sox_ng/sox_ng

There is a copy of the code repository at
[git.kaki87.net/sox_ng/sox_ng](https://git.kaki87.net/sox_ng/sox_ng)
which is constantly updated ("push mirrored") by Codeberg.

### Wiki

It's easy enough to make a backup of the wiki:

    git clone https://codeberg.org/sox_ng/sox_ng.wiki wiki

There is a copy of the wiki at
[git.kaki87.net/sox_ng/sox_ng/wiki](https://git.kaki87.net/sox_ng/sox_ng/wiki)
which is constantly updated ("push mirrored") by Codeberg.

### Issues

It's easy enough to make a backup of the issues'
title, description, milestone, labels and attachments:

    sh issues/getissues.sh

The issues are not automatically updated by the push mirror
but if you have write permission to the issues on `git.kaki87.net`
they can be updated periodically by running in a `sox_ng` git dir:

    issues/getissues.sh
    issues/putissues.sh -s git.kaki87.net -f

## Mail

### Mailing list

[`sox-ng@groups.io`] is automatically archived
[on mail-archive.com](https://www.mail-archive.com/sox-ng@groups.io)
and is received by `sox_ng@fastmail.com`

### Private mailbox

The mail of `sox_ng@fastmail.com` can be downloaded by an IMAP client
by anyone having its password.

## Keyholders

See [Accounts](Accounts) for a list of keys/keyholders of the above.
