import { Component, inject, input, output, signal } from '@angular/core';
import { MockWsService } from '../mocks/mock-ws.service';
import { RUN_SCRIPT_IDS, RunScriptId, loadRunScript } from '../mocks/scripts';

const SPEEDS = [
  { value: 1, label: '1×' },
  { value: 4, label: '4×' },
  { value: 0, label: 'Instant' },
];

/** Shown only when replaying scripted runs: pick a script and a speed, then play it. */
@Component({
  selector: 'app-mock-bar',
  template: `
    <span class="chip tag">Mock</span>
    <label class="script">
      <span class="visually-hidden">Scripted run</span>
      <select [disabled]="busy()" (change)="selectScript($any($event.target).value)">
        @for (id of ids; track id) {
          <option [value]="id" [selected]="id === mock.script()">{{ titles()[id] ?? id }}</option>
        }
      </select>
    </label>
    <label>
      <span class="visually-hidden">Replay speed</span>
      <select (change)="selectSpeed(+$any($event.target).value)">
        @for (s of speeds; track s.value) {
          <option [value]="s.value" [selected]="s.value === mock.speed()">{{ s.label }}</option>
        }
      </select>
    </label>
    <button type="button" class="btn" [disabled]="busy()" (click)="play.emit()">Play</button>
  `,
  styles: `
    :host {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }
    .script {
      flex: 1 1 180px;
      min-width: 0;
    }
    .script select {
      width: 100%;
    }
    .tag {
      background: var(--running);
      color: var(--surface);
    }
    select {
      width: auto;
      min-height: 32px;
      padding-block: 4px;
    }
    .btn {
      min-height: 32px;
      padding-block: 4px;
    }
  `,
})
export class MockBar {
  readonly busy = input(false);
  /** Load the selected script's request into the controls and run it. */
  readonly play = output<void>();

  protected readonly mock = inject(MockWsService);
  protected readonly ids = RUN_SCRIPT_IDS;
  protected readonly speeds = SPEEDS;
  protected readonly titles = signal<Partial<Record<RunScriptId, string>>>({});

  constructor() {
    void Promise.all(RUN_SCRIPT_IDS.map(async (id) => [id, (await loadRunScript(id)).title])).then(
      (entries) => this.titles.set(Object.fromEntries(entries)),
    );
  }

  protected selectScript(id: RunScriptId): void {
    this.mock.script.set(id);
    this.updateUrl();
  }

  protected selectSpeed(speed: number): void {
    this.mock.speed.set(speed);
    this.updateUrl();
  }

  /** Keep ?mock= and ?speed= in the URL, so a reload reopens the same state. */
  private updateUrl(): void {
    const url = new URL(location.href);
    url.searchParams.set('mock', this.mock.script());
    url.searchParams.set('speed', String(this.mock.speed()));
    history.replaceState(null, '', url);
  }
}
