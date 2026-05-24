"""Integration test — реальный bsl-LS sidecar.

ПРОПУСКАЕТСЯ автоматически если binaries не установлены — для CI без бинарников.

Запуск локально: `pytest backend/tests/bsl_ls/test_integration.py -v -s`
после `scripts\setup-bsl-ls-binaries.ps1`.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest
import pytest_asyncio

from optimyzer_backend.bsl_ls import (
    AnalyzeRequest,
    BslLsClient,
    get_client,
    shutdown_client,
)
from optimyzer_backend.bsl_ls.lifecycle import BslLsBinariesNotFoundError, get_paths


# Гейт: skip всю модулю если бинарники не установлены.
def _binaries_available() -> bool:
    try:
        paths = get_paths()
        paths.validate()
        return True
    except BslLsBinariesNotFoundError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _binaries_available(),
        reason="bsl-LS binaries not installed (run scripts/setup-bsl-ls-binaries.ps1)",
    ),
]


@pytest_asyncio.fixture(scope="module")
async def client() -> AsyncIterator[BslLsClient]:
    """Один BslLsClient на всю модулю — экономим cold-start ~10s.

    Требует pyproject.toml `asyncio_default_test_loop_scope = "module"` чтобы
    fixture и тесты делили один event loop (иначе reader_task ставит Event
    в одном loop, ждётся в другом).
    """
    c = await get_client()
    yield c
    await shutdown_client()


@pytest.mark.asyncio
async def test_client_is_alive(client: BslLsClient) -> None:
    assert await client.is_alive()


@pytest.mark.asyncio
async def test_analyze_simple_query_no_diagnostics(client: BslLsClient) -> None:
    """Простой корректный запрос без проблем — ожидаем 0 diagnostics."""
    sdbl = "ВЫБРАТЬ Ссылка КАК Ссылка ИЗ Справочник.Контрагенты"
    result = await client.analyze_sdbl(AnalyzeRequest(query_sdbl=sdbl))
    # Может быть warnings про AssignAlias и т.п., но не должно быть Blocker/Critical.
    blocker_critical = [
        d for d in result.diagnostics if d.severity.value in {"Blocker", "Critical"}
    ]
    assert not blocker_critical, (
        f"Не ожидали Blocker/Critical на простом запросе, получили: {blocker_critical}"
    )


@pytest.mark.asyncio
async def test_analyze_ref_overuse(client: BslLsClient) -> None:
    """RefOveruse: Док.Ссылка.Контрагент.Ссылка.Наименование."""
    sdbl = (
        "ВЫБРАТЬ Док.Ссылка.Контрагент.Ссылка.Наименование "
        "ИЗ Документ.ПродажаТоваров КАК Док"
    )
    result = await client.analyze_sdbl(AnalyzeRequest(query_sdbl=sdbl))
    codes = {d.code for d in result.diagnostics}
    assert "RefOveruse" in codes or "QueryNestedFieldsByDot" in codes, (
        f"Ожидали RefOveruse, получили {codes}"
    )


@pytest.mark.asyncio
async def test_analyze_join_with_subquery(client: BslLsClient) -> None:
    sdbl = (
        "ВЫБРАТЬ Т1.Ссылка КАК Ссылка ИЗ Справочник.Контрагенты КАК Т1 "
        "ЛЕВОЕ СОЕДИНЕНИЕ (ВЫБРАТЬ Ссылка КАК Ссылка ИЗ Документ.ПриходТовара) КАК Т2 "
        "ПО Т1.Ссылка = Т2.Ссылка"
    )
    result = await client.analyze_sdbl(AnalyzeRequest(query_sdbl=sdbl))
    codes = {d.code for d in result.diagnostics}
    assert "JoinWithSubQuery" in codes, f"Ожидали JoinWithSubQuery, получили {codes}"


@pytest.mark.asyncio
async def test_analyze_virtual_table_no_params(client: BslLsClient) -> None:
    sdbl = "ВЫБРАТЬ * ИЗ РегистрНакопления.ТоварыНаСкладах.Остатки()"
    result = await client.analyze_sdbl(AnalyzeRequest(query_sdbl=sdbl))
    codes = {d.code for d in result.diagnostics}
    assert "VirtualTableCallWithoutParameters" in codes, (
        f"Ожидали VirtualTableCallWithoutParameters, получили {codes}"
    )


@pytest.mark.asyncio
async def test_analyze_result_has_grouped(client: BslLsClient) -> None:
    sdbl = "ВЫБРАТЬ Док.Ссылка.Контрагент.Ссылка.Наименование ИЗ Документ.ПродажаТоваров КАК Док"
    result = await client.analyze_sdbl(AnalyzeRequest(query_sdbl=sdbl))
    # grouped <= diagnostics (дедупликация overlap'ов)
    assert len(result.grouped) <= len(result.diagnostics)
    assert result.analysis_duration_ms > 0


@pytest.mark.asyncio
async def test_analyze_duration_under_3_sec_after_warmup(client: BslLsClient) -> None:
    """После warmup анализ простого запроса должен быть быстрым."""
    # Прогрев.
    await client.analyze_sdbl(
        AnalyzeRequest(query_sdbl="ВЫБРАТЬ 1 КАК Один")
    )
    # Реальный замер.
    result = await client.analyze_sdbl(
        AnalyzeRequest(query_sdbl="ВЫБРАТЬ Ссылка КАК Ссылка ИЗ Справочник.Контрагенты")
    )
    assert result.analysis_duration_ms < 3000, (
        f"Анализ занял {result.analysis_duration_ms}ms — медленнее 3s"
    )
