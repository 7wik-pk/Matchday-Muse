import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { OutputKind, RangeRequest, RunStartPayload, StyleId } from './contracts/contracts';
import { Controls, competitionKey } from './controls/controls';
import { ErrorCard } from './error-card/error-card';
import { MockBar } from './mock-bar/mock-bar';
import { MockWsService } from './mocks/mock-ws.service';
import { PromptModal } from './prompt-modal/prompt-modal';
import { defaultRange, todayIn } from './range/range';
import { ResultCard } from './result-card/result-card';
import { isActive, isRetell } from './run/run-state';
import { RunStore } from './run/run-store';
import { SettingsDrawer } from './settings-drawer/settings-drawer';
import { LlmSettingsService } from './settings/llm-settings.service';
import { StagePanel } from './stage-panel/stage-panel';

const CONNECTION_NOTES = {
  connecting: 'Connecting…',
  reconnecting: 'Reconnecting…',
  closed: 'Offline',
  open: null,
} as const;

@Component({
  selector: 'app-root',
  imports: [Controls, ErrorCard, MockBar, PromptModal, ResultCard, SettingsDrawer, StagePanel],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly store = inject(RunStore);
  protected readonly settings = inject(LlmSettingsService);
  protected readonly mock = inject(MockWsService, { optional: true });

  protected readonly competition = signal('football/eng.1');
  protected readonly range = signal<RangeRequest>(defaultRange(todayIn(this.store.timeZone)));
  protected readonly style = signal<StyleId>('ballad');
  protected readonly outputKind = signal<OutputKind>('text');
  protected readonly drawerOpen = signal(false);

  protected readonly session = this.store.session;
  protected readonly run = this.store.run;
  protected readonly models = computed(() => this.session()?.models ?? []);
  protected readonly selectedModel = computed(
    () => this.models().find((m) => m.id === this.settings.model()) ?? null,
  );
  protected readonly llmLabel = computed(() =>
    this.settings.hasKey() ? (this.selectedModel()?.label ?? 'Your key') : 'Add your key',
  );
  protected readonly connectionNote = computed(() => CONNECTION_NOTES[this.store.connection()]);
  protected readonly imageBlockedReason = computed(() => {
    if (!this.settings.hasKey()) return 'Image output needs your own LLM key.';
    const model = this.selectedModel();
    if (!model) return 'Choose a model in Your LLM first.';
    return model.imageCompanion ? null : `${model.label} has no image model.`;
  });
  /** Takes whose passage has been shown in full, so revisiting one does not replay the reveal. */
  protected readonly revealedIds = signal<ReadonlySet<string>>(new Set());
  /** The style being retold while a retell runs. */
  protected readonly pendingStyle = computed(() => {
    const { phase, request } = this.run();
    return isActive(phase) && isRetell(request) ? request.style : null;
  });
  protected readonly retellError = computed(() =>
    this.store.retelling() ? this.run().error : null,
  );
  protected readonly workingMessage = computed(
    () => this.run().stages.find((s) => s.status === 'running')?.message ?? 'Starting the run',
  );

  constructor() {
    this.store.connect();

    let firstSession = true;
    effect(() => {
      const session = this.session();
      if (!session) return;
      untracked(() => {
        this.settings.applyRegistry(session.models);
        if (!session.competitions.some((c) => competitionKey(c) === this.competition())) {
          this.competition.set(competitionKey(session.competitions[0]));
        }
        if (firstSession && this.mock) {
          firstSession = false;
          void (this.mock.autoplay ? this.playMock() : this.loadMockRequest());
        }
      });
    });

    effect(() => {
      if (this.imageBlockedReason() && untracked(this.outputKind) === 'image') {
        this.outputKind.set('text');
      }
    });
  }

  protected generate(): void {
    const [sport, league] = this.competition().split('/');
    this.store.start({
      sport,
      league,
      range: this.range(),
      style: this.style(),
      output: this.outputKind(),
      llm: this.settings.llm(),
    });
  }

  protected retry(): void {
    const request = this.run().request;
    if (request) this.store.repeat(request, this.settings.llm());
  }

  protected retell(style: StyleId): void {
    this.store.retell(style, this.settings.llm());
  }

  protected markRevealed(runId: string): void {
    if (!this.revealedIds().has(runId)) this.revealedIds.update((ids) => new Set([...ids, runId]));
  }

  protected trySuggestion(range: RangeRequest): void {
    this.range.set(range);
    this.generate();
  }

  protected answer(choice: string): void {
    this.store.answer(choice);
    if (choice === 'switch_model') this.drawerOpen.set(true);
  }

  /** Mock mode: show the selected script's request in the controls, then run it. */
  protected async playMock(): Promise<void> {
    await this.loadMockRequest();
    this.generate();
  }

  private async loadMockRequest(): Promise<void> {
    const start = await this.mock?.scriptStart();
    if (start) this.applyRequest(start);
  }

  private applyRequest(request: RunStartPayload): void {
    this.competition.set(competitionKey(request));
    this.range.set(request.range);
    this.style.set(request.style);
    this.outputKind.set(request.output);
  }
}
