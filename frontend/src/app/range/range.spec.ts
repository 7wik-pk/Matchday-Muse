import {
  defaultRange,
  rangeBounds,
  rangeLabel,
  shiftRange,
  timeZoneText,
  todayIn,
  withGranularity,
} from './range';

describe('range', () => {
  it('bounds a week from Monday to Sunday', () => {
    expect(rangeBounds({ granularity: 'week', anchor: '2026-10-14' })).toEqual({
      start: '2026-10-12',
      end: '2026-10-18',
    });
    expect(rangeBounds({ granularity: 'week', anchor: '2026-10-18' }).start).toBe('2026-10-12');
    expect(rangeBounds({ granularity: 'week', anchor: '2026-10-12' }).end).toBe('2026-10-18');
  });

  it('bounds a month, including February in a leap year', () => {
    expect(rangeBounds({ granularity: 'month', anchor: '2028-02-17' })).toEqual({
      start: '2028-02-01',
      end: '2028-02-29',
    });
  });

  it('shifts by one unit', () => {
    expect(shiftRange({ granularity: 'day', anchor: '2026-10-31' }, 1).anchor).toBe('2026-11-01');
    expect(shiftRange({ granularity: 'week', anchor: '2026-10-14' }, -1).anchor).toBe('2026-10-05');
    expect(shiftRange({ granularity: 'month', anchor: '2026-01-31' }, -1).anchor).toBe(
      '2025-12-01',
    );
  });

  it('keeps the first day of the old range when the granularity changes', () => {
    expect(withGranularity({ granularity: 'week', anchor: '2026-10-14' }, 'day')).toEqual({
      granularity: 'day',
      anchor: '2026-10-12',
    });
  });

  it('labels each granularity with the timezone', () => {
    const tz = 'Europe/London';
    expect(rangeLabel({ granularity: 'week', anchor: '2026-10-13' }, tz)).toBe(
      'Mon 12 Oct – Sun 18 Oct 2026, London time',
    );
    expect(rangeLabel({ granularity: 'day', anchor: '2026-10-14' }, tz)).toBe(
      'Wed 14 Oct 2026, London time',
    );
    expect(rangeLabel({ granularity: 'month', anchor: '2026-10-20' }, tz)).toBe(
      'October 2026, London time',
    );
    expect(rangeLabel({ granularity: 'week', anchor: '2026-12-31' }, tz)).toBe(
      'Mon 28 Dec 2026 – Sun 3 Jan 2027, London time',
    );
  });

  it('names timezones by their city', () => {
    expect(timeZoneText('America/Argentina/Buenos_Aires')).toBe('Buenos Aires time');
    expect(timeZoneText('Etc/UTC')).toBe('UTC');
  });

  it('opens on last week on a Monday, this week otherwise', () => {
    expect(defaultRange('2026-10-19').anchor).toBe('2026-10-12');
    expect(defaultRange('2026-10-20').anchor).toBe('2026-10-20');
  });

  it('reads today in the given timezone', () => {
    const now = new Date('2026-10-19T14:30:00Z');
    expect(todayIn('Europe/London', now)).toBe('2026-10-19');
    expect(todayIn('Australia/Melbourne', now)).toBe('2026-10-20');
  });
});
