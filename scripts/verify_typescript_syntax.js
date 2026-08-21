
const fs = require("fs");
const path = require("path");
const ts = require("/opt/nvm/versions/node/v22.16.0/lib/node_modules/typescript");

const root = process.argv[2];
const files = [];
function walk(dir) {
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (full.endsWith(".ts") || full.endsWith(".tsx")) files.push(full);
  }
}
walk(root);

let errors = [];
for (const file of files) {
  const source = fs.readFileSync(file, "utf8");
  const result = ts.transpileModule(source, {
    fileName: file,
    reportDiagnostics: true,
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ESNext,
      jsx: ts.JsxEmit.ReactJSX,
      strict: true
    }
  });
  for (const d of result.diagnostics || []) {
    if (d.category === ts.DiagnosticCategory.Error) {
      const msg = ts.flattenDiagnosticMessageText(d.messageText, "\n");
      errors.push(`${file}: TS${d.code}: ${msg}`);
    }
  }
}
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(JSON.stringify({files: files.length, errors: 0}));
