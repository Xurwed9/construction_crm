# Lead Management — Архитектураи модул

## 1. Сохтори папкаҳо

Лоиҳа ба қабатҳо ҷудо шудааст (layered architecture):

```
construction_crm/
├── app/
│   ├── api/v1/endpoints/     → Рутерҳои HTTP (қабати веб)
│   │   ├── auth.py           → Авторизатсия (мавҷуда)
│   │   ├── users.py          → Корбарон (мавҷуда)
│   │   ├── matrix.py         → Матритсаи хонаҳо (мавҷуда)
│   │   └── leads.py          → Модули Lead Management (нав)
│   ├── models/               → Моделҳои SQLAlchemy (қабати дода)
│   │   └── lead.py           → Lead, LeadNote, LeadTimeline (нав)
│   ├── schemas/              → Схемаҳои Pydantic v2 (қабати тасдиқ)
│   │   └── lead.py           → LeadCreate, LeadRead, ... (нав)
│   ├── repositories/         → Логикаи пойгоҳи додаҳо (SQL)
│   │   └── lead.py           → LeadRepository, LeadNoteRepository, ... (нав)
│   ├── services/             → Логикаи тиҷоратӣ
│   │   └── lead.py           → LeadService (нав)
│   ├── permissions/          → Ҳуқуқҳои дастрасӣ
│   │   └── roles.py          → LEADS_CREATE, LEADS_VIEW, ... (нав)
│   ├── dependencies/         → Тобеъиятҳои FastAPI
│   ├── core/                 → Config, Database, Exceptions
│   └── main.py               → Насби FastAPI ва рутерҳо
├── alembic/versions/         → Мигратсияҳои пойгоҳи додаҳо
│   └── 006_create_lead_management.py  (нав)
├── tests/
│   └── test_leads.py         → Тестҳои модули Lead (нав)
├── learning.md               → Дастури омӯзишӣ (тоҷикӣ)
└── architecture.md           → Ин ҳуҷҷат
```

## 2. Ҷараёни дода (Data Flow)

Додаҳо дар ин тартиб ҳаракат мекунанд:

```
HTTP Request (JSON)
       ↓
Router (leads.py)
   ├── Параметрҳоро мегирад
   ├── Ҳуқуқҳоро тафтиш мекунад (require_permission)
   ↓
Service (lead.py)
   ├── Логикаи тиҷоратӣ
   ├── Санҷиши мансубият (менеҷер ↔ лидҳои худаш)
   ├── Санҷиши гузариши статус
   ├── Эҷоди таймлайн
   ↓
Repository (lead.py)
   ├── SQL queries
   ├── Филтр, тартиб, саҳифабандӣ
   ↓
PostgreSQL / SQLite
```

### Мисоли пурра: Тағйири статус

```
1. Клиент: PATCH /api/v1/leads/{id}/status  {"status": "first_call"}
2. Router: ҳуқуқи LEADS_MOVE-ро тафтиш мекунад
3. Service: лидро мегирад, мансубиятро месанҷад
4. Service: гузаришро месанҷад (new → first_call = имконпазир)
5. Repository: статусро нав мекунад
6. Service: ба таймлайн вуруди "status_changed" меиловад
7. Клиент: 200 OK бо лиди навшуда
```

## 3. Давраи ҳаёти лид (Lead Lifecycle)

Лид аз сар то охир тарҳи фурӯшро тай мекунад:

```
new → first_call → consultation → office_visit → presentation
   → decision → reservation → contract → payment → completed

Ҳар ҷо → lost (гумшуда)
lost → new (эҳё)
```

1. **new** — лид ворид шуд (аз Instagram, телефон, сайт)
2. **first_call** — занг зада шуд
3. **consultation** — машварат дод шуд
4. **office_visit** — офисро ташриф овард
5. **presentation** — презентатсияи лоиҳа
6. **decision** — қабули қарор
7. **reservation** — банд кардани хона
8. **contract** — бастани шартнома
9. **payment** — пардохт
10. **completed** — муомилаи пурра анҷом ёфт

Ҳар қадам дар таймлайн сабт мешавад. Лидро аз ҳар ҷо ба **lost** бурдан мумкин аст, ва аз **lost** ба **new** эҳё кардан.

## 4. Интегратсияи оянда

Модули Lead ба тавре сохта шудааст, ки барои интегратсия бо дигар модулҳо омода аст:

### Apartment Matrix (Матритсаи хонаҳо)
- Майдонҳои `project_id`, `building_id`, `apartment_id` аллакай дар модел мавҷуданд
- Санҷиши мавҷудияти лоиҳа/бино/хона ҳангоми эҷод аллакай кор мекунад
- Оянда: вақте лид ба `reservation` меравад, ҳолати хонаро ба `reserved` тағйир додан мумкин
- Оянда: аз канбан хонаи дастрасро бевосита интихоб кардан

### Reservations (Бандкуниҳо)
- Статуси `reservation` аллакай дар тарҳи фурӯш мавҷуд аст
- Оянда: ҳангоми гузариш ба `reservation` сабти нави бандкунӣ эҷод карда мешавад
- Оянда: вақте бандкунӣ бекор мешавад, лид автоматикӣ ба `decision` бармегардад

### Deals (Муомилаҳо)
- Ҷадвали `apartments` аллакай сутуни `deal_id` дорад
- Оянда: лид → deal → хона пайваст мешавад
- Оянда: маблағи лид (`budget`) ба deal интиқол меёбад

### Contracts (Шартномаҳо)
- Статуси `contract` аллакай дар тарҳи фурӯш мавҷуд аст
- Оянда: ҳангоми гузариш ба `contract`, шартномаи нав эҷод мешавад
- Оянда: дар таймлайни лид вуруди "Contract Created" пайдо мешавад

### Payments (Пардохтҳо)
- Статуси `payment` аллакай дар тарҳи фурӯш мавҷуд аст
- Оянда: ҳангоми пардохти аввал, лид ба `payment` меравад
- Оянда: ба таймлайн вуруди "Payment Received" илова мешавад

## 5. Таймлайн ҳамчун Activity Log

Ҷадвали `lead_timelines` ҳамчун логги автоматии ҳама амалҳо хидмат мекунад:

- Ҳар эҷод/таҳрир/ҳазф → сабт
- Ҳар тағйири статус → сабт
- Ҳар таъини менеҷер → сабт
- Ҳар нота → сабт

Ин барои ҳисоботдиҳӣ (audit) ва фаҳмидани таърихи ҳар лид кӯмак мекунад.

## 6. Қарорҳои асосии техникӣ

| Масъала | Қарор |
|---------|-------|
| Калиди асосӣ | UUID (барои ҳамаи моделҳо) |
| Статусҳо | Enum бо арзишҳои lowercase |
| Ҳазфи лид | Soft delete (`deleted_at`) барои нигоҳ доштани таърих |
| Мансубият | Менеҷер танҳо `assigned_manager_id == actor.id` |
| Тартиби афзалият | CASE-тартиб: urgent → high → medium → low |
| Таърихи амалҳо | Ҷадвали алоҳидаи `lead_timelines` |
| Мигратсия | Alembic (006) |
| Тасдиқ | Pydantic v2: телефон, почта, бюджет, статус, афзалият |
