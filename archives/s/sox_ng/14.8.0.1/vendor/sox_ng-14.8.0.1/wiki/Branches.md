# Branches

A rethinking of how to use git branches to maintain multiple release lines.

So far (2025-01-13) I've been committing almost everything into
the `main` git branch and sprouting maintenance branches at
various release points to apply bug fixes for future micro releases
in that series.

    main
     ^ 
     | <bug fixes>
    Release 14.5.0.2 ----> branch 14.5.0.X: further critical patches to 14.5.0
     | <critical fix>
    Release 14.5.0.1
     | <critical fix>
    Release 14.5.0 ------> branch 14.5.X
     | <new features and bug fixes>
    Release 14.4.3.1 ----> branch 14.4.X (used to be called branch 14.4.4)
     | <fixes to 14.4.3>
    Release 14.4.3
     | <bug fixes only>
    Release 14.4.2
     |
     History...

What should have happened is:

    will be 14.6.0
     ^
     |
    main (a.k.a 14.X)
     ^                     will be Release 14.5.1
     |                      ^
     | <new features>       |                 Release 14.5.0.2
     |                      | <bug fixes       | <critical patch>
     |                      |  to 14.5.0>     Release 14.5.0.1
     |                      |                  | <critical patch>
    Release 14.5.0 ------> branch 14.5.X ---> branch 14.5.0.X
     ^
     |                     will be Release 14.4.4
     |                      ^
     |                      |                  Release 14.4.3.1
     | <new features>       |                   | <critical patch>
     |                     Release 14.4.3 ---> branch 14.4.3.X
     |                      ^
     |                      | <bug fixes to 14.4.2>
     |                      |
     |-------------------> branch 14.4.X
     |
     | <The sox_ng hard fork>
     |
    Release 14.4.2 from sox.sf.net
     ^
     |
    History...

What I now face is importing all the bug fixes from main
* that apply to Release 14.4.3 into branch 14.4.X for Release 14.4.4
* that apply to Release 14.5.0 into branch 14.5.X for Release 14.5.1
but they'll be new commits with the same contents but with different hashes,
which makes referencing them from the issues a pain, as well as storing
all changes several times in the git tree.

What I should have done is
- develop every bug fix on its own personal branch
  and when it's OK merge it into every branch that it applies to
- develop each new feature on its own personal branch
  and when it's OK merge it into main

As to where each bug fix's branch should sprout from...
the oldest place that has the bug?
That's easy for bugs that were in 14.4.2, less so for bugs in new stuff
and for fixes to areas that have already received bug fixes.

We can probably do critical patches on the 14.?.?.X branches
and merge them into the 14.?.X branches and main.

We can probably do bug fixes on the oldest 14.?.X branch that they apply to
and merge that branch into the 14.?.X branches newer than them and into main.
