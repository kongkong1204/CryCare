import { useState } from 'react';
import { Alert, Modal, Platform, Pressable, StyleSheet } from 'react-native';
import { DateTimePicker } from '@expo/ui/community/datetime-picker';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';

// 케어 기록은 최근 일주일 안에서만 고친다. 미래 시각은 고를 수 없다 (maximumDate = 지금).
const MAX_DAYS_BACK = 7;

function minimumDate() {
  const d = new Date();
  d.setDate(d.getDate() - MAX_DAYS_BACK);
  d.setHours(0, 0, 0, 0);
  return d;
}

type Props = {
  initial: Date;
  onSave: (date: Date) => void;
  onCancel: () => void;
};

// 마운트되면 바로 열린다. 저장·취소 후 호출부에서 언마운트할 것.
export function TimeEditPicker(props: Props) {
  return Platform.OS === 'android' ? <AndroidDialogs {...props} /> : <IosSheet {...props} />;
}

// Android 시스템 다이얼로그는 날짜·시간을 한 번에 못 고른다 → 날짜 다음 시간.
// 시간 다이얼로그는 maximumDate를 지원하지 않아 고른 뒤 미래인지 검사한다.
function AndroidDialogs({ initial, onSave, onCancel }: Props) {
  const [day, setDay] = useState<Date | null>(null);

  if (!day) {
    return (
      <DateTimePicker
        value={initial}
        mode="date"
        minimumDate={minimumDate()}
        maximumDate={new Date()}
        onValueChange={(_, date) => setDay(date)}
        onDismiss={onCancel}
        positiveButton={{ label: '다음' }}
        negativeButton={{ label: '취소' }}
      />
    );
  }

  return (
    <DateTimePicker
      value={initial}
      mode="time"
      is24Hour={false}
      onValueChange={(_, time) => {
        const result = new Date(day.getFullYear(), day.getMonth(), day.getDate(), time.getHours(), time.getMinutes());
        if (result.getTime() > Date.now()) {
          Alert.alert('미래 시각은 고를 수 없어요', '지금보다 이전 시각을 선택해주세요.');
          onCancel();
          return;
        }
        onSave(result);
      }}
      onDismiss={onCancel}
      positiveButton={{ label: '저장' }}
      negativeButton={{ label: '취소' }}
    />
  );
}

function IosSheet({ initial, onSave, onCancel }: Props) {
  const colorScheme = useColorScheme();
  const [value, setValue] = useState(initial);
  // 시트를 연 뒤 시간이 흘러도 그 시점까지만 고를 수 있게 고정
  const [maxDate] = useState(() => new Date());

  return (
    <Modal transparent animationType="slide" onRequestClose={onCancel}>
      <Pressable style={styles.backdrop} onPress={onCancel} />
      <ThemedView style={styles.sheet}>
        <ThemedView style={styles.sheetHeader}>
          <Pressable onPress={onCancel} hitSlop={8}>
            <ThemedText type="small">취소</ThemedText>
          </Pressable>
          <ThemedText type="smallBold">시각 수정</ThemedText>
          <Pressable onPress={() => onSave(value.getTime() > maxDate.getTime() ? maxDate : value)} hitSlop={8}>
            <ThemedText type="smallBold">저장</ThemedText>
          </Pressable>
        </ThemedView>
        <DateTimePicker
          value={value}
          mode="datetime"
          display="spinner"
          locale="ko_KR"
          minimumDate={minimumDate()}
          maximumDate={maxDate}
          themeVariant={colorScheme === 'dark' ? 'dark' : 'light'}
          onValueChange={(_, date) => setValue(date)}
          style={styles.picker}
        />
      </ThemedView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.3)' },
  sheet: {
    paddingHorizontal: Spacing.four,
    paddingTop: Spacing.three,
    paddingBottom: Spacing.five,
    borderTopLeftRadius: Spacing.three,
    borderTopRightRadius: Spacing.three,
  },
  sheetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  picker: { height: 216 },
});
