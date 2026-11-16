"""Badge catalog and gateway adapter. No UI, images, CSS or direct Sheets writes.

Badge/title share a single equipment ID. `0` means unequipped. The Apps Script
engine is the authority; Python never grants awards from browser-supplied IDs.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
import logging
from pathlib import Path
import re
from typing import Mapping

BADGE_VERSION = 1
LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _catalog() -> dict:
    return json.loads(Path(__file__).with_name('badge_catalog.json').read_text(encoding='utf-8'))


def get_catalog() -> dict:
    """Return a copy; future icon assets use each entry's stable icon_key."""
    return deepcopy(_catalog())


def build_evidence(game: str, is_win: bool, state: Mapping,
                   supplied: Mapping | None = None) -> dict:
    """Translate committed server-side selections; 1 digit unit is 0.01%p."""
    if type(is_win) is not bool:
        raise ValueError('is_win must be boolean')
    if game == 'game_1':
        evidence = dict(supplied or {})
        if set(evidence) != {'predicted_digits', 'answer_digits'}:
            raise ValueError('Game 1 needs both predicted and actual digits')
        a, b = evidence['predicted_digits'], evidence['answer_digits']
        if any(type(v) is not int or not 0 <= v <= 99 for v in (a, b)) or is_win != (a == b):
            raise ValueError('Game 1 digits do not match the settled outcome')
        return {'predicted_digits': a, 'answer_digits': b}
    if game in ('game_2', 'game_3'):
        if supplied is not None:
            evidence = dict(supplied)
        elif game == 'game_2':
            evidence = {'choice': state.get('game_2_user_choice')}
        else:
            evidence = {'choice': {'홀': 'ODD', '짝': 'EVEN'}.get(state.get('game_3_choice'))}
        allowed = ('HIGH', 'LOW') if game == 'game_2' else ('ODD', 'EVEN')
        if set(evidence) != {'choice'} or evidence['choice'] not in allowed:
            raise ValueError('A confirmed game choice is required')
        return evidence
    if game not in ('game_4', 'game_5') or supplied not in (None, {}):
        raise ValueError('Unknown game or unexpected badge evidence')
    return {}


def remember_capabilities(result: Mapping, student_id: str) -> None:
    import streamlit as st
    from modules.transactions import TransactionError

    enabled = result.get('badges_enabled', False)
    if type(enabled) is not bool or (enabled and result.get('badge_version') != BADGE_VERSION):
        raise TransactionError('배지 서버 버전을 확인해야 합니다.', code='BADGES_NOT_READY')
    st.session_state['_badge_gateway'] = {'student_id': student_id, 'enabled': enabled}


def collection_enabled(student_id: str) -> bool:
    import streamlit as st

    mode = st.session_state.get('_badge_gateway') or {}
    return mode.get('student_id') == student_id and mode.get('enabled') is True


def settlement_fields(game: str, is_win: bool, student_id: str,
                      evidence: Mapping | None) -> dict:
    import streamlit as st
    from modules.transactions import TransactionError

    if not collection_enabled(student_id):
        return {}
    try:
        facts = build_evidence(game, is_win, st.session_state, evidence)
    except (ValueError, TypeError) as exc:
        raise TransactionError('배지 판정에 필요한 게임 기록이 올바르지 않습니다.',
                               code='BADGE_EVIDENCE_REQUIRED') from exc
    return {'badge_version': BADGE_VERSION, 'badge_evidence': facts}


def absorb_profile(result: Mapping, student_id: str) -> dict | None:
    """Never turn a successful wallet settlement into a cosmetic-data failure."""
    import streamlit as st

    profile = result.get('badge_profile')
    if profile is None:
        return None
    known = {b['id'] for b in _catalog()['badges']}
    if (not isinstance(profile, dict) or profile.get('student_id') != student_id
            or profile.get('schema_version') != BADGE_VERSION
            or type(profile.get('revision')) is not int or profile['revision'] < 0
            or not isinstance(profile.get('unlocked'), dict)
            or not set(profile['unlocked']).issubset(known)
            or not isinstance(profile.get('progress'), dict)
            or not isinstance(profile.get('equipped'), str)
            or (profile.get('equipped') != '0' and profile.get('equipped') not in profile['unlocked'])):
        LOGGER.warning('Ignored an invalid badge profile response')
        return None
    st.session_state['badge_profile'] = deepcopy(profile)
    return deepcopy(profile)


def fetch_badge_profile() -> dict:
    from modules.transactions import _request, _student_id, transaction_id, TransactionError

    sid = _student_id()
    result = _request({'transaction_id': transaction_id('badge_profile'),
                       'kind': 'badge_profile', 'student_id': sid, 'badge_version': BADGE_VERSION})
    profile = absorb_profile(result, sid)
    if profile is None:
        raise TransactionError('배지 프로필을 확인할 수 없습니다.', code='BADGE_DATA_INVALID')
    return profile


def equip_badge(badge_id: str | int, *, expected_revision: int, request_id: str) -> dict:
    """Reuse request_id on timeout. Refresh first on STALE_BADGE_PROFILE.

    Only the logged-in account can be changed. No function accepts an arbitrary
    target account, an owned-ID list, a rarity, or an unlock command from the UI.
    """
    from modules.transactions import _request, _student_id, TransactionError

    if type(badge_id) is int and badge_id == 0:
        badge_id = '0'
    known = {b['id'] for b in _catalog()['badges']}
    if (not isinstance(badge_id, str) or (badge_id != '0' and badge_id not in known)
            or type(expected_revision) is not int or expected_revision < 0
            or not isinstance(request_id, str) or not re.fullmatch(r'badge_equip:[a-f0-9]{32}', request_id)):
        raise ValueError('Invalid equipment request')
    sid = _student_id()
    result = _request({'transaction_id': request_id, 'kind': 'badge_equip',
                       'student_id': sid, 'badge_version': BADGE_VERSION,
                       'badge_id': badge_id, 'expected_revision': expected_revision})
    profile = absorb_profile(result, sid)
    if profile is None:
        raise TransactionError('장착 결과를 확인할 수 없습니다. 같은 요청 번호로 재시도해야 합니다.',
                               code='BADGE_DATA_INVALID')
    return profile


def get_badge_progress(profile: Mapping) -> list[dict]:
    """Popup-ready descriptions; an earned badge stays complete after a loss."""
    state = profile['progress']
    owned = profile['unlocked']
    result = []
    for badge in _catalog()['badges']:
        conditions = []
        for condition in badge['conditions']:
            metric = condition['metric']
            if metric == 'played_games':
                current = sum(g['played'] > 0 for g in state['games'].values())
            elif metric in ('streak_game_count_5', 'streak_game_count_8'):
                current = len(set(state['streak_games'][-int(metric.rsplit('_', 1)[1]):]))
            else:
                current = state
                for key in metric.split('.'):
                    current = current[key]
            conditions.append({**condition, 'current': condition['target'] if badge['id'] in owned
                               else min(current, condition['target'])})
        result.append({**deepcopy(badge), 'unlocked': badge['id'] in owned,
                       'equipped': badge['id'] == profile['equipped'],
                       'earned': deepcopy(owned.get(badge['id'])), 'progress': conditions})
    return result
