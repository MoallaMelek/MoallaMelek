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
