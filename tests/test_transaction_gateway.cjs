/* Apps Script contract tests in a simulated Sheets/LockService environment. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const script = fs.readFileSync(path.join(__dirname, '..', 'apps_script', 'Code.gs'), 'utf8');
const badgeScript = fs.readFileSync(path.join(__dirname, '..', 'apps_script', 'Badges.gs'), 'utf8');
const headers = [
  'transaction_id', 'timestamp', 'student_id', 'kind', 'game', 'round_id',
  'bet', 'coin_delta', 'is_win', 'coins_before', 'coins_after',
  'streak_before', 'streak_after', 'loan_before', 'loan_after', 'detail'
];
const hex = char => char.repeat(32);

function environment(usersRows = [['11011', 'Alice', 5000, 1, '', 'pw', 0]], newsRows = []) {
  const state = {failedBatch: false, batches: 0, locked: false};
  const rows = {
    users: [
      ['학번', '아이디', '코인', '연승', '추천인', '비밀번호', '대출금', '대출원금', '마지막기사URL', '장착배지', '보유배지'],
      ...usersRows.map(r => {
        const row = r.length >= 8 ? [...r] : [...r, r[6] === '' || r[6] == null ? 0 : r[6]];
        return [...row.slice(0, 8), '', '0', ''];
      }),
    ],
    ledger: [headers],
    news: [
      ['URL', 'Count', 'Title', 'SubmittedBy', 'SubmittedByName',
        'SourceType', 'AddedAt', 'Active', 'URLHash'],
      ...newsRows.map(row => [...row]),
    ],
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
  const sheetObjects = {users: fakeSheet('users'), ledger: fakeSheet('ledger'), news: fakeSheet('news')};
  const ss = {
    getSheetByName(name) {
      return name === 'Users' ? sheetObjects.users :
        name === 'Transactions' ? sheetObjects.ledger :
        name === 'News' ? sheetObjects.news : null;
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
        news: rows.news.map(r => [...r]),
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
      rows.news = snapshot.news;
      state.batches++;
    }}},
    console: {error() {}},
  };
  vm.createContext(ctx);
  vm.runInContext(script, ctx, {filename: 'Code.gs'});
  vm.runInContext(badgeScript, ctx, {filename: 'Badges.gs'});
  return {
    rows, state,
    install() {
      return ctx.installPrincipalColumn_(sheetObjects.users, sheetObjects.ledger);
    },
    installBadges() {return ctx.installBadgeColumns();},
    evaluateBadges(events) {return ctx.evaluateBadgesFromSettlements_(events);},
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

test('repayment accepts 1C increments while borrowing still requires 1000C', () => {
  const e = environment([['11011', 'Alice', 2000, 0, '', 'pw', 1500, 1000]]);
  const oneCoin = {kind:'repay',transaction_id:'repay:'+hex('1'),
    amount:1,expected_coins:2000,expected_loan:1500,expected_principal:1000};
  const first = e.call(oneCoin);
  assert.equal(first.balances.coins, 1999);
  assert.equal(first.balances.loan, 1499);
  assert.equal(first.balances.principal, 1000); // interest is repaid first
  assert.equal(e.call(oneCoin).replayed, true);

  const part = e.call({kind:'repay',transaction_id:'repay:'+hex('2'),
    amount:500,expected_coins:1999,expected_loan:1499,expected_principal:1000});
  assert.equal(part.balances.coins, 1499);
  assert.equal(part.balances.loan, 999);
  assert.equal(part.balances.principal, 999);

  assert.throws(() => e.call({kind:'borrow',transaction_id:'borrow:'+hex('3'),
    amount:1,expected_coins:1499,expected_loan:999,expected_principal:999}),
  /Borrowed principal limit exceeded/);

  const paidOff = e.call({kind:'repay',transaction_id:'repay:'+hex('4'),
    amount:999,expected_coins:1499,expected_loan:999,expected_principal:999});
  assert.equal(paidOff.balances.coins, 500);
  assert.equal(paidOff.balances.loan, 0);
  assert.equal(paidOff.balances.principal, 0);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'repay').length, 3);
  assert.throws(() => e.call({kind:'repay',transaction_id:'repay:'+hex('5'),
    amount:1,expected_coins:500,expected_loan:0,expected_principal:0}),
  /Invalid repayment/);
});

test('registration and referrer bonuses commit in one batch and retry once', () => {
  const e = environment([['20102', 'Bob', 4000, 0, '', 'pw', 0]]);
  const request = {kind:'register',transaction_id:'register:'+hex('d'),
    student_id:'30103',nickname:'Cathy',password:'pass',referrer_id:'20102'};
  const r = e.call(request);
  assert.equal(r.balances.coins, 6000);
  assert.equal(e.rows.users.find(row => row[0] === '30103')[2], 6000);
  assert.equal(e.rows.users.find(row => row[0] === '20102')[2], 7000);
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
  assert.equal(won.balances.coins, 7000);
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
    amount: 1000, expected_coins: 7000, expected_loan: 0, expected_principal: 0});
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
    expected_coins:7000,expected_loan:9600,expected_principal:8000});
  assert.equal(more.balances.coins, 9000);
  assert.equal(more.balances.loan, 11600);
  assert.equal(more.balances.principal, 10000);
  assert.equal(e.rows.users[1][6], 11600);
  assert.equal(e.rows.users[1][7], 10000);
  assert.throws(() => e.call({kind:'borrow',transaction_id:'borrow:'+hex('9'),
    amount:1000,expected_coins:9000,expected_loan:11600,expected_principal:10000}),
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
      student_id: String(30100 + i), nickname, password: 'pw', referrer_id: '',
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
      student_id: String(10100 + i), nickname, password: 'pw', referrer_id: '',
    });
  }
  assert.deepEqual(e.rows.users.slice(1).map(row => row[1]), valid);
});


test('status probe returns gateway version and C/D/G/H without writing to sheets', () => {
  const e = environment([['11011', 'Alice', 5000, 2, '', 'pw', 9600, 8000]]);
  const result = e.call({kind: 'status', transaction_id: 'status:' + hex('9')});
  assert.equal(result.ok, true);
  assert.equal(result.gateway_version, 3);
  assert.equal(result.balances.coins, 5000);
  assert.equal(result.balances.streak, 2);
  assert.equal(result.balances.loan, 9600);
  assert.equal(result.balances.principal, 8000);
  assert.equal(result.settlement, null);
  assert.equal(result.interest, null);
  assert.equal(e.state.batches, 0);
  assert.equal(e.rows.ledger.length, 1);
  assert.equal(e.state.locked, false);
});

test('status probe flags missing principal column or uninitialized H', () => {
  const e = environment();
  const probe = {kind: 'status', transaction_id: 'status:' + hex('a')};
  e.rows.users[1][7] = '';
  assert.throws(() => e.call(probe), err => err.code === 'PRINCIPAL_NOT_READY');
  e.rows.users[1][7] = 0;
  e.rows.users[0][7] = '';
  assert.throws(() => e.call(probe), err => err.code === 'PRINCIPAL_NOT_READY');
  assert.equal(e.state.batches, 0);
  assert.equal(e.rows.ledger.length, 1);
});

test('status never changes principal or accrues a turn interest', () => {
  const e = environment([['11011','Alice',5000,0,'','pw',8000,8000]]);
  for (const suffix of ['b','c','d']) {
    e.call({kind:'status',transaction_id:'status:'+hex(suffix)});
  }
  assert.equal(e.rows.users[1][6], 8000);
  assert.equal(e.rows.users[1][7], 8000);
  assert.equal(e.rows.ledger.length, 1);
  assert.equal(e.state.batches, 0);
});


test('school IDs are checked before accepting a new student', () => {
  const e = environment([]);
  for (const [i, student_id] of
      ['10001','11001','10601','10120','40101','00101','99999'].entries()) {
    assert.throws(() => e.call({
      kind:'register', transaction_id:'register:'+(i+1).toString(16).repeat(32),
      student_id, nickname:'학생', password:'pw', referrer_id:'',
    }), err => err.code === 'INVALID_STUDENT_ID');
  }
  assert.equal(e.rows.users.length, 1);
  assert.equal(e.state.batches, 0);
});

test('different transaction IDs cannot duplicate a student account or referral', () => {
  const e = environment([['20102','Bob',4000,0,'','pw',0]]);
  const r = {kind:'register',transaction_id:'register:'+hex('a'),
    student_id:'10101',nickname:'학생',password:'pw',referrer_id:'20102'};
  e.call(r);
  assert.throws(() => e.call({...r,transaction_id:'register:'+hex('b')}),
    err => err.code === 'ALREADY_REGISTERED');
  assert.equal(e.rows.users.length, 3);
  assert.equal(e.rows.users[1][2], 7000);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'referrer').length, 1);
});

test('failed student registration is atomic and safe to retry', () => {
  const e = environment([['20102','Bob',4000,0,'','pw',0]]);
  const r = {kind:'register',transaction_id:'register:'+hex('c'),
    student_id:'10101',nickname:'학생',password:'pw',referrer_id:'20102'};
  e.state.failedBatch = true;
  assert.throws(() => e.call(r), /Simulated atomic batch failure/);
  assert.equal(e.rows.users.length, 2);
  assert.equal(e.rows.users[1][2], 4000);
  assert.equal(e.rows.ledger.length, 1);
  e.state.failedBatch = false;
  e.call(r);
  assert.equal(e.rows.users[1][2], 7000);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'register').length, 1);
});

test('teacher IDs are sequential and retries do not create another account', () => {
  const e = environment([['40101','Original',5000,0,'','pw',0]]);
  const r = {kind:'register_teacher',transaction_id:'register_teacher:'+hex('a'),
    student_id:'',nickname:'교사1',password:'pw',referrer_id:''};
  const first = e.call(r);
  assert.equal(first.student_id, '40102');
  assert.equal(first.balances.coins, 5000);
  const replay = e.call(r);
  assert.equal(replay.replayed, true);
  assert.equal(replay.student_id, '40102');
  const second = e.call({...r,transaction_id:'register_teacher:'+hex('b'),nickname:'교사2'});
  assert.equal(second.student_id, '40103');
  assert.equal(e.rows.users.length, 4);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'referrer').length, 0);
  assert.throws(() => e.call({...r,nickname:'바뀐이름'}),
    err => err.code === 'IDEMPOTENCY_CONFLICT');
  assert.equal(e.state.batches, 2);
});

test('teacher sequence starts at 40101 and continues past 40109', () => {
  const e = environment([]);
  const r = {kind:'register_teacher',transaction_id:'register_teacher:'+hex('a'),
    student_id:'',nickname:'교사',password:'pw',referrer_id:''};
  assert.equal(e.call(r).student_id, '40101');
  const other = environment([['40109','Older',5000,0,'','pw',0]]);
  assert.equal(other.call(r).student_id, '40110');
});

test('teacher registration accepts no custom ID or referral', () => {
  const e = environment([['40101','Teacher',5000,0,'','pw',0]]);
  const r = {kind:'register_teacher',transaction_id:'register_teacher:'+hex('a'),
    student_id:'',nickname:'교사',password:'pw',referrer_id:''};
  assert.throws(() => e.call({...r,student_id:'40102'}), err => err.code === 'INVALID_REQUEST');
  assert.throws(() => e.call({...r,referrer_id:'10101'}), err => err.code === 'INVALID_REQUEST');
  const student = e.call({kind:'register',transaction_id:'register:'+hex('b'),
    student_id:'10101',nickname:'학생',password:'pw',referrer_id:'40101'});
  assert.equal(student.balances.coins, 5000);
  assert.equal(e.rows.users[1][2], 5000);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'referrer').length, 0);
});

test('failed teacher registration does not consume the next ID', () => {
  const e = environment([]);
  const r = {kind:'register_teacher',transaction_id:'register_teacher:'+hex('a'),
    student_id:'',nickname:'교사',password:'pw',referrer_id:''};
  e.state.failedBatch = true;
  assert.throws(() => e.call(r), /Simulated atomic batch failure/);
  assert.equal(e.rows.users.length, 1);
  assert.equal(e.rows.ledger.length, 1);
  e.state.failedBatch = false;
  assert.equal(e.call(r).student_id, '40101');
  assert.equal(e.rows.ledger.length, 2);
});


test('new badge columns are required and installer does not replace unrelated data', () => {
  const e = environment();
  e.rows.users[0][9] = 'Other';
  assert.throws(() => e.installBadges(), /other headers/);
  e.rows.users[0][9] = '';
  e.rows.users[0][10] = '';
  e.rows.users[1][9] = 'some value';
  assert.throws(() => e.installBadges(), /data without badge headers/);
  e.rows.users[1][9] = '';
  assert.throws(() => e.call({
    kind: 'status', transaction_id: 'status:' + hex('f'),
  }), /Run installBadgeColumns/);
  e.installBadges();
  assert.equal(e.rows.users[0][9], '장착배지');
  assert.equal(e.rows.users[0][10], '보유배지');
  assert.equal(e.rows.users[1][9], '0');
  e.installBadges(); // rerun is safe
  assert.ok(e.call({kind:'status', transaction_id:'status:' + hex('e')}).ok);
});

test('game1 proof awards overlapping near-miss badges in the same coin batch', () => {
  const e = environment();
  const id = hex('8');
  e.call({kind:'bet', transaction_id:'bet:' + id, round_id:id, game:'game_1', bet:1000});
  const payload = {kind:'settle', transaction_id:'settle:' + id,
    round_id:id, game:'game_1', bet:1000, is_win:false,
    badge_evidence:{predicted_digits:37, answer_digits:36}};
  const result = e.call(payload);
  const expected = ['first_round', 'g1_within_ten', 'g1_within_three', 'g1_exact_one'];
  for (const name of expected) assert.ok(result.badges.unlocked.includes(name), name);
  assert.equal(e.rows.users[1][2], 4000);
  assert.equal(e.rows.users[1][9], '0');
  assert.equal(e.rows.users[1][10], expected.join(' '));
  assert.match(e.rows.ledger.at(-1)[15], /^badge-v1:/);
  assert.equal(e.state.batches, 2);
  const replay = e.call(payload);
  assert.equal(replay.replayed, true);
  assert.equal(e.state.batches, 2);
  assert.deepEqual([...replay.badges.unlocked], []);
  assert.throws(() => e.call({
    ...payload, badge_evidence:{predicted_digits:37, answer_digits:35},
  }), /proof changed on replay/);
  assert.equal(e.rows.users[1][10], expected.join(' '));
});

test('game1 exact hit needs proof and inconsistent evidence cannot pay coins', () => {
  const e = environment(), id = hex('9');
  e.call({kind:'bet', transaction_id:'bet:' + id, round_id:id, game:'game_1', bet:1000});
  const bad = {kind:'settle', transaction_id:'settle:' + id, round_id:id,
    game:'game_1', bet:1000, is_win:true,
    badge_evidence:{predicted_digits:31, answer_digits:32}};
  assert.throws(() => e.call(bad), /disagrees with win\/loss/);
  assert.equal(e.rows.users[1][2], 5000);
  assert.equal(e.rows.ledger.length, 2);
  const good = e.call({...bad, badge_evidence:{predicted_digits:32, answer_digits:32}});
  assert.ok(good.badges.unlocked.includes('g1_hit'));
  assert.equal(e.rows.users[1][2], 105000);
});

test('awards are included in an atomic settlement rollback', () => {
  const e = environment(), id = hex('7');
  e.call({kind:'bet', transaction_id:'bet:' + id, round_id:id, game:'game_5', bet:1000});
  e.state.failedBatch = true;
  assert.throws(() => e.call({kind:'settle',transaction_id:'settle:' + id,
    round_id:id,game:'game_5',bet:1000,is_win:true}), /Simulated/);
  assert.equal(e.rows.users[1][2], 5000);
  assert.equal(e.rows.users[1][10], '');
  assert.equal(e.rows.ledger.length, 2);
  e.state.failedBatch = false;
  const result = e.call({kind:'settle',transaction_id:'settle:' + id,
    round_id:id,game:'game_5',bet:1000,is_win:true});
  assert.ok(result.badges.unlocked.includes('first_round'));
});

test('multi-game streak condition excludes a single-game winning streak', () => {
  const e = environment();
  const single = Array.from({length:8}, (_, i) =>
    ({round_id:'x'+i, game:'game_2', is_win:true, evidence:{choice:'HIGH'}}));
  const a = e.evaluateBadges(single);
  assert.ok(a.includes('streak_three'));
  assert.ok(!a.includes('streak_five_mixed'));
  assert.ok(!a.includes('streak_eight_mixed'));
  const mixed = single.map((row,i) =>
    ({...row, game: ['game_2','game_3','game_4'][i % 3]}));
  const b = e.evaluateBadges(mixed);
  assert.ok(b.includes('streak_five_mixed'));
  assert.ok(b.includes('streak_eight_mixed'));
});


test('equipped badge is saved to Users J without touching coins, debts or ownership', () => {
  const e = environment();
  e.rows.users[1][10] = 'first_round g1_hit';
  const probe = e.call({kind:'status',transaction_id:'status:' + hex('1')});
  assert.equal(probe.badge_capabilities.equip, true);
  const beforeCoins = e.rows.users[1][2];
  const id = hex('a');
  const request = {kind:'equip',transaction_id:'equip:' + id,badge_id:'g1_hit'};
  const equipped = e.call(request);
  assert.equal(equipped.badges.equipped, 'g1_hit');
  assert.deepEqual([...equipped.badges.owned], ['first_round','g1_hit']);
  assert.equal(e.rows.users[1][9], 'g1_hit');
  assert.equal(e.rows.users[1][10], 'first_round g1_hit');
  assert.equal(e.rows.users[1][2], beforeCoins);
  assert.equal(e.rows.users[1][6], 0);
  assert.equal(e.rows.ledger.at(-1)[3], 'equip');
  assert.equal(e.rows.ledger.at(-1)[15], 'badge-equip:g1_hit');
  const writes = e.state.batches;
  const replay = e.call(request);
  assert.equal(replay.replayed, true);
  assert.equal(e.state.batches, writes);
  assert.throws(() => e.call({...request,badge_id:'first_round'}), /Equipped badge changed on replay/);
  assert.equal(e.rows.users[1][9], 'g1_hit');
});

test('equipping a locked badge fails safely, and 0 unequips without deleting earned badges', () => {
  const e = environment();
  e.rows.users[1][10] = 'first_round';
  assert.throws(
    () => e.call({kind:'equip',transaction_id:'equip:' + hex('b'),badge_id:'g1_hit'}),
    /Badge has not been earned/,
  );
  assert.equal(e.rows.ledger.length, 1);
  e.call({kind:'equip',transaction_id:'equip:' + hex('c'),badge_id:'first_round'});
  const unequipped = e.call({kind:'equip',transaction_id:'equip:' + hex('d'),badge_id:'0'});
  assert.equal(unequipped.badges.equipped, '0');
  assert.equal(e.rows.users[1][9], '0');
  assert.equal(e.rows.users[1][10], 'first_round');
  assert.throws(
    () => e.call({kind:'equip',transaction_id:'equip:' + hex('e'),badge_id:'fake'}),
    /Unknown badge identifier/,
  );
});

test('concurrent player badge ownership is isolated and equip batch is atomic', () => {
  const e = environment([['11011','Alice',5000,0,'','pw',0],
                         ['22022','Bob',5000,0,'','pw',0]]);
  e.rows.users[1][10] = 'first_round';
  e.rows.users[2][10] = 'g1_hit';
  e.state.failedBatch = true;
  assert.throws(() => e.call({
    kind:'equip', transaction_id:'equip:' + hex('1'), badge_id:'first_round',
  }), /Simulated atomic batch failure/);
  assert.equal(e.rows.users[1][9], '0');
  assert.equal(e.rows.ledger.length, 1);
  e.state.failedBatch = false;
  assert.throws(() => e.call({
    kind:'equip', transaction_id:'equip:' + hex('2'), student_id:'22022',
    badge_id:'first_round',
  }), /Badge has not been earned/);
  const saved = e.call({
    kind:'equip', transaction_id:'equip:' + hex('3'), student_id:'22022',
    badge_id:'g1_hit',
  });
  assert.equal(saved.badges.equipped, 'g1_hit');
  assert.equal(e.rows.users[1][9], '0');
  assert.equal(e.rows.users[2][9], 'g1_hit');
});


test('first successful borrowing and repayment earn Common badges exactly once', () => {
  const e = environment();
  const borrow = {kind:'borrow',transaction_id:'borrow:'+hex('a'),amount:1000,
    expected_coins:5000,expected_loan:0,expected_principal:0};
  const b = e.call(borrow);
  assert.ok(b.badges.unlocked.includes('first_borrow'));
  assert.equal(e.rows.users[1][10], 'first_borrow');
  assert.equal(e.call(borrow).replayed, true);
  const repay = {kind:'repay',transaction_id:'repay:'+hex('b'),amount:1,
    expected_coins:6000,expected_loan:1000,expected_principal:1000};
  const r = e.call(repay);
  assert.ok(r.badges.unlocked.includes('first_repay'));
  assert.equal(e.rows.users[1][10], 'first_borrow first_repay');
  assert.equal(e.call(repay).replayed, true);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'repay').length, 1);
});

test('bankruptcy requires both no minimum bet and no 1000C additional loan', () => {
  const bankrupt = environment([['11011','Alice',1000,0,'','pw',10000,10000]]);
  const round = hex('c');
  bankrupt.call({kind:'bet',transaction_id:'bet:'+round,round_id:round,game:'game_2',bet:1000});
  const result = bankrupt.call({kind:'settle',transaction_id:'settle:'+round,
    round_id:round,game:'game_2',bet:1000,is_win:false});
  assert.equal(result.balances.coins, 0);
  assert.ok(result.badges.unlocked.includes('bankrupt'));
  assert.ok(!result.badges.unlocked.includes('all_legendary'));
  assert.equal(bankrupt.rows.users[1][9], '0');

  const canBorrow = environment([['11011','Alice',1000,0,'','pw',9000,9000]]);
  const r2 = hex('d');
  canBorrow.call({kind:'bet',transaction_id:'bet:'+r2,round_id:r2,game:'game_2',bet:1000});
  const outcome = canBorrow.call({kind:'settle',transaction_id:'settle:'+r2,
    round_id:r2,game:'game_2',bet:1000,is_win:false});
  assert.ok(!outcome.badges.unlocked.includes('bankrupt'));
  const stillRich = environment([['11011','Alice',2000,0,'','pw',10000,10000]]);
  const r3 = hex('e');
  stillRich.call({kind:'bet',transaction_id:'bet:'+r3,round_id:r3,game:'game_2',bet:1000});
  const r3s = stillRich.call({kind:'settle',transaction_id:'settle:'+r3,
    round_id:r3,game:'game_2',bet:1000,is_win:false});
  assert.equal(r3s.balances.coins, 1000);
  assert.ok(!r3s.badges.unlocked.includes('bankrupt'));
});

function bankRound(e, n) {
  const round = String(n).repeat(32);
  e.call({kind:'bet',transaction_id:'bet:'+round,round_id:round,game:'game_2',bet:1000});
  e.call({kind:'settle',transaction_id:'settle:'+round,
    round_id:round,game:'game_2',bet:1000,is_win:false});
  return e.call({kind:'interest',transaction_id:'interest:'+round,
    round_id:round,game:'game_2'});
}

function repayAll(e, letter) {
  const wallet = e.call({kind:'status',transaction_id:'status:'+hex(letter)}).balances;
  return e.call({kind:'repay',transaction_id:'repay:'+hex(letter),amount:wallet.loan,
    expected_coins:wallet.coins,expected_loan:wallet.loan,
    expected_principal:wallet.principal});
}

test('Legendary finance badge needs a single 5000C+ borrow, five settled turns, and full repayment', () => {
  const early = environment([['11011','Alice',50000,0,'','pw',0]]);
  early.call({kind:'borrow',transaction_id:'borrow:'+hex('a'),amount:5000,
    expected_coins:50000,expected_loan:0,expected_principal:0});
  for(let i=1;i<=4;i++) bankRound(early,i);
  const before = repayAll(early,'e');
  assert.ok(!before.badges.unlocked.includes('loan_survivor'));
  assert.ok(!early.rows.users[1][10].includes('loan_survivor'));

  const e = environment([['11011','Alice',50000,0,'','pw',0]]);
  e.call({kind:'borrow',transaction_id:'borrow:'+hex('a'),amount:5000,
    expected_coins:50000,expected_loan:0,expected_principal:0});
  for(let i=1;i<=5;i++) bankRound(e,i);
  const balance = e.call({kind:'status',transaction_id:'status:'+hex('f')}).balances;
  assert.equal(balance.loan, 12442); // 5000 * 1.2^5, rounded each turn
  const part = e.call({kind:'repay',transaction_id:'repay:'+hex('b'),amount:3000,
    expected_coins:balance.coins,expected_loan:balance.loan,expected_principal:balance.principal});
  assert.ok(!part.badges.unlocked.includes('loan_survivor'));
  const final = repayAll(e,'c');
  assert.ok(final.badges.unlocked.includes('loan_survivor'));
  assert.equal(final.balances.loan, 0);
  assert.ok(e.rows.users[1][10].includes('loan_survivor'));
  assert.throws(() => e.call({kind:'repay',transaction_id:'repay:'+hex('c'),
    amount:1,expected_coins:0,expected_loan:0,
    expected_principal:0}), /different arguments/);
});

test('Mythic gold requires all SIX Legendary badges including 3 successful referrals', () => {
  const e = environment([['20102','Bob',5000,0,'','pw',0]]);
  e.rows.users[1][10] =
    'streak_eight_mixed g1_hit g4_four_streak g5_three_streak loan_survivor';
  const before = e.call({kind:'badge_sync',
    student_id:'20102',transaction_id:'badge_sync:'+hex('a')});
  assert.ok(!before.badges.owned.includes('all_legendary'));
  // A mere pre-existing collection of five Legendary badges no longer
  // unlocks the Mythic collector for players who haven't earned it.
  ['30103','30104','30105'].forEach((student_id, i) => {
    const r = e.call({kind:'register',transaction_id:'register:'+hex(String(i+1)),
      student_id,nickname:'초대한 친구',password:'pw',referrer_id:'20102'});
    assert.equal(r.balances.coins,6000);
    assert.equal(e.rows.users[1][10].includes('all_legendary'), i===2);
  });
  assert.ok(e.rows.users[1][10].includes('invite_three'));
  assert.ok(e.rows.users[1][10].includes('all_legendary'));

  // Once earned under the old 5-Legendary rule, the Mythic badge is
  // never revoked: awards are permanent.
  const old = environment([['20102','Bob',5000,0,'','pw',0]]);
  old.rows.users[1][10]='all_legendary';
  old.call({kind:'badge_sync',
    student_id:'20102',transaction_id:'badge_sync:'+hex('d')});
  assert.ok(old.rows.users[1][10].includes('all_legendary'));
});

test('bank badge write failure is atomic and replay never duplicates milestone', () => {
  const e = environment();
  e.state.failedBatch = true;
  const req={kind:'borrow',transaction_id:'borrow:'+hex('b'),amount:1000,
    expected_coins:5000,expected_loan:0,expected_principal:0};
  assert.throws(()=>e.call(req),/Simulated atomic batch failure/);
  assert.equal(e.rows.users[1][10], '');
  assert.equal(e.rows.users[1][2],5000);
  assert.equal(e.rows.ledger.length,1);
  e.state.failedBatch=false;
  const first=e.call(req);
  assert.ok(first.badges.unlocked.includes('first_borrow'));
  assert.equal(e.state.batches,1);
  assert.equal(e.call(req).replayed,true);
  assert.equal(e.state.batches,1);
});

test('badge_sync grants already bankrupt users without a bet or wallet mutation', () => {
  const e = environment([['11011','Alice',500,0,'','pw',10000,10000]]);
  const before = e.call({kind:'status',transaction_id:'status:'+hex('a')});
  assert.equal(before.badge_capabilities.sync,true);
  assert.equal(e.state.batches,0);
  assert.equal(e.rows.users[1][10],'');
  const sync={kind:'badge_sync',transaction_id:'badge_sync:'+hex('b')};
  const result=e.call(sync);
  assert.equal(result.balances.coins,500);
  assert.ok(result.badges.unlocked.includes('bankrupt'));
  assert.equal(e.rows.users[1][10],'bankrupt');
  assert.equal(e.rows.ledger.at(-1)[3],'badge_sync');
  assert.equal(e.state.batches,1);
  assert.equal(e.call(sync).replayed,true);
  assert.equal(e.state.batches,1);
  const next=e.call({kind:'badge_sync',transaction_id:'badge_sync:'+hex('c')});
  assert.deepEqual([...next.badges.unlocked],[]);
  assert.equal(e.state.batches,1); // no ledger spam when nothing new
});
test('badge_sync can recover historic first borrow and repayment records', () => {
  const e=environment([['11011','Alice',5000,0,'','pw',0]]);
  e.call({kind:'borrow',transaction_id:'borrow:'+hex('d'),amount:1000,
    expected_coins:5000,expected_loan:0,expected_principal:0});
  e.call({kind:'repay',transaction_id:'repay:'+hex('e'),amount:1000,
    expected_coins:6000,expected_loan:1000,expected_principal:1000});
  e.rows.users[1][10]=''; // simulate records created before the badge upgrade
  const recovered=e.call({kind:'badge_sync',transaction_id:'badge_sync:'+hex('f')});
  assert.ok(recovered.badges.unlocked.includes('first_borrow'));
  assert.ok(recovered.badges.unlocked.includes('first_repay'));
  assert.equal(e.rows.users[1][10], 'first_borrow first_repay');
});


function registerReferral(e, studentId, txDigit, referrerId='20102') {
  return e.call({kind:'register',transaction_id:'register:'+hex(txDigit),
    student_id:studentId,nickname:'새 친구',password:'pw',
    referrer_id:referrerId});
}

test('one verified referral grants Epic and three distinct referrals grant winged Legendary', () => {
  const e=environment([['20102','Bob',4000,0,'','pw',0]]);
  assert.equal(registerReferral(e,'30103','a').balances.coins,6000);
  assert.equal(e.rows.users[1][2],7000);
  assert.ok(e.rows.users[1][10].includes('invite_one'));
  assert.ok(!e.rows.users[1][10].includes('invite_three'));
  assert.equal(e.rows.ledger.filter(r=>r[3]==='referrer').length,1);
  assert.equal(registerReferral(e,'30104','b').balances.coins,6000);
  assert.ok(!e.rows.users[1][10].includes('invite_three'));
  assert.equal(registerReferral(e,'30105','c').balances.coins,6000);
  assert.equal(e.rows.users[1][2],13000);
  assert.ok(e.rows.users[1][10].includes('invite_one'));
  assert.ok(e.rows.users[1][10].includes('invite_three'));
  assert.equal(e.rows.ledger.filter(r=>r[3]==='referrer').length,3);
  assert.equal(e.rows.ledger.filter(r=>r[3]==='register').length,3);
  const sync=e.call({kind:'badge_sync',student_id:'20102',
    transaction_id:'badge_sync:'+hex('f')});
  assert.equal(sync.badges.unlocked.length,0);
});

test('duplicate request, duplicate student ID and malformed referral logs never inflate count', () => {
  const e=environment([['20102','Bob',4000,0,'','pw',0]]);
  const payload={kind:'register',transaction_id:'register:'+hex('a'),
    student_id:'30103',nickname:'새 친구',password:'pw',referrer_id:'20102'};
  e.call(payload);
  assert.equal(e.call(payload).replayed,true);
  assert.throws(()=>e.call({...payload,transaction_id:'register:'+hex('b')}),
    /Player exists/);
  const duplicate = [...e.rows.ledger.find(row=>row[3]==='referrer')];
  duplicate[0]='referrer:'+hex('c');
  e.rows.ledger.push(duplicate); // same invitee ID -> should count once
  const forged=[...duplicate];
  forged[0]='referrer:'+hex('d');
  forged[15]='referral:40101'; // teacher ID -> must not count
  e.rows.ledger.push(forged);
  const malformed=[...duplicate];
  malformed[0]='referrer:'+hex('e');
  malformed[15]='incomplete referral';
  e.rows.ledger.push(malformed);
  const sync=e.call({kind:'badge_sync',student_id:'20102',
    transaction_id:'badge_sync:'+hex('f')});
  assert.equal(sync.badges.owned.includes('invite_one'),true);
  assert.equal(sync.badges.owned.includes('invite_three'),false);
  assert.equal(e.rows.users[1][2],7000);
});

test('self referral, invalid referrer and teacher do not earn referral badges', () => {
  const e=environment([['20102','Bob',4000,0,'','pw',0],
    ['40101','Teacher',5000,0,'','pw',0]]);
  registerReferral(e,'30103','a','30103'); // self
  registerReferral(e,'30104','b','40101'); // teacher
  registerReferral(e,'30105','c','30109'); // missing account
  assert.equal(e.rows.ledger.filter(row=>row[3]==='referrer').length,0);
  assert.equal(e.rows.users[1][10],'');
  assert.equal(e.rows.users[2][10],'');
  assert.equal(e.rows.users[1][2],4000);
});

test('referral badge + credit + registered friend commit atomically and retries safely', () => {
  const e=environment([['20102','Bob',4000,0,'','pw',0]]);
  const req={kind:'register',transaction_id:'register:'+hex('a'),
    student_id:'30103',nickname:'새 친구',password:'pw',referrer_id:'20102'};
  e.state.failedBatch=true;
  assert.throws(()=>e.call(req),/Simulated atomic batch failure/);
  assert.equal(e.rows.users.length,2);
  assert.equal(e.rows.users[1][2],4000);
  assert.equal(e.rows.users[1][10],'');
  assert.equal(e.rows.ledger.length,1);
  e.state.failedBatch=false;
  e.call(req);
  assert.equal(e.rows.users.length,3);
  assert.equal(e.rows.users[1][2],7000);
  assert.equal(e.rows.users[1][10],'invite_one');
  assert.equal(e.call(req).replayed,true);
  assert.equal(e.rows.ledger.filter(row=>row[3]==='referrer').length,1);
  assert.equal(e.state.batches,1);
});

test('badge_sync retroactively awards proven historical friend referrals only', () => {
  const e=environment([['20102','Bob',4000,0,'','pw',0]]);
  registerReferral(e,'30103','a');
  registerReferral(e,'30104','b');
  registerReferral(e,'30105','c');
  e.rows.users[1][10]=''; // historical rewards from before badge release
  const result=e.call({kind:'badge_sync',student_id:'20102',
    transaction_id:'badge_sync:'+hex('f')});
  assert.ok(result.badges.unlocked.includes('invite_one'));
  assert.ok(result.badges.unlocked.includes('invite_three'));
  assert.equal(e.rows.users[1][10],'invite_one invite_three');
  assert.equal(e.rows.users[1][2],13000); // sync grants no bonus coins
  const second=e.call({kind:'badge_sync',student_id:'20102',
    transaction_id:'badge_sync:'+hex('e')});
  assert.equal(second.badges.unlocked.length,0);
});



function badgeProgressRound(e, n, game, isWin, evidence = {}) {
  const id = n.toString(16).padStart(32, '0');
  e.call({kind:'bet', transaction_id:'bet:' + id, round_id:id, game, bet:1000});
  return e.call({kind:'settle', transaction_id:'settle:' + id,
    round_id:id, game, bet:1000, is_win:isWin, badge_evidence:evidence});
}

test('badge_sync exposes the historical best streak, even after a loss', () => {
  const e = environment([['11011','Alice',100000,0,'','pw',0]]);
  for (let i = 1; i <= 3; i++) badgeProgressRound(e, i, 'game_3', true, {choice:'홀'});
  badgeProgressRound(e, 4, 'game_3', false, {choice:'짝'});
  const request = {kind:'badge_sync', transaction_id:'badge_sync:' + hex('a')};
  const sync = e.call(request);
  assert.equal(sync.badges.progress.g3_five_streak[0].current, 3);
  assert.equal(sync.badges.progress.g3_five_streak[0].target, 5);
  assert.equal(sync.badges.progress.streak_three[0].current, 3);
  assert.equal(sync.badges.progress.g3_both_five[0].current, 3);
  assert.equal(sync.badges.progress.g3_both_five[1].current, 0);
  assert.equal(e.call(request).badges.progress.g3_five_streak[0].current, 3);
  const settled = e.rows.ledger.find(row => row[3] === 'settle');
  e.rows.ledger.push([...settled]); // duplicate round ID cannot inflate progress
  const duplicateSync = e.call({kind:'badge_sync', transaction_id:'badge_sync:' + hex('b')});
  assert.equal(duplicateSync.badges.progress.g3_both_five[0].current, 3);
});

test('mixed streak progress keeps distinct-game requirement separate from win count', () => {
  const e = environment([['11011','Alice',100000,0,'','pw',0]]);
  for (let i = 1; i <= 5; i++) badgeProgressRound(e, i, 'game_2', true, {choice:'HIGH'});
  let sync = e.call({kind:'badge_sync',transaction_id:'badge_sync:' + hex('c')});
  assert.equal(sync.badges.progress.streak_five_mixed[0].current, 5);
  assert.equal(sync.badges.progress.streak_five_mixed[1].current, 1);
  assert.equal(sync.badges.owned.includes('streak_five_mixed'), false);
  badgeProgressRound(e, 6, 'game_3', true, {choice:'짝'});
  sync = e.call({kind:'badge_sync',transaction_id:'badge_sync:' + hex('d')});
  assert.equal(sync.badges.progress.streak_five_mixed[0].current, 5);
  assert.equal(sync.badges.progress.streak_five_mixed[1].current, 2);
  assert.equal(sync.badges.owned.includes('streak_five_mixed'), true);
  assert.equal(sync.badges.progress.streak_eight_mixed[0].current, 6);
  assert.equal(sync.badges.progress.streak_eight_mixed[1].current, 2);
});

test('multi-part accuracy and referral milestones use authenticated counts', () => {
  const e = environment([['11011','Alice',100000,0,'','pw',0]]);
  badgeProgressRound(e, 1, 'game_2', true, {choice:'HIGH'});
  badgeProgressRound(e, 2, 'game_2', true, {choice:'LOW'});
  badgeProgressRound(e, 3, 'game_2', true, {choice:'HIGH'});
  badgeProgressRound(e, 4, 'game_5', true);
  badgeProgressRound(e, 5, 'game_5', true);
  const sync = e.call({kind:'badge_sync',transaction_id:'badge_sync:' + hex('e')});
  assert.equal(sync.badges.progress.g2_both_fifteen[0].current, 2);
  assert.equal(sync.badges.progress.g2_both_fifteen[1].current, 1);
  assert.equal(sync.badges.progress.g5_three_wins[0].current, 2);
  assert.equal(sync.badges.progress.g5_three_streak[0].current, 2);
  assert.equal(sync.badges.progress.thirty_rounds[0].current, 5);
  assert.equal(sync.badges.progress.all_games[0].current, 2);
  assert.equal(sync.badges.progress.invite_three[0].current, 0);
});

test('article failure counter is global, replay-safe, and disables every matching row at 3', () => {
  const one = ['https://www.yna.co.kr/view/AKR1?utm_source=x', 0, '첫 기사', '', '', '', '', true, ''];
  const duplicate = ['https://www.yna.co.kr/view/AKR1', 0, '중복 기사', '', '', '', '', true, ''];
  const other = ['https://www.yna.co.kr/view/AKR2', 0, '다른 기사', '', '', '', '', true, ''];
  const e = environment(undefined, [one, duplicate, other]);
  const request = {
    kind: 'article_failure',
    url: 'https://www.yna.co.kr/view/AKR1',
    url_hash: '1'.repeat(64),
    event_id: 'a'.repeat(32)
  };
  const first = e.call({...request, student_id: '11011'});
  assert.equal(first.failure_count, 1);
  assert.equal(first.disabled, false);
  assert.equal(e.rows.news[1][9], 1);
  assert.equal(e.rows.news[2][9], 1);
  assert.equal(e.rows.news[1][7], true);

  const replay = e.call({...request, student_id: '22022'});
  assert.equal(replay.failure_count, 1);
  assert.equal(replay.replayed, true);
  assert.equal(e.rows.news[1][9], 1);

  const second = e.call({...request, event_id: 'b'.repeat(32), student_id: '22022'});
  assert.equal(second.failure_count, 2);
  const third = e.call({...request, event_id: 'c'.repeat(32), student_id: '33033'});
  assert.equal(third.failure_count, 3);
  assert.equal(third.disabled, true);
  assert.equal(e.rows.news[1][7], false);
  assert.equal(e.rows.news[2][7], false);
  assert.equal(e.rows.news[3][7], true);
  assert.equal(e.rows.news[3][9] || 0, 0);
  assert.equal(e.rows.news[0][9], 'FailureCount');
  assert.equal(e.rows.news[0][10], 'FailureEventIds');
});

test('article failure count and deactivation are atomic on Sheets errors', () => {
  const e = environment(undefined, [
    ['https://www.yna.co.kr/view/AKR3', 0, '기사', '', '', '', '', true, '']
  ]);
  const req = {kind:'article_failure',url:'https://www.yna.co.kr/view/AKR3',
    url_hash:'3'.repeat(64),event_id:'d'.repeat(32)};
  e.state.failedBatch = true;
  assert.throws(() => e.call(req), /Simulated atomic batch failure/);
  assert.equal(e.rows.news[1][9] || 0, 0);
  assert.equal(e.rows.news[1][7], true);
  e.state.failedBatch = false;
  assert.equal(e.call(req).failure_count, 1);
  assert.equal(e.rows.news[1][9], 1);
});

test('article failures require a valid request and never modify wallet balances', () => {
  const e = environment(undefined, [
    ['https://www.yna.co.kr/view/AKR4', 0, '기사', '', '', '', '', true, '']
  ]);
  const base = {kind:'article_failure',url:'https://www.yna.co.kr/view/AKR4',
    url_hash:'4'.repeat(64),event_id:'e'.repeat(32)};
  assert.throws(() => e.call({...base, event_id:'bad'}), /Article failure request/);
  assert.equal(e.call(base).tracked, true);
  assert.equal(e.rows.users[1][2], 5000);
  assert.equal(e.rows.ledger.length, 1);
});


test('game 4 fresh wins earn +3x net coins and duplicate settlement never re-pays', () => {
  const e = environment(), id = hex('b');
  e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id,
    game: 'game_4', bet: 1000});
  const request = {kind: 'settle', transaction_id: 'settle:' + id,
    round_id: id, game: 'game_4', bet: 1000, is_win: true};
  const first = e.call(request);
  assert.equal(first.settlement.delta, 3000);
  assert.equal(first.balances.coins, 8000); // 5,000C wallet; bet is not deducted.
  const replay = e.call(request);
  assert.equal(replay.replayed, true);
  assert.equal(replay.settlement.delta, 3000);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1);
  assert.equal(e.rows.users[1][2], 8000);
});

test('game 4 historical +2x settled receipt replays without changing the wallet', () => {
  const e = environment(), id = hex('c');
  e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id,
    game: 'game_4', bet: 1000});
  // A prior gateway already credited this win at the old +2x rule.
  e.rows.ledger.push([
    'settle:' + id, '2026-11-01T00:00:00Z', '11011', 'settle',
    'game_4', id, 1000, 2000, true, 5000, 7000, 1, 2, 0, 0, '',
  ]);
  e.rows.users[1][2] = 7000;
  e.rows.users[1][3] = 2;
  const request = {kind: 'settle', transaction_id: 'settle:' + id,
    round_id: id, game: 'game_4', bet: 1000, is_win: true};
  const batchesBefore = e.state.batches;
  const replay = e.call(request);
  assert.equal(replay.replayed, true);
  assert.equal(replay.settlement.delta, 2000);
  assert.equal(replay.balances.coins, 7000);
  assert.equal(e.state.batches, batchesBefore);
  assert.equal(e.rows.users[1][2], 7000);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1);
  assert.throws(() => e.call({...request, is_win: false}), /different arguments/);
});

test('all five winning games pay the configured net multiplier, not gross stake return', () => {
  const configured = [
    ['game_1', 100], ['game_2', 2], ['game_3', 2],
    ['game_4', 3], ['game_5', 5],
  ];
  for (const [game, multiplier] of configured) {
    const e = environment();
    const id = hex('a');
    e.call({kind: 'bet', transaction_id: 'bet:' + id,
      round_id: id, game, bet: 1000});
    const request = {kind: 'settle', transaction_id: 'settle:' + id,
      round_id: id, game, bet: 1000, is_win: true};
    const win = e.call(request);
    assert.equal(win.settlement.delta, 1000 * multiplier, game);
    assert.equal(win.balances.coins, 5000 + 1000 * multiplier, game);
    assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1);
    const repeated = e.call(request);
    assert.equal(repeated.replayed, true, game);
    assert.equal(repeated.settlement.delta, 1000 * multiplier, game);
    assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1);
  }
});

test('prior game 2 and game 3 +1x wins replay their original receipts without new credits', () => {
  for (const game of ['game_2', 'game_3']) {
    const e = environment(), id = hex('d');
    e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id,
      game, bet: 1000});
    // Existing ledger history from the old +1x gateway must remain immutable.
    e.rows.ledger.push([
      'settle:' + id, '2026-11-01T00:00:00Z', '11011', 'settle',
      game, id, 1000, 1000, true, 5000, 6000, 1, 2, 0, 0, '',
    ]);
    e.rows.users[1][2] = 6000;
    e.rows.users[1][3] = 2;
    const oldRows = e.rows.ledger.length;
    const request = {kind: 'settle', transaction_id: 'settle:' + id,
      round_id: id, game, bet: 1000, is_win: true};
    const replay = e.call(request);
    assert.equal(replay.replayed, true, game);
    assert.equal(replay.settlement.delta, 1000, game);
    assert.equal(replay.balances.coins, 6000, game);
    assert.equal(e.rows.ledger.length, oldRows);
    assert.equal(e.rows.users[1][2], 6000, game);
    assert.throws(() => e.call({...request, is_win: false}), /different arguments/);
  }
});

test('all five games lose the entire bet, including Game 3', () => {
  for (const game of ['game_1', 'game_2', 'game_3', 'game_4', 'game_5']) {
    const e = environment(), id = hex('f');
    e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id,
      game, bet: 1000});
    const request = {kind: 'settle', transaction_id: 'settle:' + id,
      round_id: id, game, bet: 1000, is_win: false};
    const loss = e.call(request);
    assert.equal(loss.settlement.delta, -1000, game);
    assert.equal(loss.balances.coins, 4000, game);
    const replay = e.call(request);
    assert.equal(replay.replayed, true, game);
    assert.equal(replay.settlement.delta, -1000, game);
    assert.equal(e.rows.users[1][2], 4000, game);
    assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1, game);
  }
});

test('Game 3 full-wallet loss reaches zero without extra deductions on replay', () => {
  const e = environment(), id = hex('e');
  e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id,
    game: 'game_3', bet: 5000});
  const request = {kind: 'settle', transaction_id: 'settle:' + id,
    round_id: id, game: 'game_3', bet: 5000, is_win: false};
  const first = e.call(request);
  assert.equal(first.settlement.delta, -5000);
  assert.equal(first.balances.coins, 0);
  assert.equal(e.call(request).settlement.delta, -5000);
  assert.equal(e.rows.users[1][2], 0);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1);
});

test('old Game 3 half-stake loss receipt replays without changing historical balance', () => {
  const e = environment(), id = hex('9');
  e.call({kind: 'bet', transaction_id: 'bet:' + id, round_id: id,
    game: 'game_3', bet: 1050});
  // The prior server charged only floor(1050/2) = 525C.
  e.rows.ledger.push([
    'settle:' + id, '2026-11-20T00:00:00Z', '11011', 'settle',
    'game_3', id, 1050, -525, false, 5000, 4475, 1, 0, 0, 0, '',
  ]);
  e.rows.users[1][2] = 4475;
  e.rows.users[1][3] = 0;
  const request = {kind: 'settle', transaction_id: 'settle:' + id,
    round_id: id, game: 'game_3', bet: 1050, is_win: false};
  const before = e.state.batches;
  const replay = e.call(request);
  assert.equal(replay.replayed, true);
  assert.equal(replay.settlement.delta, -525);
  assert.equal(replay.balances.coins, 4475);
  assert.equal(e.rows.users[1][2], 4475);
  assert.equal(e.state.batches, before);
  assert.equal(e.rows.ledger.filter(row => row[3] === 'settle').length, 1);
  assert.throws(() => e.call({...request, is_win: true}), /different arguments/);
});
