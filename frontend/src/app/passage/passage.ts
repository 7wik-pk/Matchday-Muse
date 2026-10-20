import { NgTemplateOutlet } from '@angular/common';
import {
  Component,
  InjectionToken,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { Fact, Line, PassageText, SourceLink } from '../contracts/contracts';

/** How long the reveal takes in milliseconds, whatever the poem's length; 0 shows it at once. */
export const REVEAL_MS = new InjectionToken<number>('REVEAL_MS', { factory: () => 5000 });
const TICK_MS = 40;

const wordsOf = (text: string) => text.split(/\s+/).filter(Boolean);

/** The headline and poem as plain text: one line per line, a blank line between stanzas. */
export function plainText(text: PassageText): string {
  const stanzas = text.stanzas.map((s) => s.lines.map((l) => l.text).join('\n'));
  return [text.headline.text, ...stanzas].join('\n\n');
}

interface LineView extends Line {
  key: string;
  /** The line's words, each but the last with its following space, so the template adds none. */
  words: string[];
  /** Index of this line's first word in the whole text, headline first. */
  start: number;
}

/**
 * The headline and poem. A new take types itself out word by word over about
 * five seconds (REVEAL_MS; a click, a tap or any key skips to the end). The
 * words not yet revealed are laid out but transparent, so nothing jumps, and
 * screen readers have the full text from the start. Once revealed, "Show your
 * working" underlines every line that rests on facts and lists those facts.
 */
@Component({
  selector: 'app-passage',
  imports: [NgTemplateOutlet],
  templateUrl: './passage.html',
  styleUrl: './passage.css',
  host: { '(document:keydown)': 'onKey($event)' },
})
export class Passage {
  readonly text = input.required<PassageText>();
  readonly facts = input.required<Fact[]>();
  readonly sources = input.required<SourceLink[]>();
  /** Type the text out; false shows it at once (a take already seen). */
  readonly animate = input(false);
  /** Emitted once the whole text is showing. */
  readonly revealed = output<void>();

  private readonly revealMs = inject(REVEAL_MS);

  private readonly view = computed(() => {
    let start = 0;
    let index = 0;
    const toView = (line: Line): LineView => {
      const words = wordsOf(line.text).map((word, i, all) =>
        i < all.length - 1 ? `${word} ` : word,
      );
      const view = { ...line, key: `l${index++}`, words, start };
      start += words.length;
      return view;
    };
    const { headline, stanzas } = this.text();
    return {
      headline: toView(headline),
      stanzas: stanzas.map((s) => s.lines.map(toView)),
      total: start,
    };
  });
  protected readonly headline = computed(() => this.view().headline);
  protected readonly stanzas = computed(() => this.view().stanzas);

  protected readonly shown = signal(0);
  protected readonly done = computed(() => this.shown() >= this.view().total);

  protected readonly working = signal(false);
  protected readonly activeKey = signal<string | null>(null);
  protected readonly activeFacts = computed(() => {
    const key = this.activeKey();
    const { headline, stanzas } = this.view();
    const line = [headline, ...stanzas.flat()].find((l) => l.key === key);
    if (!line) return [];
    const titles = new Map(this.sources().map((s) => [s.url, s.title]));
    return line.factIds.flatMap((id) => {
      const fact = this.facts().find((f) => f.id === id);
      return fact ? [{ ...fact, sourceTitle: titles.get(fact.sourceUrl) ?? fact.sourceUrl }] : [];
    });
  });

  constructor() {
    effect((onCleanup) => {
      const total = this.view().total;
      const duration = this.revealMs;
      const animate = this.animate() && duration > 0 && !prefersReducedMotion();
      untracked(() => {
        this.working.set(false);
        this.activeKey.set(null);
        this.shown.set(animate ? 0 : total);
      });
      if (!animate) {
        this.revealed.emit();
        return;
      }
      const startedAt = performance.now();
      const timer = setInterval(() => {
        // A skip has already shown everything and emitted.
        if (this.done()) return clearInterval(timer);
        const shown = Math.ceil((total * (performance.now() - startedAt)) / duration);
        this.shown.set(Math.min(total, shown));
        if (shown >= total) {
          clearInterval(timer);
          this.revealed.emit();
        }
      }, TICK_MS);
      onCleanup(() => clearInterval(timer));
    });
  }

  protected skip(): void {
    if (this.done()) return;
    this.shown.set(this.view().total);
    this.revealed.emit();
  }

  protected onKey(event: KeyboardEvent): void {
    const target = event.target;
    if (target instanceof Element && target.closest('input, select, textarea')) return;
    this.skip();
  }

  protected grounded(line: LineView): boolean {
    return this.working() && line.factIds.length > 0;
  }

  protected toggleWorking(): void {
    this.working.update((on) => !on);
    this.activeKey.set(null);
  }
}

function prefersReducedMotion(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}
