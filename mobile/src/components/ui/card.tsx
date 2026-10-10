import { StyleSheet, View, type ViewProps } from 'react-native';

import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

// 배경 위에 얹는 기본 카드. tone으로 강조 배경을 바꾼다.
export function Card({
  style,
  tone = 'default',
  ...rest
}: ViewProps & { tone?: 'default' | 'primary' | 'warning' | 'danger' }) {
  const theme = useTheme();
  const backgroundColor = {
    default: theme.backgroundElement,
    primary: theme.primarySoft,
    warning: theme.warningSoft,
    danger: theme.dangerSoft,
  }[tone];
  const borderColor = tone === 'default' ? theme.border : 'transparent';

  return <View style={[styles.card, { backgroundColor, borderColor }, style]} {...rest} />;
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: Spacing.three,
    gap: Spacing.two,
  },
});
