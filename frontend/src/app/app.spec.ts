import { ComponentFixture, TestBed } from '@angular/core/testing';
import { App } from './app';
import { provideSocket } from './app.config';
import { APP_CONFIG } from './config';

// The whole app against the mock socket, replaying instantly.
async function boot(search: string) {
  sessionStorage.clear();
  TestBed.configureTestingModule({
    providers: [
      { provide: APP_CONFIG, useValue: { wsUrl: null } },
      provideSocket({ wsUrl: null }, search),
    ],
  });
  const fixture = TestBed.createComponent(App);
  const el = fixture.nativeElement as HTMLElement;
  const settle = async (check: () => void) => {
    await vi.waitFor(async () => {
      await fixture.whenStable();
      check();
    });
  };
  return { fixture, el, settle };
}

const squash = (text: string | null | undefined) => (text ?? '').replace(/\s+/g, ' ').trim();

const button = (el: HTMLElement, text: string) =>
  [...el.querySelectorAll('button')].find((b) => b.textContent?.trim() === text);

async function clickGenerate(fixture: ComponentFixture<App>, el: HTMLElement) {
  await vi.waitFor(async () => {
    await fixture.whenStable();
    expect(button(el, 'Generate')?.disabled).toBe(false);
  });
  button(el, 'Generate')!.click();
}

describe('App', () => {
  it('runs a scripted success from Generate to the result card', async () => {
    const { fixture, el, settle } = await boot('?speed=0');
    await clickGenerate(fixture, el);
    await settle(() =>
      expect(squash(el.querySelector('app-result-card .match')?.textContent)).toBe(
        'Brentford 1–2 Liverpool',
      ),
    );
    expect(squash(el.querySelector('app-passage h2')?.textContent)).toBe(
      'The Ballad of the Nine-Man Bees',
    );
    expect(el.querySelectorAll('.stage[data-status="done"]')).toHaveLength(10);
    // The controls show the request the script answers.
    expect(el.querySelector('.range-label')?.textContent).toContain('Mon 12 Oct – Sun 18 Oct 2026');
  });

  it('writes in the style chosen in the controls', async () => {
    const { fixture, el, settle } = await boot('?speed=0');
    await settle(() =>
      expect(el.querySelector('.controls optgroup[label="Light verse"]')).not.toBeNull(),
    );
    const select = el.querySelector<HTMLSelectElement>('.controls .style select')!;
    select.value = 'nursery_rhyme';
    select.dispatchEvent(new Event('change'));
    await clickGenerate(fixture, el);
    await settle(() =>
      expect(squash(el.querySelector('app-passage h2')?.textContent)).toBe(
        'Hey Diddle Diddle, the Bees in the Middle',
      ),
    );
  });

  it('retells the match in another style and keeps both takes', async () => {
    const { fixture, el, settle } = await boot('?speed=0');
    await clickGenerate(fixture, el);
    await settle(() => expect(el.querySelector('app-result-card .retell')).not.toBeNull());
    const select = el.querySelector<HTMLSelectElement>('.retell select')!;
    select.value = 'sonnet';
    select.dispatchEvent(new Event('change'));
    button(el, 'Retell')!.click();
    await settle(() =>
      expect([...el.querySelectorAll('.takes .take')].map((t) => squash(t.textContent))).toEqual([
        'Ballad',
        'Shakespearean sonnet',
      ]),
    );
    expect(squash(el.querySelector('app-passage h2')?.textContent)).toBe(
      'Sonnet for a Head Too Rash',
    );
    // The stage panel shows only the retell's stages.
    expect(el.querySelectorAll('.stage')).toHaveLength(3);
    button(el, 'Ballad')!.click();
    await settle(() =>
      expect(squash(el.querySelector('app-passage h2')?.textContent)).toBe(
        'The Ballad of the Nine-Man Bees',
      ),
    );
  });

  it('opens a ?mock= state directly and answers its prompt', async () => {
    const { el, settle } = await boot('?mock=quota-exceeded&speed=0');
    await settle(() => expect(el.querySelector('app-prompt-modal')).not.toBeNull());
    button(el, 'Wait and retry')!.click();
    await settle(() => expect(el.querySelector('app-result-card')).not.toBeNull());
    expect(el.querySelector('app-prompt-modal')).toBeNull();
  });

  it('ends the run and opens Your LLM when the user chooses to switch model', async () => {
    const { el, settle } = await boot('?mock=quota-exceeded&speed=0');
    await settle(() => expect(el.querySelector('app-prompt-modal')).not.toBeNull());
    button(el, 'Switch model')!.click();
    await settle(() =>
      expect(el.querySelector('[role="dialog"] h2')?.textContent).toBe('Your LLM'),
    );
    expect(el.querySelector('app-error-card .eyebrow')?.textContent).toContain('Quota used up');
    expect(button(el, 'Try again')).toBeDefined();
  });

  it('cancels a run that is waiting at the cancel step', async () => {
    const { el, settle } = await boot('?mock=cancelled&speed=0');
    await settle(() => expect(button(el, 'Cancel')?.disabled).toBe(false));
    button(el, 'Cancel')!.click();
    await settle(() =>
      expect(el.querySelector('app-error-card h2')?.textContent).toContain('Run cancelled'),
    );
    expect(button(el, 'Generate')).toBeDefined();
  });
});
