import { Injectable, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import { App } from './app';
import { provideSocket } from './app.config';
import { APP_CONFIG } from './config';
import { ClientMessage, ServerMessage } from './contracts/contracts';
import { MOCK_OPTIONS } from './mocks/mock-ws.service';
import { loadSessionScript } from './mocks/scripts';
import { sendsOf } from './mocks/testing';
import { REVEAL_MS } from './passage/passage';
import { ConnectionState, MatchdaySocket } from './socket/socket';
import { WsService } from './socket/ws.service';

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

/** The backend for sample mode: answers the handshake, records what it is sent. */
@Injectable()
class SessionBackend extends MatchdaySocket {
  private readonly incoming = new Subject<ServerMessage>();
  readonly messages = this.incoming.asObservable();
  readonly state = signal<ConnectionState>('closed');
  readonly sent: ClientMessage[] = [];

  connect(): void {
    void loadSessionScript().then((script) => {
      this.state.set('open');
      this.incoming.next(sendsOf(script)[0]);
    });
  }

  send(message: ClientMessage): void {
    this.sent.push(message);
  }
}

// Production's socket: runs without a key replay the sample run.
async function bootSamples(apiKey = '') {
  sessionStorage.clear();
  if (apiKey) {
    const llm = { provider: 'gemini', model: 'gemini/gemini-flash-latest', apiKey };
    sessionStorage.setItem('matchday-muse.llm', JSON.stringify(llm));
  }
  const config = { wsUrl: 'ws://test/ws', samplesWithoutKey: true };
  TestBed.configureTestingModule({
    providers: [
      { provide: APP_CONFIG, useValue: config },
      provideSocket(config, ''),
      { provide: WsService, useClass: SessionBackend },
      { provide: MOCK_OPTIONS, useValue: { script: 'success', speed: 0, autoplay: false } },
      { provide: REVEAL_MS, useValue: 0 },
    ],
  });
  const fixture = TestBed.createComponent(App);
  const el = fixture.nativeElement as HTMLElement;
  const backend = TestBed.inject(WsService) as unknown as SessionBackend;
  const settle = async (check: () => void) => {
    await vi.waitFor(async () => {
      await fixture.whenStable();
      check();
    });
  };
  return { fixture, el, backend, settle };
}

describe('App without a key, in production', () => {
  it('locks the controls to the sample week and plays the sample run', async () => {
    const { fixture, el, backend, settle } = await bootSamples();
    await settle(() =>
      expect(el.querySelector('.range-label')?.textContent).toContain(
        'Mon 12 Oct – Sun 18 Oct 2026',
      ),
    );
    expect(el.querySelector<HTMLFieldSetElement>('fieldset.range')?.disabled).toBe(true);
    expect(el.querySelector('.range-lock')?.textContent).toContain('add your LLM key');
    expect(el.querySelector('.sample-note')).not.toBeNull();
    expect(el.querySelector('app-mock-bar')).toBeNull();

    await clickGenerate(fixture, el);
    await settle(() =>
      expect(squash(el.querySelector('app-result-card figcaption')?.textContent)).toContain(
        'A sample poem, written in advance',
      ),
    );
    expect(el.querySelector('app-result-card .usage')).toBeNull();
    expect(backend.sent).toEqual([]);
  });

  it('sends runs to the backend, for any week, once there is a key', async () => {
    const { fixture, el, backend, settle } = await bootSamples('k-test');
    await settle(() => expect(button(el, 'Generate')?.disabled).toBe(false));
    expect(el.querySelector<HTMLFieldSetElement>('fieldset.range')?.disabled).toBe(false);
    expect(el.querySelector('.range-lock')).toBeNull();

    await clickGenerate(fixture, el);
    expect(backend.sent.map((m) => m.type)).toEqual(['run.start']);
    expect(backend.sent[0]).toMatchObject({ payload: { llm: { mode: 'byok' } } });
  });
});
