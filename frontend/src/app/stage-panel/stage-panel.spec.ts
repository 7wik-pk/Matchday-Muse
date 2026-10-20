import { TestBed } from '@angular/core/testing';
import { loadRunScript } from '../mocks/scripts';
import { sendsOf } from '../mocks/testing';
import { applyMessage, runStarting } from '../run/run-state';
import { StagePanel, formatElapsed } from './stage-panel';

async function stagesAfter(id: 'success' | 'stage-failed', messages: number) {
  const script = await loadRunScript(id);
  return sendsOf(script).slice(0, messages).reduce(applyMessage, runStarting(script.start!)).stages;
}

async function render(stages: Awaited<ReturnType<typeof stagesAfter>>) {
  const fixture = TestBed.createComponent(StagePanel);
  fixture.componentRef.setInput('stages', stages);
  await fixture.whenStable();
  return fixture.nativeElement as HTMLElement;
}

const statuses = (el: HTMLElement) =>
  [...el.querySelectorAll('.stage')].map((li) => li.getAttribute('data-status'));

describe('StagePanel', () => {
  it('explains itself before a run', async () => {
    const el = await render([]);
    expect(el.textContent).toContain('Each step of the run shows up here');
  });

  it('draws every stage, with the running one mid-way', async () => {
    // accepted, resolve ×2, fetch ×2, score running, "3 of 10 matches loaded"
    const el = await render(await stagesAfter('success', 7));
    expect(statuses(el)).toEqual(['done', 'done', 'running', ...Array(7).fill('pending')]);
    expect(el.textContent).toContain('3 of 10 matches loaded');
    expect(el.querySelectorAll('.stage')[1].querySelector('details')?.textContent).toContain(
      'belongs to the next week',
    );
  });

  it('shows a failed stage and its message', async () => {
    const el = await render(await stagesAfter('stage-failed', 99));
    expect(statuses(el).slice(0, 3)).toEqual(['done', 'failed', 'pending']);
    expect(el.querySelector('[data-status="failed"] .message')?.textContent).toContain(
      'ESPN did not respond',
    );
  });

  it('formats elapsed time', () => {
    expect(formatElapsed(1240)).toBe('1.2 s');
    expect(formatElapsed(42_000)).toBe('42 s');
    expect(formatElapsed(65_000)).toBe('1 m 05 s');
  });
});
