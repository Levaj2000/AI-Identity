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

Both patches apply on praxis `main` at `da22e0a`, the merge commit of
praxis-proxy/policy#84. They were produced and verified on that commit with
the pinned toolchain (1.96.0, nightly rustfmt): `make lint`, `make test`,
`make doc` and `cargo deny check` clean, 35 tests, the three conformance
vectors byte-identical, `panic_drive` landing the driven panic on
`gw-1:decision` at `stream_seq` 0. Full numbers are in `PRBODY.md`.

## Routing

Nothing here posts to praxis from a session. The maintainer runs the blocks
below from his own terminal. Each block returns to the prompt on failure.

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

Pushes to `origin` when the account has push access to praxis, otherwise to
a fork, and opens the pull request as a draft with `PRBODY.md` as its body.
Mark it ready from the GitHub page.

```bash
(
set -e
cd ~/ocsfport/policy
REMOTE=origin
HEADREF=port/ocsf-audit
if [ "$(gh api repos/praxis-proxy/policy --jq .permissions.push)" != "true" ]; then
  gh repo fork praxis-proxy/policy --remote --remote-name fork >/dev/null 2>&1 || true
  REMOTE=fork
  HEADREF="$(gh api user --jq .login):port/ocsf-audit"
fi
git push -u "$REMOTE" port/ocsf-audit
gh pr create --repo praxis-proxy/policy --base main --head "$HEADREF" --draft --title 'feat(audit): OCSF audit sink as a reference plugin' --body-file ../prbody.md
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
git filter-repo --force --refs import-src --path integrations/cpex-ocsf-audit/src --path integrations/cpex-ocsf-audit/examples --path integrations/cpex-ocsf-audit/Cargo.toml --path integrations/cpex-ocsf-audit/README.md --path integrations/cpex-ocsf-audit/SAMPLE-OUTPUT.md --path integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-DECISIONS.md --path integrations/cpex-ocsf-audit/SAMPLE-OUTPUT-PROVENANCE.md --path-rename integrations/cpex-ocsf-audit/:reference/plugins/ocsf-audit/
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

The push block above then applies unchanged. In that shape the pull request
also owes `docs/dev/port-provenance.md` a third import section (source
commit `395d64e`, 28 commits after filtering, 16 files, the seven selected
paths); write it in the praxis checkout as its own commit before pushing,
since it only exists in this shape.
