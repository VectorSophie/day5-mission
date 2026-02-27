from collections.abc import AsyncGenerator, AsyncIterator
from importlib import import_module
from typing import Any, Literal, Protocol, cast
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from loguru import logger

from app.core.config import settings
from app.graph import get_lumi_graph
from app.schemas.chat import ChatRequest, ChatResponse, StreamEvent, Viseme

router = APIRouter()

Emotion = Literal["neutral", "happy", "sad", "angry"]
Phoneme = Literal["a", "i", "u", "e", "o"]

SESSION_STORE: dict[str, list[BaseMessage]] = {}
AUDIO_STORE: dict[str, tuple[bytes, str]] = {}


class _GraphRunner(Protocol):
    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]: ...

    def astream(
        self, state: dict[str, Any], stream_mode: list[str]
    ) -> AsyncIterator[tuple[str, Any]]: ...


def _normalize_emotion(
    value: str | None,
) -> Emotion:
    if value in {"neutral", "happy", "sad", "angry"}:
        return cast(Emotion, value)
    return "neutral"


def _generate_visemes(text: str) -> list[Viseme]:
    visemes: list[Viseme] = []
    t = 0.0
    step = 0.11
    for ch in text.lower():
        if ch in {"a", "i", "u", "e", "o"}:
            phoneme = cast(Phoneme, ch)
            visemes.append(
                Viseme(phoneme=phoneme, start=round(t, 3), end=round(t + step, 3))
            )
            t += step
        elif ch.isspace():
            t += 0.03
        else:
            t += 0.02
    return visemes


async def _maybe_synthesize_audio_url(text: str) -> str | None:
    provider = str(settings.tts_provider).strip().lower()
    audio: bytes | None = None

    if provider == "elevenlabs":
        audio = await _synthesize_elevenlabs_audio(text)
        if not audio:
            logger.warning("ElevenLabs failed, trying edge-tts fallback")
            audio = await _synthesize_edge_audio(text)
    elif provider == "edge":
        audio = await _synthesize_edge_audio(text)

    if not audio:
        return None

    audio_id = uuid4().hex
    AUDIO_STORE[audio_id] = (audio, "audio/mpeg")
    return f"/api/v1/chat/audio/{audio_id}"


async def _synthesize_edge_audio(text: str) -> bytes | None:
    try:
        edge_tts = import_module("edge_tts")
    except ImportError:
        logger.warning("edge-tts not installed; skip audio generation")
        return None

    try:
        communicate = edge_tts.Communicate(text=text, voice=settings.edge_tts_voice)
        audio = bytearray()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                audio.extend(chunk.get("data", b""))
        if not audio:
            return None
        return bytes(audio)
    except Exception as exc:
        logger.warning(f"edge-tts generation failed: {exc}")
        return None


async def _resolve_eleven_voice_id(client: httpx.AsyncClient) -> str | None:
    headers = {"xi-api-key": settings.eleven_api_key}
    response = await client.get("https://api.elevenlabs.io/v1/voices", headers=headers)
    response.raise_for_status()
    payload = response.json()
    voices = payload.get("voices", []) if isinstance(payload, dict) else []
    for item in voices:
        if not isinstance(item, dict):
            continue
        if item.get("name") == settings.eleven_voice_name:
            voice_id = item.get("voice_id")
            if isinstance(voice_id, str) and voice_id:
                return voice_id
    return None


async def _synthesize_elevenlabs_audio(text: str) -> bytes | None:
    if not settings.eleven_api_key:
        logger.warning("ELEVEN_API_KEY missing; skip ElevenLabs TTS")
        return None

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            voice_id = await _resolve_eleven_voice_id(client)
            if not voice_id:
                logger.warning(
                    f"ElevenLabs voice not found: {settings.eleven_voice_name}; skip TTS"
                )
                return None

            headers = {
                "xi-api-key": settings.eleven_api_key,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            }
            body = {
                "text": text,
                "model_id": settings.eleven_model_id,
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.8},
            }
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            return response.content if response.content else None
    except Exception as exc:
        logger.warning(f"ElevenLabs TTS generation failed: {exc}")
        return None


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str) -> Response:
    if audio_id not in AUDIO_STORE:
        raise HTTPException(status_code=404, detail="audio not found")
    payload, mime = AUDIO_STORE[audio_id]
    return Response(content=payload, media_type=mime)


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    logger.info(f"chat request: session={request.session_id}")
    try:
        graph = cast(_GraphRunner, cast(Any, get_lumi_graph()))
        history = SESSION_STORE.get(request.session_id, [])
        new_message = HumanMessage(content=request.message)
        initial_state = {
            "messages": history + [new_message],
            "intent": None,
            "retrieved_docs": [],
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
            "session_id": request.session_id,
            "user_id": request.user_id,
        }
        final_state = await graph.ainvoke(initial_state)
        messages = final_state["messages"]
        if len(messages) < 2:
            raise ValueError("no response message")

        text = str(messages[-1].content)
        SESSION_STORE.setdefault(request.session_id, []).extend(
            [new_message, AIMessage(content=text)]
        )
        visemes = _generate_visemes(text)
        audio_url = await _maybe_synthesize_audio_url(text)
        emotion = _normalize_emotion(final_state.get("emotion"))

        return ChatResponse(
            message=text,
            text=text,
            emotion=emotion,
            audio_url=audio_url,
            visemes=visemes,
            tool_used=final_state.get("tool_name"),
            cached=False,
        )
    except Exception as exc:
        logger.error(f"chat error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


async def stream_with_status(
    message: str,
    session_id: str,
    user_id: str | None = None,
) -> AsyncGenerator[
    tuple[
        str | None,
        str | None,
        str | None,
        str | None,
        Emotion,
        str | None,
        list[Viseme] | None,
    ],
    None,
]:
    graph = cast(_GraphRunner, cast(Any, get_lumi_graph()))
    session_id = session_id or "default"
    history = SESSION_STORE.get(session_id, [])
    new_message = HumanMessage(content=message)

    initial_state = {
        "messages": history + [new_message],
        "intent": None,
        "retrieved_docs": [],
        "tool_name": None,
        "tool_args": None,
        "tool_result": None,
        "session_id": session_id,
        "user_id": user_id,
    }

    final_response = ""
    final_tool_name = None
    final_emotion: Emotion = "neutral"
    current_node = None
    node_status = {
        "router": "🔀 루미 생각 중...",
        "rag": "📚 정보 검색 중...",
        "tool": "🔧 도구 실행 중...",
        "response": "💬 응답 작성 중...",
    }

    async for mode, event in graph.astream(
        initial_state, stream_mode=["updates", "messages"]
    ):
        if mode == "updates":
            for node_name, node_output in event.items():
                if node_name != current_node and node_name in node_status:
                    current_node = node_name
                    yield (
                        node_status[node_name],
                        None,
                        None,
                        None,
                        final_emotion,
                        None,
                        None,
                    )
                if node_name == "tool" and node_output:
                    final_tool_name = node_output.get("tool_name")
                if isinstance(node_output, dict):
                    final_emotion = _normalize_emotion(node_output.get("emotion"))

        elif mode == "messages":
            msg, meta = event
            node_name = meta.get("langgraph_node", "") if isinstance(meta, dict) else ""
            if node_name != "response":
                continue
            if isinstance(msg, AIMessageChunk):
                chunk_content = msg.content
                token = chunk_content if isinstance(chunk_content, str) else ""
                if token:
                    final_response += token
                    yield (None, token, None, None, final_emotion, None, None)

    if final_response:
        SESSION_STORE.setdefault(session_id, []).extend(
            [new_message, AIMessage(content=final_response)]
        )

    visemes = _generate_visemes(final_response) if final_response else []
    audio_url = (
        await _maybe_synthesize_audio_url(final_response) if final_response else None
    )
    yield (
        None,
        None,
        final_response,
        final_tool_name,
        final_emotion,
        audio_url,
        visemes,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for (
                status,
                token,
                final,
                tool_used,
                emotion,
                audio_url,
                visemes,
            ) in stream_with_status(
                request.message,
                request.session_id,
                request.user_id,
            ):
                if status:
                    yield StreamEvent(type="thinking", content=status).to_sse()
                if token:
                    yield StreamEvent(type="token", content=token).to_sse()
                if final:
                    yield StreamEvent(
                        type="response",
                        content=final,
                        text=final,
                        emotion=emotion,
                        tool_used=tool_used,
                        audio_url=audio_url,
                        visemes=visemes,
                    ).to_sse()
            yield StreamEvent(type="done").to_sse()
        except Exception as exc:
            logger.error(f"stream error: {exc}")
            yield StreamEvent(type="error", error=str(exc)).to_sse()
            yield StreamEvent(type="done").to_sse()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
