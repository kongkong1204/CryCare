// 기본값은 Cloud Run 서울 배포 서버 (스펙 §4). 로컬 백엔드·ngrok으로 개발할 땐 .env의 EXPO_PUBLIC_API_URL로 덮어쓴다.
// APK(EAS 빌드)는 .env를 못 읽으므로 eas.json 프로필의 env 또는 이 기본값을 쓴다.
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? 'https://crycare-api-631565758538.asia-northeast3.run.app';
