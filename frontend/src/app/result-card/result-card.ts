import { Component, computed, input, linkedSignal, output, signal } from '@angular/core';
import { RunErrorPayload, StyleId, StylePreset } from '../contracts/contracts';
import { ERROR_HEADLINES } from '../error-card/error-card';
import { GuardrailChips } from '../guardrail-chips/guardrail-chips';
import { Passage, plainText } from '../passage/passage';
import { Take } from '../run/run-store';
import { groupStyles } from '../styles/style-groups';

/** "Sat 17 Oct 2026" in the given timezone. Built from parts, since browsers differ on commas. */
export function matchDay(iso: string, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone,
  }).formatToParts(new Date(iso));
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value;
  return `${part('weekday')} ${part('day')} ${part('month')} ${part('year')}`;
}

export function formatCost(usd: number | null): string {
  if (usd === null) return 'cost unknown';
  return usd < 0.01 ? `about $${usd.toFixed(4)}` : `about $${usd.toFixed(2)}`;
}

/**
 * The takes of one match: a tab per style, then the selected take's headline
 * and passage, its sources, its guardrail checks and what it cost, and a way to
 * retell it in another style. The final score and the moment stay hidden until
 * the passage has been revealed, so its payoff is not spoiled.
 */
@Component({
  selector: 'app-result-card',
  imports: [GuardrailChips, Passage],
  templateUrl: './result-card.html',
  styleUrl: './result-card.css',
})
export class ResultCard {
  readonly takes = input.required<Take[]>();
  /** A sample take, written in advance: labelled as such, with no usage line. */
  readonly sample = input(false);
  readonly take = input.required<Take>();
  readonly styles = input.required<StylePreset[]>();
  readonly timeZone = input.required<string>();
  /** Takes whose passage has been shown in full; they are not typed out again. */
  readonly revealedIds = input<ReadonlySet<string>>(new Set());
  /** A run is in progress, so Retell is unavailable. */
  readonly busy = input(false);
  /** The style of a retell in progress, shown as a pending tab. */
  readonly pendingStyle = input<StyleId | null>(null);
  /** Why the last retell ended without a take. */
  readonly retellError = input<RunErrorPayload | null>(null);

  readonly select = output<string>();
  readonly retell = output<StyleId>();
  readonly retryRetell = output<void>();
  readonly revealed = output<string>();

  protected readonly copied = signal(false);
  protected readonly result = computed(() => this.take().result);
  protected readonly isRevealed = computed(
    () => this.result().output === 'image' || this.revealedIds().has(this.take().runId),
  );
  protected readonly styleGroups = computed(() => groupStyles(this.styles()));
  /** The first style not yet told, as the retell suggestion. */
  protected readonly retellStyle = linkedSignal<StyleId>(() => {
    const told = new Set(this.takes().map((t) => t.result.style));
    return (this.styles().find((s) => !told.has(s.id)) ?? this.styles()[0]).id;
  });
  protected readonly showTabs = computed(
    () => this.takes().length > 1 || this.pendingStyle() !== null,
  );
  protected readonly retellErrorText = computed(() => {
    const error = this.retellError();
    return error ? `${ERROR_HEADLINES[error.code]}: ${error.message}` : null;
  });

  protected readonly matchLine = computed(() => {
    const { competition, startTime, venue } = this.result().match;
    return [competition, matchDay(startTime, this.timeZone()), venue].filter(Boolean).join(' · ');
  });
  protected readonly tokens = computed(() => {
    const { inputTokens, outputTokens } = this.result().usage;
    return `${inputTokens.toLocaleString('en-GB')} in · ${outputTokens.toLocaleString('en-GB')} out`;
  });
  protected readonly cost = computed(() => formatCost(this.result().usage.costUsd));

  protected styleLabel(id: StyleId): string {
    return this.styles().find((s) => s.id === id)?.label ?? id;
  }

  protected async copy(): Promise<void> {
    const text = this.result().text;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(plainText(text));
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    } catch {
      // Clipboard blocked; the passage can still be selected by hand.
    }
  }
}
