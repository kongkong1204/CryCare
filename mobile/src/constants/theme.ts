/**
 * Below are the colors that are used in the app. The colors are defined in the light and dark mode.
 * There are many other ways to style your app. For example, [Nativewind](https://www.nativewind.dev/), [Tamagui](https://tamagui.dev/), [unistyles](https://reactnativeunistyles.vercel.app), etc.
 */

import '@/global.css';

import { Platform } from 'react-native';

// 차분한 웜톤 배경 + 인디고 포인트. 카드(backgroundElement)는 배경보다 한 단계 밝게(라이트)/높게(다크).
export const Colors = {
  light: {
    text: '#1C1B1F',
    background: '#F6F4F0',
    backgroundElement: '#FFFFFF',
    backgroundSelected: '#ECE8E1',
    textSecondary: '#6B6760',
    border: '#E4E0D8',
    primary: '#5B67E8',
    primarySoft: '#EAECFD',
    onPrimary: '#FFFFFF',
    danger: '#D93F45',
    dangerSoft: '#FCEBEB',
    warning: '#A65F00',
    warningSoft: '#FFF3DF',
  },
  dark: {
    text: '#F3F2F5',
    background: '#111216',
    backgroundElement: '#1C1D23',
    backgroundSelected: '#2A2C34',
    textSecondary: '#A3A2AB',
    border: '#2E3038',
    primary: '#8590FF',
    primarySoft: '#262A4D',
    onPrimary: '#FFFFFF',
    danger: '#FF6B6F',
    dangerSoft: '#3A1E21',
    warning: '#FFB547',
    warningSoft: '#3A2E17',
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: 'var(--font-display)',
    serif: 'var(--font-serif)',
    rounded: 'var(--font-rounded)',
    mono: 'var(--font-mono)',
  },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const Radius = { sm: 8, md: 12, lg: 20, pill: 999 } as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 800;
