"""
PyBridge — модуль для выполнения Python-кода в изолированных средах.

Модуль позволяет запускать код на разных версиях Python, управлять процессами
и безопасно исполнять пользовательские скрипты внутри Ren'Py приложений.

Особенности:
- Полностью совместим с обычным Python-интерпретатором
- Может использоваться как в Ren'Py, так и вне его
- Обеспечивает безопасное выполнение Python-кода в отдельных процессах
- Автоматически создаёт временные копии интерпретаторов Python нужных версий
- Кеширование: пересоздаёт модуль только при изменении исходного файла

Использование:
    from PyBridge import pybridge
    result = pybridge.python(code="print('Hello from PyBridge!')")
"""

import os
import sys
import hashlib
import json
from typing import Optional, Dict, Any


def _get_file_hash(file_path: str) -> Optional[str]:
    """
    Вычисляет SHA256 хеш файла.

    Args:
        file_path: Путь к файлу

    Returns:
        str: Хеш файла в hex формате или None при ошибке
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Читаем файл блоками для эффективности
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IOError, OSError):
        return None


def _load_cache(cache_path: str) -> Optional[Dict[str, Any]]:
    """
    Загружает кеш из JSON файла.

    Args:
        cache_path: Путь к файлу кеша

    Returns:
        dict: Данные кеша или None при ошибке
    """
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, OSError, json.JSONDecodeError, ValueError):
        return None


def _save_cache(cache_path: str, cache_data: Dict[str, Any]) -> bool:
    """
    Сохраняет кеш в JSON файл.

    Args:
        cache_path: Путь к файлу кеша
        cache_data: Данные для сохранения

    Returns:
        bool: True если успешно, False при ошибке
    """
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        return True
    except (IOError, OSError, TypeError):
        return False


def _check_cache_validity(rpy_file: str, output_file: str, cache_file: str) -> bool:
    """
    Проверяет актуальность кеша.

    Args:
        rpy_file: Путь к исходному .rpy файлу
        output_file: Путь к выходному .py файлу
        cache_file: Путь к файлу кеша

    Returns:
        bool: True если кеш актуален, False если требуется пересоздание
    """
    # Проверяем существование всех необходимых файлов
    if not os.path.exists(output_file):
        return False

    if not os.path.exists(cache_file):
        return False

    # Загружаем кеш
    cache_data = _load_cache(cache_file)
    if cache_data is None:
        return False

    # Вычисляем текущий хеш исходного файла
    current_hash = _get_file_hash(rpy_file)
    if current_hash is None:
        return False

    # Сравниваем хеши
    cached_hash = cache_data.get("source_hash")
    if cached_hash != current_hash:
        return False

    # Проверяем, что выходной файл не был изменён вручную
    output_hash = _get_file_hash(output_file)
    cached_output_hash = cache_data.get("output_hash")

    if output_hash != cached_output_hash:
        return False

    return True


def _update_cache(rpy_file: str, output_file: str, cache_file: str) -> bool:
    """
    Обновляет кеш после успешного создания модуля.

    Args:
        rpy_file: Путь к исходному .rpy файлу
        output_file: Путь к выходному .py файлу
        cache_file: Путь к файлу кеша

    Returns:
        bool: True если успешно, False при ошибке
    """
    source_hash = _get_file_hash(rpy_file)
    output_hash = _get_file_hash(output_file)

    if source_hash is None or output_hash is None:
        return False

    cache_data = {
        "source_hash": source_hash,
        "output_hash": output_hash,
        "source_file": rpy_file,
        "output_file": output_file,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    return _save_cache(cache_file, cache_data)


def _create_renpy_stubs() -> str:
    """
    Создаёт заглушки для Ren'Py API, когда модуль используется вне Ren'Py.

    Returns:
        str: Код заглушек для внедрения
    """
    return """
import sys

if sys.version_info[0] >= 3:
    import types
    
    renpy = types.SimpleNamespace(
        log=print,
        invoke_in_main_thread=lambda cb, *args, **kwargs: cb(*args, **kwargs),
        loader=types.SimpleNamespace(transfn=lambda path: path),
    )
    config = types.SimpleNamespace(quit_callbacks=[])
else:
    # Python 2 совместимость
    class _Namespace(object):
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    renpy = _Namespace(
        log=print,
        invoke_in_main_thread=lambda cb, *args, **kwargs: cb(*args, **kwargs),
        loader=_Namespace(transfn=lambda path: path),
    )
    config = _Namespace(quit_callbacks=[])
"""


def _read_rpy_file(file_path: str) -> Optional[list]:
    """
    Читает содержимое .rpy файла.

    Args:
        file_path: Путь к файлу

    Returns:
        list: Список строк файла или None при ошибке
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except (FileNotFoundError, IOError, OSError) as e:
        print(f"Ошибка чтения файла '{file_path}': {e}", file=sys.stderr)
        return None


def _process_rpy_lines(lines: list, module_dir: str) -> str:
    """
    Обрабатывает строки из .rpy файла, адаптируя их для Python.

    Args:
        lines: Список строк из .rpy файла
        module_dir: Директория модуля

    Returns:
        str: Обработанный код
    """
    # Пропускаем первые две строки (обычно это шапка Ren'Py)
    if len(lines) >= 2:
        lines = lines[2:]

    code_parts = [_create_renpy_stubs()]

    for line in lines:
        # Удаляем отступ Ren'Py (4 пробела)
        processed_line = line[4:] if line.startswith("    ") else line

        # Заменяем placeholder для MODULE_NAME
        if "_MODULE_NAME = None" in processed_line:
            parent_dir = os.path.dirname(os.path.abspath(module_dir))
            normalized_path = parent_dir.replace("\\", "/")
            processed_line = processed_line.replace("None", f"'{normalized_path}'")

        code_parts.append(processed_line)

    return "".join(code_parts)


def _write_adapted_module(file_path: str, code: str) -> bool:
    """
    Записывает адаптированный модуль в файл.

    Args:
        file_path: Путь для записи
        code: Код для записи

    Returns:
        bool: True если успешно, False при ошибке
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return True
    except (IOError, OSError) as e:
        print(f"Ошибка записи файла '{file_path}': {e}", file=sys.stderr)
        return False


def _cleanup_globals(names: list) -> None:
    """
    Удаляет временные переменные из глобального пространства имён.

    Args:
        names: Список имён для удаления
    """
    frame = sys._getframe(1)
    global_vars = frame.f_globals

    for name in names:
        global_vars.pop(name, None)


def _initialize_pybridge():
    """
    Инициализирует PyBridge при импорте, адаптируя .rpy файл для Python.
    Использует кеширование для избежания лишних пересозданий модуля.
    """
    # Определяем пути
    module_dir = os.path.dirname(os.path.abspath(__file__))
    rpy_file = os.path.join(module_dir, "PyBridge.rpy")
    output_file = os.path.join(module_dir, "_PyBridge.py")
    cache_file = os.path.join(module_dir, ".pybridge_cache.json")

    # Проверяем актуальность кеша
    if _check_cache_validity(rpy_file, output_file, cache_file):
        # Кеш актуален, пропускаем пересоздание
        return

    # Кеш неактуален или отсутствует - пересоздаём модуль
    lines = _read_rpy_file(rpy_file)
    if lines is None:
        sys.exit(1)

    # Обрабатываем содержимое
    adapted_code = _process_rpy_lines(lines, module_dir)

    # Сохраняем адаптированную версию
    if not _write_adapted_module(output_file, adapted_code):
        sys.exit(1)

    # Обновляем кеш
    _update_cache(rpy_file, output_file, cache_file)

    # Очищаем временные переменные
    cleanup_names = [
        "module_dir",
        "rpy_file",
        "output_file",
        "cache_file",
        "lines",
        "adapted_code",
        "_get_file_hash",
        "_load_cache",
        "_save_cache",
        "_check_cache_validity",
        "_update_cache",
        "_create_renpy_stubs",
        "_read_rpy_file",
        "_process_rpy_lines",
        "_write_adapted_module",
        "_cleanup_globals",
        "_initialize_pybridge",
    ]
    _cleanup_globals(cleanup_names)


# Инициализация происходит только при импорте модуля
if __name__ != "__main__":
    _initialize_pybridge()

    # Импортируем адаптированный модуль
    try:
        from ._PyBridge import *
    except ImportError as e:
        print(f"Ошибка импорта адаптированного модуля: {e}", file=sys.stderr)
        sys.exit(1)
