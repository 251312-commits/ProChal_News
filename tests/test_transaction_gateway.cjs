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
    users: [
      ['학번', '아이디', '코인', '연승', '추천인', '비밀번호', '대출금', '대출원금'],
      ...usersRows.map(r => r.length >= 8 ? [...r] : [...r, r[6] === '' || r[6] == null ? 0 : r[6]]),
    ],
    ledger: [headers],
  };
  function fakeSheet(id) {
    return {
      getSheetId() {return id;},
      getLastRow() {return rows[id].length;},
      getMaxColumns() {return rows[id][0].length;},
      insertColumnsAfter(index, count) {
        rows[id].forEach(row => row.splice(index, 0, ...Array(count).fill('')));
      },
      getRange(startRow, startCol, numberRows = 1, numberCols = 1) {
        return {
          getValues() {
            return Array.from({length: numberRows}, (_, i) =>
              Array.from({length: numberCols}, (_, j) =>
                rows[id][startRow - 1 + i]?.[startCol - 1 + j] ?? ''));
          },
          setValues(values) {
            for (let i = 0; i < numberRows; i++) {
              for (let j = 0; j < numberCols; j++) {
                rows[id][startRow - 1 + i][startCol - 1 + j] = values[i][j];
              }
            }
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
    install() {
      return ctx.installPrincipalColumn_(sheetObjects.users, sheetObjects.ledger);
    },
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
    expected_coins:5000,expected_loan:0,expected_principal:0});
  assert.equal(first.balances.coins, 8000);
  assert.equal(first.balances.loan, 3000);
  assert.equal(first.balances.principal, 3000);
  assert.equal(e.rows.users[1][7], 3000);
  assert.throws(() => e.call({kind:'borrow',transaction_id:'borrow:'+hex('b'),
    amount:1000,expected_coins:5000,expected_loan:0,expected_principal:0}), /Balance has changed/);
  const after = e.call({kind:'repay',transaction_id:'repay:'+hex('c'),
    amount:1000,expected_coins:8000,expected_loan:3000,expected_principal:3000});
  assert.equal(after.balances.coins, 7000);
  assert.equal(after.balances.loan, 2000);
  assert.equal(after.balances.principal, 2000);
  assert.equal(e.rows.users[1][7], 2000);
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
    amount:1000,expected_coins:5000,expected_loan:0,expected_principal:0}), /Simulated/);
  assert.equal(e.rows.users[1][2], 5000);
  assert.equal(e.rows.users[1][6], 0);
  assert.equal(e.rows.ledger.length, 1);
  assert.equal(e.state.locked, false);
});

test('legacy blank streak and debt columns behave as zero', () => {
  const e = environment([['11011','Alice',5000,'','','pw','']]);
  const id = hex('e');
  const res = e.call({kind:'bet',transaction_id:'bet:'+id,
    round_id:id,game:'game_2',bet:1000});
  assert.equal(res.balances.streak, 0);
  assert.equal(res.balances.loan, 0);
  const won = e.call({kind:'settle',transaction_id:'settle:'+id,
    round_id:id,game:'game_2',bet:1000,is_win:true});
  assert.equal(won.balances.coins, 6000);
  assert.equal(won.balances.streak, 1);
  assert.equal(e.rows.users[1][6], 0);
});

test('settlement rejects a different player or unconfirmed round', () => {
  const e = environment([['11011','Alice',5000,1,'','pw',0], ['22022','Bob',5000,0,'','pw',0]]);
  const id = hex('f');
  e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_5',bet:1000});
  assert.throws(() => e.call({kind:'settle',transaction_id:'settle:'+id,
    round_id:id,game:'game_5',bet:1000,is_win:true,student_id:'22022'}), /No matching bet/);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 0);
});


test('turn-end interest compounds 20% once per settled round and never changes coins', () => {
  const e = environment([['11011', 'Alice', 5000, 1, '', 'pw', 1000]]);
  const round = hex('1');
  const confirm = id => e.call({
    kind: 'bet', transaction_id: 'bet:' + id, round_id: id, game: 'game_2', bet: 1000,
  });
  const settle = id => e.call({
    kind: 'settle', transaction_id: 'settle:' + id, round_id: id,
    game: 'game_2', bet: 1000, is_win: true,
  });
  const interest = id => e.call({
    kind: 'interest', transaction_id: 'interest:' + id, round_id: id, game: 'game_2',
  });
  confirm(round);
  settle(round);
  const coins = e.rows.users[1][2];
  const streak = e.rows.users[1][3];
  const first = interest(round);
  assert.equal(first.interest.charged, 200);
  assert.equal(first.interest.loan_before, 1000);
  assert.equal(first.interest.loan_after, 1200);
  assert.equal(e.rows.users[1][6], 1200);
  assert.equal(e.rows.users[1][2], coins);
  assert.equal(e.rows.users[1][3], streak);
  assert.equal(first.settlement, null);
  const batches = e.state.batches;
  const replay = interest(round);
  assert.equal(replay.replayed, true);
  assert.equal(replay.interest.charged, 200);
  assert.equal(e.state.batches, batches);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'interest').length, 1);
  const next = hex('2');
  confirm(next);
  settle(next);
  const second = interest(next);
  assert.equal(second.interest.charged, 240);
  assert.equal(second.interest.loan_after, 1440);
  assert.equal(e.rows.users[1][6], 1440);
});

test('interest only applies to a matching settled player/game/round', () => {
  const e = environment([['11011','Alice',5000,0,'','pw',1000],
    ['22022','Bob',5000,0,'','pw',1000]]);
  const id = hex('3');
  const request = {kind: 'interest', transaction_id: 'interest:' + id,
    round_id: id, game: 'game_1'};
  assert.throws(() => e.call(request), /No matching settled round/);
  e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id, game: 'game_1', bet: 1000});
  assert.throws(() => e.call(request), /No matching settled round/);
  e.call({kind: 'settle', transaction_id: 'settle:' + id,
    round_id: id, game: 'game_1', bet: 1000, is_win: false});
  assert.throws(() => e.call({...request, student_id: '22022'}), /No matching settled round/);
  assert.throws(() => e.call({...request, game: 'game_2'}), /No matching settled round|Invalid game/);
  const receipt = e.call(request);
  assert.equal(receipt.interest.loan_after, 1200);
});

test('zero-debt turn records an idempotent receipt even if player borrows later', () => {
  const e = environment();
  const id = hex('4');
  e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id, game: 'game_2', bet: 1000});
  e.call({kind: 'settle', transaction_id: 'settle:' + id,
    round_id: id, game: 'game_2', bet: 1000, is_win: true});
  const request = {kind: 'interest', transaction_id: 'interest:' + id,
    round_id: id, game: 'game_2'};
  const first = e.call(request);
  assert.equal(first.interest.charged, 0);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'interest').length, 1);
  e.call({kind: 'borrow', transaction_id: 'borrow:' + hex('5'),
    amount: 1000, expected_coins: 6000, expected_loan: 0, expected_principal: 0});
  const replay = e.call(request);
  assert.equal(replay.replayed, true);
  assert.equal(replay.interest.loan_after, 0);
  assert.equal(replay.balances.loan, 1000);
  assert.equal(e.rows.users[1][6], 1000);
});

test('fractional interest rounds up and failed atomic batch is safely retryable', () => {
  const e = environment([['11011','Alice',5000,0,'','pw',3]]);
  const id = hex('6');
  e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_2',bet:1000});
  e.call({kind:'settle',transaction_id:'settle:'+id,
    round_id:id,game:'game_2',bet:1000,is_win:false});
  const request = {kind:'interest',transaction_id:'interest:'+id,round_id:id,game:'game_2'};
  e.state.failedBatch = true;
  assert.throws(() => e.call(request), /Simulated atomic batch failure/);
  assert.equal(e.rows.users[1][6], 3);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'interest').length, 0);
  assert.equal(e.state.locked, false);
  e.state.failedBatch = false;
  const result = e.call(request);
  assert.equal(result.interest.charged, 1);
  assert.equal(result.interest.loan_after, 4);
  assert.equal(e.rows.users[1][6], 4);
});


test('8000 borrowed + 1600 interest still permits 2000 new borrowing', () => {
  const e = environment([['11011','Alice',5000,0,'','pw',8000]]);
  const id = hex('7');
  e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_2',bet:1000});
  e.call({kind:'settle',transaction_id:'settle:'+id,round_id:id,
    game:'game_2',bet:1000,is_win:true});
  const interest = e.call({kind:'interest',transaction_id:'interest:'+id,round_id:id,game:'game_2'});
  assert.equal(interest.balances.loan, 9600);
  assert.equal(interest.balances.principal, 8000);
  const more = e.call({kind:'borrow',transaction_id:'borrow:'+hex('8'),amount:2000,
    expected_coins:6000,expected_loan:9600,expected_principal:8000});
  assert.equal(more.balances.coins, 8000);
  assert.equal(more.balances.loan, 11600);
  assert.equal(more.balances.principal, 10000);
  assert.equal(e.rows.users[1][6], 11600);
  assert.equal(e.rows.users[1][7], 10000);
  assert.throws(() => e.call({kind:'borrow',transaction_id:'borrow:'+hex('9'),
    amount:1000,expected_coins:8000,expected_loan:11600,expected_principal:10000}),
  /Borrowed principal limit exceeded/);
});

test('interest can raise total debt past cap; repayments pay interest first', () => {
  const e = environment([['11011','Alice',10000,0,'','pw',10000]]);
  const id = hex('a');
  e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_2',bet:1000});
  e.call({kind:'settle',transaction_id:'settle:'+id,round_id:id,
    game:'game_2',bet:1000,is_win:false});
  const turn = e.call({kind:'interest',transaction_id:'interest:'+id,round_id:id,game:'game_2'});
  assert.equal(turn.balances.loan, 12000);
  assert.equal(turn.balances.principal, 10000);
  const interestRepay = e.call({kind:'repay',transaction_id:'repay:'+hex('b'),
    amount:1000,expected_coins:9000,expected_loan:12000,expected_principal:10000});
  assert.equal(interestRepay.balances.loan, 11000);
  assert.equal(interestRepay.balances.principal, 10000);
  const principalRepay = e.call({kind:'repay',transaction_id:'repay:'+hex('c'),
    amount:3000,expected_coins:8000,expected_loan:11000,expected_principal:10000});
  assert.equal(principalRepay.balances.loan, 8000);
  assert.equal(principalRepay.balances.principal, 8000);
  const borrow = e.call({kind:'borrow',transaction_id:'borrow:'+hex('d'),
    amount:2000,expected_coins:5000,expected_loan:8000,expected_principal:8000});
  assert.equal(borrow.balances.principal, 10000);
  assert.equal(borrow.balances.loan, 10000);
});

test('installer restores principal from recorded interest, not inflated total G', () => {
  const e = environment([['11011','Alice',5000,0,'','pw',8000]]);
  const id = hex('e');
  e.call({kind:'bet',transaction_id:'bet:'+id,round_id:id,game:'game_2',bet:1000});
  e.call({kind:'settle',transaction_id:'settle:'+id,round_id:id,
    game:'game_2',bet:1000,is_win:false});
  e.call({kind:'interest',transaction_id:'interest:'+id,round_id:id,game:'game_2'});
  assert.equal(e.rows.users[1][6], 9600);
  e.rows.users[0][7] = '';
  e.rows.users[1][7] = '';
  e.install();
  assert.equal(e.rows.users[0][7], '대출원금');
  assert.equal(e.rows.users[1][6], 9600);
  assert.equal(e.rows.users[1][7], 8000);
  e.install(); // idempotent
  assert.equal(e.rows.users[1][7], 8000);
});

test('installer backfills legacy debt and refuses an occupied H column', () => {
  const e = environment([['11011','Alice',5000,0,'','pw',3000]]);
  e.rows.users[0].pop();
  e.rows.users[1].pop();
  e.install();
  assert.equal(e.rows.users[1][6], 3000);
  assert.equal(e.rows.users[1][7], 3000);
  e.rows.users[0][7] = 'another column';
  assert.throws(() => e.install(), /Users!H is in use/);
});


test('registration rejects HTML, entity and spreadsheet-injection nicknames', () => {
  const e = environment([]);
  const invalid = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '&lt;script&gt;',
    'Alice" onclick="evil()',
    '=IMPORTXML("http://example.com")',
    'a\nb',
    'a/b',
    '   ',
    'x'.repeat(81),
  ];
  for (const [i, nickname] of invalid.entries()) {
    assert.throws(() => e.call({
      kind: 'register', transaction_id: 'register:' + (i + 1).toString(16).repeat(32),
      student_id: String(30000 + i), nickname, password: 'pw', referrer_id: '',
    }), error => error.code === 'INVALID_NICKNAME', nickname);
  }
  assert.equal(e.rows.users.length, 1);
  assert.equal(e.rows.ledger.length, 1);
  assert.equal(e.state.batches, 0);
});

test('registration accepts normal Korean, alphanumeric and spaced nicknames', () => {
  const e = environment([]);
  const valid = ['안닢', 'Student_01', '김 철수', 'Mina-02.'];
  for (const [i, nickname] of valid.entries()) {
    e.call({
      kind: 'register', transaction_id: 'register:' + (i + 1).toString(16).repeat(32),
      student_id: String(40000 + i), nickname, password: 'pw', referrer_id: '',
    });
  }
  assert.deepEqual(e.rows.users.slice(1).map(row => row[1]), valid);
});
