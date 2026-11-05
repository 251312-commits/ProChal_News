"""Select six stable slots underneath the top-three ranking podium."""


def select_ranking_rows(total_users, my_rank):
    """Return six slots: ranks, a gap marker, and optional empty placeholders.

    Ranks 4 and 5 stay visible. Near the top, show ranks 4-9. Further down,
    reserve one slot for the gap and three for the current user's neighbors;
    shift the last three ranks upward when the user is last or second-last.
    """
    if total_users >= 10 and 8 <= my_rank <= total_users:
        nearby_start = min(my_rank - 1, total_users - 2)
        return [4, 5, "...", nearby_start, nearby_start + 1, nearby_start + 2]

    ranks = list(range(4, min(total_users, 9) + 1))
    return ranks + [None] * (6 - len(ranks))
