import { randomUUID } from 'expo-crypto';
import { File, Paths } from 'expo-file-system';

// 기기 식별자(UUID)와 동의 상태를 앱 문서 폴더에 저장한다 (스펙 §5, §8-0).
// 앱을 삭제하면 이 파일도 함께 지워진다 (스펙 §10.1).

export type LocalConsent = { version: string; agreedAt: string };

type DeviceState = { deviceId: string; consent: LocalConsent | null };

const stateFile = new File(Paths.document, 'crycare-device.json');

let cached: DeviceState | null = null;

function save(state: DeviceState) {
  if (!stateFile.exists) stateFile.create();
  stateFile.write(JSON.stringify(state));
  cached = state;
}

function load(): DeviceState {
  if (cached) return cached;
  if (stateFile.exists) {
    try {
      const parsed = JSON.parse(stateFile.textSync()) as DeviceState;
      if (parsed.deviceId) {
        cached = parsed;
        return parsed;
      }
    } catch {
      // 파일이 깨졌으면 새로 만든다
    }
  }
  const fresh: DeviceState = { deviceId: randomUUID(), consent: null };
  save(fresh);
  return fresh;
}

export function getDeviceId(): string {
  return load().deviceId;
}

export function getLocalConsent(): LocalConsent | null {
  return load().consent;
}

export function setLocalConsent(consent: LocalConsent | null) {
  save({ ...load(), consent });
}

// 데이터 전체 삭제(동의 철회) 후에는 새 기기 식별자로 처음부터 시작한다
export function resetDevice() {
  save({ deviceId: randomUUID(), consent: null });
}
