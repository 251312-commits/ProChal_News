/* Apps Script contract tests in a simulated Sheets/LockService environment. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const script = fs.readFileSync(path.join(__dirname, '..', 'apps_script', 'Code.gs'), 'utf8');
const headers = [
  'transaction_id', 'timestamp', 'student_id', 'kind', 'game', 'round_id',
  'bet', 'coin_delta', 'is_win', 'coins_before', 'coins_after',
  'streak_before', 'streak_after', 'loan_before', 'loan_after', 'detail'
];
const hex = char => char.repeat(32);

function environment(usersRows = [['11011', 'Alice', 5000, 1, '', 'pw', 0]]) {
  const state = {failedBatch: false, batches: 0, locked: false};
  const rows = {
    users: [['학번', '아이디', '코인', '연승', '추천인', '비밀번호', '대출금'], ...usersRows.map(r => [...r])],
    ledger: [headers],
  };
  function fakeSheet(id) {
    return {
      getSheetId() {return id;},
      getLastRow() {return rows[id].length;},
      getRange(startRow, startCol, numberRows = 1, numberCols = 1) {
        return {
          getValues() {
            return Array.from({length: numberRows}, (_, i) =>
              Array.from({length: numberCols}, (_, j) =>
                rows[id][startRow - 1 + i]?.[startCol - 1 + j] ?? ''));
          },
        };
      },
    };
  }
  const sheetObjects = {users: fakeSheet('users'), ledger: fakeSheet('ledger')};
  const ss = {
    getSheetByName(name) {
      return name === 'Users' ? sheetObjects.users :
        name === 'Transactions' ? sheetObjects.ledger : null;
    },
    getId() {return 'test-spreadsheet';},
  };
  const ctx = {
    SpreadsheetApp: {openById: () => ss},
    PropertiesService: {getScriptProperties: () => ({
      getProperty(name) {
        return {SPREADSHEET_ID: 'test-spreadsheet', TRANSACTION_TOKEN: 'secret'}[name];
      },
    })},
    LockService: {getScriptLock: () => ({
      tryLock() {
        if (state.locked) return false;
        state.locked = true;
        return true;
      },
      releaseLock() {state.locked = false;},
    })},
    Sheets: {Spreadsheets: {batchUpdate(batch, id) {
      assert.equal(id, 'test-spreadsheet');
      if (state.failedBatch) throw new Error('Simulated atomic batch failure');
      const snapshot = {
        users: rows.users.map(r => [...r]),
        ledger: rows.ledger.map(r => [...r]),
      };
      const value = cell => cell.userEnteredValue.numberValue ??
        cell.userEnteredValue.boolValue ?? cell.userEnteredValue.stringValue;
      for (const request of batch.requests) {
        if (request.updateCells) {
          const u = request.updateCells;
          u.rows.forEach((row, idx) => {
            const target = snapshot[u.start.sheetId][u.start.rowIndex + idx];
            assert.ok(target, 'existing row for update');
            row.values.forEach((cell, col) => {
              target[u.start.columnIndex + col] = value(cell);
            });
          });
        } else if (request.appendCells) {
          const a = request.appendCells;
          a.rows.forEach(row => snapshot[a.sheetId].push(row.values.map(value)));
        } else throw new Error('Unknown Sheets update');
      }
      rows.users = snapshot.users;
      rows.ledger = snapshot.ledger;
      state.batches++;
    }}},
    console: {error() {}},
  };
  vm.createContext(ctx);
  vm.runInContext(script, ctx, {filename: 'Code.gs'});
  return {
    rows, state,
    call(payload) {
      return ctx.process_({token: 'secret', student_id: '11011', ...payload});
    },
  };
}

test('settlement is atomic and exact duplicate does not pay twice', () => {
  const e = environment(), id = hex('a');
  e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_1',bet:1000});
  const request = {kind:'settle',transaction_id:'settle:'+id,round_id:id,
    game:'game_1',bet:1000,is_win:true};
  const first = e.call(request);
  assert.equal(first.balances.coins, 105000);
  assert.equal(first.balances.streak, 2);
  assert.equal(e.rows.users[1][2], 105000);
  assert.equal(e.rows.ledger.length, 3);
  const again = e.call(request);
  assert.equal(again.replayed, true);
  assert.equal(again.settlement.delta, 100000);
  assert.equal(e.rows.ledger.length, 3);
  assert.equal(e.state.batches, 2);
  assert.throws(() => e.call({...request,is_win:false}), /different arguments/);
  assert.equal(e.rows.users[1][2], 105000);
});

test('two tabs cannot both spend the same wallet balance', () => {
  const e = environment(), ids = [hex('a'), hex('b')];
  for (const id of ids) {
    e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_2',bet:5000});
  }
  e.call({kind:'settle',transaction_id:'settle:'+ids[0],round_id:ids[0],
    game:'game_2',bet:5000,is_win:false});
  assert.equal(e.rows.users[1][2], 0);
  assert.throws(() => e.call({kind:'settle',transaction_id:'settle:'+ids[1],
    round_id:ids[1],game:'game_2',bet:5000,is_win:false}), /Insufficient coins/);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1);
});

test('borrow and repay revalidate expected values under the lock', () => {
  const e = environment();
  const first = e.call({kind:'borrow',transaction_id:'borrow:'+hex('a'),amount:3000,
    expected_coins:5000,expected_loan:0});
  assert.equal(first.balances.coins, 8000);
  assert.equal(first.balances.loan, 3000);
  assert.throws(() => e.call({kind:'borrow',transaction_id:'borrow:'+hex('b'),
    amount:1000,expected_coins:5000,expected_loan:0}), /Balance has changed/);
  const after = e.call({kind:'repay',transaction_id:'repay:'+hex('c'),
    amount:1000,expected_coins:8000,expected_loan:3000});
  assert.equal(after.balances.coins, 7000);
  assert.equal(after.balances.loan, 2000);
  assert.equal(e.rows.ledger.length, 3);
});

test('registration and referrer bonuses commit in one batch and retry once', () => {
  const e = environment([['22022', 'Bob', 4000, 0, '', 'pw', 0]]);
  const request = {kind:'register',transaction_id:'register:'+hex('d'),
    student_id:'33033',nickname:'Cathy',password:'pass',referrer_id:'22022'};
  const r = e.call(request);
  assert.equal(r.balances.coins, 6000);
  assert.equal(e.rows.users.find(row => row[0] === '33033')[2], 6000);
  assert.equal(e.rows.users.find(row => row[0] === '22022')[2], 7000);
  assert.equal(e.rows.ledger.length, 3);
  const replay = e.call(request);
  assert.equal(replay.replayed, true);
  assert.throws(() => e.call({...request, password:'changed'}), /Registration retry details differ/);
  assert.equal(e.rows.ledger.length, 3);
  assert.equal(e.state.batches, 1);
});

test('failed batch leaves both Users and Transactions unchanged and releases lock', () => {
  const e = environment();
  e.state.failedBatch = true;
  assert.throws(() => e.call({kind:'borrow',transaction_id:'borrow:'+hex('a'),
    amount:1000,expected_coins:5000,expected_loan:0}), /Simulated/);
  assert.equal(e.rows.users[1][2], 5000);
  assert.equal(e.rows.users[1][6], 0);
  assert.equal(e.rows.ledger.length, 1);
  assert.equal(e.state.locked, false);
});

test('settlement rejects a different player or unconfirmed round', () => {
  const e = environment([['11011','Alice',5000,1,'','pw',0], ['22022','Bob',5000,0,'','pw',0]]);
  const id = hex('f');
  e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_5',bet:1000});
  assert.throws(() => e.call({kind:'settle',transaction_id:'settle:'+id,
    round_id:id,game:'game_5',bet:1000,is_win:true,student_id:'22022'}), /No matching bet/);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 0);
});
