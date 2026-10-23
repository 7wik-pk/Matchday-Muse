import { InjectionToken } from '@angular/core';

export interface AppConfig {
  /** Backend WebSocket URL. Null means there is no backend yet, so the app replays mock runs. */
  wsUrl: string | null;
  /**
   * Runs without the user's own key replay the sample run instead of reaching
   * the backend (RoutingSocket). On in production, where the server has no LLM
   * key; off under ng serve, where such runs use the server's development key.
   */
  samplesWithoutKey?: boolean;
}

export const APP_CONFIG = new InjectionToken<AppConfig>('APP_CONFIG');
