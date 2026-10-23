import { AppConfig } from '../app/config';

// The production build. ng serve uses environment.development.ts instead.
export const environment: AppConfig = {
  // The backend's socket on this origin. ?mock=<script> still replays a
  // scripted run instead.
  wsUrl: `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`,
  // The server has no LLM key in production, so a visitor without one sees the sample run.
  samplesWithoutKey: true,
};
