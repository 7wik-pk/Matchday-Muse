import { MockScript, MockTakes } from '../contracts/contracts';

// The scripted runs in contracts/ws/examples/. `make test` validates them
// against the contracts, so they are cast here rather than checked again.
// Each loads as its own chunk, so a build with a real backend never fetches them.
const loaders = {
  success: () => import('@contracts/ws/examples/success.json'),
  'quota-exceeded': () => import('@contracts/ws/examples/quota-exceeded.json'),
  'guardrail-failed': () => import('@contracts/ws/examples/guardrail-failed.json'),
  'no-matches': () => import('@contracts/ws/examples/no-matches.json'),
  cancelled: () => import('@contracts/ws/examples/cancelled.json'),
  'stage-failed': () => import('@contracts/ws/examples/stage-failed.json'),
};

export type RunScriptId = keyof typeof loaders;
export const RUN_SCRIPT_IDS = Object.keys(loaders) as RunScriptId[];
export const DEFAULT_RUN_SCRIPT: RunScriptId = 'success';

export const isRunScriptId = (id: string | null): id is RunScriptId =>
  id !== null && Object.hasOwn(loaders, id);

export async function loadRunScript(id: RunScriptId): Promise<MockScript> {
  return (await loaders[id]()).default as unknown as MockScript;
}

export async function loadSessionScript(): Promise<MockScript> {
  return (await import('@contracts/ws/examples/session.json')).default as unknown as MockScript;
}

/** Answers every run.retell; its result is swapped for the take in the requested style. */
export async function loadRetellScript(): Promise<MockScript> {
  return (await import('@contracts/ws/examples/retell.json')).default as unknown as MockScript;
}

/** One run.result per style preset, all for the same match. */
export async function loadTakes(): Promise<MockTakes> {
  return (await import('@contracts/ws/examples/takes.json')).default as unknown as MockTakes;
}
