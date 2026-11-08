# Profile activity

The profile's SVG cards are generated from GitHub's contribution calendar by
`scripts/generate_cards.py`. The refresh workflow runs hourly, on relevant
default-branch pushes, and when manually dispatched in GitHub Actions.

## What the numbers mean

- **Current streak:** consecutive UTC dates with at least one contribution.
  An unfinished today does not break yesterday's streak.
- **Longest streak:** the longest consecutive run across the account's history,
  including runs that cross a year boundary.
- **Active days:** distinct dates with one or more contributions.
- **Recent activity:** all contributions today and over the last 7 or 31 days.
- **Total commits:** GitHub's counted commit contributions across calendar years.
  Bot-authored refresh commits are not the profile owner's commits.

Future calendar padding is excluded. The public snapshot reflects the data
visible to the workflow token. A configured `METRICS_TOKEN` can provide private
contribution visibility; never commit a token to this repository.

## Refresh and verification

1. Check the workflow badge and timestamp below the activity chart.
2. Open `assets/activity-data.json` to inspect the source counts.
3. Compare today's count with the live GitHub contribution calendar.
4. For a missing commit, check its author association, default branch, and
   repository eligibility. GitHub indexing and image caching can delay display.

SVG image URLs include content hashes, so updated cards receive new URLs.
No displayed contribution count is fabricated or backdated.

Run locally with Python 3.12 and `GH_TOKEN` (or `GITHUB_TOKEN`) in the environment:

```sh
python scripts/generate_cards.py
```

The generator uses only Python's standard library. Its JSON snapshot records
the refresh time in UTC; Tunisia local time is UTC+1.

## Diagnosing a stale graph without changing its design

Run `python -m unittest discover -s tests` before changing generation code. The
regressions check streak boundaries, SVG dimensions, green calendar colors,
curve coordinates, text escaping, reduced-motion support, and image hashes.

If the calendar is current but a README image is stale, compare its `?v=` value
with the first 12 hexadecimal characters of the SVG's SHA-256. Regenerate the
cards and links together; do not edit counts or chart coordinates by hand.
If both are stale, inspect the latest **Update profile cards** run and its
generation step. Re-run the workflow after new default-branch commits have
appeared in GitHub's calendar. A successful push alone does not prove indexing.

For an activity audit, save the calendar count before and after the work, record
the new commit hashes and their default branches, and verify each commit's author
is associated with the profile owner. Report the observed difference separately
from the number pushed. Automated card-refresh commits belong to the bot and
must not be reported as new owner-authored contributions.

## Generated asset reference

| File under `assets/` | Purpose | Source |
| --- | --- | --- |
| `activity-data.json` | Inspectable counts and refresh time | GitHub GraphQL |
| `activity.svg` | Activity curve since September 26, 2026 | Lifetime calendar |
| `heatmap.svg` | Rolling 365-day calendar | Lifetime calendar |
| `streak.svg` | Active days, current streak, longest streak | Lifetime calendar |
| `recent-activity.svg` | Today, last 7 days, last 31 days | Recent calendar |
| `stats.svg` | Account and repository totals | Account queries |
| `top-langs.svg` | Language byte shares | Public repository languages |
| `activity-updated.svg` | Snapshot timestamp | Generator's UTC clock |
| `profile-views.svg` | Last accepted view count | Counter snapshot script |

Generated files support maintenance even when the README does not embed every
card. The visible streak image currently uses the external streak service.

## Generator configuration

Run commands from the repository root. `GH_USER` selects the GitHub login and
defaults to `MoallaMelek`. `GH_TOKEN` takes precedence over `GITHUB_TOKEN`.
The generator stops before making requests when neither token is set.

The workflow supplies the repository owner as `GH_USER`. Output paths are
derived from the script location, rather than the shell's working directory.
No third-party Python package is required.

## Lifetime and annual statistics

The total-commit value sums GitHub's `totalCommitContributions` across account
years. Separate calendar-year queries avoid requesting the entire account
history in one contribution collection. The current year's contribution total
comes from its own January-to-refresh-time query.

These values measure different things: yearly contributions include activity
beyond commits. Do not use the yearly total as a commit count or derive the
owner's work from the number of bot refresh commits.

## Curve and calendar ranges

The curve includes dates from September 26, 2026 onward. Its vertical scale
adapts to the highest count in that range, so a higher peak can change the
positions of older points without changing their counts.

The heatmap includes today and the preceding 364 dates. Dates before that
window can still contribute to lifetime streak metrics. Both renderers remove
future calendar padding; their different ranges are intentional.

## Recent activity boundaries

Recent-activity windows include today. A seven-day total covers offsets zero
through six days ago; a 31-day total covers offsets zero through thirty days
ago. A contribution seven days ago is outside the weekly total, while one
thirty days ago is still inside the monthly total.

The active-day caption counts dates with positive contributions, rather than
the number of contributions. Missing dates contribute zero to these windows.

## Streak examples

With contributions on Monday and Tuesday, an unfinished Wednesday preserves a
current streak of two days. If Wednesday finishes with no contributions and
Thursday also has none yet, the current streak is zero.

A contribution on Thursday starts a new streak of one day; it does not fill
Wednesday. The longest historical run remains available independently of the
current streak. Adding more commits on one date increases volume, not days.

## Project card maintenance

The `PINNED` list in `scripts/generate_cards.py` selects which project cards
are generated. A listed name must match a repository returned by the account
query. Missing projects are skipped; adding a name does not add a README link.

Cards use the repository description, primary language, stars, and forks.
Descriptions are limited to three wrapped lines. A missing primary language
uses Markdown, and long names shrink to fit the existing card width.

## Language card interpretation

Languages are weighted by repository language bytes, not commit volume, usage
frequency, or proficiency. The query reads public, owned, non-fork repositories;
the profile repository is excluded from project aggregation.

The generator excludes Hack, Batchfile, and Objective-C as tooling noise.
It displays up to eight languages; percentages use the aggregated language
total before that display limit. Listed percentages therefore need not sum to
100 when additional languages exist. The query currently requests at most
100 repositories and 20 languages per repository.

## Profile-view recovery

`scripts/refresh_profile_views.py` accepts a numeric SVG counter title.
Oversized, malformed, unavailable, or decreasing responses keep an existing
snapshot and produce a warning. Without an existing snapshot, a failed refresh
raises an error instead of inventing a badge.

A successful response is written to a temporary file and then replaces the
badge. The snapshot request uses its own user agent. The separate one-pixel
README image remains responsible for recording profile requests.

## Failed refresh procedure

1. Open the failed **Update profile cards** run.
2. Identify the first failed step: tests, view snapshot, card generation, or
   commit publication.
3. For a test failure, reproduce the reported test before changing generation.
   For a generation failure, inspect the API error and token availability.
4. For a publication failure, compare the checked-out branch with current
   `master`; retain newer repository changes.
5. Correct the cause, rerun the workflow, and inspect the resulting JSON timestamp.

A successful test step alone does not prove that cards were generated or pushed.
Keep the last published assets until a complete refresh succeeds.

## Scheduling and concurrent updates

The workflow is scheduled at minute 17 of each UTC hour and also supports
manual dispatch. Pushes to `master` trigger it when a configured path changes.
Check the workflow file for the current path list.

The `profile-cards` concurrency group cancels an older in-progress run when a
newer one starts. Checkout explicitly targets current `master`, and publication
rebases onto the remote branch before pushing. If publication still fails,
inspect concurrent edits; do not force-push generated cards over them.

## Credentials and workflow permissions

The workflow grants `contents: write` so its final step can publish generated
assets. Card generation uses `METRICS_TOKEN` when configured, otherwise the
built-in `GITHUB_TOKEN`.

Use repository secrets for credentials. Do not put token values in command
examples, documentation, snapshots, screenshots, or logs. A change in token
visibility can change the activity returned by GitHub; compare visibility
before treating different snapshots as a calculation defect.

## Preserving the existing design

For a data-only refresh, compare the README before and after with image
`?v=` values ignored. Its section order, links, widths, heights, alternative
text, and surrounding markup should remain unchanged.

Check the curve's 900-by-280 canvas and the heatmap's 900-by-180 canvas. Confirm
that palette and typography definitions did not change. Updated coordinates,
counts, dates, and cache hashes are expected. Source checks verify these
contracts; a rendered visual check is a separate check and should be reported
only when performed.

## Inspecting a published snapshot

From the repository root, print the last recorded date and streak metrics:

```sh
python -c "import json; from pathlib import Path; d=json.loads(Path('assets/activity-data.json').read_text(encoding='utf-8')); print(d['updated_at']); print(d['days'][-1]); print(d['streak'])"
```

Confirm that the final date matches the intended UTC contribution day and that
the snapshot was refreshed after the relevant commits became visible. To
verify an image version, compute the corresponding SVG's SHA-256 and compare
its first 12 hexadecimal characters with the README URL.

Run the offline regressions with `python -m unittest discover -s tests`.
These checks cover boundary dates, API handling, counters, cache versions, and
generation output; they do not verify live indexing or external image delivery.

## Offline audit before publication

Run `python scripts/verify_profile.py` from the repository root to check the
saved snapshot, SVG cards, and local README image hashes together. The command
reads files without changing them and makes no network requests. It checks UTC
dates, count types, streak consistency, SVG dimensions and contents, and cache
versions. Each failed check prints a diagnostic and produces exit status 1.

Use `--root PATH` to inspect another checkout or `--json` for a machine-readable
result. Run against a complete set of assets from the same refresh. Local image
hashes depend on exact bytes, so converting line endings can invalidate them.

The refresh workflow runs this audit after card generation and before commit
publication. The audit confirms file consistency; live GitHub indexing and
external streak-image delivery must still be verified separately. If an audit
fails, inspect its named check, correct the source, regenerate, and rerun it.
Do not repair a failure by editing contribution counts or disabling the check.
