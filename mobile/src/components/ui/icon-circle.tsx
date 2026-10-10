import { View } from 'react-native';

import { Icon, type IconName } from '@/components/ui/icon';

// 색 원 안의 아이콘 (클래스·이벤트 표시)
export function IconCircle({ name, color, size = 40 }: { name: IconName; color: string; size?: number }) {
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: `${color}22`,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
      <Icon name={name} size={size * 0.5} color={color} />
    </View>
  );
}
