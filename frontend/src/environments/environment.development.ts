import { AppConfig } from '../app/config';

// ng serve (the development build).
export const environment: AppConfig = {
  // The backend's socket on this origin; ng serve proxies /ws to it
  // (proxy.conf.mjs). ?mock=<script> still replays a scripted run instead.
  wsUrl: `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`,
  // Runs without a key in the browser use the server's LLM_API_KEY, if set.
  samplesWithoutKey: false,
};
