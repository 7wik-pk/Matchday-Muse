// Compiles every schema in contracts/, then checks each scripted run in
// ws/examples/, and the per-style takes in ws/examples/takes.json, against the
// schemas and the rules that the schemas alone cannot express. Exits non-zero
// on any failure.

import { isDeepStrictEqual } from 'node:util';
import { readFileSync, readdirSync } from 'node:fs';
import { basename, dirname, join, relative } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const examplesDir = join(root, 'ws', 'examples');
const SCHEMA_DIRS = ['ws', 'pipeline'];

const readJson = (file) => JSON.parse(readFileSync(file, 'utf8'));
const idFor = (file) => pathToFileURL(file).href;

const ajv = new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true });
addFormats(ajv);

const schemaFiles = SCHEMA_DIRS.flatMap((dir) =>
  readdirSync(join(root, dir))
    .filter((name) => name.endsWith('.json'))
    .map((name) => join(root, dir, name)),
);
for (const file of schemaFiles) {
  ajv.addSchema({ ...readJson(file), $id: idFor(file) });
}

const failures = [];
const fail = (where, message) => failures.push(`${where}: ${message}`);

for (const file of schemaFiles) {
  try {
    ajv.getSchema(idFor(file));
  } catch (err) {
    fail(relative(root, file), `does not compile: ${err.message}`);
  }
}

const validateScript = ajv.getSchema(idFor(join(root, 'ws', 'mock-script.json')));
const validateTakes = ajv.getSchema(idFor(join(root, 'ws', 'mock-takes.json')));

// Validating against the ServerMessage union reports every branch's errors;
// validating against the message's own type names the real problem.
const serverMessageId = idFor(join(root, 'ws', 'server-message.json'));
const DEF_BY_TYPE = {
  'session.ready': 'SessionReady',
  'run.accepted': 'RunAccepted',
  'stage.update': 'StageUpdate',
  'prompt.request': 'PromptRequest',
  'run.result': 'RunResult',
  'run.error': 'RunError',
};

function explainScriptErrors(where, script) {
  const precise = [];
  script.steps?.forEach((step, i) => {
    const def = DEF_BY_TYPE[step?.send?.type];
    if (!def) return;
    const validate = ajv.getSchema(`${serverMessageId}#/$defs/${def}`);
    if (validate(step.send)) return;
    for (const err of validate.errors) {
      precise.push(`/steps/${i}/send${err.instancePath} ${err.message}`);
    }
  });
  const errors = precise.length
    ? precise
    : validateScript.errors.map((err) => `${err.instancePath || '/'} ${err.message}`);
  for (const message of errors) fail(where, message);
}
const TERMINAL = new Set(['run.result', 'run.error']);
const STAGE_FINAL = new Set(['done', 'skipped', 'failed']);
const RETELL_STAGES = ['generate', 'guardrails', 'done'];
const MAX_HEADLINE_WORDS = 10;
const MAX_POEM_WORDS = 300;

const wordCount = (text) => text.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length;

// What the result schema cannot say: text and image are exclusive, every
// line's facts exist, every fact cites a listed source, and the length caps.
function checkResult(where, result) {
  if ((result.output === 'text') !== (result.text !== null)) {
    fail(where, 'text must be set exactly when output is text');
  }
  if ((result.output === 'image') !== (result.imageUrl !== null)) {
    fail(where, 'imageUrl must be set exactly when output is image');
  }
  const factIds = new Set();
  for (const fact of result.facts) {
    if (factIds.has(fact.id)) fail(where, `fact id ${fact.id} is repeated`);
    factIds.add(fact.id);
  }
  const sourceUrls = new Set(result.sources.map((s) => s.url));
  for (const fact of result.facts) {
    if (!sourceUrls.has(fact.sourceUrl)) fail(where, `fact ${fact.id} cites a url not in sources`);
  }
  if (!result.text) return;
  const { headline, stanzas } = result.text;
  const lines = stanzas.flatMap((s) => s.lines);
  for (const line of [headline, ...lines]) {
    for (const id of line.factIds) {
      if (!factIds.has(id)) fail(where, `line "${line.text.slice(0, 30)}…" cites unknown fact ${id}`);
    }
  }
  if (wordCount(headline.text) > MAX_HEADLINE_WORDS) {
    fail(where, `the headline is over ${MAX_HEADLINE_WORDS} words`);
  }
  const words = wordCount(lines.map((l) => l.text).join(' '));
  if (words > MAX_POEM_WORDS) fail(where, `the poem is ${words} words, over ${MAX_POEM_WORDS}`);
}

function checkSession(where, sends) {
  if (sends.length !== 1 || sends[0].type !== 'session.ready') {
    fail(where, 'the session script must send exactly one session.ready');
  }
}

function checkRun(where, script) {
  const { steps, start } = script;
  const sends = steps.filter((s) => s.send).map((s) => s.send);
  const first = sends[0];
  if (first?.type !== 'run.accepted') {
    fail(where, 'the first message must be run.accepted');
    return;
  }
  const runId = first.runId;
  const stageIds = first.payload.stages.map((s) => s.id);
  if ('fromRunId' in start && !isDeepStrictEqual(stageIds, RETELL_STAGES)) {
    fail(where, `a retell must list exactly the stages ${RETELL_STAGES.join(', ')}`);
  }
  let lastTs = -Infinity;
  let lastStageIndex = -1;
  const finished = new Set();

  sends.forEach((msg, i) => {
    const at = `${where} message ${i + 1} (${msg.type})`;
    if (msg.runId !== runId) fail(at, `runId ${msg.runId} differs from ${runId}`);
    if (msg.seq !== i + 1) fail(at, `seq is ${msg.seq}, expected ${i + 1}`);
    const ts = Date.parse(msg.ts);
    if (ts < lastTs) fail(at, 'ts goes backwards');
    lastTs = ts;
    if (TERMINAL.has(msg.type) && i !== sends.length - 1) {
      fail(at, `${msg.type} must be the last message`);
    }
    if (msg.type !== 'stage.update') return;

    const { stage, status } = msg.payload;
    const index = stageIds.indexOf(stage);
    if (index === -1) fail(at, `stage ${stage} is not in run.accepted`);
    if (index < lastStageIndex) fail(at, `stage ${stage} updates after a later stage`);
    if (finished.has(stage)) fail(at, `stage ${stage} updates after it finished`);
    if (STAGE_FINAL.has(status)) finished.add(stage);
    lastStageIndex = Math.max(lastStageIndex, index);
  });

  const last = sends.at(-1);
  if (!TERMINAL.has(last.type)) fail(where, 'the last message must be run.result or run.error');
  if (last.type === 'run.result') {
    if (finished.size !== stageIds.length) fail(where, 'run.result arrived before every stage finished');
    if (last.payload.style !== start.style) fail(where, 'run.result is not in the requested style');
    checkResult(where, last.payload);
  }

  steps.forEach((step, i) => {
    if (!step.await) return;
    const before = steps.slice(0, i).filter((s) => s.send).at(-1)?.send;
    if (step.await === 'prompt.answer' && before?.type !== 'prompt.request') {
      fail(where, `step ${i + 1} awaits prompt.answer without a prompt.request before it`);
    }
    if (step.await === 'run.cancel' && last.payload.code !== 'cancelled') {
      fail(where, `step ${i + 1} awaits run.cancel but the run does not end with code cancelled`);
    }
  });
}

const TAKES_FILE = 'takes.json';
const exampleFiles = readdirSync(examplesDir).filter(
  (name) => name.endsWith('.json') && name !== TAKES_FILE,
);
const scripts = [];
for (const name of exampleFiles) {
  const where = `ws/examples/${name}`;
  const script = readJson(join(examplesDir, name));
  if (!validateScript(script)) {
    explainScriptErrors(where, script);
    continue;
  }
  scripts.push(script);
  if (script.id !== basename(name, '.json')) fail(where, `id ${script.id} does not match the file name`);
  const sends = script.steps.filter((s) => s.send).map((s) => s.send);
  if (script.start === null) checkSession(where, sends);
  else checkRun(where, script);
}

const lastSend = (script) => script.steps.filter((s) => s.send).at(-1)?.send;

// A retell must name a run that another script finishes with a result.
const resultRunIds = new Set(
  scripts.map(lastSend).filter((m) => m?.type === 'run.result').map((m) => m.runId),
);
for (const script of scripts) {
  if (script.start && 'fromRunId' in script.start && !resultRunIds.has(script.start.fromRunId)) {
    fail(`ws/examples/${script.id}.json`, `retells ${script.start.fromRunId}, which no script finishes`);
  }
}

// One take per style, all of one match, and identical to any script result for
// the same match and style apart from usage, so the takes cannot drift.
const takesWhere = `ws/examples/${TAKES_FILE}`;
const takesDoc = readJson(join(examplesDir, TAKES_FILE));
const styleIds = readJson(join(root, 'ws', 'common.json')).$defs.StyleId.enum;
if (!validateTakes(takesDoc)) {
  for (const err of validateTakes.errors) fail(takesWhere, `${err.instancePath || '/'} ${err.message}`);
} else {
  const { takes } = takesDoc;
  const styles = takes.map((t) => t.style);
  for (const id of styleIds) {
    const count = styles.filter((s) => s === id).length;
    if (count !== 1) fail(takesWhere, `style ${id} has ${count} takes, expected 1`);
  }
  if (new Set(takes.map((t) => t.match.matchId)).size > 1) fail(takesWhere, 'takes cover more than one match');
  takes.forEach((take) => checkResult(`${takesWhere} (${take.style})`, take));
  const withoutUsage = ({ usage, ...rest }) => rest;
  for (const script of scripts) {
    const result = lastSend(script);
    if (result?.type !== 'run.result') continue;
    const take = takes.find(
      (t) => t.style === result.payload.style && t.match.matchId === result.payload.match.matchId,
    );
    if (take && !isDeepStrictEqual(withoutUsage(take), withoutUsage(result.payload))) {
      fail(`ws/examples/${script.id}.json`, `run.result differs from the ${take.style} take`);
    }
  }
}

if (failures.length) {
  console.error(failures.map((f) => `FAIL ${f}`).join('\n'));
  process.exit(1);
}
console.log(
  `ok: ${schemaFiles.length} schemas, ${exampleFiles.length} scripted runs, ${styleIds.length} takes`,
);
