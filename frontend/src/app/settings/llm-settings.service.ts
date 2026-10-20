import { Injectable, computed, effect, signal } from '@angular/core';
import { ByokLlm, HouseLlm, ModelInfo } from '../contracts/contracts';

const STORAGE_KEY = 'matchday-muse.llm';

interface StoredSettings {
  provider: string | null;
  model: string | null;
  apiKey: string;
}

export const PROVIDER_LABELS: Record<string, string> = {
  gemini: 'Google Gemini',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
};

export const providerLabel = (provider: string) => PROVIDER_LABELS[provider] ?? provider;

/** Only models that can call tools and return JSON can run the pipeline. */
export const usableModels = (models: ModelInfo[]) => models.filter((m) => m.tools && m.json);

/**
 * The user's own LLM: provider, model and key. Kept in sessionStorage only,
 * so the key is gone when the tab closes, and never logged.
 */
@Injectable({ providedIn: 'root' })
export class LlmSettingsService {
  private readonly stored = readStored();

  readonly provider = signal<string | null>(this.stored.provider);
  readonly model = signal<string | null>(this.stored.model);
  readonly apiKey = signal(this.stored.apiKey);
  readonly hasKey = computed(() => this.apiKey().trim().length > 0);

  constructor() {
    effect(() => {
      writeStored({ provider: this.provider(), model: this.model(), apiKey: this.apiKey() });
    });
  }

  /** Fills in a provider and model from the registry when none is chosen, or the chosen one is gone. */
  applyRegistry(models: ModelInfo[]): void {
    const usable = usableModels(models);
    if (usable.some((m) => m.id === this.model() && m.provider === this.provider())) return;
    const fallback = usable.find((m) => m.provider === this.provider()) ?? usable[0];
    this.provider.set(fallback?.provider ?? null);
    this.model.set(fallback?.id ?? null);
  }

  selectProvider(provider: string, models: ModelInfo[]): void {
    this.provider.set(provider);
    this.model.set(usableModels(models).find((m) => m.provider === provider)?.id ?? null);
  }

  forgetKey(): void {
    this.apiKey.set('');
  }

  /** What run.start sends: the user's key when there is one, otherwise the server's. */
  llm(): ByokLlm | HouseLlm {
    const provider = this.provider();
    const model = this.model();
    const apiKey = this.apiKey().trim();
    return provider && model && apiKey
      ? { mode: 'byok', provider, model, apiKey }
      : { mode: 'house' };
  }
}

function readStored(): StoredSettings {
  const empty: StoredSettings = { provider: null, model: null, apiKey: '' };
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? { ...empty, ...JSON.parse(raw) } : empty;
  } catch {
    return empty;
  }
}

function writeStored(settings: StoredSettings): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // Storage blocked: settings last until the page reloads.
  }
}
