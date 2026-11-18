const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const ts = require('typescript');

const file = path.join(__dirname, '../src/hooks/usePresets.ts');
const source = fs.readFileSync(file, 'utf8');
const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true);
const names = [];
function visit(node) {
  if (ts.isVariableDeclaration(node) && ts.isArrayBindingPattern(node.name) && ts.isCallExpression(node.initializer)
      && node.initializer.expression.getText(tree) === 'useState') names.push(node.name.elements[0].getText(tree));
  ts.forEachChild(node, visit);
}
visit(tree);
const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;

function setup(api) {
  const boxes = {};
  let index = 0;
  const react = {
    useState(initial) {
      const name = names[index++];
      boxes[name] = initial;
      return [initial, value => { boxes[name] = typeof value === 'function' ? value(boxes[name]) : value; }];
    },
    useRef: initial => ({ current: initial }),
  };
  const exports = {};
  const requireStub = name => {
    if (name === 'react') return react;
    if (name === '../utils/api') return { api };
    if (name === './useAsync') return { useAsync: () => ({ data: {}, isLoading: false, error: null }) };
    throw new Error('Unexpected import ' + name);
  };
  new Function('require', 'exports', code)(requireStub, exports);
  return { state: boxes, submit: exports.usePresets().predictPreset };
}

test('a failed retry clears only the selected preset result and explanation', async () => {
  let fail;
  let retry = false;
  const { state, submit } = setup({
    predictCustom: async input => retry ? new Promise((resolve, reject) => { fail = reject; }) : { profile: input.id },
    getLocalShap: async () => ({ model: 'XGB' }),
  });
  await submit('first', { id: 1 });
  await submit('other', { id: 2 });
  retry = true;
  const pending = submit('first', { id: 1 });
  assert.equal(state.presetPredictions.first, undefined);
  assert.equal(state.presetShapResults.first, undefined);
  assert.equal(state.presetPredictions.other.profile, 2);
  assert.equal(state.presetPredictionLoading.first, true);
  fail(new Error('synthetic failure'));
  await pending;
  assert.equal(state.presetPredictionLoading.first, false);
  assert.match(state.presetPredictionErrors.first.message, /Prediction unavailable/);
  assert.equal(state.presetPredictions.first, undefined);
});

test('a preset explanation error preserves its fresh prediction and exposes feedback', async () => {
  const prediction = { predictions: {} };
  const { state, submit } = setup({
    predictCustom: async () => prediction,
    getLocalShap: async () => { throw new Error('synthetic unavailable'); },
  });
  await submit('first', {});
  assert.equal(state.presetPredictions.first, prediction);
  assert.equal(state.presetShapResults.first, undefined);
  assert.match(state.presetShapErrors.first.message, /local explanation/);
});

test('an older same-profile response cannot overwrite its newer request', async () => {
  let finishFirst;
  let calls = 0;
  const { state, submit } = setup({
    predictCustom: async () => ++calls === 1 ? new Promise(resolve => { finishFirst = resolve; }) : { version: 2 },
    getLocalShap: async () => ({ version: 2 }),
  });
  const old = submit('first', {});
  await submit('first', {});
  finishFirst({ version: 1 });
  await old;
  assert.equal(state.presetPredictions.first.version, 2);
  assert.equal(state.presetShapResults.first.version, 2);
});
