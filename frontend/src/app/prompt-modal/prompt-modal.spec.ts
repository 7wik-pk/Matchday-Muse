import { TestBed } from '@angular/core/testing';
import { PromptRequest } from '../contracts/contracts';
import { loadRunScript } from '../mocks/scripts';
import { sendsOf } from '../mocks/testing';
import { PromptModal, formatCountdown } from './prompt-modal';

describe('PromptModal', () => {
  it('asks the question with a countdown and answers with the chosen option', async () => {
    const prompt = sendsOf(await loadRunScript('quota-exceeded')).find(
      (m): m is PromptRequest => m.type === 'prompt.request',
    )!;
    const fixture = TestBed.createComponent(PromptModal);
    fixture.componentRef.setInput('prompt', prompt.payload);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    let answer: string | undefined;
    fixture.componentInstance.answer.subscribe((choice) => (answer = choice));

    expect(el.querySelector('[role="alertdialog"] h2')?.textContent).toBe('Quota reached');
    expect(el.querySelector('.countdown')?.textContent).toContain('Resets in 38 s');
    const buttons = [...el.querySelectorAll('button')];
    expect(buttons.map((b) => b.textContent?.trim())).toEqual([
      'Wait and retry',
      'Switch model',
      'Cancel run',
    ]);
    expect(document.activeElement).toBe(buttons[0]);
    buttons[1].click();
    expect(answer).toBe('switch_model');
  });

  it('formats countdowns from seconds to hours', () => {
    expect(formatCountdown(38)).toBe('38 s');
    expect(formatCountdown(245)).toBe('4 m 05 s');
    expect(formatCountdown(22_320)).toBe('6 h 12 m');
  });
});
