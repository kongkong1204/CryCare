import { StyleSheet, View } from 'react-native';

import { BranchBadge, branchHint } from '@/components/branch-badge';
import { ThemedText } from '@/components/themed-text';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icon';
import { IconCircle } from '@/components/ui/icon-circle';
import { CLASS_META } from '@/constants/cry-classes';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { CLASS_LABELS_KO, type Branch, type CryClass, type Probability } from '@/lib/api';

// 결과 화면·이력 상세가 함께 쓰는 분석 결과 표시

export function ResultHero({ prediction, branch }: { prediction: CryClass; branch: Branch }) {
  const meta = CLASS_META[prediction];
  const hint = branchHint(branch);
  return (
    <View style={styles.hero}>
      <IconCircle name={meta.icon} color={meta.color} size={88} />
      <ThemedText style={styles.heroTitle}>{CLASS_LABELS_KO[prediction]}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {meta.hint}
      </ThemedText>
      <BranchBadge branch={branch} />
      {hint && (
        <ThemedText type="small" themeColor="textSecondary" style={styles.heroHint}>
          {hint}
        </ThemedText>
      )}
    </View>
  );
}

export function ProbabilityBars({ probabilities }: { probabilities: Probability[] }) {
  const theme = useTheme();
  return (
    <Card>
      <ThemedText type="smallBold">소리 분석 결과</ThemedText>
      {probabilities.slice(0, 3).map((p) => {
        const pct = Math.round(p.prob * 100);
        const color = CLASS_META[p.label].color;
        return (
          <View key={p.label} style={styles.probRow}>
            <ThemedText type="small" style={styles.probLabel}>
              {CLASS_LABELS_KO[p.label]}
            </ThemedText>
            <View style={[styles.probTrack, { backgroundColor: theme.backgroundSelected }]}>
              <View style={[styles.probFill, { width: `${pct}%`, backgroundColor: color }]} />
            </View>
            <ThemedText type="smallBold" style={styles.probPct}>
              {pct}%
            </ThemedText>
          </View>
        );
      })}
    </Card>
  );
}

export function SuggestionCard({
  suggestion,
  retrying,
  onRetry,
}: {
  suggestion: string | null;
  retrying: boolean;
  onRetry: () => void;
}) {
  const theme = useTheme();

  if (suggestion === null) {
    return (
      <Card tone="danger">
        <View style={styles.cardTitle}>
          <Icon name="warning" size={18} color={theme.danger} />
          <ThemedText type="smallBold" style={{ color: theme.danger }}>
            대응 제안을 만들지 못했어요
          </ThemedText>
        </View>
        <ThemedText type="small" themeColor="textSecondary">
          소리 분석 결과는 정상이에요. 잠시 후 다시 시도해주세요.
        </ThemedText>
        <Button label="다시 시도" icon="retry" variant="secondary" compact loading={retrying} onPress={onRetry} />
      </Card>
    );
  }

  return (
    <Card tone="primary">
      <View style={styles.cardTitle}>
        <Icon name="suggestion" size={18} color={theme.primary} />
        <ThemedText type="smallBold" style={{ color: theme.primary }}>
          이렇게 해보세요
        </ThemedText>
      </View>
      <ThemedText type="default" style={styles.suggestion}>
        {suggestion}
      </ThemedText>
    </Card>
  );
}

const styles = StyleSheet.create({
  hero: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.three },
  heroTitle: { fontSize: 34, lineHeight: 42, fontWeight: 700, marginTop: Spacing.one },
  heroHint: { textAlign: 'center', paddingHorizontal: Spacing.three },
  probRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  probLabel: { width: 64 },
  probTrack: { flex: 1, height: 10, borderRadius: Radius.pill, overflow: 'hidden' },
  probFill: { height: '100%', borderRadius: Radius.pill },
  probPct: { width: 44, textAlign: 'right' },
  cardTitle: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  suggestion: { lineHeight: 26 },
});
