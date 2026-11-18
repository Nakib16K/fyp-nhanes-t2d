const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const ts = require('typescript');

const file = path.join(__dirname, '../src/components/Exploratory/CustomPredictionForm.tsx');
const source = fs.readFileSync(file, 'utf8');
const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const functions = {};
function visit(node) {
  if (ts.isVariableDeclaration(node) && ['handleSubmit', 'validateForm'].includes(node.name.getText(tree))) {
    const expression = ts.createPrinter().printNode(ts.EmitHint.Expression, node.initializer, tree);
    functions[node.name.getText(tree)] = ts.transpileModule('const fn = ' + expression + ';', {
      compilerOptions: { target: ts.ScriptTarget.ES2022 },
    }).outputText + '\nreturn fn;';
  }
  ts.forEachChild(node, visit);
}
visit(tree);

function profile(education) {
  return { age_years: '45', gender_code: 1, ethnicity_code: 7, education_level: education,
    poverty_ratio: '2.5', height_cm: '175', weight_kg: '85', waist_circumference: '95',
    systolic_bp: '128', diastolic_bp: '82', pulse_60s: '72', smoked_100_cigs: 1,
    vigorous_activity: 2, family_history_diabetes: 1, history_high_bp: 1 };
}

for (const level of [1, 2, 3, 4, 5, 7, 9]) {
  test(`education choice ${level} validates and serializes correctly`, async () => {
    const formData = profile(level);
    let errors;
    let sent;
    const validateForm = new Function('formData', 'setValidationErrors', functions.validateForm)(formData, value => { errors = value; });
    assert.equal(validateForm(), true);
    assert.deepEqual(errors, {});
    const submit = new Function('formData', 'validateForm', 'onSubmit', 'selectedModel', functions.handleSubmit)(
      formData, validateForm, async (body, model) => { sent = { body, model }; }, 'LR');
    await submit({ preventDefault() {} });
    assert.equal(sent.model, 'LR');
    assert.equal(sent.body.education_level, [7, 9].includes(level) ? null : level);
    assert.equal(sent.body.ethnicity_code, 7);
  });
}

test('blank and unsupported education choices remain invalid', () => {
  for (const value of [0, 6, 8]) {
    let errors;
    const validate = new Function('formData', 'setValidationErrors', functions.validateForm)(profile(value), next => { errors = next; });
    assert.equal(validate(), false);
    assert.ok(errors.education_level);
  }
});
