import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import {
  DISCLAIMER,
  GUARDIAN_NOTICE,
  PRIVACY_ITEMS,
  WARNING_SIGNS,
  WARNING_SIGNS_INTRO,
} from '@/constants/notices';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Icon, type IconName } from '@/components/ui/icon';
import { ScreenHeader } from '@/components/ui/screen-header';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { deleteAllData } from '@/lib/api';
import { useConsent } from '@/lib/consent-context';
import { getDeviceId, getLocalConsent, resetDevice } from '@/lib/device';
import { useResult } from '@/lib/result-context';

// 스펙 §10.3 출처 신고
const CREDITS: { label: string; value: string }[] = [
  { label: '생성형 AI', value: 'Claude Haiku 4.5 (대응 제안 생성), Claude Code (개발 보조)' },
  { label: '데이터', value: 'babycry (Kaggle, chris0223) — 연구·비상업 목적 한정 사용' },
  {
    label: '오픈소스',
    value: 'librosa, scikit-learn, NumPy, SciPy, FastAPI, uvicorn, anthropic SDK, SQLite, React Native, Expo, expo-audio',
  },
  { label: '외부 서비스', value: 'Google Cloud Run (서버, 서울 리전), Anthropic API (대응 제안 생성)' },
];

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function AboutScreen() {
  const { setResult } = useResult();
  const { reset: resetConsent } = useConsent();
  const [deleting, setDeleting] = useState(false);
  const consent = getLocalConsent();

  const runDelete = async () => {
    setDeleting(true);
    try {
      const res = await deleteAllData();
      setResult(null);
      Alert.alert(
        '삭제 완료',
        `서버에서 분석 기록 ${res.deleted_records}건(녹음 포함)과 수유·기저귀 기록 ${res.deleted_events}건을 영구 삭제하고 동의를 철회했어요.`,
        [
          {
            text: '확인',
            // 동의 철회: 새 기기 식별자로 바꾸고 동의 화면으로 돌아간다
            onPress: () => {
              resetDevice();
              resetConsent();
            },
          },
        ]
      );
    } catch (e) {
      Alert.alert('삭제 실패', e instanceof Error ? e.message : '잠시 후 다시 시도해주세요.');
    } finally {
      setDeleting(false);
    }
  };

  const handleDelete = () => {
    Alert.alert(
      '내 데이터 전체 삭제',
      '서버에 저장된 녹음, 분석 기록, 수유·기저귀 기록, 피드백이 모두 영구 삭제되고 동의도 철회돼요. 되돌릴 수 없어요.',
      [
        { text: '취소', style: 'cancel' },
        { text: '삭제', style: 'destructive', onPress: runDelete },
      ]
    );
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ScrollView contentContainerStyle={styles.scroll}>
          <ScreenHeader title="About" subtitle="CryCare 안내와 내 데이터 관리" />

          <Section icon="info" title="CryCare는">
            <ThemedText type="small">
              아기 울음소리를 분석하고 수유·기저귀 기록과 함께 살펴서, 무엇을 먼저 시도해볼지 제안하는 육아 보조
              앱이에요.
            </ThemedText>
            <ThemedText type="smallBold">{DISCLAIMER}</ThemedText>
          </Section>

          <Section icon="emergency" title="이럴 땐 바로 병원에" tone="warning">
            <ThemedText type="small">{WARNING_SIGNS_INTRO}</ThemedText>
            {WARNING_SIGNS.map((sign) => (
              <ThemedText key={sign} type="small">
                • {sign}
              </ThemedText>
            ))}
          </Section>

          <Section icon="privacy" title="개인정보 처리 안내">
            <ThemedText type="small" themeColor="textSecondary">
              {GUARDIAN_NOTICE}
            </ThemedText>
            {PRIVACY_ITEMS.map((item) => (
              <View key={item.label} style={styles.item}>
                <ThemedText type="smallBold">{item.label}</ThemedText>
                <ThemedText type="small">{item.value}</ThemedText>
              </View>
            ))}
            <View style={styles.meta}>
              {consent && (
                <ThemedText type="small" themeColor="textSecondary">
                  동의 일시: {formatDate(consent.agreedAt)} ({consent.version})
                </ThemedText>
              )}
              <ThemedText type="small" themeColor="textSecondary">
                기기 식별자: {getDeviceId().slice(0, 8)}…
              </ThemedText>
            </View>
            <Button label="내 데이터 전체 삭제" icon="trash" variant="danger" loading={deleting} onPress={handleDelete} />
          </Section>

          <Section icon="credits" title="출처">
            {CREDITS.map((item) => (
              <View key={item.label} style={styles.item}>
                <ThemedText type="smallBold">{item.label}</ThemedText>
                <ThemedText type="small">{item.value}</ThemedText>
              </View>
            ))}
          </Section>
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

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  scroll: { paddingHorizontal: Spacing.four, paddingBottom: Spacing.five, gap: Spacing.three },
  sectionTitle: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  item: { gap: Spacing.half },
  meta: { gap: Spacing.half, marginTop: Spacing.one },
});
