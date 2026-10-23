import { Injectable, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import {
  ClientMessage,
  LlmChoice,
  RunStartPayload,
  ServerMessage,
  SessionHelloPayload,
  StyleId,
} from '../contracts/contracts';
import { MOCK_OPTIONS, MockWsService } from '../mocks/mock-ws.service';
import { RoutingSocket } from './routing-socket';
import { ConnectionState, MatchdaySocket } from './socket';
import { WsService } from './ws.service';

/** Stands in for the backend: records what it is sent. */
@Injectable()
class FakeBackend extends MatchdaySocket {
  readonly incoming = new Subject<ServerMessage>();
  readonly messages = this.incoming.asObservable();
  readonly state = signal<ConnectionState>('closed');
  readonly sent: ClientMessage[] = [];
  hello: SessionHelloPayload | null = null;

  connect(hello: SessionHelloPayload): void {
    this.hello = hello;
    this.state.set('open');
  }

  send(message: ClientMessage): void {
    this.sent.push(message);
  }
}

const BYOK: LlmChoice = {
  mode: 'byok',
  provider: 'groq',
  model: 'groq/openai/gpt-oss-120b',
  apiKey: 'k',
};

function setup() {
  TestBed.configureTestingModule({
    providers: [
      { provide: MOCK_OPTIONS, useValue: { script: 'success', speed: 0, autoplay: false } },
      { provide: WsService, useClass: FakeBackend },
      MockWsService,
      RoutingSocket,
    ],
  });
  const socket = TestBed.inject(RoutingSocket);
  const backend = TestBed.inject(WsService) as unknown as FakeBackend;
  const received: ServerMessage[] = [];
  socket.messages.subscribe((m) => received.push(m));
  return { socket, backend, received };
}

const start = (socket: RoutingSocket, llm: LlmChoice, style: StyleId = 'ballad') =>
  socket.send({
    v: 1,
    type: 'run.start',
    runId: null,
    payload: { style, output: 'text', llm } as RunStartPayload,
  });

const retell = (socket: RoutingSocket, fromRunId: string, style: StyleId) =>
  socket.send({
    v: 1,
    type: 'run.retell',
    runId: null,
    payload: { fromRunId, style, output: 'text', llm: { mode: 'house' } },
  });

const result = (received: ServerMessage[]) => received.find((m) => m.type === 'run.result');

describe('RoutingSocket', () => {
  it('connects only the backend, and takes its connection state', () => {
    const { socket, backend } = setup();
    socket.connect({ sessionToken: null, timezone: 'Europe/London' });
    expect(backend.hello?.timezone).toBe('Europe/London');
    expect(socket.state()).toBe('open');
  });

  it('replays the sample run when there is no key, in the chosen style', async () => {
    const { socket, backend, received } = setup();
    start(socket, { mode: 'house' }, 'limericks');
    await vi.waitFor(() => expect(result(received)).toBeDefined());
    const done = result(received)!;
    expect(done.type === 'run.result' && done.payload.style).toBe('limericks');
    expect(backend.sent).toEqual([]);
    expect(socket.isSample(done.runId!)).toBe(true);
  });

  it('sends runs with the user key to the backend', () => {
    const { socket, backend, received } = setup();
    start(socket, BYOK);
    expect(backend.sent.map((m) => m.type)).toEqual(['run.start']);
    expect(received).toEqual([]);
    expect(socket.isSample('r_backend')).toBe(false);
  });

  it('decides per run, so adding a key needs no reload', async () => {
    const { socket, backend, received } = setup();
    start(socket, { mode: 'house' });
    await vi.waitFor(() => expect(result(received)).toBeDefined());
    start(socket, BYOK);
    expect(backend.sent.map((m) => m.type)).toEqual(['run.start']);
  });

  it('retells a sample from the samples and any other run on the backend', async () => {
    const { socket, backend, received } = setup();
    start(socket, { mode: 'house' });
    await vi.waitFor(() => expect(result(received)).toBeDefined());
    retell(socket, result(received)!.runId!, 'sonnet');
    await vi.waitFor(() =>
      expect(received.filter((m) => m.type === 'run.result').at(-1)).toMatchObject({
        payload: { style: 'sonnet' },
      }),
    );
    expect(backend.sent).toEqual([]);

    retell(socket, 'r_backend', 'sonnet');
    expect(backend.sent.map((m) => m.type)).toEqual(['run.retell']);
  });

  it('sends run.cancel where the run went', () => {
    const { socket, backend } = setup();
    start(socket, BYOK);
    socket.send({ v: 1, type: 'run.cancel', runId: 'r_backend', payload: {} });
    expect(backend.sent.map((m) => m.type)).toEqual(['run.start', 'run.cancel']);
  });

  it('offers the sample run request, for the controls', async () => {
    const { socket } = setup();
    const request = await socket.sampleRequest();
    expect(request?.range).toEqual({ granularity: 'week', anchor: expect.any(String) });
  });
});
