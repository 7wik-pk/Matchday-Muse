import { AppConfig } from '../app/config';

export const environment: AppConfig = {
  // No backend yet, so the app replays the scripted runs. Once the backend
  // exists, set this to the /ws URL; ?mock=<script> still forces the mock.
  wsUrl: null,
};
