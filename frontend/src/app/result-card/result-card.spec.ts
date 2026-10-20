import { TestBed } from '@angular/core/testing';
import { RunErrorPayload, SessionReady, StyleId } from '../contracts/contracts';
import { loadSessionScript, loadTakes } from '../mocks/scripts';
import { sendsOf } from '../mocks/testing';
import { REVEAL_MS } from '../passage/passage';
import { Take } from '../run/run-store';
import { ResultCard, formatCost, matchDay } from './result-card';

async function takes(...styles: StyleId[]): Promise<Take[]> {
  const all = (await loadTakes()).takes;
  return styles.map((style, i) => ({
    runId: `r${i + 1}`,
    result: all.find((t) => t.style === style)!,
  }));
}

async function render(
  options: {
    takes?: Take[];
    revealed?: boolean;
    pendingStyle?: StyleId | null;
    retellError?: RunErrorPayload | null;
  } = {},
) {
  TestBed.configureTestingModule({ providers: [{ provide: REVEAL_MS, useValue: 5000 }] });
  const list = options.takes ?? (await takes('ballad'));
  const session = sendsOf(await loadSessionScript())[0] as SessionReady;
  const fixture = TestBed.createComponent(ResultCard);
  const emitted = { retell: [] as StyleId[], select: [] as string[], revealed: [] as string[] };
  fixture.componentInstance.retell.subscribe((s) => emitted.retell.push(s));
  fixture.componentInstance.select.subscribe((id) => emitted.select.push(id));
  fixture.componentInstance.revealed.subscribe((id) => emitted.revealed.push(id));
  fixture.componentRef.setInput('takes', list);
  fixture.componentRef.setInput('take', list.at(-1));
  fixture.componentRef.setInput('styles', session.payload.styles);
  fixture.componentRef.setInput('timeZone', 'Europe/London');
  fixture.componentRef.setInput(
    'revealedIds',
    new Set(options.revealed === false ? [] : list.map((t) => t.runId)),
  );
  fixture.componentRef.setInput('pendingStyle', options.pendingStyle ?? null);
  fixture.componentRef.setInput('retellError', options.retellError ?? null);
  await fixture.whenStable();
  return { fixture, el: fixture.nativeElement as HTMLElement, emitted };
}

const squash = (text: string | null | undefined) => (text ?? '').replace(/\s+/g, ' ').trim();

describe('ResultCard', () => {
  it('shows the match, the headline, the passage and the AI label', async () => {
    const { el } = await render();
    expect(squash(el.querySelector('.match')?.textContent)).toBe('Brentford 1–2 Liverpool');
    expect(el.querySelector('.eyebrow')?.textContent).toContain('Sat 17 Oct 2026');
    expect(squash(el.querySelector('app-passage h2')?.textContent)).toBe(
      'The Ballad of the Nine-Man Bees',
    );
    expect(el.textContent).toContain('Ballad · AI-generated from match data; may contain errors.');
  });

  it('keeps the final score and the moment back until the passage is revealed', async () => {
    const { el, emitted } = await render({ revealed: false });
    expect(squash(el.querySelector('.match')?.textContent)).toBe('Brentford v Liverpool');
    expect(el.querySelector('.moment')?.textContent).not.toContain('comeback');
    el.querySelector<HTMLElement>('.passage')!.click();
    expect(emitted.revealed).toEqual(['r1']);
  });

  it('shows one chip per guardrail check', async () => {
    const chips = [...(await render()).el.querySelectorAll('app-guardrail-chips li')];
    expect(chips.map((c) => c.getAttribute('data-status'))).toEqual(Array(7).fill('pass'));
    expect(chips.some((c) => c.textContent?.includes('Length and form'))).toBe(true);
  });

  it('opens sources in a new tab without an opener', async () => {
    const links = [...(await render()).el.querySelectorAll<HTMLAnchorElement>('.sources a')];
    expect(links).toHaveLength(2);
    expect(links[0].href).toBe('https://www.espn.com/soccer/report/_/gameId/401879262');
    expect(links[0].rel).toBe('noopener noreferrer');
  });

  it('shows tokens and cost', async () => {
    expect((await render()).el.querySelector('.usage')?.textContent).toContain(
      '21,840 in · 2,310 out tokens · about $0.0042',
    );
  });

  it('suggests a style not yet told, grouped by family, and retells in it', async () => {
    const { el, emitted } = await render({ takes: await takes('ballad', 'sonnet') });
    const select = el.querySelector<HTMLSelectElement>('.retell select')!;
    expect([...select.querySelectorAll('optgroup')].map((g) => g.label)).toEqual([
      'Formal verse',
      'Light verse',
    ]);
    expect(select.value).toBe('villanelle');
    select.value = 'limericks';
    select.dispatchEvent(new Event('change'));
    el.querySelector<HTMLButtonElement>('.retell button')!.click();
    expect(emitted.retell).toEqual(['limericks']);
  });

  it('shows a tab per take, the pending retell, and switches takes', async () => {
    const { el, emitted } = await render({
      takes: await takes('ballad', 'limericks'),
      pendingStyle: 'clerihews',
    });
    const tabs = [...el.querySelectorAll<HTMLElement>('.takes .take')];
    expect(tabs.map((t) => squash(t.textContent))).toEqual(['Ballad', 'Limericks', 'Clerihews…']);
    expect(tabs[1].getAttribute('aria-current')).toBe('true');
    tabs[0].click();
    expect(emitted.select).toEqual(['r1']);
  });

  it('shows no tabs for a single take', async () => {
    expect((await render()).el.querySelector('.takes')).toBeNull();
  });

  it('reports a failed retell above the take it kept', async () => {
    const { el } = await render({
      retellError: {
        code: 'guardrail_failed',
        message: 'The passage failed the fact check twice.',
        retryable: true,
        stage: 'guardrails',
        reasons: [],
        guardrails: null,
        suggestion: null,
      },
    });
    const alert = el.querySelector('.retell-error')!;
    expect(alert.textContent).toContain('Held back by the fact check: The passage failed');
    expect(alert.querySelector('button')?.textContent?.trim()).toBe('Try again');
  });

  it('dates the match in the viewer’s timezone', () => {
    expect(matchDay('2026-10-17T14:00:00Z', 'Europe/London')).toBe('Sat 17 Oct 2026');
    expect(matchDay('2026-10-17T14:00:00Z', 'Australia/Melbourne')).toBe('Sun 18 Oct 2026');
  });

  it('formats cost', () => {
    expect(formatCost(null)).toBe('cost unknown');
    expect(formatCost(0.25)).toBe('about $0.25');
  });
});
