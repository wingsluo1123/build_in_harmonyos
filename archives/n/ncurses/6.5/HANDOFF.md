# ncurses 6.5 handoff

## Identity
- Issue: #1437, https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1437
- AgentID: windrel
- Worktree: `D:\Huawei\worktrees\ncurses`
- Branch: `feat/ncurses-6.5-windrel`

## Scope
- Only `archives/n/ncurses/6.5` is changed in this branch.
- This dependency unblocks `boxes/2.3.1` after `libunistring/1.0` is also available.

## Validation plan
```powershell
$env:CI_PACKAGES="archives/n/ncurses/6.5"
# Run project single-package shadow CI on device when lock is available.
```

## Current status
- Conan recipe and direct-compile consumer test package prepared.
- Real-device shadow CI passed on 2026-07-25.
- Passing run: `windrel-ncurses-6.5-ci-20260725-202207-61862`.
- Result: `L0_RESULT=pass`, `L1_RESULT=pass`, `L5_RESULT=pass`, build summary `Success: 1, Failed: 0`.
