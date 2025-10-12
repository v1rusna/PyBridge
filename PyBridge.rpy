"""
# Для совместимости с обычным python:
if sys.version_info[0] >= 3:
    import types
    import os
    # Создаём минимальные заглушки, которые ожидает модуль
    renpy = types.SimpleNamespace(
        log=print,
        invoke_in_main_thread=lambda cb, *a, **k: cb(*a, **k),  # просто вызываем колбэк сразу
        loader=types.SimpleNamespace(transfn=lambda p: p)
    )
    config = types.SimpleNamespace(quit_callbacks=[])
else:
    class _NS(object):
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    renpy = _NS(log=print, invoke_in_main_thread=lambda cb, *a, **k: cb(*a, **k),
            loader=_NS(transfn=lambda p: p))
    config = _NS(quit_callbacks=[])
"""

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
        def __init__(self, filename="pybridge.log"):
            self.path = "v1rus_team/PyBridge/logs/"
            self.filename = self.path+filename
            self.file = None
            self.enabled = True
            self._lock = threading.Lock()
            #self.__size_cache = 0
            self.open()

        def __del__(self):
            self.close()

        def open(self):
            if self.file is None and self.enabled:
                try:
                    if not os.path.exists(self.path):
                        os.makedirs(self.path)
                    self.file = codecs.open(self.filename, "a", encoding="utf-8")
                    self.log("Log started")
                except Exception as e:
                    try:
                        renpy.log("LogSystem: Failed to open log file: %s" % e)
                    except:
                        pass
                    self.file = None

        def close(self):
            if self.file:
                try:
                    self.log("Log closed")
                    self.file.close()
                except Exception as e:
                    try:
                        renpy.log("LogSystem: Failed to close log file: %s" % e)
                    except:
                        pass
                self.file = None

        def log(self, message, no_lock=False):
            if no_lock:
                self.__log(message)
            else:
                with self._lock:
                    self.__log(message)

        def __log(self, message):
            if not self.enabled:
                return
            if self.file is None:
                self.open()

            try:
                if os.path.exists(self.filename) and os.path.getsize(self.filename) > 5 * 1024 * 1024:
                    self.file.close()
                    os.rename(self.filename, self.filename + ".old")
                    self.open()

                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                self.file.write("[%s] %s\n" % (timestamp, message))
                self.file.flush()
            except Exception as e:
                try:
                    renpy.log("LogSystem: Failed to write to log file: %s" % e)
                    renpy.log("Original message for file '%s': %s" % (self.filename, message))
                except:
                    pass

    class PyBridge(object):
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
            full_python_path = os.path.join("game", path)
            if not os.path.exists(full_python_path):
                raise PyBridgeInitException("Default Python executable not found: %s" % path)

            # --- Версия Python по умолчанию ---
            if version is None:
                version = "3.13.7"

            # --- Серверный файл по умолчанию ---
            if server_default is None:
                server_default = "PyBridge/python_embed_server.py"

            full_server_path = os.path.join("game", server_default)
            if not os.path.exists(full_server_path):
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
                server = self.create_server()
                if server and server.is_alive():
                    with self._lock:
                        self.__process_pool.append(server)
                    self._log("Pool: started server %d on port %d" % (i, server.PORT))

        def _get_server_from_pool(self):
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
                server = min(self.__process_pool, key=lambda s: s.tasks_count())

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

        def create_server(self, version="3.13.7", port=5000):
            """Создает объект серверного Python процесса указанной версии на указанном порту"""
            try:
                with self._lock:
                    # Уже активен сервер этой версии
                    for server in self.__all_servers:
                        if version == server.version():
                            return server

                    if version not in self.__server_python:
                        raise PyBridgeException("Server for Python version '%s' not found" % version)

                    python_path = self._get_temp_python(version)
                    temp_path = self.__create_temp_file(self.__server_python[version])

                    # Найти свободный порт
                    port = self._find_free(self.__busy_ports, start=port, end=60000)

                proc = self.__popenen(python_path, [temp_path, str(port)])

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
        
        def python(self, version="3.13.7", code="", seconds=5, args=None, variables=None, cwd=None, input_data=None, use_pool=True, error=True):
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
                            #self.init_pool()
                            self._log("The server on port %s from the pool failed the connection check; the standard method is used." % server.PORT)
                            self.__wrapper(code, variables) #safe_mode
                            out, err = execute()
                            #flags = ["-c", wrapper] + args
                            #out, err = self._exec(python_path, seconds, flags, cwd=cwd, input_data=input_data)
                            return out

                        result = server.send(wrapper)
                        return result[len("RESULT:"):] if result.startswith("RESULT:") else result
                    except Exception as e:
                        if error:
                            raise PyBridgeExecException("Pool execution error: %s" % e)
                else:
                    out, err = execute()
                    #flags = ["-c", wrapper] + args
                    #out, err = self._exec(python_path, seconds, flags, cwd=cwd, input_data=input_data)

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

        def __wrapper(self, code, variables, server_mode=False): #variables, safe_mode, server_mode
            import json, base64
            if not server_mode:
                code_bytes = code.encode('utf-8')
                b64 = base64.b64encode(code_bytes)

                if isinstance(b64, bytes):
                    code_base64 = b64.decode('ascii')
                else:
                    code_base64 = b64


            # подготовим сериализованные переменные
            try:
                vars_json = json.dumps(variables)
            except Exception:
                # если переменные не JSON-сериализуемы — пустой словарь
                vars_json = "{}"

            lines = []
            lines.append("import base64, json, sys, traceback")
            #if safe_mode:
            #    lines.append(self.__make_safe_builtins_code())
            #    lines.append("globals_dict = {'__builtins__': safe_builtins}")
            #else:
            lines.append("globals_dict = globals().copy()")
            lines.append("vars_data = json.loads(%r)" % vars_json)
            lines.append("for k,v in list(vars_data.items()):")
            lines.append("    if not isinstance(k, str) or not k.isidentifier():")
            lines.append("        continue")
            lines.append("    if k.startswith('__'):")
            lines.append("        continue")
            lines.append("    globals_dict[k] = v")
            # декодируем и выполняем исходный код внутри этих глобов
            #lines.append("locals_dict = {}")
            lines.append("def __print(*args, **kwargs):")
            lines.append("    try:")
            lines.append("        print(*args, **kwargs)")
            lines.append("        if not 'result' in globals_dict:")
            lines.append("            globals_dict['result'] = ''")
            lines.append("        res = ' '.join(str(a) for a in args) + '\\n'")
            lines.append("        if res != globals_dict['result']:")
            lines.append("            globals_dict['result'] += ' '.join(str(a) for a in args)")
            lines.append("    except Exception as e:")
            lines.append("        sys.stderr.write('Error in print():\\n' + traceback.format_exc())")
            lines.append("globals_dict['print'] = __print")

            if not server_mode:
                lines.append("code_b = %r" % code_base64)
                lines.append("try:")
                lines.append("    code = base64.b64decode(code_b).decode('utf-8')")
                #lines.append("    # используем отдельные локалы чтобы не давать доступ к родным локалам")
                lines.append("    exec(code, globals_dict)")
                lines.append("except Exception as e:")
                lines.append("    sys.stderr.write('Error in user code:\\n' + traceback.format_exc())")
            else:
                for line in code.split("\n"):
                    lines.append(line)
            wrapper = "\n".join(lines)
            return wrapper

        #def __make_safe_builtins_code(self):
        #    """
        #    Возвращает строку Python-кода, который создаёт словарь safe_builtins
        #    и помещает его в переменную safe_builtins (внутри wrapper).
        #    Это корректно вставляется в текст wrapper'а.
        #    """
        #    # Явно задаём белый список имён, которые возьмём из builtins
        #    safe_names = [
        #        'None','True','False',
        #        'int','float','complex','bool','str','bytes','bytearray',
        #        'list','tuple','set','frozenset','dict',
        #        'range','slice',
        #        'abs','all','any','ascii','bin','chr','divmod','enumerate',
        #        'filter','format','hash','hex','id','isinstance','issubclass',
        #        'iter','len','map','max','min','next','oct','ord','pow','repr',
        #        'reversed','round','sorted','sum','zip'
        #    ]
        #    # Вставим создание словаря безопасных builtins как код-строку
        #    lines = []
        #    lines.append("import builtins as __builtins_mod")
        #    lines.append("safe_builtins = {}")
        #    for name in safe_names:
        #        # присваиваем только если есть в builtins
        #        lines.append("if hasattr(__builtins_mod, '%s'):\n    safe_builtins['%s'] = getattr(__builtins_mod, '%s')" % (name, name, name))
        #    # добавим модули, если хотим
        #    lines.append("import math as __math_mod")
        #    lines.append("safe_builtins['math'] = __math_mod")
        #    lines.append("import itertools as __it_mod")
        #    lines.append("safe_builtins['itertools'] = __it_mod")
        #    # добавим безопасную функцию print (пишет в stderr, но можно сделать логер)
        #    #lines.append("def __safe_print(*args, **kwargs):\n    try:\n        __builtins_mod.print(*args, **kwargs)\n    except Exception:\n        pass")
        #    lines.append("safe_builtins['print'] = __safe_print")
        #    # явное отключение опасных имён (на всякий случай)
        #    banned = ['__import__','open','eval','exec','compile','input','globals','locals','vars','help']
        #    for b in banned:
        #        lines.append("safe_builtins.pop('%s', None)" % b)
        #    return "\n".join(lines)

        def init_python(self, version="3.13.7"):
            """Инициализирует и возвращает путь к Python интерпретатору указанной версии"""
            return self._get_temp_python(version)

        def python_async(self, version="3.13.7", code="", callback=None, seconds=5, args=None, variables=None, cwd=None, input_data=None):
            if not code:
                if callback:
                    # вызываем callback в основном потоке
                    renpy.invoke_in_main_thread(callback, "")
                return

            def target():
                try:
                    result = self.python(version, code, seconds, args, variables, cwd, input_data)
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
                temp_path = os.path.join(self.__temp_dir, os.path.basename(abs_file))
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
            self.__tasks_count = 0
            self.__log_system = LogSystem("pybridge_server_%d.log" % port)
            self.__tasks_lock = threading.Lock()

        def __del__(self):
            self.close()

        def tasks_count(self):
            with self.__tasks_lock:
                return self.__tasks_count

        def get_id(self):
            return self.__id

        def version(self):
            return self.__version

        def send(self, code, timeout=5, buffer_size=65536):
            import socket
            if not self.__active or not self.is_alive():
                self.close()
                raise PyBridgeServerException("Server on port %d not alive" % self.PORT)

            with self.__tasks_lock:
                self.__tasks_count += 1

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
                with self.__tasks_lock:
                    self.__tasks_count -= 1

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
            t = threading.Thread(target=stdout_reader)
            t.daemon = True
            t.start()

            def stderr_reader():
                for line in iter(self.__proc.stderr.readline, b''):
                    if not self.__active:
                        break
                    self.__log_system.log("Server[%d][['error']: %s" % (self.PORT, line.decode('utf-8', errors='replace').strip()))

            t = threading.Thread(target=stderr_reader)
            t.daemon = True
            t.start()

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

