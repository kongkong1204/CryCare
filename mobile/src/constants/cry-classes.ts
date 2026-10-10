import type { IconName } from '@/components/ui/icon';
import type { CryClass } from '@/lib/api';

// 5클래스 표시 정보. 색은 라이트·다크 모두에서 읽히는 중간 채도
export const CLASS_META: Record<CryClass, { icon: IconName; color: string; hint: string }> = {
  awake: { icon: 'awake', color: '#E39B2D', hint: '깨어서 놀거나 자극을 원해요' },
  hug: { icon: 'hug', color: '#E0607E', hint: '안아주길 원해요' },
  hungry: { icon: 'hungry', color: '#EA7440', hint: '배가 고파요' },
  sleepy: { icon: 'sleepy', color: '#7A6CEB', hint: '졸려요' },
  uncomfortable: { icon: 'uncomfortable', color: '#24A096', hint: '어딘가 불편해요' },
};

