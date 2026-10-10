import { useCallback, useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import Animated, {
  cancelAnimation,
  Easing,
  interpolate,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useFocusEffect } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { TimeEditPicker } from '@/components/time-edit-picker';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { IconCircle } from '@/components/ui/icon-circle';
import { ScreenHeader } from '@/components/ui/screen-header';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { useCryRecorder } from '@/hooks/use-cry-recorder';
import {
  ConsentRequiredError,
  createEvent,
  getContext,
  getEvents,
  predict,
  updateEventTime,
  type AnalysisContext,
  type CareEvent,
  type CareEventType,
} from '@/lib/api';
import { useConsent } from '@/lib/consent-context';
import { useResult } from '@/lib/result-context';

export default function AnalyzeScreen() {
  const theme = useTheme();
  const { setResult } = useResult();
  const { reset: resetConsent } = useConsent();
  const recorder = useCryRecorder();

  const [context, setContext] = useState<Partial<AnalysisContext>>({});
  const [latestEvents, setLatestEvents] = useState<Partial<Record<CareEventType, CareEvent>>>({});
  const [editingType, setEditingType] = useState<CareEventType | null>(null);
  const [recordedUri, setRecordedUri] = useState<string | null>(null);
  const [recordedSeconds, setRecordedSeconds] = useState(0);
  const [correcting, setCorrecting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const refreshContext = useCallback(async () => {
    try {
      const [ctx, events] = await Promise.all([getContext(), getEvents(30)]);
      setContext(ctx);
      // 서버가 최신순으로 준다. 종류별 첫 항목이 가장 최근 기록
      const latest: Partial<Record<CareEventType, CareEvent>> = {};
      for (const event of events) latest[event.type] ??= event;
      setLatestEvents(latest);
    } catch {
      // 백엔드 미기동 등 - 화면 진입 자체는 막지 않는다
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      refreshContext();
    }, [refreshContext])
  );

  const handleCorrect = async (type: 'feeding' | 'diaper') => {
    setCorrecting(true);
    try {
      await createEvent(type);
      await refreshContext();
    } catch (e) {
      if (e instanceof ConsentRequiredError) return resetConsent();
      Alert.alert('오류', e instanceof Error ? e.message : '이벤트 기록에 실패했어요.');
    } finally {
      setCorrecting(false);
    }
  };

  // 시각 직접 수정 (§8-1): 가장 최근 기록의 시각을 고치고, 기록이 없으면 그 시각으로 새로 만든다
  const handleSaveTime = async (date: Date) => {
    const type = editingType;
    setEditingType(null);
    if (!type) return;
    setCorrecting(true);
    try {
      const latest = latestEvents[type];
      if (latest) await updateEventTime(latest.id, date);
      else await createEvent(type, date);
      await refreshContext();
    } catch (e) {
      if (e instanceof ConsentRequiredError) return resetConsent();
      Alert.alert('오류', e instanceof Error ? e.message : '시각 수정에 실패했어요.');
    } finally {
      setCorrecting(false);
    }
  };

  const handleToggleRecording = async () => {
    if (recorder.isRecording) {
      setRecordedSeconds(Math.round(recorder.durationMillis / 1000));
      const uri = await recorder.stop();
      setRecordedUri(uri);
      return;
    }
    setRecordedUri(null);
    const started = await recorder.start();
    if (!started) {
      Alert.alert('마이크 권한 필요', '설정에서 마이크 접근을 허용해주세요.');
    }
  };

  const handleAnalyze = async () => {
    if (!recordedUri) return;
    setAnalyzing(true);
    try {
      const response = await predict(recordedUri);
      setResult(response);
      setRecordedUri(null);
      router.push('/result');
    } catch (e) {
      if (e instanceof ConsentRequiredError) return resetConsent();
      Alert.alert('분석 실패', e instanceof Error ? e.message : '알 수 없는 오류가 발생했어요.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <ScrollView contentContainerStyle={styles.scroll}>
          <ScreenHeader title="CryCare" subtitle="울음소리와 기록으로 먼저 해볼 일을 찾아드려요" />

          <View style={styles.careRow}>
            {CARE_ITEMS.map(({ type, label, contextKey, color }) => (
              <Card key={type} style={styles.careCard}>
                <View style={styles.careTop}>
                  <IconCircle name={type} color={color} size={36} />
                  <Pressable
                    disabled={correcting}
                    onPress={() => setEditingType(type)}
                    hitSlop={10}
                    accessibilityLabel={`${label} 시각 ${latestEvents[type] ? '수정' : '입력'}`}>
                    <Icon name="edit" size={18} color={theme.textSecondary} />
                  </Pressable>
                </View>
                <ThemedText type="small" themeColor="textSecondary">
                  마지막 {label}
                </ThemedText>
                <ThemedText style={styles.careValue} numberOfLines={1} adjustsFontSizeToFit>
                  {context[contextKey] ?? '…'}
                </ThemedText>
                <Button
                  label={`방금 ${label}`}
                  variant="secondary"
                  compact
                  disabled={correcting}
                  onPress={() => handleCorrect(type)}
                />
              </Card>
            ))}
          </View>

          <View style={styles.recordSection}>
            <RecordButton recording={recorder.isRecording} onPress={handleToggleRecording} />
            <ThemedText type="smallBold" style={styles.recordStatus}>
              {recorder.isRecording
                ? `듣고 있어요 · ${formatSeconds(recorder.durationMillis / 1000)}`
                : recordedUri
                  ? `녹음 완료 · ${formatSeconds(recordedSeconds)}`
                  : '버튼을 눌러 울음소리를 녹음하세요'}
            </ThemedText>
            {!recorder.isRecording && !recordedUri && (
              <ThemedText type="small" themeColor="textSecondary" style={styles.recordHint}>
                조용한 곳에서 아기 가까이 5~10초 녹음하고, 울음이 그치면 바로 멈춰주세요
              </ThemedText>
            )}
          </View>

          {!recorder.isRecording && recordedUri && (
            <View style={styles.actions}>
              <Button label="분석하기" icon="analyze" loading={analyzing} onPress={handleAnalyze} />
              <Button
                label="다시 녹음"
                variant="ghost"
                disabled={analyzing}
                onPress={() => setRecordedUri(null)}
              />
            </View>
          )}
        </ScrollView>
      </SafeAreaView>

      {editingType && (
        <TimeEditPicker
          initial={latestEvents[editingType] ? new Date(latestEvents[editingType].occurred_at) : new Date()}
          onSave={handleSaveTime}
          onCancel={() => setEditingType(null)}
        />
      )}
    </ThemedView>
  );
}

const CARE_ITEMS = [
  { type: 'feeding', label: '수유', contextKey: '마지막 수유', color: '#EA7440' },
  { type: 'diaper', label: '기저귀', contextKey: '마지막 기저귀', color: '#24A096' },
] as const;

function formatSeconds(seconds: number) {
  const s = Math.floor(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

const RECORD_SIZE = 148;

// 녹음 중에는 바깥 링이 숨 쉬듯 퍼진다
function RecordButton({ recording, onPress }: { recording: boolean; onPress: () => void }) {
  const theme = useTheme();
  const pulse = useSharedValue(0);

  useEffect(() => {
    if (!recording) {
      cancelAnimation(pulse);
      pulse.value = 0;
      return;
    }
    pulse.value = withRepeat(withTiming(1, { duration: 1400, easing: Easing.out(Easing.ease) }), -1, false);
  }, [recording, pulse]);

  const ringStyle = useAnimatedStyle(() => ({
    opacity: interpolate(pulse.value, [0, 1], [recording ? 0.35 : 0.12, 0]),
    transform: [{ scale: interpolate(pulse.value, [0, 1], [1, 1.45]) }],
  }));

  const color = recording ? theme.danger : theme.primary;

  return (
    <View style={styles.recordWrap}>
      <Animated.View
        pointerEvents="none"
        style={[styles.recordRing, { backgroundColor: color }, ringStyle]}
      />
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={recording ? '녹음 정지' : '녹음 시작'}
        style={({ pressed }) => [
          styles.recordButton,
          { backgroundColor: color, transform: [{ scale: pressed ? 0.96 : 1 }] },
        ]}>
        <Icon name={recording ? 'stop' : 'mic'} size={56} color={theme.onPrimary} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  scroll: { paddingHorizontal: Spacing.four, paddingBottom: Spacing.five, gap: Spacing.four },
  careRow: { flexDirection: 'row', gap: Spacing.three },
  careCard: { flex: 1, gap: Spacing.one },
  careTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: Spacing.one },
  careValue: { fontSize: 20, lineHeight: 28, fontWeight: 700, marginBottom: Spacing.two },
  recordSection: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.four },
  recordWrap: { width: RECORD_SIZE * 1.5, height: RECORD_SIZE * 1.5, alignItems: 'center', justifyContent: 'center' },
  recordRing: { position: 'absolute', width: RECORD_SIZE, height: RECORD_SIZE, borderRadius: RECORD_SIZE / 2 },
  recordButton: {
    width: RECORD_SIZE,
    height: RECORD_SIZE,
    borderRadius: RECORD_SIZE / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  recordStatus: { fontSize: 16 },
  recordHint: { textAlign: 'center' },
  actions: { gap: Spacing.two },
});
