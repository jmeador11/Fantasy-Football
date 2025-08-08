from ff_agent.lineup_optimizer import optimize_lineup


def test_optimize_lineup_picks_healthy_bench_over_injured_starter():
    players_index = {
        "1": {"first_name": "A", "last_name": "QB1", "position": "QB", "fantasy_positions": ["QB"], "injury_status": "Out"},
        "2": {"first_name": "B", "last_name": "QB2", "position": "QB", "fantasy_positions": ["QB"], "injury_status": None},
    }
    roster_player_ids = ["1", "2"]
    roster_positions = ["QB"]

    starters, bench = optimize_lineup(roster_player_ids, roster_positions, players_index, projections=None)

    assert starters["0"] == "2"  # healthy QB2 should be chosen