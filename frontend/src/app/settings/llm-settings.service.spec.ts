import { TestBed } from '@angular/core/testing';
import { ModelInfo, SessionReady } from '../contracts/contracts';
import { loadSessionScript } from '../mocks/scripts';
import { sendsOf } from '../mocks/testing';
import { LlmSettingsService } from './llm-settings.service';

const STORAGE_KEY = 'matchday-muse.llm';

async function registry(): Promise<ModelInfo[]> {
  return (sendsOf(await loadSessionScript())[0] as SessionReady).payload.models;
}

describe('LlmSettingsService', () => {
  beforeEach(() => sessionStorage.clear());

  it('uses the server key until the user adds one', async () => {
    const settings = TestBed.inject(LlmSettingsService);
    settings.applyRegistry(await registry());
    expect(settings.llm()).toEqual({ mode: 'house' });

    settings.apiKey.set('  sk-test  ');
    expect(settings.llm()).toEqual({
      mode: 'byok',
      provider: 'gemini',
      model: 'gemini/gemini-flash',
      apiKey: 'sk-test',
    });
  });

  it('keeps settings in sessionStorage and forgets the key on request', async () => {
    const settings = TestBed.inject(LlmSettingsService);
    settings.selectProvider('anthropic', await registry());
    settings.apiKey.set('sk-test');
    TestBed.tick();
    expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY)!)).toEqual({
      provider: 'anthropic',
      model: 'anthropic/claude-haiku',
      apiKey: 'sk-test',
    });

    settings.forgetKey();
    TestBed.tick();
    expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY)!).apiKey).toBe('');
    expect(settings.llm()).toEqual({ mode: 'house' });
  });

  it('restores settings from sessionStorage', () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ provider: 'gemini', model: 'gemini/gemini-flash', apiKey: 'sk-saved' }),
    );
    expect(TestBed.inject(LlmSettingsService).hasKey()).toBe(true);
  });

  it('replaces a model that is no longer in the registry', async () => {
    const settings = TestBed.inject(LlmSettingsService);
    settings.provider.set('anthropic');
    settings.model.set('anthropic/retired-model');
    settings.applyRegistry(await registry());
    expect(settings.model()).toBe('anthropic/claude-haiku');
  });
});
