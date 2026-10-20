import {
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  computed,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { PromptRequestPayload } from '../contracts/contracts';

const TITLES: Record<PromptRequestPayload['kind'], string> = {
  free_runs_exhausted: 'Free runs used up',
  quota_exceeded: 'Quota reached',
  switch_model: 'Switch model?',
};

/** "38 s", "4 m 05 s", "6 h 12 m". */
export function formatCountdown(seconds: number): string {
  if (seconds < 60) return `${seconds} s`;
  if (seconds < 3600)
    return `${Math.floor(seconds / 60)} m ${String(seconds % 60).padStart(2, '0')} s`;
  return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} m`;
}

/** A mid-run question from the backend. The run waits until one option is chosen. */
@Component({
  selector: 'app-prompt-modal',
  template: `
    @let p = prompt();
    <div class="backdrop">
      <div
        class="dialog card"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="prompt-title"
        aria-describedby="prompt-message"
      >
        <h2 id="prompt-title">{{ title() }}</h2>
        <p id="prompt-message">{{ p.message }}</p>
        @if (remaining(); as seconds) {
          <p class="hint countdown" aria-live="off">Resets in {{ countdown(seconds) }}</p>
        }
        <div class="actions" #actions>
          @for (option of p.options; track option.id) {
            <button
              type="button"
              class="btn"
              [class.primary]="$first"
              (click)="answer.emit(option.id)"
            >
              {{ option.label }}
            </button>
          }
        </div>
      </div>
    </div>
  `,
  styles: `
    .backdrop {
      position: fixed;
      inset: 0;
      z-index: 20;
      display: grid;
      place-items: center;
      padding: 16px;
      background: rgb(0 0 0 / 40%);
    }
    .dialog {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: min(440px, 100%);
      padding: 24px;
    }
    h2 {
      font: 600 22px/1.3 var(--font-prose);
    }
    .countdown {
      font-variant-numeric: tabular-nums;
    }
  `,
})
export class PromptModal {
  readonly prompt = input.required<PromptRequestPayload>();
  readonly answer = output<string>();

  private readonly actions = viewChild.required<ElementRef<HTMLElement>>('actions');
  private readonly openedAt = Date.now();
  private readonly now = signal(Date.now());

  protected readonly title = computed(() => TITLES[this.prompt().kind]);
  protected readonly countdown = formatCountdown;
  protected readonly remaining = computed(() => {
    const total = this.prompt().retryAfterSeconds;
    if (total === null) return null;
    return Math.max(0, total - Math.floor((this.now() - this.openedAt) / 1000)) || null;
  });

  constructor() {
    const timer = setInterval(() => this.now.set(Date.now()), 1000);
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
    afterNextRender(() => this.actions().nativeElement.querySelector('button')?.focus());
  }
}
