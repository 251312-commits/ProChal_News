"""Badge client contracts. Isolated dependencies: no Streamlit server or network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch

from modules import badge_service as badges

ROOT = Path(__file__).resolve().parents[1]


def empty_profile(sid='10101'):
    return {'student_id': sid, 'schema_version': 1, 'equipped': '0', 'unlocked': {},
            'revision': 0, 'updated_at': '', 'progress': {
                'total': 0, 'streak': 0, 'best_streak': 0, 'streak_games': [], 'epoch': '',
                'high_wins': 0, 'low_wins': 0, 'odd_wins': 0, 'even_wins': 0,
                'near_10': 0, 'near_3': 0, 'exact_10': 0, 'exact_1': 0,
                'games': {f'game_{i}': {'played': 0, 'wins': 0, 'streak': 0, 'best_streak': 0}
                          for i in range(1, 6)}}}


class BadgeCatalogTests(unittest.TestCase):
    def test_generated_catalog_is_current(self):
        subprocess.run([sys.executable, str(ROOT / 'scripts/sync_badge_catalog.py'), '--check'], check=True)

    def test_twenty_stable_ids_and_independent_copies(self):
        c = badges.get_catalog()
        self.assertEqual(len(c['badges']), 20)
        self.assertEqual(len({b['id'] for b in c['badges']}), 20)
        self.assertEqual([b['number'] for b in c['badges']], list(range(1, 21)))
        c['badges'][0]['name'] = 'changed'
        self.assertEqual(badges.get_catalog()['badges'][0]['name'], '신입 에이전트')

    def test_main_public_catalog_uses_the_same_immutable_ids_and_effects(self):
        from modules.badges import BADGES
        catalog = badges.get_catalog()['badges']
        self.assertEqual([b.id for b in BADGES], [b['id'] for b in catalog])
        self.assertEqual([b.title for b in BADGES], [b['name'] for b in catalog])
        self.assertEqual([b.effect for b in BADGES], [
            '' if b['effect']['animation'] == 'none' else b['effect']['animation'] for b in catalog])

    def test_game_one_integer_evidence_and_outcome_consistency(self):
        expected = {'predicted_digits': 0, 'answer_digits': 99}
        self.assertEqual(badges.build_evidence('game_1', False, {}, expected), expected)
        for supplied in [{}, {'predicted_digits': True, 'answer_digits': 1},
                         {'predicted_digits': 100, 'answer_digits': 1},
                         {'predicted_digits': 37, 'answer_digits': 37},
                         {'predicted_digits': '36', 'answer_digits': 37}]:
            with self.subTest(supplied=supplied), self.assertRaises(ValueError):
                badges.build_evidence('game_1', False, {}, supplied)

    def test_existing_game_two_and_three_selection_keys(self):
        self.assertEqual(badges.build_evidence('game_2', True, {'game_2_user_choice': 'LOW'}), {'choice': 'LOW'})
        self.assertEqual(badges.build_evidence('game_3', True, {'game_3_choice': '홀'}), {'choice': 'ODD'})
        self.assertEqual(badges.build_evidence('game_3', False, {'game_3_choice': '짝'}), {'choice': 'EVEN'})
        for game in ['game_2', 'game_3']:
            with self.assertRaises(ValueError): badges.build_evidence(game, True, {})

    def test_games_four_five_and_unknown_evidence(self):
        for game in ['game_4', 'game_5']:
            self.assertEqual(badges.build_evidence(game, True, {}), {})
            with self.assertRaises(ValueError): badges.build_evidence(game, True, {}, {'unlock': 'g1_hit'})
        with self.assertRaises(ValueError): badges.build_evidence('game_6', True, {})

    def test_progress_keeps_earned_streak_complete_after_loss(self):
        p = empty_profile()
        p['unlocked']['streak_three'] = {'earned_at': '2026-11-16T00:00:00Z', 'round_id': 'a' * 32}
        view = {b['id']: b for b in badges.get_badge_progress(p)}
        self.assertTrue(view['streak_three']['unlocked'])
        self.assertEqual(view['streak_three']['progress'][0]['current'], 3)
        self.assertEqual(view['streak_five_mixed']['progress'][0]['current'], 0)


class BadgeClientTests(unittest.TestCase):
    def setUp(self):
        self.st = types.ModuleType('streamlit')
        self.st.session_state = {'current_user': '10101', 'current_user_data': {'학번': '10101'},
                                 'game_4_round_id': 'a' * 32}
        self.st.secrets = {'transaction_endpoint': 'https://script.google.com/macros/s/test/exec',
                           'transaction_token': 'secret'}
        math = types.ModuleType('modules.account_math')
        math.account_amount = lambda v, strict=False: int(v)
        ids = types.ModuleType('modules.account_ids')
        ids.is_valid_student_id = lambda v: True
        ids.is_valid_teacher_id = lambda v: True
        nickname = types.ModuleType('modules.nickname'); nickname.normalize_nickname = lambda v: v
        spec = importlib.util.spec_from_file_location('modules.transactions', ROOT / 'modules/transactions.py')
        self.tx = importlib.util.module_from_spec(spec)
        self.patcher = patch.dict(sys.modules, {'streamlit': self.st, 'modules.transactions': self.tx,
            'modules.account_math': math, 'modules.account_ids': ids, 'modules.nickname': nickname})
        self.patcher.start(); self.addCleanup(self.patcher.stop); spec.loader.exec_module(self.tx)

    def status(self, enabled=True):
        return {'ok': True, 'gateway_version': 2, 'badge_version': 1, 'badges_enabled': enabled,
                'balances': {'coins': 5000, 'streak': 0, 'loan': 0, 'principal': 0}}

    def receipt(self, with_profile=True):
        return {'ok': True, 'balances': {'coins': 7000, 'streak': 1, 'loan': 0},
                'settlement': {'delta': 2000, 'coins': 7000, 'streak': 1, 'loan': 0},
                **({'badge_profile': empty_profile()} if with_profile else {})}

    def test_default_off_preserves_legacy_settle_request(self):
        with patch.object(self.tx, '_request', return_value=self.receipt(False)) as request:
            result = self.tx.settle_game_round('game_4', 1000, True)
        request.assert_called_once()
        self.assertNotIn('badge_version', request.call_args.args[0])
        self.assertEqual(result['reward'], 2000)

    def test_enabled_settlement_negotiates_before_commit_and_sends_evidence(self):
        badges.remember_capabilities(self.status(), '10101')
        with patch.object(self.tx, '_request', side_effect=[self.status(), self.receipt()]) as request:
            result = self.tx.settle_game_round('game_4', 1000, True)
        self.assertEqual([c.args[0]['kind'] for c in request.call_args_list], ['status', 'settle'])
        payload = request.call_args.args[0]
        self.assertEqual(payload['badge_version'], 1); self.assertEqual(payload['badge_evidence'], {})
        self.assertEqual(payload['transaction_id'], 'settle:' + 'a' * 32)
        self.assertEqual(result['new_coins'], 7000)
        self.assertEqual(self.st.session_state['badge_profile']['student_id'], '10101')

    def test_flag_switched_after_bet_retries_same_round_only_after_precommit_error(self):
        error = self.tx.TransactionError('toggle', code='BADGE_EVIDENCE_REQUIRED')
        with patch.object(self.tx, '_request', side_effect=[error, self.status(), self.receipt()]) as request:
            self.tx.settle_game_round('game_4', 1000, True)
        calls = [c.args[0] for c in request.call_args_list]
        self.assertEqual([c['kind'] for c in calls], ['settle', 'status', 'settle'])
        self.assertEqual(calls[0]['transaction_id'], calls[2]['transaction_id'])
        self.assertNotIn('badge_version', calls[0]); self.assertEqual(calls[2]['badge_version'], 1)

    def test_network_timeout_does_not_issue_a_new_settlement(self):
        error = self.tx.TransactionError('timeout', code='NETWORK_ERROR')
        with patch.object(self.tx, '_request', side_effect=error) as request:
            with self.assertRaises(self.tx.TransactionError): self.tx.settle_game_round('game_4', 1000, True)
        request.assert_called_once(); self.assertEqual(self.st.session_state['game_4_round_id'], 'a' * 32)

    def test_capabilities_do_not_leak_to_a_different_account(self):
        badges.remember_capabilities(self.status(), '10101')
        self.assertTrue(badges.collection_enabled('10101'))
        self.assertFalse(badges.collection_enabled('10102'))
        with self.assertRaises(self.tx.TransactionError):
            badges.remember_capabilities({**self.status(), 'badge_version': 99}, '10101')

    def test_malformed_cosmetic_response_cannot_fail_a_committed_wallet(self):
        result = self.receipt(); result['badge_profile']['equipped'] = []
        with patch.object(self.tx, '_request', return_value=result):
            actual = self.tx.settle_game_round('game_4', 1000, True)
        self.assertEqual(actual['new_coins'], 7000)
        self.assertNotIn('badge_profile', self.st.session_state)

    def test_profile_fetch_uses_logged_in_id(self):
        with patch.object(self.tx, '_request', return_value={'badge_profile': empty_profile()}) as request:
            self.assertEqual(badges.fetch_badge_profile()['student_id'], '10101')
        self.assertEqual(request.call_args.args[0]['student_id'], '10101')
        self.assertEqual(request.call_args.args[0]['kind'], 'badge_profile')

    def test_equipment_preserves_idempotency_key_and_zero(self):
        with patch.object(self.tx, '_request', return_value={'badge_profile': empty_profile()}) as request:
            badges.equip_badge(0, expected_revision=0, request_id='badge_equip:' + 'b' * 32)
        self.assertEqual(request.call_args.args[0]['badge_id'], '0')
        self.assertEqual(request.call_args.args[0]['expected_revision'], 0)
        self.assertEqual(request.call_args.args[0]['transaction_id'], 'badge_equip:' + 'b' * 32)
        with self.assertRaises(ValueError): badges.equip_badge('invented', expected_revision=0, request_id='bad')

    def test_game_one_evidence_is_explicit(self):
        self.st.session_state['game_1_round_id'] = 'c' * 32
        badges.remember_capabilities(self.status(), '10101')
        with patch.object(self.tx, '_request', side_effect=[self.status(), self.receipt()]) as request:
            self.tx.settle_game_round('game_1', 1000, False,
                badge_evidence={'predicted_digits': 36, 'answer_digits': 37})
        self.assertEqual(request.call_args.args[0]['badge_evidence'], {'predicted_digits': 36, 'answer_digits': 37})


class GameOneRetryTests(unittest.TestCase):
    def test_scored_evidence_is_frozen_before_lost_response_and_changes_for_new_round(self):
        import ast
        import asyncio
        from contextlib import nullcontext
        from unittest.mock import AsyncMock, MagicMock

        class Session(dict):
            __getattr__ = dict.__getitem__
            __setattr__ = dict.__setitem__

        class TxError(RuntimeError):
            pass

        class BalanceChanged(TxError):
            pass

        st = MagicMock()
        st.session_state = Session(current_user='10101', current_user_data={},
            game_1_bet=1000, game_1_round_id='a' * 32, game_1_predicted_digits=36)
        summary = AsyncMock(return_value='요약')
        similarity = Mock(side_effect=[{'score': 87.37, 'score_hundredths': 8737},
                                       {'score': 87.36, 'score_hundredths': 8736}])
        receipt = {'reward': -1000, 'new_coins': 4000, 'new_streak': 0}
        settle = Mock(side_effect=[TxError('lost response'), receipt, receipt])
        tree = ast.parse((ROOT / 'games/game1/game1.py').read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'show_game_1')
        ns = {'st': st, 'asyncio': asyncio, 'summary': summary, 'similarity_check': similarity,
              'get_game_news_selection': lambda *a, **k: ('제목', '본문', 'url'),
              'similarity_analysis_loading': nullcontext, 'settle_game_round': settle,
              'BalanceChanged': BalanceChanged, 'TransactionError': TxError,
              'apply_end_of_turn_interest': lambda *a: True, 'GAME_1_WIN_MULTIPLIER': 100}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'game1-function', 'exec'), ns)
        reveal = types.ModuleType('games.game1.result_reveal'); reveal.render_game1_result_reveal = Mock()
        with patch.dict(sys.modules, {'games.game1.result_reveal': reveal}):
            ns['show_game_1'](); self.assertNotIn('game_1_result', st.session_state)
            ns['show_game_1']()
            self.assertEqual(similarity.call_count, 1); self.assertEqual(summary.call_count, 1)
            self.assertEqual(settle.call_args_list[0].kwargs, settle.call_args_list[1].kwargs)
            self.assertEqual(settle.call_args.kwargs['badge_evidence']['answer_digits'], 37)
            del st.session_state['game_1_result']; st.session_state['game_1_round_id'] = 'b' * 32
            ns['show_game_1']()
            self.assertEqual(similarity.call_count, 2)
            self.assertEqual(settle.call_args.kwargs['badge_evidence']['answer_digits'], 36)


if __name__ == '__main__':
    unittest.main()
