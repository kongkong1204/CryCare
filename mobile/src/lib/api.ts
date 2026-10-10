import { File } from 'expo-file-system';

import { API_BASE_URL } from './config';
import { getDeviceId } from './device';

export const CLASSES = ['awake', 'hug', 'hungry', 'sleepy', 'uncomfortable'] as const;
export type CryClass = (typeof CLASSES)[number];

export const CLASS_LABELS_KO: Record<CryClass, string> = {
  awake: '깨어있음',
  hug: '안아달라',
  hungry: '배고픔',
  sleepy: '졸림',
  uncomfortable: '불편함',
};

export type Probability = { label: CryClass; prob: number };

// B1 확신 / B2 불확실 / B3 첫 사용 / B4 제안 생성 실패 (스펙 §3.1)
export type Branch = 'B1' | 'B2' | 'B3' | 'B4';

// 서버가 계산한 맥락. 문자열 항목은 표시용, facts는 서버 분기 판정용
export type AnalysisContext = {
  '마지막 수유': string;
  '마지막 기저귀': string;
  '최근 피드백': string;
  facts: unknown;
};

export type PredictResponse = {
  record_id: number;
  prediction: CryClass;
  probabilities: Probability[];
  context: AnalysisContext;
  branch: Branch;
  suggestion: string | null;
  reason_error: string | null;
  // 최근 30분 안에 3번 이상 분석함 → 오래 우는 상황 안내 (스펙 §10.2)
  prolonged_crying?: boolean;
};

export type HistoryItem = {
  id: number;
  created_at: string;
  prediction: CryClass;
  branch: Branch;
  suggestion: string | null;
  actual_label: CryClass | null;
};

// 서버에 동의 기록이 없을 때(403 consent_required) - 동의 화면으로 돌려보낸다
export class ConsentRequiredError extends Error {
  constructor() {
    super('서비스 이용 동의가 필요해요.');
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('X-Device-Id', getDeviceId());
  // ngrok 무료 플랜이 끼워 넣는 경고 페이지(HTML)를 건너뛴다. 로컬 서버에는 영향 없음
  headers.set('ngrok-skip-browser-warning', '1');
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    if (res.status === 403 && body.includes('consent_required')) throw new ConsentRequiredError();
    throw new Error(`${path} 요청 실패 (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

export function getConsent(): Promise<{ agreed: boolean; version?: string; agreed_at?: string }> {
  return request('/consent');
}

export function postConsent(version: string): Promise<{ ok: true }> {
  return request('/consent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version }),
  });
}

export function getContext(): Promise<AnalysisContext> {
  return request('/context');
}

export function createEvent(type: CareEventType, occurredAt?: Date): Promise<{ id: number }> {
  return request('/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, occurred_at: occurredAt?.toISOString() }),
  });
}

export async function predict(fileUri: string): Promise<PredictResponse> {
  // SDK 57의 fetch는 WinterCG 표준을 따라서 RN 전통 방식({uri,name,type})을
  // 받아들이지 않는다. Blob을 구현하는 expo-file-system File을 대신 붙인다.
  const file = new File(fileUri);
  const form = new FormData();
  form.append('file', file, file.name);

  return request('/predict', { method: 'POST', body: form });
}

export function retryReason(
  recordId: number
): Promise<{ suggestion: string | null; branch: Branch; reason_error: string | null }> {
  return request(`/records/${recordId}/reason`, { method: 'POST' });
}

// memo를 생략하면 서버에 저장된 메모를 유지한다
export function labelRecord(recordId: number, actualLabel: CryClass, memo?: string): Promise<{ ok: true }> {
  return request(`/records/${recordId}/label`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actual_label: actualLabel, memo }),
  });
}

export function getHistory(limit = 20): Promise<HistoryItem[]> {
  return request(`/history?limit=${limit}`);
}

export function deleteAllData(): Promise<{ deleted_records: number; deleted_events: number }> {
  return request('/data', { method: 'DELETE' });
}

export type RecordDetail = {
  id: number;
  created_at: string;
  prediction: CryClass;
  probabilities: Probability[];
  context: AnalysisContext;
  branch: Branch;
  suggestion: string | null;
  actual_label: CryClass | null;
  memo: string | null;
  label_updated_at: string | null;
};

export function getRecord(recordId: number): Promise<RecordDetail> {
  return request(`/records/${recordId}`);
}

export type CareEventType = 'feeding' | 'diaper';

export const EVENT_LABELS_KO: Record<CareEventType, string> = {
  feeding: '수유',
  diaper: '기저귀',
};

export type CareEvent = {
  id: number;
  type: CareEventType;
  occurred_at: string;
  // manual: 직접 기록, feedback: "실제 니즈=배고픔" 피드백으로 자동 기록
  source: 'manual' | 'feedback';
};

export function getEvents(limit = 30): Promise<CareEvent[]> {
  return request(`/events?limit=${limit}`);
}

export function updateEventTime(eventId: number, occurredAt: Date): Promise<{ ok: true }> {
  return request(`/events/${eventId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occurred_at: occurredAt.toISOString() }),
  });
}

export function deleteEvent(eventId: number): Promise<{ ok: true }> {
  return request(`/events/${eventId}`, { method: 'DELETE' });
}
