from __future__ import annotations

import argparse
from typing import Optional

from .config import AgentConfig, load_config, save_config
from .sleeper_client import SleeperClient
from .lineup_optimizer import optimize_lineup
from .waiver_agent import compute_roster_needs, suggest_trending_adds
from .notifier import notify_console, notify_slack


def resolve_value(cli_value, cfg_value, name: str):
    if cli_value is not None:
        return cli_value
    if cfg_value is not None:
        return cfg_value
    raise SystemExit(f"Missing required value for {name}. Provide via flag or config file.")


def cmd_list_leagues(args):
    cfg = load_config()
    username = resolve_value(args.username, cfg.username, "username")
    season = resolve_value(args.season, cfg.season, "season")

    client = SleeperClient()
    user = client.get_user(username)
    leagues = client.get_user_leagues(user["user_id"], season)
    for lg in leagues:
        print(f"{lg['league_id']}  {lg['name']}  status={lg['status']}  rosters={lg['total_rosters']}")


def cmd_init(args):
    cfg = AgentConfig(
        username=args.username,
        season=args.season,
        league_id=args.league_id,
        slack_webhook_url=args.slack_webhook_url,
    )
    save_config(cfg)
    print("Saved configuration to ~/.ff_agent/config.json")


def cmd_recommend_lineup(args):
    cfg = load_config()
    username = resolve_value(args.username, cfg.username, "username")
    season = resolve_value(args.season, cfg.season, "season")
    league_id = resolve_value(args.league_id, cfg.league_id, "league_id")

    client = SleeperClient()
    user = client.get_user(username)
    state = client.get_state("nfl")
    if args.week == "auto":
        week_num = int(state.get("week") or state.get("leg") or 1)
    else:
        week_num = int(args.week)

    league = client.get_league(league_id)
    roster_positions = league.get("roster_positions", [])

    rosters = client.get_rosters(league_id)
    user_id = user["user_id"]

    my_roster = next((r for r in rosters if r.get("owner_id") == user_id), None)
    if not my_roster:
        raise SystemExit(2)

    players_index = client.get_all_players("nfl")

    projections = client.get_projections(season=season, week=week_num)

    starters_map, bench_choices = optimize_lineup(
        roster_player_ids=[str(pid) for pid in (my_roster.get("players") or [])],
        roster_positions=roster_positions,
        players_index=players_index,
        projections=projections,
    )

    def fmt_player(pid: str) -> str:
        pdata = players_index.get(str(pid), {})
        name = f"{pdata.get('first_name','')} {pdata.get('last_name','')}".strip() or pid
        pos = (pdata.get("fantasy_positions") or [pdata.get("position") or "-"])[0]
        team = pdata.get("team") or "-"
        return f"{name} ({pos} {team})"

    starter_lines = []
    for idx, pid in starters_map.items():
        if not pid:
            starter_lines.append(f"Slot {idx}: [empty]")
        else:
            starter_lines.append(f"Slot {idx}: {fmt_player(pid)}")

    bench_lines = [f"{fmt_player(pc.player_id)}  score={pc.score:.2f}  reason={pc.reason}" for pc in bench_choices[:15]]

    title = f"Lineup recommendation - Week {week_num}"
    notify_console(title, starter_lines + ["", "Bench candidates:"] + bench_lines)
    notify_slack(cfg.slack_webhook_url, title, starter_lines)


def cmd_waivers(args):
    cfg = load_config()
    username = resolve_value(args.username, cfg.username, "username")
    season = resolve_value(args.season, cfg.season, "season")
    league_id = resolve_value(args.league_id, cfg.league_id, "league_id")

    client = SleeperClient()
    user = client.get_user(username)
    league = client.get_league(league_id)
    roster_positions = league.get("roster_positions", [])
    rosters = client.get_rosters(league_id)
    my_roster = next((r for r in rosters if r.get("owner_id") == user["user_id"]), None)
    if not my_roster:
        raise SystemExit(2)

    players_index = client.get_all_players("nfl")

    needs = compute_roster_needs(
        roster_positions=roster_positions,
        current_players=[str(pid) for pid in (my_roster.get("players") or [])],
        players_index=players_index,
    )

    trending = client.get_trending_players("nfl", trend_type="add", hours=args.hours, limit=args.limit)
    suggestions = suggest_trending_adds(trending, players_index, needs)

    def fmt(pid: str) -> str:
        pdata = players_index.get(str(pid), {})
        name = f"{pdata.get('first_name','')} {pdata.get('last_name','')}".strip() or pid
        pos = (pdata.get("fantasy_positions") or [pdata.get("position") or "-"])[0]
        team = pdata.get("team") or "-"
        return f"{name} ({pos} {team})"

    lines = [f"{fmt(pid)}  adds={count}" for pid, pos, count in suggestions]
    title = "Waiver suggestions (trending adds filtered by needs)"
    notify_console(title, lines)
    notify_slack(cfg.slack_webhook_url, title, lines)


def cmd_weekly_report(args):
    cfg = load_config()
    username = resolve_value(args.username, cfg.username, "username")
    season = resolve_value(args.season, cfg.season, "season")
    league_id = resolve_value(args.league_id, cfg.league_id, "league_id")

    client = SleeperClient()
    user = client.get_user(username)
    state = client.get_state("nfl")
    if args.week == "auto":
        week_num = int(state.get("week") or state.get("leg") or 1)
    else:
        week_num = int(args.week)

    league = client.get_league(league_id)
    rosters = client.get_rosters(league_id)

    players_index = client.get_all_players("nfl")

    my_roster = next((r for r in rosters if r.get("owner_id") == user["user_id"]), None)
    if not my_roster:
        raise SystemExit(2)

    projections = client.get_projections(season=season, week=week_num)

    starters_map, bench_choices = optimize_lineup(
        roster_player_ids=[str(pid) for pid in (my_roster.get("players") or [])],
        roster_positions=league.get("roster_positions", []),
        players_index=players_index,
        projections=projections,
    )

    trending = client.get_trending_players("nfl", trend_type="add", hours=48, limit=50)
    needs = compute_roster_needs(
        roster_positions=league.get("roster_positions", []),
        current_players=[str(pid) for pid in (my_roster.get("players") or [])],
        players_index=players_index,
    )
    waiver_suggestions = suggest_trending_adds(trending, players_index, needs)

    def fmt(pid: str) -> str:
        pdata = players_index.get(str(pid), {})
        name = f"{pdata.get('first_name','')} {pdata.get('last_name','')}".strip() or pid
        pos = (pdata.get("fantasy_positions") or [pdata.get("position") or "-"])[0]
        team = pdata.get("team") or "-"
        return f"{name} ({pos} {team})"

    starter_lines = [f"Slot {idx}: {fmt(pid) if pid else '[empty]'}" for idx, pid in starters_map.items()]
    waiver_lines = [f"{fmt(pid)} adds={cnt}" for pid, pos, cnt in waiver_suggestions[:10]]

    lines = [
        f"League: {league.get('name')}  Week: {week_num}",
        "",
        "Starters:",
        *starter_lines,
        "",
        "Top Waiver Suggestions:",
        *waiver_lines,
    ]

    title = "Weekly Report"
    notify_console(title, lines)
    notify_slack(cfg.slack_webhook_url, title, lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ff-agent", description="Fantasy Football agent (Sleeper)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list-leagues")
    p.add_argument("--username")
    p.add_argument("--season", type=int)
    p.set_defaults(func=cmd_list_leagues)

    p = sub.add_parser("init")
    p.add_argument("--username")
    p.add_argument("--season", type=int)
    p.add_argument("--league-id")
    p.add_argument("--slack-webhook-url")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("recommend-lineup")
    p.add_argument("--league-id")
    p.add_argument("--username")
    p.add_argument("--season", type=int)
    p.add_argument("--week", default="auto")
    p.set_defaults(func=cmd_recommend_lineup)

    p = sub.add_parser("waivers")
    p.add_argument("--league-id")
    p.add_argument("--username")
    p.add_argument("--season", type=int)
    p.add_argument("--hours", type=int, default=24)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_waivers)

    p = sub.add_parser("weekly-report")
    p.add_argument("--league-id")
    p.add_argument("--username")
    p.add_argument("--season", type=int)
    p.add_argument("--week", default="auto")
    p.set_defaults(func=cmd_weekly_report)

    return parser


def main(argv: Optional[list[str]] = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()