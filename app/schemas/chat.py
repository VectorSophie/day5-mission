from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="사용자 메시지"
    )
    session_id: str = Field(
        ..., min_length=1, max_length=100, description="세션 식별자"
    )
    user_id: str | None = Field(
        default=None, max_length=100, description="사용자 식별자"
    )


class Viseme(BaseModel):
    phoneme: Literal["a", "i", "u", "e", "o"]
    start: float = Field(ge=0)
    end: float = Field(ge=0)


class ChatResponse(BaseModel):
    message: str = Field(..., description="루미의 응답 메시지 (legacy)")
    text: str = Field(..., description="루미의 응답 메시지")
    emotion: Literal["neutral", "happy", "sad", "angry"] = Field(
        default="neutral", description="응답 감정 상태"
    )
    audio_url: str | None = Field(default=None, description="생성된 TTS 오디오 URL")
    visemes: list[Viseme] = Field(
        default_factory=list, description="립싱크 음소 타임라인"
    )
    tool_used: str | None = Field(default=None, description="사용된 Tool 이름")
    cached: bool = Field(default=False, description="캐시된 응답 여부")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="응답 생성 시간 (UTC)"
    )


StreamEventType = Literal["thinking", "tool", "token", "response", "error", "done"]


class StreamEvent(BaseModel):
    type: StreamEventType = Field(..., description="이벤트 타입")
    node: str | None = Field(default=None, description="현재 실행 중인 노드")
    content: str | None = Field(default=None, description="텍스트 내용")
    tool_name: str | None = Field(default=None, description="실행된 Tool 이름")
    tool_result: Any | None = Field(default=None, description="Tool 실행 결과")
    tool_used: str | None = Field(default=None, description="최종 응답에서 사용된 Tool")
    text: str | None = Field(default=None, description="최종 응답 텍스트")
    emotion: Literal["neutral", "happy", "sad", "angry"] | None = Field(
        default=None, description="응답 감정 상태"
    )
    audio_url: str | None = Field(default=None, description="TTS 오디오 URL")
    visemes: list[Viseme] | None = Field(default=None, description="립싱크 음소 데이터")
    error: str | None = Field(default=None, description="에러 메시지")

    def to_sse(self) -> str:
        import orjson

        payload = self.model_dump(exclude_none=True)
        return f"data: {orjson.dumps(payload).decode('utf-8')}\n\n"
