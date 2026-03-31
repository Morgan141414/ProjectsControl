# ML — Machine Learning модели ProjectsControl

## Модули

### 1. Questionnaire Validator (`questionnaire_validator.py`)
Мгновенная валидация анкет пользователей при регистрации.
- Проверка корректности ФИО, email, телефона
- Оценка качества текстовых полей
- Автоматическое одобрение (score >= 70) или отклонение

### 2. Screenshot Analyzer (`screenshot_analyzer.py`)
AI-анализ скриншотов экрана сотрудников в реальном времени.
- Распознавание активных приложений
- Классификация продуктивности
- Генерация отчётов в реальном времени

### 3. API (`api.py`)
FastAPI эндпоинты для интеграции ML моделей.

## Установка
```bash
pip install -r requirements.txt
```
