# PyBridge - документация

## Содержание
- [PyBridge - кратко про модуль](#pybridge---кратко-про-модуль)
- [Краткое описание](#краткое-описание)
- [Быстрый старт](#быстрый-старт)
- [Основные понятия и терминология](#основные-понятия-и-терминология)
- [Примеры использования](#примеры-использования)
- [Подробное API](#подробное-api)
- [Вспомогательные и приватные элементы](#вспомогательные-и-приватные-элементы)
- [Файловая структура модуля](#файловая-структура-модуля)
- [Логирование и диагностика](#логирование-и-диагностика)
- [Жизненный цикл сервера / запуск кода](#жизненный-цикл-сервера--запуск-кода)
- [Рекомендации по безопасности и ограничениям](#рекомендации-по-безопасности-и-ограничениям)
- [Тонкости и советы](#тонкости-и-советы)
- [Частые ошибки и их исправление](#частые-ошибки-и-их-исправление)
- [Контакты / автор / лицензия](#контакты--автор--лицензия)
- [Приложения](#приложения)

## PyBridge - кратко про модуль

PyBridge - это модуль для выполнения Python-кода в изолированных средах внутри Ren'Py приложений. Модуль позволяет запускать код на разных версиях Python, управлять процессами и безопасно исполнять пользовательские скрипты.

## Краткое описание

PyBridge предоставляет механизм для выполнения Python-кода в отдельных процессах с контролируемыми версиями интерпретатора. Основные возможности:
- Запуск кода на разных версиях Python (3.13.7 по умолчанию)
- Пул процессов для эффективного выполнения
- Кэширование и управление временными файлами
- Асинхронное выполнение с callback-функциями
- Логирование и обработка ошибок

Модуль особенно полезен для модификаций игр, где требуется выполнение современного Python-кода в среде Ren'Py.

## Быстрый старт

```python
# В коде Ren'Py инициализация происходит автоматически
init python:
    # Выполнение простого кода
    result = pybridge.python(code="print('Hello World')")
    print(result)  # Выведет: Hello World

    # Создание своей версии Python
    pybridge.add_python("my_project", "default")
    
    # Асинхронное выполнение
    def callback(result, error=None):
        if error:
            print(f"Ошибка: {error}")
        else:
            print(f"Результат: {result}")
    
    pybridge.python_async(code="2 + 2", callback=callback)
```
## Основные понятия и терминология

- **PyBridge** - основной класс для управления выполнением кода
- **PyServer** - класс, представляющий серверный процесс Python
- **LogSystem** - система логирования модуля
- **Версия Python** - конкретная версия интерпретатора (например, "3.13.7")
- **Пул процессов** - набор заранее запущенных серверов для быстрого выполнения
- **Временная копия Python** - изолированная копия интерпретатора для безопасного выполнения

## Примеры использования

### Пример 1: Базовое выполнение кода
```python
# Синхронное выполнение
result = pybridge.python(
    version="3.13.7",
    code="import math; result = math.sqrt(16)",
    seconds=5
)
print(result)  # Выведет: 4.0
```

### Пример 2: Передача переменных в код
```python
# Передача переменных в выполняемый код
variables = {
    "name": "Иван",
    "age": 25
}

result = pybridge.python(
    code="""
greeting = f'Привет, {name}! Тебе {age} лет.'
result = greeting.upper()
""",
    variables=variables
)
print(result)  # Выведет: ПРИВЕТ, ИВАН! ТЕБЕ 25 ЛЕТ.
```

### Пример 3: Асинхронное выполнение с callback
```python
def handle_result(result, error=None):
    if error:
        renpy.notify(f"Ошибка: {error}")
    else:
        renpy.notify(f"Результат: {result}")

# Асинхронное выполнение
pybridge.python_async(
    code="import time; time.sleep(2); result = 'Готово!'",
    callback=handle_result
)
```

## Подробное API

### Класс PyBridge

Основной класс для управления выполнением Python-кода.

#### `PyBridge.__init__(version=None, path=None, server_default=None, max_age=3600, pool_size=2, safe_mode=True, debug=True, decoder=None)`

Инициализирует экземпляр PyBridge.

**Параметры:**

| Параметр       | Тип      | По умолчанию | Описание                         |
| -------------- | -------- | ------------ | -------------------------------- |
| version        | str      | None         | Версия Python по умолчанию       |
| path           | str      | None         | Путь к исполняемому файлу Python |
| server_default | str      | None         | Путь к серверному файлу          |
| max_age        | int      | 3600         | Время жизни кэша в секундах      |
| pool_size      | int      | 2            | Размер пула процессов            |
| safe_mode      | bool     | False        | Режим безопасного выполнения     |
| debug          | bool     | True         | Включение отладки                |
| decoder        | callable | None         | Функция декодирования вывода     |


**Исключения:**
- `PyBridgeInitException`: при повторном создании экземпляра

#### `PyBridge.add_python(version, path, server_file="default")`

Добавляет версию Python для использования.

| Параметр    | Тип | По умолчанию | Описание                |
| ----------- | --- | ------------ | ----------------------- |
| version     | str | -            | Идентификатор версии    |
| path        | str | -            | Путь к интерпретатору   |
| server_file | str | "default"    | Путь к серверному файлу |


**Параметры:**

```python
pybridge.add_python("my_version", "path/to/python", "path/to/server.py")
```

#### `PyBridge.python(version="3.13.7", code="", seconds=5, args=None, variables=None, cwd=None, input_data=None, use_pool=True)`

Выполняет Python-код синхронно.

**Параметры:

| Параметр   | Тип       | По умолчанию | Описание                    |
| ---------- | --------- | ------------ | --------------------------- |
| version    | str       | "3.13.7"     | Версия Python               |
| code       | str       | ""           | Код для выполнения          |
| seconds    | int       | 5            | Таймаут выполнения          |
| args       | list      | None         | Аргументы командной строки  |
| variables  | dict      | None         | Переменные для контекста    |
| cwd        | str       | None         | Рабочая директория          |
| input_data | str/bytes | None         | Входные данные для процесса |
| use_pool   | bool      | True         | Использовать пул процессов  |

**Возвращает:** str - результат выполнения (stdout)

**Исключения:**
- `PyBridgeExecException`: при ошибке выполнения

```python
result = pybridge.python(
    version="3.13.7",
    code="x = 10; y = 20; result = x + y",
    seconds=10
)
```

#### `PyBridge.python_async(version="3.13.7", code="", callback=None, seconds=5, args=None, variables=None, cwd=None, input_data=None)`

Выполняет Python-код асинхронно.

**Параметры:**
Аналогично `python()`, плюс:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| callback | callable | None | Функция обратного вызова |

```python
def my_callback(result, error):
    if error:
        print(f"Ошибка: {error}")
    else:
        print(f"Результат: {result}")

pybridge.python_async(code="2 * 3", callback=my_callback)
```

#### `PyBridge.create_server(version="3.13.7", port=5000)`

Создает серверный процесс.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| version | str | "3.13.7" | Версия Python |
| port | int | 5000 | Порт для сервера |

**Возвращает:** `PyServer` - объект сервера

### Класс PyServer

Управляет серверным процессом Python.

#### `PyServer.send(code, timeout=5, buffer_size=65536)`

Отправляет код на выполнение серверу.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| code | str | - | Код для выполнения |
| timeout | int | 5 | Таймаут соединения |
| buffer_size | int | 65536 | Размер буфера |

**Возвращает:** str - результат выполнения

#### `PyServer.send_async(data, timeout=15, callback=None)`

Асинхронная отправка кода серверу.

### Класс LogSystem

Система логирования с ротацией файлов.

#### `LogSystem.log(message)`

Записывает сообщение в лог.
## Вспомогательные и приватные элементы

Следующие элементы считаются внутренними и не рекомендуются к использованию напрямую, если вы не понимаете последствий:

- Все методы/поля с префиксом `__` (например, `__temp_pythons`, `__create_temp_file`, `__get_hash`, `__cache_info`).
    
- `__wrapper`, `__popenen` — низкоуровневые helpers.
    
- Внутренние структуры lock'ов: `_lock`, `__tasks_lock`.

Эти элементы предназначены для внутренней логики и могут измениться между версиями.
### Внутренние методы PyBridge (internal)

- `_get_temp_python(version)`: Создает и возвращает путь к временной копии Python для изоляции
- `_exec(python_path, seconds, flags, cwd, input_data)`: Внутренний метод выполнения процесса Python
- `_decoder(stdout, stderr)`: Декодирует вывод процесса с учетом локали системы
- `_get_server_from_pool()`: Получает доступный сервер из пула процессов
- `_has_pip(python_path, timeout)`: Проверяет наличие pip в интерпретаторе
- `_log(message)`: Внутреннее логирование с префиксом PyBridge
- `_find_free(used_set, start, end)`: Находит свободный номер в диапазоне
- `__wrapper(code, variables)`: Создает обертку для безопасного выполнения кода
- `__clear_cache()`: Очищает устаревшие кэшированные файлы
- `__get_hash(code)`: Генерирует хеш для кэширования
- `__get_file_hash(file_path)`: Генерирует хеш файла
- `__set_cache(path, key)`: Сохраняет путь в кэше
- `__get_cache(key)`: Получает данные из кэша
- `__create_temp_file(file, cache)`: Создает временную копию файла
- `__popenen(python_path, flags, cwd)`: Запускает процесс Python
- `__wait_for_server(port, timeout)`: Ожидает запуск сервера

### Внутренние методы PyServer (internal)

- `start_logging()`: Запускает поток для логирования вывода сервера
- `tasks_count()`: Возвращает количество активных задач сервера

### Внутренние методы LogSystem (internal)

- `open()`: Открывает файл лога
- `close()`: Закрывает файл лога

**Примечание**: Методы с двойным подчеркиванием (`__method`) считаются приватными и не предназначены для прямого использования.

## Файловая структура модуля

```
game/
├── PyBridge/
│   ├── python/                    # Встроенные интерпретаторы Python
│   │   ├── win/
│   │   │   └── python.exe         # Python для Windows
│   │   ├── linux/
│   │   │   └── bin/python3        # Python для Linux
│   │   └── mac/
│   │       └── bin/python3        # Python для macOS
│   └── python_embed_server.py     # Стандартный серверный скрипт
├── v1rus_team/
│   └── PyBridge/
│       └── logs/                  # Директория логов
│           ├── pybridge.log       # Основной лог модуля
│           └── pybridge_server_*.log  # Логи отдельных серверов
└── [ваш_мод]/
    └── mod_assets/
        └── scripts/
            └── *.rpy              # Ваши пользовательские скрипты
```

## Логирование и диагностика

### Система логирования

PyBridge использует многоуровневую систему логирования:

1. **Основное логирование** - `v1rus_team/PyBridge/logs/pybridge.log`
2. **Логи серверов** - `v1rus_team/PyBridge/logs/pybridge_server_<port>.log`
3. **Резервное логирование** - через `renpy.log()` при ошибках файловой системы

### Использование функции log в выполняемом коде

При выполнении кода автоматически создается функция `log` - безопасная обертка над `print`:

```python
result = pybridge.python(
    version="3.13.7",
    code="""
log("Начало сложных вычислений")
import time

# Длительная операция
start_time = time.time()
data = [i**2 for i in range(10000)]
end_time = time.time()

log(f"Вычисления заняли: {end_time - start_time:.2f} секунд")
log(f"Создано {len(data)} элементов")
result = sum(data)
"""
)
```

### Диагностика и отладка

```python
init python:
    def debug_pybridge():
        """Комплексная диагностика PyBridge"""
        try:
            # Проверка доступных версий
            versions = pybridge.list_versions()
            print(f"Доступные версии Python: {versions}")
            
            # Проверка активных серверов
            active_servers = pybridge.get_servers()
            print(f"Активные серверы: {len(active_servers)}")
            
            # Детальная информация о версиях
            for version in versions:
                try:
                    info = pybridge.get_info(version)
                    print(f"Информация о {version}: {info.get('version', 'N/A')}")
                except Exception as e:
                    print(f"Ошибка получения информации о {version}: {e}")
            
            # Отладочная информация
            pybridge.debug_info()
            
            return "Диагностика завершена"
        except Exception as e:
            return f"Ошибка диагностики: {e}"

    # Запуск диагностики
    debug_result = debug_pybridge()
    print(debug_result)
```

### Мониторинг состояния серверов

```python
init python:
    def check_server_health():
        """Проверка здоровья всех серверов"""
        healthy_servers = []
        problematic_servers = []
        
        for server in pybridge.get_all_servers():
            if server.is_alive():
                healthy_servers.append(server)
            else:
                problematic_servers.append(server)
        
        print(f"Здоровые серверы: {len(healthy_servers)}")
        print(f"Проблемные серверы: {len(problematic_servers)}")
        
        # Перезапуск проблемных серверов
        for server in problematic_servers:
            try:
                pybridge.close_server(server)
                new_server = pybridge.create_server(server.version())
                print(f"Перезапущен сервер {server.version()} на порту {new_server.PORT}")
            except Exception as e:
                print(f"Ошибка перезапуска сервера {server.version()}: {e}")
```

## Жизненный цикл сервера / запуск кода

### Детальный процесс выполнения кода

1. **Инициализация среды**
   ```python
   # Создается временная копия Python
   temp_python = pybridge._get_temp_python("3.13.7")
   ```

2. **Подготовка кода**
   ```python
   # Код оборачивается для безопасного выполнения
   wrapped_code = pybridge.__wrapper("print('Hello')", {})
   ```

3. **Выбор способа выполнения**
   - Через пул процессов (use_pool=True)
   - Прямой запуск процесса (use_pool=False)

4. **Обработка результатов**
   - Декодирование вывода
   - Обработка ошибок
   - Очистка временных ресурсов

### Управление временем жизни сервера

```python
init python:
    class ServerManager:
        def __init__(self):
            self.last_activity = time.time()
            
        def keep_alive(self):
            """Поддерживает серверы активными"""
            current_time = time.time()
            if current_time - self.last_activity > 300:  # 5 минут
                self._ping_servers()
                self.last_activity = current_time
        
        def _ping_servers(self):
            """Пинг серверов для поддержания активности"""
            for version in pybridge.list_versions():
                try:
                    pybridge.python(
                        version=version,
                        code="result = 'ping'",
                        seconds=2,
                        use_pool=True
                    )
                except Exception as e:
                    print(f"Пинг сервера {version} не удался: {e}")
    
    # Создание менеджера серверов
    server_manager = ServerManager()
    
    # Регулярный вызов в игровом цикле
    def periodic_keep_alive():
        server_manager.keep_alive()
    
    # Вызов каждые 2 минуты (пример для Ren'Py)
    # config.periodic_callback = periodic_keep_alive
```

### Автоматическое восстановление серверов

```python
init python:
    def execute_with_fallback(code, version="3.13.7", max_retries=2):
        """Выполнение кода с автоматическим восстановлением при сбоях"""
        for attempt in range(max_retries + 1):
            try:
                result = pybridge.python(
                    version=version,
                    code=code,
                    seconds=10,
                    use_pool=True
                )
                return result
            except PyBridgeServerException as e:
                if attempt < max_retries:
                    print(f"Попытка {attempt + 1}: Перезапуск сервера...")
                    # Закрываем проблемный сервер
                    try:
                        pybridge.close_server(pybridge._get_server_from_pool())
                    except:
                        pass
                    # Создаем новый
                    pybridge.create_server(version=version)
                    time.sleep(1)  # Даем время на запуск
                else:
                    raise e
    
    # Использование
    try:
        result = execute_with_fallback("import os; result = os.cpu_count()")
        print(f"Количество ядер: {result}")
    except Exception as e:
        print(f"Все попытки завершились ошибкой: {e}")
```

## Рекомендации по безопасности и ограничениям

### Создание изолированных сред

```python
init python:
    # РЕКОМЕНДУЕТСЯ: Создание отдельных версий для каждого мода
    pybridge.add_python("my_mod_v1", "default")
    pybridge.add_python("another_mod_v1", "default")
    
    # НЕ РЕКОМЕНДУЕТСЯ: Использование общей версии
    # pybridge.python(version="3.13.7", code="...")  # Может конфликтовать!
```

### Ограничение прав доступа

```python
init python:
    def safe_execute(code, timeout=5):
        """Безопасное выполнение пользовательского кода"""
        # Ограничение времени выполнения
        result = pybridge.python(
            code=code,
            seconds=timeout,
            safe_mode=True,
            use_pool=True  # Изоляция в пуле процессов
        )
        return result
    
    # Пример использования с ненадежным кодом
    user_code = """
# Потенциально опасные операции блокируются в safe_mode
import sys
try:
    # Эти операции могут быть ограничены
    sys.exit(1)
except:
    result = "Безопасное выполнение"
"""
    
    safe_result = safe_execute(user_code, timeout=3)
```

### Обработка больших данных

```python
init python:
    def process_large_data(data_chunks):
        """Обработка больших данных с контролем памяти"""
        results = []
        
        for i, chunk in enumerate(data_chunks):
            try:
                result = pybridge.python(
                    code=f"""
# Обработка чанка данных
chunk = {chunk}
result = sum(x * 2 for x in chunk)
""",
                    seconds=30,  # Увеличенный таймаут
                    use_pool=True
                )
                results.append(result)
                
                # Очистка памяти между выполнениями
                if i % 10 == 0:
                    pybridge.reset()
                    
            except PyBridgeExecException as e:
                print(f"Ошибка обработки чанка {i}: {e}")
                continue
        
        return results
```

## Тонкости и советы (Best practices)

### 1. Эффективное использование пула процессов

```python
init python:
    def optimized_batch_processing(tasks):
        """Пакетная обработка с оптимальным использованием пула"""
        results = []
        
        # Предварительный нагрев пула
        if not pybridge.get_servers():
            pybridge.init_pool()
        
        for task in tasks:
            result = pybridge.python(
                code=task['code'],
                variables=task.get('variables', {}),
                use_pool=True,  # Ключевая оптимизация
                seconds=task.get('timeout', 5)
            )
            results.append(result)
        
        return results
```

### 2. Кэширование часто используемых скриптов

```python
init python:
    # Кэширование тяжелых скриптов
    def get_cached_script_result(script_path, version="3.13.7"):
        """Выполнение скрипта с кэшированием"""
        return pybridge.exec_temp_file(
            src_path=script_path,
            version=version,
            cache=True,  # Кэширование включено
            seconds=30
        )
    
    # Первый вызов - создается кэш
    result1 = get_cached_script_result("scripts/heavy_calculation.py")
    
    # Последующие вызовы - используется кэш
    result2 = get_cached_script_result("scripts/heavy_calculation.py")
```

### 3. Грамотная обработка ошибок

```python
init python:
    def robust_python_execution(code, **kwargs):
        """Надежное выполнение кода с комплексной обработкой ошибок"""
        try:
            return pybridge.python(code=code, **kwargs)
            
        except PyBridgeExecException as e:
            # Ошибки выполнения кода
            print(f"Ошибка выполнения: {e}")
            return None
            
        except PyBridgeServerException as e:
            # Проблемы с сервером
            print(f"Ошибка сервера: {e}")
            return None
            
        except PyBridgeCacheException as e:
            # Проблемы с кэшем
            print(f"Ошибка кэша: {e}")
            # Продолжаем без кэша
            kwargs['use_pool'] = False
            return pybridge.python(code=code, **kwargs)
```

### 4. Асинхронные операции для UI

```python
init python:
    def async_with_progress(code, callback, progress_callback=None):
        """Асинхронное выполнение с отслеживанием прогресса"""
        progress = 0
        
        def update_progress():
            nonlocal progress
            progress += 25
            if progress_callback and progress <= 100:
                renpy.invoke_in_main_thread(progress_callback, progress)
        
        def execute():
            # Имитация прогресса
            for i in range(4):
                time.sleep(0.5)
                update_progress()
            
            # Основное выполнение
            try:
                result = pybridge.python(code=code, seconds=30)
                renpy.invoke_in_main_thread(callback, result, None)
            except Exception as e:
                renpy.invoke_in_main_thread(callback, None, e)
        
        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()
    
    # Использование в интерфейсе
    def show_loading_screen(progress):
        renpy.show_screen("loading_screen", progress=progress)
    
    def on_calculation_done(result, error):
        if error:
            renpy.notify(f"Ошибка: {error}")
        else:
            renpy.notify(f"Результат: {result}")
        renpy.hide_screen("loading_screen")
    
    # Запуск
    async_with_progress(
        code="import time; time.sleep(2); result = 'Готово!'",
        callback=on_calculation_done,
        progress_callback=show_loading_screen
    )
```

## Частые ошибки и их исправление (Troubleshooting)

### Ошибка: "PyBridge instance already created"

**Симптомы**: При создании PyBridge возникает исключение
**Причина**: Глобальный экземпляр уже создан в `init -9999 python`
**Решение**: Используйте готовый экземпляр `pybridge`

```python
# Неправильно:
init python:
    my_bridge = PyBridge()  # Ошибка!

# Правильно:
init python:
    # Используйте существующий экземпляр
    result = pybridge.python(code="2+2")
```

### Ошибка: "Default Python executable not found"

**Симптомы**: Модуль не может найти интерпретатор Python
**Причина**: Файлы Python не скопированы в game/PyBridge/
**Решение**: Убедитесь в наличии структуры:
```
game/PyBridge/python/win/python.exe
game/PyBridge/python/linux/bin/python3  
game/PyBridge/python/mac/bin/python3
```

### Ошибка: "No free slots in range 5000-6000"

**Симптомы**: Не удается запустить сервер из-за занятых портов
**Причина**: Много активных серверов или конфликт портов
**Решение**:

```python
init python:
    # Очистка и перезапуск
    pybridge.cleanup()
    pybridge.reset()
    
    # Ручное указание порта
    server = pybridge.create_server(port=6001)
```

### Ошибка: "Python process timeout after X seconds"

**Симптомы**: Код выполняется дольше разрешенного времени
**Решение**:

```python
init python:
    # Увеличение таймаута
    result = pybridge.python(
        code="import time; time.sleep(10); result = 'done'",
        seconds=15  # Увеличиваем таймаут
    )
    
    # Или оптимизация кода
    optimized_code = """
# Вместо time.sleep используйте эффективные алгоритмы
result = sum(i for i in range(1000000))  # Быстрее чем sleep
"""
```

### Ошибка: "Failed to write to log file"

Ошибка не критичная и может быть встречена только в config.log
**Симптомы**: Проблемы с записью логов
**Причина**: Отсутствуют права на запись или диск переполнен
**Решение**:

```python
init python:
    # Проверка доступности директории логов
    import os
    log_dir = "v1rus_team/PyBridge/logs"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception as e:
            print(f"Не удалось создать директорию логов: {e}")
    
    # Использование renpy.log как запасного варианта
    renpy.log("Резервное логирование PyBridge")
```

### Ошибки производительности

**Симптомы**: Медленное выполнение кода
**Решение**:

```python
init python:
    def optimize_performance():
        """Оптимизация производительности PyBridge"""
        
        # 1. Использование пула процессов
        pybridge.init_pool()
        
        # 2. Кэширование часто используемых скриптов
        pybridge.exec_temp_file("common_scripts.py", cache=True)
        
        # 3. Предварительная загрузка модулей
        # Только есть риск что из пула попадется несколько разных процессов если пулл больше одного
        for module in ["math", "json", "random"]:
            try:
                pybridge.python(code=f"import {module}", use_pool=True)
            except:
                pass
        
        # 4. Регулярная очистка кэша
        pybridge.reset()
```

### Диагностика сетевых проблем

```python
init python:
    def diagnose_connection_issues():
        """Диагностика проблем с соединением серверов"""
        import socket
        
        for server in pybridge.get_all_servers():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', server.PORT))
                sock.close()
                
                if result == 0:
                    print(f"Сервер на порту {server.PORT} доступен")
                else:
                    print(f"Сервер на порту {server.PORT} недоступен")
            except Exception as e:
                print(f"Ошибка проверки порта {server.PORT}: {e}")
```

## Контакты / автор / лицензия

**Разработчик**: v1rus team  
**Лицензия**: MIT License
**Версия модуля**: 10.10.2025 
**Совместимость**: Ren'Py 7.x+  

**Канал поддержки**: [v1rus team Telegram](https://t.me/+VewEitmB66k0MmQy)  
**Сообщения о ошибках**: Через платформу распространения мода или в канал поддержки

**Важно**: При использовании PyBridge в ваших модах укажите авторство и соблюдайте условия лицензии.

## Приложения

### Полный пример использования

```python
init python:
    class PyBridgeHelper:
        """Вспомогательный класс для работы с PyBridge"""
        
        def __init__(self, mod_name):
            self.mod_name = mod_name
            self.setup_environment()
        
        def setup_environment(self):
            """Настройка среды выполнения для мода"""
            # Создание изолированной версии Python
            pybridge.add_python(f"{self.mod_name}_python", "default")
            
            # Предварительная инициализация пула
            pybridge.init_pool()
            
            # Предзагрузка common модулей
            self.preload_modules(["json", "math", "random", "time"])
        
        def preload_modules(self, modules):
            """Предзагрузка модулей в пул процессов"""
            for module in modules:
                try:
                    pybridge.python(
                        code=f"import {module}",
                        use_pool=True,
                        seconds=2
                    )
                except Exception as e:
                    print(f"Не удалось предзагрузить {module}: {e}")
        
        def safe_execute(self, code, timeout=10, variables=None):
            """Безопасное выполнение кода с обработкой ошибок"""
            try:
                return pybridge.python(
                    version=f"{self.mod_name}_python",
                    code=code,
                    seconds=timeout,
                    variables=variables or {},
                    use_pool=True
                )
            except PyBridgeException as e:
                print(f"Ошибка выполнения кода в {self.mod_name}: {e}")
                return None
    
    # Использование в моде
    mod_bridge = PyBridgeHelper("my_awesome_mod")
    
    # Выполнение кода
    result = mod_bridge.safe_execute("""
import random
numbers = [random.randint(1, 100) for _ in range(10)]
result = {
    'numbers': numbers,
    'sum': sum(numbers),
    'average': sum(numbers) / len(numbers)
}
""")
```

### Пример серверного протокола

```python
# Пример ручного взаимодействия с сервером PyBridge
import socket
import json

def send_to_pybridge_server(port, code):
    """Прямая отправка кода на сервер PyBridge"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        client.connect(('127.0.0.1', port))
        
        # Отправка кода
        client.send(code.encode('utf-8'))
        
        # Получение ответа
        response = client.recv(65536).decode('utf-8')
        client.close()
        
        return response
    except Exception as e:
        return f"ERROR: {e}"

# Использование
response = send_to_pybridge_server(5000, "print('Hello Server'); result = 42")
print(f"Ответ сервера: {response}")  # RESULT:42
```

### Пример использования PyServer для кастомной функциональности

```python
init python:
    class CustomPyBridgeClient:
        """Кастомный клиент для расширенного взаимодействия с PyServer"""
        
        def __init__(self, version="3.13.7"):
            self.version = version
            self.server = None
            self.connect()
        
        def connect(self):
            """Установка соединения с сервером"""
            try:
                self.server = pybridge.create_server(
                    version=self.version,
                    port=5000
                )
                print(f"Подключено к серверу Python {self.version} на порту {self.server.PORT}")
            except PyBridgeServerException as e:
                print(f"Ошибка подключения: {e}")
                self.server = None
        
        def execute_with_retry(self, code, max_retries=3, timeout=10):
            """Выполнение кода с повторными попытками"""
            for attempt in range(max_retries):
                try:
                    if not self.server or not self.server.is_alive():
                        self.connect()
                        if not self.server:
                            continue
                    
                    response = self.server.send(code, timeout=timeout)
                    
                    if response.startswith("RESULT:"):
                        return response[7:]  # Убираем "RESULT:"
                    elif response.startswith("ERROR:"):
                        print(f"Ошибка выполнения: {response[6:]}")
                        continue
                    else:
                        return response
                        
                except Exception as e:
                    print(f"Попытка {attempt + 1} не удалась: {e}")
                    if attempt < max_retries - 1:
                        self.connect()
            
            raise PyBridgeExecException(f"Не удалось выполнить код после {max_retries} попыток")
        
        def import_module(self, module_name):
            """Импорт модуля на сервере"""
            return self.execute_with_retry(f"IMPORT:{module_name}")
        
        def close(self):
            """Закрытие соединения"""
            if self.server:
                pybridge.close_server(self.server)
                self.server = None
    
    # Использование кастомного клиента
    def example_custom_client():
        client = CustomPyBridgeClient("3.13.7")
        
        try:
            # Импорт необходимых модулей
            client.import_module("json")
            client.import_module("math")
            
            # Выполнение сложного кода
            result = client.execute_with_retry("""
import json
import math

data = {
    "values": [math.sin(i * 0.1) for i in range(10)],
    "stats": {
        "max": max([math.sin(i * 0.1) for i in range(10)]),
        "min": min([math.sin(i * 0.1) for i in range(10)]),
        "average": sum([math.sin(i * 0.1) for i in range(10)]) / 10
    }
}

result = json.dumps(data, indent=2)
""", timeout=15)
            
            print("Результат выполнения:")
            print(result)
            
        finally:
            client.close()
    
    # Запуск примера
    # example_custom_client()
```

### Пример асинхронной работы с PyServer

```python
init python:
    class AsyncPyBridgeManager:
        """Менеджер для асинхронной работы с несколькими серверами"""
        
        def __init__(self, versions=None):
            self.versions = versions or ["3.13.7"]
            self.servers = {}
            self.setup_servers()
        
        def setup_servers(self):
            """Настройка серверов для каждой версии"""
            for version in self.versions:
                try:
                    server = pybridge.create_server(version=version)
                    self.servers[version] = server
                    print(f"Сервер для {version} запущен на порту {server.PORT}")
                except PyBridgeServerException as e:
                    print(f"Не удалось запустить сервер для {version}: {e}")
        
        def execute_parallel(self, tasks):
            """Параллельное выполнение задач на разных серверах"""
            results = {}
            threads = []
            
            def worker(version, code, task_id):
                try:
                    if version in self.servers:
                        result = self.servers[version].send(code)
                        results[task_id] = result
                    else:
                        results[task_id] = f"ERROR: Сервер для {version} не доступен"
                except Exception as e:
                    results[task_id] = f"ERROR: {e}"
            
            # Запуск задач в отдельных потоках
            for task_id, task in enumerate(tasks):
                thread = threading.Thread(
                    target=worker,
                    args=(task.get('version', '3.13.7'), task['code'], task_id)
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # Ожидание завершения всех потоков
            for thread in threads:
                thread.join(timeout=30)  # Таймаут 30 секунд
            
            return results
        
        def close_all(self):
            """Закрытие всех серверов"""
            for version, server in list(self.servers.items()):
                try:
                    pybridge.close_server(server)
                    print(f"Сервер для {version} закрыт")
                except Exception as e:
                    print(f"Ошибка закрытия сервера {version}: {e}")
            
            self.servers.clear()
    
    # Пример использования менеджера
    def example_parallel_execution():
        manager = AsyncPyBridgeManager(["3.13.7"])
        
        try:
            tasks = [
                {
                    'version': '3.13.7',
                    'code': "import time; time.sleep(2); result = 'Задача 1 завершена'"
                },
                {
                    'version': '3.13.7', 
                    'code': "import time; time.sleep(1); result = 'Задача 2 завершена'"
                },
                {
                    'version': '3.13.7',
                    'code': "result = sum(i*i for i in range(1000))"
                }
            ]
            
            start_time = time.time()
            results = manager.execute_parallel(tasks)
            end_time = time.time()
            
            print(f"Параллельное выполнение заняло: {end_time - start_time:.2f} секунд")
            
            for task_id, result in results.items():
                print(f"Задача {task_id}: {result}")
                
        finally:
            manager.close_all()
    
    # Запуск примера
    # example_parallel_execution()
```

### Пример реализации кастомного серверного протокола

```python
init python:
    class CustomProtocolHandler:
        """Обработчик кастомного протокола поверх PyServer"""
        
        def __init__(self, server):
            self.server = server
            self.session_data = {}
        
        def send_command(self, command_type, data=None):
            """Отправка структурированной команды серверу"""
            if data is None:
                data = {}
            
            # Создание команды в формате JSON
            command = {
                "type": command_type,
                "data": data,
                "timestamp": time.time(),
                "session_id": id(self)
            }
            
            code = f"""
import json
command = json.loads('{json.dumps(command)}')
            
if command['type'] == 'calculate':
    # Обработка команды calculate
    expression = command['data'].get('expression', '0')
    result = eval(expression)
elif command['type'] == 'store':
    # Обработка команды store
    key = command['data'].get('key')
    value = command['data'].get('value')
    if key and value is not None:
        stored_data = globals().get('_custom_storage', {{}})
        stored_data[key] = value
        globals()['_custom_storage'] = stored_data
        result = f"Сохранено: {{key}} = {{value}}"
    else:
        result = "ERROR: Неверные параметры"
elif command['type'] == 'retrieve':
    # Обработка команды retrieve
    key = command['data'].get('key')
    stored_data = globals().get('_custom_storage', {{}})
    result = stored_data.get(key, "Не найдено")
else:
    result = "ERROR: Неизвестная команда"

result = str(result)
"""
            
            try:
                response = self.server.send(code)
                if response.startswith("RESULT:"):
                    return response[7:]
                else:
                    return f"ERROR: {response}"
            except Exception as e:
                return f"ERROR: {e}"
        
        def calculate(self, expression):
            """Вычисление математического выражения"""
            return self.send_command("calculate", {"expression": expression})
        
        def store_data(self, key, value):
            """Сохранение данных в сессии сервера"""
            return self.send_command("store", {"key": key, "value": value})
        
        def retrieve_data(self, key):
            """Получение данных из сессии сервера"""
            return self.send_command("retrieve", {"key": key})
    
    # Пример использования кастомного протокола
    def example_custom_protocol():
        server = pybridge.create_server(version="3.13.7")
        handler = CustomProtocolHandler(server)
        
        try:
            # Вычисление выражений
            result1 = handler.calculate("2 + 2 * 2")
            print(f"2 + 2 * 2 = {result1}")
            
            result2 = handler.calculate("math.sqrt(16)")  # Нужен import math
            print(f"math.sqrt(16) = {result2}")
            
            # Работа с данными
            handler.store_data("player_name", "Алексей")
            handler.store_data("score", 100)
            
            name = handler.retrieve_data("player_name")
            score = handler.retrieve_data("score")
            print(f"Игрок: {name}, Счет: {score}")
            
        finally:
            pybridge.close_server(server)
    
    # Запуск примера
    # example_custom_protocol()
```

### Тестирование функциональности

```python
init python:
    def run_pybridge_tests():
        """Набор тестов для проверки функциональности PyBridge"""
        tests = [
            {
                "name": "Простое вычисление",
                "code": "result = 2 + 2",
                "expected": "4"
            },
            {
                "name": "Импорт модуля", 
                "code": "import math; result = math.pi",
                "expected": "3.141592653589793"
            },
            {
                "name": "Работа с переменными",
                "code": "result = f'{name} is {age} years old'",
                "variables": {"name": "Alice", "age": 25},
                "expected": "Alice is 25 years old"
            }
        ]
        
        for test in tests:
            try:
                result = pybridge.python(
                    code=test["code"],
                    variables=test.get("variables", {}),
                    seconds=5
                )
                
                if result == test["expected"]:
                    print(f"✓ {test['name']}: УСПЕХ")
                else:
                    print(f"✗ {test['name']}: ОШИБКА (ожидалось: {test['expected']}, получено: {result})")
                    
            except Exception as e:
                print(f"✗ {test['name']}: ИСКЛЮЧЕНИЕ ({e})")
    
    # Запуск тестов при инициализации
    # run_pybridge_tests()
```

### Пример интеграции с игровыми механиками

```python
init python:
    class GameIntegrationExample:
        """Пример интеграции PyBridge с игровыми механиками"""
        
        def __init__(self):
            self.procedural_content = {}
            self.dynamic_variables = {}
        
        def generate_procedural_content(self, seed=None):
            """Генерация процедурного контента через Python"""
            code = f"""
import random
{"random.seed(" + str(seed) + ")" if seed else ""}

# Генерация случайного уровня
level_data = {{
    "rooms": [],
    "enemies": [],
    "items": []
}}

# Генерация комнат
for i in range(random.randint(5, 10)):
    room = {{
        "id": i,
        "size": (random.randint(3, 8), random.randint(3, 8)),
        "connections": [],
        "type": random.choice(["normal", "treasure", "enemy"])
    }}
    level_data["rooms"].append(room)

# Генерация врагов
enemy_types = ["goblin", "skeleton", "orc", "spider"]
for i in range(random.randint(3, 7)):
    enemy = {{
        "type": random.choice(enemy_types),
        "health": random.randint(10, 30),
        "damage": random.randint(2, 8),
        "room": random.randint(0, len(level_data["rooms"]) - 1)
    }}
    level_data["enemies"].append(enemy)

result = level_data
"""
            
            try:
                result_json = pybridge.python(code=code, seconds=10)
                # Парсинг JSON результата
                self.procedural_content = json.loads(result_json)
                return self.procedural_content
            except Exception as e:
                print(f"Ошибка генерации контента: {e}")
                return None
        
        def calculate_dynamic_difficulty(self, player_level, success_rate):
            """Динамический расчет сложности через ML-like алгоритмы"""
            code = f"""
# Упрощенный алгоритм адаптивной сложности
player_level = {player_level}
success_rate = {success_rate}

# Базовые параметры
base_difficulty = player_level * 0.5

# Корректировка на основе успешности
if success_rate > 0.8:
    # Игрок успешен - увеличиваем сложность
    adjustment = 1.2
elif success_rate < 0.4:
    # Игрок struggles - уменьшаем сложность
    adjustment = 0.8
else:
    adjustment = 1.0

final_difficulty = base_difficulty * adjustment

# Ограничение диапазона
final_difficulty = max(1, min(final_difficulty, 10))

result = {{
    "difficulty": round(final_difficulty, 1),
    "enemy_health_multiplier": final_difficulty * 0.8,
    "enemy_damage_multiplier": final_difficulty * 0.6,
    "reward_multiplier": final_difficulty * 0.3
}}
"""
            
            try:
                result_json = pybridge.python(code=code, seconds=5)
                return json.loads(result_json)
            except Exception as e:
                print(f"Ошибка расчета сложности: {e}")
                return {"difficulty": 1.0, "enemy_health_multiplier": 1.0, 
                       "enemy_damage_multiplier": 1.0, "reward_multiplier": 1.0}
    
    # Использование в игре
    game_integration = GameIntegrationExample()
    
    # Генерация уровня при старте игры
    # generated_level = game_integration.generate_procedural_content(seed=12345)
    
    # Расчет сложности в реальном времени
    # difficulty_settings = game_integration.calculate_dynamic_difficulty(
    #     player_level=5, 
    #     success_rate=0.65
    # )
```

Эти примеры демонстрируют, как можно использовать `PyServer` для создания кастомной функциональности, расширяя базовые возможности PyBridge под конкретные нужды вашего мода.


Эта документация охватывает все основные аспекты работы с модулем PyBridge и должна помочь разработчикам в создании надежных и эффективных модификаций для Ren'Py.