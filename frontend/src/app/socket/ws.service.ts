import { DestroyRef, Injectable, inject, signal } from '@angular/core';
import { Observable, Subject, Subscription, retry, timer } from 'rxjs';
import { WebSocketSubject, webSocket } from 'rxjs/webSocket';
import { ClientMessage, ServerMessage, SessionHelloPayload } from '../contracts/contracts';
import { APP_CONFIG } from '../config';
import { ConnectionState, MatchdaySocket } from './socket';

const MAX_BACKOFF_MS = 30_000;

/** The real socket. Reconnects with exponential backoff and says hello again each time. */
@Injectable()
export class WsService extends MatchdaySocket {
  private readonly url = inject(APP_CONFIG).wsUrl;
  private readonly incoming = new Subject<ServerMessage>();
  private socket?: WebSocketSubject<unknown>;
  private subscription?: Subscription;

  readonly messages: Observable<ServerMessage> = this.incoming.asObservable();
  readonly state = signal<ConnectionState>('closed');

  constructor() {
    super();
    inject(DestroyRef).onDestroy(() => this.subscription?.unsubscribe());
  }

  connect(hello: SessionHelloPayload): void {
    if (!this.url) throw new Error('WsService needs APP_CONFIG.wsUrl');
    this.subscription?.unsubscribe();
    this.state.set('connecting');
    this.socket = webSocket({
      url: this.url,
      openObserver: {
        next: () => {
          this.state.set('open');
          this.socket?.next({ v: 1, type: 'session.hello', runId: null, payload: hello });
        },
      },
      closeObserver: { next: () => this.state.set('reconnecting') },
    });
    this.subscription = this.socket
      .pipe(
        retry({
          delay: (_err, attempt) => timer(Math.min(1000 * 2 ** (attempt - 1), MAX_BACKOFF_MS)),
          resetOnSuccess: true,
        }),
      )
      .subscribe({
        next: (message) => this.incoming.next(message as ServerMessage),
        complete: () => this.state.set('closed'),
      });
  }

  send(message: ClientMessage): void {
    this.socket?.next(message);
  }
}
