from __future__ import annotations

from typing import Any, Dict, List, Tuple


def compute_roster_needs(
    roster_positions: List[str],
    current_players: List[str],
    players_index: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    needed: Dict[str, int] = {}
    counts: Dict[str, int] = {}

    # Count how many starters slots per position (FLEX is handled separately)
    for pos in roster_positions:
        if pos == "FLEX":
            continue
        needed[pos] = needed.get(pos, 0) + 1

    # Count how many roster players per position
    for pid in current_players:
        pdata = players_index.get(pid) or {}
        pos_list = pdata.get("fantasy_positions") or ([pdata.get("position")] if pdata.get("position") else [])
        if not pos_list:
            continue
        primary = pos_list[0]
        counts[primary] = counts.get(primary, 0) + 1

    # Need = starters minus on-roster; negative means surplus
    for pos, num_slots in list(needed.items()):
        have = counts.get(pos, 0)
        needed[pos] = num_slots - have

    return needed


def suggest_trending_adds(
    trending: List[Dict[str, Any]],
    players_index: Dict[str, Dict[str, Any]],
    roster_needs: Dict[str, int],
    max_per_position: int = 5,
) -> List[Tuple[str, str, int]]:
    """
    Returns list of (player_id, position, count) tuples filtered by roster needs.
    """
    suggestions: List[Tuple[str, str, int]] = []
    per_pos_count: Dict[str, int] = {}

    for row in trending:
        pid = str(row.get("player_id"))
        count = int(row.get("count", 0))
        pdata = players_index.get(pid) or {}
        pos_list = pdata.get("fantasy_positions") or ([pdata.get("position")] if pdata.get("position") else [])
        primary = pos_list[0] if pos_list else None
        if not primary:
            continue
        need = roster_needs.get(primary, 0)
        if need <= 0:
            continue
        if per_pos_count.get(primary, 0) >= max_per_position:
            continue
        suggestions.append((pid, primary, count))
        per_pos_count[primary] = per_pos_count.get(primary, 0) + 1

    return suggestions