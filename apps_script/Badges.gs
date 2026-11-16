/**
 * Badge awarding support for Code.gs. All writes are owned by the same
 * Apps Script transaction gateway and guarded by its ScriptLock.
 *
 * Transaction !P stores a badge-v1 evidence payload on each successful
 * settlement. Old settlements lacking the payload still count toward
 * game-play / win / streak achievements.
 */
const BADGE_EQUIPPED_COLUMN = 10; // Users!J (1-based)
const BADGE_OWNED_COLUMN = 11; // Users!K (1-based)
const BADGE_COLUMN_HEADERS = ['장착배지', '보유배지'];
const BADGE_DETAIL_PREFIX = 'badge-v1:';
const BADGE_IDS = [
  'first_round', 'all_games', 'thirty_rounds', 'streak_three',
  'streak_five_mixed', 'streak_eight_mixed', 'g1_ten',
  'g1_within_ten', 'g1_within_three', 'g1_exact_ten', 'g1_exact_one',
  'g1_hit', 'g2_ten_wins', 'g2_both_fifteen',
  'g3_both_five', 'g3_five_streak', 'g4_five_wins',
  'g4_four_streak', 'g5_three_wins', 'g5_three_streak'
];
const BADGE_ID_SET = new Set(BADGE_IDS);

/**
 * Run once as spreadsheet owner after backing up Users.
 * Refuses to repurpose any already occupied J/K cells.
 * Can be rerun after a successful installation without resetting badges.
 */
function installBadgeColumns() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) fail_('BUSY', 'Transaction service is busy');
  try {
    const ss = SpreadsheetApp.openById(property_('SPREADSHEET_ID'));
    const users = ss.getSheetByName(USER_TAB);
    if (!users) fail_('NOT_CONFIGURED', 'Users sheet not found');
    if (users.getMaxColumns() < BADGE_OWNED_COLUMN) {
      users.insertColumnsAfter(users.getMaxColumns(), BADGE_OWNED_COLUMN - users.getMaxColumns());
    }
    const n = Math.max(1, users.getLastRow());
    const cells = users.getRange(1, BADGE_EQUIPPED_COLUMN, n, 2).getValues();
    const header = cells[0].map(String);
    const valid = header.every((value, idx) => value === '' || value === BADGE_COLUMN_HEADERS[idx]);
    if (!valid) fail_('BADGES_NOT_READY', 'Users J/K already contain other headers');
    // If the header is missing, refuse to adopt an occupied column.
    for (let column = 0; column < 2; column++) {
      if (header[column] === '') {
        if (cells.slice(1).some(row => row[column] !== '' && row[column] !== null)) {
          fail_('BADGES_NOT_READY', 'Users J/K have data without badge headers');
        }
      }
    }
    users.getRange(1, BADGE_EQUIPPED_COLUMN, 1, 2).setValues([BADGE_COLUMN_HEADERS]);
    if (n > 1) {
      const equipped = cells.slice(1).map(row => [row[0] === '' || row[0] === null ? '0' : String(row[0])]);
      users.getRange(2, BADGE_EQUIPPED_COLUMN, equipped.length, 1).setValues(equipped);
    }
    return {ok: true, users_initialized: n - 1};
  } finally {
    lock.releaseLock();
  }
}

function requireBadgeColumns_(users) {
  if (users.getMaxColumns() < BADGE_OWNED_COLUMN) {
    fail_('BADGES_NOT_READY', 'Run installBadgeColumns first');
  }
  const headers = users.getRange(1, BADGE_EQUIPPED_COLUMN, 1, 2).getValues()[0];
  if (headers[0] !== BADGE_COLUMN_HEADERS[0] || headers[1] !== BADGE_COLUMN_HEADERS[1]) {
    fail_('BADGES_NOT_READY', 'Run installBadgeColumns first');
  }
}

function badgeProfile_(users, zeroBasedRowIndex) {
  const values = users.getRange(zeroBasedRowIndex + 1, BADGE_EQUIPPED_COLUMN, 1, 2).getValues()[0];
  const rawEquipped = String(values[0] == null || values[0] === '' ? '0' : values[0]);
  const seen = new Set();
  const tokens = String(values[1] || '').split(/\s+/).filter(Boolean);
  tokens.forEach(id => {
    if (BADGE_ID_SET.has(id)) seen.add(id);
  });
  const owned = BADGE_IDS.filter(id => seen.has(id));
  return {equipped: rawEquipped === '0' || owned.includes(rawEquipped) ? rawEquipped : '0', owned: owned};
}

function badgeProfileWrite_(users, zeroBasedRowIndex, profile) {
  return {updateCells: {
    start: {sheetId: users.getSheetId(), rowIndex: zeroBasedRowIndex, columnIndex: BADGE_EQUIPPED_COLUMN - 1},
    rows: [{values: [cell_(profile.equipped), cell_(profile.owned.join(' '))]}],
    fields: 'userEnteredValue'
  }};
}

function badgeDigits_(value) {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 99;
}

function badgeEvidence_(game, raw, isWin) {
  // Old clients may omit evidence: they still receive basic round achievements.
  if (raw == null) return {};
  if (typeof raw !== 'object' || Array.isArray(raw)) fail_('INVALID_REQUEST', 'Invalid badge evidence');
  const keys = Object.keys(raw);
  const allowed = game === 'game_1' ? ['predicted_digits', 'answer_digits'] :
    (game === 'game_2' || game === 'game_3' ? ['choice'] : []);
  if (keys.some(key => !allowed.includes(key))) fail_('INVALID_REQUEST', 'Invalid badge evidence fields');
  if (game === 'game_1' && keys.length) {
    if (!badgeDigits_(raw.predicted_digits) || !badgeDigits_(raw.answer_digits)) {
      fail_('INVALID_REQUEST', 'Prediction evidence needs two valid digits');
    }
    if ((raw.predicted_digits === raw.answer_digits) !== isWin) {
      fail_('INVALID_REQUEST', 'Prediction evidence disagrees with win/loss');
    }
    return {predicted_digits: raw.predicted_digits, answer_digits: raw.answer_digits};
  }
  if (game === 'game_2' && keys.length) {
    if (keys.length !== 1 || !['HIGH', 'LOW'].includes(raw.choice)) {
      fail_('INVALID_REQUEST', 'Invalid HIGH/LOW selection evidence');
    }
    return {choice: raw.choice};
  }
  if (game === 'game_3' && keys.length) {
    if (keys.length !== 1 || !['홀', '짝'].includes(raw.choice)) {
      fail_('INVALID_REQUEST', 'Invalid parity selection evidence');
    }
    return {choice: raw.choice};
  }
  return {};
}

function badgeDetail_(evidence) {
  return BADGE_DETAIL_PREFIX + JSON.stringify(evidence);
}

function badgeParseDetail_(value) {
  const raw = String(value || '');
  if (!raw.startsWith(BADGE_DETAIL_PREFIX)) return {};
  try {
    const result = JSON.parse(raw.substring(BADGE_DETAIL_PREFIX.length));
    return result && typeof result === 'object' && !Array.isArray(result) ? result : {};
  } catch (error) {
    return {};
  }
}

/**
 * Rebuild awards from committed settlement records in ledger order.
 * No provisional bet or client-side session value enters this function.
 */
function evaluateBadgesFromSettlements_(settlements) {
  const earned = new Set();
  const seen = new Set();
  const games = ['game_1', 'game_2', 'game_3', 'game_4', 'game_5'];
  const plays = {}, wins = {}, gameStreak = {};
  games.forEach(g => {plays[g] = 0; wins[g] = 0; gameStreak[g] = 0;});
  const choices = {game_2: {HIGH: 0, LOW: 0}, game_3: {'홀': 0, '짝': 0}};
  let globalStreak = [];

  settlements.forEach(event => {
    const rid = String(event.round_id || '');
    const game = event.game;
    if (!rid || seen.has(rid) || !games.includes(game) || typeof event.is_win !== 'boolean') return;
    seen.add(rid);
    const won = event.is_win;
    plays[game]++;
    if (won) {
      wins[game]++;
      gameStreak[game]++;
      globalStreak.push(game);
    } else {
      gameStreak[game] = 0;
      globalStreak = [];
    }
    earned.add('first_round');
    if (games.every(g => plays[g] > 0)) earned.add('all_games');
    if (games.reduce((acc, g) => acc + plays[g], 0) >= 30) earned.add('thirty_rounds');
    if (globalStreak.length >= 3) earned.add('streak_three');
    if (globalStreak.length >= 5 && new Set(globalStreak.slice(-5)).size >= 2) earned.add('streak_five_mixed');
    if (globalStreak.length >= 8 && new Set(globalStreak.slice(-8)).size >= 3) earned.add('streak_eight_mixed');
    const evidence = event.evidence || {};
    if (game === 'game_1') {
      if (plays[game] >= 10) earned.add('g1_ten');
      if (badgeDigits_(evidence.predicted_digits) && badgeDigits_(evidence.answer_digits)) {
        const diff = Math.abs(evidence.predicted_digits - evidence.answer_digits);
        if (won && diff === 0) earned.add('g1_hit');
        if (!won && diff > 0) {
          if (diff <= 10) earned.add('g1_within_ten');
          if (diff <= 3) earned.add('g1_within_three');
          if (diff === 10) earned.add('g1_exact_ten');
          if (diff === 1) earned.add('g1_exact_one');
        }
      }
    }
    if (game === 'game_2') {
      if (wins[game] >= 10) earned.add('g2_ten_wins');
      if (won && ['HIGH', 'LOW'].includes(evidence.choice)) choices.game_2[evidence.choice]++;
      if (choices.game_2.HIGH >= 15 && choices.game_2.LOW >= 15) earned.add('g2_both_fifteen');
    }
    if (game === 'game_3') {
      if (won && ['홀', '짝'].includes(evidence.choice)) choices.game_3[evidence.choice]++;
      if (choices.game_3['홀'] >= 5 && choices.game_3['짝'] >= 5) earned.add('g3_both_five');
      if (gameStreak[game] >= 5) earned.add('g3_five_streak');
    }
    if (game === 'game_4') {
      if (wins[game] >= 5) earned.add('g4_five_wins');
      if (gameStreak[game] >= 4) earned.add('g4_four_streak');
    }
    if (game === 'game_5') {
      if (wins[game] >= 3) earned.add('g5_three_wins');
      if (gameStreak[game] >= 3) earned.add('g5_three_streak');
    }
  });
  return BADGE_IDS.filter(id => earned.has(id));
}

function badgeSettlements_(ledger, studentId, newSettleRow) {
  const n = Math.max(0, ledger.getLastRow() - 1);
  const all = n ? ledger.getRange(2, 1, n, HEADERS.length).getValues() : [];
  if (newSettleRow) all.push(newSettleRow);
  return all.filter(row =>
    String(row[3]) === 'settle' &&
    sid_(row[2]) === studentId &&
    Object.prototype.hasOwnProperty.call(RULES, String(row[4]))
  ).map(row => ({
    round_id: String(row[5]),
    game: String(row[4]),
    is_win: row[8] === true,
    evidence: badgeParseDetail_(row[15])
  }));
}

function awardBadges_(ledger, users, user, studentId, newSettleRow) {
  const profile = badgeProfile_(users, user.rowIndex);
  const earned = evaluateBadgesFromSettlements_(badgeSettlements_(ledger, studentId, newSettleRow));
  const before = new Set(profile.owned);
  const unlocked = earned.filter(id => !before.has(id));
  if (!unlocked.length) return {profile: profile, unlocked: [], request: null};
  const all = new Set(profile.owned.concat(unlocked));
  const updated = {equipped: profile.equipped, owned: BADGE_IDS.filter(id => all.has(id))};
  return {profile: updated, unlocked: unlocked, request: badgeProfileWrite_(users, user.rowIndex, updated)};
}
