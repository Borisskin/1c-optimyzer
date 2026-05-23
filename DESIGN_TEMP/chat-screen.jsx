/* Main chat workspace screen */

const Sidebar = ({ activeBaseId = "erp", activeHistory = 0 }) => {
  const bases = [
    { id: "erp", icon: "ERP", name: "ERP Производство v4.2", status: "green", sub: "Индекс актуален • 47 мин", active: true },
    { id: "buh", icon: "БП", name: "Бухгалтерия 3.0 — Клиент А", status: "gray", sub: "Не подключено" },
    { id: "utm", icon: "УТ", name: "Управление торговлей 11.5", status: "amber", sub: "Индексация • 62%" },
    { id: "zup", icon: "ЗУП", name: "ЗУП КОРП v3.1", status: "green", sub: "Индекс актуален • 3 ч" },
  ];
  const history = [
    { text: "Добавь в РеализациюТоваровУслуг учёт серий номенклатуры", time: "сейчас", active: true },
    { text: "Регистр накопления по партиям с FIFO-списанием", time: "32 мин" },
    { text: "Отчёт по дебиторской задолженности с фильтром по контрагенту", time: "вчера" },
    { text: "Расширение — экспорт документов в формате УПД 5.03", time: "вчера" },
    { text: "Обработка для массовой перепроведения за период", time: "12 апр" },
    { text: "Право на просмотр себестоимости только для финдира", time: "10 апр" },
  ];
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"></div>
        <div className="brand-name">Agenter</div>
        <div className="brand-version">v0.9.4</div>
      </div>

      <div className="side-section">
        <div className="side-section-header">
          <div className="side-label">Мои базы</div>
          <div className="side-count">{bases.length}</div>
        </div>
        {bases.map(b => (
          <div key={b.id} className={`base-card ${b.id === activeBaseId ? "active" : ""}`}>
            <div className="base-icon">{b.icon}</div>
            <div className="base-meta">
              <div className="base-name">{b.name}</div>
              <div className="base-sub">
                <span className={`dot ${b.status}`}></span>
                <span>{b.sub}</span>
              </div>
            </div>
          </div>
        ))}
        <button className="add-base">
          <Icon name="plus" size={13} />
          <span>Подключить новую базу</span>
        </button>
      </div>

      <div className="divider"></div>

      <div className="side-section" style={{ flex: 1, overflow: "auto", paddingBottom: 8 }}>
        <div className="side-section-header">
          <div className="side-label">История задач</div>
          <Icon name="history" size={12} className="ic-sm" />
        </div>
        <div className="history-list">
          {history.map((h, i) => (
            <div key={i} className={`history-item ${h.active ? "active" : ""}`}>
              <div className="history-text">{h.text}</div>
              <div className="history-time">{h.time}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="avatar">ДК</div>
        <div className="user-meta">
          <div className="user-name">Дмитрий К.</div>
          <div className="user-org">Франчайзи · Северо-Запад</div>
        </div>
        <div style={{ marginLeft: "auto" }}>
          <Icon name="settings" size={14} className="ic" style={{ color: "var(--text-3)" }} />
        </div>
      </div>
    </aside>
  );
};

const ExecLog = ({ rows, runningIndex }) => {
  return (
    <div className="exec-log">
      <div className="exec-log-head">
        <Icon name="terminal" size={13} className="ic" style={{ color: "var(--text-2)" }} />
        <div className="exec-title">Выполнение задачи</div>
        <div className={`exec-state ${runningIndex < rows.length - 1 ? "running" : ""}`}>
          <span className="pulse"></span>
          <span>{runningIndex < rows.length - 1 ? "RUNNING" : "COMPLETED"}</span>
        </div>
      </div>
      <div className="exec-rows">
        {rows.map((r, i) => {
          const status = i < runningIndex ? "done" : i === runningIndex ? "active" : "pending";
          return (
            <div key={i}
                 className={`exec-row ${status}`}
                 style={{ animationDelay: `${i * 120}ms` }}>
              <span className="ts">[{r.ts}]</span>
              <span className="marker"></span>
              <span className="text">{r.text}</span>
              <span className="meta">{r.meta || ""}</span>
            </div>
          );
        })}
      </div>
      <div className="exec-foot">
        <span>extension://CЕРИИ_НОМЕНКЛАТУРЫ.cfe</span>
        <span style={{ marginLeft: "auto" }} className="ok">
          <span className="check"><Icon name="check" size={8} /></span>
          12 объектов · 4.2с
        </span>
      </div>
    </div>
  );
};

const ChatScreen = () => {
  const logRows = [
    { ts: "09:41:02", text: "Анализ структуры документа РеализацияТоваровУслуг", meta: "1.2с" },
    { ts: "09:41:08", text: "Поиск зависимостей по сериям номенклатуры", meta: "0.8с" },
    { ts: "09:41:14", text: "Создание реквизита СерияНоменклатуры", meta: "СправочникСсылка" },
    { ts: "09:41:21", text: "Модификация формы документа и печатной формы УПД", meta: "2 формы" },
    { ts: "09:41:34", text: "Валидация BSL-кода расширения", meta: "0 errors" },
    { ts: "09:41:39", text: "Загрузка расширения в тестовую базу через десктоп-ассистент", meta: "✓" },
  ];

  return (
    <div className="workspace" data-screen-label="01 Chat workspace">
      <Sidebar />
      <main className="main">
        <div className="topbar">
          <div className="crumbs">
            <Icon name="database" size={14} className="ic" style={{ color: "var(--text-3)" }} />
            <strong>ERP Производство v4.2</strong>
            <span className="crumb-sep">/</span>
            <span>main</span>
            <span className="crumb-sep">/</span>
            <span>Серии номенклатуры</span>
          </div>
          <div className="index-status">
            <span className="dot"></span>
            <span>Индекс актуален · 47 мин назад</span>
          </div>
          <div className="topbar-spacer"></div>
          <button className="btn">
            <Icon name="refresh" size={13} className="ic" />
            <span>Переиндексировать</span>
          </button>
          <button className="icon-btn"><Icon name="more" size={14} /></button>
        </div>

        <div className="chat">
          <div className="chat-scroll">
            <div className="chat-inner">
              <div className="session-meta">сессия #4821 · 04 мая 2026 · 09:41 МСК</div>

              <div className="msg user">
                <div className="bubble">
                  Добавь в документ <code style={{ background: "rgba(255,255,255,0.5)", border: "1px solid rgba(37,99,235,0.15)" }}>РеализацияТоваровУслуг</code> возможность указывать серию номенклатуры с контролем остатков по сериям и выводом в печатную форму УПД.
                </div>
              </div>

              <div className="msg agent">
                <div className="agent-avatar"></div>
                <div className="agent-body">
                  <div className="agent-head">
                    <span className="agent-name">Agenter</span>
                    <span className="agent-time">09:41 · ERP Производство v4.2</span>
                  </div>
                  <div className="agent-text">
                    <p>Принял задачу. Проверил конфигурацию — справочник <code>СерииНоменклатуры</code> уже существует, но не подключен к документу. Подготавливаю расширение, ничего в типовой конфигурации не меняю.</p>
                  </div>
                  <ExecLog rows={logRows} runningIndex={logRows.length - 1} />

                  <div className="final-summary">
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      <span style={{ width: 18, height: 18, borderRadius: "50%", background: "var(--success)", color: "#fff", display: "grid", placeItems: "center" }}>
                        <Icon name="check" size={11} />
                      </span>
                      <strong style={{ fontFamily: "var(--font-display)", fontSize: 13.5 }}>Готово. Изменения применены.</strong>
                    </div>
                    <div>
                      Расширение <code>СЕРИИ_НОМЕНКЛАТУРЫ.cfe</code> загружено в тестовую базу. Модифицированы: форма документа, печатная форма УПД, регистр накопления <code>ОстаткиТоваровПоСериям</code>. Откройте документ <code>РеализацияТоваровУслуг</code> и проверьте — если что-то нужно скорректировать, напишите в чат.
                    </div>
                    <div className="summary-actions">
                      <button className="chip primary"><Icon name="play" size={11} /> Открыть в 1С</button>
                      <button className="chip"><Icon name="code" size={11} /> Посмотреть код</button>
                      <button className="chip"><Icon name="download" size={11} /> Скачать .cfe</button>
                      <button className="chip"><Icon name="branch" size={11} /> Создать ветку</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="composer-wrap">
            <div className="composer-inner">
              <div className="composer">
                <div className="composer-input" contentEditable suppressContentEditableWarning data-placeholder="Опишите задачу или уточнение…">
                  Проверь, чтобы при проведении документа списание шло по FIFO внутри выбранной серии…
                </div>
                <div className="composer-bar">
                  <div className="composer-tag">
                    <span className="dot green"></span>
                    <span>ERP Производство v4.2</span>
                  </div>
                  <button className="icon-btn" title="Прикрепить"><Icon name="paperclip" size={14} /></button>
                  <button className="icon-btn" title="Скриншот"><Icon name="image" size={14} /></button>
                  <button className="icon-btn" title="Код"><Icon name="code" size={14} /></button>
                  <div className="composer-spacer"></div>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--text-4)", marginRight: 8 }}>Ctrl+Enter</span>
                  <button className="send-btn primary">
                    <Icon name="send" size={12} />
                    Отправить
                  </button>
                </div>
              </div>
              <div className="composer-hints">
                <span className="hint-chip">/ команды</span>
                <span className="hint-chip">@объект конфигурации</span>
                <span className="hint-chip">↑ редактировать последний</span>
                <span className="hint-chip">⇧⏎ перенос</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      <RightPanel />
    </div>
  );
};

const RightPanel = () => {
  const changes = [
    { tag: "+", tagClass: "tag-add", text: "Реквизит СерияНоменклатуры", time: "09:41" },
    { tag: "~", tagClass: "tag-mod", text: "Форма документа РТУ", time: "09:41" },
    { tag: "+", tagClass: "tag-add", text: "РН ОстаткиТоваровПоСериям", time: "09:41" },
    { tag: "~", tagClass: "tag-mod", text: "ПечатнаяФорма_УПД", time: "09:41" },
    { tag: "+", tagClass: "tag-add", text: "Подписка ПриПроведенииРТУ", time: "09:41" },
  ];

  return (
    <aside className="rightbar">
      <div className="rb-section">
        <div className="rb-head">
          <div className="rb-title">Десктоп-ассистент</div>
          <span className="rb-action">Настройки</span>
        </div>
        <div className="assistant-card">
          <div className="assistant-row">
            <div className="host-icon"><Icon name="terminal" size={14} className="ic" /></div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="assistant-name">
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--success)", boxShadow: "0 0 0 3px rgba(16,185,129,0.18)" }}></span>
                Подключён
              </div>
              <div className="assistant-meta">v1.4.2 · ping 12ms · WIN-DEV-04</div>
            </div>
          </div>
          <div className="stat-grid">
            <div className="stat">
              <div className="stat-label">База</div>
              <div className="stat-value" style={{ fontSize: 11.5 }}>ERP Произв.</div>
            </div>
            <div className="stat">
              <div className="stat-label">Платформа</div>
              <div className="stat-value">8.3.24</div>
            </div>
          </div>
        </div>
      </div>

      <div className="rb-section">
        <div className="rb-head">
          <div className="rb-title">Последние изменения</div>
          <span className="rb-action">Журнал</span>
        </div>
        <div className="changes-list">
          {changes.map((c, i) => (
            <div key={i} className="change-row">
              <span className={`change-tag ${c.tagClass}`}>{c.tag}</span>
              <span className="change-text">{c.text}</span>
              <span className="change-time">{c.time}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rb-section">
        <div className="rb-head">
          <div className="rb-title">Быстрые команды</div>
          <Icon name="zap" size={11} className="ic-sm" style={{ color: "var(--text-3)" }} />
        </div>
        <div className="quick-grid">
          <div className="quick-row">
            <div className="quick-icon"><Icon name="file" size={13} className="ic-sm" style={{ color: "var(--text-2)" }} /></div>
            <div className="quick-text">
              <div className="quick-title">Отчёт по доработкам</div>
              <div className="quick-sub">Markdown за период</div>
            </div>
            <span className="quick-key">⌘R</span>
          </div>
          <div className="quick-row">
            <div className="quick-icon"><Icon name="shield" size={13} className="ic-sm" style={{ color: "var(--text-2)" }} /></div>
            <div className="quick-text">
              <div className="quick-title">Создать бэкап базы</div>
              <div className="quick-sub">~12 мин · 4.8 ГБ</div>
            </div>
            <span className="quick-key">⌘B</span>
          </div>
          <div className="quick-row">
            <div className="quick-icon"><Icon name="user" size={13} className="ic-sm" style={{ color: "var(--text-2)" }} /></div>
            <div className="quick-text">
              <div className="quick-title">Запросить помощь эксперта</div>
              <div className="quick-sub">Среднее время ответа · 38 мин</div>
            </div>
            <span className="quick-key">⌘E</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

window.ChatScreen = ChatScreen;
