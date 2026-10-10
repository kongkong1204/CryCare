"""SQLite 최소 저장 (스펙 §6). 녹음 wav 경로 + 분석 이력 + 피드백 라벨 + 케어 이벤트 + 동의.
모든 조회·수정·삭제는 device_id로 한정한다 (스펙 §5)."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# 배포 환경에서 바꿀 수 있게 환경변수로 받는다. 기본값은 저장소 루트
DB_PATH = Path(os.environ.get("CRYCARE_DB_PATH") or Path(__file__).resolve().parent.parent / "crycare.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id        TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    audio_path       TEXT NOT NULL,
    prediction       TEXT NOT NULL,
    probabilities    TEXT NOT NULL,
    context          TEXT NOT NULL,
    branch           TEXT NOT NULL,
    suggestion       TEXT,
    actual_label     TEXT,
    memo             TEXT,
    label_updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_records_device ON records (device_id, created_at);

CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id        TEXT NOT NULL,
    type             TEXT NOT NULL,
    occurred_at      TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'manual',
    source_record_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_events_device ON events (device_id, type, occurred_at);

CREATE TABLE IF NOT EXISTS consents (
    device_id TEXT PRIMARY KEY,
    agreed_at TEXT NOT NULL,
    version   TEXT NOT NULL
);

-- 서버 전체 하루 LLM 호출 횟수 (공개 URL 비용 상한). 기기 정보는 담지 않는다
CREATE TABLE IF NOT EXISTS llm_usage (
    day   TEXT PRIMARY KEY,
    count INTEGER NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(records)")}
        if cols and "device_id" not in cols:
            raise RuntimeError(
                f"{DB_PATH.name}가 v1 스키마입니다. 백업 후 삭제하면 v2 스키마로 새로 생성됩니다."
            )
        conn.executescript(SCHEMA)


# ---------- events ----------

def insert_event(
    device_id: str,
    event_type: str,
    occurred_at: str,
    source: str = "manual",
    source_record_id: int | None = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (device_id, type, occurred_at, source, source_record_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (device_id, event_type, occurred_at, source, source_record_id),
        )
        return cur.lastrowid


def latest_event(device_id: str, event_type: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT occurred_at FROM events WHERE device_id = ? AND type = ? "
            "ORDER BY occurred_at DESC LIMIT 1",
            (device_id, event_type),
        ).fetchone()
        return row["occurred_at"] if row else None


def list_events(device_id: str, limit: int = 20) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, type, occurred_at, source FROM events WHERE device_id = ? "
            "ORDER BY occurred_at DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()


def update_event(device_id: str, event_id: int, occurred_at: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE events SET occurred_at = ? WHERE id = ? AND device_id = ?",
            (occurred_at, event_id, device_id),
        )
        return cur.rowcount > 0


def delete_event(device_id: str, event_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM events WHERE id = ? AND device_id = ?", (event_id, device_id)
        )
        return cur.rowcount > 0


# ---------- records ----------

def insert_record(
    device_id: str,
    created_at: str,
    audio_path: str,
    prediction: str,
    probabilities_json: str,
    context_json: str,
    branch: str,
    suggestion: str | None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO records (device_id, created_at, audio_path, prediction,
                                   probabilities, context, branch, suggestion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (device_id, created_at, audio_path, prediction, probabilities_json,
             context_json, branch, suggestion),
        )
        return cur.lastrowid


def get_record(device_id: str, record_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM records WHERE id = ? AND device_id = ?", (record_id, device_id)
        ).fetchone()


def update_reason(device_id: str, record_id: int, branch: str, suggestion: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE records SET branch = ?, suggestion = ? WHERE id = ? AND device_id = ?",
            (branch, suggestion, record_id, device_id),
        )


def set_label(
    device_id: str,
    record_id: int,
    actual_label: str,
    memo: str | None,
    updated_at: str,
    event_type: str | None,
) -> bool:
    """라벨 입력·수정(덮어쓰기)과 자동 이벤트 정합을 한 트랜잭션으로 처리 (스펙 §6 FR11).
    이 기록에서 자동 생성된 이벤트를 먼저 지우고, 새 라벨이 매핑 대상이면 다시 만든다."""
    with get_conn() as conn:
        # memo가 None이면 기존 메모 유지 (라벨만 바꿀 때 메모가 지워지지 않게). ""로 지운다.
        cur = conn.execute(
            "UPDATE records SET actual_label = ?, memo = COALESCE(?, memo), label_updated_at = ? "
            "WHERE id = ? AND device_id = ?",
            (actual_label, memo, updated_at, record_id, device_id),
        )
        if cur.rowcount == 0:
            return False
        conn.execute(
            "DELETE FROM events WHERE device_id = ? AND source = 'feedback' AND source_record_id = ?",
            (device_id, record_id),
        )
        if event_type:
            conn.execute(
                "INSERT INTO events (device_id, type, occurred_at, source, source_record_id) "
                "VALUES (?, ?, ?, 'feedback', ?)",
                (device_id, event_type, updated_at, record_id),
            )
        return True


def recent_feedback(device_id: str, window: int = 5) -> list[sqlite3.Row]:
    """최근 window건 기록 중 피드백 라벨이 있는 것만 (스펙 §6 FR9)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT prediction, actual_label, created_at FROM ("
            "  SELECT * FROM records WHERE device_id = ? ORDER BY created_at DESC LIMIT ?"
            ") WHERE actual_label IS NOT NULL ORDER BY created_at DESC",
            (device_id, window),
        ).fetchall()


def count_records_since(device_id: str, since: str) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM records WHERE device_id = ? AND created_at >= ?", (device_id, since)
        ).fetchone()[0]


def list_history(device_id: str, limit: int = 20) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, created_at, prediction, branch, suggestion, actual_label "
            "FROM records WHERE device_id = ? ORDER BY created_at DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()


def list_audio_paths(device_id: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT audio_path FROM records WHERE device_id = ?", (device_id,)
        ).fetchall()
        return [row["audio_path"] for row in rows]


def delete_device_data(device_id: str) -> tuple[int, int]:
    with get_conn() as conn:
        records = conn.execute("DELETE FROM records WHERE device_id = ?", (device_id,)).rowcount
        events = conn.execute("DELETE FROM events WHERE device_id = ?", (device_id,)).rowcount
        return records, events


# ---------- consents ----------

def upsert_consent(device_id: str, agreed_at: str, version: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO consents (device_id, agreed_at, version) VALUES (?, ?, ?) "
            "ON CONFLICT(device_id) DO UPDATE SET agreed_at = excluded.agreed_at, "
            "version = excluded.version",
            (device_id, agreed_at, version),
        )


def get_consent(device_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT agreed_at, version FROM consents WHERE device_id = ?", (device_id,)
        ).fetchone()


def delete_consent(device_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM consents WHERE device_id = ?", (device_id,))


def inactive_devices(cutoff: str) -> list[str]:
    """마지막 이용(분석·이벤트·동의) 시각이 cutoff 이전인 기기 (스펙 §10.1 보관기간)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT device_id FROM ("
            "  SELECT device_id, created_at AS ts FROM records"
            "  UNION ALL SELECT device_id, occurred_at FROM events"
            "  UNION ALL SELECT device_id, agreed_at FROM consents"
            ") GROUP BY device_id HAVING MAX(ts) < ?",
            (cutoff,),
        ).fetchall()
        return [row["device_id"] for row in rows]


# ---------- LLM 호출 한도 ----------

def take_llm_quota(day: str, limit: int) -> bool:
    """오늘 호출 횟수가 한도 미만이면 1 올리고 True, 한도에 닿았으면 False."""
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO llm_usage (day, count) VALUES (?, 0)", (day,))
        return conn.execute(
            "UPDATE llm_usage SET count = count + 1 WHERE day = ? AND count < ?", (day, limit)
        ).rowcount == 1
