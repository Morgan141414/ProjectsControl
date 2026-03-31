# ТЕХНИЧЕСКОЕ ЗАДАНИЕ
## Платформа «ProjectsControl»
### Версия 2.0 | Февраль 2026

---

## СОДЕРЖАНИЕ

1. [Общая информация о проекте](#1-общая-информация-о-проекте)
2. [Текущий технологический стек](#2-текущий-технологический-стек)
3. [Модуль авторизации и аутентификации](#3-модуль-авторизации-и-аутентификации)
4. [Модуль компаний / организаций](#4-модуль-компаний--организаций)
5. [Модуль штабов / отделов](#5-модуль-штабов--отделов)
6. [Модуль найма сотрудников (hh-функционал)](#6-модуль-найма-сотрудников-hh-функционал)
7. [Система ролей и полномочий](#7-система-ролей-и-полномочий)
8. [Модуль технической поддержки](#8-модуль-технической-поддержки)
9. [Аналитика и статистика](#9-аналитика-и-статистика)
10. [Рейтинговая система](#10-рейтинговая-система)
11. [Монетизация](#11-монетизация)
12. [Тарифные планы](#12-тарифные-планы)
13. [Модуль видеозвонков](#13-модуль-видеозвонков)
14. [Сводная таблица статусов](#14-сводная-таблица-статусов)
15. [Дорожная карта реализации](#15-дорожная-карта-реализации)

---

## 1. ОБЩАЯ ИНФОРМАЦИЯ О ПРОЕКТЕ

### 1.1. Назначение

**ProjectsControl** — корпоративная платформа управления проектами, мониторинга продуктивности сотрудников и аналитики с использованием искусственного интеллекта. Платформа позволяет компаниям организовывать рабочие процессы, отслеживать активность сотрудников в реальном времени, получать AI-оценки продуктивности и управлять задачами.

### 1.2. Архитектура

| Компонент | Технология | Описание |
|-----------|-----------|----------|
| **Backend** | FastAPI 0.115.0 + Python 3.13 | REST API сервер |
| **Frontend** | PySide6 6.7.2 (Qt) | Нативное десктопное приложение |
| **ML-модуль** | scikit-learn + Anthropic Claude API | AI-анализ и валидация |
| **БД** | SQLite (dev) / PostgreSQL (prod) | Хранение данных |
| **ORM** | SQLAlchemy 2.0.36 | Работа с базой данных |

### 1.3. Текущая структура проекта

```
ProjectsControl/
├── backend/                    # FastAPI серверная часть
│   ├── app/
│   │   ├── api/routes/         # 20 роутеров API (80+ эндпоинтов)
│   │   ├── core/               # Ядро: безопасность, конфиг, планировщик
│   │   ├── db/                 # Подключение к БД
│   │   ├── models/             # 14 моделей SQLAlchemy
│   │   ├── schemas/            # Pydantic-схемы валидации
│   │   └── utils/              # Утилиты (ID, коды)
│   ├── data/                   # SQLite файл БД
│   ├── scripts/                # Сид-скрипт
│   └── tests/                  # Тесты (smoke + AI)
├── frontend/                   # PySide6 десктоп-клиент
│   ├── app/
│   │   ├── ui/
│   │   │   ├── main_window.py  # Главное окно с навигацией
│   │   │   └── screens/        # 18 экранов интерфейса
│   │   ├── services/           # API-клиент (80+ методов)
│   │   ├── state/              # Управление сессией
│   │   └── resources/          # Стили (3 темы)
│   └── requirements.txt
├── ML/                         # ML-микросервис
│   ├── api.py                  # FastAPI эндпоинты ML
│   ├── screenshot_analyzer.py  # AI-анализ скриншотов
│   ├── questionnaire_validator.py  # Валидация анкет
│   └── requirements.txt
├── start-all.ps1               # Скрипт запуска
└── launch-frontend.ps1         # Запуск фронтенда
```

---

## 2. ТЕКУЩИЙ ТЕХНОЛОГИЧЕСКИЙ СТЕК

### 2.1. Backend — что есть и что умеет

| Технология | Версия | Состояние | Функционал |
|-----------|--------|-----------|------------|
| **FastAPI** | 0.115.0 | ✅ Работает | REST API, WebSocket, middleware, CORS |
| **SQLAlchemy** | 2.0.36 | ✅ Работает | ORM, миграции, связи, индексы |
| **Pydantic** | 2.8.2 | ✅ Работает | Валидация запросов/ответов |
| **python-jose** | 3.3.0 | ✅ Работает | JWT-токены авторизации |
| **passlib + bcrypt** | 1.7.4 / 3.2.2 | ✅ Работает | Хэширование паролей |
| **google-auth** | 2.32.0 | ✅ Работает | Google OAuth авторизация |
| **APScheduler** | 3.10.4 | ✅ Работает | Фоновые задачи (AI-снимки, отчёты) |
| **httpx** | 0.27.2 | ✅ Работает | HTTP-клиент (webhook-уведомления) |
| **anthropic** | 0.18.1 | ✅ Работает | Claude Vision API для анализа скриншотов |
| **websockets** | 12.0 | ✅ Работает | Real-time стриминг экрана |
| **psycopg** | 3.2.13 | ✅ Готов | PostgreSQL драйвер (для прода) |

**Всего эндпоинтов API:** 80+
**Моделей БД:** 14
**Pydantic-схем:** 40+

### 2.2. Frontend — что есть и что умеет

| Технология | Версия | Состояние | Функционал |
|-----------|--------|-----------|------------|
| **PySide6** | 6.7.2 | ✅ Работает | Нативный GUI, анимации, виджеты |
| **httpx** | 0.27.2 | ✅ Работает | HTTP-клиент к backend |
| **mss** | 10.0.0+ | ✅ Работает | Захват скриншотов экрана |
| **opencv-python** | 4.9.0+ | ✅ Работает | Обработка изображений |
| **numpy** | 1.26.0+ | ✅ Работает | Числовые операции |
| **google-auth-oauthlib** | 1.2.1 | ✅ Работает | Google OAuth на клиенте |

**Экранов UI:** 18
**Тем оформления:** 3 (Default, Dark, iOS)
**API-методов клиента:** 80+

### 2.3. ML-модуль — что есть и что умеет

| Модуль | Состояние | Функционал |
|--------|-----------|------------|
| **questionnaire_validator** | ✅ Работает | Валидация анкет (ФИО, email, телефон, навыки), скоринг 0-100, автоодобрение ≥70 |
| **screenshot_analyzer** | ✅ Работает | AI-анализ скриншотов через Claude Vision, классификация приложений (продуктивные/непродуктивные), скоринг |
| **ML API** | ✅ Работает | `POST /ml/validate-questionnaire`, `GET /ml/health` |

---

## 3. МОДУЛЬ АВТОРИЗАЦИИ И АУТЕНТИФИКАЦИИ

### 3.1. Что реализовано ✅ ВЫПОЛНЕНО

#### 3.1.1. Регистрация пользователя
- **Эндпоинт:** `POST /auth/register`
- **Поля:** email, full_name, password
- **Валидация:** email-формат, обязательные поля
- **Безопасность:** bcrypt хэширование пароля
- **Ответ:** JWT access token
- **Статус:** ✅ ВЫПОЛНЕНО

#### 3.1.2. Авторизация по паролю
- **Эндпоинт:** `POST /auth/login`
- **Формат:** OAuth2 password flow
- **Rate limiting:** защита от перебора паролей
- **Ответ:** JWT access token (срок: 24 часа)
- **Статус:** ✅ ВЫПОЛНЕНО

#### 3.1.3. Google OAuth авторизация
- **Эндпоинт:** `POST /auth/google`
- **Процесс:**
  1. Фронтенд открывает Google OAuth окно
  2. Пользователь авторизуется в Google
  3. Google возвращает id_token
  4. Backend верифицирует токен через google-auth
  5. Создаётся/обновляется пользователь
  6. Возвращается JWT токен
- **Фоновый OAuth-воркер** на фронтенде (отдельный поток)
- **Статус:** ✅ ВЫПОЛНЕНО

#### 3.1.4. Экран авторизации (Frontend)
- Левая панель: брендинг с логотипом и описанием
- Правая панель: формы входа/регистрации
- Кнопка Google OAuth с SVG-иконкой
- Переключение между логином и регистрацией
- Валидация полей на клиенте
- Отображение ошибок
- **Статус:** ✅ ВЫПОЛНЕНО

#### 3.1.5. JWT-безопасность
- Алгоритм: HS256
- Время жизни: 24 часа (настраивается через `.env`)
- Middleware `get_current_user` для всех защищённых маршрутов
- Автоматическое декодирование и проверка
- **Статус:** ✅ ВЫПОЛНЕНО

#### 3.1.6. Сессия и автологин
- `SessionStore` — синглтон хранения состояния
- Персистентность через `.session.json`
- Автоматическая проверка токена при запуске
- Поля: token, org_id, user_id, full_name, role, theme, avatar_path
- **Статус:** ✅ ВЫПОЛНЕНО

#### 3.1.7. Onboarding flow (поток приветствия)
- Шаг 1: Авторизация → ✅ ВЫПОЛНЕНО
- Шаг 2: Согласие на обработку данных (Consent Banner) → ✅ ВЫПОЛНЕНО
- Шаг 3: Выбор роли (Админ / Сотрудник) → ✅ ВЫПОЛНЕНО
- *аг 4: Заполнение анкеты-резюме (Profile Setup) → ✅ ВЫПОЛНЕНО
- **Шаг 5:** Поиск и вступление в организацию (для сотрудников) → ✅ ВЫПОЛНЕНО

### 3.2. Что нужно доработать

| Функция | Статус | Описание |
|---------|--------|----------|
| Двухфакторная аутентификация (2FA) | ❌ Не реализовано | TOTP через Google Authenticator |
| Сброс пароля по email | ❌ Не реализовано | Отправка ссылки сброса на почту |
| Refresh tokens | ❌ Не реализовано | Обновление JWT без повторного логина |
| Блокировка после N неудачных попыток | ⚠️ Частично | Rate limiting есть, но нет блокировки аккаунта |
| Yandex OAuth | ❌ Не реализовано | Авторизация через Яндекс ID |
| OAuth через Telegram | ❌ Не реализовано | Авторизация через Telegram Bot |
| Аудит логинов | ⚠️ Частично | AuditLog модель есть, но логины не пишутся |
| Роль «Суперадмин платформы» | ❌ Не реализовано | Отдельная роль для управления всей платформой |

---

## 4. МОДУЛЬ КОМПАНИЙ / ОРГАНИЗАЦИЙ

### 4.1. Текущее состояние — что реализовано

#### 4.1.1. Модель Organization ✅ ВЫПОЛНЕНО
```
Поля:
- id (UUID, первичный ключ)
- name (строка, название компании)
- join_code (уникальный 8-символьный код для вступления)
- created_at (дата создания)
```

#### 4.1.2. Модель OrgMembership ✅ ВЫПОЛНЕНО
```
Поля:
- org_id (UUID, ссылка на организацию)
- user_id (UUID, ссылка на пользователя)
- role (enum: admin | manager | member)
- position (строка, должность)
- created_at (дата вступления)
```

#### 4.1.3. Модель OrgJoinRequest ✅ ВЫПОЛНЕНО
```
Поля:
- id (UUID)
- org_id (UUID)
- user_id (UUID)
- status (enum: pending | approved | rejected)
- created_at (дата подачи)
```

#### 4.1.4. API-эндпоинты организаций ✅ ВЫПОЛНЕНО
| Эндпоинт | Метод | Описание | Доступ |
|----------|-------|----------|--------|
| `/orgs` | POST | Создать организацию | Любой авторизованный |
| `/orgs/search` | GET | Поиск организаций | Любой авторизованный |
| `/orgs/join-request` | POST | Подать заявку на вступление | Любой авторизованный |
| `/orgs/{id}` | GET | Получить информацию об организации | Член организации |
| `/orgs/{id}/join-requests` | GET | Список заявок | Admin / Manager |
| `/orgs/{id}/join-requests/{rid}/approve` | POST | Одобрить заявку | Admin / Manager |
| `/orgs/{id}/join-requests/{rid}/reject` | POST | Отклонить заявку | Admin / Manager |
| `/orgs/{id}/members` | GET | Список участников | Член организации |
| `/orgs/{id}/members/{uid}` | PATCH | Изменить роль/должность | Admin |
| `/orgs/{id}/members/me` | GET | Моё членство | Член организации |

#### 4.1.5. Экран создания организации (OrgWizard) ✅ ВЫПОЛНЕНО
- Форма: аватар, название, описание, индустрия, цвет темы, сайт, приветственное сообщение
- Настройки приватности, максимум участников, автоодобрение
- Живой предпросмотр карточки компании
- **Статус:** ✅ ВЫПОЛНЕНО

### 4.2. Что нужно реализовать — система сертификатов и суперадмина

#### 4.2.1. Роль «Суперадмин платформы» ❌ НЕ РЕАЛИЗОВАНО

**Описание:** Суперадмин — это администратор самой платформы ProjectsControl (не компании). Только суперадмины могут создавать компании на платформе.

**Требования к реализации:**

**Backend:**
```python
# Новое поле в модели User:
class User(Base):
    ...
    is_superadmin = Column(Boolean, default=False, nullable=False)

# Новая зависимость:
def require_superadmin(user: User = Depends(get_current_user)):
    if not user.is_superadmin:
        raise HTTPException(403, "Superadmin access required")
    return user
```

**Изменение создания организаций:**
- `POST /orgs` — доступ только для суперадминов
- Суперадмин указывает: владельца компании, дату активации, срок действия
- При создании генерируется сертификат

**Технологии:** Существующий стек (FastAPI + SQLAlchemy), новая миграция БД

#### 4.2.2. Сертификат компании ❌ НЕ РЕАЛИЗОВАНО

**Описание:** Цифровой документ, подтверждающий регистрацию компании на платформе.

**Модель данных:**
```python
class OrganizationCertificate(Base):
    __tablename__ = "organization_certificates"

    id = Column(String, primary_key=True)          # UUID
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    certificate_number = Column(String, unique=True)  # Уникальный номер сертификата
    issued_at = Column(DateTime, nullable=False)      # Дата выдачи
    valid_from = Column(DateTime, nullable=False)      # Дата начала действия
    valid_until = Column(DateTime, nullable=False)     # Дата окончания действия
    owner_id = Column(String, ForeignKey("users.id"))  # Владелец компании
    issued_by_id = Column(String, ForeignKey("users.id"))  # Кто выдал (суперадмин)
    status = Column(Enum("active","suspended","expired","revoked"), default="active")
    industry = Column(String, nullable=True)           # Отрасль
    legal_name = Column(String, nullable=True)         # Юридическое название
    inn = Column(String, nullable=True)                # ИНН
    max_employees = Column(Integer, default=50)        # Лимит сотрудников
    tariff_plan_id = Column(String, ForeignKey("tariff_plans.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
```

**Поля обновления модели Organization:**
```python
class Organization(Base):
    ...
    # Новые поля:
    description = Column(Text, nullable=True)          # Описание
    industry = Column(String, nullable=True)           # Отрасль
    website = Column(String, nullable=True)            # Сайт
    logo_url = Column(String, nullable=True)           # Логотип
    owner_id = Column(String, ForeignKey("users.id"))  # Владелец
    is_active = Column(Boolean, default=True)          # Активна ли
    suspended_at = Column(DateTime, nullable=True)     # Дата приостановки
    max_members = Column(Integer, default=50)          # Лимит участников
    auto_approve = Column(Boolean, default=False)      # Автоодобрение заявок
    welcome_message = Column(Text, nullable=True)      # Приветственное сообщение
    theme_color = Column(String, nullable=True)        # Цвет темы
```

**API-эндпоинты (новые):**

| Эндпоинт | Метод | Описание | Доступ |
|----------|-------|----------|--------|
| `/admin/orgs` | POST | Создать компанию (суперадмин) | Суперадмин |
| `/admin/orgs` | GET | Список всех компаний | Суперадмин |
| `/admin/orgs/{id}/suspend` | POST | Приостановить компанию | Суперадмин |
| `/admin/orgs/{id}/activate` | POST | Активировать компанию | Суперадмин |
| `/admin/orgs/{id}/certificate` | GET | Получить сертификат | Суперадмин / Владелец |
| `/admin/orgs/{id}/certificate/renew` | POST | Продлить сертификат | Суперадмин |
| `/admin/orgs/{id}/certificate/revoke` | POST | Отозвать сертификат | Суперадмин |
| `/admin/orgs/{id}/certificate/pdf` | GET | Скачать PDF сертификат | Суперадмин / Владелец |

**Генерация PDF-сертификата:**
- **Технология:** `reportlab` или `weasyprint`
- **Содержание:** Номер, дата выдачи, дата окончания, название компании, владелец, QR-код для верификации
- **Формат:** A4, с логотипом платформы и водяным знаком

**Экран суперадмин-панели (Frontend):**
- Список всех компаний с фильтрами (активные, приостановленные, истёкшие)
- Форма создания компании
- Просмотр и управление сертификатами
- Статистика по компаниям

---

## 5. МОДУЛЬ ШТАБОВ / ОТДЕЛОВ

### 5.1. Что реализовано ✅ ВЫПОЛНЕНО

#### 5.1.1. Модель Team (Отдел/Штаб) ✅ ВЫПОЛНЕНО
```
Поля:
- id (UUID)
- org_id (UUID, ссылка на организацию)
- project_id (UUID, nullable, ссылка на проект)
- name (название отдела)
- created_at (дата создания)

Связи:
- organization → Organization
- project → Project (опционально)
- members → TeamMembership (каскадное удаление)
- tasks → Task
```

#### 5.1.2. Модель TeamMembership ✅ ВЫПОЛНЕНО
```
Поля:
- team_id (UUID)
- user_id (UUID)
- role (enum: member | lead) — сотрудник или тимлид
- created_at (дата вступления)
```

#### 5.1.3. API-эндпоинты отделов ✅ ВЫПОЛНЕНО
| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/orgs/{id}/teams` | POST | Создать отдел |
| `/orgs/{id}/teams` | GET | Список отделов |
| `/orgs/{id}/teams/me` | GET | Мои отделы |
| `/orgs/{id}/teams/{tid}` | PATCH | Обновить отдел |
| `/orgs/{id}/teams/{tid}` | DELETE | Удалить отдел |
| `/orgs/{id}/teams/{tid}/members` | POST | Добавить сотрудника |

#### 5.1.4. Экран отделов (Frontend) ✅ ВЫПОЛНЕНО
- Список отделов с карточками
- На карточке: название, тимлид, количество участников
- Создание отдела (admin)
- Удаление отдела (admin)
- Переход в детальный экран отдела
- **Статус:** ✅ ВЫПОЛНЕНО

#### 5.1.5. Экран отдела — Department Dashboard ✅ ВЫПОЛНЕНО
- **Вкладка «Обзор»:** тимлид, коллеги, проекты, задачи на сегодня, KPI
- **Вкладка «Команда»:** лучший сотрудник, рейтинг участников с КПД, общий КПД
- **Вкладка «Детали»:** активные сессии в реальном времени, live-превью, AI-аналитика
- **Статус:** ✅ ВЫПОЛНЕНО

### 5.2. Что нужно доработать

| Функция | Статус | Описание |
|---------|--------|----------|
| Иерархия отделов (подотделы) | ❌ Не реализовано | Дерево отделов с parent_id |
| Руководитель отдела vs Тимлид | ❌ Не реализовано | Разделить роли: руководитель отдела, тимлид проекта |
| Описание и аватар отдела | ❌ Не реализовано | Расширить модель Team |
| Перемещение сотрудников между отделами | ❌ Не реализовано | Drag & drop или меню перевода |
| KPI отдела с историей | ⚠️ Частично | KPI есть, истории нет |
| Удаление участника из отдела | ❌ Не реализовано | Эндпоинт DELETE team member |

---

## 6. МОДУЛЬ НАЙМА СОТРУДНИКОВ (HH-ФУНКЦИОНАЛ)

### 6.1. Сравнение с HeadHunter (hh.ru)

| Функция hh.ru | Наша платформа | Статус |
|---------------|----------------|--------|
| **Регистрация соискателя** | Регистрация пользователя (email + пароль или Google OAuth) | ✅ ВЫПОЛНЕНО |
| **Заполнение резюме** | Экран Profile Setup — анкета-резюме в стиле hh.ru | ✅ ВЫПОЛНЕНО |
| **Поиск компаний** | Поиск организаций по названию/коду | ✅ ВЫПОЛНЕНО |
| **Отклик на вакансию (подача заявки)** | OrgJoinRequest — подача заявки на вступление | ✅ ВЫПОЛНЕНО |
| **Статус отклика (ожидание/одобрено/отказ)** | Статусы: pending / approved / rejected | ✅ ВЫПОЛНЕНО |
| **Уведомления о заявках** | Панель уведомлений для админов/менеджеров | ✅ ВЫПОЛНЕНО |
| **Одобрение/отклонение заявки** | Approve / Reject кнопки в уведомлениях | ✅ ВЫПОЛНЕНО |
| **ML-валидация анкеты** | questionnaire_validator с автоскорингом | ✅ ВЫПОЛНЕНО |
| **Профиль-портфолио** | Профиль: аватар, ФИО, специальность, bio, сайт, соцсети | ✅ ВЫПОЛНЕНО |
| **Вступление по коду (приглашение)** | join_code — уникальный код организации | ✅ ВЫПОЛНЕНО |
| **Просмотр резюме соискателя** | Поиск пользователей по имени/email/специальности | ✅ ВЫПОЛНЕНО |
| **Публикация вакансий** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **Каталог вакансий** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **Фильтры по навыкам/опыту** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **Рекомендации вакансий** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **Чат между HR и соискателем** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **Тестовые задания** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **Приглашение по email/ссылке** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **История откликов** | ❌ | ❌ НЕ РЕАЛИЗОВАНО |
| **Рейтинг соискателя** | ❌ (AI Score есть, но внутренний) | ⚠️ ЧАСТИЧНО |

### 6.2. Текущий поток найма — что есть

```
Соискатель                              Компания (Admin/Manager)
    │                                        │
    ├─ 1. Регистрация ✅                      │
    ├─ 2. Consent (согласие) ✅                │
    ├─ 3. Выбор роли ✅                       │
    ├─ 4. Заполнение анкеты-резюме ✅          │
    │    └─ ML-валидация (скоринг 0-100) ✅    │
    ├─ 5. Поиск компании ✅                    │
    ├─ 6. Подача заявки (join-request) ✅       │
    │                                    ├─ 7. Получение уведомления ✅
    │                                    ├─ 8. Просмотр профиля заявителя ✅
    │                                    └─ 9. Approve / Reject ✅
    ├─ 10. Получение статуса ✅                │
    └─ 11. Вход в рабочий интерфейс ✅         │
```

### 6.3. Что нужно реализовать

#### 6.3.1. Система вакансий ❌ НЕ РЕАЛИЗОВАНО

**Модель данных:**
```python
class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    title = Column(String, nullable=False)           # Название вакансии
    description = Column(Text)                       # Описание
    requirements = Column(Text)                      # Требования
    salary_min = Column(Integer, nullable=True)      # Мин. зарплата
    salary_max = Column(Integer, nullable=True)      # Макс. зарплата
    salary_currency = Column(String, default="RUB")
    experience_years = Column(Integer, default=0)    # Требуемый опыт
    skills_required = Column(JSON, default=list)     # Требуемые навыки
    employment_type = Column(Enum("full_time","part_time","contract","internship"))
    is_active = Column(Boolean, default=True)
    views_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now_naive)
    closed_at = Column(DateTime, nullable=True)

class VacancyApplication(Base):
    __tablename__ = "vacancy_applications"

    id = Column(String, primary_key=True)
    vacancy_id = Column(String, ForeignKey("vacancies.id"))
    user_id = Column(String, ForeignKey("users.id"))
    cover_letter = Column(Text, nullable=True)       # Сопроводительное письмо
    status = Column(Enum("pending","reviewing","interview","offered","rejected","withdrawn"))
    ai_match_score = Column(Float, nullable=True)    # AI-совместимость
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=True)
```

**API-эндпоинты:**

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/orgs/{id}/vacancies` | POST | Создать вакансию |
| `/orgs/{id}/vacancies` | GET | Список вакансий компании |
| `/vacancies/search` | GET | Глобальный поиск вакансий |
| `/vacancies/{vid}` | GET | Детали вакансии |
| `/vacancies/{vid}/apply` | POST | Откликнуться |
| `/vacancies/{vid}/applications` | GET | Отклики на вакансию |
| `/vacancies/{vid}/applications/{aid}` | PATCH | Обновить статус отклика |
| `/users/me/applications` | GET | Мои отклики |

**AI-matching:** Использовать ML-модуль для сопоставления навыков из профиля с требованиями вакансии (cosine similarity по TF-IDF или sentence embeddings).

#### 6.3.2. Приглашение по email/ссылке ❌ НЕ РЕАЛИЗОВАНО

**Модель:**
```python
class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    invited_by = Column(String, ForeignKey("users.id"))
    email = Column(String, nullable=False)
    token = Column(String, unique=True)               # Уникальный токен приглашения
    role = Column(Enum(OrgRole), default="member")
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    status = Column(Enum("pending","accepted","expired","cancelled"))
    expires_at = Column(DateTime, nullable=False)      # Срок действия (7 дней)
    created_at = Column(DateTime, default=utc_now_naive)
```

**Технологии для email:** `aiosmtplib` + шаблоны `jinja2`, или интеграция с SendGrid/Mailgun API.

#### 6.3.3. Расширение профиля-портфолио ❌ НЕ РЕАЛИЗОВАНО

**Новые поля модели User:**
```python
class User(Base):
    ...
    # Профессиональные данные:
    position = Column(String, nullable=True)         # Текущая должность
    experience_years = Column(Integer, nullable=True) # Опыт в годах
    skills = Column(JSON, default=list)              # Массив навыков
    experience_description = Column(Text, nullable=True) # Описание опыта
    education = Column(Text, nullable=True)          # Образование
    phone = Column(String, nullable=True)            # Телефон
    city = Column(String, nullable=True)             # Город
    portfolio_url = Column(String, nullable=True)    # Ссылка на портфолио
    resume_file = Column(String, nullable=True)      # Путь к PDF-резюме
    is_looking_for_job = Column(Boolean, default=False)  # Ищет работу
    desired_salary = Column(Integer, nullable=True)  # Желаемая зарплата
    questionnaire_score = Column(Float, nullable=True)   # ML-скор анкеты
    questionnaire_status = Column(Enum("pending","approved","rejected"), nullable=True)
```

---

## 7. СИСТЕМА РОЛЕЙ И ПОЛНОМОЧИЙ

### 7.1. Текущие роли ✅ ВЫПОЛНЕНО

| Роль | Уровень | Описание | Статус |
|------|---------|----------|--------|
| **Admin** | Организация | Полный доступ внутри организации | ✅ ВЫПОЛНЕНО |
| **Manager** | Организация | Управление командами, проектами, задачами | ✅ ВЫПОЛНЕНО |
| **Member** | Организация | Базовый доступ: задачи, отчёты, свой кабинет | ✅ ВЫПОЛНЕНО |
| **Lead** | Команда | Тимлид отдела | ✅ ВЫПОЛНЕНО |
| **Member** | Команда | Рядовой сотрудник отдела | ✅ ВЫПОЛНЕНО |

### 7.2. Текущая матрица доступа ✅ ВЫПОЛНЕНО

| Действие | Admin | Manager | Member |
|----------|-------|---------|--------|
| Создать проект | ✅ | ✅ | ❌ |
| Видеть все проекты | ✅ | ✅ | ❌ (только свои через команды) |
| Создать отдел/команду | ✅ | ✅ | ❌ |
| Удалить отдел | ✅ | ❌ | ❌ |
| Добавить сотрудника в отдел | ✅ | ✅ | ❌ |
| Создать задачу | ✅ | ✅ | ❌ |
| Обновить задачу | ✅ | ✅ | ✅ (только свои) |
| Просматривать сессии других | ✅ | ✅ | ❌ |
| Live-трансляции | ✅ | ✅ | ❌ |
| KPI-отчёты | ✅ | ✅ | ❌ |
| Экспорт отчётов | ✅ | ✅ | ❌ |
| Одобрить/отклонить заявку | ✅ | ✅ | ❌ |
| Изменить роль сотрудника | ✅ | ❌ | ❌ |
| Privacy-правила | ✅ | ✅ | ❌ |
| Webhook-уведомления | ✅ | ✅ | ❌ |
| AI-скоркарты (свои) | ✅ | ✅ | ✅ |
| AI-скоркарты (всех) | ✅ | ✅ | ❌ |

### 7.3. Расширенная система ролей — ЧТО НУЖНО РЕАЛИЗОВАТЬ ❌

Для имитации реальной корпоративной структуры предлагается следующая иерархия:

#### Уровень 1: Платформа
| Роль | Полномочия |
|------|-----------|
| **Суперадмин платформы** | Создание/блокировка компаний, выдача сертификатов, управление тарифами, техподдержка всей платформы, доступ к аналитике платформы, управление банами |

#### Уровень 2: Организация
| Роль | Полномочия |
|------|-----------|
| **Владелец (Owner)** | Полный контроль компании, назначение директоров, изменение тарифа, удаление компании |
| **Директор (Director)** | Управление всеми отделами, проектами, найм/увольнение, финансовые решения |
| **HR-менеджер** | Управление вакансиями, просмотр анкет, приглашения, onboarding новых сотрудников |
| **Бухгалтер (Accountant)** | Просмотр финансовой статистики, тарифов, отчётов по расходам |
| **Менеджер проекта (PM)** | Управление одним или несколькими проектами, командами проекта |

#### Уровень 3: Отдел / Команда
| Роль | Полномочия |
|------|-----------|
| **Руководитель отдела (Head of Department)** | Управление всеми командами в отделе, назначение тимлидов |
| **Тимлид (Team Lead)** | Управление своей командой, задачами, код-ревью (если IT) |
| **Старший специалист (Senior)** | Менторство, доступ к расширенной аналитике |
| **Специалист (Specialist)** | Основной исполнитель, полный рабочий функционал |
| **Стажёр (Intern)** | Ограниченный доступ, задачи только от тимлида |

#### Реализация в коде:

**Новый enum ролей:**
```python
class PlatformRole(str, Enum):
    superadmin = "superadmin"

class OrgRole(str, Enum):
    owner = "owner"
    director = "director"
    hr_manager = "hr_manager"
    accountant = "accountant"
    project_manager = "project_manager"
    admin = "admin"        # backward compatibility
    manager = "manager"    # backward compatibility
    member = "member"      # backward compatibility

class TeamRole(str, Enum):
    head = "head"
    lead = "lead"
    senior = "senior"
    specialist = "specialist"
    intern = "intern"
```

**Модель разрешений (RBAC):**
```python
class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True)       # "tasks.create", "reports.view", etc.
    description = Column(String)

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role = Column(String, primary_key=True)
    permission_id = Column(String, ForeignKey("permissions.id"), primary_key=True)
```

**Технология:** RBAC (Role-Based Access Control) на уровне middleware FastAPI. Кеширование разрешений в Redis (при масштабировании).

---

## 8. МОДУЛЬ ТЕХНИЧЕСКОЙ ПОДДЕРЖКИ

### 8.1. Текущее состояние

**Техподдержка не реализована.** ❌ НЕ РЕАЛИЗОВАНО

### 8.2. Архитектура модуля техподдержки

#### 8.2.1. Уровни техподдержки

| Уровень | Описание | Время отклика |
|---------|----------|---------------|
| **L1 — Самообслуживание** | FAQ, база знаний, AI-чатбот | Мгновенно |
| **L2 — Стандартная поддержка** | Тикет-система, чат с оператором | До 24 часов |
| **L3 — Приоритетная поддержка** | Выделенный менеджер (тариф Premium) | До 4 часов |
| **L4 — Экстренная** | Критические сбои платформы | До 1 часа |

#### 8.2.2. Модель данных

```python
class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(String, primary_key=True)
    ticket_number = Column(String, unique=True)       # TICKET-2026-00001
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    category = Column(Enum(
        "bug_report",        # Баг
        "feature_request",   # Запрос функции
        "billing",           # Оплата/тариф
        "account",           # Аккаунт
        "organization",      # Организация
        "technical",         # Техническая проблема
        "security",          # Безопасность
        "other"              # Другое
    ))
    priority = Column(Enum("low","medium","high","critical"), default="medium")
    status = Column(Enum(
        "open",              # Открыт
        "in_progress",       # В работе
        "waiting_for_user",  # Ожидание ответа пользователя
        "waiting_for_support", # Ожидание ответа поддержки
        "resolved",          # Решён
        "closed",            # Закрыт
        "reopened"           # Переоткрыт
    ), default="open")
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    resolution = Column(Text, nullable=True)
    satisfaction_rating = Column(Integer, nullable=True)  # 1-5
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(String, primary_key=True)
    ticket_id = Column(String, ForeignKey("support_tickets.id"))
    sender_id = Column(String, ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)       # Внутренняя заметка
    attachments_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now_naive)

class FAQArticle(Base):
    __tablename__ = "faq_articles"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    views_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=True)
```

#### 8.2.3. API-эндпоинты

| Эндпоинт | Метод | Описание | Доступ |
|----------|-------|----------|--------|
| `/support/tickets` | POST | Создать тикет | Любой авторизованный |
| `/support/tickets` | GET | Мои тикеты | Любой авторизованный |
| `/support/tickets/{id}` | GET | Детали тикета | Автор / Суперадмин |
| `/support/tickets/{id}/messages` | POST | Отправить сообщение | Автор / Поддержка |
| `/support/tickets/{id}/messages` | GET | История сообщений | Автор / Поддержка |
| `/support/tickets/{id}/status` | PATCH | Сменить статус | Поддержка |
| `/support/tickets/{id}/assign` | POST | Назначить агента | Суперадмин |
| `/support/tickets/{id}/rate` | POST | Оценить решение | Автор |
| `/admin/support/tickets` | GET | Все тикеты (фильтры) | Суперадмин |
| `/admin/support/stats` | GET | Статистика поддержки | Суперадмин |
| `/support/faq` | GET | Список FAQ | Все |
| `/support/faq/{id}` | GET | Статья FAQ | Все |
| `/admin/support/faq` | POST | Создать FAQ | Суперадмин |
| `/support/ai-chat` | POST | AI-ассистент | Любой авторизованный |

#### 8.2.4. AI-чатбот первой линии

**Технология:** Anthropic Claude API (уже подключён в проекте)

**Логика работы:**
1. Пользователь описывает проблему в чате
2. AI анализирует текст, ищет похожие FAQ-статьи (semantic search)
3. Если уверенность > 80% — отвечает автоматически
4. Если уверенность < 80% — создаёт тикет и передаёт оператору
5. AI предлагает категорию и приоритет тикета

#### 8.2.5. Экран техподдержки (Frontend)

- **Для пользователя:** Список тикетов, чат-интерфейс, FAQ-поиск, AI-ассистент
- **Для суперадмина:** Дашборд с метриками (открытые тикеты, среднее время ответа, CSAT), очередь тикетов, назначение агентов

---

## 9. АНАЛИТИКА И СТАТИСТИКА

### 9.1. Что реализовано ✅ ВЫПОЛНЕНО

#### 9.1.1. KPI-отчёты организации ✅ ВЫПОЛНЕНО
- **Эндпоинт:** `GET /orgs/{id}/reports/kpi`
- **Метрики:** Количество задач, процент выполнения, активное время, данные по пользователям и командам
- **Доступ:** Admin / Manager

#### 9.1.2. KPI-отчёты проектов ✅ ВЫПОЛНЕНО
- **Эндпоинт:** `GET /orgs/{id}/reports/projects/kpi`
- **Метрики:** Статистика по задачам проекта, участникам, прогрессу

#### 9.1.3. AI-аналитика (продвинутая) ✅ ВЫПОЛНЕНО
- **Эндпоинт:** `GET /orgs/{id}/ai/kpi`
- **Возможности:**
  - Многофакторный скоринг (10+ измерений)
  - Обнаружение аномалий (Isolation Forest)
  - Детектирование flow-сессий (состояние потока)
  - Оценка риска выгорания
  - Циркадный и ультрадианный ритм-анализ
  - Анализ отвлечений
  - Интеллект перерывов (оптимальные перерывы)
  - Предиктивный скоринг (Holt linear + регрессия)
  - Отслеживание импульса (momentum)
  - Кластеризация рабочих стилей
  - Оценка благополучия (wellbeing)

#### 9.1.4. AI-скоркарты ✅ ВЫПОЛНЕНО
- **Эндпоинт:** `GET /orgs/{id}/ai/scorecards`
- **Режимы:** employee (личные данные), executive (данные всех сотрудников)
- **Поля:** score (0-100), completion_rate, active_ratio, tasks stats, session stats, reasons, drivers

#### 9.1.5. Экспорт отчётов ✅ ВЫПОЛНЕНО
- CSV и JSON форматы
- Экспорт KPI организации и проектов
- Список экспортов с загрузкой
- Расписание автоматического экспорта

#### 9.1.6. Метрики сессий и пользователей ✅ ВЫПОЛНЕНО
- **Сессии:** Длительность, события, использование приложений, idle-время
- **Пользователи:** Агрегированные метрики за период, топ приложений
- **Activity per task:** Метрики активности привязанные к задачам

#### 9.1.7. Фоновый планировщик ✅ ВЫПОЛНЕНО
- Daily AI snapshots (2:00 UTC)
- Weekly AI snapshots (Воскресенье 23:59)
- Расписание экспорта отчётов (каждые 5 минут check)
- Очистка старых записей (retention: 90 дней записи, 30 дней события)

#### 9.1.8. Мониторинг в реальном времени ✅ ВЫПОЛНЕНО
- Live-трансляции экранов сотрудников (WebSocket)
- Захват скриншотов каждые 10 сек (mss + opencv)
- AI-анализ скриншотов через Claude Vision
- Превью-кадры с поллингом (1 FPS)
- Статусы REC с индикацией

#### 9.1.9. Аудит-логи ✅ ВЫПОЛНЕНО
- **Эндпоинт:** `GET /orgs/{id}/audit`
- **Действия:** create, update, delete, approve, reject, login
- **Поля:** actor, entity_type, entity_id, details, timestamp

### 9.2. Что нужно доработать

| Функция | Статус | Описание |
|---------|--------|----------|
| Дашборд аналитики (Frontend) | ⚠️ Частично | KPI показывается в department screen, но нет отдельного дашборда |
| Графики и визуализация | ❌ Не реализовано | Интерактивные графики (line, bar, pie charts) |
| Сравнительная аналитика | ❌ Не реализовано | Сравнение отделов, проектов, периодов |
| Аналитика платформы (суперадмин) | ❌ Не реализовано | Общая статистика: компании, пользователи, активность |
| Экспорт в PDF | ❌ Не реализовано | PDF-отчёты с графиками |
| Пользовательские дашборды | ❌ Не реализовано | Конструктор дашбордов с виджетами |
| Прогнозирование сроков проектов | ❌ Не реализовано | ML-модель предсказания дедлайнов |

**Технологии для графиков (Frontend):**
- `PySide6.QtCharts` — встроенные Qt графики
- `pyqtgraph` — высокопроизводительные графики
- Или встроенный `QWebEngineView` с `Chart.js` / `ECharts` для интерактивных дашбордов

---

## 10. РЕЙТИНГОВАЯ СИСТЕМА

### 10.1. Текущее состояние

| Компонент | Статус | Описание |
|-----------|--------|----------|
| AI Score (0-100) | ✅ ВЫПОЛНЕНО | Автоматический скоринг продуктивности |
| Daily/Weekly снимки | ✅ ВЫПОЛНЕНО | Ежедневные и еженедельные AI-оценки |
| Рейтинг в отделе | ✅ ВЫПОЛНЕНО | На экране Department — ранжирование по КПД |

### 10.2. Внешняя рейтинговая система (стабильная) ❌ НЕ РЕАЛИЗОВАНО

**Описание:** Публичный рейтинг, видимый всем пользователям платформы. Обновляется раз в квартал. Отражает общую репутацию сотрудника и компании.

#### 10.2.1. Рейтинг сотрудника (внешний)

**Модель:**
```python
class EmployeePublicRating(Base):
    __tablename__ = "employee_public_ratings"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    quarter = Column(String, nullable=False)          # "2026-Q1"
    year = Column(Integer, nullable=False)

    # Составляющие рейтинга
    productivity_score = Column(Float, default=0)     # Продуктивность (из AI Score)
    task_completion_rate = Column(Float, default=0)    # Процент выполненных задач
    punctuality_score = Column(Float, default=0)      # Соблюдение дедлайнов
    collaboration_score = Column(Float, default=0)    # Командная работа
    quality_score = Column(Float, default=0)          # Качество работы (из ревью)
    innovation_score = Column(Float, default=0)       # Инициативность

    overall_score = Column(Float, default=0)          # Итоговый рейтинг (0-100)
    rank_in_platform = Column(Integer, nullable=True) # Место на платформе
    rank_in_org = Column(Integer, nullable=True)      # Место в компании
    badge = Column(Enum("platinum","gold","silver","bronze","none"), default="none")

    is_published = Column(Boolean, default=False)
    calculated_at = Column(DateTime)
    published_at = Column(DateTime, nullable=True)
```

**Формула:**
```
overall_score = (
    productivity_score * 0.25 +
    task_completion_rate * 0.25 +
    punctuality_score * 0.15 +
    collaboration_score * 0.15 +
    quality_score * 0.10 +
    innovation_score * 0.10
)
```

**Бейджи:**
| Бейдж | Диапазон | Описание |
|-------|----------|----------|
| Platinum | 90-100 | Топ-5% платформы |
| Gold | 75-89 | Топ-15% |
| Silver | 60-74 | Выше среднего |
| Bronze | 40-59 | Средний уровень |
| — None | 0-39 | Нужно улучшение |

#### 10.2.2. Рейтинг компании (внешний)

**Модель:**
```python
class OrgPublicRating(Base):
    __tablename__ = "org_public_ratings"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    quarter = Column(String)                           # "2026-Q1"
    year = Column(Integer)

    avg_employee_score = Column(Float, default=0)     # Средний скор сотрудников
    employee_retention_rate = Column(Float, default=0) # % удержания сотрудников
    project_success_rate = Column(Float, default=0)   # % успешных проектов
    growth_rate = Column(Float, default=0)            # Рост команды
    activity_level = Column(Float, default=0)         # Активность на платформе
    support_rating = Column(Float, default=0)         # Оценки техподдержки

    overall_score = Column(Float, default=0)
    rank_in_platform = Column(Integer, nullable=True)
    tier = Column(Enum("enterprise","professional","standard","starter"))
    badge = Column(Enum("top_employer","rising_star","reliable","none"), default="none")

    is_published = Column(Boolean, default=False)
    calculated_at = Column(DateTime)
```

### 10.3. Внутренняя рейтинговая система (ежемесячная) ❌ НЕ РЕАЛИЗОВАНО

**Описание:** Виден только внутри компании. Обновляется ежемесячно. Детальный, включает более глубокие метрики.

**Модель:**
```python
class EmployeeMonthlyRating(Base):
    __tablename__ = "employee_monthly_ratings"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    user_id = Column(String, ForeignKey("users.id"))
    month = Column(Integer)                           # 1-12
    year = Column(Integer)

    # Детальные метрики
    tasks_assigned = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_overdue = Column(Integer, default=0)
    avg_task_time_hours = Column(Float, default=0)
    total_active_hours = Column(Float, default=0)
    total_idle_hours = Column(Float, default=0)
    productive_app_ratio = Column(Float, default=0)   # % продуктивных приложений
    avg_daily_score = Column(Float, default=0)        # Средний дневной AI-скор
    flow_sessions_count = Column(Integer, default=0)  # Количество flow-сессий
    burnout_risk = Column(Float, default=0)           # Риск выгорания (0-1)
    reports_submitted = Column(Integer, default=0)    # Подано отчётов
    streak_days = Column(Integer, default=0)          # Серия рабочих дней
    peer_reviews_given = Column(Integer, default=0)   # Ревью для коллег
    peer_reviews_received = Column(Integer, default=0)

    overall_score = Column(Float, default=0)
    rank_in_org = Column(Integer, nullable=True)
    rank_in_team = Column(Integer, nullable=True)
    trend = Column(Enum("up","stable","down"), default="stable")  # Тренд
    manager_comment = Column(Text, nullable=True)     # Комментарий руководителя

    calculated_at = Column(DateTime)
```

**API-эндпоинты рейтингов:**

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/ratings/employees/public` | GET | Публичный рейтинг сотрудников |
| `/ratings/employees/{uid}/public` | GET | Публичный рейтинг конкретного сотрудника |
| `/ratings/orgs/public` | GET | Публичный рейтинг компаний |
| `/orgs/{id}/ratings/monthly` | GET | Внутренний ежемесячный рейтинг |
| `/orgs/{id}/ratings/monthly/{uid}` | GET | Рейтинг конкретного сотрудника за месяц |
| `/orgs/{id}/ratings/leaderboard` | GET | Лидерборд организации |
| `/admin/ratings/recalculate` | POST | Пересчитать рейтинги | Суперадмин |

**Фоновые задачи (APScheduler):**
- Ежемесячный расчёт внутренних рейтингов (1-е число каждого месяца)
- Ежеквартальный расчёт внешних рейтингов (1-е число квартала)
- Публикация после модерации суперадмином

---

## 11. МОНЕТИЗАЦИЯ

### 11.1. Текущее состояние

**Монетизация не реализована.** ❌ НЕ РЕАЛИЗОВАНО

### 11.2. Система банов и платной отсрочки ❌ НЕ РЕАЛИЗОВАНО

#### 11.2.1. Модель данных

```python
class UserBan(Base):
    __tablename__ = "user_bans"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)  # null = платформенный бан
    reason = Column(Text, nullable=False)
    banned_by = Column(String, ForeignKey("users.id"))
    ban_type = Column(Enum("temporary","permanent"), default="temporary")
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=True)         # null для permanent
    is_active = Column(Boolean, default=True)
    payment_id = Column(String, ForeignKey("payments.id"), nullable=True)  # Если оплачена отсрочка
    created_at = Column(DateTime, default=utc_now_naive)

class BanAppeal(Base):
    __tablename__ = "ban_appeals"

    id = Column(String, primary_key=True)
    ban_id = Column(String, ForeignKey("user_bans.id"))
    user_id = Column(String, ForeignKey("users.id"))
    reason = Column(Text, nullable=False)             # Причина апелляции
    status = Column(Enum("pending","approved","rejected"), default="pending")
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    payment_option = Column(Boolean, default=False)   # Хочет ли оплатить отсрочку
    created_at = Column(DateTime, default=utc_now_naive)
```

#### 11.2.2. Логика оплаты отсрочки бана

**Процесс:**
1. Пользователь получает временный бан (например, 7 дней)
2. Пользователь видит экран бана с таймером и причиной
3. На экране — кнопка «Снять бан досрочно» с ценой
4. Цена рассчитывается: `оставшиеся_дни × ставка_за_день`
5. После оплаты бан снимается мгновенно
 

### 11.3. LLM-модуль для компаний ❌ НЕ РЕАЛИЗОВАНО

**Описание:** Умная AI-система для анализа и управления внутри компании. Предоставляется как premium-функция.

#### 11.3.1. Возможности LLM-модуля

| Функция | Описание | Технология |
|---------|----------|-----------|
| **AI-ассистент компании** | Чат-бот, отвечающий на вопросы о процессах компании | Anthropic Claude API |
| **Автоматические отчёты** | Генерация текстовых отчётов на основе данных | Claude + Jinja2 шаблоны |
| **Рекомендации по оптимизации** | AI-советы по улучшению процессов | Claude + ML-модели |
| **Анализ настроения команды** | Sentiment analysis из отчётов и сообщений | NLP (transformers) |
| **Прогнозирование KPI** | Предсказание будущих показателей | scikit-learn (уже есть в проекте) |
| **Автоназначение задач** | AI рекомендует исполнителя на основе навыков/загрузки | Matching алгоритм |
| **Суммаризация активности** | Краткий отчёт дня/недели | Claude API |
| **Обнаружение рисков** | Раннее предупреждение о проблемах (дедлайны, выгорание) | Уже частично есть (burnout risk) |

#### 11.3.2. Модель данных

```python
class AICompanyAssistant(Base):
    __tablename__ = "ai_company_assistants"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"), unique=True)
    is_enabled = Column(Boolean, default=False)
    model = Column(String, default="claude-sonnet-4-20250514")
    monthly_tokens_limit = Column(Integer, default=1_000_000)
    tokens_used_this_month = Column(Integer, default=0)
    context_json = Column(JSON, default=dict)          # Контекст компании
    created_at = Column(DateTime, default=utc_now_naive)

class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    user_id = Column(String, ForeignKey("users.id"))
    messages_json = Column(JSON, default=list)         # История диалога
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=True)
```

**API-эндпоинты:**

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/orgs/{id}/ai/assistant/chat` | POST | Отправить сообщение AI |
| `/orgs/{id}/ai/assistant/conversations` | GET | История разговоров |
| `/orgs/{id}/ai/assistant/report` | POST | Сгенерировать AI-отчёт |
| `/orgs/{id}/ai/assistant/recommendations` | GET | AI-рекомендации |
| `/orgs/{id}/ai/assistant/settings` | PATCH | Настройки AI |

**Технологии:**
- Anthropic Claude API (уже подключён: `anthropic==0.18.1`)
- Streaming ответов через SSE (Server-Sent Events)
- RAG (Retrieval-Augmented Generation) для контекста компании
- Кеширование контекста в JSON-поле

### 11.4. Платёжная система ❌ НЕ РЕАЛИЗОВАНО

**Модель:**
```python
class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    amount = Column(Float, nullable=False)            # Сумма в рублях
    currency = Column(String, default="RUB")
    payment_type = Column(Enum(
        "ban_appeal",        # Отсрочка бана
        "tariff_subscription", # Подписка на тариф
        "tariff_renewal",    # Продление тарифа
        "ai_addon",          # Дополнительные AI-токены
        "premium_feature"    # Премиум-функция
    ))
    status = Column(Enum("pending","completed","failed","refunded"), default="pending")
    provider = Column(Enum("yookassa","stripe","tinkoff"), default="yookassa")
    external_id = Column(String, nullable=True)       # ID в платёжной системе
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now_naive)
    completed_at = Column(DateTime, nullable=True)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    tariff_plan_id = Column(String, ForeignKey("tariff_plans.id"))
    status = Column(Enum("active","expired","cancelled","suspended"), default="active")
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=True)
    last_payment_id = Column(String, ForeignKey("payments.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
```

**Технологии для приёма платежей:**
- **ЮKassa (YooMoney)** — для российского рынка (рубли, карты, электронные кошельки)
- **Tinkoff Acquiring** — альтернатива для РФ
- **Stripe** — для международных платежей
- Библиотека: `yookassa` (Python SDK)
- Webhook для уведомлений о статусе платежа

---

## 12. ТАРИФНЫЕ ПЛАНЫ

### 12.1. Текущее состояние

**Тарифные планы не реализованы.** ❌ НЕ РЕАЛИЗОВАНО

### 12.2. Структура тарифов

#### 12.2.1. Модель данных

```python
class TariffPlan(Base):
    __tablename__ = "tariff_plans"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)             # Название тарифа
    code = Column(String, unique=True)                # starter, business, enterprise
    description = Column(Text)
    price_monthly = Column(Float, nullable=False)     # Цена в месяц
    price_yearly = Column(Float, nullable=False)      # Цена в год (скидка)
    currency = Column(String, default="RUB")

    # Лимиты
    max_employees = Column(Integer)                   # Макс. сотрудников
    max_teams = Column(Integer)                       # Макс. отделов
    max_projects = Column(Integer)                    # Макс. проектов
    max_storage_gb = Column(Integer)                  # Хранилище (ГБ)
    max_ai_tokens_monthly = Column(Integer)           # AI-токены в месяц

    # Фичи (JSON-массив строк)
    features_json = Column(JSON, default=list)

    # Техподдержка
    support_level = Column(Enum("community","standard","priority","dedicated"))
    support_response_hours = Column(Integer)          # Время отклика (часы)

    # Флаги
    has_ai_assistant = Column(Boolean, default=False)
    has_live_streaming = Column(Boolean, default=True)
    has_export_reports = Column(Boolean, default=True)
    has_custom_branding = Column(Boolean, default=False)
    has_api_access = Column(Boolean, default=False)
    has_video_calls = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now_naive)
```

#### 12.2.2. Тарифные планы

| Параметр |  Starter |  Business |  Enterprise |
|----------|-----------|------------|--------------|
| **Цена/мес** | Бесплатно | 4 990 ₽/мес | 14 990 ₽/мес |
| **Цена/год** | Бесплатно | 49 900 ₽/год (-17%) | 149 900 ₽/год (-17%) |
| **Сотрудников** | До 5 | До 50 | Без лимита |
| **Отделов** | 1 | 10 | Без лимита |
| **Проектов** | 2 | 20 | Без лимита |
| **Хранилище** | 1 ГБ | 50 ГБ | 500 ГБ |
| **AI-токены/мес** | 10 000 | 500 000 | 5 000 000 |
| **AI-ассистент** | ❌ | ✅ | ✅ |
| **Live-трансляции** | ✅ | ✅ | ✅ |
| **Экспорт отчётов** | CSV | CSV + JSON | CSV + JSON + PDF |
| **Видеозвонки** | ❌ | До 10 чел. | До 100 чел. |
| **Кастомный брендинг** | ❌ | ❌ | ✅ |
| **API-доступ** | ❌ | ✅ | ✅ |
| **Техподдержка** | Community (форум) | Standard (24ч) | Priority (4ч) + выделенный менеджер |
| **Срок сертификата** | 3 мес. | 12 мес. | 12 мес. |
| **Продление** | Автоматическое | По подписке | По подписке |

#### 12.2.3. API-эндпоинты

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/tariffs` | GET | Список тарифных планов |
| `/tariffs/{id}` | GET | Детали тарифа |
| `/orgs/{id}/subscription` | GET | Текущая подписка компании |
| `/orgs/{id}/subscription/upgrade` | POST | Повысить тариф |
| `/orgs/{id}/subscription/downgrade` | POST | Понизить тариф |
| `/orgs/{id}/subscription/renew` | POST | Продлить подписку |
| `/orgs/{id}/subscription/cancel` | POST | Отменить подписку |
| `/admin/tariffs` | POST/PATCH/DELETE | Управление тарифами |

#### 12.2.4. Middleware проверки лимитов

```python
async def check_tariff_limit(org_id: str, resource: str, db: Session):
    """Проверяет, не превышен ли лимит тарифа."""
    subscription = db.query(Subscription).filter(
        Subscription.org_id == org_id,
        Subscription.status == "active"
    ).first()

    if not subscription:
        raise HTTPException(402, "No active subscription")

    plan = subscription.tariff_plan
    current_count = get_resource_count(org_id, resource, db)

    limits = {
        "employees": plan.max_employees,
        "teams": plan.max_teams,
        "projects": plan.max_projects,
    }

    if limits.get(resource) and current_count >= limits[resource]:
        raise HTTPException(403, f"Tariff limit reached for {resource}")
```

---

## 13. МОДУЛЬ ВИДЕОЗВОНКОВ

### 13.1. Текущее состояние

**Видеозвонки не реализованы.** ❌ НЕ РЕАЛИЗОВАНО

Однако уже есть базовая инфраструктура:
 ✅ WebSocket-стриминг экрана (уже работает в Activity)
 ✅ Real-time обмен данными
 ✅ Живые превью через HTTP-поллинг

### 13.2. Архитектура видеозвонков

#### 13.2.1. Технологический стек

| Компонент | Технология | Описание |
|-----------|-----------|----------|
| **Сигналинг** | WebSocket (FastAPI) | Обмен SDP/ICE-кандидатами |
| **Медиа-транспорт** | WebRTC через `aiortc` | Передача аудио/видео P2P |
| **TURN/STUN-сервер** | `coturn` | NAT-traversal для P2P |
| **SFU (Selective Forwarding Unit)** | `mediasoup` или `Janus` | Для групповых звонков (>2 чел.) |
| **Запись звонков** | GStreamer / FFmpeg | Серверная запись |
| **Экранная демонстрация** | PySide6 screen capture + WebRTC | Шаринг экрана |

#### 13.2.2. Модели данных

```python
class VideoRoom(Base):
    __tablename__ = "video_rooms"

    id = Column(String, primary_key=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    name = Column(String, nullable=False)
    room_type = Column(Enum(
        "one_on_one",        # 1:1
        "group",             # Групповой
        "webinar",           # Вебинар (один говорит, остальные слушают)
        "standup"            # Стендап (быстрый)
    ))
    created_by = Column(String, ForeignKey("users.id"))
    max_participants = Column(Integer, default=10)
    is_recording = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    scheduled_at = Column(DateTime, nullable=True)    # Запланированный звонок
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

class VideoParticipant(Base):
    __tablename__ = "video_participants"

    id = Column(String, primary_key=True)
    room_id = Column(String, ForeignKey("video_rooms.id"))
    user_id = Column(String, ForeignKey("users.id"))
    role = Column(Enum("host","co_host","participant","viewer"), default="participant")
    is_muted = Column(Boolean, default=False)
    is_camera_on = Column(Boolean, default=True)
    is_screen_sharing = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=utc_now_naive)
    left_at = Column(DateTime, nullable=True)

class VideoRecording(Base):
    __tablename__ = "video_recordings"

    id = Column(String, primary_key=True)
    room_id = Column(String, ForeignKey("video_rooms.id"))
    file_path = Column(String, nullable=False)
    duration_seconds = Column(Integer)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, default=utc_now_naive)
```

#### 13.2.3. Функции видеозвонков

| Функция | Аналог в Zoom/Meet | Описание |
|---------|-------------------|----------|
| Создание комнаты | Create Meeting | Создать звонок с названием и типом |
| Приглашение участников | Invite | По ссылке или из списка участников отдела |
| Аудио/Видео | Audio/Video | WebRTC P2P или через SFU |
| Чат в звонке | In-meeting chat | Текстовый чат внутри комнаты |
| Шаринг экрана | Screen sharing | Через PySide6 capture + WebRTC |
| Запись звонка | Record | Серверная запись через GStreamer |
| Поднять руку | Raise hand | Виртуальная реакция |
| Mute/Unmute всех | Host controls | Управление для хоста |
| Расписание | Schedule | Запланировать звонок на время |
| Breakout rooms | Breakout rooms | Разделение на подгруппы |
| Виртуальный фон | Virtual background | Замена фона (через OpenCV) |

#### 13.2.4. API-эндпоинты

| Эндпоинт | Метод | Описание |
|----------|-------|----------|
| `/orgs/{id}/video/rooms` | POST | Создать комнату |
| `/orgs/{id}/video/rooms` | GET | Список комнат (активных/запланированных) |
| `/orgs/{id}/video/rooms/{rid}` | GET | Детали комнаты |
| `/orgs/{id}/video/rooms/{rid}/join` | POST | Присоединиться |
| `/orgs/{id}/video/rooms/{rid}/leave` | POST | Покинуть |
| `/orgs/{id}/video/rooms/{rid}/end` | POST | Завершить звонок |
| `ws://.../video/rooms/{rid}/signal` | WebSocket | Сигналинг (SDP/ICE) |
| `/orgs/{id}/video/rooms/{rid}/recordings` | GET | Записи звонка |
| `/orgs/{id}/video/schedule` | POST | Запланировать звонок |

#### 13.2.5. Интеграция с PySide6 (Frontend)

**Компоненты UI:**
- `VideoCallScreen` — основной экран звонка
- Сетка участников (2x2, 3x3 adaptive)
- Панель управления: микрофон, камера, шаринг, запись, рука, чат
- Мини-превью своего видео
- Чат-панель сбоку
- Список участников

**Технология захвата:**
- Камера: `QCamera` + `QMediaCaptureSession` (PySide6)
- Микрофон: `QAudioInput` (PySide6)
- Экран: `mss` (уже используется) или `QScreen.grabWindow()`
- WebRTC: `aiortc` (Python WebRTC implementation)

**Библиотеки для установки:**
```
aiortc>=1.9.0          # Python WebRTC
aioice>=0.9.0          # ICE for WebRTC
av>=12.0.0             # Audio/Video codecs (PyAV)
```

---

## 14. СВОДНАЯ ТАБЛИЦА СТАТУСОВ

### Реализованные модули ✅

| # | Модуль | Эндпоинтов | Моделей | Экранов (UI) | Состояние |
|---|--------|-----------|---------|-------------|-----------|
| 1 | Авторизация (email + Google OAuth) | 3 | 1 (User) | 1 (AuthScreen) | ✅ Полностью |
| 2 | Onboarding (Consent + Role + Profile) | 2 | 1 (Consent) | 3 экрана | ✅ Полностью |
| 3 | Организации (CRUD + Join) | 10 | 3 (Org, Membership, JoinRequest) | 2 экрана | ✅ Полностью |
| 4 | Отделы / Команды | 6 | 2 (Team, TeamMembership) | 2 экрана | ✅ Полностью |
| 5 | Проекты | 4 | 1 (Project) | — (в дашборде) | ✅ Полностью |
| 6 | Задачи | 3 | 1 (Task) | — (в кабинете) | ✅ Полностью |
| 7 | Мониторинг активности | 8 | 4 (Session, Event, Audit, Recording) | 2 экрана | ✅ Полностью |
| 8 | AI-аналитика (KPI, скоркарты) | 3 | 1 (AIScore) | — (в отделе) | ✅ Полностью |
| 9 | Ежедневные отчёты | 4 | 2 (Report, Attachment) | — (в кабинете) | ✅ Полностью |
| 10 | Экспорт отчётов + расписание | 6 | 2 (Export, Schedule) | — | ✅ Полностью |
| 11 | Privacy-правила | 4 | 1 (PrivacyRule) | — | ✅ Полностью |
| 12 | Webhook-уведомления | 4 | 1 (NotificationHook) | 1 панель | ✅ Полностью |
| 13 | Профиль + Поиск | 5 | — | 3 экрана | ✅ Полностью |
| 14 | Live-трансляции | 2 (WS + HTTP) | — | 2 экрана | ✅ Полностью |
| 15 | ML-валидация анкет | 2 | — | — (в profile setup) | ✅ Полностью |
| 16 | ML-анализ скриншотов | — | — | — (в кабинете) | ✅ Полностью |
| 17 | Воспроизведение записей | 2 | — | 1 экран | ✅ Полностью |
| 18 | Настройки + Темы | — | — | 1 экран | ✅ Базово |

**ИТОГО РЕАЛИЗОВАНО:** 80+ эндпоинтов, 14 моделей, 18 экранов, 3 ML-модуля

### Нереализованные модули ❌

| # | Модуль | Приоритет | Сложность | Ориентировочные сроки |
|---|--------|----------|-----------|----------------------|
| 1 | Суперадмин + Сертификаты компаний | 🔴 Высокий | Средняя | 2-3 недели |
| 2 | Расширенная система ролей (RBAC) | 🔴 Высокий | Высокая | 3-4 недели |
| 3 | Система вакансий (hh-функционал) | 🟡 Средний | Высокая | 4-5 недель |
| 4 | Техническая поддержка (тикеты + FAQ + AI-чатбот) | 🟡 Средний | Высокая | 3-4 недели |
| 5 | Рейтинговая система (внешняя + внутренняя) | 🟡 Средний | Средняя | 2-3 недели |
| 6 | Монетизация (баны + платежи) | 🟡 Средний | Высокая | 4-5 недель |
| 7 | LLM-ассистент для компаний | 🟡 Средний | Средняя | 2-3 недели |
| 8 | Тарифные планы + подписки | 🟡 Средний | Средняя | 2-3 недели |
| 9 | Видеозвонки (WebRTC) | 🔴 Высокий | Очень высокая | 6-8 недель |
| 10 | Мессенджер (чат между пользователями) | 🟡 Средний | Высокая | 3-4 недели |
| 11 | Email-уведомления + приглашения | 🟢 Низкий | Низкая | 1 неделя |
| 12 | 2FA + сброс пароля | 🟢 Низкий | Низкая | 1 неделя |
| 13 | PDF-отчёты + графики | 🟢 Низкий | Средняя | 1-2 недели |

---

## 15. ДОРОЖНАЯ КАРТА РЕАЛИЗАЦИИ

### Фаза 1: Корпоративное управление (Месяц 1-2)

**Цель:** Суперадмин, сертификаты, расширенные роли

| Неделя | Задача | Результат |
|--------|--------|----------|
| 1 | Модель суперадмина + миграция БД | Роль superadmin в User |
| 1 | Административный API (/admin/*) | CRUD компаний суперадмином |
| 2 | Модель OrganizationCertificate + API | Выдача/отзыв сертификатов |
| 2 | PDF-генерация сертификата (reportlab) | Скачиваемый PDF с QR-кодом |
| 3 | Расширенный OrgRole enum | owner, director, hr_manager, etc. |
| 3 | RBAC middleware + Permission model | Гранулярный контроль доступа |
| 4 | Суперадмин-панель (Frontend) | Экран управления компаниями |
| 4 | Обновлённые экраны ролей | Новые интерфейсы для ролей |

**Новые зависимости:** `reportlab>=4.0`, `qrcode>=7.4`

### Фаза 2: HR и найм (Месяц 2-3)

**Цель:** Вакансии, приглашения, расширенный профиль

| Неделя | Задача | Результат |
|--------|--------|----------|
| 5 | Модели Vacancy + VacancyApplication | Публикация вакансий |
| 5 | Расширение User (навыки, опыт, портфолио) | Полное резюме-портфолио |
| 6 | API вакансий + поиск + отклики | Полный цикл найма |
| 6 | AI-matching навыков (TF-IDF / embeddings) | Автоматический матчинг |
| 7 | Модель Invitation + email-рассылка | Приглашения по email |
| 7 | Экраны вакансий (Frontend) | Каталог + детали + отклик |
| 8 | HR-панель (Frontend) | Управление откликами |
| 8 | Тестирование + интеграция | E2E тесты |

**Новые зависимости:** `aiosmtplib>=2.0`, `jinja2>=3.1`, `sentence-transformers>=2.0` (для AI-matching)

### Фаза 3: Монетизация и рейтинги (Месяц 3-4)

**Цель:** Платежи, тарифы, рейтинги

| Неделя | Задача | Результат |
|--------|--------|----------|
| 9 | Модели TariffPlan + Subscription | 3 тарифных плана |
| 9 | Модели Payment + интеграция ЮKassa | Приём платежей |
| 10 | Middleware проверки лимитов | Ограничения по тарифу |
| 10 | Модели UserBan + BanAppeal + оплата | Система банов с отсрочкой |
| 11 | Внешний рейтинг (EmployeePublicRating, OrgPublicRating) | Квартальные рейтинги |
| 11 | Внутренний рейтинг (EmployeeMonthlyRating) | Ежемесячные рейтинги |
| 12 | Экраны тарифов + оплаты (Frontend) | Оплата и управление подпиской |
| 12 | Экраны рейтингов (Frontend) | Лидерборд + бейджи |

**Новые зависимости:** `yookassa>=3.0`

### Фаза 4: Техподдержка и AI (Месяц 4-5)

**Цель:** Тикет-система, AI-чатбот, LLM-ассистент

| Неделя | Задача | Результат |
|--------|--------|----------|
| 13 | Модели SupportTicket + TicketMessage + FAQ | Тикет-система |
| 13 | API техподдержки | CRUD тикетов + сообщения |
| 14 | AI-чатбот первой линии (Claude API) | Автоответы + маршрутизация |
| 14 | FAQ-модуль + поиск | База знаний |
| 15 | LLM-ассистент для компаний | AI-чат + рекомендации |
| 15 | RAG-контекст из данных компании | Персонализированные ответы |
| 16 | Экраны техподдержки (Frontend) | Тикеты + чат + FAQ |
| 16 | Дашборд поддержки для суперадмина | Метрики, очередь |

**Новые зависимости:** `chromadb>=0.5` (для RAG), `tiktoken>=0.7` (подсчёт токенов)

### Фаза 5: Видеозвонки (Месяц 5-7)

**Цель:** Полнофункциональные видеозвонки внутри компаний

| Неделя | Задача | Результат |
|--------|--------|----------|
| 17 | Исследование + прототип WebRTC (aiortc) | Proof of concept P2P-звонок |
| 18 | Сигналинг-сервер (WebSocket) | Обмен SDP/ICE |
| 19 | TURN/STUN сервер (coturn) | NAT-traversal |
| 20 | SFU для групповых звонков | Масштабирование >2 участников |
| 21 | Модели VideoRoom + Participant | Управление комнатами |
| 22 | Запись звонков (GStreamer/FFmpeg) | Серверная запись |
| 23 | UI видеозвонков (Frontend) | Экран звонка, сетка, управление |
| 24 | Шаринг экрана + виртуальный фон | Дополнительные функции |

**Новые зависимости:** `aiortc>=1.9`, `aioice>=0.9`, `av>=12.0`
**Инфраструктура:** Сервер coturn, медиа-сервер (Janus/mediasoup)

### Фаза 6: Полировка и масштабирование (Месяц 7-8)

| Неделя | Задача | Результат |
|--------|--------|----------|
| 25-26 | 2FA, сброс пароля, email-уведомления | Безопасность |
| 27-28 | Мессенджер (личные сообщения) | Полноценный чат |
| 29-30 | PDF-отчёты, графики, дашборды | Визуализация |
| 31-32 | Миграция на PostgreSQL + Redis | Масштабируемость |

---

## ПРИЛОЖЕНИЕ А: Полный список переменных окружения

```env
# === База данных ===
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/projectscontrol

# === JWT ===
JWT_SECRET_KEY=<secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# === Хранилище ===
STORAGE_DRIVER=local
STORAGE_PATH=./data/recordings
PREVIEWS_PATH=./data/previews
MAX_UPLOAD_MB=2048

# === Retention ===
RETENTION_DAYS=90
EVENTS_RETENTION_DAYS=30

# === Отчёты ===
REPORTS_PATH=./data/reports
REPORTS_MAX_EXPORT_MB=50
REPORTS_MAX_RANGE_DAYS=365

# === Планировщик ===
SCHEDULE_TICK_SECONDS=300

# === OAuth ===
GOOGLE_OAUTH_CLIENT_ID=<client_id>

# === AI ===
ANTHROPIC_API_KEY=<api_key>

# === Rate Limiting ===
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# === Платежи (новое) ===
YOOKASSA_SHOP_ID=<shop_id>
YOOKASSA_SECRET_KEY=<secret>

# === Email (новое) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASSWORD=<password>

# === WebRTC (новое) ===
TURN_SERVER_URL=turn:turn.example.com:3478
TURN_USERNAME=<username>
TURN_PASSWORD=<password>
```

## ПРИЛОЖЕНИЕ Б: Требования к инфраструктуре (Production)

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| **Backend API** | 2 vCPU, 4 ГБ RAM | 4 vCPU, 8 ГБ RAM |
| **PostgreSQL** | 2 vCPU, 4 ГБ RAM, 50 ГБ SSD | 4 vCPU, 16 ГБ RAM, 200 ГБ SSD |
| **Redis** | 1 vCPU, 2 ГБ RAM | 2 vCPU, 4 ГБ RAM |
| **TURN/STUN** | 2 vCPU, 4 ГБ RAM | 4 vCPU, 8 ГБ RAM |
| **Media Server (SFU)** | 4 vCPU, 8 ГБ RAM | 8 vCPU, 16 ГБ RAM |
| **Файловое хранилище** | 100 ГБ | 1 ТБ (S3-совместимое) |
| **ML-сервер** | 2 vCPU, 4 ГБ RAM | 4 vCPU, 8 ГБ RAM + GPU |

**Рекомендуемый хостинг:** Yandex Cloud, VK Cloud, Selectel (РФ) или AWS/GCP (международный)

---

*Документ подготовлен: 16 февраля 2026*
*Версия ТЗ: 2.0*
*Автор: AI-ассистент на базе анализа кодовой базы ProjectsControl*
