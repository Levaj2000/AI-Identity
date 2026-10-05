# Praxis in-tree port, staged

The prepared pull request for praxis-proxy/policy that
[`PRAXIS-INTREE-PLAN.md`](../PRAXIS-INTREE-PLAN.md) describes: this crate
adapted to that tree as `reference/plugins/ocsf-audit`, crate
`praxis-policy-plugin-ocsf-audit`. It is kept here as patches because the
praxis repository gates merges on a CLA that resolves every commit identity
to a GitHub account, so the maintainer applies and pushes them under his own
identity. Delete this directory once the praxis pull request merges; the
patches are a snapshot, not a mirror.

| File | What it is |
|---|---|
| `0001-import.patch` | Verbatim copy of this crate at AI-Identity `395d64e` into `reference/plugins/ocsf-audit`. Not a workspace member yet. |
| `0002-adapt.patch` | The adaptation: workspace member, workspace dependencies, the PPE lint set, edition 2024, headers and comments, README and auditing-guide edits. The whole port is this diff. |
| `PRBODY.md` | The pull request description. |
| `review/` | Follow-up patches answering review rounds on the open pull requests; see "Review follow-ups". |

Both patches apply on praxis `main` at `da22e0a`, the merge commit of
praxis-proxy/policy#84. They were produced and verified on that commit with
the pinned toolchain (1.96.0, nightly rustfmt): `make lint`, `make test`,
`make doc` and `cargo deny check` clean, 35 tests, the three conformance
vectors byte-identical, `panic_drive` landing the driven panic on
`gw-1:decision` at `stream_seq` 0. Full numbers are in `PRBODY.md`.

## Routing

Nothing here posts to praxis from a session. The maintainer runs the blocks
below from his own terminal. Each block returns to the prompt on failure.

Forking is disabled on `praxis-proxy/policy`: GitHub answers "You can't fork
this repository at this time" to both the API and the fork page (observed
2026-10-05). The push block therefore needs collaborator write access on the
repository itself. Without it, hand the maintainers the signed-off patches
(see "Hand-off without push access").

## Apply (squash copy, the default)

Fetches the patches from this repository's `main`, clones praxis at the
base commit, and applies both patches signed off under the GitHub noreply
identity. Inspect the result before the next block.

```bash
(
set -e
mkdir -p ~/ocsfport && cd ~/ocsfport
BASE=https://raw.githubusercontent.com/Levaj2000/AI-Identity/main/integrations/cpex-ocsf-audit/praxis-port
curl -fsSL -o 0001.patch "$BASE/0001-import.patch"
curl -fsSL -o 0002.patch "$BASE/0002-adapt.patch"
curl -fsSL -o prbody.md "$BASE/PRBODY.md"
rm -rf policy
git clone -q https://github.com/praxis-proxy/policy policy
cd policy
git checkout -q -b port/ocsf-audit da22e0aff86de0bb20c5fae3406f73c40576b078
git -c user.name='Jeff Leva' -c user.email='120221487+Levaj2000@users.noreply.github.com' am -s ../0001.patch ../0002.patch
git log --format='%h %an %s' -2
cargo test -p praxis-policy-plugin-ocsf-audit 2>&1 | grep 'test result'
)
```

## Push and open the pull request

Needs push access to `praxis-proxy/policy`; the block checks and stops before
pushing if the account does not have it. Opens the pull request as a draft
with `PRBODY.md` as its body. Mark it ready from the GitHub page.

```bash
(
set -e
cd ~/ocsfport/policy
test "$(gh api repos/praxis-proxy/policy --jq .permissions.push)" = "true" || { echo "no push access to praxis-proxy/policy and forking is disabled; ask a maintainer for collaborator write, or use the hand-off block"; exit 1; }
git push -u origin port/ocsf-audit
gh pr create --repo praxis-proxy/policy --base main --head port/ocsf-audit --draft --title 'feat(audit): OCSF audit sink as a reference plugin' --body-file ../prbody.md
)
```

## Hand-off without push access

Writes the two commits from the local branch as patches that carry the
maintainer's sign-off (the patches fetched by the apply block do not; `git am
-s` added the sign-off locally), plus the pull request body, into one folder
to send. A praxis maintainer applies them with `git am` on a branch from
`da22e0a` and pushes; the commits keep their author, so the CLA check
resolves to the author's account, not the pusher's.

```bash
(
set -e
cd ~/ocsfport/policy
rm -rf ~/ocsfport/forteryl && mkdir -p ~/ocsfport/forteryl
git format-patch -2 -o ~/ocsfport/forteryl
cp ../prbody.md ~/ocsfport/forteryl/prbody.md
ls -l ~/ocsfport/forteryl
)
```

## Alternative: import with history

`docs/dev/port-provenance.md` in praxis records their convention for the two
earlier imports: `git-filter-repo` in a single pass with the path rename,
merged with unrelated histories allowed, so `git blame` reaches back to the
source. If Teryl asks for that shape, this block replaces the first one.
The filtered history is 28 commits and 16 files, and its tip tree is
identical to what `0001-import.patch` adds, so `0002-adapt.patch` applies on
top unchanged. Verified end to end on 2026-10-02.

The source history is not clean enough to import as is. Of the commits that
touch the seven selected paths at `395d64e`, one is authored by Claude, one
by renovate, seven carry `Co-Authored-By: Claude` and `Claude-Session`
trailers (one in lowercase, from a squash), and none carries a sign-off. Praxis forbids AI co-author trailers
and requires human sign-off on every commit, and its CLA check resolves every
author to a GitHub account (the ws4 PR #181 failure of 2026-09-08 was exactly
a Claude-authored commit). The block below rewrites author and committer to
the maintainer, strips both trailer kinds, appends the sign-off, and refuses
to continue if any commit still mentions Claude. Do not run the earlier,
unfiltered form of this block; it was run once on 2026-10-05 and would have
pushed all of the above.

```bash
(
set -e
command -v git-filter-repo >/dev/null 2>&1 || brew install git-filter-repo
mkdir -p ~/ocsfport && cd ~/ocsfport
BASE=https://raw.githubusercontent.com/Levaj2000/AI-Identity/main/integrations/cpex-ocsf-audit/praxis-port
curl -fsSL -o 0002.patch "$BASE/0002-adapt.patch"
curl -fsSL -o prbody.md "$BASE/PRBODY.md"
rm -rf aidsrc policy
git clone -q https://github.com/Levaj2000/AI-Identity aidsrc
cd aidsrc
git checkout -q -b import-src 395d64ed8bea695896af1557e530b0065145f593
git filter-repo --force --refs import-src --path integrations/cpex-ocsf-audit/src --path integrations/cpex-ocsf-audit/examples --path integrations/cpex-ocsf-audit/Cargo.toml --path integrations/cpex-ocsf-audit/README.md --path integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md --path integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-DECISIONS.md --path integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-PROVENANCE.md --path-rename integrations/cpex-ocsf-audit/:reference/plugins/ocsf-audit/ --commit-callback 'commit.author_name = b"Jeff Leva"; commit.author_email = b"120221487+Levaj2000@users.noreply.github.com"; commit.committer_name = commit.author_name; commit.committer_email = commit.author_email' --message-callback 'keep = [l for l in message.split(b"\n") if not l.lower().startswith((b"co-authored-by:", b"claude-session:", b"signed-off-by:"))]; return b"\n".join(keep).rstrip(b"\n") + b"\n\nSigned-off-by: Jeff Leva <120221487+Levaj2000@users.noreply.github.com>\n"'
test "$(git log --format='%an %ae %cn %ce %B' import-src | grep -ci claude)" = "0"
test "$(git log --format='%B' import-src | grep -c '^Signed-off-by:')" = "$(git rev-list --count import-src)"
cd ..
git clone -q https://github.com/praxis-proxy/policy policy
cd policy
git checkout -q -b port/ocsf-audit da22e0aff86de0bb20c5fae3406f73c40576b078
git fetch -q ../aidsrc import-src
git -c user.name='Jeff Leva' -c user.email='120221487+Levaj2000@users.noreply.github.com' merge --allow-unrelated-histories --no-edit -m 'chore(audit): import the OCSF audit sink from AI-Identity with history' FETCH_HEAD
git -c user.name='Jeff Leva' -c user.email='120221487+Levaj2000@users.noreply.github.com' am -s ../0002.patch
git log --format='%h %an %s' -3
cargo test -p praxis-policy-plugin-ocsf-audit 2>&1 | grep 'test result'
)
```

The push block above then applies unchanged (it still needs push access). In that shape the pull request
also owes `docs/dev/port-provenance.md` a third import section (source
commit `395d64e`, 28 commits after filtering, 16 files, the seven selected
paths); write it in the praxis checkout as its own commit before pushing,
since it only exists in this shape.

## Review follow-ups (praxis #171 and #173)

`review/` holds the patches that answer the first CodeRabbit round on the
two praxis pull requests, prepared 2026-10-05 and verified on the pinned
toolchain (36 tests, clippy clean, `panic_drive` unchanged in what it
asserts). Same routing as everything above: the maintainer applies them
with his own identity and sign-off and pushes to his fork, which is where
both pull requests live.

| File | Lands on | What it changes |
|---|---|---|
| `review/0003-review-171.patch` | praxis #171, branch `port/ocsf-audit` | Refuse `signing: dsse` with `chain: false` at construction (a test pins it); declare `read_subject` in `panic_drive`'s YAML; reword the key-ordering note in SAMPLE-OUTPUT.md. |
| `review/0004-review-173.patch` | praxis #173, branch `spike/audit-serialization-transport` | F5 reports a stream gap as loss evidence, not a verification failure; R5 requires keyed digests where the host provides a key and names the unkeyed form as guessable. |
| `review/0005-review-173-tail.patch` | praxis #173, after 0004 | Second round: a dense `stream_seq` from 0 shows no leading or interior gap but cannot show a trailing loss; tail completeness needs a trusted terminal sequence or checkpoint from the host. |
| `review/0006-review-171-round2.patch` | praxis #171, after 0003 | Second round: `#[serde(deny_unknown_fields)]` on the config (a misspelled `authority_uid` was silently dropped), with a test; the canonicalizer writes object keys without cloning them. This crate takes both. |
| `review/0007-review-171-vendor.patch` | praxis #171, after 0006, the maintainer's choice | Default `metadata.product` to Praxis instead of AI Identity for deployments that set neither name. Every example and vector sets both explicitly, so no vector changes. In-tree only; this crate keeps its own defaults. |

The findings these do not address, and why, are in the pull request
threads: `#![allow]` to `#![expect]` on the examples (the tree's own
examples carry the same block; `expect` fails when a lint does not fire),
the dependency-pinning
conventions and the docstring threshold (the maintainers' call), and the
uid collision across restarts and the RFC 8785 finding (both confirmed:
`cmf.mcp` and violation details are open JSON, so floats and non-ASCII
keys can reach the canonicalizer and falsify the `serialization_id 2`
claim in release; both change the hashed bytes and the vectors, so they
land in this crate first with a spec bump and a validator that does full
RFC 8785, then the port follows). The decline of the RFC 8785 finding in
the first round was wrong and is withdrawn on the thread.

The `dsse` guard and the SAMPLE-OUTPUT.md wording land in this crate in the
same change that adds these patches. `read_subject` is a PPE capability
with no cpex counterpart, so the canonical `panic_drive` is unchanged.

```bash
(
set -e
cd ~/ocsfport/policy
curl -fsSL -o ../0003.patch https://raw.githubusercontent.com/Levaj2000/AI-Identity/main/integrations/cpex-ocsf-audit/praxis-port/review/0003-review-171.patch
git -c user.name='Jeff Leva' -c user.email='120221487+Levaj2000@users.noreply.github.com' am -s ../0003.patch
cargo test -p praxis-policy-plugin-ocsf-audit 2>&1 | grep 'test result'
git push fork port/ocsf-audit
)
```

```bash
(
set -e
cd ~/praxisspike/policy
curl -fsSL -o ../0004.patch https://raw.githubusercontent.com/Levaj2000/AI-Identity/main/integrations/cpex-ocsf-audit/praxis-port/review/0004-review-173.patch
git -c user.name='Jeff Leva' -c user.email='120221487+Levaj2000@users.noreply.github.com' am -s ../0004.patch
git push fork spike/audit-serialization-transport
)
```
