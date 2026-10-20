import { TestBed } from '@angular/core/testing';
import {
  ClientMessage,
  RunResult,
  RunStartPayload,
  ServerMessage,
  StyleId,
} from '../contracts/contracts';
import { MOCK_OPTIONS, MockWsService } from './mock-ws.service';
import { RunScriptId, loadRunScript } from './scripts';
import { sendsOf } from './testing';

function setup(script: RunScriptId) {
  TestBed.configureTestingModule({
    providers: [
      { provide: MOCK_OPTIONS, useValue: { script, speed: 0, autoplay: false } },
      MockWsService,
    ],
  });
  const mock = TestBed.inject(MockWsService);
  const received: ServerMessage[] = [];
  mock.messages.subscribe((m) => received.push(m));
  return { mock, received };
}

const start = (mock: MockWsService, style?: StyleId) =>
  mock.send({ v: 1, type: 'run.start', runId: null, payload: { style } as RunStartPayload });

const retell = (mock: MockWsService, fromRunId: string, style: StyleId) =>
  mock.send({
    v: 1,
    type: 'run.retell',
    runId: null,
    payload: { fromRunId, style, output: 'text', llm: { mode: 'house' } },
  });

const send = (mock: MockWsService, type: 'run.cancel' | 'prompt.answer', choice = 'wait') =>
  mock.send(
    (type === 'run.cancel'
      ? { v: 1, type, runId: 'r', payload: {} }
      : { v: 1, type, runId: 'r', payload: { promptId: 'p', choice } }) as ClientMessage,
  );

const last = (received: ServerMessage[]) => received.at(-1);

describe('MockWsService', () => {
  it('sends session.ready on connect', async () => {
    const { mock, received } = setup('success');
    mock.connect({ sessionToken: null, timezone: 'Europe/London' });
    await vi.waitFor(() => expect(received.map((m) => m.type)).toEqual(['session.ready']));
    expect(mock.state()).toBe('open');
  });

  it('replays the selected script with fresh timestamps', async () => {
    const { mock, received } = setup('success');
    const expected = sendsOf(await loadRunScript('success'));
    const before = Date.now();
    start(mock);
    await vi.waitFor(() => expect(received).toHaveLength(expected.length));
    expect(received.map((m) => m.type)).toEqual(expected.map((m) => m.type));
    expect(received.map((m) => m.seq)).toEqual(expected.map((m) => m.seq));
    expect(Date.parse(received[0].ts)).toBeGreaterThanOrEqual(before);
  });

  it('pauses at a prompt until it is answered', async () => {
    const { mock, received } = setup('quota-exceeded');
    start(mock);
    await vi.waitFor(() => expect(last(received)?.type).toBe('prompt.request'));
    await new Promise((r) => setTimeout(r, 20));
    expect(last(received)?.type).toBe('prompt.request');
    send(mock, 'prompt.answer', 'wait');
    await vi.waitFor(() => expect(last(received)?.type).toBe('run.result'));
  });

  it('ends the run as cancelled when the prompt answer is cancel', async () => {
    const { mock, received } = setup('quota-exceeded');
    start(mock);
    await vi.waitFor(() => expect(last(received)?.type).toBe('prompt.request'));
    send(mock, 'prompt.answer', 'cancel');
    await vi.waitFor(() => expect(last(received)?.type).toBe('run.error'));
    const error = last(received);
    expect(error?.type === 'run.error' && error.payload.code).toBe('cancelled');
    expect(error?.seq).toBe(received.at(-2)!.seq + 1);
  });

  it('follows the script after a cancel it is waiting for', async () => {
    const { mock, received } = setup('cancelled');
    const expected = sendsOf(await loadRunScript('cancelled'));
    start(mock);
    // The script waits for Cancel once build_fact_sheet is running.
    await vi.waitFor(() =>
      expect(last(received)).toMatchObject({
        payload: { stage: 'build_fact_sheet', status: 'running' },
      }),
    );
    await new Promise((r) => setTimeout(r, 20));
    expect(received).toHaveLength(expected.length - 2);
    send(mock, 'run.cancel');
    await vi.waitFor(() => expect(received).toHaveLength(expected.length));
    expect(received.at(-1)).toMatchObject({
      ...expected.at(-1),
      runId: expect.any(String),
      ts: expect.any(String),
    });
  });

  it('gives every replay a runId of its own', async () => {
    const { mock, received } = setup('no-matches');
    start(mock);
    await vi.waitFor(() => expect(last(received)?.type).toBe('run.error'));
    start(mock);
    await vi.waitFor(() => expect(received.filter((m) => m.type === 'run.error')).toHaveLength(2));
    const runIds = new Set(received.map((m) => m.runId));
    expect(runIds.size).toBe(2);
  });

  it('answers in the requested style with that style’s take', async () => {
    const { mock, received } = setup('success');
    start(mock, 'terrace_chant');
    await vi.waitFor(() => expect(last(received)?.type).toBe('run.result'));
    const result = last(received) as RunResult;
    expect(result.payload.style).toBe('terrace_chant');
    expect(result.payload.text?.headline.text).toBe('Sing Up for Saturday at the Gtech');
  });

  it('retells a finished run with only the last three stages', async () => {
    const { mock, received } = setup('success');
    start(mock);
    await vi.waitFor(() => expect(last(received)?.type).toBe('run.result'));
    const fromRunId = last(received)!.runId!;
    const count = received.length;
    retell(mock, fromRunId, 'mock_heroic');
    await vi.waitFor(() => expect(received.length).toBeGreaterThan(count + 1));
    await vi.waitFor(() => expect(last(received)?.type).toBe('run.result'));
    const retold = received.slice(count);
    expect(retold[0]).toMatchObject({ type: 'run.accepted' });
    expect(retold[0].type === 'run.accepted' && retold[0].payload.stages.map((s) => s.id)).toEqual([
      'generate',
      'guardrails',
      'done',
    ]);
    const result = last(received) as RunResult;
    expect(result.runId).not.toBe(fromRunId);
    expect(result.payload.style).toBe('mock_heroic');
    // The retell's own usage, not the full run's.
    expect(result.payload.usage.inputTokens).toBe(6120);
  });

  it('refuses to retell a run it never finished', async () => {
    const { mock, received } = setup('success');
    retell(mock, 'r_unknown', 'limericks');
    expect(last(received)).toMatchObject({
      type: 'run.error',
      runId: null,
      payload: { code: 'retell_unavailable', retryable: false },
    });
  });

  it('stops a script with no await step when cancelled', async () => {
    const { mock, received } = setup('success');
    mock.speed.set(50);
    start(mock);
    await vi.waitFor(() => expect(received.length).toBeGreaterThan(3));
    send(mock, 'run.cancel');
    const error = last(received);
    expect(error?.type).toBe('run.error');
    expect(error?.type === 'run.error' && error.payload.code).toBe('cancelled');
    const count = received.length;
    await new Promise((r) => setTimeout(r, 300));
    expect(received).toHaveLength(count);
  });
});
