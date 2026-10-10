// 동의 화면·About·결과 하단에서 함께 쓰는 고지 문구 (스펙 §10).
// 문구를 바꾸면 CONSENT_VERSION도 올려서 기존 사용자에게 다시 동의를 받는다.

export const CONSENT_VERSION = 'v4';

// 스펙 §10.1 보관기간 (2026-10-02 확정). 서버가 시작할 때 기간이 지난 기기 데이터를 파기한다
export const RETENTION_PERIOD = '마지막 이용일로부터 1년';

export const DISCLAIMER =
  'CryCare는 육아를 돕는 참고용 도구이며 의료기기가 아닙니다. 질병의 진단·치료·예방 목적으로 사용할 수 없습니다.';

export const WARNING_SIGNS_INTRO = '다음과 같은 경우 앱 결과와 관계없이 즉시 의료기관 진료를 받으세요 (응급 시 119).';

export const WARNING_SIGNS = [
  '평소와 다르게 오래 달래지지 않는 울음',
  '발열 (특히 생후 3개월 미만 38℃ 이상)',
  '처지거나 깨우기 어려움',
  '호흡 곤란, 입술이 파래짐',
  '반복되는 구토',
  '수유 거부',
];

export const RESULT_FOOTER = '육아 보조용 참고 정보입니다. 이상 징후 시 의료기관에 문의하세요.';

export const PRIVACY_ITEMS: { label: string; value: string }[] = [
  {
    label: '수집 항목',
    value: '울음 녹음 파일, 분석 결과, 수유·기저귀 기록 시각, 피드백(실제 니즈), 기기 식별자(무작위 UUID). 이름·연락처는 수집하지 않습니다.',
  },
  { label: '이용 목적', value: '울음 분석 및 대응 제안 제공, 서비스 개선(향후 모델 재학습).' },
  { label: '보관 기간', value: `${RETENTION_PERIOD}. 기간이 지나거나 삭제를 요청하면 5일 이내 복구할 수 없게 파기합니다.` },
  {
    label: '외부 전송',
    value:
      '대응 제안 문장을 만들기 위해 분석 결과(울음 종류별 확률), 수유·기저귀 경과시간, 최근 피드백 요약을 Anthropic(미국)의 AI API로 전송합니다. 녹음 파일과 기기 식별자는 전송하지 않습니다.',
  },
  {
    label: '처리 위탁',
    value:
      '서버 운영을 위해 녹음, 분석 결과, 수유·기저귀 기록, 피드백을 Google Cloud(서울 리전)의 서버에 보관합니다. 수탁자: Google / 위탁 업무: 서버 운영 및 데이터 보관.',
  },
  {
    label: '동의 거부 권리',
    value: '동의를 거부할 권리가 있으며, 거부 시 서비스 이용이 제한됩니다.',
  },
  {
    label: '삭제 방법',
    value: 'About 탭의 "내 데이터 전체 삭제"로 서버의 녹음·기록이 즉시 삭제됩니다. 앱을 지우기 전에 먼저 이 버튼으로 삭제해주세요.',
  },
];

export const GUARDIAN_NOTICE =
  '아기(만 14세 미만)의 정보이므로 보호자(법정대리인)인 사용자의 동의가 필요합니다 (개인정보 보호법 제22조의2).';

// 같은 기기에서 짧은 시간에 여러 번 분석했을 때 결과 화면에 띄우는 안내 (서버 prolonged_crying)
export const PROLONGED_CRYING_NOTICE =
  '짧은 시간에 여러 번 분석했어요. 평소와 다르게 오래 달래지지 않는다면 앱 결과와 관계없이 의료기관에 문의하세요 (응급 시 119).';
