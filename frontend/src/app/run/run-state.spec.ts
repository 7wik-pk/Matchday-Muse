import { RunStartPayload, ServerMessage } from '../contracts/contracts';
import { RUN_SCRIPT_IDS, loadRunScript } from '../mocks/scripts';
import { sendsOf } from '../mocks/testing';
import { IDLE_RUN, RunState, applyMessage, connectionLost, runStarting } from './run-state';

async function replay(id: (typeof RUN_SCRIPT_IDS)[number]): Promise<RunState> {
  const script = await loadRunScript(id);
  return sendsOf(script).reduce(applyMessage, runStarting(script.start as RunStartPayload));
}

describe('applyMessage', () => {
  it('ends every scripted run with exactly a result or an error', async () => {
    for (const id of RUN_SCRIPT_IDS) {
      const state = await replay(id);
      expect(['succeeded', 'failed'], id).toContain(state.phase);
      expect(Boolean(state.result) !== Boolean(state.error), id).toBe(true);
      expect(state.prompt, id).toBeNull();
    }
  });

  it('finishes every stage of a successful run, timed from the server timestamps', async () => {
    const state = await replay('success');
    expect(state.phase).toBe('succeeded');
    expect(state.result?.match.finalResult).toBe('Brentford 1–2 Liverpool');
    expect(state.stages.map((s) => s.status)).toEqual(Array(10).fill('done'));
    const pick = state.stages.find((s) => s.id === 'pick_match')!;
    expect(pick.detail).toContain('nine men');
    expect(pick.finishedAt! - pick.startedAt!).toBe(4100);
  });

  it('marks the failing stage and leaves later stages pending', async () => {
    const state = await replay('stage-failed');
    expect(state.error?.code).toBe('stage_failed');
    expect(state.stages.find((s) => s.id === 'fetch_matches')?.status).toBe('failed');
    expect(state.stages.find((s) => s.id === 'generate')?.status).toBe('pending');
  });

  it('holds a prompt until the run moves on', async () => {
    const script = await loadRunScript('quota-exceeded');
    const sends = sendsOf(script);
    const promptAt = sends.findIndex((m) => m.type === 'prompt.request');
    const waiting = sends.slice(0, promptAt + 1).reduce(applyMessage, runStarting(script.start!));
    expect(waiting.prompt?.kind).toBe('quota_exceeded');
    expect(waiting.phase).toBe('running');
  });

  it('ignores messages for another run and repeated seqs', async () => {
    const script = await loadRunScript('success');
    const [accepted, first, second] = sendsOf(script);
    const state = [accepted, first].reduce(applyMessage, runStarting(script.start!));
    expect(applyMessage(state, first)).toBe(state);
    expect(applyMessage(state, { ...second, runId: 'r_other' } as ServerMessage)).toBe(state);
    expect(applyMessage(IDLE_RUN, accepted)).toBe(IDLE_RUN);
  });

  it('keeps the cancelling phase while the current stage finishes', async () => {
    const script = await loadRunScript('cancelled');
    const sends = sendsOf(script);
    let state = runStarting(script.start!);
    state = applyMessage(state, sends[0]);
    state = { ...state, phase: 'cancelling' };
    state = sends.slice(1, -1).reduce(applyMessage, state);
    expect(state.phase).toBe('cancelling');
    expect(applyMessage(state, sends.at(-1)!).error?.code).toBe('cancelled');
  });

  it('accepts a run.error with no runId as the answer to a rejected run.start', () => {
    const state = applyMessage(runStarting({} as RunStartPayload), {
      v: 1,
      type: 'run.error',
      runId: null,
      seq: 0,
      ts: '2026-10-20T09:00:00Z',
      payload: {
        code: 'bad_request',
        message: 'Unknown league.',
        retryable: false,
        stage: null,
        reasons: [],
        guardrails: null,
        suggestion: null,
      },
    });
    expect(state.phase).toBe('failed');
    expect(state.error?.code).toBe('bad_request');
  });
});

describe('connectionLost', () => {
  it('ends an active run as interrupted, naming the running stage', async () => {
    const script = await loadRunScript('success');
    const sends = sendsOf(script);
    const state = sends.slice(0, 4).reduce(applyMessage, runStarting(script.start!));
    const lost = connectionLost(state);
    expect(lost.phase).toBe('failed');
    expect(lost.error?.code).toBe('interrupted');
    expect(lost.error?.stage).toBe('fetch_matches');
  });

  it('leaves a finished run alone', async () => {
    const state = await replay('success');
    expect(connectionLost(state)).toBe(state);
  });
});
