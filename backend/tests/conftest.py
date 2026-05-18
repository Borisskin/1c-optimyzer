"""Общие фикстуры для тестов парсера и storage."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _load_env_test() -> None:
    """Загружает .env.test из корня репо в os.environ (если файл есть).

    Без зависимости на python-dotenv. Простой KEY=VALUE формат, # комментарии.
    """
    repo_root = Path(__file__).resolve().parents[2]
    env_file = repo_root / ".env.test"
    if not env_file.is_file():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_test()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def synthetic_dbmssql_log() -> str:
    """Многострочное DBMSSQL событие + CALL событие, два разных типа подряд."""
    return (
        "32:14.402023-8124000,DBMSSQL,5,process=rphost,p:processName=erp,"
        "OSThread=12340,t:clientID=14,"
        "Sql='SELECT T1._Fld5640RRef, SUM(T1._Fld5642) FROM _AccumRgT5634 T1\n"
        "WHERE T1._Fld5612 = @P1\n"
        "GROUP BY T1._Fld5640RRef',"
        "Rows=234,RowsAffected=0,"
        "Context='Документ.РеализацияТоваровУслуг.Модуль.ОбработкаПроведения'\n"
        "32:14.501234-15000,CALL,3,process=rphost,p:processName=erp,"
        "OSThread=12340,t:clientID=14,Context='ОбщийМодуль.РасчётыСКонтрагентами'\n"
    )


@pytest.fixture
def synthetic_mixed_log() -> str:
    """CALL, DBMSSQL, EXCP, TLOCK, TDEADLOCK, плюс неизвестный тип."""
    return (
        "00:01.100000-2000,CALL,3,process=rphost,OSThread=1,t:clientID=10,Context='Test.Module'\n"
        "00:01.200000-5000,DBMSSQL,5,process=rphost,OSThread=1,Sql='SELECT 1',Rows=1\n"
        "00:01.300000-1000,EXCP,2,process=rphost,Exception='SystemError',Descr='Test'\n"
        "00:02.000000-100000,TLOCK,4,process=rphost,Granted='X',Wait=0,Regions='RegisterFoo'\n"
        "00:03.500000-500000,TDEADLOCK,4,process=rphost,DeadlockConnectionIntersections='14:18'\n"
        "00:04.000000-0,UNKNOWNFOO,1,key=value\n"
    )
