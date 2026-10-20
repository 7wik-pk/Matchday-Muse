import { ApplicationConfig, Provider, provideBrowserGlobalErrorListeners } from '@angular/core';
import { environment } from '../environments/environment';
import { APP_CONFIG, AppConfig } from './config';
import { MOCK_OPTIONS, MockOptions, MockWsService } from './mocks/mock-ws.service';
import { DEFAULT_RUN_SCRIPT, isRunScriptId } from './mocks/scripts';
import { REVEAL_MS } from './passage/passage';
import { MatchdaySocket } from './socket/socket';
import { WsService } from './socket/ws.service';

/**
 * Real socket when a backend URL is set; otherwise, or with ?mock=<script>,
 * the mock. ?speed=<n> replays n times faster, the passage reveal included
 * (0 for instant).
 */
export function provideSocket(config: AppConfig, search: string): Provider[] {
  const params = new URLSearchParams(search);
  const requested = params.get('mock');
  if (config.wsUrl && requested === null) {
    return [WsService, { provide: MatchdaySocket, useExisting: WsService }];
  }
  const speed = Number(params.get('speed') ?? 1);
  const options: MockOptions = {
    script: isRunScriptId(requested) ? requested : DEFAULT_RUN_SCRIPT,
    speed: Number.isFinite(speed) && speed >= 0 ? speed : 1,
    autoplay: isRunScriptId(requested),
  };
  return [
    { provide: MOCK_OPTIONS, useValue: options },
    { provide: REVEAL_MS, useValue: options.speed > 0 ? 5000 / options.speed : 0 },
    MockWsService,
    { provide: MatchdaySocket, useExisting: MockWsService },
  ];
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    { provide: APP_CONFIG, useValue: environment },
    provideSocket(environment, location.search),
  ],
};
