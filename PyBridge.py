"""
PyBridge — это модуль для выполнения Python-кода в изолированных средах внутри Ren'Py приложений. Модуль позволяет запускать код на разных версиях Python, управлять процессами и безопасно исполнять пользовательские скрипты.

Модуль автоматически адаптирует код для python при импорте:
    ```import PyBridge
    ```

После импорта система создаёт или подключает серверные Python-процессы, управляет
их пулом, выполняет переданный код в изолированной среде и возвращает результат
в виде текста. Поддерживает кэширование, временные директории, асинхронное выполнение
и логирование с ротацией логов.

Особенности:
- Полностью совместим с обычным Python-интерпретатором.
- Может использоваться как в Ren’Py, так и вне его.
- Обеспечивает безопасное выполнение Python-кода в отдельных процессах.
- Автоматически создаёт временные копии интерпретаторов Python нужных версий.

Использование:
    from PyBridge import pybridge
    result = pybridge.python(code="print('Hello from PyBridge!')")

Файл PyBridge.py можно импортировать напрямую — при этом код будет автоматически
адаптирован под стандартный Python без необходимости в Ren’Py.
"""

if __name__ != "__main__":
    plugs = """
import sys
if sys.version_info[0] >= 3:
    import types
    # Создаём минимальные заглушки, которые ожидает модуль
    renpy = types.SimpleNamespace(
        log=print,
        invoke_in_main_thread=lambda cb, *a, **k: cb(
            *a, **k
        ),  # просто вызываем колбэк сразу
        loader=types.SimpleNamespace(transfn=lambda p: p),
    )
    config = types.SimpleNamespace(quit_callbacks=[])
else:
    class _NS(object):
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)
    renpy = _NS(
        log=print,
        invoke_in_main_thread=lambda cb, *a, **k: cb(*a, **k),
        loader=_NS(transfn=lambda p: p),
    )
    config = _NS(quit_callbacks=[])
"""

    import os, sys

    if sys.platform.startswith("win"):
        path = "win"
    elif sys.platform.startswith("linux"):
        path = "linux/bin/"
    elif sys.platform == "darwin":
        path = "mac/bin/"

    MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
    # MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(MODULE_DIR, "PyBridge.rpy")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = f.readlines()
    except FileNotFoundError:
        print("File 'PyBridge.rpy' not found", file=sys.stderr)
        sys.exit(1)

    data.pop(0)
    data.pop(0)
    code = plugs

    for line in list(data):
        line = line[4:]
        if "_MODULE_NAME = None" in line:
            m_name = os.path.dirname(os.path.abspath(MODULE_DIR)).replace("\\", "/")
            line = line.replace("None", f"'{m_name}'")
        code += line

    file_path = os.path.join(MODULE_DIR, "_PyBridge.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    if "sys" in globals():
        del globals()["sys"]

    if "types" in globals():
        del globals()["types"]

    if "os" in globals():
        del globals()["os"]

    from ._PyBridge import *
