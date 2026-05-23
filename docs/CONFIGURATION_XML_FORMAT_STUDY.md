# Configuration XML Format Study

**Источник:** `C:\BUFFER\SCHEME`  
**Phase:** Sprint 5 Phase 0 (Discovery)  
**Цель:** зафиксировать формат XML выгрузки конфигурации 1С
до написания backend парсера (Phase A).

Документ сгенерирован автоматически скриптом
`backend/scripts/inspect_configuration_xml.py`.

## 1. Общая статистика

| Папка (EN) | Тип объекта (RU) | Кол-во | Запросный? |
|---|---|---:|:---:|
| AccountingRegisters | РегистрБухгалтерии | 1 | Yes |
| AccumulationRegisters | РегистрНакопления | 75 | Yes |
| Catalogs | Справочник | 262 | Yes |
| ChartsOfAccounts | ПланСчетов | 1 | Yes |
| ChartsOfCalculationTypes | ПланВидовРасчета | 3 | Yes |
| ChartsOfCharacteristicTypes | ПланВидовХарактеристик | 7 | Yes |
| CommandGroups | ГруппаКоманд | 21 | — |
| CommonAttributes | ОбщийРеквизит | 2 | — |
| CommonCommands | ОбщаяКоманда | 482 | — |
| CommonForms | ОбщаяФорма | 151 | — |
| CommonModules | ОбщийМодуль | 860 | — |
| CommonPictures | ОбщаяКартинка | 702 | — |
| CommonTemplates | ОбщийМакет | 94 | — |
| Constants | Константа | 252 | Yes |
| DataProcessors | Обработка | 155 | — |
| DefinedTypes | ОпределяемыйТип | 13 | — |
| DocumentJournals | ЖурналДокументов | 23 | Yes |
| DocumentNumerators | НумераторДокументов | 1 | — |
| Documents | Документ | 195 | Yes |
| Enums | Перечисление | 422 | Yes |
| EventSubscriptions | ПодпискаНаСобытие | 208 | — |
| ExchangePlans | ПланОбмена | 20 | Yes |
| Ext | — | 6 | — |
| FilterCriteria | КритерийОтбора | 5 | — |
| FunctionalOptions | ФункциональнаяОпция | 221 | — |
| FunctionalOptionsParameters | ПараметрФункциональнойОпции | 5 | — |
| InformationRegisters | РегистрСведений | 381 | Yes |
| Languages | Язык | 1 | — |
| Reports | Отчет | 269 | — |
| Roles | Роль | 118 | — |
| ScheduledJobs | РегламентноеЗадание | 35 | — |
| Sequences | Последовательность | 5 | Yes |
| SessionParameters | ПараметрСеанса | 28 | — |
| SettingsStorages | ХранилищеНастроек | 1 | — |
| StyleItems | ЭлементСтиля | 118 | — |
| Subsystems | Подсистема | 48 | — |
| WebServices | WebСервис | 11 | — |
| XDTOPackages | ПакетXDTO | 84 | — |
| **Итого** | | **5286** | |
| (из них запросных) | | **1647** | |

## 2. Корневой `Configuration.xml`

Содержит имя конфигурации, синоним, версию платформы, версию конфигурации, поставщика, ссылки на все объекты. Для Sprint 5 нас интересуют только `Properties/Name` и `Properties/Synonym`:

- **Корневой тег:** `Configuration`
- **Name:** `БухгалтерияПредприятия`
- **Synonym (ru):** `Бухгалтерия предприятия, редакция 3.0`

## 3. Структура XML-файла объекта (общая схема)

Каждый XML-файл объекта (например `Catalogs/Контрагенты.xml`) имеет
единообразную структуру:

```xml
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" ...>
  <Catalog uuid="..."> <!-- ИЛИ Document, AccumulationRegister, и т.д. -->
    <InternalInfo>
      <xr:GeneratedType name="CatalogRef.Контрагенты" category="Ref"/>
      <!-- generated types: Object, Ref, Selection, List, Manager -->
    </InternalInfo>
    <Properties>
      <Name>Контрагенты</Name>
      <Synonym>
        <v8:item>
          <v8:lang>ru</v8:lang>
          <v8:content>Контрагенты</v8:content>
        </v8:item>
      </Synonym>
      <!-- type-specific properties: Hierarchical, RegisterType, ChartOfAccounts ... -->
    </Properties>
    <ChildObjects>
      <Attribute>...</Attribute>            <!-- реквизит -->
      <Dimension>...</Dimension>            <!-- измерение (регистры) -->
      <Resource>...</Resource>              <!-- ресурс (регистры) -->
      <TabularSection>...</TabularSection>  <!-- табчасть -->
      <EnumValue>...</EnumValue>            <!-- значение перечисления -->
      <Form>имя_формы</Form>                <!-- ссылка на форму -->
      <Command>...</Command>
    </ChildObjects>
  </Catalog>
</MetaDataObject>
```

**Корневые теги по типам:**

| Папка | Корневой тег объекта |
|---|---|
| Catalogs | `Catalog` |
| Documents | `Document` |
| AccumulationRegisters | `AccumulationRegister` |
| InformationRegisters | `InformationRegister` |
| AccountingRegisters | `AccountingRegister` |
| CalculationRegisters | `CalculationRegister` |
| ChartsOfAccounts | `ChartOfAccounts` |
| ChartsOfCharacteristicTypes | `ChartOfCharacteristicTypes` |
| ChartsOfCalculationTypes | `ChartOfCalculationTypes` |
| Enums | `Enum` |
| DocumentJournals | `DocumentJournal` |
| Constants | `Constant` |
| ExchangePlans | `ExchangePlan` |

## 4. Структура `Attribute` / `Dimension` / `Resource`

У всех трёх типов структура `<Properties>` одинаковая:

```xml
<Attribute uuid="...">
  <Properties>
    <Name>ИНН</Name>
    <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>ИНН</v8:content></v8:item></Synonym>
    <Type>
      <v8:Type>xs:string</v8:Type>            <!-- примитивный -->
      <v8:StringQualifiers>
        <v8:Length>12</v8:Length>
        <v8:AllowedLength>Variable</v8:AllowedLength>
      </v8:StringQualifiers>
    </Type>
  </Properties>
</Attribute>
```

**Возможные значения `<v8:Type>`:**

- `xs:string` — Строка (+ StringQualifiers с Length)
- `xs:decimal` — Число (+ NumberQualifiers с Digits/FractionDigits)
- `xs:boolean` — Булево
- `xs:dateTime` — Дата
- `cfg:CatalogRef.X` — ссылка на справочник X
- `cfg:DocumentRef.X` — ссылка на документ X
- `cfg:EnumRef.X` — ссылка на перечисление X
- `cfg:ChartOfCharacteristicTypesRef.X` — ссылка на ПВХ X
- `cfg:DefinedType.X` — определяемый тип (составной)
- `cfg:AccumulationRegisterRecordSet.X` — рекордсет регистра

Несколько `<v8:Type>` внутри одного `<Type>` = составной тип.

## 5. Виртуальные таблицы регистров

Виртуальные таблицы не хранятся отдельным тегом — они выводятся из
типа регистра:

| Тип регистра | XML-тег | RegisterType | Виртуальные таблицы (SDBL) |
|---|---|---|---|
| Регистр накопления (остатков) | `AccumulationRegister` | `Balance` | `Остатки`, `Обороты`, `ОстаткиИОбороты` |
| Регистр накопления (оборотов) | `AccumulationRegister` | `Turnovers` | `Обороты` |
| Регистр сведений | `InformationRegister` | — | `СрезПоследних`, `СрезПервых` |
| Регистр бухгалтерии | `AccountingRegister` | — | `Остатки`, `Обороты`, `ОстаткиИОбороты`, `ДвиженияССубконто`, `ОборотыДтКт` |
| Регистр расчёта | `CalculationRegister` | — | `БазаДанных`, `ДанныеГрафика`, `ФактическийПериодДействия` |

## 6. Образцы структуры по типам

### Catalogs (Справочник) — образец `АктОбОказанииПроизводственныхУслугПрисоединенныеФайлы.xml`

- **Корневой тег:** `Catalog`
- **Name:** `АктОбОказанииПроизводственныхУслугПрисоединенныеФайлы`
- **Synonym (ru):** `Присоединенные файлы (Оказание производственных услуг)`
- **Реквизитов:** 18
- **Измерений:** 0
- **Ресурсов:** 0
- **Табчастей:** 2
- **Значений перечисления:** 0

Первые 5 реквизитов:
  - `Автор` : `cfg:CatalogRef.Пользователи`
  - `ВладелецФайла` : `cfg:DocumentRef.АктОбОказанииПроизводственныхУслуг`
  - `ДатаМодификацииУниверсальная` : `xs:dateTime`
  - `ДатаСоздания` : `xs:dateTime`
  - `Зашифрован` : `xs:boolean`

### Documents (Документ) — образец `АвансовыйОтчет.xml`

- **Корневой тег:** `Document`
- **Name:** `АвансовыйОтчет`
- **Synonym (ru):** `Авансовый отчет`
- **Реквизитов:** 19
- **Измерений:** 0
- **Ресурсов:** 0
- **Табчастей:** 5
- **Значений перечисления:** 0

Первые 5 реквизитов:
  - `ВалютаДокумента` : `cfg:CatalogRef.Валюты`
  - `Комментарий` : `xs:string`
  - `КурсДокумента` : `xs:decimal`
  - `КратностьДокумента` : `xs:decimal`
  - `Организация` : `cfg:CatalogRef.Организации`

### AccumulationRegisters (РегистрНакопления) — образец `АвансовыеПлатежиИностранцевПоНДФЛ.xml`

- **Корневой тег:** `AccumulationRegister`
- **Name:** `АвансовыеПлатежиИностранцевПоНДФЛ`
- **Synonym (ru):** `Авансовые платежи иностранцев по НДФЛ`
- **RegisterType:** `Balance`
- **Реквизитов:** 5
- **Измерений:** 4
- **Ресурсов:** 1
- **Табчастей:** 0
- **Значений перечисления:** 0

Первые 5 реквизитов:
  - `Подразделение` : ``
  - `РегистрацияВНалоговомОргане` : `cfg:CatalogRef.РегистрацииВНалоговомОргане`
  - `СтавкаНалогообложенияРезидента` : `cfg:EnumRef.НДФЛСтавкиНалогообложенияРезидента`
  - `МесяцНалоговогоПериода` : `xs:dateTime`
  - `КодДохода` : `cfg:CatalogRef.ВидыДоходовНДФЛ`

Измерения:
  - `ГоловнаяОрганизация` : `cfg:CatalogRef.Организации`
  - `ФизическоеЛицо` : `cfg:CatalogRef.ФизическиеЛица`
  - `Год` : `xs:decimal`
  - `Организация` : `cfg:CatalogRef.Организации`

Ресурсы:
  - `Сумма` : `xs:decimal`

### InformationRegisters (РегистрСведений) — образец `АдресныеОбъекты.xml`

- **Корневой тег:** `InformationRegister`
- **Name:** `АдресныеОбъекты`
- **Synonym (ru):** `Адресные объекты`
- **Реквизитов:** 0
- **Измерений:** 11
- **Ресурсов:** 6
- **Табчастей:** 0
- **Значений перечисления:** 0

Измерения:
  - `Уровень` : `xs:decimal`
  - `КодСубъектаРФ` : `xs:decimal`
  - `КодОкруга` : `xs:decimal`
  - `КодРайона` : `xs:decimal`
  - `КодГорода` : `xs:decimal`
  - `КодВнутригородскогоРайона` : `xs:decimal`
  - `КодНаселенногоПункта` : `xs:decimal`
  - `КодУлицы` : `xs:decimal`
  - `КодДополнительногоЭлемента` : `xs:decimal`
  - `КодПодчиненногоЭлемента` : `xs:decimal`
  - `Идентификатор` : `v8:UUID`

Ресурсы:
  - `ПочтовыйИндекс` : `xs:decimal`
  - `Наименование` : `xs:string`
  - `Сокращение` : `xs:string`
  - `Дополнительно` : `v8:UUID`
  - `КодКЛАДР` : `xs:decimal`
  - `Актуален` : `xs:boolean`

### AccountingRegisters (РегистрБухгалтерии) — образец `Хозрасчетный.xml`

- **Корневой тег:** `AccountingRegister`
- **Name:** `Хозрасчетный`
- **Synonym (ru):** `Журнал проводок (бухгалтерский и налоговый учет)`
- **Реквизитов:** 2
- **Измерений:** 3
- **Ресурсов:** 6
- **Табчастей:** 0
- **Значений перечисления:** 0

Первые 5 реквизитов:
  - `Содержание` : `xs:string`
  - `НеКорректироватьСтоимостьАвтоматически` : `xs:boolean`

Измерения:
  - `Организация` : `cfg:CatalogRef.Организации`
  - `Валюта` : `cfg:CatalogRef.Валюты`
  - `Подразделение` : `cfg:CatalogRef.ПодразделенияОрганизаций`

Ресурсы:
  - `Сумма` : `xs:decimal`
  - `ВалютнаяСумма` : `xs:decimal`
  - `Количество` : `xs:decimal`
  - `СуммаНУ` : `xs:decimal`
  - `СуммаПР` : `xs:decimal`
  - `СуммаВР` : `xs:decimal`

### ChartsOfCharacteristicTypes (ПланВидовХарактеристик) — образец `ВидыСубконтоХозрасчетные.xml`

- **Корневой тег:** `ChartOfCharacteristicTypes`
- **Name:** `ВидыСубконтоХозрасчетные`
- **Synonym (ru):** `Виды субконто хозрасчетные`
- **Реквизитов:** 0
- **Измерений:** 0
- **Ресурсов:** 0
- **Табчастей:** 0
- **Значений перечисления:** 0

### ChartsOfAccounts (ПланСчетов) — образец `Хозрасчетный.xml`

- **Корневой тег:** `ChartOfAccounts`
- **Name:** `Хозрасчетный`
- **Synonym (ru):** `План счетов бухгалтерского учета`
- **Реквизитов:** 2
- **Измерений:** 0
- **Ресурсов:** 0
- **Табчастей:** 0
- **Значений перечисления:** 0

Первые 5 реквизитов:
  - `ЗапретитьИспользоватьВПроводках` : `xs:boolean`
  - `КодБыстрогоВыбора` : `xs:string`

### Enums (Перечисление) — образец `АмортизационныеГруппы.xml`

- **Корневой тег:** `Enum`
- **Name:** `АмортизационныеГруппы`
- **Synonym (ru):** `Амортизационные группы`
- **Реквизитов:** 0
- **Измерений:** 0
- **Ресурсов:** 0
- **Табчастей:** 0
- **Значений перечисления:** 11

Значения: `ПерваяГруппа, ВтораяГруппа, ТретьяГруппа, ЧетвертаяГруппа, ПятаяГруппа, ШестаяГруппа, СедьмаяГруппа, ВосьмаяГруппа, ДевятаяГруппа, ДесятаяГруппа`

### DocumentJournals (ЖурналДокументов) — образец `АнкетыПерсонифицированногоУчета.xml`

- **Корневой тег:** `DocumentJournal`
- **Name:** `АнкетыПерсонифицированногоУчета`
- **Synonym (ru):** `Анкеты персучета (АДВ-1,2,3)`
- **Реквизитов:** 0
- **Измерений:** 0
- **Ресурсов:** 0
- **Табчастей:** 0
- **Значений перечисления:** 0

## 7. Выводы и input для Phase A

**Структура единообразная** — `MetaDataObject/<тип>/Properties` +
`ChildObjects` есть у всех queryable объектов. Можно сделать
**generic парсер с диспатчем по корневому тегу**.

**Парсер Phase A должен:**

1. Игнорировать неprestrelnye типы (CommonModules, CommonPictures,
   Roles, и т.п.) — они не упоминаются в SDBL.
2. Извлекать только `Name`, `Synonym` (ru), `Attribute`, `Dimension`,
   `Resource`, `TabularSection`, `EnumValue` — этого достаточно для
   семантической валидации запросов в Sprint 5.
3. Для регистров — определять тип виртуальных таблиц по
   `RegisterType` + типу регистра (см. таблицу в разделе 5).
4. Использовать только `xml.etree.ElementTree` (ADR-030).

**STOP RULE не сработал:** структура полностью консистентна между
разными типами объектов. Generic парсер с базовым алгоритмом +
type-specific шагами (например, RegisterType для AccumulationRegister)
реализуем без блокирующих неопределённостей.

