#!/usr/bin/env node
/**
 * Translation consistency check -- `npm run check:i18n`.
 *
 * English (messages/en) is the reference. For every other locale it fails on:
 *   - a namespace file that is missing, or not registered in <locale>/index.ts
 *   - a key that is missing, or that only exists in the translation
 *   - an empty translation
 *   - {placeholders} or <tags> that differ from English (they would render
 *     wrong or throw at runtime)
 * and warns (without failing) on values identical to English, which are
 * often just forgotten translations. Run with --strict to fail on those too.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const MESSAGES_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../messages");
const REFERENCE = "en";
const strict = process.argv.includes("--strict");

// Values that are legitimately the same in every language.
const SAME_AS_ENGLISH_ALLOWED = new Set(["GreenGuard", "pH", "DAP", "MOP / SOP"]);

const errors = [];
const warnings = [];

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    errors.push(`${path.relative(MESSAGES_DIR, file)}: invalid JSON (${error.message})`);
    return null;
  }
}

function flatten(tree, prefix = "", out = new Map()) {
  for (const [key, value] of Object.entries(tree)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (value !== null && typeof value === "object") flatten(value, fullKey, out);
    else out.set(fullKey, value);
  }
  return out;
}

/** Collects ICU argument names, skipping the literal text of plural/select branches. */
function icuArguments(message) {
  const names = new Set();
  let i = 0;

  const parseText = () => {
    while (i < message.length) {
      const ch = message[i];
      if (ch === "{") {
        i += 1;
        parseArgument();
      } else if (ch === "}") {
        return;
      } else {
        i += 1;
      }
    }
  };

  const readUntil = (stops) => {
    const start = i;
    while (i < message.length && !stops.includes(message[i])) i += 1;
    return message.slice(start, i).trim();
  };

  const parseArgument = () => {
    names.add(readUntil([",", "}"]));
    if (message[i] === "}") {
      i += 1;
      return;
    }
    i += 1;
    const type = readUntil([",", "}"]);
    if (message[i] === "}") {
      i += 1;
      return;
    }
    i += 1;
    if (["plural", "select", "selectordinal"].includes(type)) {
      while (i < message.length && message[i] !== "}") {
        readUntil(["{", "}"]);
        if (message[i] === "{") {
          i += 1;
          parseText();
          i += 1;
        }
      }
      i += 1;
      return;
    }
    // number/date/time with a style: skip to the matching brace.
    let depth = 1;
    while (i < message.length && depth > 0) {
      if (message[i] === "{") depth += 1;
      if (message[i] === "}") depth -= 1;
      i += 1;
    }
  };

  parseText();
  return names;
}

function tags(message) {
  return new Set([...message.matchAll(/<\/?([A-Za-z][\w-]*)>/g)].map((match) => match[1]));
}

const sameSet = (a, b) => a.size === b.size && [...a].every((value) => b.has(value));
const show = (set) => `{${[...set].sort().join(", ")}}`;

const locales = fs
  .readdirSync(MESSAGES_DIR, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name);

const namespaceFiles = (locale) =>
  fs.readdirSync(path.join(MESSAGES_DIR, locale)).filter((file) => file.endsWith(".json")).sort();

const referenceFiles = namespaceFiles(REFERENCE);

for (const locale of locales) {
  const indexFile = path.join(MESSAGES_DIR, locale, "index.ts");
  const indexSource = fs.existsSync(indexFile) ? fs.readFileSync(indexFile, "utf8") : "";
  if (!indexSource) errors.push(`${locale}/index.ts: missing`);

  for (const file of namespaceFiles(locale)) {
    if (indexSource && !indexSource.includes(`"./${file}"`)) {
      errors.push(`${locale}/${file}: not imported in ${locale}/index.ts, so the app never loads it`);
    }
  }

  if (locale === REFERENCE) continue;

  for (const file of namespaceFiles(locale)) {
    if (!referenceFiles.includes(file)) errors.push(`${locale}/${file}: has no ${REFERENCE}/${file} counterpart`);
  }

  for (const file of referenceFiles) {
    const translatedPath = path.join(MESSAGES_DIR, locale, file);
    if (!fs.existsSync(translatedPath)) {
      errors.push(`${locale}/${file}: missing (copy ${REFERENCE}/${file} and translate it)`);
      continue;
    }
    const reference = readJson(path.join(MESSAGES_DIR, REFERENCE, file));
    const translated = readJson(translatedPath);
    if (!reference || !translated) continue;

    const referenceKeys = flatten(reference);
    const translatedKeys = flatten(translated);
    const where = (key) => `${locale}/${file} → ${key}`;

    for (const [key, englishValue] of referenceKeys) {
      if (!translatedKeys.has(key)) {
        errors.push(`${where(key)}: missing`);
        continue;
      }
      const value = translatedKeys.get(key);
      if (typeof value !== "string" || value.trim() === "") {
        errors.push(`${where(key)}: empty or not a string`);
        continue;
      }
      const expectedArgs = icuArguments(englishValue);
      const actualArgs = icuArguments(value);
      if (!sameSet(expectedArgs, actualArgs)) {
        errors.push(`${where(key)}: placeholders ${show(actualArgs)} should be ${show(expectedArgs)}`);
      }
      const expectedTags = tags(englishValue);
      const actualTags = tags(value);
      if (!sameSet(expectedTags, actualTags)) {
        errors.push(`${where(key)}: tags ${show(actualTags)} should be ${show(expectedTags)}`);
      }
      if (
        value === englishValue &&
        /[A-Za-z]{3,}/.test(value.replace(/\{[^{}]*\}/g, "")) &&
        !SAME_AS_ENGLISH_ALLOWED.has(value)
      ) {
        warnings.push(`${where(key)}: identical to English ("${value}")`);
      }
    }

    for (const key of translatedKeys.keys()) {
      if (!referenceKeys.has(key)) errors.push(`${where(key)}: not in ${REFERENCE}/${file} (typo or stale key?)`);
    }
  }
}

for (const warning of warnings) console.warn(`warning  ${warning}`);
for (const error of errors) console.error(`error    ${error}`);

const failed = errors.length > 0 || (strict && warnings.length > 0);
console.log(
  `\ni18n check: ${locales.length} locales, ${referenceFiles.length} namespaces -- ` +
    `${errors.length} error(s), ${warnings.length} warning(s).`
);
process.exit(failed ? 1 : 0);
