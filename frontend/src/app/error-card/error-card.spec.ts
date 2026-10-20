import { TestBed } from '@angular/core/testing';
import { RangeRequest, RunError } from '../contracts/contracts';
import { RunScriptId, loadRunScript } from '../mocks/scripts';
import { sendsOf } from '../mocks/testing';
import { applyMessage, runStarting } from '../run/run-state';
import { ErrorCard } from './error-card';

async function render(id: RunScriptId) {
  const script = await loadRunScript(id);
  const sends = sendsOf(script);
  const fixture = TestBed.createComponent(ErrorCard);
  fixture.componentRef.setInput('error', (sends.at(-1) as RunError).payload);
  fixture.componentRef.setInput(
    'stages',
    sends.reduce(applyMessage, runStarting(script.start!)).stages,
  );
  await fixture.whenStable();
  const buttons = () => [...(fixture.nativeElement as HTMLElement).querySelectorAll('button')];
  return {
    el: fixture.nativeElement as HTMLElement,
    component: fixture.componentInstance,
    buttons,
  };
}

describe('ErrorCard', () => {
  it('offers the suggested range as a one-click button', async () => {
    const { el, component, buttons } = await render('no-matches');
    let tried: RangeRequest | undefined;
    component.trySuggestion.subscribe((range) => (tried = range));
    expect(el.querySelector('.eyebrow')?.textContent).toContain(
      'No matches · Find completed matches',
    );
    expect(buttons().map((b) => b.textContent?.trim())).toEqual([
      'Try the whole week: Mon 12 – Sun 18 Oct',
    ]);
    buttons()[0].click();
    expect(tried).toEqual({ granularity: 'week', anchor: '2026-10-12' });
  });

  it('lists the reasons and the failed check, and offers a retry', async () => {
    const { el, component, buttons } = await render('guardrail-failed');
    let retried = false;
    component.retry.subscribe(() => (retried = true));
    expect(el.querySelector('.reasons')?.textContent).toContain('Unsupported claim');
    expect(el.querySelector('[data-status="fail"]')?.textContent).toContain('Grounding');
    expect(el.textContent).toContain('Failed again after one rewrite.');
    buttons()[0].click();
    expect(retried).toBe(true);
  });
});
