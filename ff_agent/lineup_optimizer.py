from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


INJURY_BAD_STATUSES = {"Out", "Doubtful", "IR", "Suspended", "PUP"}


@dataclass
class PlayerChoice:
    player_id: str
    position: str
    score: float
    reason: str


def build_projection_lookup(projections: Optional[List[Dict[str, Any]]]) -> Dict[str, float]:
    if not projections:
        return {}
    result: Dict[str, float] = {}
    for row in projections:
        # Sleeper projections commonly carry: player_id and pts_half_ppr / pts_ppr
        pid = str(row.get("player_id"))
        pts = None
        for key in ("pts_ppr", "pts_half_ppr", "pts_std"):
            if isinstance(row.get(key), (int, float)):
                pts = float(row[key])
                break
        if pid and pts is not None:
            result[pid] = pts
    return result


def is_injured(player: Dict[str, Any]) -> bool:
    status = player.get("injury_status") or player.get("status")
    if not status:
        return False
    return str(status) in INJURY_BAD_STATUSES


def optimize_lineup(
    roster_player_ids: List[str],
    roster_positions: List[str],  # e.g., ["QB","RB","RB","WR","WR","TE","FLEX","K","DEF"]
    players_index: Dict[str, Dict[str, Any]],
    projections: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, str], List[PlayerChoice]]:
    """
    Returns: (starters_map, bench_choices)
    - starters_map: slot_index -> player_id chosen for that slot index
    - bench_choices: sorted list of candidates with scores and reasons
    """
    proj_lookup = build_projection_lookup(projections)

    # Build candidates by primary position
    position_to_candidates: Dict[str, List[PlayerChoice]] = {}
    flex_positions = {"RB", "WR", "TE"}

    for pid in roster_player_ids:
        pdata = players_index.get(pid) or {}
        pos_list = pdata.get("fantasy_positions") or ([pdata.get("position")] if pdata.get("position") else [])
        if not pos_list:
            continue
        primary = pos_list[0]
        if primary == "DEF":
            primary = "DEF"
        # Scoring
        if pid in proj_lookup:
            score = proj_lookup[pid]
            reason = "projection"
        else:
            # Heuristic score: start with baseline per position, penalize injuries and depth
            score = 0.0
            reason = "heuristic"
            if is_injured(pdata):
                score -= 100.0
                reason = "injury"
            # Prefer starters on depth chart
            depth_order = pdata.get("depth_chart_order")
            if isinstance(depth_order, int):
                score += max(0.0, 10.0 - float(depth_order))
            # Slight bump for likely starters
            if pdata.get("depth_chart_position") == 1:
                score += 2.0
        pc = PlayerChoice(player_id=pid, position=primary, score=float(score), reason=reason)
        position_to_candidates.setdefault(primary, []).append(pc)
        # Add to FLEX bucket if eligible
        if primary in flex_positions:
            position_to_candidates.setdefault("FLEX", []).append(pc)

    # Sort candidates per position by score desc
    for plist in position_to_candidates.values():
        plist.sort(key=lambda x: x.score, reverse=True)

    # Allocate starters to each roster position sequentially
    taken: set[str] = set()
    starters: Dict[str, str] = {}

    for idx, slot in enumerate(roster_positions):
        pool = position_to_candidates.get(slot, [])
        if slot == "FLEX":
            pool = position_to_candidates.get("FLEX", [])
        choice = None
        for pc in pool:
            if pc.player_id not in taken:
                choice = pc
                break
        if choice is not None:
            starters[str(idx)] = choice.player_id
            taken.add(choice.player_id)
        else:
            starters[str(idx)] = ""

    # Bench = all not taken
    bench_choices: List[PlayerChoice] = []
    for plist in position_to_candidates.values():
        for pc in plist:
            if pc.player_id not in taken and pc not in bench_choices:
                bench_choices.append(pc)
    bench_choices.sort(key=lambda x: x.score, reverse=True)

    return starters, bench_choices