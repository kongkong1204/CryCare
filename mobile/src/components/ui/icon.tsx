import { SymbolView } from 'expo-symbols';
import type { ColorValue } from 'react-native';

// iOS는 SF Symbols, Android는 Material Symbols (expo-symbols, Expo Go 포함)
const ICONS = {
  awake: { ios: 'sun.max.fill', android: 'light_mode' },
  hug: { ios: 'heart.fill', android: 'favorite' },
  hungry: { ios: 'waterbottle.fill', android: 'local_drink' },
  sleepy: { ios: 'moon.zzz.fill', android: 'bedtime' },
  uncomfortable: { ios: 'exclamationmark.bubble.fill', android: 'sentiment_dissatisfied' },
  feeding: { ios: 'waterbottle.fill', android: 'local_drink' },
  diaper: { ios: 'sparkles', android: 'baby_changing_station' },
  mic: { ios: 'mic.fill', android: 'mic' },
  stop: { ios: 'stop.fill', android: 'stop' },
  analyze: { ios: 'waveform', android: 'graphic_eq' },
  history: { ios: 'clock.arrow.circlepath', android: 'history' },
  info: { ios: 'info.circle', android: 'info' },
  suggestion: { ios: 'lightbulb.fill', android: 'lightbulb' },
  warning: { ios: 'exclamationmark.triangle.fill', android: 'warning' },
  emergency: { ios: 'cross.case.fill', android: 'emergency' },
  privacy: { ios: 'lock.shield.fill', android: 'shield' },
  credits: { ios: 'doc.text', android: 'article' },
  trash: { ios: 'trash', android: 'delete' },
  checked: { ios: 'checkmark.square.fill', android: 'check_box' },
  unchecked: { ios: 'square', android: 'check_box_outline_blank' },
  chevron: { ios: 'chevron.right', android: 'chevron_right' },
  edit: { ios: 'pencil', android: 'edit' },
  retry: { ios: 'arrow.clockwise', android: 'refresh' },
  check: { ios: 'checkmark', android: 'check' },
} as const;

export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 20, color }: { name: IconName; size?: number; color: ColorValue }) {
  return <SymbolView name={ICONS[name]} size={size} tintColor={color} />;
}
