import { Granularity, RangeRequest } from '../contracts/contracts';

// Ranges are calendar dates in the user's timezone, written YYYY-MM-DD. The
// arithmetic below runs on UTC midnights so it never meets a DST change.

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const LONG_MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
const DAY_MS = 86_400_000;

const parse = (date: string) => {
  const [y, m, d] = date.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};
const format = (date: Date) => date.toISOString().slice(0, 10);
const addDays = (date: string, days: number) =>
  format(new Date(parse(date).getTime() + days * DAY_MS));
const weekday = (date: string) => (parse(date).getUTCDay() + 6) % 7; // Monday = 0

/** Today's date in the given IANA timezone. */
export function todayIn(timeZone: string, now = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone }).format(now);
}

/** The browser's IANA timezone. */
export function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

/**
 * The week the app opens on: this week, or last week on a Monday, when this
 * week has had no weekend yet. The design's rule (open on the latest week
 * with completed matches) needs match data, so it moves to the backend later.
 */
export function defaultRange(today: string): RangeRequest {
  return { granularity: 'week', anchor: weekday(today) === 0 ? addDays(today, -7) : today };
}

/** First and last day of the range, inclusive. */
export function rangeBounds({ granularity, anchor }: RangeRequest): { start: string; end: string } {
  if (granularity === 'day') return { start: anchor, end: anchor };
  if (granularity === 'week') {
    const start = addDays(anchor, -weekday(anchor));
    return { start, end: addDays(start, 6) };
  }
  const first = parse(anchor);
  first.setUTCDate(1);
  const last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0));
  return { start: format(first), end: format(last) };
}

/** Changes the granularity, keeping the anchor inside the old range's first day. */
export function withGranularity(range: RangeRequest, granularity: Granularity): RangeRequest {
  return { granularity, anchor: rangeBounds(range).start };
}

/** The previous (-1) or next (+1) day, week or month. */
export function shiftRange(range: RangeRequest, direction: -1 | 1): RangeRequest {
  const { start } = rangeBounds(range);
  if (range.granularity === 'day') return { ...range, anchor: addDays(start, direction) };
  if (range.granularity === 'week') return { ...range, anchor: addDays(start, 7 * direction) };
  const date = parse(start);
  date.setUTCMonth(date.getUTCMonth() + direction);
  return { ...range, anchor: format(date) };
}

/** "Wed 14 Oct 2026", "Mon 12 Oct – Sun 18 Oct 2026" or "October 2026". */
export function rangeText(range: RangeRequest): string {
  const { start, end } = rangeBounds(range);
  const s = parse(start);
  const e = parse(end);
  const short = (d: Date) =>
    `${WEEKDAYS[(d.getUTCDay() + 6) % 7]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
  if (range.granularity === 'month') return `${LONG_MONTHS[s.getUTCMonth()]} ${s.getUTCFullYear()}`;
  if (range.granularity === 'day') return `${short(s)} ${s.getUTCFullYear()}`;
  return s.getUTCFullYear() === e.getUTCFullYear()
    ? `${short(s)} – ${short(e)} ${e.getUTCFullYear()}`
    : `${short(s)} ${s.getUTCFullYear()} – ${short(e)} ${e.getUTCFullYear()}`;
}

/** "London time" for Europe/London; "UTC" for UTC. */
export function timeZoneText(timeZone: string): string {
  if (timeZone === 'UTC' || timeZone === 'Etc/UTC') return 'UTC';
  const city = timeZone.split('/').at(-1) ?? timeZone;
  return `${city.replaceAll('_', ' ')} time`;
}

/** The label under the range picker: "Mon 12 Oct – Sun 18 Oct 2026, London time". */
export function rangeLabel(range: RangeRequest, timeZone: string): string {
  return `${rangeText(range)}, ${timeZoneText(timeZone)}`;
}
