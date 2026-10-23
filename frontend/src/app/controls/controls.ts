import { Component, computed, input, model, output } from '@angular/core';
import {
  Competition,
  Granularity,
  OutputKind,
  RangeRequest,
  SessionReadyPayload,
  StyleId,
} from '../contracts/contracts';
import { RunPhase, isActive } from '../run/run-state';
import { rangeLabel, shiftRange, withGranularity } from '../range/range';
import { groupStyles } from '../styles/style-groups';

export const competitionKey = (c: Pick<Competition, 'sport' | 'league'>) =>
  `${c.sport}/${c.league}`;

const GRANULARITIES: { id: Granularity; label: string }[] = [
  { id: 'day', label: 'Day' },
  { id: 'week', label: 'Week' },
  { id: 'month', label: 'Month' },
];

/** Competition, range, style and output, plus Generate (Cancel while a run is active). */
@Component({
  selector: 'app-controls',
  templateUrl: './controls.html',
  styleUrl: './controls.css',
})
export class Controls {
  readonly session = input.required<SessionReadyPayload | null>();
  readonly phase = input.required<RunPhase>();
  readonly timeZone = input.required<string>();
  /** Why Image is unavailable, or null when it can be chosen. */
  readonly imageBlockedReason = input<string | null>(null);
  /** Why the competition and range are fixed (the sample run's), or null when they can change. */
  readonly rangeLock = input<string | null>(null);

  readonly competition = model.required<string>();
  readonly range = model.required<RangeRequest>();
  readonly style = model.required<StyleId>();
  readonly outputKind = model.required<OutputKind>();

  readonly generate = output<void>();
  readonly cancel = output<void>();

  protected readonly granularities = GRANULARITIES;
  protected readonly competitionKey = competitionKey;
  protected readonly active = computed(() => isActive(this.phase()));
  protected readonly label = computed(() => rangeLabel(this.range(), this.timeZone()));
  protected readonly unit = computed(() => this.range().granularity);
  protected readonly sports = computed(() => {
    const groups = new Map<string, Competition[]>();
    for (const c of this.session()?.competitions ?? []) {
      groups.set(c.sportLabel, [...(groups.get(c.sportLabel) ?? []), c]);
    }
    return [...groups].map(([label, competitions]) => ({ label, competitions }));
  });
  protected readonly styleGroups = computed(() => groupStyles(this.session()?.styles ?? []));
  protected readonly styleDescription = computed(
    () => this.session()?.styles.find((s) => s.id === this.style())?.description ?? '',
  );

  protected setGranularity(granularity: Granularity): void {
    this.range.update((range) => withGranularity(range, granularity));
  }

  protected shift(direction: -1 | 1): void {
    this.range.update((range) => shiftRange(range, direction));
  }

  protected setAnchor(value: string): void {
    if (!value) return;
    // <input type="month"> gives YYYY-MM.
    const anchor = value.length === 7 ? `${value}-01` : value;
    this.range.update((range) => ({ ...range, anchor }));
  }

  protected submit(event: Event): void {
    event.preventDefault();
    if (!this.active() && this.session()) this.generate.emit();
  }
}
