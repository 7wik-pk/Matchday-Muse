import {
  PromptRequestPayload,
  RunErrorPayload,
  RunResultPayload,
  RunRetellPayload,
  RunStartPayload,
  ServerMessage,
  StageId,
  StageUpdatePayload,
} from '../contracts/contracts';

export type StageStatus = 'pending' | StageUpdatePayload['status'];

export interface StageView {
  id: StageId;
  label: string;
  status: StageStatus;
  message: string | null;
  progress: number | null;
  detail: string | null;
  /** Epoch ms of the first `running` update. */
  startedAt: number | null;
  /** Epoch ms of the `done`, `skipped` or `failed` update. */
  finishedAt: number | null;
}

export type RunPhase = 'idle' | 'starting' | 'running' | 'cancelling' | 'succeeded' | 'failed';

/** What started a run: a full run.start, or a run.retell of an earlier result. */
export type RunRequest = RunStartPayload | RunRetellPayload;

export const isRetell = (request: RunRequest | null): request is RunRetellPayload =>
  request !== null && 'fromRunId' in request;

export interface RunState {
  phase: RunPhase;
  request: RunRequest | null;
  runId: string | null;
  lastSeq: number;
  stages: StageView[];
  prompt: PromptRequestPayload | null;
  result: RunResultPayload | null;
  error: RunErrorPayload | null;
}

export const IDLE_RUN: RunState = {
  phase: 'idle',
  request: null,
  runId: null,
  lastSeq: 0,
  stages: [],
  prompt: null,
  result: null,
  error: null,
};

const FINAL = new Set<StageStatus>(['done', 'skipped', 'failed']);

export const isActive = (phase: RunPhase) =>
  phase === 'starting' || phase === 'running' || phase === 'cancelling';

/** A run.start or run.retell was sent; nothing has come back yet. */
export function runStarting(request: RunRequest): RunState {
  return { ...IDLE_RUN, phase: 'starting', request };
}

/** Applies one server message to the current run. Messages for other runs, or replays of old seqs, are ignored. */
export function applyMessage(state: RunState, message: ServerMessage): RunState {
  if (message.type === 'session.ready') return state;

  if (message.type === 'run.accepted') {
    if (state.phase !== 'starting' && state.phase !== 'cancelling') return state;
    return {
      ...state,
      phase: state.phase === 'cancelling' ? 'cancelling' : 'running',
      runId: message.runId,
      lastSeq: message.seq,
      stages: message.payload.stages.map((s) => ({
        id: s.id,
        label: s.label,
        status: 'pending',
        message: null,
        progress: null,
        detail: null,
        startedAt: null,
        finishedAt: null,
      })),
    };
  }

  // A run.error with no runId answers a message that never started a run, such as a bad run.start.
  const rejected =
    message.type === 'run.error' && message.runId === null && state.phase === 'starting';
  if (!rejected && (message.runId !== state.runId || message.seq <= state.lastSeq)) return state;
  const next = { ...state, lastSeq: message.seq };
  const at = Date.parse(message.ts);

  switch (message.type) {
    case 'stage.update': {
      const update = message.payload;
      return {
        ...next,
        stages: state.stages.map((stage) =>
          stage.id !== update.stage
            ? stage
            : {
                ...stage,
                status: update.status,
                message: update.message,
                progress: update.progress,
                detail: update.detail ?? stage.detail,
                startedAt: stage.startedAt ?? at,
                finishedAt: FINAL.has(update.status) ? at : null,
              },
        ),
      };
    }
    case 'prompt.request':
      return { ...next, prompt: message.payload };
    case 'run.result':
      return { ...next, phase: 'succeeded', prompt: null, result: message.payload };
    case 'run.error':
      return { ...next, phase: 'failed', prompt: null, error: message.payload };
  }
}

/** The socket dropped mid-run. Until Phase 3 the backend cancels the run, so the UI ends it too. */
export function connectionLost(state: RunState): RunState {
  if (!isActive(state.phase)) return state;
  return {
    ...state,
    phase: 'failed',
    prompt: null,
    error: {
      code: 'interrupted',
      message: 'The connection to the server dropped, so the run was stopped.',
      retryable: true,
      stage: state.stages.find((s) => s.status === 'running')?.id ?? null,
      reasons: [],
      guardrails: null,
      suggestion: null,
    },
  };
}
