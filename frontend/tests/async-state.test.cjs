const assert = require('node:assert/strict');
const { test } = require('node:test');
const { loadSource } = require('./load-source.cjs');

// Test hook state and effects without mounting the dashboard.
function setup() {
  const slots = [];
  let index;
  let pending;
  const react = {
    useState(initial) {
      const slot = index++;
      if (!(slot in slots)) slots[slot] = initial;
      return [slots[slot], (value) => { slots[slot] = typeof value === 'function' ? value(slots[slot]) : value; }];
    },
    useRef(initial) {
      const slot = index++;
      return slots[slot] ||= { current: initial };
    },
    useEffect(effect, dependencies) {
      const slot = index++;
      const previous = slots[slot];
      if (!previous || dependencies.some((value, i) => !Object.is(value, previous.dependencies[i]))) {
        pending.push(() => {
          previous?.cleanup?.();
          slots[slot] = { dependencies, cleanup: effect() };
        });
      }
    },
  };
  const { useAsync } = loadSource('hooks/useAsync.ts', { react });
  return {
    render(task, immediate = true) {
      index = 0;
      pending = [];
      const state = useAsync(task, immediate);
      pending.forEach((effect) => effect());
      return state;
    },
    state: () => slots[0],
    unmount: () => slots.forEach((slot) => slot?.cleanup?.()),
  };
}

test('new inline callbacks do not restart a pending request on each render', async () => {
  const hook = setup();
  let calls = 0;
  let complete;
  hook.render(() => { calls++; return new Promise((resolve) => { complete = resolve; }); });
  hook.render(async () => { calls++; return 'new task'; });
  assert.equal(calls, 1);
  complete('first result');
  await Promise.resolve();
  assert.deepEqual(hook.state(), { data: 'first result', error: null, isLoading: false });
});

test('enabling a deferred request uses the latest callback', async () => {
  const hook = setup();
  let oldCalls = 0;
  hook.render(async () => { oldCalls++; }, false);
  hook.render(async () => 'latest', true);
  await Promise.resolve();
  assert.equal(oldCalls, 0);
  assert.equal(hook.state().data, 'latest');
});

test('a completed request cannot publish state after unmount', async () => {
  const hook = setup();
  let complete;
  hook.render(() => new Promise((resolve) => { complete = resolve; }));
  const before = hook.state();
  hook.unmount();
  complete('late result');
  await Promise.resolve();
  assert.equal(hook.state(), before);
});
