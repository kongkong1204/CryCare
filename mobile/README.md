# CryCare 앱 (React Native · Expo)

CryCare의 Android/iOS 앱입니다. 프로젝트 소개, 실행 방법, APK 설치 방법은 [저장소 루트 README](../README.md)를 보세요.

```bash
npm install
cp .env.example .env      # 로컬 백엔드로 개발할 때만. 없으면 배포 서버(Cloud Run 서울)를 씁니다
npx expo start
npx eas-cli@latest build -p android --profile preview   # APK 빌드
```
