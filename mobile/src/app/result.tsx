import { useState } from 'react';
import { Alert, ScrollView, StyleSheet } from 'react-native';
import { router } from 'expo-router';

import { ProbabilityBars, ResultHero, SuggestionCard } from '@/components/analysis-view';
import { LabelPicker } from '@/components/label-picker';
import { MemoInput } from '@/components/memo-input';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { PROLONGED_CRYING_NOTICE, RESULT_FOOTER } from '@/constants/notices';
import { Spacing } from '@/constants/theme';
import {
  ConsentRequiredError,
  labelRecord,
  retryReason,
  type CryClass,
} from '@/lib/api';
import { useConsent } from '@/lib/consent-context';
import { useResult } from '@/lib/result-context';

export default function ResultScreen() {
  const { result, setResult } = useResult();
  const { reset: resetConsent } = useConsent();
  const [retrying, setRetrying] = useState(false);
  const [savedLabel, setSavedLabel] = useState<CryClass | null>(null);
  const [saving, setSaving] = useState<CryClass | null>(null);
  const [memo, setMemo] = useState('');
  const [savedMemo, setSavedMemo] = useState('');
  const [savingMemo, setSavingMemo] = useState(false);

  if (!result) {
    return (
      <ThemedView style={styles.emptyContainer}>
        <ThemedText type="default">표시할 결과가 없어요.</ThemedText>
        <Button label="돌아가기" variant="ghost" onPress={() => router.back()} />
      </ThemedView>
    );
  }

  const handleFeedback = async (label: CryClass) => {
    setSaving(label);
    try {
      await labelRecord(result.record_id, label, memo.trim());
      setSavedLabel(label);
      setSavedMemo(memo.trim());
    } catch (e) {
      if (e instanceof ConsentRequiredError) return resetConsent();
      Alert.alert('오류', e instanceof Error ? e.message : '피드백 저장에 실패했어요.');
    } finally {
      setSaving(null);
    }
  };

  const handleSaveMemo = async () => {
    if (!savedLabel) return;
    setSavingMemo(true);
    try {
      await labelRecord(result.record_id, savedLabel, memo.trim());
      setSavedMemo(memo.trim());
    } catch (e) {
      if (e instanceof ConsentRequiredError) return resetConsent();
      Alert.alert('오류', e instanceof Error ? e.message : '메모 저장에 실패했어요.');
    } finally {
      setSavingMemo(false);
    }
  };

  // B4: 제안 생성 실패 시 분류 결과는 그대로 두고 제안만 다시 요청 (FR12)
  const handleRetry = async () => {
    setRetrying(true);
    try {
      const res = await retryReason(result.record_id);
      setResult({ ...result, ...res });
      if (res.suggestion === null) Alert.alert('제안 생성 실패', '잠시 후 다시 시도해주세요.');
    } catch (e) {
      if (e instanceof ConsentRequiredError) return resetConsent();
      Alert.alert('오류', e instanceof Error ? e.message : '다시 시도에 실패했어요.');
    } finally {
      setRetrying(false);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <ResultHero prediction={result.prediction} branch={result.branch} />
        {result.prolonged_crying && (
          <Card tone="danger">
            <ThemedText type="smallBold">오래 울고 있나요?</ThemedText>
            <ThemedText type="small">{PROLONGED_CRYING_NOTICE}</ThemedText>
          </Card>
        )}
        <SuggestionCard suggestion={result.suggestion} retrying={retrying} onRetry={handleRetry} />
        <ProbabilityBars probabilities={result.probabilities} />

        <Card>
          <ThemedText type="smallBold">실제로는 무엇이었나요?</ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            {savedLabel ? '저장됐어요. 다른 항목을 누르면 바뀌어요.' : '알려주시면 다음 분석에 참고해요.'}
          </ThemedText>
          <LabelPicker selected={savedLabel} saving={saving} onSelect={handleFeedback} />
          <MemoInput
            value={memo}
            onChangeText={setMemo}
            showSave={savedLabel !== null && memo.trim() !== savedMemo}
            saving={savingMemo}
            onSave={handleSaveMemo}
          />
        </Card>

        <ThemedText type="small" themeColor="textSecondary" style={styles.footer}>
          {RESULT_FOOTER}
        </ThemedText>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.four, gap: Spacing.three, paddingBottom: Spacing.six },
  emptyContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: Spacing.two },
  footer: { textAlign: 'center', marginTop: Spacing.two },
});
