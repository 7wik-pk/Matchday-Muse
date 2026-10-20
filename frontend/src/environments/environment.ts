import { AppConfig } from '../app/config';

export const environment: AppConfig = {
  // The backend's socket on this origin; ng serve proxies /ws to it
  // (proxy.conf.mjs). ?mock=<script> still replays a scripted run instead.
  wsUrl: `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`,
};
