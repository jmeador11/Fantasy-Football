from __future__ import annotations

from typing import Any, Dict, List, Tuple


def team_position_counts(roster_player_ids: List[str], players_index: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for pid in roster_player_ids:
        pdata = players_index.get(pid) or {}
        pos_list = pdata.get("fantasy_positions") or ([pdata.get("position")] if pdata.get("position") else [])
        if not pos_list:
            continue
        primary = pos_list[0]
        counts[primary] = counts.get(primary, 0) + 1
    return counts


def suggest_trade_targets(
    my_needs: Dict[str, int],
    all_team_rosters: Dict[int, List[str]],  # roster_id -> player_ids
    my_roster_id: int,
    players_index: Dict[str, Dict[str, Any]],
    top_n_per_position: int = 3,
) -> Dict[str, List[Tuple[str, int]]]:
    """
    Returns position -> [(player_id, other_roster_id)] potential targets from teams with surpluses.
    """
    suggestions: Dict[str, List[Tuple[str, int]]] = {}

    for other_roster_id, pids in all_team_rosters.items():
        if other_roster_id == my_roster_id:
            continue
        counts = team_position_counts(pids, players_index)
        for pos, need in my_needs.items():
            if need <= 0:
                continue
            surplus = counts.get(pos, 0)
            if surplus <= 1:  # leave them at least one buffer
                continue
            # Pick top players by a simple heuristic: presence of projection-like fields or depth chart
            ranked = sorted(
                pids,
                key=lambda pid: (
                    players_index.get(pid, {}).get("depth_chart_position") == 1,
                    -(players_index.get(pid, {}).get("depth_chart_order") or 99),
                ),
                reverse=True,
            )
            picks = [(pid, other_roster_id) for pid in ranked[:top_n_per_position]]
            if picks:
                suggestions.setdefault(pos, []).extend(picks)

    return suggestions