import { InjectionToken } from '@angular/core';

export interface AppConfig {
  /** Backend WebSocket URL. Null means there is no backend yet, so the app replays mock runs. */
  wsUrl: string | null;
}

export const APP_CONFIG = new InjectionToken<AppConfig>('APP_CONFIG');
