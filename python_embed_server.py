"""
TODO: Структура данных которою нужно сделать
На сервер:
{
    "id": "<уникальный идентификатор запроса>",
    "action": "<действие>", (exec, import, exit),
    "code": "<код для выполнения>", (если action exec)
    "module": "<имя модуля для импорта>" (если action import)
    "variables": {<переменные для контекста выполнения>}, (необязательно)
    "timeout": <таймаут в секундах> (необязательно)
}
От сервера:
{
    "id": "<уникальный идентификатор запроса>",
    status: "<статус выполнения>", (ok, error),
    "result": "<результат выполнения>", (если status ok)
    "stderr": "<текст ошибки>" (если status error),
    "execution_time": <время выполнения в секундах> (необязательно)
}
"""

# python_embed_server.py
import socket, sys, traceback, json


def log(*args, **kwargs):
    kwargs["flush"] = True
    print(*args, **kwargs)


class User:
    def __init__(self, conn: socket.socket):
        self.conn = conn
        log("User connected")

    def recv(self, buffer_size=65536):
        try:
            data = self.conn.recv(buffer_size)
            if not data:
                return
            return data.decode("utf-8")
        except Exception as e:
            log("Receive error:", e, file=sys.stderr)
            return

    def send(self, data):
        if data is None:
            return
        if isinstance(data, dict):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode("utf-8")
        try:
            self.conn.sendall(data)
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except:
            pass
        log("User disconnected")


class ServerEmbed:

    def __init__(self, host="127.0.0.1", port=5000):
        self.HOST = host
        self.PORT = port
        self.server = None

    def bind(self):
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((self.HOST, self.PORT))
            server.listen(1)
            server.settimeout(600)
            log("Socket binded to port", self.PORT)
            return server
        except Exception as e:
            log("Server error:", e, file=sys.stderr)
            traceback.print_exc()

    def cycle(self):
        if self.server is None:
            return

        while True:
            conn, addr = self.server.accept()
            user = User(conn)
            code = user.recv()

            if not code:
                user.close()
                continue

            try:
                if code.startswith("EXIT"):
                    user.send("RESULT:ok")
                    user.close()
                    break

                if code.startswith("IMPORT:"):
                    module_name = code[len("IMPORT:") :].strip()
                    __import__(module_name)
                    user.send("RESULT:ok")
                    user.close()
                    continue

                if code.startswith("PING"):
                    user.send("PONG")
                    user.close()
                    continue

                # Выполняем код в общем контексте
                exec_globals = globals()
                exec_locals = {}

                exec(code, exec_globals, exec_locals)
                result = exec_locals.get("result", "ok")
                user.send("RESULT:" + str(result))
            except Exception:
                user.send("ERROR:\n" + traceback.format_exc())

            user.close()

        log("Shutting down server...")
        self.server.close()

    def start(self):
        self.server = self.bind()
        if self.server is None:
            return

        log("Server started on %s:%s" % (self.HOST, self.PORT))
        self.cycle()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    server = ServerEmbed(port=port)
    server.start()
