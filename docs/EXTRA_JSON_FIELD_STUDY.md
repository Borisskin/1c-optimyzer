# Extra JSON Field Study — реальный архив (Sprint 3 Phase 0)

> **Источник:** `C:\Users\User\AppData\Roaming\1c-optimyzer\duckdb\99cabbc238fd46e2a0343a8548d9f253.duckdb`  
> **Размер БД:** 548.5 MB  
> **Дата:** 2026-05-19 06:21  
> **Sample size per type:** до 50,000 events  

Этот документ — fact-based input для Sprint 3 Phase C (Document Anatomy) и Phase D 
(Deadlock Anatomy). Все поля и их частоты получены из реального production-архива 
Сергея, не гипотетически.

## 1. Распределение событий по event_type

| event_type | count | % |
|---|---:|---:|
| `CALL` | 438,868 | 40.23% |
| `Context` | 302,137 | 27.69% |
| `SRVC` | 214,548 | 19.67% |
| `SCALL` | 93,489 | 8.57% |
| `CONN` | 14,530 | 1.33% |
| `VRSREQUEST` | 6,479 | 0.59% |
| `VRSRESPONSE` | 6,175 | 0.57% |
| `SESN` | 5,470 | 0.50% |
| `VRSCACHE` | 3,078 | 0.28% |
| `ATTN` | 2,918 | 0.27% |
| `CLSTR` | 1,985 | 0.18% |
| `EXCPCNTX` | 450 | 0.04% |
| `EXCP` | 299 | 0.03% |
| `HASP` | 262 | 0.02% |
| `TLOCK` | 142 | 0.01% |
| `SCOM` | 110 | 0.01% |
| `LIC` | 28 | 0.00% |
| `PROC` | 21 | 0.00% |
| `SYSTEM` | 6 | 0.00% |
| **TOTAL** | **1,090,995** | **100%** |

## 2. Поля `extra` JSON по типу события

Колонки таблицы:
- **field** — ключ внутри `extra` JSON
- **freq** — в скольких % sampled events этот ключ присутствует
- **types** — какие Python-типы значений встречаются
- **examples** — 1-3 примера значений (обрезано до 200 символов)

### `CALL` — sampled 50,000 events, 17 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×50000 | `INFO`<br>`ERROR` |
| `OSThread` | 100.0% | str×50000 | `22612`<br>`6020`<br>`14452` |
| `callWait` | 100.0% | str×50000 | `93`<br>`0`<br>`15` |
| `first` | 100.0% | str×50000 | `1`<br>`0` |
| `Method` | 100.0% | str×50000 | `0`<br>`methodsCount`<br>`Release` |
| `CallID` | 100.0% | str×50000 | `30086`<br>`30090`<br>`30091` |
| `Memory` | 100.0% | str×50000 | `195184`<br>`185320`<br>`1054496` |
| `MemoryPeak` | 100.0% | str×50000 | `196720`<br>`185416`<br>`1054592` |
| `InBytes` | 100.0% | str×50000 | `0`<br>`390`<br>`201` |
| `OutBytes` | 100.0% | str×50000 | `0`<br>`1557`<br>`103` |
| `CpuTime` | 100.0% | str×50000 | `0`<br>`46875`<br>`15625` |
| `t:applicationName` | 99.6% | str×49783 | `Debugger`<br>`ServerProcess`<br>`AgentProcess` |
| `t:computerName` | 98.8% | str×49377 | `WIN` |
| `Interface` | 98.5% | str×49254 | `7f58f27d-5ad8-43a1-aa1e-c982f41bed5c`<br>`6068d073-39aa-4cd0-8ca8-95bd6dac3f15`<br>`5cf29e71-ec34-4f01-b7d1-3529a3da6a21` |
| `IName` | 98.5% | str×49254 | `IRemoteCreatorService`<br>`IDebugDataTarget`<br>`IDebugConnection` |
| `MName` | 98.5% | str×49254 | `createRemoteInstance`<br>`getTargetsInfo`<br>`debugAuthenticate` |
| `RetExcp` | 0.0% | str×4 | `97503acb-074d-4af7-9d89-f101713b6474`<br>`Первичный вызов сервиса пришел в пассивный сервис.`<br>`Сеанс отсутствует или удален ID=ead15a46-ad03-4b1b-b0f5-373b63b193d8, File=src\\rserver\\src\\IRMngrSrvcImpl.cpp(639)` |

### `Context` — sampled 50,000 events, 4 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×50000 | `INFO` |
| `OSThread` | 100.0% | str×50000 | `11640`<br>`29984`<br>`20944` |
| `t:applicationName` | 100.0% | str×50000 | `Debugger`<br>`ServerProcess` |
| `t:computerName` | 100.0% | str×50000 | `WIN` |

### `SRVC` — sampled 50,000 events, 5 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×50000 | `INFO` |
| `OSThread` | 100.0% | str×50000 | `29960`<br>`10432`<br>`30604` |
| `t:applicationName` | 100.0% | str×50000 | `ServerProcess` |
| `t:computerName` | 100.0% | str×50000 | `WIN` |
| `Descr` | 100.0% | str×50000 | `EventLogService: service notified,onCommitTransaction(infoBaseID=cb84bf9f-e01d-43ef-85ff-0b8d65925c77, connectID=85, seanceID=4dcb123a-e2a6-4f1a-916a-c72f3d72f9aa)`<br>`DbCopiesService: service notified,onCommitTransaction(infoBaseID=cb84bf9f-e01d-43ef-85ff-0b8d65925c77, connectID=85, seanceID=4dcb123a-e2a6-4f1a-916a-c72f3d72f9aa)`<br>`TimestampService: service notified,onCommitTransaction(infoBaseID=cb84bf9f-e01d-43ef-85ff-0b8d65925c77, connectID=85, seanceID=4dcb123a-e2a6-4f1a-916a-c72f3d72f9aa)` |

### `SCALL` — sampled 50,000 events, 11 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×50000 | `INFO` |
| `OSThread` | 100.0% | str×50000 | `5956`<br>`1428`<br>`17164` |
| `ClientID` | 100.0% | str×50000 | `1`<br>`2`<br>`3` |
| `CallID` | 100.0% | str×50000 | `12772`<br>`12773`<br>`12774` |
| `MName` | 100.0% | str×50000 | `createRemoteInstance`<br>`methodsCount`<br>`selectProcess` |
| `DstClientID` | 100.0% | str×50000 | `0`<br>`1550`<br>`850` |
| `Interface` | 98.3% | str×49162 | `7f58f27d-5ad8-43a1-aa1e-c982f41bed5c`<br>`73b7d3a3-fe0b-4fdf-ba70-b74b3589ffc3`<br>`bc15bd01-10bf-413c-a856-ddc907fcd123` |
| `IName` | 98.3% | str×49162 | `IRemoteCreatorService`<br>`ISelectSrvrProcess`<br>`IVResourceRemoteConnection` |
| `Method` | 97.4% | str×48685 | `0`<br>`1`<br>`43` |
| `t:applicationName` | 0.0% | str×17 | `Debugger` |
| `t:computerName` | 0.0% | str×17 | `WIN` |

### `CONN` — sampled 14,530 events, 10 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×14530 | `INFO` |
| `OSThread` | 99.7% | str×14485 | `5956`<br>`30708`<br>`10932` |
| `Txt` | 86.3% | str×12538 | `addrBelongsToThisComputer2, address=WIN, result=true`<br>`Connected, client=(23)[fe80::dc18:7c08:fb24:b7d8%27]:10316, server=(23)[fe80::dc18:7c08:fb24:b7d8%27]:2541, marker=1`<br>`Ping direction opened: address=[fe80::dc18:7c08:fb24:b7d8%27]:2541,current pingTimeout=15000,current pingPeriod=3000,lastSentTs=1290209084,lastReceivedTs=1290209084,lastReceivedTestTs=,directionID=cd2…` |
| `ClientID` | 29.8% | str×4329 | `1`<br>`2`<br>`3` |
| `t:applicationName` | 14.6% | str×2116 | `Debugger`<br>`AgentProcess`<br>`ServerProcess` |
| `Protected` | 10.7% | str×1551 | `0` |
| `t:computerName` | 8.0% | str×1168 | `WIN` |
| `t:connectID` | 6.9% | str×1003 | `0` |
| `Calls` | 6.9% | str×1003 | `6`<br>`13`<br>`2187` |
| `Descr` | 6.8% | str×989 | `server_addr=(2)127.0.0.1:8140 descr=recv returns zero, disconnected line=2282 file=src\\rtrsrvc\\src\\DataExchangeServerImpl.cpp`<br>`server_addr=(2)127.0.0.1:8170 descr=recv returns zero, disconnected line=2282 file=src\\rtrsrvc\\src\\DataExchangeServerImpl.cpp`<br>`server_addr=(2)127.0.0.1:8199 descr=recv returns zero, disconnected line=2282 file=src\\rtrsrvc\\src\\DataExchangeServerImpl.cpp` |

### `VRSREQUEST` — sampled 6,479 events, 9 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×6479 | `INFO` |
| `OSThread` | 100.0% | str×6479 | `5956`<br>`18076`<br>`21608` |
| `Method` | 100.0% | str×6479 | `POST`<br>`GET` |
| `URI` | 100.0% | str×6479 | `/e1cib/login?vl=ru_RU&version=8.3.27.1859&clnPid=23100&dppw=2100&nm=463105007949314142&ld=jblw4QoT9SPskLuQZUhLrfXixIpYF6au6VVneuBp9dlhPvpezaYxYktd_v_98ZgC03kU9N8bBjXfVRgoVFXGWDYGCJR7pZUQbVe_QpQLTIH91h…`<br>`/e1cib/metadata/splash?sysver=8.3.27.1859&confver=99984a2fb0fb4e41ad0489373fc731cb00000000&scale=100&operatingSystem=0&interfaceVar=0&extract=true`<br>`/e1cib/metadata/splash?sysver=8.3.27.1859&confver=99984a2fb0fb4e41ad0489373fc731cb00000000&scale=100&interfaceVar=0&operatingSystem=0&extract=true` |
| `Headers` | 100.0% | str×6479 | `1C-BaseLocation: e1c://server/localhost:2541/Test1CProf User-Agent: 1CV8C Content-Length: 72 1C-ApplicationName: 1CV8C Accept-Charset: utf-8 Accept-Encoding: zstd,lz4;q=0.7,deflate;q=0.5,1CSDC;q=0.2 A…`<br>`1C-BaseLocation: e1c://server/localhost:2541/Test1CProf User-Agent: 1CV8C Content-Length: 100 1C-ApplicationName: 1CV8C Accept-Charset: utf-8 Accept-Encoding: zstd,lz4;q=0.7,deflate;q=0.5,1CSDC;q=0.2 …`<br>`1C-BaseLocation: e1c://server/localhost:2541/Test1CProf User-Agent: 1CV8C Content-Length: 92 1C-ApplicationName: 1CV8C Accept-Charset: utf-8 Accept-Encoding: zstd,lz4;q=0.7,deflate;q=0.5,1CSDC;q=0.2 A…` |
| `Body` | 100.0% | str×6479 | `72`<br>`100`<br>`92` |
| `Cached` | 15.8% | str×1022 | `1` |
| `t:applicationName` | 0.1% | str×6 | `Debugger` |
| `t:computerName` | 0.1% | str×6 | `WIN` |

### `VRSRESPONSE` — sampled 6,175 events, 9 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×6175 | `INFO` |
| `OSThread` | 100.0% | str×6175 | `5956`<br>`18076`<br>`21608` |
| `Status` | 100.0% | str×6175 | `200`<br>`400`<br>`204` |
| `Phrase` | 100.0% | str×6175 | `OK`<br>`Bad request`<br>`No content` |
| `Headers` | 100.0% | str×6175 | `Server: 1C:Enterprise/8.3.27.1859 Content-Encoding: zstd Content-Language: ru-RU vrs-session: ZWFkMTVhNDYtYWQwMy00YjFiLWIwZjUtMzczYjYzYjE5M2Q4mZhKL7D7TkGtBIk3P8cxywAAAAA Content-Type: application/json…`<br>`Server: 1C:Enterprise/8.3.27.1859 Content-Encoding: zstd Content-Language: ru-RU vrs-session: ZWFkMTVhNDYtYWQwMy00YjFiLWIwZjUtMzczYjYzYjE5M2Q4mZhKL7D7TkGtBIk3P8cxywAAAAA vrs-predefinedCache: 1 Content…`<br>`Server: 1C:Enterprise/8.3.27.1859 Content-Encoding: zstd Content-Language: ru-RU Cache-Control: private, max-age=31536000 Content-Type: image/png Content-Length: 73022 Content-Disposition: inline; fil…` |
| `Body` | 100.0% | str×6175 | `72`<br>`100`<br>`1257` |
| `Cached` | 11.6% | str×719 | `1` |
| `t:applicationName` | 0.1% | str×6 | `Debugger` |
| `t:computerName` | 0.1% | str×6 | `WIN` |

### `SESN` — sampled 5,470 events, 9 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×5470 | `INFO` |
| `OSThread` | 100.0% | str×5470 | `29960`<br>`10432`<br>`20284` |
| `t:applicationName` | 100.0% | str×5470 | `ServerProcess` |
| `t:computerName` | 100.0% | str×5470 | `WIN` |
| `Func` | 100.0% | str×5470 | `Attach`<br>`Finish`<br>`Start` |
| `IB` | 100.0% | str×5470 | `Test1CProf` |
| `Appl` | 100.0% | str×5470 | `1CV8C`<br>`Designer`<br>`BackgroundJob` |
| `Nmb` | 100.0% | str×5470 | `14`<br>`1`<br>`2` |
| `ID` | 100.0% | str×5470 | `4dcb123a-e2a6-4f1a-916a-c72f3d72f9aa`<br>`0d94157f-f49d-44fd-830b-004f3a744095`<br>`9fc2d31e-af96-4052-9efd-22212a2acdd1` |

### `VRSCACHE` — sampled 3,078 events, 11 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×3078 | `INFO` |
| `OSThread` | 100.0% | str×3078 | `5956`<br>`18076`<br>`21608` |
| `action` | 65.8% | str×2026 | `lookup`<br>`create`<br>`check` |
| `resource` | 65.8% | str×2026 | `/e1cib/metadata/splash?sysver=8.3.27.1859&confver=99984a2fb0fb4e41ad0489373fc731cb00000000&scale=100&interfacevar=0&operatingsystem=0&extract=true`<br>`/e1cib/metadata/splash?sysver=8.3.27.1859&confver=99984a2fb0fb4e41ad0489373fc731cb00000000&scale=100&interfacevar=0&operatingsystem=0&extract=false`<br>`/e1cib/types?sysver=8.3.27.1859&types=c558190c989d3b6f7877a678edfca21f` |
| `Result` | 56.8% | str×1747 | `miss`<br>`hit`<br>`fresh` |
| `Method` | 42.1% | str×1295 | `GET` |
| `storage` | 32.2% | str×992 | `private`<br>`public` |
| `age` | 23.2% | str×713 | `4409`<br>`4410`<br>`4430` |
| `life` | 23.2% | str×713 | `31536000`<br>`259200` |
| `statusCode` | 8.9% | str×273 | `200` |
| `ETag` | 0.2% | str×6 | `"0c4a84bae76c8a35c0e809c7797035e0"` |

### `ATTN` — sampled 2,918 events, 13 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×2918 | `WARNING` |
| `OSThread` | 100.0% | str×2918 | `15600`<br>`21540`<br>`29200` |
| `Descr` | 100.0% | str×2918 | `Server online`<br>`Process online`<br>`Memory shortage detected` |
| `AgentUrl` | 93.7% | str×2734 | `` |
| `Url` | 62.5% | str×1823 | `tcp://WIN:2560`<br>`tcp://WIN:2541` |
| `ProcessId` | 62.5% | str×1823 | `bedd661d-ce4d-4eb8-b72d-9250d695f1a1`<br>`b56dcc07-d144-4579-a6e4-e78dcf221dbb` |
| `Pid` | 62.5% | str×1823 | `28220`<br>`24128` |
| `t:applicationName` | 6.3% | str×184 | `AgentProcess` |
| `t:computerName` | 6.3% | str×184 | `WIN` |
| `ServerId` | 6.3% | str×184 | `06e4c2f6-c5bd-4ea1-9432-6137510c95c1` |
| `Host` | 6.3% | str×184 | `WIN` |
| `FreeMemory` | 6.3% | str×184 | `674488320`<br>`568549376`<br>`675119104` |
| `SafeLimit` | 6.3% | str×184 | `1324652625` |

### `CLSTR` — sampled 1,985 events, 19 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×1985 | `INFO` |
| `OSThread` | 100.0% | str×1985 | `21068`<br>`8276`<br>`29960` |
| `Event` | 100.0% | str×1985 | `Performance update`<br>`Rebalance denied`<br>`Successful service call` |
| `Data` | 90.7% | str×1801 | `process=tcp://WIN:2541,pid=24128,sql=0,cpu=20,queue_length=1,queue_length/cpu_num=0,memory_performance=16,disk_performance=10,response_time=55,average_response_time=39.44`<br>`process=tcp://WIN:2560,pid=28220,sql=115,cpu=18,queue_length=1,queue_length/cpu_num=0,memory_performance=18,disk_performance=10,response_time=55,average_response_time=39.99`<br>`process=tcp://WIN:2541,pid=24128,sql=0,cpu=23,queue_length=1,queue_length/cpu_num=0,memory_performance=17,disk_performance=9,response_time=58,average_response_time=39.96` |
| `t:applicationName` | 54.2% | str×1076 | `Notification`<br>`ServerProcess`<br>`Debugger` |
| `t:computerName` | 54.2% | str×1076 | `WIN` |
| `Ref` | 8.1% | str×160 | `Test1CProf` |
| `SrcAddr` | 8.1% | str×160 | `WIN:2560`<br>`` |
| `SrcId` | 8.1% | str×160 | `bedd661d-ce4d-4eb8-b72d-9250d695f1a1`<br>`` |
| `SrcPid` | 8.1% | str×160 | `28220`<br>`` |
| `ApplicationExt` | 8.1% | str×160 | `1CV8C`<br>`Designer`<br>`BackgroundJob.CommonModule.СтандартныеПодсистемыСервер.ПередЗапускомФоновогоЗаданияСКонтекстомКлиента` |
| `Request` | 1.9% | str×37 | `a74b865c-7829-4f5c-96ca-8866aa377541`<br>`5bb79851-4c8b-46bc-a534-e78576a72c71`<br>`46f0f5d8-1276-401e-bfb1-d339fc88ed9a` |
| `DstAddr` | 1.9% | str×37 | `WIN:2560` |
| `DstId` | 1.9% | str×37 | `bedd661d-ce4d-4eb8-b72d-9250d695f1a1` |
| `DstPid` | 1.9% | str×37 | `28220` |
| `RmngrURL` | 1.0% | str×20 | `` |
| `ServiceName` | 1.0% | str×20 | `DebugService`<br>`WebSocketService`<br>`SpeechToTextModelManagementService` |
| `TargetCall` | 1.0% | str×20 | `0` |
| `Message` | 0.2% | str×4 | `serviceName=WebSocketService serviceID=ad029342-9cc0-427e-abe4-4b566fe969a1 stubID=a2f54ecf-ebcc-48ee-befd-9c410b9fe3f4`<br>`serviceName=SpeechToTextModelManagementService serviceID=6df1c45d-91b5-4201-aee9-f7285854f51b stubID=00d78045-6f69-49e1-9b5d-dbd325cbc4db` |

### `EXCPCNTX` — sampled 450 events, 10 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×450 | `WARNING` |
| `SrcName` | 52.7% | str×237 | `CONN`<br>`SCOM`<br>`PROC` |
| `OSThread` | 52.7% | str×237 | `4968`<br>`18076`<br>`14928` |
| `ClientID` | 50.0% | str×225 | `16`<br>`17`<br>`18` |
| `Txt` | 50.0% | str×225 | `Outgoing connection closed` |
| `ClientComputerName` | 47.3% | str×213 | `` |
| `ServerComputerName` | 47.3% | str×213 | `` |
| `ConnectString` | 47.3% | str×213 | `` |
| `ProcessName` | 1.3% | str×6 | `RHostRoot` |
| `SrcProcessName` | 1.3% | str×6 | `RHostRoot` |

### `EXCP` — sampled 299 events, 7 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×299 | `WARNING`<br>`ERROR`<br>`INFO` |
| `OSThread` | 100.0% | str×299 | `30708`<br>`4968`<br>`18076` |
| `Exception` | 100.0% | str×299 | `d294e384-7ea6-49c6-be96-f3a6e3de1242`<br>`9db1fa37-b455-4f3f-b8dd-7de0ea7d6da3`<br>`dd149677-3d47-4e05-a55f-4e75b13a441f` |
| `Descr` | 100.0% | str×299 | `LoadComponent(cfgtest): d294e384-7ea6-49c6-be96-f3a6e3de1242: Ошибка загрузки компоненты cfgtest: 126(0x0000007E): Не найден указанный модуль. `<br>`src\\backend\\src\\ClientFileCacheImpl.cpp(280): 9db1fa37-b455-4f3f-b8dd-7de0ea7d6da3: Файл не обнаружен 'v8stg64://c:/1/DynamicalWorkCache': src\\core\\src\\Storage64.cpp(3220)`<br>`src\\backend\\src\\ClientFileCacheImpl.cpp(280): 9db1fa37-b455-4f3f-b8dd-7de0ea7d6da3: Файл не обнаружен 'v8stg64://c:/3/DynamicalWorkCache': src\\core\\src\\Storage64.cpp(3182)` |
| `ClientID` | 71.2% | str×213 | `16`<br>`17`<br>`18` |
| `t:applicationName` | 6.0% | str×18 | `ServerProcess` |
| `t:computerName` | 6.0% | str×18 | `WIN` |

### `HASP` — sampled 262 events, 3 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×262 | `INFO` |
| `OSThread` | 100.0% | str×262 | `5956`<br>`30708`<br>`3472` |
| `Txt` | 100.0% | str×262 | ` LOCALHASP_HASPSTATUS(,,ser=ORGL8,,,,)->size=4,type=10,port=102,ApiVer=25684`<br>` MEMOHASP_READBLOCK(,port=102,ser=ORGL8,pos=56,size=1,,)->,,stat=0,buf=0500`<br>` LOCALHASP_ISHASP(,,ser=ORGL8,,,,)->found=1,port=0,stat=0,` |

### `TLOCK` — sampled 142 events, 8 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×142 | `INFO` |
| `OSThread` | 100.0% | str×142 | `20212`<br>`26380`<br>`27176` |
| `Func` | 100.0% | str×142 | `lockGranted src`<br>`Callback thread started`<br>`lockGranted dst` |
| `connectionID` | 91.5% | str×130 | `b38a1437-4371-46fa-b96a-c21eb589ab75`<br>`f8988907-bf26-456c-a561-d2d87a347dd5`<br>`c8a45605-3e30-47fa-88d4-9d2b5ad49811` |
| `transactionID` | 91.5% | str×130 | `2289`<br>`2349`<br>`2430` |
| `t:applicationName` | 45.8% | str×65 | `ServerProcess` |
| `t:computerName` | 45.8% | str×65 | `WIN` |
| `Host` | 8.5% | str×12 | `tcp://WIN:2560` |

### `SCOM` — sampled 110 events, 6 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×110 | `INFO` |
| `Func` | 100.0% | str×110 | `new ServerProcessData(199037d5740,,)`<br>`setSrcProcessName(199037d5740,DebugQueryTargets,DebugQueryTargets)`<br>`delete ServerProcessData(199037d5740,DebugQueryTargets,DebugQueryTargets)` |
| `OSThread` | 96.4% | str×106 | `6020`<br>`10832`<br>`28776` |
| `t:applicationName` | 80.9% | str×89 | `Debugger`<br>`AgentStandardCall`<br>`ragent` |
| `ProcessName` | 34.5% | str×38 | `DebugQueryTargets`<br>`DebugControlCenter`<br>`RHostRoot` |
| `SrcProcessName` | 34.5% | str×38 | `DebugQueryTargets`<br>`DebugControlCenter`<br>`RHostRoot` |

### `LIC` — sampled 28 events, 5 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×28 | `INFO` |
| `OSThread` | 100.0% | str×28 | `5956`<br>`30708`<br>`10832` |
| `Func` | 100.0% | str×28 | `initialize`<br>`getLicense`<br>`HaspLicense::InternalRelease` |
| `txt` | 100.0% | str×28 | `local Application, hasp HL soft local, ORGL8 local net, ORG8A local net, ORG8B local net, Base local net`<br>`0, client, seize, 2051857670784, local Application;    hard, local, client, 5, 1, (_) hard, local, 5, 1, (_)`<br>`2051857670784, 20260518135541, client; hard, local, client, 5` |
| `res` | 64.3% | str×18 | `seize`<br>`release` |

### `PROC` — sampled 21 events, 8 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×21 | `INFO` |
| `OSThread` | 95.2% | str×20 | `840`<br>`1128`<br>`19716` |
| `Txt` | 28.6% | str×6 | `Process terminated. Stopped as windows service: SERVICE_CONTROL_STOP`<br>`1C:Enterprise 8.3 (x86-64) (8.3.27.1859) Server Agent (debug) finished.`<br>`Process terminated. Stop signal received (ragent)` |
| `Finish` | 19.0% | str×4 | `success`<br>`Terminated by AppService, ExitCode:0` |
| `Err` | 9.5% | str×2 | `0` |
| `RunAs` | 4.8% | str×1 | `application` |
| `Port` | 4.8% | str×1 | `2540` |
| `Event` | 4.8% | str×1 | `Cluster lock absent` |

### `SYSTEM` — sampled 6 events, 5 unique fields

| field | freq | types | examples |
|---|---:|---|---|
| `level` | 100.0% | str×6 | `INFO` |
| `OSThread` | 100.0% | str×6 | `28776`<br>`19600`<br>`26752` |
| `operation` | 100.0% | str×6 | `sdc_init_client` |
| `config_version` | 100.0% | str×6 | `99984a2fb0fb4e41ad0489373fc731cb00000000` |
| `dictionary_hash` | 100.0% | str×6 | `1690499228` |

## 3. Top raw `context` значений (CALL / SCALL)

Эти строки — input для Phase A normalization. Цель — извлечь `Тип.Имя.Сущность`, отбросив `: line : statement`.

| count | raw context (первые 200 символов) |
|---:|---|
| 33 | ` МодульОбычногоПриложения : 38 : СтандартныеПодсистемыКлиент.ПередНачаломРаботыСистемы(); 	ОбщийМодуль.СтандартныеПодсистемыКлиент.Модуль : 228 : ПараметрыКлиента = СтандартныеПодсистемыКлиентПовтИсп.…` |
| 18 | ` МодульОбычногоПриложения : 54 : СтандартныеПодсистемыКлиент.ПередЗавершениемРаботыСистемы(Отказ); 	ОбщийМодуль.СтандартныеПодсистемыКлиент.Модуль : 397 : ВыполнитьОбработкуОповещения(Параметры.Обрабо…` |
| 2 | ` МодульОбычногоПриложения : 46 : СтандартныеПодсистемыКлиент.ПриНачалеРаботыСистемы(); 	ОбщийМодуль.СтандартныеПодсистемыКлиент.Модуль : 270 : ОбщегоНазначенияКлиентСервер.ПроверитьПараметр("Стандартн…` |
| 2 | ` МодульОбычногоПриложения : 46 : СтандартныеПодсистемыКлиент.ПриНачалеРаботыСистемы(); 	ОбщийМодуль.СтандартныеПодсистемыКлиент.Модуль : 314 : ВыполнитьОбработкуОповещения(Параметры.ОбработкаПродолжен…` |
| 1 | ` МодульОбычногоПриложения : 46 : СтандартныеПодсистемыКлиент.ПриНачалеРаботыСистемы(); 	ОбщийМодуль.СтандартныеПодсистемыКлиент.Модуль : 314 : ВыполнитьОбработкуОповещения(Параметры.ОбработкаПродолжен…` |

## 4. Распределение `Descr` для EXCP

| count | Descr (первые 120 символов) |
|---:|---|
| 18 | `src\\mngui\\src\\ExceptionWriterUIImpl.cpp(714), shown to the user: dc31263e-ecbf-41bd-9b3a-7b55897d5fd6: Не удалось заблок` |
| 11 | `src\\mngui\\src\\ExceptionWriterUIImpl.cpp(714), shown to the user: f6f167a0-dcc9-49ad-8f8e-2c9d9904e4fe: Не удалось провес` |
| 6 | `server_addr=tcp://WIN:2541 descr=[fe80::dc18:7c08:fb24:b7d8%27]:2541:10061(0x0000274D): Подключение не установлено, т.к.` |
| 6 | `src\\vrscore\\src\\InfobaseConnectionServiceImpl.cpp(224): 81029657-3fe6-4cd6-80c0-36de78fe6657: server_addr=tcp://WIN:2541` |
| 5 | `src\\rserver\\src\\IRMngrSrvcImpl.cpp(639): 60c686dc-798f-4d17-aadb-a90156a16eb8: ╨б╨╡╨░╨╜╤Б ╨╛╤В╤Б╤Г╤В╤Б╤В╨▓╤Г╨╡╤В ╨╕╨╗╨╕ ` |
| 5 | `src\\rserver\\src\\RemoteProxyStubServiceStubPlugin.cpp(206): 2386a9f7-a5fa-4d5b-9f6e-1179e73f150a: ╨Я╨╡╤А╨▓╨╕╤З╨╜╤Л╨╣ ╨▓╤Л` |
| 4 | `server_addr=tcp://127.0.0.1:1566 descr=127.0.0.1:1566:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1571 descr=127.0.0.1:1571:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `src\\vrscore\\src\\VResourceConnectionImpl.cpp(1060): 81029657-3fe6-4cd6-80c0-36de78fe6657: server_addr=tcp://WIN:2541 desc` |
| 4 | `server_addr=tcp://127.0.0.1:1569 descr=127.0.0.1:1569:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1577 descr=127.0.0.1:1577:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1585 descr=127.0.0.1:1585:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1589 descr=127.0.0.1:1589:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1590 descr=127.0.0.1:1590:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1586 descr=127.0.0.1:1586:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1575 descr=127.0.0.1:1575:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1572 descr=127.0.0.1:1572:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1574 descr=127.0.0.1:1574:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1573 descr=127.0.0.1:1573:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |
| 4 | `server_addr=tcp://127.0.0.1:1584 descr=127.0.0.1:1584:10060(0x0000274C): ╨Я╨╛╨┐╤Л╤В╨║╨░ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨╛╨╡╨┤╨╕╨` |

## 5. Implications для Sprint 3

- **TDEADLOCK:** в архиве не найдено или extra пустой → Phase D нужны дополнительные архивы
- **TLOCK:** 142 sampled, 8 полей.
  Топ-5 полей: `level`, `OSThread`, `Func`, `connectionID`, `transactionID`.
- **EXCP:** 299 sampled, 7 полей.

Полные таблицы выше → используем при designe explainer rules (Phase E).

---

_Сгенерировано `backend/scripts/inspect_extra_json.py` 2026-05-19 06:21_
