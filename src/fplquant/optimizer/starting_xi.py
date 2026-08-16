from fplquant.optimizer.types import (
    DEFENDER,
    FORWARD,
    GOALKEEPER,
    MIDFIELDER,
    InfeasibleSquadError,
    PlayerCandidate,
    StartingXI,
)

# (DEF, MID, FWD) — GKP is always exactly 1 and isn't listed. All 8 formations
# legal under FPL's rules: 1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD, 11 total.
VALID_FORMATIONS: list[tuple[int, int, int]] = [
    (3, 4, 3),
    (3, 5, 2),
    (4, 3, 3),
    (4, 4, 2),
    (4, 5, 1),
    (5, 2, 3),
    (5, 3, 2),
    (5, 4, 1),
]


def select_starting_xi(
    squad: list[PlayerCandidate], forced_formation: tuple[int, int, int] | None = None
) -> StartingXI:
    """Pick the best valid starting XI from a 15-man squad.

    For each of FPL's 8 legal formations, the best XI is just the top N
    players by predicted_points at each position — points are additive
    across positions with no cross-position synergy in this model, so
    picking greedily per position and comparing the (small, fixed) set of
    formation totals is provably optimal, no ILP needed. Captain and
    vice-captain are the top two starters by predicted_points.

    If `forced_formation` is given, only that formation is considered
    (instead of searching for the highest-scoring one).
    """
    by_position: dict[int, list[PlayerCandidate]] = {
        GOALKEEPER: [],
        DEFENDER: [],
        MIDFIELDER: [],
        FORWARD: [],
    }
    for player in squad:
        by_position[player.element_type].append(player)
    for players in by_position.values():
        players.sort(key=lambda p: p.predicted_points, reverse=True)

    if not by_position[GOALKEEPER]:
        raise InfeasibleSquadError("Squad has no goalkeeper, can't pick a starting XI")

    formations_to_try = [forced_formation] if forced_formation is not None else VALID_FORMATIONS

    best_formation: tuple[int, int, int] | None = None
    best_starters: list[PlayerCandidate] = []
    best_total = float("-inf")

    for def_count, mid_count, fwd_count in formations_to_try:
        if (
            len(by_position[DEFENDER]) < def_count
            or len(by_position[MIDFIELDER]) < mid_count
            or len(by_position[FORWARD]) < fwd_count
        ):
            continue
        starters = (
            by_position[GOALKEEPER][:1]
            + by_position[DEFENDER][:def_count]
            + by_position[MIDFIELDER][:mid_count]
            + by_position[FORWARD][:fwd_count]
        )
        total = sum(p.predicted_points for p in starters)
        if total > best_total:
            best_total = total
            best_formation = (def_count, mid_count, fwd_count)
            best_starters = starters

    if best_formation is None:
        if forced_formation is not None:
            d, m, f = forced_formation
            raise InfeasibleSquadError(f"Squad can't fill the {d}-{m}-{f} formation")
        raise InfeasibleSquadError("No valid formation fits this squad")

    starter_ids = {p.player_id for p in best_starters}
    bench = [p for p in squad if p.player_id not in starter_ids]
    bench_gkp = [p for p in bench if p.element_type == GOALKEEPER]
    bench_outfield = sorted(
        (p for p in bench if p.element_type != GOALKEEPER),
        key=lambda p: p.predicted_points,
        reverse=True,
    )
    bench = bench_gkp + bench_outfield

    ranked_starters = sorted(best_starters, key=lambda p: p.predicted_points, reverse=True)
    captain, vice_captain = ranked_starters[0], ranked_starters[1]

    return StartingXI(
        formation=f"{best_formation[0]}-{best_formation[1]}-{best_formation[2]}",
        starters=best_starters,
        bench=bench,
        captain=captain,
        vice_captain=vice_captain,
        starting_predicted_points=best_total,
        bench_boost_value=sum(p.predicted_points for p in bench),
        triple_captain_value=captain.predicted_points,
    )
