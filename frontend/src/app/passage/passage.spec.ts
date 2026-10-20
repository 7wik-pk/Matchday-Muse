import { TestBed } from '@angular/core/testing';
import { RunResultPayload } from '../contracts/contracts';
import { loadTakes } from '../mocks/scripts';
import { Passage, REVEAL_MS, plainText } from './passage';

const squash = (text: string | null | undefined) => (text ?? '').replace(/\s+/g, ' ').trim();

async function takeOf(style: RunResultPayload['style']) {
  return (await loadTakes()).takes.find((t) => t.style === style)!;
}

async function render(style: RunResultPayload['style'], animate: boolean, revealMs = 5000) {
  TestBed.configureTestingModule({ providers: [{ provide: REVEAL_MS, useValue: revealMs }] });
  const take = await takeOf(style);
  const fixture = TestBed.createComponent(Passage);
  let revealed = 0;
  fixture.componentInstance.revealed.subscribe(() => revealed++);
  fixture.componentRef.setInput('text', take.text);
  fixture.componentRef.setInput('facts', take.facts);
  fixture.componentRef.setInput('sources', take.sources);
  fixture.componentRef.setInput('animate', animate);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  return { fixture, el, take, revealedCount: () => revealed };
}

const button = (el: HTMLElement, text: string) =>
  [...el.querySelectorAll('button')].find((b) => b.textContent?.trim() === text);

describe('Passage', () => {
  it('shows a take it is not animating at once, and says so', async () => {
    const { el, revealedCount } = await render('ballad', false);
    expect(squash(el.querySelector('h2')?.textContent)).toBe('The Ballad of the Nine-Man Bees');
    expect(el.querySelectorAll('.pending')).toHaveLength(0);
    expect(el.querySelectorAll('.passage p.stanza')).toHaveLength(7);
    expect(revealedCount()).toBe(1);
  });

  it('lays the poem out in stanzas of lines', async () => {
    const { el } = await render('limericks', false);
    const stanzas = el.querySelectorAll('.passage p.stanza');
    expect(stanzas).toHaveLength(3);
    expect(stanzas[0].querySelectorAll('.line')).toHaveLength(5);
  });

  it('types a new take out, with the hidden words already laid out', async () => {
    const { fixture, el, revealedCount } = await render('ballad', true, 400);
    const words = el.querySelectorAll('.line > span').length;
    expect(el.querySelectorAll('.pending').length).toBeGreaterThan(words / 2);
    // The full text is in the page from the start, for screen readers.
    expect(el.textContent).toContain('who came from behind and turned the tide.');
    expect(button(el, 'Show it all')).toBeDefined();
    await vi.waitFor(async () => {
      await fixture.whenStable();
      expect(el.querySelectorAll('.pending')).toHaveLength(0);
    });
    expect(revealedCount()).toBe(1);
  });

  it('skips to the end on a click or a key, and reports it once', async () => {
    const first = await render('ballad', true);
    first.el.querySelector<HTMLElement>('.passage')!.click();
    await first.fixture.whenStable();
    expect(first.el.querySelectorAll('.pending')).toHaveLength(0);
    expect(first.revealedCount()).toBe(1);
    first.el.querySelector<HTMLElement>('.passage')!.click();
    expect(first.revealedCount()).toBe(1);

    TestBed.resetTestingModule();
    const second = await render('ballad', true);
    document.dispatchEvent(new KeyboardEvent('keydown', { key: ' ' }));
    await second.fixture.whenStable();
    expect(second.el.querySelectorAll('.pending')).toHaveLength(0);
  });

  it('shows the facts behind a line when Show your working is on', async () => {
    const { fixture, el } = await render('ballad', false);
    expect(el.querySelectorAll('.grounded')).toHaveLength(0);
    button(el, 'Show your working')!.click();
    await fixture.whenStable();
    const grounded = [...el.querySelectorAll<HTMLElement>('.grounded')];
    // Every line with facts is underlined: the headline and 25 of the 28 lines.
    expect(grounded).toHaveLength(26);
    expect(el.querySelector('.working-panel')?.textContent).toContain('Point at, tap or tab');

    const equaliser = grounded.find((s) => squash(s.textContent).includes('Muñoz down the right'))!;
    equaliser.focus();
    await fixture.whenStable();
    const panel = el.querySelector('.working-panel')!;
    expect(panel.textContent).toContain("62': Víctor Muñoz");
    const link = panel.querySelector<HTMLAnchorElement>('a')!;
    expect(link.href).toBe('https://www.espn.com/soccer/match/_/gameId/401879262');
    expect(link.rel).toBe('noopener noreferrer');
  });

  it('copies as plain text, keeping lines and paragraphs', async () => {
    const take = await takeOf('limericks');
    const text = plainText(take.text!);
    expect(text.startsWith('Three Limericks From a Nine-Man Afternoon\n\nKeane Lewis-Potter')).toBe(
      true,
    );
    expect(text).toContain('though small,\noutjumped every Red');
    expect(text.split('\n\n')).toHaveLength(4);
  });
});
