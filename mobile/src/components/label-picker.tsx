import { Pressable, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Icon } from '@/components/ui/icon';
import { CLASS_META } from '@/constants/cry-classes';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { CLASS_LABELS_KO, CLASSES, type CryClass } from '@/lib/api';

// "실제 니즈는?" 5클래스 택1 (FR6). 다시 누르면 덮어쓰기 (FR11).
export function LabelPicker({
  selected,
  saving,
  onSelect,
}: {
  selected: CryClass | null;
  saving: CryClass | null;
  onSelect: (label: CryClass) => void;
}) {
  const theme = useTheme();

  return (
    <View style={styles.row}>
      {CLASSES.map((cls) => {
        const isSelected = selected === cls;
        const { icon, color } = CLASS_META[cls];
        return (
          <Pressable
            key={cls}
            disabled={saving !== null || isSelected}
            onPress={() => onSelect(cls)}
            accessibilityRole="radio"
            accessibilityState={{ selected: isSelected }}
            style={[
              styles.chip,
              {
                borderColor: isSelected ? color : theme.border,
                backgroundColor: isSelected ? `${color}22` : theme.backgroundElement,
                opacity: saving !== null && saving !== cls ? 0.5 : 1,
              },
            ]}>
            <Icon name={isSelected ? 'check' : icon} size={16} color={color} />
            <ThemedText type={isSelected ? 'smallBold' : 'small'}>{CLASS_LABELS_KO[cls]}</ThemedText>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.one,
    borderWidth: 1,
    borderRadius: Radius.pill,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
});
