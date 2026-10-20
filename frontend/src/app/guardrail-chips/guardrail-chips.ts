import { Component, input } from '@angular/core';
import { GuardrailReport } from '../contracts/contracts';

const STATUS_TEXT = { pass: 'passed', fail: 'failed', skipped: 'skipped' } as const;

/** One chip per guardrail check; the check's detail shows on hover. */
@Component({
  selector: 'app-guardrail-chips',
  template: `
    <ul class="chips" aria-label="Guardrail checks">
      @for (check of report().checks; track check.id) {
        <li class="chip" [attr.data-status]="check.status" [attr.title]="check.detail">
          <span aria-hidden="true">{{ icons[check.status] }}</span>
          {{ check.label }}
          <span class="visually-hidden"
            >{{ statusText[check.status] }}{{ check.detail ? ': ' + check.detail : '' }}</span
          >
        </li>
      }
    </ul>
    @if (report().attempts > 1) {
      <p class="hint">
        {{ report().passed ? 'Passed after one rewrite.' : 'Failed again after one rewrite.' }}
      </p>
    }
  `,
  styles: `
    :host {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px 12px;
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
  `,
})
export class GuardrailChips {
  readonly report = input.required<GuardrailReport>();

  protected readonly icons = { pass: '✓', fail: '✕', skipped: '–' } as const;
  protected readonly statusText = STATUS_TEXT;
}
