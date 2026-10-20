import { Signal } from '@angular/core';
import { Observable } from 'rxjs';
import { ClientMessage, ServerMessage, SessionHelloPayload } from '../contracts/contracts';

export type ConnectionState = 'connecting' | 'open' | 'reconnecting' | 'closed';

/**
 * The one socket to the backend. WsService talks to the real /ws endpoint;
 * MockWsService replays the scripted runs in contracts/ws/examples/.
 */
export abstract class MatchdaySocket {
  abstract readonly messages: Observable<ServerMessage>;
  abstract readonly state: Signal<ConnectionState>;

  /** Opens the socket and sends session.hello, again after every reconnect. */
  abstract connect(hello: SessionHelloPayload): void;

  abstract send(message: ClientMessage): void;
}
