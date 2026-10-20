import { Component, DestroyRef, computed, effect, inject, input, signal } from '@angular/core';
import { StageStatus, StageView } from '../run/run-state';

const STATUS_TEXT: Record<StageStatus, string> = {
  pending: 'Waiting',
  running: 'Running',
  done: 'Done',
  skipped: 'Skipped',
  failed: 'Failed',
};

/** "0.8 s", "12 s", "1 m 05 s". */
export function formatElapsed(ms: number): string {
  if (ms < 10_000) return `${(ms / 1000).toFixed(1)} s`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds} s`;
  return `${Math.floor(seconds / 60)} m ${String(seconds % 60).padStart(2, '0')} s`;
}

/** The vertical stepper built from run.accepted and driven by stage.update. */
@Component({
  selector: 'app-stage-panel',
  templateUrl: './stage-panel.html',
  styleUrl: './stage-panel.css',
})
export class StagePanel {
  readonly stages = input.required<StageView[]>();

  protected readonly statusText = STATUS_TEXT;
  private readonly now = signal(Date.now());
  private readonly running = computed(() => this.stages().some((s) => s.status === 'running'));

  constructor() {
    // Tick the elapsed time of the running stage.
    let timer: ReturnType<typeof setInterval> | undefined;
    effect(() => {
      clearInterval(timer);
      timer = undefined;
      if (this.running()) timer = setInterval(() => this.now.set(Date.now()), 200);
    });
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
  }

  protected elapsed(stage: StageView): string {
    if (stage.startedAt === null) return '';
    const end = stage.finishedAt ?? Math.max(this.now(), stage.startedAt);
    return formatElapsed(end - stage.startedAt);
  }
}
