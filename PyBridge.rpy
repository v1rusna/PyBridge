"""Имеет совместимость с обычным python, нужно импортировать файл PyBridge.py, код автоматически будет адаптирован мод python"""
init -9999 python:
    import os
    import subprocess
    import shutil
    import tempfile
    import codecs
    import threading
    import locale
    import sys
    import time
    import hashlib
    import random

    class PyBridgeException(Exception):
        """Базовое исключение для всех ошибок PyBridge"""
        def __init__(self, message, **context):
            super(PyBridgeException, self).__init__(message)
            self.context = context

    class PyBridgeInitException(PyBridgeException):
        """Ошибка инициализации или конфигурации PyBridge"""
        pass

    class PyBridgeServerException(PyBridgeException):
        """Ошибка, связанная с сервером (создание, подключение, завершение)"""
        pass

    class PyBridgeExecException(PyBridgeException):
        """Ошибка исполнения кода на стороне Python"""
        pass

    class PyBridgeCacheException(PyBridgeException):
        """Ошибка работы с кэшем (недоступен, повреждён, не найден)"""
        pass

    class PyBridgeFileException(PyBridgeException):
        """Ошибка работы с файлами (копирование, временные пути, доступ)"""
        pass

    class LogSystem(object):
        """Класс для логирования в файл с ротацией по размеру."""
        
        def __init__(self, filename="pybridge.log", max_size=5*1024*1024, backup_count=3):
            """
            Инициализация системы логирования.
            
            Args:
                filename: имя файла лога
                max_size: максимальный размер файла в байтах (по умолчанию 5MB)
                backup_count: количество резервных копий для хранения
            """
            self.path = "v1rus_team/PyBridge/logs/"
            self.filename = self.path + filename
            self.max_size = max_size
            self.backup_count = backup_count
            self.file = None
            self.enabled = True
            self._lock = threading.Lock()
            self._size_cache = 0
            self._closed = False
            self.open()
        
        def __del__(self):
            self.close()
        
        def open(self):
            """Открывает файл для логирования."""
            if self.file is None and self.enabled and not self._closed:
                try:
                    if not os.path.exists(self.path):
                        os.makedirs(self.path)
                    
                    # Проверяем существование файла и его размер
                    if os.path.exists(self.filename):
                        self._size_cache = os.path.getsize(self.filename)
                    else:
                        self._size_cache = 0
                    
                    self.file = codecs.open(self.filename, "a", encoding="utf-8")
                    self._write_direct(u"=== Log started ===")
                except Exception as e:
                    self._fallback_log("LogSystem: Failed to open log file: %s" % e)
                    self.file = None
                    self.enabled = False
        
        def close(self):
            """Закрывает файл логирования."""
            if self.file and not self._closed:
                try:
                    self._write_direct(u"=== Log closed ===")
                    self.file.close()
                except Exception as e:
                    self._fallback_log("LogSystem: Failed to close log file: %s" % e)
                finally:
                    self.file = None
                    self._closed = True
        
        def log(self, message, no_lock=False, level="INFO"):
            """
            Записывает сообщение в лог.
            
            Args:
                message: текст сообщения
                level: уровень логирования (INFO, WARNING, ERROR, DEBUG)
            """
            if no_lock:
                self._log_internal(message, level)
            else:
                with self._lock:
                    self._log_internal(message, level)
        
        def to_unicode(self, message):
            """Безопасно приводит значение к unicode-строке"""
            try:
                unicode_type = unicode  # Python 2
            except NameError:
                unicode_type = str      # Python 3

            if isinstance(message, unicode_type):
                return message

            # Если это байты — декодируем
            if isinstance(message, bytes):
                try:
                    return message.decode("utf-8", errors="replace")
                except Exception:
                    return message.decode("utf-8", "replace")

            # Всё остальное превращаем в строку
            try:
                return unicode_type(str(message))
            except Exception:
                return unicode_type(repr(message))


        def _log_internal(self, message, level):
            """Внутренний метод для записи лога (без блокировки)."""
            if not self.enabled or self._closed:
                return
            
            if self.file is None:
                self.open()
            
            if self.file is None:
                return
            
            try:
                # Проверка на необходимость ротации
                if self._size_cache > self.max_size:
                    self._rotate_logs()
                
                # Формирование сообщения
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                message_str = self.to_unicode(message)
                
                # Разбиваем многострочные сообщения
                lines = message_str.split("\n")
                for line in lines:
                    log_line = u"[%s] [%s] %s\n" % (timestamp, level, line)
                    self.file.write(log_line)
                    self._size_cache += len(log_line.encode("utf-8"))
                
                self.file.flush()
                
            except Exception as e:
                self._fallback_log("LogSystem: Failed to write to log file: %s" % e)
                self._fallback_log("Original message: %s" % message)
        
        def _rotate_logs(self):
            """Выполняет ротацию логов."""
            try:
                self.file.close()
                
                # Удаляем самый старый бэкап если превышено количество
                oldest_backup = "%s.%d" % (self.filename, self.backup_count)
                if os.path.exists(oldest_backup):
                    os.remove(oldest_backup)
                
                # Сдвигаем все бэкапы на один номер выше
                for i in range(self.backup_count - 1, 0, -1):
                    old_name = "%s.%d" % (self.filename, i)
                    new_name = "%s.%d" % (self.filename, i + 1)
                    if os.path.exists(old_name):
                        os.rename(old_name, new_name)
                
                # Переименовываем текущий лог в первый бэкап
                if os.path.exists(self.filename):
                    os.rename(self.filename, "%s.1" % self.filename)
                
                # Открываем новый файл
                self._size_cache = 0
                self.file = codecs.open(self.filename, "a", encoding="utf-8")
                self._write_direct(u"=== Log rotated ===")
                
            except Exception as e:
                self._fallback_log("LogSystem: Failed to rotate logs: %s" % e)
                # Пытаемся переоткрыть файл в любом случае
                try:
                    self.file = codecs.open(self.filename, "a", encoding="utf-8")
                    self._size_cache = os.path.getsize(self.filename) if os.path.exists(self.filename) else 0
                except:
                    self.file = None
                    self.enabled = False
        
        def _write_direct(self, message):
            """Записывает служебное сообщение напрямую."""
            if self.file:
                try:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    log_line = u"[%s] %s\n" % (timestamp, message)
                    self.file.write(log_line)
                    self.file.flush()
                    self._size_cache += len(log_line.encode("utf-8"))
                except:
                    pass
        
        def _fallback_log(self, message):
            """Резервное логирование в renpy.log."""
            try:
                renpy.log(message)
            except:
                pass
        
        # Удобные методы для разных уровней логирования
        def info(self, message):
            """Логирование информационного сообщения."""
            self.log(message, "INFO")
        
        def warning(self, message):
            """Логирование предупреждения."""
            self.log(message, "WARNING")
        
        def error(self, message):
            """Логирование ошибки."""
            self.log(message, "ERROR")
        
        def debug(self, message):
            """Логирование отладочной информации."""
            self.log(message, "DEBUG")
        
        def disable(self):
            """Отключает логирование."""
            with self._lock:
                self.enabled = False
                self.close()
        
        def enable(self):
            """Включает логирование."""
            with self._lock:
                if not self.enabled:
                    self.enabled = True
                    self._closed = False
                    self.open()

    class PyBridge(object):
        _MODULE_NAME = None # Абсолютный путь директории с файлом PyBridge.py
        create_bridge = False

        def __init__(self, version=None, path=None, server_default=None,
            max_age=3600, pool_size=2, safe_mode=False, debug=True, decoder=None):

            # --- Проверка единственности экземпляра ---
            if PyBridge.create_bridge:
                raise PyBridgeInitException("PyBridge instance already created")
            PyBridge.create_bridge = True

            # --- Основные параметры ---
            self.MAX_AGE = max_age              # Максимальный возраст кэша (в секундах)
            self.POOL_SIZE = pool_size          # Размер пула серверов
            self.safe_mode = safe_mode
            self.debug = debug

            # --- Инициализация декодера (если передан) ---
            if decoder and callable(decoder):
                self._decoder = decoder

            # --- Определение пути к Python (если не задан) ---
            if path is None:
                if sys.platform.startswith("win"):
                    path = "PyBridge/python/win/python.exe"
                elif sys.platform.startswith("linux"):
                    path = "PyBridge/python/linux/bin/python3"
                elif sys.platform == "darwin":
                    path = "PyBridge/python/mac/bin/python3"

            # Проверка существования интерпретатора Python
            if not os.path.exists(self._path(path)):
                raise PyBridgeInitException("Default Python executable not found: %s" % path)

            # --- Версия Python по умолчанию ---
            if version is None:
                version = "3.13.7"

            # --- Серверный файл по умолчанию ---
            if server_default is None:
                server_default = "PyBridge/python_embed_server.py"

            if not os.path.exists(self._path(server_default)):
                raise PyBridgeInitException("Default server file not found: %s" % server_default)

            # --- Системные словари и параметры ---
            self.__pythons = {version: path}
            self.__python313_default_path = path
            self.__server_default_path = server_default
            self.__server_python = {version: self.__server_default_path}

            # --- Внутренние состояния ---
            self.__all_servers = []
            self._lock = threading.RLock()
            self.__temp_dir = None
            self.__temp_pythons = {}
            self.__cache_info = {}
            self._cache = {}
            self.__process_pool = []
            self.__busy_ports = set()
            self.__busy_server_ids = set()

            # --- Очистка временных директорий PyBridge ---
            try:
                temp_root = tempfile.gettempdir()
                for name in os.listdir(temp_root):
                    if name.startswith("pybridge_"):
                        shutil.rmtree(os.path.join(temp_root, name), ignore_errors=True)
            except Exception:
                # Игнорируем любые ошибки при очистке
                pass

        def __del__(self):
            PyBridge.create_bridge = False
            self.cleanup()

        def _path(self, *paths, game_path=True):
            """
            Формирует путь к файлу или директории внутри проекта.

            Если game_path=True строит путь относительно 'game'

            Пример:
                self._path("assets", "images", "hero.png")
            """
            base = PyBridge._MODULE_NAME if PyBridge._MODULE_NAME else ("game" if game_path else "")
            parts = [base] + [p for p in paths if p]
            return os.path.normpath(os.path.join(*parts))

        def reset(self):
            with self._lock:
                self.cleanup()
                self._cache.clear()
                self.__cache_info.clear()
                self.__temp_pythons.clear()
                self.__process_pool.clear()
                self.__busy_ports.clear()
                self.__busy_server_ids.clear()
                self._log("PyBridge has been reset.")

        def init_pool(self):
            with self._lock:
                self.__process_pool.clear()
            for i in range(self.POOL_SIZE):
                server = self.create_server(cache=False)
                if server and server.is_alive():
                    with self._lock:
                        self.__process_pool.append(server)
                    self._log("Pool: started server %d on port %d" % (i, server.PORT))

        def _get_server_from_pool(self):
            if not self.POOL_SIZE:
                return

            if not self.__process_pool:
                self.init_pool()

            dead_indices = []
            with self._lock:
                for i, s in enumerate(self.__process_pool):
                    if not s.is_alive():
                        dead_indices.append((i, s))

            for i, s in dead_indices:
                self._log("Server %s dead, restarting..." % s.get_id())
                try:
                    new_s = self.create_server(s.version())
                except Exception as e:
                    new_s = None
                    self._log("Failed to restart server: %s" % e)
                with self._lock:
                    if new_s:
                        self.__process_pool[i] = new_s
                    else:
                        self.__process_pool.pop(i)

            with self._lock:
                if not self.__process_pool:
                    raise PyBridgeException("No servers in pool")
                count = 50
                while count > 0:
                    servers = [server for server in self.__process_pool if not server.is_busy()]
                    if not servers:
                        count -= 1
                        continue
                    server = random.choice(servers)
                    break

            return server

        def __set_cache(self, path, key=None):
            """Кэширует данные в памяти, возвращает ключ. Если ключ не указан, генерируется хеш."""
            if key is None:
                key = self.__get_hash(path)

            try:
                with self._lock:
                    self._cache[key] = {"path": path, "time": time.time()}
            except Exception as e:
                raise PyBridgeCacheException("Failed to set cache: %s" % e)

            self.__clear_cache()

        def __get_cache(self, key):
            """Возвращает кэшированные данные по ключу, или None если не найдено или устарело."""
            self.__clear_cache()

            try:
                with self._lock:
                    if key in self._cache:
                        self.__touch_cache(key)
                        info = self._cache[key]
                        return info["path"]
            except Exception as e:
                raise PyBridgeCacheException("Failed to get cache: %s" % e)

        def __clear_cache(self):
            try:
                with self._lock:
                    for key, info in list(self._cache.items()):
                        if time.time() - info["time"] > self.MAX_AGE:
                            self._log("Clearing cached file: " + info["path"], no_lock=True)
                            try:
                                os.remove(info["path"])
                            except OSError:
                                pass
                            del self._cache[key]

                    for key, info in list(self.__cache_info.items()):
                        self._log("Checking cached info for key: " + key, no_lock=True)
                        if time.time() - info["time"] > self.MAX_AGE:
                            del self.__cache_info[key]

                        
            except Exception as e:
                raise PyBridgeCacheException("Failed to clear cache: %s" % e)
            
        def __touch_cache(self, key):
            try:
                if key in self._cache:
                    self._cache[key]['time'] = time.time()
            except Exception as e:
                raise PyBridgeCacheException("Failed to touch cache: %s" % e)

        def get_path(self, path):
            if not path:
                return ""
            path = path.strip()
            try:
                path = renpy.loader.transfn(path)
                return os.path.normpath(path)
            except:
                return ""
        
        def _get_temp_python(self, version):
            """Возвращает путь к безопасной временной копии Python для указанной версии"""
            with self._lock:
                if version in self.__temp_pythons:
                    temp_path = self.__temp_pythons[version]
                    if os.path.exists(temp_path):
                        return temp_path

                if version not in self.__pythons:
                    raise PyBridgeException("Python version '%s' not found" % version)

                original_path = self.get_path(self.__pythons[version])

                if not os.path.exists(original_path):
                    raise PyBridgeFileException("Python executable not found: %s" % original_path)

                if os.path.getsize(original_path) > 60 * 1024 * 1024:
                    raise PyBridgeException("Python version “%s” weighs more than 60 MB." % version)

                self.__create_temp_dir()

                temp_python_dir = os.path.join(self.__temp_dir, "python_" + version.replace(".", "_"))

                if not os.path.exists(temp_python_dir):
                    self._log("Copying Python from %s → %s" % (os.path.dirname(original_path), temp_python_dir))
                    shutil.copytree(os.path.dirname(original_path), temp_python_dir)

                temp_python_exe = os.path.join(temp_python_dir, os.path.basename(original_path))

                if not os.path.exists(temp_python_exe):
                    raise PyBridgeFileException("Failed to copy Python executable to temp directory")

                self.__temp_pythons[version] = temp_python_exe
                self._log("Using temp Python: " + temp_python_exe)

            return temp_python_exe
    
        def __create_temp_dir(self):
            if self.__temp_dir is None:
                self.__temp_dir = tempfile.mkdtemp(prefix="pybridge_")
                self._log("Created temp directory: " + self.__temp_dir)

        def list_servers(self):
            return list(self.__server_python.keys())

        def _find_free(self, used_set, start=5000, end=6000):
            """Возвращает свободное число из диапазона и добавляет его в used_set"""
            value = start
            while value in used_set and value < end:
                value += 1
            if value >= end:
                raise PyBridgeException("No free slots in range %d-%d" % (start, end))
            used_set.add(value)
            return value

        def create_server(self, version="3.13.7", port=5000, cache=True):
            """Создает объект серверного Python процесса указанной версии на указанном порту, если cache=True вернет уже созданный сервер указанной версии если он есть"""
            try:
                with self._lock:
                    # Уже активен сервер этой версии
                    if cache:
                        for server in self.__all_servers:
                            if version == server.version():
                                return server

                    if version not in self.__server_python:
                        raise PyBridgeException("Server for Python version '%s' not found" % version)

                    python_path = self._get_temp_python(version)
                    temp_path = self.__create_temp_file(self.__server_python[version])

                    # Найти свободный порт
                    port = self._find_free(self.__busy_ports, start=port, end=60000)

                try:
                    proc = self.__popenen(python_path, [temp_path, str(port)])
                except OSError:
                    raise PyBridgeServerException("Unable to start the server on port '%s' because it is busy" % port)

                if not self.__wait_for_server(port):
                    raise PyBridgeServerException("Failed to start server on port %d" % port)

                with self._lock:
                    # Генерация уникального ID
                    random_id = self._find_free(self.__busy_server_ids, start=1000, end=9999)

                    # Создание объекта сервера
                    server = PyServer(version, self, port, proc, python_path, random_id)
                    self.__all_servers.append(server)

                # Удаляем временный файл (если остался)
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass

                return server

            except Exception as e:
                self._log("Error creating server on port %d: %s" % (port, e))
                with self._lock:
                    self.__busy_ports.discard(port)
                    if 'random_id' in locals():
                        self.__busy_server_ids.discard(random_id)
                    # Удаляем битый сервер, если был создан
                    for srv in list(self.__all_servers):
                        if getattr(srv, "PORT", None) == port:
                            srv.close()
                            break
                raise PyBridgeServerException("Failed to create server: %s" % e)

        def __wait_for_server(self, port, timeout=5.0):
            import socket
            start = time.time()
            while time.time() - start < timeout:
                try:
                    s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
                    s.close()
                    return True
                except socket.error:
                    time.sleep(0.05)
            return False

        def close_server(self, server):
            if not isinstance(server, PyServer):
                return
            if not server.is_alive():
                pylog.log("Server on port %d already closed." % server.PORT)
            else:
                server.close()

            with self._lock:
                if server in self.__all_servers:
                    self.__all_servers.pop(self.__all_servers.index(server))
                self.__busy_ports.discard(server.PORT)
                self.__busy_server_ids.discard(server.get_id())

        def get_servers(self):
            with self._lock:
                return list(self.__all_servers)

        def add_python(self, version, path, server_file="default"):
            if path == "default":
                path = self.__python313_default_path

            original_path = self.get_path(path)
            if not os.path.exists(original_path):
                raise PyBridgeFileException("Python executable not found: %s" % original_path)

            try:
                if os.path.getsize(original_path) > 60 * 1024 * 1024:
                    raise PyBridgeException("Python version “%s” weighs more than 60 MB." % version)
            except OSError:
                # если нельзя получить размер (на некоторых FS) — просто пропускаем или логируем
                self._log("Warning: could not determine size of %s" % original_path, no_lock=True)

            with self._lock:
                self.__pythons[version] = path
                if version in self.__temp_pythons:
                    del self.__temp_pythons[version]
                if server_file == "default":
                    server_file = self.__server_default_path
                self.__server_python[version] = server_file

        def remove_python(self, version):
            with self._lock:
                if version in self.__pythons:
                    del self.__pythons[version]
                if version in self.__temp_pythons:
                    del self.__temp_pythons[version]
                if version in self.__server_python:
                    del self.__server_python[version]
                for server in list(self.__all_servers):
                    if version == server.version():
                        try:
                            server.close()
                        except Exception:
                            pass
        
        def list_versions(self):
            return list(self.__pythons.keys())
        
        def get_info(self, version):
            """Возвращает подробную информацию об интерпретаторе указанной версии"""
            with self._lock:
                if version in self.__cache_info:
                    return self.__cache_info[version]["info"]

            import json

            lines = [
                "import sys, sysconfig, os, platform, json, site, pkgutil",
                "info = {",
                '    "version": sys.version,',
                '    "version_info": tuple(sys.version_info),',
                '}',
                'print(json.dumps(info, ensure_ascii=False, indent=4, default=str))'
            ]
            code = "\n".join(lines)

            out = self.python(version=version, code=code, seconds=None)
            with self._lock:
                self.__cache_info[version] = {"info": json.loads(out), "time": time.time()}
                return self.__cache_info[version]["info"]

        def __get_hash(self, code):
            if not isinstance(code, str) and not isinstance(code, bytes):
                code = str(code)
            if not isinstance(code, bytes):
                code = code.encode('utf-8')

            return hashlib.sha256(code).hexdigest()

        def __get_file_hash(self, file_path):
            with open(file_path, "rb") as f:
                return self.__get_hash(f.read())

        def cleanup(self):
            """Очищает временную директорию и завершает все активные серверы"""
            try:
                with self._lock:
                    if self.__process_pool:
                        for server in self.__process_pool:
                            try:
                                server.close()
                            except Exception:
                                pass
                        self.__process_pool = []

                    if self.__all_servers:
                        for server in list(self.__all_servers):
                            try:
                                server.close()
                            except Exception:
                                pass
                        self.__all_servers = []

                    if self.__temp_dir and os.path.exists(self.__temp_dir):
                        try:
                            shutil.rmtree(self.__temp_dir)
                            self._log("Cleaned up temp directory: " + self.__temp_dir)
                            self.__temp_dir = None
                            self.__temp_pythons = {}
                        except Exception as e:
                            pylog.log("Failed to cleanup temp directory: " + str(e))
            except:
                pass
        
        def python(self, version="3.13.7", code="", seconds=5, args=None, variables=None, cwd=None, input_data=None, use_pool=True):
            """Выполняет код на указанной версии Python, возвращает stdout"""
            if not code:
                return ""
            if seconds is None or seconds <= 0:
                seconds = 9999
            if variables is None:
                variables = {}
            if args is None:
                args = []
            #if safe_mode is None:
            #    safe_mode = self.safe_mode

            def execute():
                flags = ["-c", wrapper] + args
                out, err = self._exec(python_path, seconds, flags, cwd=cwd, input_data=input_data)
                self._log("--out: %s" % out)
                return out, err

            try:
                python_path = self._get_temp_python(version)

                # Создаем обертку, которая декодирует и выполняет код
                wrapper = self.__wrapper(code, variables, server_mode=use_pool) #safe_mode

                if self.debug:
                    with codecs.open("debug.py", "w", encoding="utf-8") as f:
                        f.write(wrapper)
                        
                if use_pool and self.POOL_SIZE > 0:
                    server = self._get_server_from_pool()
                    try:
                        if not server.is_alive(check_connection=True):
                            #self._log("The server on port %s from the pool failed the connection check; the standard method is used." % server.PORT)
                            pylog.log("The server on port %s from the pool failed the connection check; the standard method is used." % server.PORT)
                            self.__wrapper(code, variables) #safe_mode
                            out, err = execute()
                            return out

                        result = server.send(wrapper)
                        return result[len("RESULT:"):] if result.startswith("RESULT:") else result
                    except Exception as e:
                        raise PyBridgeExecException("Pool execution error: %s" % e)
                else:
                    out, err = execute()

                return out

            except Exception as e:
                pylog.log("PyBridge: python() exception: %s" % repr(e))
                raise

        def _exec(self, python_path, seconds, flags=None, cwd=None, input_data=None):
            if flags is None:
                flags = []
            if not isinstance(input_data, (bytes, type(None))):
                input_data = input_data.encode('utf-8')

            proc = self.__popenen(python_path, flags, cwd)

            start = time.time()
            while proc.poll() is None:
                if time.time() - start > seconds:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    raise PyBridgeExecException("Python process timeout after %d seconds" % seconds)
                time.sleep(0.05)

            stdout, stderr = proc.communicate(input=input_data) # timeout - нет в python 2.7 и поэтому он воссоздан вручную

            out, err = self._decoder(stdout, stderr)

            if proc.returncode != 0:
                raise PyBridgeExecException("Python execution failed (rc=%s): %s" % (proc.returncode, err))
                    
            return out, err

        def __popenen(self, python_path, flags, cwd=None):
            if cwd is None:
                working_dir = os.path.dirname(python_path)
            else:
                working_dir = cwd

            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.Popen(
                [python_path] + flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                cwd=working_dir
            )

            return proc

        def _decoder(self, stdout=None, stderr=None):
            out = err = ""
            try:
                if stdout:
                    out = stdout.decode('utf-8').strip()
                if stderr:
                    err = stderr.decode('utf-8').strip()
            except Exception:
                enc = locale.getpreferredencoding(False) or "utf-8"
                if stdout:
                    out = stdout.decode(enc, errors='replace').strip()
                if stderr:
                    err = stderr.decode(enc, errors='replace').strip()

            return out, err

        def __wrapper(self, code, variables, server_mode=False):
            import json, base64

            try:
                vars_json = json.dumps(variables)
            except Exception:
                vars_json = "{}"

            code = code.replace("print(", "_log(")

            lines = []
            lines.append("result = ''")
            if server_mode:
                lines.append("import json")
            else:
                lines.append("import base64, json, sys, traceback")
            lines.append("vars_data = json.loads(%r)" % vars_json)
            lines.append("for k,v in list(vars_data.items()):")
            lines.append("    if not isinstance(k, str) or not k.isidentifier():")
            lines.append("        continue")
            lines.append("    if k.startswith('__'):")
            lines.append("        continue")
            lines.append("    globals()[k] = v")

            lines.append("def _log(*args, **kwargs):")
            lines.append("    global result")
            lines.append("    end = kwargs.get('end', '\\n')")
            lines.append("    if not isinstance(end, str):")
            lines.append("        end = '\\n'")
            lines.append("    sep = kwargs.get('sep', ' ')")
            lines.append("    if not isinstance(sep, str):")
            lines.append("        sep = ' '")
            lines.append("    res = sep.join(str(a) for a in args) + end")
            lines.append("    result += res")

            if server_mode:
                lines.append(code) 
            else:
                code_bytes = code.encode('utf-8')
                b64 = base64.b64encode(code_bytes)

                if isinstance(b64, bytes):
                    code_base64 = b64.decode('ascii')
                else:
                    code_base64 = b64

                lines.append("code_b = %r" % code_base64)
                lines.append("try:")
                lines.append("    code = base64.b64decode(code_b).decode('utf-8')")
                lines.append("    exec(code, globals())")
                #lines.append("    print(globals().get('result', 'ok'))")
                lines.append("    sys.stdout.write(str(globals().get('result', 'ok')))")
                lines.append("except Exception as e:")
                lines.append("    sys.stderr.write('Error in user code:\\n' + traceback.format_exc())")

            if server_mode:
                lines.append("for k in list(vars_data.keys()):")
                lines.append("    if not isinstance(k, str) or not k.isidentifier():")
                lines.append("        continue")
                lines.append("    if k.startswith('__'):")
                lines.append("        continue")
                lines.append("    globals().pop(k)")

            wrapper = "\n".join(lines)
            return wrapper

        def init_python(self, version="3.13.7"):
            """Инициализирует и возвращает путь к Python интерпретатору указанной версии"""
            return self._get_temp_python(version)

        def python_async(self, version="3.13.7", code="", callback=None, seconds=5, args=None, variables=None, cwd=None, input_data=None, use_pool=False):
            if not code:
                if callback:
                    # вызываем callback в основном потоке
                    renpy.invoke_in_main_thread(callback, "")
                return

            def target():
                try:
                    result = self.python(version, code, seconds, args, variables, cwd, input_data, use_pool)
                    if callback:
                        renpy.invoke_in_main_thread(callback, result)
                except Exception as e:
                    if callback:
                        renpy.invoke_in_main_thread(callback, None, e)

            t = threading.Thread(target=target)
            t.setDaemon(True)
            t.start()

        def _has_pip(self, python_path, timeout=2):
            try:
                out = subprocess.check_output(
                    [python_path, "-c", "import importlib.util; print(importlib.util.find_spec('pip') is not None)"],
                    stderr=subprocess.STDOUT, timeout=timeout)
                return out.strip().lower() in (b"true", b"1")
            except Exception:
                return False

        def debug_info(self):
            info = {
                "Loaded versions": self.__pythons,
                "Temp dir": self.__temp_dir,
                "Active copies": self.__temp_pythons,
            }
            for k, v in info.items():
                pylog.log(k + ": " + str(v))

        def __create_temp_file(self, file, cache=False):
            file = self.get_path(file)
            if not os.path.exists(file):
                raise PyBridgeException("Source file does not exist: %s" % file)

            self.__create_temp_dir()

            abs_file = os.path.abspath(file)
            file_hash = self.__get_file_hash(abs_file)
            temp_data = self.__get_cache(file_hash)

            if cache and temp_data:
                temp_path = temp_data
            else:
                temp_path = os.path.join(self.__temp_dir, os.path.basename(abs_file+".%s" % random.randint(0, 9999)))
                shutil.copy2(abs_file, temp_path)
                if cache:
                    self.__set_cache(temp_path, self.__get_file_hash(abs_file))

            return temp_path

        def exec_temp_file(self, src_path, version="3.13.7", seconds=10, cache=False):
            """
            Копирует указанный файл во временную директорию PyBridge, выполняет его указанной версией Python.
            Если cache=True, временный файл сохраняется для повторного использования.
            Возвращает stdout.
            """
            temp_path = self.__create_temp_file(src_path, cache)

            python_path = self._get_temp_python(version)
            cwd = os.path.dirname(temp_path)

            # Выполнение файла
            try:
                out, err = self._exec(python_path, seconds, flags=[temp_path], cwd=cwd)
            except Exception as e:
                raise PyBridgeExecException("Failed to execute temporary file: %s" % e)

            # Если кэш не нужен, удаляем временный файл
            if not cache:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

            return out

        def _log(self, message, no_lock=False):
            if self.debug:
                pylog.log("PyBridge: " + message, no_lock=no_lock)

    class PyServer(object):
        """
        Класс для управления серверным Python процессом, общение по TCP сокету, не потокобезопасен.
        Серверный процесс должен принимать соединения на localhost:port, читать код из сокета, выполнять его и возвращать результат.
        Принимает команды:
        - код Python для выполнения
        - EXIT для завершения сервера
        - IMPORT:<module> для импорта модуля
        Возвращает:
        - RESULT:<output> при успешном выполнении кода (output это переменная result из выполненного кода, если переменной этой нет в вашем коде, возвращается "ok")
        """
        def __init__(self, version, pybridge, port, proc, python_path, random_id):
            self.HOST = "127.0.0.1"
            self.PORT = port

            self.__id = random_id
            self.__version = version
            self.__active = True
            self.__pybridge = pybridge
            self.__proc = proc
            self.__python_path = python_path
            self.__server_is_alive = True
            self.__log_system = LogSystem("pybridge_server_%d.log" % port)
            self.__lock = threading.Lock()
            self.__logging_tread = []
            self.__busy = False

        def __del__(self):
            self.close()

        def is_busy(self):
            with self.__lock:
                return self.__busy

        def get_id(self):
            return self.__id

        def version(self):
            return self.__version

        def send(self, code, timeout=5, buffer_size=65536):
            import socket
            if not self.__active or not self.is_alive():
                self.close()
                raise PyBridgeServerException("Server on port %d not alive" % self.PORT)

            with self.__lock:
                self.__busy = True

            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.settimeout(timeout)
                client.connect((self.HOST, self.PORT))
                if not isinstance(code, bytes):
                    code = code.encode('utf-8')
                client.sendall(code)
                data = client.recv(buffer_size)
                return data.decode('utf-8', errors='replace')
            except Exception as e:
                self.__log_system.log("Send error on port %d: %s" % (self.PORT, e))
                raise
            finally:
                try:
                    client.close()
                except:
                    pass
                with self.__lock:
                    self.__busy = False

        def is_alive(self, close=True, check_connection=False):
            if not self.__server_is_alive:
                return False

            if not check_connection:
                if self.__proc.poll() is not None:
                    self.__server_is_alive = False
                    if close:
                        self.close()
                    return False
                return True
            else:
                alive = self.__check_connection(self.HOST, self.PORT)
                if not alive:
                    self.__server_is_alive = False
                    if close:
                        self.close()
                    return False
                return True

        def __check_connection(self, host, port):
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            try:
                s.connect((host, port))
                s.sendall(b"PING")
                result = s.recv(1024)
                return True
            except (ConnectionRefusedError, socket.timeout):
                return False
            finally:
                try:
                    s.close()
                except Exception:
                    pass

        def start_logging(self):
            def stdout_reader():
                for line in iter(self.__proc.stdout.readline, b''):
                    if not self.__active:
                        break
                    self.__log_system.log("Server[%d]: %s" % (self.PORT, line.decode('utf-8', errors='replace').strip()))
            t1 = threading.Thread(target=stdout_reader)
            t1.daemon = True
            t1.start()
            self.__logging_tread.append(t1)

            def stderr_reader():
                for line in iter(self.__proc.stderr.readline, b''):
                    if not self.__active:
                        break
                    self.__log_system.log("Server[%d][['error']: %s" % (self.PORT, line.decode('utf-8', errors='replace').strip()))

            t2 = threading.Thread(target=stderr_reader)
            t2.daemon = True
            t2.start()
            self.__logging_tread.append(t2)

            self.__log_system.log("Server[%d]: %s" % (self.PORT, "start logging"))

        def send_async(self, data, timeout=15, callback=None):
            """
            Отправляет код на сервер асинхронно.
            Выполняет callback(result, error=None) в главном потоке Ren'Py после завершения.
            """

            def target():
                try:
                    result = self.send(data, timeout)
                    if callback:
                        # вызываем callback(result, None) в главном потоке Ren'Py
                        renpy.invoke_in_main_thread(callback, result, None)
                except Exception as e:
                    if callback:
                        # вызываем callback(None, e) в главном потоке Ren'Py
                        renpy.invoke_in_main_thread(callback, None, e)

            t = threading.Thread(target=target)
            t.setDaemon(True)
            t.start()

        def close(self):
            """защита от рекурсии реализованно в поле __active"""
            if self.__active:
                try:
                    if self.is_alive():
                        self.send("EXIT")
                except Exception:
                    pass
                self.__active = False
                self.__server_is_alive = False
                self.__pybridge.close_server(self)


    pylog = LogSystem()
    pybridge = PyBridge()
    
    # Очистка временных файлов при выходе
    def cleanup_pybridge():
        pybridge.cleanup()
    
    config.quit_callbacks.append(cleanup_pybridge)

