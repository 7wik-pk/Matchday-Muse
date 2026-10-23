import { Injectable, InjectionToken, inject, signal } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import {
  AwaitStep,
  ClientMessage,
  MockScript,
  RunErrorPayload,
  RunResultPayload,
  RunStartPayload,
  ServerMessage,
  SessionHelloPayload,
  StageId,
  StyleId,
} from '../contracts/contracts';
import { ConnectionState, MatchdaySocket } from '../socket/socket';
import {
  DEFAULT_RUN_SCRIPT,
  RunScriptId,
  loadRetellScript,
  loadRunScript,
  loadSessionScript,
  loadTakes,
} from './scripts';

export interface MockOptions {
  /** The scripted run that answers the next run.start. */
  script: RunScriptId;
  /** Replay speed: 1 is real time, 4 is four times faster, 0 sends every step at once. */
  speed: number;
  /** Start the script's run as soon as the session is ready (set by ?mock=<id>). */
  autoplay: boolean;
}

export const MOCK_OPTIONS = new InjectionToken<MockOptions>('MOCK_OPTIONS', {
  factory: () => ({ script: DEFAULT_RUN_SCRIPT, speed: 1, autoplay: false }),
});

interface Replay {
  /** The style the client asked for; the script's run.result is swapped for that take. */
  style: StyleId | null;
  /** Replaces the script's runId, so every replay is a run of its own. */
  runId: string;
  /** Seq of the last run message sent; 0 until the run is accepted. */
  lastSeq: number;
  runningStage: StageId | null;
  waitingFor: { kind: AwaitStep['await']; resume: () => void } | null;
}

/**
 * Replays the scripted runs in contracts/ws/examples/ in place of the backend.
 * Every run.start plays the selected script and every run.retell the retell
 * script, with three rewrites: timestamps become the moment each message is
 * sent, each replay gets a fresh runId, and the run.result is swapped for the
 * take in the requested style (from takes.json), keeping the script's usage.
 */
@Injectable()
export class MockWsService extends MatchdaySocket {
  private readonly options = inject(MOCK_OPTIONS);
  private readonly incoming = new Subject<ServerMessage>();
  private replay: Replay | null = null;
  private replays = 0;
  /** Runs that ended in run.result, which a retell may name. */
  private readonly finishedRuns = new Set<string>();

  readonly messages: Observable<ServerMessage> = this.incoming.asObservable();
  readonly state = signal<ConnectionState>('closed');
  readonly script = signal<RunScriptId>(this.options.script);
  readonly speed = signal(this.options.speed);
  readonly autoplay = this.options.autoplay;

  connect(_hello: SessionHelloPayload): void {
    this.state.set('connecting');
    void loadSessionScript().then((script) => {
      this.state.set('open');
      return this.play(script, this.startReplay(null));
    });
  }

  send(message: ClientMessage): void {
    switch (message.type) {
      case 'run.start': {
        const replay = this.startReplay(message.payload.style);
        void loadRunScript(this.script()).then((script) => this.play(script, replay));
        return;
      }
      case 'run.retell': {
        if (!this.finishedRuns.has(message.payload.fromRunId)) {
          this.retellUnavailable();
          return;
        }
        const replay = this.startReplay(message.payload.style);
        void loadRetellScript().then((script) => this.play(script, replay));
        return;
      }
      case 'run.cancel':
        if (!this.resumeIfWaiting('run.cancel')) this.cancelReplay();
        return;
      case 'prompt.answer':
        if (message.payload.choice === 'cancel') this.cancelReplay();
        else if (message.payload.choice === 'switch_model') this.endForModelSwitch();
        else this.resumeIfWaiting('prompt.answer');
        return;
    }
  }

  /** True for a run this mock replayed through to its run.result. */
  hasRun(runId: string): boolean {
    return this.finishedRuns.has(runId);
  }

  /** The run.start payload of the selected script, so the controls can match it. */
  async scriptStart(): Promise<RunStartPayload | null> {
    // Every selectable script answers a run.start; only the retell script does not.
    return (await loadRunScript(this.script())).start as RunStartPayload | null;
  }

  private startReplay(style: StyleId | null): Replay {
    this.replays += 1;
    this.replay = {
      style,
      runId: `r_mock_${this.replays}`,
      lastSeq: 0,
      runningStage: null,
      waitingFor: null,
    };
    return this.replay;
  }

  private async play(script: MockScript, replay: Replay): Promise<void> {
    for (const step of script.steps) {
      if (this.replay !== replay) return;
      if ('await' in step) {
        await new Promise<void>((resume) => (replay.waitingFor = { kind: step.await, resume }));
        replay.waitingFor = null;
        continue;
      }
      await this.sleep(step.delayMs);
      let message = { ...step.send, ts: new Date().toISOString() } as ServerMessage;
      if (message.runId !== null) message = { ...message, runId: replay.runId } as ServerMessage;
      if (message.type === 'run.result') {
        message = { ...message, payload: await this.takeFor(message.payload, replay.style) };
      }
      if (this.replay !== replay) return;
      replay.lastSeq = message.seq;
      if (message.type === 'stage.update') {
        replay.runningStage = message.payload.status === 'running' ? message.payload.stage : null;
      }
      if (message.type === 'run.result') this.finishedRuns.add(replay.runId);
      this.incoming.next(message);
    }
    if (this.replay === replay) this.replay = null;
  }

  /** The take in the requested style for the same match, keeping the script's usage. */
  private async takeFor(
    result: RunResultPayload,
    style: StyleId | null,
  ): Promise<RunResultPayload> {
    if (!style || style === result.style) return result;
    const { takes } = await loadTakes();
    const take = takes.find((t) => t.style === style && t.match.matchId === result.match.matchId);
    return take ? { ...take, usage: result.usage } : result;
  }

  private resumeIfWaiting(kind: AwaitStep['await']): boolean {
    const waiting = this.replay?.waitingFor;
    if (waiting?.kind !== kind) return false;
    waiting.resume();
    return true;
  }

  /** Cancel pressed where the script has no await step: stop and end the run as the backend would. */
  private cancelReplay(): void {
    const replay = this.replay;
    if (!replay?.lastSeq) return;
    this.replay = null;
    this.emitError(replay.runId, replay.lastSeq + 1, {
      code: 'cancelled',
      message: 'Run cancelled. Nothing was generated.',
      retryable: true,
      stage: replay.runningStage,
    });
  }

  /** "Switch model" ends the run; the user retries it on the model they choose. */
  private endForModelSwitch(): void {
    const replay = this.replay;
    if (!replay?.lastSeq) return;
    this.replay = null;
    this.emitError(replay.runId, replay.lastSeq + 1, {
      code: 'quota_exceeded',
      message: 'Run stopped so you can switch model. Choose one in Your LLM, then try again.',
      retryable: true,
      stage: replay.runningStage,
    });
  }

  /** A retell of a run the mock never finished, as after a page reload. */
  private retellUnavailable(): void {
    this.emitError(null, 0, {
      code: 'retell_unavailable',
      message: 'That run is no longer available to retell. Generate a new one.',
      retryable: false,
      stage: null,
    });
  }

  private emitError(
    runId: string | null,
    seq: number,
    error: Pick<RunErrorPayload, 'code' | 'message' | 'retryable' | 'stage'>,
  ): void {
    this.incoming.next({
      v: 1,
      type: 'run.error',
      runId,
      seq,
      ts: new Date().toISOString(),
      payload: { ...error, reasons: [], guardrails: null, suggestion: null },
    });
  }

  private sleep(delayMs: number): Promise<void> {
    const speed = this.speed();
    return new Promise((resolve) => setTimeout(resolve, speed > 0 ? delayMs / speed : 0));
  }
}
