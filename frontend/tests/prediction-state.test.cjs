const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const ts = require('typescript');

// Exercise the actual submission handler with synthetic requests and state setters.
const file = path.join(__dirname, '../src/components/Exploratory/ExploratoryMode.tsx');
const text = fs.readFileSync(file, 'utf8');
const tree = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
let handler;
function visit(node) {
  if (ts.isVariableDeclaration(node) && node.name.getText(tree) === 'handleCustomPrediction') handler = node.initializer;
  ts.forEachChild(node, visit);
}
visit(tree);
assert(handler && ts.isArrowFunction(handler));
const expression = ts.createPrinter().printNode(ts.EmitHint.Expression, handler, tree);
const code = ts.transpileModule('const handler = ' + expression + ';', {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText;

function setup(api) {
  const state = { prediction: null, error: null, loading: false, shap: null, shapLoading: false };
  const names = ['setCustomPrediction', 'setCustomPredictionLoading', 'setCustomPredictionError', 'setShapExplanation', 'setShapLoading'];
  const fields = ['prediction', 'loading', 'error', 'shap', 'shapLoading'];
  const create = new Function('api', 'console', ...names, code + '\nreturn handler;');
  const submit = create(api, { error() {} }, ...fields.map(key => value => { state[key] = value; }));
  return { state, submit };
}

test('a successful request displays its own result and explanation', async () => {
  const result = { predictions: { XGB: { probability_score: 0.3 } } };
  const explanation = { shap_values_sorted: [] };
  const { state, submit } = setup({ predictCustom: async () => result, getLocalShap: async () => explanation });
  await submit({ age_years: 30 }, 'XGB');
  assert.equal(state.prediction, result);
  assert.equal(state.shap, explanation);
  assert.equal(state.loading, false);
  assert.equal(state.error, null);
});

test('a new failed request cannot retain the previous input result', async () => {
  const first = { predictions: { XGB: { probability_score: 0.9 } } };
  let calls = 0;
  let rejectSecond;
  const { state, submit } = setup({
    predictCustom: async () => ++calls === 1 ? first : new Promise((resolve, reject) => { rejectSecond = reject; }),
    getLocalShap: async () => ({ shap_values_sorted: [] }),
  });
  await submit({ age_years: 60 }, 'XGB');
  assert.equal(state.prediction, first);
  const pending = submit({ age_years: 30 }, 'XGB');
  assert.equal(state.prediction, null);
  assert.equal(state.shap, null);
  assert.equal(state.loading, true);
  const error = new Error('Synthetic unavailable prediction');
  rejectSecond(error);
  await pending;
  assert.equal(state.prediction, null);
  assert.equal(state.error, error);
  assert.equal(state.loading, false);
});

test('an explanation failure preserves the successful current prediction', async () => {
  const result = { predictions: { XGB: { probability_score: 0.3 } } };
  const { state, submit } = setup({
    predictCustom: async () => result,
    getLocalShap: async () => { throw new Error('Synthetic unavailable explanation'); },
  });
  await submit({ age_years: 30 }, 'XGB');
  assert.equal(state.prediction, result);
  assert.equal(state.shap, null);
  assert.equal(state.error, null);
  assert.equal(state.loading, false);
  assert.equal(state.shapLoading, false);
});
