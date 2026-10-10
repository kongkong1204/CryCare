import { Tabs } from 'expo-router';

import { Icon } from '@/components/ui/icon';
import { useTheme } from '@/hooks/use-theme';

export default function TabLayout() {
  const theme = useTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.primary,
        tabBarInactiveTintColor: theme.textSecondary,
        tabBarStyle: { backgroundColor: theme.backgroundElement, borderTopColor: theme.border },
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
      }}>
      <Tabs.Screen
        name="index"
        options={{ title: '분석', tabBarIcon: ({ color }) => <Icon name="analyze" size={22} color={color} /> }}
      />
      <Tabs.Screen
        name="history"
        options={{ title: '이력', tabBarIcon: ({ color }) => <Icon name="history" size={22} color={color} /> }}
      />
      <Tabs.Screen
        name="about"
        options={{ title: 'About', tabBarIcon: ({ color }) => <Icon name="info" size={22} color={color} /> }}
      />
    </Tabs>
  );
}
