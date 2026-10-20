import {
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  model,
  signal,
  viewChild,
} from '@angular/core';
import { ModelInfo } from '../contracts/contracts';
import { LlmSettingsService, providerLabel, usableModels } from '../settings/llm-settings.service';

/** "Your LLM": provider, model and API key, kept in this tab's sessionStorage only. */
@Component({
  selector: 'app-settings-drawer',
  templateUrl: './settings-drawer.html',
  styleUrl: './settings-drawer.css',
  host: { '(document:keydown.escape)': 'open.set(false)' },
})
export class SettingsDrawer {
  readonly open = model(false);
  readonly models = input.required<ModelInfo[]>();

  protected readonly settings = inject(LlmSettingsService);
  protected readonly showKey = signal(false);
  protected readonly providerLabel = providerLabel;

  protected readonly usable = computed(() => usableModels(this.models()));
  protected readonly providers = computed(() => [...new Set(this.usable().map((m) => m.provider))]);
  protected readonly providerModels = computed(() =>
    this.usable().filter((m) => m.provider === this.settings.provider()),
  );
  protected readonly selectedModel = computed(() =>
    this.usable().find((m) => m.id === this.settings.model()),
  );

  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');

  constructor() {
    effect(() => {
      if (this.open()) this.panel()?.nativeElement.focus();
    });
  }

  protected setProvider(provider: string): void {
    this.settings.selectProvider(provider, this.models());
  }
}
