"""Compatibility facade; all shared implementations live in games/shared/."""
from games.shared.betting import (
    MIN_BET, _no_money_modal, _adjust_bet_amount,
    check_user_coins_or_pop_bank, render_betting_ui,
)
from games.shared.loading import similarity_analysis_loading
from games.shared.news_flow import (
    get_game_news_selection, _get_news_candidates, _open_chosen_article,
)
