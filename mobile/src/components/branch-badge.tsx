import { StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import type { Branch } from '@/lib/api';

// 서버가 코드로 판정한 분기 (스펙 §3.1, §8-2). 정확도를 장담하지 않도록
// "판단 근거가 얼마나 갖춰졌는지"를 단계로 표시한다. B4는 단계 없음.
const STAGES: Record<Branch, { stage: number | null; label: string; hint: string | null }> = {
  B3: { stage: 1, label: '기록 부족', hint: '수유·기저귀 기록이 없어 소리만 참고했어요. 기록하면 다음부터 더 정확해져요.' },
  B2: { stage: 2, label: '확실하지 않음', hint: '소리나 기록만으로는 단정하기 어려워요. 아래 순서대로 시도해보세요.' },
  B1: { stage: 3, label: '근거 일치', hint: '소리 분석과 기록이 같은 쪽을 가리켜요. 그래도 참고용으로만 봐주세요.' },
  B4: { stage: null, label: '제안 없음', hint: null },
};

const MAX_STAGE = 3;

export function branchHint(branch: Branch) {
  return STAGES[branch].hint;
}

export function BranchBadge({ branch }: { branch: Branch }) {
  const theme = useTheme();
  const { stage, label } = STAGES[branch];
  const { bg, fg } = {
    B1: { bg: theme.primarySoft, fg: theme.primary },
    B2: { bg: theme.warningSoft, fg: theme.warning },
    B3: { bg: theme.backgroundSelected, fg: theme.text },
    B4: { bg: theme.dangerSoft, fg: theme.danger },
  }[branch];

  return (
    <View
      style={[styles.badge, { backgroundColor: bg }]}
      accessibilityLabel={stage ? `판단 근거 ${stage}단계, ${label}` : label}>
      {stage !== null && (
        <View style={styles.dots}>
          {Array.from({ length: MAX_STAGE }, (_, i) => (
            <View key={i} style={[styles.dot, { backgroundColor: fg, opacity: i < stage ? 1 : 0.25 }]} />
          ))}
        </View>
      )}
      <ThemedText type="smallBold" style={{ color: fg }}>
        {stage !== null ? `${stage}단계 · ${label}` : label}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    alignSelf: 'center',
    borderRadius: Radius.pill,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
  },
  dots: { flexDirection: 'row', gap: 3 },
  dot: { width: 6, height: 6, borderRadius: 3 },
});
