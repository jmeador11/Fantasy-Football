# Fantasy-Football Agent

A Python agent that connects to Sleeper's public API to help manage your fantasy football team. It can:

- Fetch your leagues and rosters
- Generate weekly lineup recommendations (uses Sleeper projections when available; otherwise health- and role-based heuristics)
- Suggest waiver targets using trending players
- Produce a weekly report and optional Slack notifications

## Quick start

1) Requirements: Python 3.13+ (no external packages needed)

2) Configure:

Create `~/.ff_agent/config.json` with:

```
{
  "username": "your_sleeper_username_or_user_id",
  "season": 2025,
  "league_id": "your_league_id",
  "slack_webhook_url": null
}
```

Alternatively, run:

```
python -m ff_agent.cli init --username your_user --season 2025 --league-id YOUR_LEAGUE_ID
```

3) CLI usage:

```
python -m ff_agent.cli list-leagues --username your_user --season 2025
python -m ff_agent.cli recommend-lineup --league-id YOUR_LEAGUE_ID --week auto
python -m ff_agent.cli waivers --league-id YOUR_LEAGUE_ID --hours 48 --limit 50
python -m ff_agent.cli weekly-report --league-id YOUR_LEAGUE_ID --week auto
```

## Notes

- Sleeper's public API is read-only. The agent recommends lineup changes and waivers; it cannot perform transactions.
- Projections are fetched from Sleeper if their endpoint is available. If not, the agent falls back to health/status and positional depth heuristics.
