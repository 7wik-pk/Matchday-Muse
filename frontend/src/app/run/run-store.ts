import { DestroyRef, Injectable, computed, effect, inject, signal } from '@angular/core';
import {
  LlmChoice,
  RunResultPayload,
  RunStartPayload,
  SessionReadyPayload,
  StyleId,
} from '../contracts/contracts';
import { MatchdaySocket } from '../socket/socket';
import { browserTimeZone } from '../range/range';
import {
  IDLE_RUN,
  RunRequest,
  RunState,
  applyMessage,
  connectionLost,
  isActive,
  isRetell,
  runStarting,
} from './run-state';

/** One finished retelling of the current match: the full run's, or a retell's. */
export interface Take {
  runId: string;
  result: RunResultPayload;
}

/** The most takes kept per match; the oldest retell drops out first. */
export const MAX_TAKES = 6;

/** Adds a take, keeping the full run's take first and at most MAX_TAKES in all. */
export function addTake(takes: Take[], take: Take): Take[] {
  const next = [...takes, take];
  return next.length > MAX_TAKES ? [next[0], ...next.slice(-(MAX_TAKES - 1))] : next;
}

/** The session, the current run, and the takes of the current match, as signals fed by the socket. */
@Injectable({ providedIn: 'root' })
export class RunStore {
  private readonly socket = inject(MatchdaySocket);

  readonly timeZone = browserTimeZone();
  readonly session = signal<SessionReadyPayload | null>(null);
  readonly run = signal<RunState>(IDLE_RUN);
  readonly active = computed(() => isActive(this.run().phase));
  readonly connection = this.socket.state;

  readonly takes = signal<Take[]>([]);
  readonly selectedRunId = signal<string | null>(null);
  readonly selectedTake = computed(
    () => this.takes().find((t) => t.runId === this.selectedRunId()) ?? this.takes().at(-1) ?? null,
  );
  /** True while the current run, or its outcome, is a retell of the takes shown. */
  readonly retelling = computed(() => isRetell(this.run().request));

  constructor() {
    const subscription = this.socket.messages.subscribe((message) => {
      if (message.type === 'session.ready') {
        this.session.set(message.payload);
        return;
      }
      const before = this.run();
      const after = applyMessage(before, message);
      this.run.set(after);
      if (message.type === 'run.result' && after !== before && after.runId) {
        const take = { runId: after.runId, result: message.payload };
        this.takes.update((takes) => (isRetell(after.request) ? addTake(takes, take) : [take]));
        this.selectedRunId.set(after.runId);
      }
    });
    inject(DestroyRef).onDestroy(() => subscription.unsubscribe());

    effect(() => {
      if (this.connection() === 'reconnecting') this.run.update(connectionLost);
    });
  }

  connect(): void {
    this.socket.connect({ sessionToken: null, timezone: this.timeZone });
  }

  start(request: RunStartPayload): void {
    if (this.active()) return;
    this.takes.set([]);
    this.selectedRunId.set(null);
    this.run.set(runStarting(request));
    this.socket.send({ v: 1, type: 'run.start', runId: null, payload: request });
  }

  /** Retells the current match in another style, from the full run's fact sheet. */
  retell(style: StyleId, llm: LlmChoice): void {
    const source = this.takes()[0];
    if (this.active() || !source) return;
    const request = { fromRunId: source.runId, style, output: source.result.output, llm };
    this.run.set(runStarting(request));
    this.socket.send({ v: 1, type: 'run.retell', runId: null, payload: request });
  }

  /** Starts the same request again, with the current LLM choice. */
  repeat(request: RunRequest, llm: LlmChoice): void {
    if (isRetell(request)) this.retell(request.style, llm);
    else this.start({ ...request, llm });
  }

  cancel(): void {
    const { runId, phase } = this.run();
    if (!runId || phase !== 'running') return;
    this.run.update((run) => ({ ...run, phase: 'cancelling' }));
    this.socket.send({ v: 1, type: 'run.cancel', runId, payload: {} });
  }

  answer(choice: string): void {
    const { runId, prompt } = this.run();
    if (!runId || !prompt) return;
    this.run.update((run) => ({ ...run, prompt: null }));
    this.socket.send({
      v: 1,
      type: 'prompt.answer',
      runId,
      payload: { promptId: prompt.promptId, choice },
    });
  }
}
