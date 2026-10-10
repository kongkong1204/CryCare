import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

import type { PredictResponse } from './api';

type ResultContextValue = {
  result: PredictResponse | null;
  setResult: (result: PredictResponse | null) => void;
};

const ResultContext = createContext<ResultContextValue | null>(null);

export function ResultProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<PredictResponse | null>(null);
  const value = useMemo(() => ({ result, setResult }), [result]);
  return <ResultContext.Provider value={value}>{children}</ResultContext.Provider>;
}

export function useResult() {
  const ctx = useContext(ResultContext);
  if (!ctx) throw new Error('useResult must be used within ResultProvider');
  return ctx;
}
