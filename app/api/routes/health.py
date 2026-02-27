"""
서버 상태 확인 엔드포인트

Production 환경에서 필수적인 헬스체크 API입니다.
로드밸런서, 쿠버네티스 등에서 서버 상태를 확인할 때 사용합니다.

엔드포인트:
    GET /health/         - 기본 헬스체크
    GET /health/ready    - 준비 상태 확인 (DB 연결 등)
"""

import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import cast

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


def _get_version() -> str:
    try:
        return metadata.version("lumi-agent")
    except metadata.PackageNotFoundError:
        pass

    try:
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        data = cast(
            dict[str, object], tomllib.loads(pyproject.read_text(encoding="utf-8"))
        )
        project_value = data.get("project")
        if isinstance(project_value, Mapping):
            project = cast(Mapping[str, object], project_value)
            version_value = project.get("version")
            if isinstance(version_value, str):
                return version_value
        return "0.0.0"
    except Exception:
        return "0.0.0"


@router.get("/", summary="Application health check")
async def get_health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "lumi-agent",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "version": _get_version(),
    }


@router.get("/ready", summary="Readiness check")
async def get_readiness() -> dict[str, str]:
    return {
        "status": "ready",
        "service": "lumi-agent",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "version": _get_version(),
    }
