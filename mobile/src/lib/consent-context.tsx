import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { CONSENT_VERSION } from '@/constants/notices';

import { getConsent, postConsent } from './api';
import { getLocalConsent, setLocalConsent } from './device';

type ConsentContextValue = {
  consented: boolean;
  agree: () => Promise<void>;
  // 서버가 consent_required로 거절했을 때 동의 화면으로 되돌린다
  reset: () => void;
};

const ConsentContext = createContext<ConsentContextValue | null>(null);

function hasValidLocalConsent() {
  return getLocalConsent()?.version === CONSENT_VERSION;
}

export function ConsentProvider({ children }: { children: ReactNode }) {
  const [consented, setConsented] = useState(hasValidLocalConsent);

  // 로컬엔 동의가 있는데 서버 기록이 없으면(서버 DB 초기화 등) 다시 동의를 받는다.
  // 서버에 닿지 않으면 로컬 상태를 믿고 진행한다.
  useEffect(() => {
    if (!consented) return;
    getConsent()
      .then((res) => {
        if (!res.agreed || res.version !== CONSENT_VERSION) {
          setLocalConsent(null);
          setConsented(false);
        }
      })
      .catch(() => {});
    // 앱 시작 시 한 번만 확인
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const agree = useCallback(async () => {
    await postConsent(CONSENT_VERSION);
    setLocalConsent({ version: CONSENT_VERSION, agreedAt: new Date().toISOString() });
    setConsented(true);
  }, []);

  const reset = useCallback(() => {
    setLocalConsent(null);
    setConsented(false);
  }, []);

  const value = useMemo(() => ({ consented, agree, reset }), [consented, agree, reset]);
  return <ConsentContext.Provider value={value}>{children}</ConsentContext.Provider>;
}

export function useConsent() {
  const ctx = useContext(ConsentContext);
  if (!ctx) throw new Error('useConsent must be used within ConsentProvider');
  return ctx;
}
