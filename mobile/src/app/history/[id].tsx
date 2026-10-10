import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, ScrollView, StyleSheet, View } from 'react-native';
import { useFocusEffect, useLocalSearchParams } from 'expo-router';

import { ProbabilityBars, ResultHero, SuggestionCard } from '@/components/analysis-view';
import { LabelPicker } from '@/components/label-picker';
import { MemoInput } from '@/components/memo-input';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import {
  ConsentRequiredError,
  getRecord,
  labelRecord,
  retryReason,
  type CryClass,
  type RecordDetail,
} from '@/lib/api';
import { useConsent } from '@/lib/consent-context';

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString('ko-KR', { dateStyle: 'medium', timeStyle: 'short' });
}

const CONTEXT_KEYS = ['마지막 수유', '마지막 기저귀', '최근 피드백'] as const;

export default function HistoryDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const recordId = Number(id);
  const { reset: resetConsent } = useConsent();
  const theme = useTheme();

  const [record, setRecord] = useState<RecordDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState<CryClass | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [memo, setMemo] = useState('');
  const [savingMemo, setSavingMemo] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getRecord(recordId);
      setRecord(data);
      setMemo(data.memo ?? '');
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : '기록을 불러오지 못했어요.');
    }
  }, [recordId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleError = (e: unknown, fallback: string) => {
    if (e instanceof ConsentRequiredError) return resetConsent();
    Alert.alert('오류', e instanceof Error ? e.message : fallback);
  };

  // 라벨 수정은 덮어쓰기. 배고픔 라벨로 자동 생긴 수유 기록도 서버가 함께 정리한다 (FR11)
  const handleLabel = async (label: CryClass) => {
    setSaving(label);
    try {
      await labelRecord(recordId, label, memo.trim());
      await load();
    } catch (e) {
      handleError(e, '피드백 저장에 실패했어요.');
    } finally {
      setSaving(null);
    }
  };

  const handleSaveMemo = async () => {
    if (!record?.actual_label) return;
    setSavingMemo(true);
    try {
      await labelRecord(recordId, record.actual_label, memo.trim());
      await load();
    } catch (e) {
      handleError(e, '메모 저장에 실패했어요.');
    } finally {
      setSavingMemo(false);
    }
  };

  const handleRetry = async () => {
    if (!record) return;
    setRetrying(true);
    try {
      const res = await retryReason(recordId);
      setRecord({ ...record, ...res });
      if (res.suggestion === null) Alert.alert('제안 생성 실패', '잠시 후 다시 시도해주세요.');
    } catch (e) {
      handleError(e, '다시 시도에 실패했어요.');
    } finally {
      setRetrying(false);
    }
  };

  if (!record) {
    return (
      <ThemedView style={styles.center}>
        {loadError ? (
          <ThemedText type="small" themeColor="textSecondary">
            {loadError}
          </ThemedText>
        ) : (
          <ActivityIndicator />
        )}
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <ThemedText type="small" themeColor="textSecondary" style={styles.date}>
          {formatDate(record.created_at)}
        </ThemedText>
        <ResultHero prediction={record.prediction} branch={record.branch} />
        <SuggestionCard suggestion={record.suggestion} retrying={retrying} onRetry={handleRetry} />
        <ProbabilityBars probabilities={record.probabilities} />

        <Card>
          <ThemedText type="smallBold">분석 당시 기록</ThemedText>
          {CONTEXT_KEYS.map((key) => (
            <View key={key} style={styles.contextRow}>
              <ThemedText type="small" themeColor="textSecondary">
                {key}
              </ThemedText>
              <ThemedText type="small" style={styles.contextValue}>
                {record.context[key] ?? '기록 없음'}
              </ThemedText>
            </View>
          ))}
        </Card>

        <Card>
          <ThemedText type="smallBold">실제로는 무엇이었나요?</ThemedText>
          <View style={styles.noteRow}>
            <Icon name="info" size={14} color={theme.textSecondary} />
            <ThemedText type="small" themeColor="textSecondary" style={styles.noteText}>
              {record.actual_label
                ? '다른 항목을 누르면 수정돼요. 배고픔으로 고르면 수유 기록이 자동으로 추가돼요.'
                : '고른 피드백은 다음 분석 때 참고돼요.'}
            </ThemedText>
          </View>
          <LabelPicker selected={record.actual_label} saving={saving} onSelect={handleLabel} />
          <MemoInput
            value={memo}
            onChangeText={setMemo}
            showSave={record.actual_label !== null && memo.trim() !== (record.memo ?? '')}
            saving={savingMemo}
            onSave={handleSaveMemo}
          />
        </Card>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.six },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.four },
  date: { textAlign: 'center' },
  contextRow: { flexDirection: 'row', justifyContent: 'space-between', gap: Spacing.three },
  contextValue: { flex: 1, textAlign: 'right' },
  noteRow: { flexDirection: 'row', gap: Spacing.one, alignItems: 'flex-start' },
  noteText: { flex: 1 },
});
