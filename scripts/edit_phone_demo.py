"""폰 화면 기록(tc2.mp4, 라이트 모드)을 시연 영상으로 편집한다.

- iOS는 앱이 마이크로 녹음하는 동안 화면 기록의 마이크를 막아 영상이 무음이 된다.
  촬영 마지막에 TC7(데이터 전체 삭제)로 앱 녹음 파일도 지워졌으므로, 맥 스피커로 재생한
  원본 울음 wav를 합성한다. 재생이 끝나면 바로 녹음을 정지했으므로 녹음 종료 시각에 맞춘다.
- 구간을 잘라 화면당 10초 이내로 줄인다(울음 녹음 장면은 자르지 않음). 자막은 넣지 않는다.
- 오래 보여줄 화면은 마지막 프레임을 멈춤 화면으로 늘린다.

사용: venv/bin/python scripts/edit_phone_demo.py [원본 mp4] [출력 mp4]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Downloads/tc2.mp4")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "evidence/video/phone_demo.mp4")
FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
DATA = Path.home() / "Downloads/BabyCry-C5_160"

# 녹음 구간 (영상에서 녹음 버튼이 빨간색인 구간, 초)과 그때 재생한 울음
RECORDINGS = [
    (16.2, 34.2, DATA / "hungry/hungry_0.wav"),
    (53.6, 72.6, DATA / "hungry/hungry_1.wav"),
    (141.0, 159.8, DATA / "hungry/hungry_1.wav"),
]
REACTION = 0.7  # "재생 끝"을 보고 정지를 누르기까지 걸린 시간(초)

# (원본 시작, 원본 끝, 장면 설명(편집 메모, 영상에는 표시하지 않음)[, 끝 프레임 멈춤 초])
SEGMENTS = [
    (2.0, 12.0, "FR14 최초 실행 동의\n고지 확인 후 보호자 동의"),
    (14.5, 34.2, "TC3 첫 사용자: 수유·기저귀·피드백 기록 없음\n울음 녹음 (데이터셋 샘플을 스피커로 재생)"),
    (34.2, 39.5, "녹음 종료 → 분석"),
    (39.5, 47.8, "TC3 결과: ●○○ 1단계 · 기록 부족 (B3)\n보수적 안내 + 기록 유도 → 실제 니즈 피드백"),
    (52.0, 72.6, "TC2 불확실 안내: 두 번째 녹음"),
    (72.6, 78.0, "녹음 종료 → 분석"),
    (78.5, 88.8, "TC2 결과: 1순위 확률 0.41 (0.5 미만)\n→ ●●○ 2단계 · 확실하지 않음 + 시도 순서"),
    (94.0, 101.0, "TC4 피드백 저장: \"배고픔\" 피드백 2건\n→ 수유 기록 자동 추가"),
    (115.0, 125.0, "TC4 피드백 수정: 실제 니즈를\n\"배고픔\" → \"안아달라\"로 덮어쓰기"),
    (133.8, 137.0, "TC4 정합 처리: 수정한 기록의\n자동 수유 기록 삭제 (2건 → 1건)"),
    (139.5, 159.8, "TC5 피드백 맥락 반영: 세 번째 녹음"),
    (159.8, 166.5, "녹음 종료 → 분석"),
    (166.5, 174.5, "결과: ●●○ 2단계 · 확실하지 않음"),
    (196.0, 203.0, "TC5: 분석 당시 기록에 최근 피드백 포함\n최근 피드백 2건 중 2건 불일치 → 제안 맥락에 반영", 5.0),
    (223.0, 233.0, "TC7 데이터 삭제: 내 데이터 전체 삭제\n→ 서버 기록·녹음 영구 삭제"),
]


def main() -> None:
    inputs = ["-i", str(SRC)]
    for _, _, wav in RECORDINGS:
        inputs += ["-i", str(wav)]

    n = len(SEGMENTS)
    graph = []
    # 재생한 울음을 "녹음 종료 - 반응 시간 - 울음 길이" 시각에 배치해 원본 길이의 오디오 트랙을 만든다
    for i, (_, rec_end, wav) in enumerate(RECORDINGS, 1):
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
            capture_output=True, text=True, check=True).stdout)
        start = rec_end - REACTION - dur
        graph.append(f"[{i}:a]adelay={int(start * 1000)}:all=1,aresample=44100,"
                     f"aformat=channel_layouts=stereo[r{i}]")
    graph.append("".join(f"[r{i}]" for i in range(1, len(RECORDINGS) + 1))
                 + f"amix=inputs={len(RECORDINGS)}:normalize=0,apad,asplit={n}"
                 + "".join(f"[a{k}]" for k in range(n)))
    graph.append(f"[0:v]split={n}" + "".join(f"[v{k}]" for k in range(n)))

    for k, (s, e, _note, *rest) in enumerate(SEGMENTS):
        freeze = rest[0] if rest else 0
        graph.append(
            f"[v{k}]trim={s}:{e},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={freeze},"
            f"scale=720:-2[sv{k}]")
        graph.append(f"[a{k}]atrim={s}:{e},asetpts=PTS-STARTPTS,apad=pad_dur={freeze}[sa{k}]")
    graph.append("".join(f"[sv{k}][sa{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(graph),
         "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-movflags", "faststart", str(OUT)],
        check=True)
    total = sum(e - s + (rest[0] if rest else 0) for s, e, _, *rest in SEGMENTS)
    print(f"{OUT} ({total:.1f}초, {n}개 구간)")


if __name__ == "__main__":
    main()
