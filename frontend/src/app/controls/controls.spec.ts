import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { OutputKind, RangeRequest, SessionReady, StyleId } from '../contracts/contracts';
import { loadSessionScript } from '../mocks/scripts';
import { sendsOf } from '../mocks/testing';
import { RunPhase } from '../run/run-state';
import { Controls } from './controls';

@Component({
  imports: [Controls],
  template: `
    <app-controls
      [session]="session()"
      [phase]="phase()"
      timeZone="Europe/London"
      [imageBlockedReason]="imageBlocked()"
      [(competition)]="competition"
      [(range)]="range"
      [(style)]="style"
      [(outputKind)]="outputKind"
      (generate)="generated = generated + 1"
      (cancel)="cancelled = cancelled + 1"
    />
  `,
})
class Host {
  session = signal<SessionReady['payload'] | null>(null);
  phase = signal<RunPhase>('idle');
  imageBlocked = signal<string | null>(null);
  competition = signal('football/eng.1');
  range = signal<RangeRequest>({ granularity: 'week', anchor: '2026-10-14' });
  style = signal<StyleId>('ballad');
  outputKind = signal<OutputKind>('text');
  generated = 0;
  cancelled = 0;
}

async function setup() {
  const fixture = TestBed.createComponent(Host);
  const host = fixture.componentInstance;
  host.session.set((sendsOf(await loadSessionScript())[0] as SessionReady).payload);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const button = (text: string) =>
    [...el.querySelectorAll('button')].find((b) => b.textContent?.trim() === text)!;
  const label = () => el.querySelector('.range-label')?.textContent?.trim();
  return { fixture, host, el, button, label };
}

describe('Controls', () => {
  it('shows the resolved range and moves it a week at a time', async () => {
    const { fixture, el, label } = await setup();
    expect(label()).toBe('Mon 12 Oct – Sun 18 Oct 2026, London time');
    el.querySelector<HTMLButtonElement>('[aria-label="Next week"]')!.click();
    await fixture.whenStable();
    expect(label()).toBe('Mon 19 Oct – Sun 25 Oct 2026, London time');
  });

  it('switches granularity from the start of the current range', async () => {
    const { fixture, host, button, label } = await setup();
    button('Day').click();
    await fixture.whenStable();
    expect(host.range()).toEqual({ granularity: 'day', anchor: '2026-10-12' });
    expect(label()).toBe('Mon 12 Oct 2026, London time');
    button('Month').click();
    await fixture.whenStable();
    expect(label()).toBe('October 2026, London time');
  });

  it('writes the chosen style back and describes it', async () => {
    const { fixture, host, el } = await setup();
    const select = el.querySelector<HTMLSelectElement>('.style select')!;
    select.value = 'villanelle';
    select.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    expect(host.style()).toBe('villanelle');
    expect(el.querySelector('.style-description')?.textContent).toContain('two refrains');
  });

  it('generates when idle and cancels while running', async () => {
    const { fixture, host, button } = await setup();
    button('Generate').click();
    expect(host.generated).toBe(1);
    host.phase.set('running');
    await fixture.whenStable();
    expect(button('Generate')).toBeUndefined();
    button('Cancel').click();
    expect(host.cancelled).toBe(1);
    host.phase.set('cancelling');
    await fixture.whenStable();
    expect(button('Cancelling…').disabled).toBe(true);
  });

  it('disables Image with the reason shown', async () => {
    const { fixture, host, el, button } = await setup();
    host.imageBlocked.set('Image output needs your own LLM key.');
    await fixture.whenStable();
    expect(button('Image').disabled).toBe(true);
    expect(el.querySelector('.output')?.textContent).toContain('needs your own LLM key');
  });
});
