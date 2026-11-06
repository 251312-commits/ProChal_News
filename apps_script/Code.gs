/**
 * Serialized Google Sheets wallet ledger for ProChal News.
 *
 * Deploy as a Web App (execute as owner; access Anyone). Set Script Properties
 * SPREADSHEET_ID and TRANSACTION_TOKEN, enable the advanced Google Sheets API,
 * and run installTransactionLedger() once before deployment.
 *
 * Every wallet mutation MUST use this gateway. Editing Users!C/D/G outside it
 * bypasses LockService and defeats its concurrency guarantee.
 */
const USER_TAB = 'Users';
const LEDGER_TAB = 'Transactions';
const HEADERS = [
  'transaction_id', 'timestamp', 'student_id', 'kind', 'game', 'round_id',
  'bet', 'coin_delta', 'is_win', 'coins_before', 'coins_after',
  'streak_before', 'streak_after', 'loan_before', 'loan_after', 'detail'
];
const RULES = {game_1: 100, game_2: 1, game_3: 1, game_4: 2, game_5: 5};
const MAX_LOAN = 10000;

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
  const rows = users.getRange(2, 1, users.getLastRow() - 1, 7).getValues();
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
  return {
    coins: number_(values[2], 'coins', 0),
    streak: number_(values[3], 'streak', 0),
    loan: number_(values[6], 'loan', 0)
  };
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
      rows: [{values: [cell_(balance.loan)]}],
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
    replayed: replayed,
    balances: balances,
    settlement: row ? {
      coins: number_(row[10], 'coins_after'),
      streak: number_(row[12], 'streak_after'),
      loan: number_(row[14], 'loan_after'),
      delta: Number(row[7]),
      is_win: row[8] === true
    } : null
  };
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
  if (!/^(bet|settle|borrow|repay|register):[a-f0-9]{32}$/.test(tx.transaction_id) ||
      !/^\d{5}$/.test(tx.student_id) ||
      !['bet', 'settle', 'borrow', 'repay', 'register'].includes(tx.kind) ||
      tx.transaction_id.split(':', 1)[0] !== tx.kind) {
    fail_('INVALID_REQUEST', 'Invalid transaction ID, student ID, or operation');
  }
  if (tx.kind === 'bet' || tx.kind === 'settle') {
    if (!Object.prototype.hasOwnProperty.call(RULES, tx.game) ||
        !/^[a-f0-9]{32}$/.test(tx.round_id) ||
        tx.transaction_id !== tx.kind + ':' + tx.round_id) {
      fail_('INVALID_REQUEST', 'Invalid game or round');
    }
    tx.bet = number_(request.bet, 'bet', 1000);
    if ((tx.bet - 1000) % 50 !== 0) fail_('INVALID_REQUEST', 'Bet must use 50C steps');
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
    const headers = ledger.getRange(1, 1, 1, HEADERS.length).getValues()[0];
    if (JSON.stringify(headers) !== JSON.stringify(HEADERS)) {
      fail_('NOT_CONFIGURED', 'Transactions schema mismatch');
    }

    const previous = findTransaction_(ledger, tx.transaction_id);
    if (previous) {
      const same = sid_(previous[2]) === tx.student_id &&
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
      const current = findUser_(users, tx.student_id);
      return result_(balance_(current.values), previous, true);
    }

    if (tx.kind === 'register') {
      if (findExisting_(users, tx.student_id)) fail_('ALREADY_REGISTERED', 'Player exists');
      const nickname = String(request.nickname || '').trim();
      const password = String(request.password || '');
      if (!nickname || !password || nickname.length > 80 || password.length > 200) {
        fail_('INVALID_REQUEST', 'Invalid registration credentials');
      }
      const referrerId = sid_(request.referrer_id || '');
      const ref = referrerId && referrerId !== tx.student_id ?
        findExisting_(users, referrerId) : null;
      const bonus = ref ? 1000 : 0;
      const starting = {coins: 5000 + bonus, streak: 0, loan: 0};
      const empty = {coins: 0, streak: 0, loan: 0};
      const requests = [
        append_(users, [[tx.student_id, nickname, starting.coins, 0, referrerId, password, 0]])
      ];
      const logs = [record_(tx, empty, starting, 'registration')];
      if (ref) {
        const prior = balance_(ref.values);
        const next = {coins: prior.coins + 3000, streak: prior.streak, loan: prior.loan};
        requests.push.apply(requests, walletUpdate_(users, ref.rowIndex, next));
        logs.push(record_({
          transaction_id: 'referrer:' + tx.transaction_id.split(':')[1],
          student_id: referrerId, kind: 'referrer', delta: 3000
        }, prior, next, 'referral:' + tx.student_id));
      }
      requests.push(append_(ledger, logs));
      commit_(ss, requests);
      return result_(starting, logs[0], false);
    }

    const user = findUser_(users, tx.student_id);
    const before = balance_(user.values);
    const after = {coins: before.coins, streak: before.streak, loan: before.loan};
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
    } else {
      const expectedCoins = number_(request.expected_coins, 'expected_coins');
      const expectedLoan = number_(request.expected_loan, 'expected_loan');
      if (before.coins !== expectedCoins || before.loan !== expectedLoan) {
        fail_('STALE_BALANCE', 'Balance has changed', before);
      }
      if (tx.kind === 'borrow') {
        if (tx.amount % 1000 !== 0 || after.loan + tx.amount > MAX_LOAN) {
          fail_('INVALID_REQUEST', 'Borrowing limit exceeded');
        }
        after.coins += tx.amount;
        after.loan += tx.amount;
        tx.delta = tx.amount;
      } else if (tx.kind === 'repay') {
        if (after.coins < tx.amount || after.loan < tx.amount ||
            (tx.amount % 1000 !== 0 && tx.amount !== after.loan)) {
          fail_('INVALID_REQUEST', 'Invalid repayment');
        }
        after.coins -= tx.amount;
        after.loan -= tx.amount;
        tx.delta = -tx.amount;
      }
    }
    if (!Number.isSafeInteger(after.coins) || !Number.isSafeInteger(after.streak) ||
        !Number.isSafeInteger(after.loan)) fail_('INVALID_REQUEST', 'Balance overflow');
    const row = record_(tx, before, after, '');
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
  const values = users.getRange(2, 1, users.getLastRow() - 1, 7).getValues();
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
