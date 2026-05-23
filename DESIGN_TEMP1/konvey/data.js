// Sample data for Konvey design — represents one project state.

window.KonveyData = (function () {
  // Field icon glyphs — use Unicode symbols rather than emoji.
  const TypeIcons = {
    str: 'T',
    num: '#',
    date: '◷',
    bool: '✓',
    ref: '→',
    table: '▤',
    register: '⊞',
    enum: '◇',
  };

  // Left column — source 1C config fields.
  // y is the row's vertical center in px (relative to the column's scroll-content)
  const sourceFields = [
    { kind: 'group', label: 'Document.РеализацияТоваровУслуг', y: 12, indent: 0, ico: '📄' },
    { kind: 'group', label: 'Реквизиты шапки', y: 36, indent: 1 },
    { id: 's-num',  type: 'str',  name: 'Номер',          dtype: 'Строка(11)',                  y: 60, indent: 2 },
    { id: 's-date', type: 'date', name: 'Дата',           dtype: 'Дата',                        y: 84, indent: 2 },
    { id: 's-sum',  type: 'num',  name: 'Сумма',          dtype: 'Число(15,2)',                 y: 108, indent: 2 },
    { id: 's-cur',  type: 'ref',  name: 'Валюта',         dtype: 'CatalogRef.Валюты',           y: 132, indent: 2 },
    { id: 's-kurs', type: 'num',  name: 'Курс',           dtype: 'Число(15,4)',                 y: 156, indent: 2 },
    { id: 's-cp',   type: 'ref',  name: 'Контрагент',     dtype: 'CatalogRef.Контрагенты',      y: 180, indent: 2 },
    { id: 's-org',  type: 'ref',  name: 'Организация',    dtype: 'CatalogRef.Организации',      y: 204, indent: 2 },
    { id: 's-skl',  type: 'ref',  name: 'Склад',          dtype: 'CatalogRef.Склады',           y: 228, indent: 2 },
    { id: 's-dog',  type: 'ref',  name: 'Договор',        dtype: 'CatalogRef.Договоры',         y: 252, indent: 2 },
    { id: 's-com',  type: 'str',  name: 'Комментарий',    dtype: 'Строка(500)',                 y: 276, indent: 2 },
    { id: 's-resp', type: 'ref',  name: 'Ответственный',  dtype: 'CatalogRef.Пользователи',     y: 300, indent: 2 },
    { kind: 'group', label: 'Табличные части', y: 324, indent: 1 },
    { kind: 'group', label: 'Товары', y: 348, indent: 2, ico: 'table' },
    { id: 's-t-nom', type: 'ref',  name: 'Номенклатура',  dtype: 'CatalogRef.Номенклатура',     y: 372, indent: 3 },
    { id: 's-t-qty', type: 'num',  name: 'Количество',    dtype: 'Число(15,3)',                 y: 396, indent: 3 },
    { id: 's-t-prc', type: 'num',  name: 'Цена',          dtype: 'Число(15,2)',                 y: 420, indent: 3 },
    { id: 's-t-sum', type: 'num',  name: 'Сумма',         dtype: 'Число(15,2)',                 y: 444, indent: 3 },
    { id: 's-t-ndp', type: 'num',  name: 'СтавкаНДС',     dtype: 'EnumRef.СтавкиНДС',           y: 468, indent: 3 },
    { kind: 'group', label: 'Услуги ▶',  y: 492, indent: 2 },
    { kind: 'group', label: 'Движения',  y: 516, indent: 1 },
    { kind: 'group', label: 'ТоварыНаСкладах ▶', y: 540, indent: 2, ico: 'register' },
  ];

  // EnterpriseData column.
  const edFields = [
    { kind: 'group', label: 'Документ.РеализацияТоваровУслуг', y: 12, indent: 0, ico: '📄' },
    { id: 'e-num',  type: 'str',  name: 'Номер',         dtype: 'xs:string',          req: true,  y: 36, indent: 1 },
    { id: 'e-date', type: 'date', name: 'Дата',          dtype: 'xs:date',            req: true,  y: 60, indent: 1 },
    { id: 'e-sum',  type: 'num',  name: 'Сумма',         dtype: 'ТипСумма',           req: true,  y: 84, indent: 1 },
    { id: 'e-cur',  type: 'ref',  name: 'Валюта',        dtype: 'КодВалюты',          req: true,  y: 108, indent: 1 },
    { id: 'e-kurs', type: 'num',  name: 'КурсВалюты',    dtype: 'xs:decimal',         req: false, y: 132, indent: 1 },
    { kind: 'group', label: 'Контрагент : КлючевыеСвойстваКонтрагент', y: 156, indent: 1, expand: true },
    { id: 'e-cp-guid', type: 'str', name: 'GUID',         dtype: 'xs:string',         req: true,  y: 180, indent: 2 },
    { id: 'e-cp-name', type: 'str', name: 'Наименование', dtype: 'xs:string',         req: true,  y: 204, indent: 2 },
    { id: 'e-cp-inn',  type: 'str', name: 'ИНН',          dtype: 'xs:string',         req: false, y: 228, indent: 2 },
    { id: 'e-cp-kpp',  type: 'str', name: 'КПП',          dtype: 'xs:string',         req: false, y: 252, indent: 2 },
    { kind: 'group', label: 'Организация : КлючевыеСвойстваОрганизация ▶', y: 276, indent: 1 },
    { id: 'e-skl',  type: 'ref',  name: 'Склад',         dtype: 'КлючСклад',          req: false, y: 300, indent: 1 },
    { id: 'e-dog',  type: 'ref',  name: 'Договор',       dtype: 'КлючДоговор',        req: false, y: 324, indent: 1 },
    { id: 'e-com',  type: 'str',  name: 'Комментарий',   dtype: 'xs:string',          req: false, y: 348, indent: 1 },
    { kind: 'group', label: 'Товары : Документ.Реализация.Товары', y: 372, indent: 1, expand: true, ico: 'table' },
    { kind: 'group', label: 'Строка', y: 396, indent: 2, expand: true },
    { id: 'e-t-nom', type: 'ref',  name: 'Номенклатура', dtype: 'КлючНоменклатура',   req: true,  y: 420, indent: 3 },
    { id: 'e-t-qty', type: 'num',  name: 'Количество',   dtype: 'xs:decimal',         req: true,  y: 444, indent: 3 },
    { id: 'e-t-prc', type: 'num',  name: 'Цена',         dtype: 'xs:decimal',         req: true,  y: 468, indent: 3 },
    { id: 'e-t-sum', type: 'num',  name: 'Сумма',        dtype: 'xs:decimal',         req: true,  y: 492, indent: 3 },
    { id: 'e-t-nds', type: 'enum', name: 'СтавкаНДС',    dtype: 'СтавкаНДСТип',       req: false, y: 516, indent: 3 },
    { kind: 'group', label: 'Услуги ▶', y: 540, indent: 1 },
  ];

  // Right column — target 1C config fields.
  const targetFields = [
    { kind: 'group', label: 'Document.РеализацияТоваровУслуг', y: 12, indent: 0, ico: '📄' },
    { kind: 'group', label: 'Реквизиты шапки', y: 36, indent: 1 },
    { id: 't-num',  type: 'str',  name: 'Номер',          dtype: 'Строка(11)',                 y: 60, indent: 2 },
    { id: 't-date', type: 'date', name: 'Дата',           dtype: 'Дата',                       y: 84, indent: 2 },
    { id: 't-sum',  type: 'num',  name: 'СуммаДокумента', dtype: 'Число(15,2)',                y: 108, indent: 2 },
    { id: 't-cur',  type: 'ref',  name: 'ВалютаДокумента',dtype: 'CatalogRef.Валюты',          y: 132, indent: 2 },
    { id: 't-kurs', type: 'num',  name: 'КурсДокумента',  dtype: 'Число(15,4)',                y: 156, indent: 2 },
    { id: 't-cp',   type: 'ref',  name: 'Контрагент',     dtype: 'CatalogRef.Контрагенты',     y: 180, indent: 2 },
    { id: 't-org',  type: 'ref',  name: 'Организация',    dtype: 'CatalogRef.Организации',     y: 204, indent: 2 },
    { id: 't-skl',  type: 'ref',  name: 'Склад',          dtype: 'CatalogRef.Склады',          y: 228, indent: 2 },
    { id: 't-dog',  type: 'ref',  name: 'ДоговорКонтрагента', dtype: 'CatalogRef.Договоры',    y: 252, indent: 2 },
    { id: 't-prim', type: 'str',  name: 'Примечание',     dtype: 'Строка(1024)',               y: 276, indent: 2 },
    { id: 't-resp', type: 'ref',  name: 'Ответственный',  dtype: 'CatalogRef.Пользователи',    y: 300, indent: 2 },
    { kind: 'group', label: 'Табличные части', y: 324, indent: 1 },
    { kind: 'group', label: 'Товары', y: 348, indent: 2, ico: 'table' },
    { id: 't-t-nom', type: 'ref',  name: 'Номенклатура',  dtype: 'CatalogRef.Номенклатура',    y: 372, indent: 3 },
    { id: 't-t-qty', type: 'num',  name: 'Количество',    dtype: 'Число(15,3)',                y: 396, indent: 3 },
    { id: 't-t-prc', type: 'num',  name: 'Цена',          dtype: 'Число(15,2)',                y: 420, indent: 3 },
    { id: 't-t-sum', type: 'num',  name: 'Сумма',         dtype: 'Число(15,2)',                y: 444, indent: 3 },
    { id: 't-t-nds', type: 'num',  name: 'СтавкаНДС',     dtype: 'EnumRef.СтавкиНДС',          y: 468, indent: 3 },
    { kind: 'group', label: 'Услуги ▶', y: 492, indent: 2 },
    { kind: 'group', label: 'Движения', y: 516, indent: 1 },
    { kind: 'group', label: 'ТоварыНаСкладах ▶', y: 540, indent: 2, ico: 'register' },
  ];

  // Left-to-ED mappings.
  const linesLE = [
    { from: 's-num',  to: 'e-num',  status: 'green' },
    { from: 's-date', to: 'e-date', status: 'green' },
    { from: 's-sum',  to: 'e-sum',  status: 'green' },
    { from: 's-cur',  to: 'e-cur',  status: 'green' },
    { from: 's-kurs', to: 'e-kurs', status: 'green' },
    { from: 's-cp',   to: 'e-cp-guid', status: 'green', selected: true },
    { from: 's-cp',   to: 'e-cp-name', status: 'green' },
    { from: 's-cp',   to: 'e-cp-inn',  status: 'green' },
    { from: 's-cp',   to: 'e-cp-kpp',  status: 'green' },
    { from: 's-skl',  to: 'e-skl',  status: 'green' },
    { from: 's-dog',  to: 'e-dog',  status: 'green' },
    { from: 's-com',  to: 'e-com',  status: 'amber' },
    { from: 's-t-nom', to: 'e-t-nom', status: 'green' },
    { from: 's-t-qty', to: 'e-t-qty', status: 'green' },
    { from: 's-t-prc', to: 'e-t-prc', status: 'green' },
    { from: 's-t-sum', to: 'e-t-sum', status: 'green' },
    { from: 's-t-ndp', to: 'e-t-nds', status: 'amber' },
  ];

  // ED-to-right mappings.
  const linesER = [
    { from: 'e-num',  to: 't-num',  status: 'green' },
    { from: 'e-date', to: 't-date', status: 'green' },
    { from: 'e-sum',  to: 't-sum',  status: 'amber' },
    { from: 'e-cur',  to: 't-cur',  status: 'green' },
    { from: 'e-kurs', to: 't-kurs', status: 'amber' },
    { from: 'e-cp-guid', to: 't-cp', status: 'green' },
    { from: 'e-skl',  to: 't-skl',  status: 'green' },
    { from: 'e-dog',  to: 't-dog',  status: 'green' },
    { from: 'e-com',  to: 't-prim', status: 'red' },
    { from: 'e-t-nom', to: 't-t-nom', status: 'green' },
    { from: 'e-t-qty', to: 't-t-qty', status: 'green' },
    { from: 'e-t-prc', to: 't-t-prc', status: 'green' },
    { from: 'e-t-sum', to: 't-t-sum', status: 'green' },
    { from: 'e-t-nds', to: 't-t-nds', status: 'amber' },
  ];

  // Left sidebar object tree.
  const sidebarTree = [
    {
      type: 'Documents', count: 5, open: true, items: [
        { ico: 'doc', name: 'РеализацияТоваровУслуг',  mapped: 22, total: 22, status: 'green', active: true },
        { ico: 'doc', name: 'ПоступлениеТоваровУслуг', mapped: 18, total: 22, status: 'amber' },
        { ico: 'doc', name: 'ВозвратТоваровОтПокупателя', mapped: 12, total: 22, status: 'red' },
        { ico: 'doc', name: 'СчётНаОплатуПокупателю',  mapped: 14, total: 14, status: 'green' },
        { ico: 'doc', name: 'ЗаказКлиента',            mapped: 9,  total: 18, status: 'amber' },
      ],
    },
    {
      type: 'Catalogs', count: 12, open: true, items: [
        { ico: 'cat', name: 'Контрагенты',     mapped: 8,  total: 8,  status: 'green' },
        { ico: 'cat', name: 'Номенклатура',    mapped: 15, total: 15, status: 'green' },
        { ico: 'cat', name: 'Договоры',        mapped: 6,  total: 9,  status: 'amber' },
        { ico: 'cat', name: 'Организации',     mapped: 7,  total: 7,  status: 'green' },
        { ico: 'cat', name: 'Склады',          mapped: 4,  total: 4,  status: 'green' },
        { ico: 'cat', name: 'Валюты',          mapped: 3,  total: 3,  status: 'green' },
        { ico: 'cat', name: 'БанковскиеСчета', mapped: 5,  total: 6,  status: 'amber' },
        { ico: 'cat', name: 'Пользователи',    mapped: 4,  total: 4,  status: 'green' },
      ],
    },
    {
      type: 'InformationRegisters', count: 3, open: false,
    },
    {
      type: 'AccumulationRegisters', count: 4, open: false,
    },
    {
      type: 'Enums', count: 8, open: false,
    },
    {
      type: 'ChartsOfCharacteristicTypes', count: 2, open: false,
    },
  ];

  return {
    TypeIcons,
    sourceFields, edFields, targetFields,
    linesLE, linesER,
    sidebarTree,
  };
})();
