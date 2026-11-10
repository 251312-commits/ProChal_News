/**
 * Serialized Google Sheets wallet ledger for ProChal News.
 *
 * Deploy as a Web App (execute as owner; access Anyone). Set Script Properties
 * SPREADSHEET_ID and TRANSACTION_TOKEN, enable the advanced Google Sheets API,
 * and run installTransactionLedger() once before deployment.
 *
 * Every wallet mutation MUST use this gateway. Editing Users!C/D/G/H outside it
 * bypasses LockService and defeats its concurrency guarantee. Users!G stores
 * total outstanding debt; Users!H stores outstanding borrowed principal.
 */
const USER_TAB = 'Users';
const LEDGER_TAB = 'Transactions';
const HEADERS = [
  'transaction_id', 'timestamp', 'student_id', 'kind', 'game', 'round_id',
  'bet', 'coin_delta', 'is_win', 'coins_before', 'coins_after',
  'streak_before', 'streak_after', 'loan_before', 'loan_after', 'detail'
];
const RULES = {game_1: 100, game_2: 1, game_3: 1, game_4: 2, game_5: 5};
const MAX_PRINCIPAL = 10000; // The limit is on unpaid borrowed principal, not interest.
const GATEWAY_VERSION = 2; // Capabilities: principal in Users!H, interest per settled round.
const MAX_NICKNAME_LENGTH = 80;
const FIRST_TEACHER_ID = 40101;
const TURN_INTEREST_RATE_PERCENT = 20; // 1/5 per completed round, compound interest

function installTransactionLedger() {
  const ss = SpreadsheetApp.openById(property_('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName(LEDGER_TAB) || ss.insertSheet(LEDGER_TAB);
  if (sheet.getLastRow() > 0) {
    const actual = sheet.getRange(1, 1, 1, HEADERS.length).getValues()[0];
    if (JSON.stringify(actual) !== JSON.stringify(HEADERS)) {
      throw new Error('Transactions sheet header differs from expected schema');
    }
  } else {
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.setFrozenRows(1);
  }
  const users = ss.getSheetByName(USER_TAB);
  if (!users) fail_('NOT_CONFIGURED', 'Missing Users sheet');
  installPrincipalColumn_(users, sheet);
}

/**
 * Backfill Users!H from historical ledger events, preserving interest already
 * charged before the migration. For legacy accounts without ledger history,
 * assume their existing Users!G debt was borrowed principal.
 *
 * Run this installer once before using the new transaction gateway. If the
 * historical ledger disagrees with Users!G, stop rather than guess principal.
 */
function principalFromHistory_(rows, sid, outstandingLoan) {
  const history = rows.filter(row => sid_(row[2]) === sid);
  if (!history.length) return outstandingLoan;

  let principal = number_(history[0][13], 'first loan_before');
  let previousTotal = principal;
  for (const row of history) {
    const totalBefore = number_(row[13], 'loan_before');
    const totalAfter = number_(row[14], 'loan_after');
    if (totalBefore !== previousTotal) {
      fail_('MIGRATION_REQUIRED', 'Historical loan ledger is discontinuous for ' + sid);
    }
    const kind = String(row[3]);
    if (kind === 'borrow') {
      if (totalAfter < totalBefore) fail_('MIGRATION_REQUIRED', 'Invalid historic borrowing');
      principal += totalAfter - totalBefore;
    } else if (kind === 'repay') {
      if (totalAfter > totalBefore) fail_('MIGRATION_REQUIRED', 'Invalid historic repayment');
      // Repay interest before principal; the principal cannot exceed total debt.
      principal = Math.min(principal, totalAfter);
    } else if (kind === 'interest') {
      if (totalAfter < totalBefore) fail_('MIGRATION_REQUIRED', 'Invalid historic interest');
    } else if (totalBefore !== totalAfter) {
      fail_('MIGRATION_REQUIRED', 'Unknown loan event for ' + sid);
    }
    previousTotal = totalAfter;
  }
  if (previousTotal !== outstandingLoan || principal > outstandingLoan ||
      !Number.isSafeInteger(principal)) {
    fail_('MIGRATION_REQUIRED', 'Users!G differs from Transactions history for ' + sid);
  }
  return principal;
}

function installPrincipalColumn_(users, ledger) {
  if (users.getMaxColumns() < 8) users.insertColumnsAfter(users.getMaxColumns(), 8 - users.getMaxColumns());
  const header = users.getRange(1, 8, 1, 1).getValues()[0][0];
  if (header && String(header) !== '대출원금') {
    fail_('NOT_CONFIGURED', 'Users!H is in use; cannot overwrite its column');
  }

  const count = Math.max(0, users.getLastRow() - 1);
  const userRows = count ? users.getRange(2, 1, count, 8).getValues() : [];
  const logCount = Math.max(0, ledger.getLastRow() - 1);
  const histories = logCount ? ledger.getRange(2, 1, logCount, HEADERS.length).getValues() : [];
  const toInitialize = [];
  userRows.forEach(function (values, index) {
    const total = number_(values[6] === '' ? 0 : values[6], 'loan');
    if (values[7] !== '' && values[7] != null) {
      const existing = number_(values[7], 'principal');
      if (existing > total) fail_('MIGRATION_REQUIRED', 'Existing principal exceeds total debt');
      return;
    }
    toInitialize.push({
      row: index + 2,
      amount: principalFromHistory_(histories, sid_(values[0]), total)
    });
  });
  users.getRange(1, 8, 1, 1).setValues([['대출원금']]);
  toInitialize.forEach(entry => users.getRange(entry.row, 8, 1, 1).setValues([[entry.amount]]));
}

function property_(name) {
  const value = PropertiesService.getScriptProperties().getProperty(name);
  if (!value) throw new Error('Missing script property: ' + name);
  return value;
}

function fail_(code, message, balances) {
  const error = new Error(message);
  error.code = code;
  if (balances) error.balances = balances;
  throw error;
}

function sid_(raw) {
  return String(raw == null ? '' : raw).trim().replace(/\.0$/, '');
}

function nickname_(raw) {
  if (typeof raw !== 'string') fail_('INVALID_NICKNAME', 'Nickname must be a string');
  const nickname = raw.trim();
  // No HTML syntax or formula characters may enter the Users sheet.
  if (!nickname || Array.from(nickname).length > MAX_NICKNAME_LENGTH ||
      !/^[\p{L}\p{N} _.-]+$/u.test(nickname)) {
    fail_('INVALID_NICKNAME', 'Nickname contains unsupported characters');
  }
  return nickname;
}

function isStudentId_(id) {
  return /^[1-3]0[1-5][01][0-9]$/.test(id);
}

function isTeacherId_(id) {
  return /^4[0-9]{4}$/.test(id);
}

function nextTeacherId_(users) {
  // Only called while holding ScriptLock.
  let highest = FIRST_TEACHER_ID - 1;
  if (users.getLastRow() > 1) {
    const ids = users.getRange(2, 1, users.getLastRow() - 1, 1).getValues();
    ids.forEach(function (entry) {
      const id = sid_(entry[0]);
      if (isTeacherId_(id)) highest = Math.max(highest, Number(id));
    });
  }
  if (highest >= 49999) fail_('TEACHER_IDS_EXHAUSTED', 'No more teacher IDs');
  return String(highest + 1);
}

function number_(value, name, min) {
  if (value === '' || value === null || value === undefined || typeof value === 'boolean') {
    fail_('INVALID_REQUEST', name + ' is missing');
  }
  const number = Number(typeof value === 'string' ? value.replace(/,/g, '') : value);
  if (!Number.isSafeInteger(number) || number < (min || 0)) {
    fail_('INVALID_REQUEST', name + ' must be a nonnegative safe integer');
  }
  return number;
}

function cell_(value) {
  if (typeof value === 'number') return {userEnteredValue: {numberValue: value}};
  if (typeof value === 'boolean') return {userEnteredValue: {boolValue: value}};
  return {userEnteredValue: {stringValue: String(value)}};
}

function findUser_(users, sid) {
  if (users.getLastRow() < 2) fail_('USER_NOT_FOUND', 'No registered player');
  const rows = users.getRange(2, 1, users.getLastRow() - 1, 8).getValues();
  let match = null;
  rows.forEach(function (values, index) {
    if (sid_(values[0]) === sid) {
      if (match) fail_('DUPLICATE_USER', 'Duplicate student ID');
      match = {rowIndex: index + 1, values: values}; // zero-based Sheets API row
    }
  });
  if (!match) fail_('USER_NOT_FOUND', 'No registered player');
  return match;
}

function findTransaction_(ledger, id) {
  const last = ledger.getLastRow();
  if (last < 2) return null;
  const ids = ledger.getRange(2, 1, last - 1, 1).getValues();
  for (let i = 0; i < ids.length; i++) {
    if (String(ids[i][0]) === id) {
      return ledger.getRange(i + 2, 1, 1, HEADERS.length).getValues()[0];
    }
  }
  return null;
}

function balance_(values) {
  // Blank streak and G debt cells are legacy zeros, but H must be explicitly
  // initialized: zeroing an unknown principal could bypass the borrowing cap.
  const sheetNumber = (raw, field) => number_(raw === '' || raw == null ? 0 : raw, field, 0);
  if (values[7] === '' || values[7] == null) {
    fail_('PRINCIPAL_NOT_READY', 'Users!H principal not initialized; run installTransactionLedger()');
  }
  const balance = {
    coins: sheetNumber(values[2], 'coins'),
    streak: sheetNumber(values[3], 'streak'),
    loan: sheetNumber(values[6], 'loan'),
    principal: number_(values[7], 'principal')
  };
  if (balance.principal > balance.loan) {
    fail_('INVALID_REQUEST', 'Principal cannot exceed total debt');
  }
  return balance;
}

function record_(tx, before, after, detail) {
  return [
    tx.transaction_id, new Date().toISOString(), tx.student_id, tx.kind,
    tx.game || '', tx.round_id || '', tx.bet || 0, tx.delta || 0,
    tx.is_win === true, before.coins, after.coins, before.streak,
    after.streak, before.loan, after.loan, detail || ''
  ];
}

function append_(sheet, rows) {
  return {
    appendCells: {
      sheetId: sheet.getSheetId(),
      rows: rows.map(function (row) {
        return {values: row.map(cell_)};
      }),
      fields: 'userEnteredValue'
    }
  };
}

function walletUpdate_(users, rowIndex, balance) {
  return [
    {updateCells: {
      start: {sheetId: users.getSheetId(), rowIndex: rowIndex, columnIndex: 2},
      rows: [{values: [cell_(balance.coins), cell_(balance.streak)]}],
      fields: 'userEnteredValue'
    }},
    {updateCells: {
      start: {sheetId: users.getSheetId(), rowIndex: rowIndex, columnIndex: 6},
      rows: [{values: [cell_(balance.loan), cell_(balance.principal)]}],
      fields: 'userEnteredValue'
    }}
  ];
}

function commit_(ss, requests) {
  if (typeof Sheets === 'undefined' || !Sheets.Spreadsheets) {
    fail_('NOT_CONFIGURED', 'Enable the Google Sheets advanced service');
  }
  // Sheets batchUpdate is atomic: either all wallet and ledger writes land or none.
  Sheets.Spreadsheets.batchUpdate({requests: requests}, ss.getId());
}

function result_(balances, row, replayed) {
  return {
    ok: true,
    gateway_version: GATEWAY_VERSION,
    replayed: replayed,
    balances: balances,
    settlement: row && String(row[3]) === 'settle' ? {
      coins: number_(row[10], 'coins_after'),
      streak: number_(row[12], 'streak_after'),
      loan: number_(row[14], 'loan_after'),
      delta: Number(row[7]),
      is_win: row[8] === true
    } : null,
    interest: row && String(row[3]) === 'interest' ? {
      charged: number_(row[14], 'loan_after') - number_(row[13], 'loan_before'),
      loan_before: number_(row[13], 'loan_before'),
      loan_after: number_(row[14], 'loan_after')
    } : null
  };
}

function turnInterest_(loan) {
  // 20% = 1/5; whole-coin round-up without floating-point multiplication.
  return Math.floor(loan / 5) + (loan % 5 === 0 ? 0 : 1);
}

function process_(request) {
  if (!request || typeof request !== 'object') fail_('INVALID_REQUEST', 'Invalid JSON');
  const token = property_('TRANSACTION_TOKEN');
  if (request.token !== token) fail_('UNAUTHORIZED', 'Invalid transaction token');
  const tx = {
    transaction_id: String(request.transaction_id || ''),
    student_id: sid_(request.student_id),
    kind: String(request.kind || ''),
    game: String(request.game || ''),
    round_id: String(request.round_id || '')
  };
  if (!/^(bet|settle|interest|borrow|repay|register|register_teacher|status):[a-f0-9]{32}$/.test(tx.transaction_id) ||
      !['bet', 'settle', 'interest', 'borrow', 'repay', 'register', 'register_teacher', 'status'].includes(tx.kind) ||
      (tx.kind === 'register_teacher' ? tx.student_id !== '' : !/^[0-9]{5}$/.test(tx.student_id)) ||
      tx.transaction_id.split(':', 1)[0] !== tx.kind) {
    fail_('INVALID_REQUEST', 'Invalid transaction ID, student ID, or operation');
  }
  if (tx.kind === 'bet' || tx.kind === 'settle' || tx.kind === 'interest') {
    if (!Object.prototype.hasOwnProperty.call(RULES, tx.game) ||
        !/^[a-f0-9]{32}$/.test(tx.round_id) ||
        tx.transaction_id !== tx.kind + ':' + tx.round_id) {
      fail_('INVALID_REQUEST', 'Invalid game or round');
    }
    if (tx.kind !== 'interest') {
      tx.bet = number_(request.bet, 'bet', 1000);
      if ((tx.bet - 1000) % 50 !== 0) fail_('INVALID_REQUEST', 'Bet must use 50C steps');
    }
  } else {
    if (tx.game || tx.round_id) fail_('INVALID_REQUEST', 'Unexpected game details');
  }
  if (tx.kind === 'settle' && typeof request.is_win !== 'boolean') {
    fail_('INVALID_REQUEST', 'is_win must be boolean');
  }
  if (tx.kind === 'borrow' || tx.kind === 'repay') {
    tx.amount = number_(request.amount, 'amount', 1);
  }

  // ScriptLock is shared across simultaneous Web App executions.
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) fail_('BUSY', 'Transaction service is busy');
  try {
    const ss = SpreadsheetApp.openById(property_('SPREADSHEET_ID'));
    const users = ss.getSheetByName(USER_TAB);
    const ledger = ss.getSheetByName(LEDGER_TAB);
    if (!users || !ledger) fail_('NOT_CONFIGURED', 'Missing Users or Transactions sheet');
    if (users.getMaxColumns() < 8 ||
        String(users.getRange(1, 8, 1, 1).getValues()[0][0]) !== '대출원금') {
      fail_('PRINCIPAL_NOT_READY', 'Users!H principal column missing; run installTransactionLedger()');
    }
    const headers = ledger.getRange(1, 1, 1, HEADERS.length).getValues()[0];
    if (JSON.stringify(headers) !== JSON.stringify(HEADERS)) {
      fail_('NOT_CONFIGURED', 'Transactions schema mismatch');
    }

    // Read-only capability and account probe: never changes a wallet or the ledger.
    // Clients call this BEFORE borrowing or betting, so an outdated deployment
    // cannot accidentally commit a transaction and then report it as a failure.
    if (tx.kind === 'status') {
      const account = findUser_(users, tx.student_id);
      return result_(balance_(account.values), null, false);
    }

    const previous = findTransaction_(ledger, tx.transaction_id);
    if (previous) {
      const same = (tx.kind === 'register_teacher' ?
          isTeacherId_(sid_(previous[2])) : sid_(previous[2]) === tx.student_id) &&
        String(previous[3]) === tx.kind && String(previous[4]) === tx.game &&
        String(previous[5]) === tx.round_id &&
        (tx.bet === undefined || Number(previous[6]) === tx.bet) &&
        (tx.kind !== 'settle' || (
          previous[8] === request.is_win &&
          Number(previous[7]) === (request.is_win ? tx.bet * RULES[tx.game] :
            -(tx.game === 'game_3' ? Math.floor(tx.bet / 2) : tx.bet))
        )) &&
        (!['borrow', 'repay'].includes(tx.kind) || Number(previous[7]) ===
          (tx.kind === 'borrow' ? tx.amount : -tx.amount));
      if (!same) fail_('IDEMPOTENCY_CONFLICT', 'Transaction ID already used with different arguments');
      const accountId = tx.kind === 'register_teacher' ? sid_(previous[2]) : tx.student_id;
      const current = findUser_(users, accountId);
      if (tx.kind === 'register' || tx.kind === 'register_teacher') {
        const expectedReferrer = tx.kind === 'register_teacher' ? '' : sid_(request.referrer_id || '');
        if (String(current.values[1]) !== String(request.nickname || '').trim() ||
            String(current.values[5]) !== String(request.password || '') ||
            sid_(current.values[4]) !== expectedReferrer) {
          fail_('IDEMPOTENCY_CONFLICT', 'Registration retry details differ');
        }
      }
      const replay = result_(balance_(current.values), previous, true);
      return tx.kind === 'register_teacher' ?
        Object.assign(replay, {student_id: accountId}) : replay;
    }

    if (tx.kind === 'register' || tx.kind === 'register_teacher') {
      const teacher = tx.kind === 'register_teacher';
      if (teacher) {
        if (sid_(request.referrer_id || '')) {
          fail_('INVALID_REQUEST', 'Teacher registration cannot include a referral');
        }
        tx.student_id = nextTeacherId_(users);
      } else {
        if (!isStudentId_(tx.student_id)) fail_('INVALID_STUDENT_ID', 'Invalid school student ID');
        if (findExisting_(users, tx.student_id)) fail_('ALREADY_REGISTERED', 'Player exists');
      }
      const nickname = nickname_(request.nickname);
      const password = String(request.password || '');
      if (!password || password.length > 200) {
        fail_('INVALID_REQUEST', 'Invalid registration credentials');
      }
      const referrerId = teacher ? '' : sid_(request.referrer_id || '');
      const ref = !teacher && isStudentId_(referrerId) && referrerId !== tx.student_id ?
        findExisting_(users, referrerId) : null;
      const bonus = ref ? 1000 : 0;
      const starting = {coins: 5000 + bonus, streak: 0, loan: 0, principal: 0};
      const empty = {coins: 0, streak: 0, loan: 0, principal: 0};
      const requests = [
        append_(users, [[tx.student_id, nickname, starting.coins, 0, referrerId, password, 0, 0]])
      ];
      const logs = [record_(tx, empty, starting, 'registration')];
      if (ref) {
        const prior = balance_(ref.values);
        const next = {coins: prior.coins + 3000, streak: prior.streak, loan: prior.loan, principal: prior.principal};
        requests.push.apply(requests, walletUpdate_(users, ref.rowIndex, next));
        logs.push(record_({
          transaction_id: 'referrer:' + tx.transaction_id.split(':')[1],
          student_id: referrerId, kind: 'referrer', delta: 3000
        }, prior, next, 'referral:' + tx.student_id));
      }
      requests.push(append_(ledger, logs));
      commit_(ss, requests);
      const result = result_(starting, logs[0], false);
      return teacher ? Object.assign(result, {student_id: tx.student_id}) : result;
    }

    const user = findUser_(users, tx.student_id);
    const before = balance_(user.values);
    const after = {
      coins: before.coins, streak: before.streak,
      loan: before.loan, principal: before.principal
    };
    if (tx.kind === 'bet') {
      if (before.coins < tx.bet) fail_('INSUFFICIENT_FUNDS', 'Insufficient coins', before);
    } else if (tx.kind === 'settle') {
      const confirmation = findTransaction_(ledger, 'bet:' + tx.round_id);
      if (!confirmation || sid_(confirmation[2]) !== tx.student_id ||
          String(confirmation[4]) !== tx.game || Number(confirmation[6]) !== tx.bet) {
        fail_('UNCONFIRMED_BET', 'No matching bet confirmation');
      }
      if (before.coins < tx.bet) fail_('INSUFFICIENT_FUNDS', 'Insufficient coins at settlement', before);
      tx.is_win = request.is_win;
      tx.delta = tx.is_win ? tx.bet * RULES[tx.game] :
        -(tx.game === 'game_3' ? Math.floor(tx.bet / 2) : tx.bet);
      after.coins += tx.delta;
      after.streak = tx.is_win ? before.streak + 1 : 0;
    } else if (tx.kind === 'interest') {
      const settled = findTransaction_(ledger, 'settle:' + tx.round_id);
      if (!settled || sid_(settled[2]) !== tx.student_id ||
          String(settled[3]) !== 'settle' || String(settled[4]) !== tx.game ||
          String(settled[5]) !== tx.round_id) {
        fail_('UNSETTLED_ROUND', 'No matching settled round');
      }
      // Record even a zero-debt turn, so replaying this result after borrowing
      // later cannot retroactively charge interest to an already ended round.
      const charged = turnInterest_(before.loan);
      if (charged > Number.MAX_SAFE_INTEGER - before.loan) {
        fail_('INVALID_REQUEST', 'Loan balance overflow');
      }
      after.loan += charged;
    } else {
      const expectedCoins = number_(request.expected_coins, 'expected_coins');
      const expectedLoan = number_(request.expected_loan, 'expected_loan');
      const expectedPrincipal = number_(request.expected_principal, 'expected_principal');
      if (before.coins !== expectedCoins || before.loan !== expectedLoan ||
          before.principal !== expectedPrincipal) {
        fail_('STALE_BALANCE', 'Balance has changed', before);
      }
      if (tx.kind === 'borrow') {
        if (tx.amount % 1000 !== 0 || tx.amount > MAX_PRINCIPAL - after.principal) {
          fail_('INVALID_REQUEST', 'Borrowed principal limit exceeded');
        }
        after.coins += tx.amount;
        after.loan += tx.amount;
        after.principal += tx.amount;
        tx.delta = tx.amount;
      } else if (tx.kind === 'repay') {
        if (after.coins < tx.amount || after.loan < tx.amount ||
            (tx.amount % 1000 !== 0 && tx.amount !== after.loan)) {
          fail_('INVALID_REQUEST', 'Invalid repayment');
        }
        after.coins -= tx.amount;
        after.loan -= tx.amount;
        // Repay accrued interest first; any leftover reduces borrowed principal.
        after.principal = Math.min(before.principal, after.loan);
        tx.delta = -tx.amount;
      }
    }
    if (!Number.isSafeInteger(after.coins) || !Number.isSafeInteger(after.streak) ||
        !Number.isSafeInteger(after.loan) || !Number.isSafeInteger(after.principal) ||
        after.principal < 0 || after.principal > after.loan) {
      fail_('INVALID_REQUEST', 'Balance or principal overflow');
    }
    const detail = tx.kind === 'interest' ?
      'turn-end compound interest ' + TURN_INTEREST_RATE_PERCENT + '%; round up to 1C' : '';
    const row = record_(tx, before, after, detail);
    const requests = tx.kind === 'bet' ? [] : walletUpdate_(users, user.rowIndex, after);
    requests.push(append_(ledger, [row]));
    commit_(ss, requests);
    return result_(after, row, false);
  } finally {
    lock.releaseLock();
  }
}

function findExisting_(users, sid) {
  if (!sid || users.getLastRow() < 2) return null;
  const values = users.getRange(2, 1, users.getLastRow() - 1, 8).getValues();
  let found = null;
  values.forEach(function (row, i) {
    if (sid_(row[0]) === sid) {
      if (found) fail_('DUPLICATE_USER', 'Duplicate student ID');
      found = {rowIndex: i + 1, values: row};
    }
  });
  return found;
}

function doPost(e) {
  let response;
  try {
    response = process_(JSON.parse(e.postData.contents));
  } catch (error) {
    response = {
      ok: false,
      code: error.code || 'SERVICE_ERROR',
      error: error.code ? error.message : 'Transaction service failed',
      balances: error.balances || null
    };
    console.error(String(error));
  }
  return ContentService.createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}
