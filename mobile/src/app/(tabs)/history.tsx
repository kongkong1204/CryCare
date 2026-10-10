import { useCallback, useState } from 'react';
import { Alert, FlatList, Pressable, RefreshControl, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useFocusEffect } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { TimeEditPicker } from '@/components/time-edit-picker';
import { BranchBadge } from '@/components/branch-badge';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { IconCircle } from '@/components/ui/icon-circle';
import { ScreenHeader } from '@/components/ui/screen-header';
import { CLASS_META } from '@/constants/cry-classes';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import {
  CLASS_LABELS_KO,
  ConsentRequiredError,
  deleteEvent,
  EVENT_LABELS_KO,
  getEvents,
  getHistory,
  updateEventTime,
  type CareEvent,
  type HistoryItem,
} from '@/lib/api';
import { useConsent } from '@/lib/consent-context';

type Tab = 'records' | 'events';

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function HistoryScreen() {
  const theme = useTheme();
  const { reset: resetConsent } = useConsent();
  const [tab, setTab] = useState<Tab>('records');
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [events, setEvents] = useState<CareEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState<CareEvent | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [historyData, eventData] = await Promise.all([getHistory(), getEvents()]);
      setItems(historyData);
      setEvents(eventData);
      setErrorMessage(null);
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : '이력을 불러오지 못했어요.');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleError = (e: unknown, fallback: string) => {
    if (e instanceof ConsentRequiredError) return resetConsent();
    Alert.alert('오류', e instanceof Error ? e.message : fallback);
  };

  const handleSaveTime = async (date: Date) => {
    const target = editing;
    setEditing(null);
    if (!target) return;
    try {
      await updateEventTime(target.id, date);
      await load();
    } catch (e) {
      handleError(e, '시각 수정에 실패했어요.');
    }
  };

  const handleDelete = (event: CareEvent) => {
    Alert.alert('기록 삭제', `${EVENT_LABELS_KO[event.type]} · ${formatDate(event.occurred_at)} 기록을 삭제할까요?`, [
      { text: '취소', style: 'cancel' },
      {
        text: '삭제',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteEvent(event.id);
            await load();
          } catch (e) {
            handleError(e, '삭제에 실패했어요.');
          }
        },
      },
    ]);
  };

  const isEmpty = tab === 'records' ? items.length === 0 : events.length === 0;
  const refreshControl = <RefreshControl refreshing={loading} onRefresh={load} tintColor={theme.textSecondary} />;

  const header = (
    <View style={styles.headerBlock}>
      <ScreenHeader title="이력" subtitle="분석 결과와 수유·기저귀 기록을 확인하고 고칠 수 있어요" />
      <View style={[styles.segment, { backgroundColor: theme.backgroundSelected }]}>
        {TABS.map(([key, label]) => {
          const active = tab === key;
          return (
            <Pressable
              key={key}
              onPress={() => setTab(key)}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              style={[styles.segmentItem, active && { backgroundColor: theme.backgroundElement }]}>
              <ThemedText type={active ? 'smallBold' : 'small'} themeColor={active ? 'text' : 'textSecondary'}>
                {label}
              </ThemedText>
            </Pressable>
          );
        })}
      </View>
      {errorMessage && (
        <Card tone="danger">
          <ThemedText type="small">{errorMessage}</ThemedText>
        </Card>
      )}
      {!errorMessage && isEmpty && !loading && (
        <ThemedText type="small" themeColor="textSecondary" style={styles.empty}>
          {tab === 'records' ? '아직 분석 기록이 없어요.' : '아직 수유·기저귀 기록이 없어요.'}
        </ThemedText>
      )}
    </View>
  );

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        {tab === 'records' ? (
          <FlatList
            data={items}
            keyExtractor={(item) => String(item.id)}
            refreshControl={refreshControl}
            ListHeaderComponent={header}
            contentContainerStyle={styles.listContent}
            renderItem={({ item }) => {
              const meta = CLASS_META[item.prediction];
              return (
                <Pressable
                  onPress={() => router.push({ pathname: '/history/[id]', params: { id: String(item.id) } })}
                  style={({ pressed }) => [{ opacity: pressed ? 0.7 : 1 }]}>
                  <Card style={styles.recordCard}>
                    <IconCircle name={meta.icon} color={meta.color} size={44} />
                    <View style={styles.recordBody}>
                      <View style={styles.recordTitleRow}>
                        <ThemedText type="smallBold">{CLASS_LABELS_KO[item.prediction]}</ThemedText>
                        <ThemedText type="small" themeColor="textSecondary">
                          {formatDate(item.created_at)}
                        </ThemedText>
                      </View>
                      <ThemedText type="small" themeColor="textSecondary" numberOfLines={2}>
                        {item.suggestion ?? '대응 제안을 만들지 못했어요'}
                      </ThemedText>
                      <View style={styles.recordFooter}>
                        <BranchBadge branch={item.branch} />
                        <ThemedText type="small" themeColor="textSecondary">
                          {item.actual_label ? `실제: ${CLASS_LABELS_KO[item.actual_label]}` : '실제 니즈 미입력'}
                        </ThemedText>
                      </View>
                    </View>
                    <Icon name="chevron" size={16} color={theme.textSecondary} />
                  </Card>
                </Pressable>
              );
            }}
          />
        ) : (
          <FlatList
            data={events}
            keyExtractor={(event) => String(event.id)}
            refreshControl={refreshControl}
            ListHeaderComponent={header}
            contentContainerStyle={styles.listContent}
            renderItem={({ item: event }) => (
              <Card style={styles.eventCard}>
                <IconCircle name={event.type} color={EVENT_COLORS[event.type]} size={40} />
                <View style={styles.recordBody}>
                  <ThemedText type="smallBold">{EVENT_LABELS_KO[event.type]}</ThemedText>
                  <ThemedText type="small" themeColor="textSecondary">
                    {formatDate(event.occurred_at)}
                    {event.source === 'feedback' ? ' · 피드백으로 자동 기록' : ''}
                  </ThemedText>
                </View>
                <Pressable
                  onPress={() => setEditing(event)}
                  hitSlop={8}
                  accessibilityLabel="시각 수정"
                  style={[styles.iconButton, { backgroundColor: theme.backgroundSelected }]}>
                  <Icon name="edit" size={16} color={theme.text} />
                </Pressable>
                <Pressable
                  onPress={() => handleDelete(event)}
                  hitSlop={8}
                  accessibilityLabel="삭제"
                  style={[styles.iconButton, { backgroundColor: theme.dangerSoft }]}>
                  <Icon name="trash" size={16} color={theme.danger} />
                </Pressable>
              </Card>
            )}
          />
        )}
      </SafeAreaView>

      {editing && (
        <TimeEditPicker
          initial={new Date(editing.occurred_at)}
          onSave={handleSaveTime}
          onCancel={() => setEditing(null)}
        />
      )}
    </ThemedView>
  );
}

const TABS = [
  ['records', '분석 기록'],
  ['events', '수유·기저귀'],
] as const;

const EVENT_COLORS = { feeding: '#EA7440', diaper: '#24A096' } as const;

const styles = StyleSheet.create({
  container: { flex: 1 },
  safeArea: { flex: 1 },
  headerBlock: { gap: Spacing.three, marginBottom: Spacing.one },
  segment: { flexDirection: 'row', borderRadius: Radius.md, padding: 3 },
  segmentItem: { flex: 1, alignItems: 'center', paddingVertical: Spacing.two, borderRadius: Radius.md - 3 },
  empty: { textAlign: 'center', marginTop: Spacing.five },
  listContent: { paddingHorizontal: Spacing.four, gap: Spacing.two, paddingBottom: Spacing.five },
  recordCard: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  recordBody: { flex: 1, gap: Spacing.one },
  recordTitleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  recordFooter: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: Spacing.half },
  eventCard: { flexDirection: 'row', alignItems: 'center', gap: Spacing.three },
  iconButton: { width: 34, height: 34, borderRadius: 17, alignItems: 'center', justifyContent: 'center' },
});
