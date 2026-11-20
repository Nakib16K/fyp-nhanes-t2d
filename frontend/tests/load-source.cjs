const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

const root = path.resolve(__dirname, '../src');

function loadSource(relative, overrides = {}) {
  const cache = new Map();
  function load(file) {
    if (cache.has(file)) return cache.get(file);
    const source = fs.readFileSync(file, 'utf8')
      .replaceAll('import.meta.env.VITE_API_URL', '"https://demo.example.com"');
    const code = ts.transpileModule(source, {
      fileName: file,
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    const exports = {};
    cache.set(file, exports);
    const localRequire = (name) => {
      if (Object.hasOwn(overrides, name)) return overrides[name];
      if (!name.startsWith('.')) return require(name);
      const base = path.resolve(path.dirname(file), name);
      if (!base.startsWith(root + path.sep)) throw new Error('Source import outside frontend');
      const target = [base + '.ts', base + '.tsx', path.join(base, 'index.ts'), path.join(base, 'index.tsx')]
        .find((candidate) => fs.existsSync(candidate));
      if (!target) throw new Error('Source import not found: ' + name);
      return load(target);
    };
    new Function('require', 'exports', code)(localRequire, exports);
    return exports;
  }
  return load(path.join(root, relative));
}

module.exports = { loadSource };
