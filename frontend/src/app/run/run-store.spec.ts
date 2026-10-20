import { TestBed } from '@angular/core/testing';
import { RunResultPayload, RunStartPayload } from '../contracts/contracts';
import { MOCK_OPTIONS, MockWsService } from '../mocks/mock-ws.service';
import { loadRunScript } from '../mocks/scripts';
import { MatchdaySocket } from '../socket/socket';
import { MAX_TAKES, RunStore, Take, addTake } from './run-store';

function setup() {
  TestBed.configureTestingModule({
    providers: [
      { provide: MOCK_OPTIONS, useValue: { script: 'success', speed: 0, autoplay: false } },
      MockWsService,
      { provide: MatchdaySocket, useExisting: MockWsService },
    ],
  });
  return TestBed.inject(RunStore);
}

const house = { mode: 'house' } as const;

async function finishFullRun(store: RunStore) {
  const request = (await loadRunScript('success')).start as RunStartPayload;
  store.start(request);
  await vi.waitFor(() => expect(store.run().phase).toBe('succeeded'));
}

const take = (runId: string): Take => ({ runId, result: {} as RunResultPayload });

describe('RunStore takes', () => {
  it('keeps the full run’s take and appends each retell', async () => {
    const store = setup();
    await finishFullRun(store);
    expect(store.takes().map((t) => t.result.style)).toEqual(['ballad']);

    store.retell('limericks', house);
    expect(store.retelling()).toBe(true);
    await vi.waitFor(() => expect(store.takes()).toHaveLength(2));
    expect(store.takes().map((t) => t.result.style)).toEqual(['ballad', 'limericks']);
    expect(store.selectedTake()?.result.style).toBe('limericks');
    // Retells always start from the full run.
    store.retell('clerihews', house);
    await vi.waitFor(() => expect(store.takes()).toHaveLength(3));
  });

  it('clears the takes when a new full run starts', async () => {
    const store = setup();
    await finishFullRun(store);
    store.start((await loadRunScript('success')).start as RunStartPayload);
    expect(store.takes()).toEqual([]);
    expect(store.selectedTake()).toBeNull();
  });

  it('repeats a retell as a retell', async () => {
    const store = setup();
    await finishFullRun(store);
    store.repeat({ fromRunId: 'ignored', style: 'villanelle', output: 'text', llm: house }, house);
    await vi.waitFor(() => expect(store.takes()).toHaveLength(2));
    expect(store.takes()[1].result.style).toBe('villanelle');
  });

  it('caps the takes, keeping the full run’s first', () => {
    let takes = [take('full')];
    for (let i = 1; i <= MAX_TAKES + 2; i++) takes = addTake(takes, take(`retell${i}`));
    expect(takes).toHaveLength(MAX_TAKES);
    expect(takes[0].runId).toBe('full');
    expect(takes.at(-1)?.runId).toBe(`retell${MAX_TAKES + 2}`);
  });
});
