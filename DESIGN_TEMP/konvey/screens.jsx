// Konvey secondary screens — Project Picker, New Project Wizard,
// Handler Editor, Diff View, Command Palette.

// ============================================================
// Project Picker
// ============================================================
function ProjectPicker() {
  const projects = [
    {
      name: 'Обмен УТ 11.5 ↔ БП 3.0',
      src: 'УТ 11.5', tgt: 'БП 3.0',
      ed: '1.8.6',
      modified: '16 мая 2026, 14:32',
      mapped: 220, total: 267,
      status: 'green', statusLabel: 'Validation OK',
    },
    {
      name: 'ERP 2.5 → Документооборот 3.0',
      src: 'ERP 2.5', tgt: 'ДО 3.0',
      ed: '1.8.6',
      modified: '15 мая 2026, 18:40',
      mapped: 142, total: 198,
      status: 'amber', statusLabel: '12 warnings',
    },
    {
      name: 'ЗУП 3.1 ↔ Бухгалтерия 3.0',
      src: 'ЗУП 3.1', tgt: 'БП 3.0',
      ed: '1.7',
      modified: '14 мая 2026, 11:02',
      mapped: 87, total: 87,
      status: 'green', statusLabel: 'Validation OK',
    },
    {
      name: 'Розница 2.3 → УТ 11.5',
      src: 'Розница 2.3', tgt: 'УТ 11.5',
      ed: '1.8.6',
      modified: '12 мая 2026, 09:15',
      mapped: 64, total: 96,
      status: 'red', statusLabel: '3 errors',
    },
    {
      name: 'УНФ 1.6 → Бухгалтерия 3.0',
      src: 'УНФ 1.6', tgt: 'БП 3.0',
      ed: '1.6',
      modified: '8 мая 2026, 17:24',
      mapped: 31, total: 142,
      status: 'gray', statusLabel: 'Not validated',
    },
    {
      name: 'Конвертация ERP-демо',
      src: 'ERP 2.5', tgt: 'ED only',
      ed: '1.8.6',
      modified: '2 мая 2026, 22:08',
      mapped: 0, total: 0,
      status: 'gray', statusLabel: 'Empty',
    },
  ];

  return (
    <div className="k-app" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="k-header" style={{ paddingLeft: 24, paddingRight: 24 }}>
        <span className="k-logo">Konvey</span>
        <span style={{ color: 'var(--k-text-3)', fontSize: 11 }}>генератор правил обмена 1С · EnterpriseData / КД 3.1</span>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost">Открыть из файла…</button>
        <button className="k-btn sm primary"><Icon.Plus/>Новый проект</button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 18 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>
            Проекты
            <span style={{ color: 'var(--k-text-3)', fontWeight: 400, marginLeft: 8 }}>{projects.length}</span>
          </h2>
          <span style={{ flex: 1 }}/>
          <div className="k-search" style={{ width: 240 }}>
            <Icon.Search/>
            <span style={{ flex: 1, color: 'var(--k-text-3)' }}>Поиск проекта…</span>
          </div>
          <div style={{ marginLeft: 8 }}>
            <button className="k-btn sm">
              Сортировка: Недавние <Icon.TriangleDown/>
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
          {projects.map((p, i) => (
            <div key={i} style={{
              background: 'var(--k-panel)',
              border: '1px solid var(--k-border)',
              borderRadius: 'var(--k-radius-md)',
              padding: '14px 16px',
              cursor: 'pointer',
              position: 'relative',
              transition: 'box-shadow 120ms, border-color 120ms',
              ...(i === 0 ? { boxShadow: 'var(--k-shadow-sm)', borderColor: 'var(--k-border-strong)' } : {}),
            }}>
              {/* hover-revealed kebab — show on first card */}
              {i === 0 && (
                <button className="k-btn icon sm" style={{ position: 'absolute', top: 10, right: 10, height: 22, width: 22, border: 'none' }}>
                  <Icon.Kebab/>
                </button>
              )}
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, letterSpacing: '-0.01em' }}>
                {p.name}
              </div>
              <div className="k-mono" style={{ fontSize: 11, color: 'var(--k-text-3)', marginBottom: 8 }}>
                {p.src} <span style={{ color: 'var(--k-text-4)' }}>→</span> {p.tgt}
                <span style={{ marginLeft: 10, color: 'var(--k-text-4)' }}>ED {p.ed}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--k-text-3)', marginBottom: 12 }}>
                изменён {p.modified}
              </div>

              {/* progress */}
              <div style={{ marginBottom: 10 }}>
                <div style={{
                  height: 4, borderRadius: 999,
                  background: 'var(--k-panel-sunk)',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%',
                    width: `${p.total ? Math.round((p.mapped / p.total) * 100) : 0}%`,
                    background: p.status === 'red' ? 'var(--k-red)' :
                                p.status === 'amber' ? 'var(--k-amber)' :
                                p.status === 'green' ? 'var(--k-green)' : 'var(--k-text-4)',
                  }}/>
                </div>
                <div className="k-mono" style={{
                  fontSize: 10.5, color: 'var(--k-text-3)',
                  marginTop: 4, display: 'flex', justifyContent: 'space-between',
                }}>
                  <span>{p.mapped}/{p.total} mapped</span>
                  <span>{p.total ? Math.round((p.mapped / p.total) * 100) : 0}%</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: p.status === 'red' ? 'var(--k-red)' :
                              p.status === 'amber' ? 'var(--k-amber)' :
                              p.status === 'green' ? 'var(--k-green)' : 'var(--k-text-4)',
                }}/>
                <span style={{ color: 'var(--k-text-2)' }}>{p.statusLabel}</span>
              </div>

              {/* Context menu on first card */}
              {i === 0 && (
                <div style={{
                  position: 'absolute', top: 36, right: 8,
                  background: 'var(--k-panel)',
                  border: '1px solid var(--k-border)',
                  borderRadius: 'var(--k-radius-md)',
                  boxShadow: 'var(--k-shadow-lg)',
                  padding: 4, minWidth: 160, zIndex: 10,
                  fontSize: 12,
                }}>
                  {['Открыть', 'Дублировать', 'Экспорт JSON…', '— —', 'Удалить'].map((it, j) => (
                    it === '— —' ? <div key={j} style={{ height: 1, background: 'var(--k-divider)', margin: '4px 0' }}/> :
                    <div key={j} style={{
                      padding: '6px 10px', borderRadius: 4,
                      color: it === 'Удалить' ? 'var(--k-red)' : 'var(--k-text)',
                      background: j === 0 ? 'var(--k-panel-sunk)' : 'transparent',
                    }}>{it}</div>
                  ))}
                </div>
              )}
            </div>
          ))}

          {/* "New project" CTA card */}
          <div style={{
            background: 'transparent',
            border: '1px dashed var(--k-border-strong)',
            borderRadius: 'var(--k-radius-md)',
            padding: '14px 16px',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            color: 'var(--k-text-3)',
            cursor: 'pointer',
            minHeight: 160,
          }}>
            <Icon.Plus style={{ width: 18, height: 18 }}/>
            <div style={{ marginTop: 6, fontSize: 12 }}>Создать проект</div>
            <div style={{ marginTop: 2, fontSize: 11, color: 'var(--k-text-4)' }} className="k-mono">⌘N</div>
          </div>
        </div>
      </div>

      <div className="k-statusbar">
        <span className="seg"><span className="label">Konvey</span> v0.14.2</span>
        <span style={{ flex: 1 }}/>
        <span className="seg" style={{ color: 'var(--k-green)' }}>● online</span>
      </div>
    </div>
  );
}

// ============================================================
// New Project Wizard — Step 4 (Objects for exchange)
// ============================================================
function WizardStep4() {
  const tree = [
    { type: 'Documents', count: 234, items: [
      { name: 'РеализацияТоваровУслуг', checked: true },
      { name: 'ПоступлениеТоваровУслуг', checked: true },
      { name: 'ВозвратТоваровОтПокупателя', checked: false },
      { name: 'ВозвратТоваровПоставщику', checked: false },
      { name: 'СчётНаОплатуПокупателю', checked: true },
      { name: 'ЗаказКлиента', checked: false },
      { name: 'ЗаказПоставщику', checked: false },
    ]},
    { type: 'Catalogs', count: 412, items: [
      { name: 'Контрагенты', checked: true, auto: true },
      { name: 'Номенклатура', checked: true, auto: true },
      { name: 'Договоры', checked: true, auto: true },
      { name: 'Организации', checked: true, auto: true },
      { name: 'Склады', checked: true, auto: true },
      { name: 'Валюты', checked: true, auto: true },
      { name: 'БанковскиеСчета', checked: true, auto: true },
      { name: 'Подразделения', checked: false },
    ]},
    { type: 'InformationRegisters', count: 89, items: [
      { name: 'КурсыВалют', checked: true, auto: true },
      { name: 'ЦеныНоменклатуры', checked: false },
    ]},
  ];

  const templates = [
    { name: 'Стандартный обмен НСИ', desc: 'Контрагенты · Договоры · Номенклатура · Банки · Валюты', active: true },
    { name: 'Только справочники', desc: 'Базовая НСИ без документов' },
    { name: 'Продажи + НСИ', desc: 'Документы реализации со связанными справочниками' },
    { name: 'Закупки + НСИ', desc: 'Поступления и заказы поставщикам' },
    { name: 'Зарплата и кадры', desc: 'Сотрудники · Подразделения · Должности' },
  ];

  const selected = [
    { kind: 'doc', name: 'Document.РеализацияТоваровУслуг', root: true },
    { kind: 'doc', name: 'Document.ПоступлениеТоваровУслуг', root: true },
    { kind: 'doc', name: 'Document.СчётНаОплатуПокупателю', root: true },
    { kind: 'cat', name: 'Catalog.Контрагенты', auto: true },
    { kind: 'cat', name: 'Catalog.Номенклатура', auto: true },
    { kind: 'cat', name: 'Catalog.Договоры', auto: true },
    { kind: 'cat', name: 'Catalog.Организации', auto: true },
    { kind: 'cat', name: 'Catalog.Склады', auto: true },
    { kind: 'cat', name: 'Catalog.Валюты', auto: true },
    { kind: 'cat', name: 'Catalog.БанковскиеСчета', auto: true },
    { kind: 'reg', name: 'InformationRegister.КурсыВалют', auto: true },
  ];

  return (
    <div className="k-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--k-panel)' }}>
      {/* Wizard header */}
      <div style={{
        padding: '14px 24px',
        borderBottom: '1px solid var(--k-border)',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>Новый проект</div>
        <span style={{ color: 'var(--k-text-3)', fontSize: 12 }}>· Обмен УТ 11.5 ↔ БП 3.0</span>
        <span style={{ flex: 1 }}/>
        <span className="k-btn icon sm ghost"><Icon.X/></span>
      </div>

      {/* Steps strip */}
      <div style={{
        padding: '14px 24px',
        background: 'var(--k-panel-sunk)',
        borderBottom: '1px solid var(--k-border)',
        display: 'flex', alignItems: 'center', gap: 18, fontSize: 12,
      }}>
        {[
          ['1', 'Стандарт', true],
          ['2', 'Источник', true],
          ['3', 'Приёмник', true],
          ['4', 'Объекты', 'active'],
        ].map(([n, label, state], i, arr) => (
          <React.Fragment key={i}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                width: 20, height: 20, borderRadius: '50%',
                display: 'grid', placeItems: 'center',
                background: state === 'active' ? 'var(--k-accent)' : state === true ? 'var(--k-green)' : 'var(--k-panel)',
                color: state ? 'white' : 'var(--k-text-3)',
                border: !state ? '1px solid var(--k-border-strong)' : 'none',
                fontFamily: 'var(--k-font-mono)',
                fontSize: 10.5,
              }}>
                {state === true ? <Icon.Check/> : n}
              </span>
              <span style={{
                fontWeight: state === 'active' ? 600 : 400,
                color: state === 'active' ? 'var(--k-text)' : state === true ? 'var(--k-text-2)' : 'var(--k-text-3)',
              }}>{label}</span>
            </div>
            {i < arr.length - 1 && <span style={{ flex: 1, height: 1, background: 'var(--k-border)' }}/>}
          </React.Fragment>
        ))}
      </div>

      {/* Body — two column */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.4fr 1fr', minHeight: 0 }}>
        {/* Left — tree + templates */}
        <div style={{ borderRight: '1px solid var(--k-border)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: 0, padding: '10px 20px 0', borderBottom: '1px solid var(--k-divider)' }}>
            {[
              ['Источник', true],
              ['Приёмник', false],
              ['EnterpriseData', false],
            ].map(([n, active], i) => (
              <div key={i} style={{
                padding: '8px 14px',
                fontSize: 12,
                color: active ? 'var(--k-text)' : 'var(--k-text-3)',
                borderBottom: active ? '2px solid var(--k-accent)' : '2px solid transparent',
                marginBottom: -1,
                fontWeight: active ? 600 : 400,
                cursor: 'pointer',
              }}>{n}</div>
            ))}
            <span style={{ flex: 1 }}/>
            <div className="k-mono" style={{ fontSize: 10.5, color: 'var(--k-text-3)', alignSelf: 'center', padding: '8px 0' }}>
              УТ 11.5.18.123 · 1247 объектов
            </div>
          </div>

          {/* Tree */}
          <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
            {tree.map((grp, gi) => (
              <div key={gi}>
                <div style={{
                  padding: '6px 16px 4px',
                  display: 'flex', alignItems: 'center', gap: 6,
                  fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em',
                  color: 'var(--k-text-3)', fontWeight: 500,
                }}>
                  <Icon.TriangleDown/>
                  <span>{grp.type}</span>
                  <span className="k-mono" style={{ color: 'var(--k-text-4)', marginLeft: 4 }}>{grp.count}</span>
                </div>
                {grp.items.map((it, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '4px 16px 4px 32px', fontSize: 12,
                    background: it.checked && !it.auto ? 'var(--k-accent-50)' : 'transparent',
                  }}>
                    <span className={`k-checkbox ${it.checked ? 'checked' : ''}`} style={it.auto ? { opacity: 0.55 } : {}}>
                      {it.checked && <Icon.Check style={{ color: 'white' }}/>}
                    </span>
                    <span className="k-mono" style={{ color: it.checked ? 'var(--k-text)' : 'var(--k-text-2)' }}>{it.name}</span>
                    {it.auto && <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--k-text-4)' }}>auto</span>}
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* Templates */}
          <div style={{ borderTop: '1px solid var(--k-divider)', padding: '12px 16px', background: 'var(--k-panel-sunk)' }}>
            <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--k-text-3)', marginBottom: 8, fontWeight: 500 }}>
              Шаблоны
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {templates.map((t, i) => (
                <div key={i} style={{
                  padding: '8px 10px',
                  background: t.active ? 'var(--k-accent-50)' : 'var(--k-panel)',
                  border: `1px solid ${t.active ? 'var(--k-accent)' : 'var(--k-border)'}`,
                  borderRadius: 'var(--k-radius)',
                  fontSize: 11.5,
                  cursor: 'pointer',
                }}>
                  <div style={{ fontWeight: 500, color: t.active ? 'var(--k-accent-text)' : 'var(--k-text)', marginBottom: 2 }}>
                    {t.name}
                  </div>
                  <div style={{ color: 'var(--k-text-3)', fontSize: 10.5, lineHeight: 1.4 }}>{t.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right — selected */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, background: 'var(--k-panel-sunk)' }}>
          <div style={{ padding: '14px 20px 8px' }}>
            <div style={{ fontSize: 12, fontWeight: 600 }}>Корневые объекты</div>
            <div style={{ fontSize: 11, color: 'var(--k-text-3)', marginTop: 2 }}>
              Выбрано: 3 документа + 7 связанных справочников + 1 регистр
            </div>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '4px 12px 12px' }}>
            {selected.map((s, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px',
                background: 'var(--k-panel)',
                border: '1px solid var(--k-divider)',
                borderRadius: 'var(--k-radius)',
                marginBottom: 4,
                fontSize: 11.5,
              }}>
                <span style={{ color: s.root ? 'var(--k-accent)' : 'var(--k-text-3)' }}>
                  <ObjectIcon kind={s.kind}/>
                </span>
                <span className="k-mono">{s.name}</span>
                {s.root && <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--k-accent)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>root</span>}
                {s.auto && !s.root && <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--k-text-4)' }}>auto-depend</span>}
              </div>
            ))}
          </div>
          <div style={{ borderTop: '1px solid var(--k-divider)', padding: '12px 20px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <span className="k-checkbox checked"><Icon.Check style={{ color: 'white' }}/></span>
              Автоматически добавлять связанные объекты по ссылкам
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginTop: 8 }}>
              <span className="k-checkbox"/>
              Только активно используемые объекты
              <span style={{ marginLeft: 4, color: 'var(--k-text-3)', fontSize: 10.5 }}>(требует подключения к базе)</span>
            </label>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '12px 20px',
        borderTop: '1px solid var(--k-border)',
        display: 'flex', alignItems: 'center', gap: 8, background: 'var(--k-panel)',
      }}>
        <button className="k-btn sm">← Назад</button>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost">Отмена</button>
        <button className="k-btn sm primary">Создать проект →</button>
      </div>
    </div>
  );
}

// ============================================================
// Handler Editor
// ============================================================
function HandlerEditor() {
  const code = `// Проверка обязательных полей перед выгрузкой.
// Документ не должен выгружаться без контрагента и организации.

Если ИсходныйОбъект.Контрагент.Пустая() Тогда
    Отказ = Истина;
    ДобавитьСообщение("Не указан контрагент: " + ИсходныйОбъект.Номер);
    Возврат;
КонецЕсли;

Если ИсходныйОбъект.Организация.Пустая() Тогда
    Отказ = Истина;
    ДобавитьСообщение("Не указана организация: " + ИсходныйОбъект.Номер);
    Возврат;
КонецЕсли;

// Преобразование валюты по курсу из регистра.
Если ИсходныйОбъект.Валюта <> Константы.ВалютаРегламентированногоУчёта.Получить() Тогда
    Курс = РегистрыСведений.КурсыВалют.ПолучитьПоследнее(
        ИсходныйОбъект.Дата,
        Новый Структура("Валюта", ИсходныйОбъект.Валюта)
    ).Курс;
    ДополнительныеПараметры.Вставить("Курс", Курс);
КонецЕсли;`;

  // BSL keyword highlighting — split lines manually.
  const keywords = /\b(Если|Тогда|КонецЕсли|Иначе|ИначеЕсли|Возврат|Новый|Пока|Цикл|КонецЦикла|Процедура|Функция|КонецПроцедуры|КонецФункции|Перем|Истина|Ложь)\b/g;
  const comments = /(\/\/[^\n]*)/g;
  const strings = /("[^"]*")/g;
  const numbers = /\b(\d+)\b/g;

  function highlight(src) {
    const lines = src.split('\n');
    return lines.map((ln, i) => {
      let h = ln
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(comments, '<span class="cmt">$1</span>')
        .replace(strings, '<span class="str">$1</span>')
        .replace(keywords, '<span class="kw">$1</span>');
      return { num: i + 1, html: h };
    });
  }

  const hl = highlight(code);

  return (
    <div className="k-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--k-panel)' }}>
      {/* Header */}
      <div style={{
        height: 44, display: 'flex', alignItems: 'center', gap: 10,
        padding: '0 16px',
        borderBottom: '1px solid var(--k-border)',
      }}>
        <Icon.Pen style={{ color: 'var(--k-text-2)' }}/>
        <span style={{ fontSize: 12.5, fontWeight: 500 }}>Handler Editor</span>
        <span style={{ color: 'var(--k-text-4)' }}>·</span>
        <span className="k-mono" style={{ fontSize: 11.5 }}>
          ПередКонвертациейОбъекта
        </span>
        <span style={{ color: 'var(--k-text-4)' }}>·</span>
        <span className="k-mono" style={{ fontSize: 11.5, color: 'var(--k-text-3)' }}>
          Document.РеализацияТоваровУслуг
        </span>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost">Validate syntax</button>
        <button className="k-btn sm ghost icon" title="Detach"><Icon.Arrow/></button>
        <button className="k-btn sm ghost icon"><Icon.X/></button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 360px', minHeight: 0 }}>
        {/* Code editor */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, borderRight: '1px solid var(--k-border)' }}>
          <div style={{
            padding: '6px 12px',
            background: 'var(--k-panel-sunk)',
            borderBottom: '1px solid var(--k-divider)',
            fontSize: 11, color: 'var(--k-text-3)',
            display: 'flex', gap: 12, alignItems: 'center',
          }}>
            <span className="k-mono">BSL · UTF-8 · LF</span>
            <span style={{ flex: 1 }}/>
            <span className="k-mono">Ln 24, Col 12</span>
          </div>
          <div style={{ flex: 1, overflow: 'auto', display: 'flex', fontFamily: 'var(--k-font-mono)', fontSize: 12.5, lineHeight: 1.55 }}>
            <style>{`
              .bsl .kw { color: #7c3aed; font-weight: 500; }
              .bsl .cmt { color: var(--k-text-3); font-style: italic; }
              .bsl .str { color: var(--k-green); }
              .bsl .lnum { color: var(--k-text-4); user-select: none; text-align: right; padding-right: 12px; min-width: 32px; }
            `}</style>
            <div className="bsl" style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', width: '100%', padding: '10px 0' }}>
              {hl.map(({ num, html }) => (
                <React.Fragment key={num}>
                  <div className="lnum">{num}</div>
                  <div style={{ paddingRight: 16, whiteSpace: 'pre' }} dangerouslySetInnerHTML={{ __html: html || '&nbsp;' }}/>
                </React.Fragment>
              ))}
            </div>
          </div>
          {/* Parameters panel */}
          <div style={{ borderTop: '1px solid var(--k-divider)', padding: '8px 12px', background: 'var(--k-panel-sunk)', fontSize: 11 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--k-text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500, marginBottom: 6 }}>
              <Icon.TriangleDown/>
              <span>Параметры обработчика</span>
            </div>
            <div className="k-mono" style={{ fontSize: 11, lineHeight: 1.7, color: 'var(--k-text-2)' }}>
              <div><span style={{ color: 'var(--k-text)' }}>ИсходныйОбъект</span> : <span style={{ color: 'var(--k-text-3)' }}>ДокументОбъект.РеализацияТоваровУслуг</span></div>
              <div><span style={{ color: 'var(--k-text)' }}>ОбъектXDTO</span> : <span style={{ color: 'var(--k-text-3)' }}>XDTOСтруктура · Документ.РеализацияТоваровУслуг</span></div>
              <div><span style={{ color: 'var(--k-text)' }}>Отказ</span> : <span style={{ color: 'var(--k-text-3)' }}>Булево (out)</span></div>
              <div><span style={{ color: 'var(--k-text)' }}>ДополнительныеПараметры</span> : <span style={{ color: 'var(--k-text-3)' }}>Структура</span></div>
            </div>
          </div>
        </div>

        {/* Side panel */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'auto', background: 'var(--k-panel-sunk)' }}>
          {/* AI Assistant */}
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--k-divider)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--k-text-3)', fontWeight: 500, marginBottom: 8 }}>
              <Icon.Sparkle/> AI Assistant
            </div>
            <textarea className="k-textarea" style={{ minHeight: 50, fontSize: 12 }} defaultValue="Добавь проверку, что курс валюты больше нуля, иначе откажи в выгрузке"/>
            <button className="k-btn sm primary" style={{ marginTop: 8, width: '100%' }}>
              <Icon.Sparkle/>Сгенерировать код
            </button>
            <div style={{ marginTop: 12, fontSize: 11, color: 'var(--k-text-3)' }}>История попыток</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, padding: '4px 6px', background: 'var(--k-green-bg)', borderRadius: 4 }}>
                <Icon.Check style={{ color: 'var(--k-green)' }}/>
                <span>попытка 2 · применена</span>
                <span style={{ marginLeft: 'auto', color: 'var(--k-text-3)' }} className="k-mono">3 мин назад</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, padding: '4px 6px', color: 'var(--k-text-3)' }}>
                <Icon.X/>
                <span>попытка 1 · отвергнута</span>
                <span style={{ marginLeft: 'auto' }} className="k-mono">8 мин</span>
              </div>
            </div>
          </div>

          {/* Templates */}
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--k-divider)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--k-text-3)', fontWeight: 500, marginBottom: 8 }}>
              Templates · ПередКонвертацией
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {[
                ['Преобразование валюты по курсу', 'из РегистрСведений.КурсыВалют'],
                ['Обогащение данных контрагента', 'поиск по ИНН в базе ФНС'],
                ['Логирование выгружаемого объекта', 'в РегистрСведений.ЛогОбмена'],
                ['Проверка обязательных полей', 'отказ при пустых required'],
              ].map(([n, d], i) => (
                <div key={i} style={{
                  padding: '7px 9px',
                  background: 'var(--k-panel)',
                  border: '1px solid var(--k-border)',
                  borderRadius: 4,
                  fontSize: 11.5,
                  cursor: 'pointer',
                }}>
                  <div>{n}</div>
                  <div style={{ fontSize: 10.5, color: 'var(--k-text-3)', marginTop: 1 }}>{d}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Context info */}
          <div style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--k-text-3)', fontWeight: 500, marginBottom: 8 }}>
              Контекст
            </div>
            <div className="k-kv" style={{ fontSize: 11.5 }}>
              <span className="k">Объект</span><span className="v mono">Document.Реализация</span>
              <span className="k">Событие</span><span className="v mono">ПередКонвертациейОбъекта</span>
              <span className="k">Сторона</span><span className="v">Источник (выгрузка)</span>
              <span className="k">Mapped fields</span><span className="v mono">12</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 16px',
        borderTop: '1px solid var(--k-border)',
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--k-panel)',
      }}>
        <span className="k-mono" style={{ fontSize: 11, color: 'var(--k-text-3)' }}>● изменения не сохранены</span>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost">Отмена</button>
        <button className="k-btn sm primary">Save <span className="k-kbd" style={{ marginLeft: 4 }}>⌘S</span></button>
      </div>
    </div>
  );
}

// ============================================================
// Diff View
// ============================================================
function DiffView() {
  const changes = [
    { type: 'add', what: 'Реализация.Скидка → СкидкиНаценки.Сумма', detail: 'auto-name match' },
    { type: 'add', what: 'Реализация.КодОперации → ВидОперации', detail: 'AI suggestion' },
    { type: 'add', what: 'Контрагент.СтраницаСайта → URL', detail: 'manual' },
    { type: 'add', what: 'Договор.ВалютаРасчётов → Валюта', detail: 'auto' },
    { type: 'add', what: 'Реализация.Подразделение → Подразделение', detail: 'auto' },
    { type: 'remove', what: 'Реализация.Комментарий → Примечание', detail: 'был неточный mapping' },
    { type: 'remove', what: 'Договор.ДатаОкончания → ДатаЗавершения', detail: 'removed by user' },
    { type: 'change', what: 'Реализация.Сумма', from: 'СуммаДок', to: 'Сумма', detail: 'reassigned' },
    { type: 'change', what: 'Контрагент', from: 'PoGUID', to: 'ИНН+КПП', detail: 'search strategy' },
    { type: 'change', what: 'Реализация.Курс', from: 'green (auto)', to: 'amber (AI)', detail: 'confidence dropped' },
  ];

  return (
    <div className="k-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--k-panel)' }}>
      {/* Header */}
      <div style={{
        height: 44, display: 'flex', alignItems: 'center', gap: 10, padding: '0 16px',
        borderBottom: '1px solid var(--k-border)',
      }}>
        <span style={{ fontSize: 12.5, fontWeight: 600 }}>Diff View</span>
        <span style={{ color: 'var(--k-text-4)' }}>·</span>
        <span className="k-mono" style={{ fontSize: 11.5, color: 'var(--k-text-3)' }}>Обмен УТ 11.5 ↔ БП 3.0</span>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost icon"><Icon.X/></button>
      </div>

      {/* Compare bar */}
      <div style={{
        padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10, fontSize: 12,
        background: 'var(--k-panel-sunk)', borderBottom: '1px solid var(--k-divider)',
      }}>
        <span style={{ color: 'var(--k-text-3)' }}>Сравнить</span>
        <button className="k-btn sm">
          <span className="k-mono">2026-05-15 14:30</span> <Icon.TriangleDown/>
        </button>
        <span style={{ color: 'var(--k-text-4)' }}>с</span>
        <button className="k-btn sm">
          <span className="k-mono">Current</span> <Icon.TriangleDown/>
        </button>
        <span style={{ color: 'var(--k-text-4)' }}>·</span>
        <span className="k-mono" style={{ fontSize: 11, color: 'var(--k-text-3)' }}>
          +5 added · −2 removed · ~3 changed
        </span>
        <span style={{ flex: 1 }}/>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--k-text-2)' }}>
          <span className="k-checkbox checked"><Icon.Check style={{ color: 'white' }}/></span>
          Скрыть неизменённые
        </label>
      </div>

      {/* Body — two panes */}
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '340px 1fr', minHeight: 0 }}>
        {/* Changes list */}
        <div style={{ borderRight: '1px solid var(--k-border)', overflow: 'auto' }}>
          {[
            { type: 'add', count: 5, color: 'var(--k-green)', sign: '+' },
            { type: 'remove', count: 2, color: 'var(--k-red)', sign: '−' },
            { type: 'change', count: 3, color: 'var(--k-amber)', sign: '~' },
          ].map((grp, gi) => (
            <div key={gi}>
              <div style={{
                padding: '8px 16px', display: 'flex', gap: 6, fontSize: 11,
                textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--k-text-3)',
                background: 'var(--k-panel-sunk)', fontWeight: 500,
              }}>
                <Icon.TriangleDown/>
                <span style={{ color: grp.color, fontWeight: 600 }}>{grp.sign}</span>
                <span>{grp.type === 'add' ? 'Added' : grp.type === 'remove' ? 'Removed' : 'Changed'}</span>
                <span className="k-mono" style={{ color: 'var(--k-text-4)', marginLeft: 'auto' }}>{grp.count}</span>
              </div>
              {changes.filter(c => c.type === grp.type).map((c, i) => (
                <div key={i} style={{
                  padding: '7px 16px 7px 22px',
                  borderBottom: '1px solid var(--k-divider)',
                  fontSize: 11.5, cursor: 'pointer',
                  background: gi === 2 && i === 0 ? 'var(--k-amber-bg)' : 'transparent',
                }}>
                  <div className="k-mono" style={{ color: 'var(--k-text)', lineHeight: 1.4 }}>{c.what}</div>
                  {c.type === 'change' && (
                    <div className="k-mono" style={{ fontSize: 10.5, color: 'var(--k-text-3)', marginTop: 2 }}>
                      <span style={{ textDecoration: 'line-through' }}>{c.from}</span>
                      <span style={{ margin: '0 6px' }}>→</span>
                      <span style={{ color: 'var(--k-amber)' }}>{c.to}</span>
                    </div>
                  )}
                  <div style={{ fontSize: 10.5, color: 'var(--k-text-4)', marginTop: 2 }}>{c.detail}</div>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Mapping diff visual */}
        <div style={{ position: 'relative', background: 'var(--k-panel-sunk)', overflow: 'auto' }}>
          <DiffMappingVisual/>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 16px',
        borderTop: '1px solid var(--k-border)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span className="k-mono" style={{ fontSize: 11, color: 'var(--k-text-3)' }}>10 changes · 5 hours apart</span>
        <span style={{ flex: 1 }}/>
        <button className="k-btn sm ghost">Cherry-pick changes…</button>
        <button className="k-btn sm">Restore this version</button>
        <button className="k-btn sm primary">Close</button>
      </div>
    </div>
  );
}

function DiffMappingVisual() {
  // Compact 3-pane visualization with diff-colored lines.
  const items = [
    { l: 'Дата', m: 'Дата', r: 'Дата', status: 'unchanged' },
    { l: 'Контрагент', m: 'Контрагент', r: 'Контрагент', status: 'unchanged' },
    { l: 'Сумма', m: 'Сумма', r: 'СуммаДок→Сумма', status: 'change', rOld: 'СуммаДок' },
    { l: 'Курс', m: 'КурсВалюты', r: 'КурсДокумента', status: 'change-conf' },
    { l: 'Скидка', m: 'СкидкиНаценки', r: 'Скидка', status: 'add' },
    { l: 'КодОперации', m: 'ВидОперации', r: 'ВидОперации', status: 'add' },
    { l: 'Подразделение', m: 'Подразделение', r: 'Подразделение', status: 'add' },
    { l: 'Комментарий', m: 'Примечание', r: '—', status: 'remove' },
  ];
  const colorFor = (s) => s === 'add' ? 'var(--k-green)' :
                         s === 'remove' ? 'var(--k-red)' :
                         s === 'change' || s === 'change-conf' ? 'var(--k-amber)' :
                         'var(--k-text-4)';

  return (
    <div style={{ padding: '16px 20px', height: '100%' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0, position: 'relative', background: 'var(--k-panel)', border: '1px solid var(--k-border)', borderRadius: 'var(--k-radius-md)', overflow: 'hidden' }}>
        {['Source · УТ 11.5', 'EnterpriseData', 'Target · БП 3.0'].map((c, i) => (
          <div key={i} style={{
            padding: '8px 12px',
            background: 'var(--k-panel-sunk)',
            borderRight: i < 2 ? '1px solid var(--k-divider)' : 'none',
            borderBottom: '1px solid var(--k-divider)',
            fontSize: 11, color: 'var(--k-text-2)',
            textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500,
          }}>{c}</div>
        ))}
        {items.map((it, i) => (
          <React.Fragment key={i}>
            <div style={{
              padding: '7px 12px',
              borderRight: '1px solid var(--k-divider)',
              borderBottom: i < items.length - 1 ? '1px solid var(--k-divider)' : 'none',
              fontFamily: 'var(--k-font-mono)', fontSize: 11.5,
              opacity: it.status === 'remove' ? 0.5 : 1,
              textDecoration: it.status === 'remove' ? 'line-through' : 'none',
            }}>
              <span style={{ color: colorFor(it.status), marginRight: 6 }}>
                {it.status === 'add' ? '+' : it.status === 'remove' ? '−' : it.status.startsWith('change') ? '~' : '·'}
              </span>
              {it.l}
            </div>
            <div style={{
              padding: '7px 12px',
              borderRight: '1px solid var(--k-divider)',
              borderBottom: i < items.length - 1 ? '1px solid var(--k-divider)' : 'none',
              fontFamily: 'var(--k-font-mono)', fontSize: 11.5,
              color: 'var(--k-text-2)',
              opacity: it.status === 'remove' ? 0.5 : 1,
            }}>{it.m}</div>
            <div style={{
              padding: '7px 12px',
              borderBottom: i < items.length - 1 ? '1px solid var(--k-divider)' : 'none',
              fontFamily: 'var(--k-font-mono)', fontSize: 11.5,
              opacity: it.status === 'remove' ? 0.5 : 1,
              textDecoration: it.status === 'remove' ? 'line-through' : 'none',
            }}>
              {it.status === 'change' ? (
                <span>
                  <span style={{ textDecoration: 'line-through', color: 'var(--k-text-3)' }}>{it.rOld}</span>
                  <span style={{ color: colorFor(it.status), margin: '0 6px' }}>→</span>
                  <span>{it.r.replace(it.rOld + '→', '')}</span>
                </span>
              ) : it.r}
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// ============================================================
// Command Palette overlay
// ============================================================
function CommandPalette() {
  const items = [
    { type: 'recent', icon: <Icon.Doc/>, name: 'Document.РеализацияТоваровУслуг', meta: 'Object · 22/22 mapped' },
    { type: 'recent', icon: <Icon.Cat/>, name: 'Catalog.Контрагенты', meta: 'Object · 8/8' },
    { type: 'cmd', icon: <Icon.Sparkle/>, name: 'Re-run AI auto-mapping for current object', meta: 'Command', kbd: '⌘⇧M' },
    { type: 'cmd', icon: <Icon.Check/>, name: 'Run validation', meta: 'Command', kbd: '⌘⇧V' },
    { type: 'cmd', icon: null, name: 'Save snapshot with name…', meta: 'Command', kbd: '⌘⇧S' },
    { type: 'cmd', icon: null, name: 'Export rules…', meta: 'Command', kbd: '⌘E' },
    { type: 'cmd', icon: null, name: 'Toggle Bottom Dock', meta: 'View' },
    { type: 'cmd', icon: null, name: 'Show diff with previous version', meta: 'Command' },
  ];

  return (
    <div className="k-app" style={{
      height: '100%', width: '100%',
      background: 'rgba(15, 15, 20, 0.35)',
      display: 'grid', placeItems: 'center',
      padding: 40,
    }}>
      <div style={{
        width: 600,
        background: 'var(--k-panel)',
        borderRadius: 'var(--k-radius-lg)',
        boxShadow: 'var(--k-shadow-lg)',
        overflow: 'hidden',
        border: '1px solid var(--k-border)',
      }}>
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--k-divider)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <Icon.Search/>
          <span className="k-mono" style={{ fontSize: 14, color: 'var(--k-text)' }}>map контра</span>
          <span style={{ width: 1, height: 16, background: 'var(--k-text)', animation: 'k-blink 1s steps(1) infinite' }}/>
          <span style={{ flex: 1 }}/>
          <span className="k-kbd">esc</span>
        </div>
        <div style={{ padding: 6 }}>
          <div style={{ padding: '4px 12px', fontSize: 10.5, color: 'var(--k-text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500 }}>
            Recent
          </div>
          {items.filter(i => i.type === 'recent').map((it, i) => (
            <CommandRow key={i} {...it} active={i === 0}/>
          ))}
          <div style={{ padding: '8px 12px 4px', fontSize: 10.5, color: 'var(--k-text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500 }}>
            Commands
          </div>
          {items.filter(i => i.type === 'cmd').map((it, i) => (
            <CommandRow key={i} {...it}/>
          ))}
        </div>
        <div style={{
          padding: '8px 16px',
          borderTop: '1px solid var(--k-divider)',
          background: 'var(--k-panel-sunk)',
          display: 'flex', gap: 14, fontSize: 11, color: 'var(--k-text-3)',
        }}>
          <span><span className="k-kbd">↑↓</span> навигация</span>
          <span><span className="k-kbd">↵</span> выбрать</span>
          <span><span className="k-kbd">⌘K</span> очистить</span>
        </div>
      </div>
      <style>{`@keyframes k-blink { 50% { opacity: 0 } }`}</style>
    </div>
  );
}

function CommandRow({ icon, name, meta, kbd, active }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '7px 12px',
      borderRadius: 'var(--k-radius)',
      background: active ? 'var(--k-accent-50)' : 'transparent',
      color: active ? 'var(--k-text)' : 'var(--k-text)',
      fontSize: 12,
    }}>
      {icon ? <span style={{ color: active ? 'var(--k-accent)' : 'var(--k-text-3)' }}>{icon}</span> : <span style={{ width: 14 }}/>}
      <span className="k-mono" style={{ flex: 1 }}>{name}</span>
      <span style={{ color: 'var(--k-text-3)', fontSize: 10.5 }}>{meta}</span>
      {kbd && <span className="k-kbd">{kbd}</span>}
    </div>
  );
}

Object.assign(window, { ProjectPicker, WizardStep4, HandlerEditor, DiffView, CommandPalette });
