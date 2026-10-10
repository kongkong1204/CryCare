import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from 'expo-router';
import { useColorScheme } from 'react-native';

import { Colors } from '@/constants/theme';

import { ConsentProvider, useConsent } from '@/lib/consent-context';
import { ResultProvider } from '@/lib/result-context';

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const base = isDark ? DarkTheme : DefaultTheme;
  const palette = Colors[isDark ? 'dark' : 'light'];
  // 내비게이션 헤더·배경을 앱 팔레트에 맞춘다
  const navTheme = {
    ...base,
    colors: {
      ...base.colors,
      primary: palette.primary,
      background: palette.background,
      card: palette.background,
      text: palette.text,
      border: palette.border,
    },
  };

  return (
    <ThemeProvider value={navTheme}>
      <ConsentProvider>
        <ResultProvider>
          <RootStack />
        </ResultProvider>
      </ConsentProvider>
    </ThemeProvider>
  );
}

function RootStack() {
  const { consented } = useConsent();

  // 동의 전에는 동의 화면만 열린다 (스펙 §8-0)
  return (
    <Stack screenOptions={{ headerTitleAlign: 'center', headerShadowVisible: false, headerBackButtonDisplayMode: 'minimal' }}>
      <Stack.Protected guard={consented}>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="result" options={{ title: '분석 결과' }} />
        <Stack.Screen name="history/[id]" options={{ title: '기록 상세' }} />
      </Stack.Protected>
      <Stack.Protected guard={!consented}>
        <Stack.Screen name="consent" options={{ headerShown: false }} />
      </Stack.Protected>
    </Stack>
  );
}
