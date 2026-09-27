"use strict";

const { readFileSync, writeFileSync } = require("node:fs");
const { resolve } = require("node:path");

const version = process.argv[2];

if (!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version ?? "")) {
  throw new Error("Expected a numeric semantic version in X.Y.Z format.");
}

const versioned_files = [
  {
    path: "pyproject.toml",
    pattern: /^(version\s*=\s*")[^"]+("\s*)$/m,
  },
  {
    path: "app/__init__.py",
    pattern: /^(__version__\s*=\s*")[^"]+("\s*)$/m,
  },
];

for (const file of versioned_files) {
  const path = resolve(process.cwd(), file.path);
  const content = readFileSync(path, "utf8");
  const matches = content.match(new RegExp(file.pattern.source, "gm"));

  if (matches?.length !== 1) {
    throw new Error(`Expected exactly one version declaration in ${file.path}.`);
  }

  writeFileSync(path, content.replace(file.pattern, `$1${version}$2`));
}
