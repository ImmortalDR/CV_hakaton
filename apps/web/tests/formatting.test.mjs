import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('../src/formatting.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText;
const { countLabel, countForms } = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));
const values = [0,1,2,4,5,11,14,21,22,25,101];
const forms = [2,0,1,1,2,2,2,0,1,2,0];
for (const kind of Object.keys(countForms)) {
  values.forEach((n,i) => assert.equal(countLabel(n,kind), `${n} ${countForms[kind][forms[i]]}`));
}
console.log('55 Russian numeral assertions passed');
