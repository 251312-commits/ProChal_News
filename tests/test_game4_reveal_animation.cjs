/* Browser-free contract test for the game4 in-place score landing sequence. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const script = fs.readFileSync(
  path.join(__dirname, '..', 'games/game4_ui/picker/picker.js'), 'utf8'
);

function makeElement(top = 0, height = 100) {
  const classes = new Set();
  const props = new Map();
  const attrs = new Map();
  return {
    top, height, textContent: '', disabled: false, hidden: false,
    dataset: {}, listeners: {},
    classList: {
      add: (...items) => items.forEach(item => classes.add(item)),
      remove: (...items) => items.forEach(item => classes.delete(item)),
      contains: item => classes.has(item),
    },
    style: {
      setProperty: (key, value) => props.set(key, value),
      removeProperty: key => props.delete(key),
      getPropertyValue: key => props.get(key),
    },
    getBoundingClientRect() { return {top: this.top, height: this.height}; },
    get offsetWidth() { return 120; },
    setAttribute(key, value) {attrs.set(key, value);},
    removeAttribute(key) {attrs.delete(key);},
    getAttribute(key) {return attrs.get(key);},
    addEventListener(key, fn) {this.listeners[key] = fn;},
  };
}

function harness(reducedMotion = false) {
  const scene = makeElement();
  const confirm = makeElement();
  const back = makeElement();
  const bank = makeElement();
  const mystery = makeElement(210, 140);
  const score = makeElement();
  const unit = makeElement();
  const subtitle = makeElement();
  mystery.querySelector = key => key === 'strong' ? score : key === '.unit' ? unit : null;
  const segments = [
    {idx: 2, top: 100}, {idx: 1, top: 210}, {idx: 0, top: 320}
  ].map(({idx, top}) => {
    const element = makeElement(top, 90);
    const range = makeElement();
    element.dataset.index = String(idx);
    element.querySelector = key => key === '.segment-range' ? range : null;
    return element;
  });
  scene.querySelectorAll = key => key === 'button'
    ? [confirm, back, bank, ...segments] : [];
  const items = {
    '.scene': scene, '.confirm': confirm, '.mystery': mystery,
    '.subtitle': subtitle, '.logo': makeElement(),
    '.laurel.left': makeElement(), '.laurel.right': makeElement(),
    '.coins': makeElement(), '.tick-label.top': makeElement(),
    '.tick-label.bottom': makeElement(), '.back': back, '.bank': bank,
  };
  const sent = [];
  const tasks = [];
  const parent = {postMessage: message => sent.push(message)};
  const window = {
    parent, innerHeight: 750, listeners: {},
    addEventListener(key, fn) {this.listeners[key] = fn;},
  };
  const ctx = {
    document: {
      querySelector: key => items[key],
      querySelectorAll: key => key === '.segment' ? segments : [],
      body: {style: {setProperty() {}}},
    },
    window,
    matchMedia: () => ({matches: reducedMotion}),
    setTimeout: (fn, ms) => { tasks.push({fn, ms}); return tasks.length; },
    clearTimeout: () => {},
    Intl,
  };
  vm.createContext(ctx);
  vm.runInContext(script, ctx, {filename: 'picker.js'});
  const ranges = ['70.00~71.99%', '72.00~73.99%', '74.00~75.99%'];
  function render(reveal = null) {
    window.listeners.message({
      source: parent, origin: 'null',
      data: {type: 'streamlit:render', args: {
        round_id: 'round-id', ranges, coins: 5000,
        art: {background: 'bg', logo: 'logo', laurel_left: 'l', laurel_right: 'r'},
        reveal,
      }}
    });
  }
  function runThrough(ms) {
    while (tasks.some(task => task.ms <= ms)) {
      const idx = tasks.findIndex(task => task.ms <= ms);
      const task = tasks.splice(idx, 1)[0];
      task.fn();
    }
  }
  return {render, runThrough, items, segments, sent, confirm, mystery, score, subtitle, tasks};
}

for (const answer of [0, 1, 2]) {
  test('reveals score and lands original mystery card at answer index ' + answer, () => {
    const page = harness();
    page.render();
    assert.equal(page.score.textContent, '??');
    page.confirm.listeners.click();
    const events = () => page.sent.filter(e => e.type === 'streamlit:setComponentValue');
    assert.equal(events().length, 1);
    assert.equal(events()[0].value.action, 'choose');
    assert.equal(events()[0].value.index, 1);

    page.render({score: '74.25', selected_index: 1, answer_index: answer});
    assert.equal(page.score.textContent, '??');
    page.runThrough(750);
    assert.equal(page.score.textContent, '74.25');
    assert.equal(page.mystery.getAttribute('aria-label'), '실제 일치율 74.25%');
    assert.equal(events().length, 1);
    page.runThrough(1050);
    const px = Number(page.mystery.style.getPropertyValue('--landing-offset').replace('px', ''));
    assert.equal(Math.sign(px), answer === 2 ? -1 : answer === 0 ? 1 : -1);
    assert.equal(page.mystery.classList.contains('moving'), true);
    page.runThrough(2050);
    const target = page.segments.find(button => Number(button.dataset.index) === answer);
    assert.equal(target.classList.contains('correct'), true);
    assert.equal(page.mystery.classList.contains('landed'), true);
    assert.equal(events().length, 1);
    page.runThrough(2600);
    assert.equal(events().length, 2);
    assert.equal(events()[1].value.action, 'reveal_complete');
    assert.equal(events()[1].value.round_id, 'round-id');
    page.render({score: '74.25', selected_index: 1, answer_index: answer});
    assert.equal(events().length, 2);
    assert.equal(page.tasks.length, 0);
  });
}

test('reduced motion shows score and highlights without vertical travel', () => {
  const page = harness(true);
  page.render({score: '74.25', selected_index: 0, answer_index: 2});
  page.runThrough(0);
  assert.equal(page.score.textContent, '74.25');
  assert.equal(page.mystery.classList.contains('moving'), false);
  assert.equal(page.segments[0].classList.contains('correct'), true);
  assert.equal(page.sent.filter(e => e.value?.action === 'reveal_complete').length, 0);
  page.runThrough(700);
  assert.equal(page.sent.filter(e => e.value?.action === 'reveal_complete').length, 1);
});
