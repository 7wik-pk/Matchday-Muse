import { Component, computed, input, output } from '@angular/core';
import { RangeRequest, RunErrorPayload } from '../contracts/contracts';
import { GuardrailChips } from '../guardrail-chips/guardrail-chips';
import { StageView } from '../run/run-state';

export const ERROR_HEADLINES: Record<RunErrorPayload['code'], string> = {
  bad_message: 'Something went wrong',
  bad_request: 'That request can’t run',
  no_matches: 'No matches',
  cancelled: 'Run cancelled',
  stage_failed: 'A step failed',
  timeout: 'The run took too long',
  budget_exceeded: 'Budget used up',
  guardrail_failed: 'Held back by the fact check',
  quota_exceeded: 'Quota used up',
  provider_error: 'The LLM provider returned an error',
  interrupted: 'Connection lost',
  retell_unavailable: 'Can’t retell that run',
};

/** A run that ended without a result: what happened, why, and what to try next. */
@Component({
  selector: 'app-error-card',
  imports: [GuardrailChips],
  template: `
    @let e = error();
    <article class="error card" [attr.data-code]="e.code" role="alert">
      <p class="eyebrow">{{ eyebrow() }}</p>
      <h2>{{ e.message }}</h2>
      @if (e.reasons.length) {
        <ul class="reasons">
          @for (reason of e.reasons; track $index) {
            <li>{{ reason }}</li>
          }
        </ul>
      }
      @if (e.guardrails; as report) {
        <app-guardrail-chips [report]="report" />
      }
      @if (e.suggestion || e.retryable) {
        <div class="actions">
          @if (e.suggestion; as suggestion) {
            <button
              type="button"
              class="btn primary"
              (click)="trySuggestion.emit(suggestion.range)"
            >
              {{ suggestion.label }}
            </button>
          }
          @if (e.retryable) {
            <button
              type="button"
              class="btn"
              [class.primary]="!e.suggestion"
              (click)="retry.emit()"
            >
              Try again
            </button>
          }
        </div>
      }
    </article>
  `,
  styles: `
    .error {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 24px 28px;
      border-left: 4px solid var(--danger);
    }
    .error[data-code='cancelled'],
    .error[data-code='no_matches'] {
      border-left-color: var(--line);
    }
    h2 {
      font: 600 22px/1.3 var(--font-prose);
    }
    .reasons {
      margin: 0;
      padding-left: 18px;
      color: var(--ink-muted);
    }
    @media (max-width: 600px) {
      .error {
        padding: 18px;
      }
    }
  `,
})
export class ErrorCard {
  readonly error = input.required<RunErrorPayload>();
  readonly stages = input<StageView[]>([]);

  readonly retry = output<void>();
  readonly trySuggestion = output<RangeRequest>();

  protected readonly eyebrow = computed(() => {
    const { code, stage } = this.error();
    const label = stage ? this.stages().find((s) => s.id === stage)?.label : undefined;
    return label ? `${ERROR_HEADLINES[code]} · ${label}` : ERROR_HEADLINES[code];
  });
}
