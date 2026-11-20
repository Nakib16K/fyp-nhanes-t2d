const assert = require('node:assert/strict');
const { test } = require('node:test');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { loadSource } = require('./load-source.cjs');

const prediction = { probability_score: .2768, risk_percentage: '27.7%',
  prediction_class: 'High Risk', above_threshold: true,
  decision_threshold: .276806, decision_margin_pp: .00052 };

function render(Component, props = {}) {
  return renderToStaticMarkup(React.createElement(Component, props));
}

test('decision presentation keeps the supplied full-precision flag near a rounded cutoff', () => {
  const { ModelDecisionExplanation } = loadSource('components/Exploratory/ModelDecisionExplanation.tsx');
  const html = render(ModelDecisionExplanation, { modelName: 'LR', prediction });
  assert.match(html, /Above model threshold/);
  assert.match(html, /Near the model&#x27;s decision cutoff/);
  assert.match(html, /full-precision score/);
});

test('older prediction responses without optional decision metadata remain displayable', () => {
  const { ModelDecisionExplanation } = loadSource('components/Exploratory/ModelDecisionExplanation.tsx');
  const html = render(ModelDecisionExplanation, { modelName: 'LR', prediction: {
    probability_score: .3, risk_percentage: '30.0%', prediction_class: 'Low Risk',
  } });
  assert.match(html, /Decision flag unavailable/);
  assert.doesNotMatch(html, /Validation-selected cutoff/);
});

test('preset summaries disclose validation thresholds and the illustrative mean', () => {
  const { PresetCard } = loadSource('components/Exploratory/PresetCard.tsx');
  const html = render(PresetCard, { name: 'healthy',
    preset: { height_cm: 175, weight_kg: 80 }, onPredict() {},
    prediction: { predictions: Object.fromEntries(['LR', 'RF', 'LGBM', 'XGB'].map((name) => [name, prediction])) },
  });
  assert.match(html, /Illustrative arithmetic mean of four model estimates/);
  assert.match(html, /Each threshold was selected on validation data/);
  assert.match(html, /not a medical cutoff/);
});

test('local SHAP renders its base-estimator scope, indicator states and only five initial rows', () => {
  const { SHAPVisualization } = loadSource('components/Exploratory/SHAPVisualization.tsx');
  const html = render(SHAPVisualization, { result: { model: 'LR', base_value: 0,
    shap_values_sorted: Array.from({ length: 6 }, (_, index) => ({ feature: 'Synthetic feature ' + index,
      impact: 1 - index / 10, indicator_state: index === 0 ? 'present' : 'absent' })),
  } });
  assert.match(html, /uncalibrated/);
  assert.match(html, /not an explanation of the calibrated probability/);
  assert.match(html, /log-odds, not probability points/);
  assert.match(html, /Indicator selected \/ present/);
  assert.match(html, /Indicator not selected \/ absent/);
  assert.doesNotMatch(html, /Synthetic feature 5/);
  assert.match(html, /Show all 6 contributions/);
});

test('global SHAP retains its uncalibrated-estimator disclosure', () => {
  let index = 0;
  const react = { ...React, useState(initial) {
    const value = index++ === 0 ? true : initial === 'metrics' ? 'shap' : initial;
    return React.useState(value);
  } };
  const { ModelCard } = loadSource('components/ModelComparison/ModelCard.tsx', { react });
  const html = render(ModelCard, { model: { model_name: 'XGB', auc_roc: .8, f1: .5,
    precision: .5, recall: .5, accuracy: .8 } });
  assert.match(html, /underlying uncalibrated estimator/);
  assert.match(html, /does not directly explain the full calibrated ensemble probabilities/);
});

test('custom results disclose full-precision decisions and the non-clinical cutoff', () => {
  let seeded = false;
  const react = { ...React, useState(initial) {
    if (initial === null && !seeded) {
      seeded = true;
      return React.useState({ predictions: { LR: prediction }, computed_metrics: { bmi: 25, waist_to_height_ratio: .5 } });
    }
    return React.useState(initial);
  } };
  const presets = { usePresets: () => ({
    presets: {}, presetsLoading: false, presetsError: null,
    presetPredictions: {}, presetPredictionLoading: {}, presetPredictionErrors: {},
    presetShapErrors: {}, presetShapResults: {}, presetShapLoading: {}, predictPreset() {},
  }) };
  const { ExploratoryMode } = loadSource('components/Exploratory/ExploratoryMode.tsx', {
    react, '../../hooks/usePresets': presets,
  });
  const html = render(ExploratoryMode);
  assert.match(html, /Each flag compares the model&#x27;s full-precision estimate/);
  assert.match(html, /not a clinically validated/);
});
