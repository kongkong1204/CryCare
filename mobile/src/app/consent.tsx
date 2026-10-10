import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Icon, type IconName } from '@/components/ui/icon';
import { IconCircle } from '@/components/ui/icon-circle';
import {
  DISCLAIMER,
  GUARDIAN_NOTICE,
  PRIVACY_ITEMS,
  WARNING_SIGNS,
  WARNING_SIGNS_INTRO,
} from '@/constants/notices';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useConsent } from '@/lib/consent-context';

// 최초 실행 동의 (스펙 §8-0, FR14). 동의해야 앱을 쓸 수 있다.
export default function ConsentScreen() {
  const theme = useTheme();
  const { agree } = useConsent();
  const [privacyChecked, setPrivacyChecked] = useState(false);
  const [disclaimerChecked, setDisclaimerChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const allChecked = privacyChecked && disclaimerChecked;

  const handleAgree = async () => {
    setSubmitting(true);
    try {
      await agree();
    } catch (e) {
      Alert.alert(
        '동의 기록 실패',
        `서버에 연결할 수 없어요. 네트워크를 확인하고 다시 시도해주세요.\n${e instanceof Error ? e.message : ''}`
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.hero}>
            <IconCircle name="hug" color={theme.primary} size={72} />
            <ThemedText style={styles.title}>CryCare 시작하기</ThemedText>
            <ThemedText type="small" themeColor="textSecondary" style={styles.subtitle}>
              시작하기 전에 아래 내용을 확인해주세요
            </ThemedText>
          </View>

          <Section icon="info" title="육아 보조 도구 안내">
            <ThemedText type="small">{DISCLAIMER}</ThemedText>
          </Section>

          <Section icon="emergency" title="이럴 땐 바로 병원에" tone="warning">
            <ThemedText type="small">{WARNING_SIGNS_INTRO}</ThemedText>
            {WARNING_SIGNS.map((sign) => (
              <ThemedText key={sign} type="small">
                • {sign}
              </ThemedText>
            ))}
          </Section>

          <Section icon="privacy" title="개인정보 수집·이용 안내">
            <ThemedText type="small" themeColor="textSecondary">
              {GUARDIAN_NOTICE}
            </ThemedText>
            {PRIVACY_ITEMS.map((item) => (
              <View key={item.label} style={styles.item}>
                <ThemedText type="smallBold">{item.label}</ThemedText>
                <ThemedText type="small">{item.value}</ThemedText>
              </View>
            ))}
          </Section>

          <View style={styles.checks}>
            <CheckRow
              checked={privacyChecked}
              onToggle={() => setPrivacyChecked((v) => !v)}
              label="(필수) 아기의 보호자로서 위 개인정보 수집·이용에 동의합니다."
            />
            <CheckRow
              checked={disclaimerChecked}
              onToggle={() => setDisclaimerChecked((v) => !v)}
              label="(필수) CryCare가 의료기기가 아닌 참고용 육아 보조 도구임을 확인했습니다."
            />
            <ThemedText type="small" themeColor="textSecondary" style={styles.refusal}>
              동의를 거부할 권리가 있으며, 거부 시 서비스 이용이 제한됩니다.
            </ThemedText>
          </View>

          <Button label="동의하고 시작하기" disabled={!allChecked} loading={submitting} onPress={handleAgree} />
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

function Section({
  icon,
  title,
  tone,
  children,
}: {
  icon: IconName;
  title: string;
  tone?: 'warning';
  children: React.ReactNode;
}) {
  const theme = useTheme();
  const color = tone === 'warning' ? theme.warning : theme.primary;
  return (
    <Card tone={tone}>
      <View style={styles.sectionTitle}>
        <Icon name={icon} size={18} color={color} />
        <ThemedText type="smallBold" style={{ color }}>
          {title}
        </ThemedText>
      </View>
      {children}
    </Card>
  );
}

function CheckRow({ checked, onToggle, label }: { checked: boolean; onToggle: () => void; label: string }) {
  const theme = useTheme();
  return (
    <Pressable
      onPress={onToggle}
      style={[styles.checkRow, { borderColor: checked ? theme.primary : theme.border, backgroundColor: theme.backgroundElement }]}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}>
      <Icon name={checked ? 'checked' : 'unchecked'} size={24} color={checked ? theme.primary : theme.textSecondary} />
      <ThemedText type="small" style={styles.checkLabel}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  scroll: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.five },
  hero: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.three },
  title: { fontSize: 26, lineHeight: 34, fontWeight: 700 },
  subtitle: { textAlign: 'center' },
  sectionTitle: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  item: { gap: Spacing.half },
  checks: { gap: Spacing.two, marginTop: Spacing.two },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    borderWidth: 1,
    borderRadius: 12,
    padding: Spacing.three,
  },
  checkLabel: { flex: 1 },
  refusal: { textAlign: 'center', marginTop: Spacing.one },
});
