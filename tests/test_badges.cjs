'use strict';
// Actual Apps Script code against an in-memory, atomic Sheets API. No network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const ROOT = path.resolve(__dirname, '..');
const plain = x => JSON.parse(JSON.stringify(x));
const hex = n => n.toString(16).padStart(32, '0');

function harness({install = true, enable = true} = {}) {
  const props = {SPREADSHEET_ID: 'test', TRANSACTION_TOKEN: 'secret'};
  const sheets = new Map();
  let nextSheet = 1, uuid = 0;
  const control = {locked: false, failCommit: false, commits: 0};
  const makeSheet = (name, rows = []) => {
    const s = {name, id: nextSheet++, rows: plain(rows), getSheetId() {return this.id;},
      getLastRow() {return this.rows.length;}, getMaxColumns() {return 26;},
      setFrozenRows() {},
      getRange(row, col, height = 1, width = 1) {
        return {
          getValues: () => Array.from({length: height}, (_, i) =>
            Array.from({length: width}, (_, j) => s.rows[row - 1 + i]?.[col - 1 + j] ?? '')),
          setValues: values => values.forEach((r, i) => {
            s.rows[row - 1 + i] ||= [];
            r.forEach((v, j) => {s.rows[row - 1 + i][col - 1 + j] = v;});
          })
        };
      }
    };
    sheets.set(name, s); return s;
  };
  const ss = {getId: () => 'test', getSheetByName: n => sheets.get(n) || null,
    insertSheet: n => {assert(!sheets.has(n)); return makeSheet(n);}};
  const propertyApi = {getProperty: k => props[k] ?? null,
    setProperty: (k, v) => {props[k] = v;}, setProperties: values => Object.assign(props, values)};
  const ctx = vm.createContext({console, Date, Math, Set, JSON,
    PropertiesService: {getScriptProperties: () => propertyApi},
    SpreadsheetApp: {openById: id => {assert.equal(id, 'test'); return ss;}},
    Utilities: {getUuid: () => 'epoch-' + ++uuid},
    LockService: {getScriptLock: () => ({tryLock() {
      if (control.locked) return false; control.locked = true; return true;
    }, releaseLock() {control.locked = false;}})},
    Sheets: {Spreadsheets: {batchUpdate({requests}, id) {
      assert.equal(id, 'test'); assert.equal(control.locked, true);
      if (control.failCommit) {control.failCommit = false; throw new Error('simulated atomic rejection');}
      const copies = new Map([...sheets.values()].map(s => [s.id, plain(s.rows)]));
      const value = cell => {
        const v = cell.userEnteredValue;
        return v.stringValue ?? v.numberValue ?? v.boolValue;
      };
      for (const request of requests) {
        if (request.appendCells) {
          const r = request.appendCells;
          copies.get(r.sheetId).push(...r.rows.map(row => row.values.map(value)));
        } else if (request.updateCells) {
          const r = request.updateCells, rows = copies.get(r.start.sheetId);
          r.rows.forEach((row, i) => {
            const index = r.start.rowIndex + i;
            rows[index] ||= [];
            row.values.forEach((v, j) => {rows[index][r.start.columnIndex + j] = value(v);});
          });
        } else throw new Error('Unexpected Sheets request');
      }
      for (const s of sheets.values()) s.rows = copies.get(s.id);
      control.commits++;
    }}}
  });
  ['Code.gs', 'BadgeCatalog.gs', 'Badges.gs'].forEach(file =>
    vm.runInContext(fs.readFileSync(path.join(ROOT, 'apps_script', file), 'utf8'), ctx, {filename: file}));
  const users = makeSheet('Users', [
    ['학번', '아이디', '코인', '연승', '추천인', '비밀번호', '대출금', '대출원금', '마지막기사URL', '기존추가열'],
    ['10101', 'Player', 5000000, 0, '', 'password', 0, 0, 'https://example.test/', 'untouched'],
    ['10102', 'Other', 5000000, 0, '', 'password', 0, 0, '', 'untouched']
  ]);
  const ledger = makeSheet('Transactions', [plain(vm.runInContext('HEADERS', ctx))]);
  if (install) ctx.installBadgeSystem();
  if (enable && install) ctx.enableBadgeCollection();
  let round = 0, command = 10000;
  const send = fields => plain(ctx.process_({token: 'secret', student_id: '10101', ...fields}));
  const evidence = (game, win) => game === 'game_1' ?
    {predicted_digits: 50, answer_digits: win ? 50 : 80} :
    game === 'game_2' ? {choice: 'HIGH'} : game === 'game_3' ? {choice: 'ODD'} : {};
  const makeRound = (game, win, facts = evidence(game, win), sid = '10101', tracked = true) => {
    const id = hex(++round);
    send({kind: 'bet', transaction_id: 'bet:' + id, round_id: id, game, bet: 1000, student_id: sid});
    const payload = {kind: 'settle', transaction_id: 'settle:' + id, round_id: id,
      game, bet: 1000, is_win: win, student_id: sid,
      ...(tracked ? {badge_version: 1, badge_evidence: facts} : {})};
    return payload;
  };
  const play = (game, win, facts, sid, tracked) => send(makeRound(game, win, facts, sid, tracked));
  const profile = (sid = '10101') => send({kind: 'badge_profile',
    transaction_id: 'badge_profile:' + hex(++command), badge_version: 1, student_id: sid}).badge_profile;
  const equip = (id, revision, n = ++command, sid = '10101') => send({kind: 'badge_equip',
    transaction_id: 'badge_equip:' + hex(n), badge_version: 1, student_id: sid,
    badge_id: id, expected_revision: revision});
  const snapshot = () => JSON.stringify([...sheets].map(([name, s]) => [name, s.rows]));
  return {ctx, props, ss, sheets, users, ledger, control, send, play, makeRound, profile, equip, snapshot};
}
function code(expected) {return error => error.code === expected;}
function owns(p, id) {return Object.hasOwn(p.unlocked, id);}

test('catalog contains exactly 20 linked icon-only badges and approved tiers/effects', () => {
  const c = JSON.parse(fs.readFileSync(path.join(ROOT, 'modules/badge_catalog.json')));
  assert.equal(c.badges.length, 20); assert.equal(new Set(c.badges.map(b => b.id)).size, 20);
  assert.equal(c.display_mode, 'icon_only'); assert.equal(c.title_linked, true); assert.equal(c.slots, 1);
  assert.deepEqual([...new Set(c.badges.map(b => b.rarity))].sort(), ['common', 'epic', 'legendary', 'rare']);
  for (const b of c.badges) {
    if (b.rarity !== 'legendary') assert.equal(b.effect.animation, 'none');
    else {assert.notEqual(b.effect.glow, 'none'); assert.equal(b.effect.reduced_motion, 'static_glow');}
  }
});

test('installer is idempotent and never modifies Users or the wallet ledger', () => {
  const h = harness({install: false, enable: false});
  const users = plain(h.users.rows), ledger = plain(h.ledger.rows);
  assert.equal(h.ctx.installBadgeSystem().created, true);
  h.play('game_4', true, {}, '10101', false);
  const before = h.snapshot();
  assert.equal(h.ctx.installBadgeSystem().created, false);
  assert.equal(h.snapshot(), before); assert.equal(h.sheets.get('BadgeProfiles').rows.length, 1);
  assert.deepEqual(h.users.rows[0], users[0]); assert.deepEqual(h.ledger.rows[0], ledger[0]);
});

test('conflicting badge headers are rejected without overwriting anything', () => {
  const h = harness({enable: false}); h.sheets.get('BadgeProfiles').rows[0][0] = 'occupied';
  const before = h.snapshot();
  assert.throws(() => h.ctx.installBadgeSystem(), code('BADGES_NOT_READY'));
  assert.equal(h.snapshot(), before);
});

test('default-off deployment needs no badge sheet and keeps legacy settlements working', () => {
  const h = harness({install: false, enable: false});
  h.play('game_1', true, undefined, undefined, false);
  assert.equal(h.users.rows[1][2], 5100000); assert.equal(h.sheets.has('BadgeProfiles'), false);
  assert.equal(h.props.BADGES_ENABLED, undefined);
});

test('read-only empty profile and bet confirmation never award badges', () => {
  const h = harness(); const before = h.snapshot();
  const p = h.profile(); assert.equal(p.equipped, '0'); assert.deepEqual(p.unlocked, {});
  assert.equal(p.progress.total, 0); assert.equal(h.snapshot(), before);
  h.makeRound('game_4', true); assert.equal(h.profile().progress.total, 0);
});

test('completed losses count; all five games and the 30-round threshold', () => {
  const h = harness();
  for (let g = 1; g <= 5; g++) h.play('game_' + g, false);
  let p = h.profile(); assert(owns(p, 'first_round')); assert(owns(p, 'all_games'));
  for (let i = 5; i < 29; i++) h.play('game_4', false);
  assert(!owns(h.profile(), 'thirty_rounds'));
  h.play('game_4', false); p = h.profile();
  assert(owns(p, 'thirty_rounds')); assert.equal(p.progress.total, 30); assert.equal(p.equipped, '0');
});

test('global mixed streak uses the last five/eight wins of an uninterrupted run', () => {
  const h = harness();
  for (let i = 0; i < 5; i++) h.play('game_2', true);
  assert(owns(h.profile(), 'streak_three')); assert(!owns(h.profile(), 'streak_five_mixed'));
  h.play('game_3', true); assert(owns(h.profile(), 'streak_five_mixed'));
  h.play('game_3', true); h.play('game_2', true);
  assert(!owns(h.profile(), 'streak_eight_mixed'));
  h.play('game_4', true); assert(owns(h.profile(), 'streak_eight_mixed'));
  h.play('game_5', false); const p = h.profile();
  assert.equal(p.progress.streak, 0); assert.deepEqual(p.progress.streak_games, []);
  assert(owns(p, 'streak_eight_mixed'));
});

test('game-specific streak ignores other games but resets on its own loss', () => {
  const h = harness();
  for (let i = 0; i < 5; i++) {h.play('game_3', true); h.play('game_4', false);}
  let p = h.profile(); assert(owns(p, 'g3_five_streak')); assert.equal(p.progress.streak, 0);
  assert.equal(p.progress.games.game_3.streak, 5);
  h.play('game_3', false); p = h.profile(); assert.equal(p.progress.games.game_3.streak, 0);
  assert(owns(p, 'g3_five_streak'));
});

for (const [guess, answer, expected] of [
  [36, 37, ['g1_within_ten', 'g1_within_three', 'g1_exact_one']],
  [38, 37, ['g1_within_ten', 'g1_within_three', 'g1_exact_one']],
  [27, 37, ['g1_within_ten', 'g1_exact_ten']],
  [34, 37, ['g1_within_ten', 'g1_within_three']],
  [33, 37, ['g1_within_ten']], [26, 37, []], [99, 0, []],
  [37, 37, ['g1_hit']]
]) test(`game 1 integer difference ${guess} -> ${answer}: exact, within, overlap, no wrap`, () => {
  const h = harness(); h.play('game_1', guess === answer, {predicted_digits: guess, answer_digits: answer});
  const ids = Object.keys(h.profile().unlocked).filter(id => id.startsWith('g1_')).sort();
  assert.deepEqual(ids, expected.sort());
});

test('game 1 cumulative 10 rounds does not require wins', () => {
  const h = harness(); for (let i = 0; i < 9; i++) h.play('game_1', false);
  assert(!owns(h.profile(), 'g1_ten'));
  h.play('game_1', false); assert(owns(h.profile(), 'g1_ten'));
});

test('HIGH/LOW and ODD/EVEN wins require BOTH counters, never just total', () => {
  const h = harness();
  for (let i = 0; i < 30; i++) h.play('game_2', true, {choice: 'HIGH'});
  assert(owns(h.profile(), 'g2_ten_wins')); assert(!owns(h.profile(), 'g2_both_fifteen'));
  for (let i = 0; i < 14; i++) h.play('game_2', true, {choice: 'LOW'});
  h.play('game_2', false, {choice: 'LOW'}); assert(!owns(h.profile(), 'g2_both_fifteen'));
  h.play('game_2', true, {choice: 'LOW'}); assert(owns(h.profile(), 'g2_both_fifteen'));
  for (let i = 0; i < 5; i++) h.play('game_3', true, {choice: 'ODD'});
  for (let i = 0; i < 4; i++) h.play('game_3', true, {choice: 'EVEN'});
  assert(!owns(h.profile(), 'g3_both_five'));
  h.play('game_3', true, {choice: 'EVEN'}); assert(owns(h.profile(), 'g3_both_five'));
});

test('game 4 and 5 cumulative wins differ from their legendary consecutive wins', () => {
  const h = harness();
  for (let i = 0; i < 5; i++) {h.play('game_4', true); h.play('game_4', false);}
  assert(owns(h.profile(), 'g4_five_wins')); assert(!owns(h.profile(), 'g4_four_streak'));
  for (let i = 0; i < 4; i++) h.play('game_4', true);
  assert(owns(h.profile(), 'g4_four_streak'));
  for (let i = 0; i < 3; i++) {h.play('game_5', true); h.play('game_5', false);}
  assert(owns(h.profile(), 'g5_three_wins')); assert(!owns(h.profile(), 'g5_three_streak'));
  for (let i = 0; i < 3; i++) h.play('game_5', true);
  assert(owns(h.profile(), 'g5_three_streak'));
});

test('old settlement replays cannot count twice or reset later equipment/progress', () => {
  const h = harness(); const request = h.makeRound('game_1', false, {predicted_digits: 36, answer_digits: 37});
  const first = h.send(request); h.play('game_4', true);
  const before = h.snapshot(), p = h.profile(); const replay = h.send(request);
  assert.equal(replay.replayed, true); assert.deepEqual(replay.newly_unlocked, first.newly_unlocked);
  assert.equal(replay.badge_profile.progress.total, p.progress.total); assert.equal(h.snapshot(), before);
  const altered = {...request, badge_evidence: {predicted_digits: 35, answer_digits: 37}};
  assert.throws(() => h.send(altered), code('IDEMPOTENCY_CONFLICT')); assert.equal(h.snapshot(), before);
});

test('wallet, receipt and profile either commit together or all remain unchanged', () => {
  const h = harness(); const request = h.makeRound('game_1', true);
  const before = h.snapshot(); h.control.failCommit = true;
  assert.throws(() => h.send(request), /simulated atomic rejection/); assert.equal(h.snapshot(), before);
  assert.equal(h.control.locked, false);
  h.send(request); assert.equal(h.profile().progress.total, 1); assert(owns(h.profile(), 'g1_hit'));
});

test('bad or missing facts cannot settle an enabled round', () => {
  const h = harness();
  for (const facts of [null, {}, {predicted_digits: true, answer_digits: 1},
    {predicted_digits: '37', answer_digits: 37}, {predicted_digits: 37, answer_digits: 37},
    {predicted_digits: 36, answer_digits: 37, unlock: 'g1_hit'}]) {
    const request = h.makeRound('game_1', false, facts); const before = h.snapshot();
    assert.throws(() => h.send(request), code('BADGE_EVIDENCE_REQUIRED')); assert.equal(h.snapshot(), before);
  }
  const request = h.makeRound('game_4', true, {}, '10101', false);
  const before = h.snapshot(); assert.throws(() => h.send(request), code('BADGE_EVIDENCE_REQUIRED'));
  assert.equal(h.snapshot(), before);
});

test('equip validates ownership and revision, supports 0, and never changes wallet/progress', () => {
  const h = harness(); const before = h.snapshot();
  assert.throws(() => h.equip('g1_hit', 0), code('BADGE_LOCKED')); assert.equal(h.snapshot(), before);
  h.play('game_1', true); const earned = h.profile(); const wallet = plain(h.users.rows);
  const equip = h.equip('g1_hit', earned.revision, 777);
  assert.equal(equip.badge_profile.equipped, 'g1_hit'); assert.deepEqual(h.users.rows, wallet);
  assert.deepEqual(equip.badge_profile.progress, earned.progress);
  assert.throws(() => h.equip('first_round', earned.revision), code('STALE_BADGE_PROFILE'));
  const cleared = h.equip('0', equip.badge_profile.revision);
  const after = h.snapshot();
  const replay = h.equip('g1_hit', earned.revision, 777);
  assert.equal(replay.replayed, true); assert.equal(replay.badge_profile.equipped, '0');
  assert.equal(h.snapshot(), after);
  assert.throws(() => h.equip('first_round', earned.revision, 777), code('IDEMPOTENCY_CONFLICT'));
  assert.throws(() => h.equip('g1_hit', 0, 778, '10102'), code('BADGE_LOCKED'));
  assert.equal(cleared.badge_profile.equipped, '0');
});

test('equipment commands and bank operations do not count as rounds', () => {
  const h = harness(); h.play('game_4', true); let p = h.profile();
  h.equip('first_round', p.revision);
  h.send({kind: 'borrow', transaction_id: 'borrow:' + hex(888), amount: 1000,
    expected_coins: h.users.rows[1][2], expected_loan: 0, expected_principal: 0});
  h.send({kind: 'interest', transaction_id: 'interest:' + hex(1), game: 'game_4', round_id: hex(1)});
  p = h.profile(); assert.equal(p.progress.total, 1); assert.equal(p.progress.streak, 1);
});

test('corrupt profiles fail closed instead of being silently zeroed', () => {
  const h = harness(); h.play('game_4', true);
  h.sheets.get('BadgeProfiles').rows[1][3] = '{broken';
  const request = h.makeRound('game_4', true); const before = h.snapshot();
  assert.throws(() => h.send(request), code('BADGE_DATA_INVALID')); assert.equal(h.snapshot(), before);
});

test('script lock and token protect all mutations', () => {
  const h = harness(); const request = h.makeRound('game_4', true); const before = h.snapshot();
  h.control.locked = true; assert.throws(() => h.send(request), code('BUSY'));
  h.control.locked = false;
  assert.throws(() => h.send({...request, token: 'wrong'}), code('UNAUTHORIZED'));
  assert.equal(h.snapshot(), before);
});

test('pause/resume preserves unlocks and totals but does not bridge unrecorded streaks', () => {
  const h = harness(); for (let i = 0; i < 3; i++) h.play('game_4', true);
  const epoch = h.props.BADGES_EPOCH; h.ctx.enableBadgeCollection(); assert.equal(h.props.BADGES_EPOCH, epoch);
  h.ctx.disableBadgeCollection(); h.play('game_4', false, {}, undefined, false);
  h.ctx.enableBadgeCollection(); assert.notEqual(h.props.BADGES_EPOCH, epoch);
  h.play('game_4', true); const p = h.profile();
  assert.equal(p.progress.total, 4); assert.equal(p.progress.streak, 1);
  assert.equal(p.progress.games.game_4.streak, 1); assert(!owns(p, 'g4_four_streak'));
  assert(owns(p, 'streak_three'));
});

test('legacy settlements never receive speculative retroactive awards', () => {
  const h = harness({enable: false}); const request = h.makeRound('game_1', true, undefined, undefined, false);
  h.send(request); h.ctx.enableBadgeCollection();
  const replay = h.send({...request, badge_version: 1, badge_evidence: {predicted_digits: 50, answer_digits: 50}});
  assert.equal(replay.badges_tracked, false); assert.equal(h.profile().progress.total, 0);
});

test('award evidence and first-earned time are durably audited, no effects enter user rows', () => {
  const h = harness(); h.play('game_1', true);
  const detail = JSON.parse(h.ledger.rows.at(-1)[15]);
  assert.equal(detail.badge_version, 1); assert.deepEqual(detail.evidence, {predicted_digits: 50, answer_digits: 50});
  assert(detail.newly_unlocked.includes('g1_hit'));
  assert.equal(h.users.rows[1][8], 'https://example.test/'); assert.equal(h.users.rows[1][9], 'untouched');
  assert(Number.isFinite(Date.parse(h.profile().unlocked.g1_hit.earned_at)));
});

test('mixed streak excludes game diversity older than the last eight wins', () => {
  const h = harness(); h.play('game_3', true);
  for (let i = 0; i < 7; i++) h.play('game_2', true);
  h.play('game_4', true);
  assert(!owns(h.profile(), 'streak_eight_mixed'));
  assert.equal(h.profile().progress.streak_games.length, 8);
  h.play('game_3', true);
  assert(owns(h.profile(), 'streak_eight_mixed'));
});
