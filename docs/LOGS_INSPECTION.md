# Logs Inspection Report

> Discovery-отчёт по реальной папке логов 1С для архитектора Sprint 1.
> Сгенерирован скриптом [`backend/scripts/inspect_logs.py`](../backend/scripts/inspect_logs.py).

**Root:** `D:\1C-Optimyzer\1c-optimyzer\logs`
**Scanned at (UTC):** `2026-05-18T13:39:47.052875+00:00`

---

## 1. Структура папок (top-2 levels)

```
D:\1C-Optimyzer\1c-optimyzer\logs/
├── 1cv8_24120/
│   └── 26051813.log
├── 1cv8_24824/
│   ├── 26051813.log
│   ├── 26051814.log
│   └── 26051815.log
├── 1cv8_24908/
│   └── 26051813.log
├── 1CV8C_12044/
│   ├── 26051813.log
│   └── 26051814.log
├── 1CV8C_13780/
│   └── 26051814.log
├── 1CV8C_20976/
│   └── 26051814.log
├── 1CV8C_22176/
│   ├── 26051813.log
│   └── 26051814.log
├── 1cv8c_23100/
│   └── 26051813.log
├── 1CV8C_24392/
│   ├── 26051814.log
│   └── 26051815.log
├── 1CV8C_6016/
│   └── 26051814.log
├── 1cv8s_1688/
│   └── 26051813.log
├── 1cv8s_18212/
│   └── 26051813.log
├── 1cv8s_23080/
│   └── 26051813.log
├── 1cv8s_23288/
│   └── 26051813.log
├── ragent_28284/
│   ├── 26051813.log
│   ├── 26051814.log
│   └── 26051815.log
├── rmngr_24128/
│   ├── 26051813.log
│   ├── 26051814.log
│   └── 26051815.log
├── rphost_28220/
│   ├── 26051813.log
│   ├── 26051814.log
│   └── 26051815.log
├── rmngr_24128.zip
```

## 2. Patterns подпапок (первый уровень)

| Префикс | Кол-во | Примеры |
|---|---:|---|
| `1cv8c` | 7 | `1CV8C_12044`, `1CV8C_13780`, `1CV8C_20976`, `1CV8C_22176`, `1cv8c_23100` |
| `1cv8s` | 4 | `1cv8s_1688`, `1cv8s_18212`, `1cv8s_23080`, `1cv8s_23288` |
| `1cv8` | 3 | `1cv8_24120`, `1cv8_24824`, `1cv8_24908` |
| `ragent` | 1 | `ragent_28284` |
| `rmngr` | 1 | `rmngr_24128` |
| `rphost` | 1 | `rphost_28220` |

## 3. Patterns имён `.log` файлов

| Pattern | Кол-во | Примеры |
|---|---:|---|
| YYMMDDHH (8 digits) | 28 | `1CV8C_12044\26051813.log`<br>`1CV8C_12044\26051814.log`<br>`1CV8C_13780\26051814.log`<br>`1CV8C_20976\26051814.log`<br>`1CV8C_22176\26051813.log`<br>`1CV8C_22176\26051814.log`<br>`1cv8c_23100\26051813.log`<br>`1CV8C_24392\26051814.log` |

**Date range** (из имён YYMMDDHH): `2026-05-18T13:00:00` → `2026-05-18T15:00:00` (28 файлов с парсимыми именами).

## 4. Распределение размеров `.log` файлов

- **Files total:** 28
- **Total:** 12,824,049,954 bytes (12229.97 MiB) (11.94 GiB)
- **Min:** 71 bytes (0.00 MiB)
- **Max:** 10,987,064,972 bytes (10478.08 MiB)
- **Median:** 1,123,771 bytes (1.07 MiB)
- **Mean:** 458,001,784 bytes (436.78 MiB)

## 5. Sample первых строк (фактический формат TJ event)

### 5.1. `1cv8s_1688\26051813.log`
- **Size:** 71 bytes (0.00 MiB)
- **Encoding:** `utf-8-sig` _(detection: BOM utf-8 detected)_

```
48:59.728001-19046999,PROC,0,level=INFO,process=1cv8s,OSThread=840
```

### 5.2. `1cv8s_23288\26051813.log`
- **Size:** 72 bytes (0.00 MiB)
- **Encoding:** `utf-8-sig` _(detection: BOM utf-8 detected)_

```
49:11.901000-8546998,PROC,0,level=INFO,process=1cv8s,OSThread=29844
```

### 5.3. `1CV8C_24392\26051814.log`
- **Size:** 1,304,422 bytes (1.24 MiB)
- **Encoding:** `utf-8-sig` _(detection: BOM utf-8 detected)_

```
09:33.371001-1,LIC,1,level=INFO,process=1CV8C,OSThread=18076,Func=initialize,txt='local Application, hasp HL soft local, ORGL8 local net, ORG8A local net, ORG8B local net, Base local net'
09:33.371005-1,HASP,3,level=INFO,process=1CV8C,OSThread=18076,Txt='
LOCALHASP_HASPSTATUS(,,ser=ORGL8,,,,)->size=4,type=10,port=102,ApiVer=25684'
```

### 5.4. `1CV8C_6016\26051814.log`
- **Size:** 708,250 bytes (0.68 MiB)
- **Encoding:** `utf-8-sig` _(detection: BOM utf-8 detected)_

```
31:10.950001-1,LIC,1,level=INFO,process=1CV8C,OSThread=28776,Func=initialize,txt='local Application, hasp HL soft local, ORGL8 local net, ORG8A local net, ORG8B local net, Base local net'
31:10.950005-1,HASP,3,level=INFO,process=1CV8C,OSThread=28776,Txt='
LOCALHASP_HASPSTATUS(,,ser=ORGL8,,,,)->size=4,type=10,port=102,ApiVer=25684'
```

### 5.5. `rmngr_24128\26051813.log`
- **Size:** 50,387,349 bytes (48.05 MiB)
- **Encoding:** `utf-8-sig` _(detection: BOM utf-8 detected)_

```
47:02.139004-1,CALL,1,level=INFO,process=rmngr,OSThread=23464,t:clientID=1434,t:applicationName=AgentProcess,t:computerName=WIN,callWait=0,first=0,Interface=0459eaa0-589f-4a6d-9eed-c1a7461c8e3f,IName=IClusterRegistry,Method=29,CallID=151791,MName=getRegistryVersion,Memory=534752,MemoryPeak=534848,InBytes=0,OutBytes=0,CpuTime=0
47:02.139007-1,CALL,1,level=INFO,process=rmngr,OSThread=23464,t:clientID=1434,t:applicationName=AgentProcess,t:computerName=WIN,callWait=0,first=0,Interface=0459eaa0-589f-4a6d-9eed-c1a7461c8e3f,IName=IClusterRegistry,Method=83,CallID=151792,MName=getServiceDistribVersion,Memory=160,MemoryPeak=256,InBytes=0,OutBytes=0,CpuTime=0
47:02.139010-1,CALL,1,level=INFO,process=rmngr,OSThread=26776,t:clientID=1415,t:applicationName=Notification,t:computerName=WIN,callWait=0,first=0,Interface=64016dc5-c439-49fa-8a71-c3cb708e243b,IName=IClusterState,Method=37,CallID=151793,MName=getProcessesSetVersion,Memory=144,MemoryPeak=240,InBytes=0,OutBytes=0,CpuTime=0
```

## 6. Encoding по sample-файлам (сводка)

| Encoding | Кол-во sample-файлов |
|---|---:|
| `utf-8-sig` | 5 |

## 7. Не-`.log` файлы

| Extension | Count |
|---|---:|
| `.log` | 28 |
| `.zip` | 1 |

**Sample non-`.log` paths (до 20):**

- `rmngr_24128.zip`

---

## Recommendations для Sprint 1 (на основе фактов)

Архитектор Opus интерпретирует фактические данные выше и финализирует Sprint 1 promt.
Этот отчёт — input, не decision.

