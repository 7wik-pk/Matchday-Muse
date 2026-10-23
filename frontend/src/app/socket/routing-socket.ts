import { Injectable, inject } from '@angular/core';
import { Observable, merge } from 'rxjs';
import {
  ClientMessage,
  RunStartPayload,
  ServerMessage,
  SessionHelloPayload,
} from '../contracts/contracts';
import { MockWsService } from '../mocks/mock-ws.service';
import { MatchdaySocket } from './socket';
import { WsService } from './ws.service';

/**
 * The socket for a deployment whose server has no LLM key. A run sent with
 * the user's own key goes to the backend; a run without one replays the sample
 * run (MockWsService: the week of 12 Oct 2026, with a take written in advance
 * for every style). The choice is made per run, from the message itself, so
 * adding or removing a key needs no reload. The backend connection carries the
 * session either way.
 */
@Injectable()
export class RoutingSocket extends MatchdaySocket {
  private readonly real = inject(WsService);
  private readonly sample = inject(MockWsService);
  /** Where the current run went: run.cancel and prompt.answer follow it. */
  private target: MatchdaySocket = this.real;

  readonly messages: Observable<ServerMessage> = merge(this.real.messages, this.sample.messages);
  readonly state = this.real.state;

  connect(hello: SessionHelloPayload): void {
    this.real.connect(hello);
  }

  send(message: ClientMessage): void {
    if (message.type === 'run.start') {
      this.target = message.payload.llm.mode === 'byok' ? this.real : this.sample;
    } else if (message.type === 'run.retell') {
      // A sample take is retold from the other takes; any other run, by the backend.
      this.target = this.isSample(message.payload.fromRunId) ? this.sample : this.real;
    }
    this.target.send(message);
  }

  /** True for a finished run that was the sample replay rather than the backend. */
  isSample(runId: string): boolean {
    return this.sample.hasRun(runId);
  }

  /** The sample run's request, so the controls can show its week. */
  sampleRequest(): Promise<RunStartPayload | null> {
    return this.sample.scriptStart();
  }
}
