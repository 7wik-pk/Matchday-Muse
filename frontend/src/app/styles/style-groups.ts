import { StyleFamily, StylePreset } from '../contracts/contracts';

const FAMILY_LABELS: Record<StyleFamily, string> = {
  formal: 'Formal verse',
  light: 'Light verse',
};

export interface StyleGroup {
  label: string;
  styles: StylePreset[];
}

/** The presets grouped by family for a select's optgroups, in the session's order. */
export function groupStyles(styles: StylePreset[]): StyleGroup[] {
  const groups = new Map<StyleFamily, StylePreset[]>();
  for (const style of styles)
    groups.set(style.family, [...(groups.get(style.family) ?? []), style]);
  return [...groups].map(([family, members]) => ({
    label: FAMILY_LABELS[family],
    styles: members,
  }));
}
