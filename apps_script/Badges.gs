/** Badge foundation: no icon rendering, no automatic equipment, no wallet bonuses.
 * All runtime reads/writes below run inside Code.gs's authenticated ScriptLock.
 * Wallet, settlement receipt and badge profile share ONE Sheets batchUpdate.
 */
const BADGE_TAB = 'BadgeProfiles';
const BADGE_HEADERS = [
  'student_id', 'equipped_badge', 'unlocked_json', 'progress_json',
  'revision', 'updated_at', 'schema_version'
];
const BADGE_GAMES = ['game_1', 'game_2', 'game_3', 'game_4', 'game_5'];
const BADGE_COUNTERS = [
  'total', 'streak', 'best_streak', 'high_wins', 'low_wins', 'odd_wins',
  'even_wins', 'near_10', 'near_3', 'exact_10', 'exact_1'
];

function badgeObject_(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function badgeCount_(value) {
  return Number.isSafeInteger(value) && value >= 0;
}
function badgeKnown_(id) {
  return typeof id === 'string' && BADGE_CATALOG.badges.some(b => b.id === id);
}
function badgeEmpty_(sid) {
  const progress = {epoch: '', streak_games: [], games: {}};
  BADGE_COUNTERS.forEach(k => { progress[k] = 0; });
  BADGE_GAMES.forEach(g => {
    progress.games[g] = {played: 0, wins: 0, streak: 0, best_streak: 0};
  });
  return {
    schema_version: 1, student_id: sid, equipped: '0', unlocked: {},
    progress: progress, revision: 0, updated_at: ''
  };
}

function badgeValidate_(p) {
  const invalid = () => fail_('BADGE_DATA_INVALID', 'Badge profile is corrupt; restore it, do not zero it');
  if (!badgeObject_(p) || p.schema_version !== 1 || !/^[0-9]{5}$/.test(p.student_id) ||
      !badgeCount_(p.revision) || typeof p.updated_at !== 'string' ||
      !badgeObject_(p.unlocked) || !badgeObject_(p.progress)) invalid();
  const s = p.progress;
  if (typeof s.epoch !== 'string' || !badgeObject_(s.games) ||
      !Array.isArray(s.streak_games) || s.streak_games.length > 8 ||
      s.streak_games.some(g => !BADGE_GAMES.includes(g)) ||
      BADGE_COUNTERS.some(k => !badgeCount_(s[k]))) invalid();
  let played = 0, wins = 0;
  BADGE_GAMES.forEach(g => {
    const a = s.games[g];
    if (!badgeObject_(a) || ['played', 'wins', 'streak', 'best_streak'].some(k => !badgeCount_(a[k])) ||
        a.wins > a.played || a.streak > a.best_streak || a.best_streak > a.wins) invalid();
    played += a.played; wins += a.wins;
  });
  if (played !== s.total || !badgeCount_(played) || !badgeCount_(wins) ||
      s.streak > s.best_streak || s.best_streak > wins ||
      s.streak_games.length !== Math.min(s.streak, 8) ||
      s.high_wins + s.low_wins !== s.games.game_2.wins ||
      s.odd_wins + s.even_wins !== s.games.game_3.wins ||
      s.exact_1 > s.near_3 || s.near_3 > s.near_10 || s.exact_10 > s.near_10 ||
      s.near_10 > s.games.game_1.played - s.games.game_1.wins) invalid();
  Object.keys(p.unlocked).forEach(id => {
    const award = p.unlocked[id];
    if (!badgeKnown_(id) || !badgeObject_(award) || typeof award.earned_at !== 'string' ||
        !Number.isFinite(Date.parse(award.earned_at)) || !/^[a-f0-9]{32}$/.test(award.round_id)) invalid();
  });
  if (p.equipped !== '0' && (!badgeKnown_(p.equipped) ||
      !Object.prototype.hasOwnProperty.call(p.unlocked, p.equipped))) invalid();
  return p;
}

function badgeEvidence_(game, win, raw) {
  if (!BADGE_GAMES.includes(game) || typeof win !== 'boolean' || !badgeObject_(raw)) {
    fail_('BADGE_EVIDENCE_REQUIRED', 'A settled round needs validated badge evidence');
  }
  let evidence = {};
  if (game === 'game_1') {
    const a = raw.predicted_digits, b = raw.answer_digits;
    if (!badgeCount_(a) || !badgeCount_(b) || a > 99 || b > 99 || win !== (a === b)) {
      fail_('BADGE_EVIDENCE_REQUIRED', 'Invalid game 1 digits or inconsistent win');
    }
    evidence = {predicted_digits: a, answer_digits: b};
  } else if (game === 'game_2' || game === 'game_3') {
    const choices = game === 'game_2' ? ['HIGH', 'LOW'] : ['ODD', 'EVEN'];
    if (!choices.includes(raw.choice)) fail_('BADGE_EVIDENCE_REQUIRED', 'Invalid game choice');
    evidence = {choice: raw.choice};
  }
  if (Object.keys(raw).sort().join(',') !== Object.keys(evidence).sort().join(',')) {
    fail_('BADGE_EVIDENCE_REQUIRED', 'Unknown evidence fields');
  }
  return evidence;
}

function badgeMetric_(s, metric) {
  if (metric === 'played_games') return BADGE_GAMES.filter(g => s.games[g].played > 0).length;
  if (metric === 'streak_game_count_5') return new Set(s.streak_games.slice(-5)).size;
  if (metric === 'streak_game_count_8') return new Set(s.streak_games.slice(-8)).size;
  return metric.split('.').reduce((value, key) => value[key], s);
}

/** Pure transition; call only AFTER the gateway rejects duplicate round IDs. */
function badgeAdvance_(profile, game, win, evidence, roundId, now, epoch) {
  badgeValidate_(profile);
  const facts = badgeEvidence_(game, win, evidence);
  if (!/^[a-f0-9]{32}$/.test(roundId) || !epoch || !Number.isFinite(Date.parse(now))) {
    fail_('BADGE_DATA_INVALID', 'Invalid round identity or collection epoch');
  }
  const p = JSON.parse(JSON.stringify(profile)), s = p.progress;
  // Paused collection is a gap, not evidence of an uninterrupted winning run.
  if (s.epoch !== epoch) {
    s.epoch = epoch; s.streak = 0; s.streak_games = [];
    BADGE_GAMES.forEach(g => { s.games[g].streak = 0; });
  }
  const g = s.games[game];
  s.total++; g.played++;
  if (win) {
    g.wins++; g.streak++; s.streak++;
    g.best_streak = Math.max(g.best_streak, g.streak);
    s.best_streak = Math.max(s.best_streak, s.streak);
    s.streak_games.push(game);
    s.streak_games = s.streak_games.slice(-8);
    if (game === 'game_2') s[facts.choice === 'HIGH' ? 'high_wins' : 'low_wins']++;
    if (game === 'game_3') s[facts.choice === 'ODD' ? 'odd_wins' : 'even_wins']++;
  } else {
    g.streak = 0; s.streak = 0; s.streak_games = [];
    if (game === 'game_1') {
      const error = Math.abs(facts.predicted_digits - facts.answer_digits);
      if (error <= 10) s.near_10++;
      if (error <= 3) s.near_3++;
      if (error === 10) s.exact_10++;
      if (error === 1) s.exact_1++;
    }
  }
  const unlocked = [];
  BADGE_CATALOG.badges.forEach(b => {
    if (!Object.prototype.hasOwnProperty.call(p.unlocked, b.id) &&
        b.conditions.every(c => badgeMetric_(s, c.metric) >= c.target)) {
      p.unlocked[b.id] = {earned_at: now, round_id: roundId};
      unlocked.push(b.id);
    }
  });
  p.revision++; p.updated_at = now;
  badgeValidate_(p);
  return {profile: p, newly_unlocked: unlocked};
}

function badgeSheet_(ss) {
  const sheet = ss.getSheetByName(BADGE_TAB);
  if (!sheet || sheet.getMaxColumns() < BADGE_HEADERS.length || sheet.getLastRow() < 1 ||
      JSON.stringify(sheet.getRange(1, 1, 1, BADGE_HEADERS.length).getValues()[0]) !== JSON.stringify(BADGE_HEADERS)) {
    fail_('BADGES_NOT_READY', 'Run installBadgeSystem(); do not overwrite existing headers');
  }
  return sheet;
}
function badgeParse_(text) {
  if (typeof text !== 'string' || text.length > 40000) fail_('BADGE_DATA_INVALID', 'Invalid badge JSON');
  try { return JSON.parse(text); }
  catch (_) { fail_('BADGE_DATA_INVALID', 'Invalid badge JSON'); }
}
function badgeRead_(ss, sid) {
  const sheet = badgeSheet_(ss);
  const rows = sheet.getLastRow() > 1 ?
    sheet.getRange(2, 1, sheet.getLastRow() - 1, BADGE_HEADERS.length).getValues() : [];
  let found = null;
  rows.forEach((row, index) => {
    if (sid_(row[0]) !== sid) return;
    if (found) fail_('BADGE_DATA_INVALID', 'Duplicate badge profile');
    const profile = {
      student_id: sid, equipped: String(row[1]), unlocked: badgeParse_(row[2]),
      progress: badgeParse_(row[3]), revision: row[4], updated_at: row[5], schema_version: row[6]
    };
    found = {sheet: sheet, rowIndex: index + 1, profile: badgeValidate_(profile)};
  });
  return found || {sheet: sheet, rowIndex: null, profile: badgeEmpty_(sid)};
}
function badgeWrite_(record, p) {
  badgeValidate_(p);
  const row = [p.student_id, p.equipped, JSON.stringify(p.unlocked), JSON.stringify(p.progress),
    p.revision, p.updated_at, p.schema_version];
  if (record.rowIndex === null) return append_(record.sheet, [row]);
  return {updateCells: {
    start: {sheetId: record.sheet.getSheetId(), rowIndex: record.rowIndex, columnIndex: 0},
    rows: [{values: row.map(cell_)}], fields: 'userEnteredValue'
  }};
}

function badgeStatus_(ss) {
  const properties = PropertiesService.getScriptProperties();
  const enabled = properties.getProperty('BADGES_ENABLED') === 'true';
  const epoch = properties.getProperty('BADGES_EPOCH') || '';
  if (enabled) {
    badgeSheet_(ss);
    if (!epoch) fail_('BADGES_NOT_READY', 'Use enableBadgeCollection() to set the collection epoch');
  }
  return {badge_version: 1, badges_enabled: enabled, badge_epoch: epoch};
}
function badgePrepare_(ss, tx, request) {
  const mode = badgeStatus_(ss);
  if (!mode.badges_enabled) {
    if (request.badge_version !== undefined) fail_('BADGES_DISABLED', 'Collection was paused; refresh and retry');
    return null;
  }
  if (request.badge_version !== 1) fail_('BADGE_EVIDENCE_REQUIRED', 'Update the app before settling badge-enabled rounds');
  const evidence = badgeEvidence_(tx.game, tx.is_win, request.badge_evidence);
  const record = badgeRead_(ss, tx.student_id);
  const advanced = badgeAdvance_(record.profile, tx.game, tx.is_win, evidence,
    tx.round_id, new Date().toISOString(), mode.badge_epoch);
  return {
    write: badgeWrite_(record, advanced.profile),
    detail: JSON.stringify({badge_version: 1, epoch: mode.badge_epoch,
      evidence: evidence, newly_unlocked: advanced.newly_unlocked}),
    response: {badge_version: 1, badges_tracked: true, badge_profile: advanced.profile,
      newly_unlocked: advanced.newly_unlocked}
  };
}
function badgeReplay_(ss, previous, request) {
  // Legacy settlements stay legacy: never manufacture pre-launch achievements.
  if (!String(previous[15] || '').startsWith('{')) return {badges_tracked: false};
  const saved = badgeParse_(previous[15]);
  if (saved.badge_version !== 1) return {badges_tracked: false};
  if (request.badge_version !== undefined) {
    if (request.badge_version !== 1 || JSON.stringify(saved.evidence) !==
        JSON.stringify(badgeEvidence_(String(previous[4]), previous[8], request.badge_evidence))) {
      fail_('IDEMPOTENCY_CONFLICT', 'Round already settled with different badge evidence');
    }
  }
  return {badge_version: 1, badges_tracked: true,
    badge_profile: badgeRead_(ss, sid_(previous[2])).profile,
    newly_unlocked: saved.newly_unlocked};
}

function badgeOperation_(ss, users, ledger, tx, request) {
  if (request.badge_version !== 1) fail_('INVALID_REQUEST', 'Unsupported badge protocol');
  const balances = balance_(findUser_(users, tx.student_id).values);
  const record = badgeRead_(ss, tx.student_id);
  if (tx.kind === 'badge_profile') {
    return Object.assign(result_(balances, null, false), {badge_version: 1, badge_profile: record.profile});
  }
  const id = request.badge_id, revision = request.expected_revision;
  if ((id !== '0' && !badgeKnown_(id)) || !badgeCount_(revision)) {
    fail_('INVALID_REQUEST', 'Unknown badge or invalid revision');
  }
  const detail = JSON.stringify({badge_id: id, expected_revision: revision});
  const previous = findTransaction_(ledger, tx.transaction_id);
  if (previous) {
    if (sid_(previous[2]) !== tx.student_id || previous[3] !== 'badge_equip' || previous[15] !== detail) {
      fail_('IDEMPOTENCY_CONFLICT', 'Equipment request ID reused with different arguments');
    }
    // Return CURRENT equipment; never re-apply an old command after a newer selection.
    return Object.assign(result_(balances, null, true), {badge_version: 1, badge_profile: record.profile});
  }
  const p = record.profile;
  if (p.revision !== revision) fail_('STALE_BADGE_PROFILE', 'Refresh badge profile before equipping');
  if (id !== '0' && !Object.prototype.hasOwnProperty.call(p.unlocked, id)) {
    fail_('BADGE_LOCKED', 'Badge not earned by this account');
  }
  p.equipped = id; p.revision++; p.updated_at = new Date().toISOString();
  const receipt = record_(tx, balances, balances, detail);
  commit_(ss, [badgeWrite_(record, p), append_(ledger, [receipt])]);
  return Object.assign(result_(balances, null, false), {badge_version: 1, badge_profile: p});
}

function badgeAdmin_(action) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) fail_('BUSY', 'Try again when transactions finish');
  try { return action(SpreadsheetApp.openById(property_('SPREADSHEET_ID'))); }
  finally { lock.releaseLock(); }
}

/** Owner-only editor action. Idempotent; NEVER edits Users, Transactions or awards. */
function installBadgeSystem() {
  return badgeAdmin_(ss => {
    let sheet = ss.getSheetByName(BADGE_TAB);
    if (sheet) { badgeSheet_(ss); return {created: false, sheet: BADGE_TAB}; }
    sheet = ss.insertSheet(BADGE_TAB);
    sheet.getRange(1, 1, 1, BADGE_HEADERS.length).setValues([BADGE_HEADERS]);
    sheet.setFrozenRows(1);
    return {created: true, sheet: BADGE_TAB};
  });
}

/** Run only AFTER deploying all .gs files and merging the updated Python client. */
function enableBadgeCollection() {
  return badgeAdmin_(ss => {
    badgeSheet_(ss);
    const properties = PropertiesService.getScriptProperties();
    if (properties.getProperty('BADGES_ENABLED') !== 'true') {
      properties.setProperties({BADGES_ENABLED: 'true', BADGES_EPOCH: Utilities.getUuid()});
    }
    return badgeStatus_(ss);
  });
}
function disableBadgeCollection() {
  return badgeAdmin_(ss => {
    PropertiesService.getScriptProperties().setProperty('BADGES_ENABLED', 'false');
    return badgeStatus_(ss);
  });
}
