# Preregistration version archive (share copy)

This copy carries only the v3 files. The superseded v1 and v2 drafts are in the archived
original repository.

## Added 2026-10-06: which file holds the text as locked

A verification on 2026-10-06 found that `PREREGISTRATION_v3_LOCKED.md` is **not** a frozen
copy. After the lock commit (`95d37e5`, 2026-09-26 04:17 UTC) it was edited three times
(`e1bb781` amendment 1, `284494e` amendment 2, `5976178` amendment 3 and the
"Campaign collected" line). It is therefore the **lock plus amendment log**, not the text as
locked. It has not been edited here; two byte-exact extracts were added beside it instead.
The commit hashes refer to the archived original repository.

| File | Extracted with | What it is |
|---|---|---|
| `PREREGISTRATION_v3_AT_LOCK_eaadaf1.md` | `git show eaadaf1:PREREGISTRATION.md` | The working copy at `eaadaf1` (2026-09-26 04:15 UTC), the commit the lock header names as the code and data state at lock. Its status line reads "READY TO LOCK". It is the pre-lock draft, **not** the frozen text: it lacks §1.5 (the `ancestor_saturation` risk to H1), the Q3 live-validation results in §6.1, the approval of the 44 + 44 family split in §7.1, and the expanded span-persistence note in §8, all of which the lock commit added. |
| `PREREGISTRATION_v3_FROZEN_95d37e5.md` | `git show 95d37e5:_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md` | The frozen copy exactly as the lock commit created it, before any amendment. This is the text as locked. It is byte-identical to `PREREGISTRATION.md` at `95d37e5`. |
| `PREREGISTRATION_v3_LOCKED.md` | (unchanged) | Lock plus amendment log: the `95d37e5` text with §12 amendments 1-3 and the closing "Campaign collected" line added after the lock. |

Checksums. The sha256 values are of the files as extracted (LF line endings, as stored in
git). A Windows checkout with `core.autocrlf=true` rewrites line endings and changes the
sha256 but not the git blob id, so both are recorded.

| File | sha256 | git blob |
|---|---|---|
| `PREREGISTRATION_v3_AT_LOCK_eaadaf1.md` | `fd67e355e4bb6ae973ed06cd6a3acf36fc268dab6b2bf9f090270f92bbe1e38c` | `a6b208be1f5d237d7d3b2f7a9f40ab0a17b23b65` |
| `PREREGISTRATION_v3_FROZEN_95d37e5.md` | `1c2aa2e758229bc9a8374176e60dbee18a6f70aa47be2080c70c431dd4947eb8` | `47f37335718a51d3d9ec7d2d12fa49fceeeaafb0` |
