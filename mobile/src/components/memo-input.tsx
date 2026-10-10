import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';

// 피드백 메모 (선택, §8-2). 라벨을 고를 때 함께 저장되고, 라벨 저장 후 고치면 저장 버튼이 뜬다.
export function MemoInput({
  value,
  onChangeText,
  showSave,
  saving,
  onSave,
}: {
  value: string;
  onChangeText: (text: string) => void;
  showSave: boolean;
  saving: boolean;
  onSave: () => void;
}) {
  const theme = useTheme();

  return (
    <View style={styles.container}>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder="메모 (선택) 예: 기저귀 갈아주니 그침"
        placeholderTextColor={theme.textSecondary}
        maxLength={200}
        multiline
        style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.background }]}
      />
      {showSave && (
        <Pressable disabled={saving} onPress={onSave} style={styles.saveButton} hitSlop={8}>
          <ThemedText type="smallBold" style={{ color: theme.primary }}>
            {saving ? '저장 중...' : '메모 저장'}
          </ThemedText>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: Spacing.one },
  input: {
    borderWidth: 1,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    minHeight: 44,
    fontSize: 14,
  },
  saveButton: { alignSelf: 'flex-end', paddingVertical: Spacing.one },
});
