
# PyBridge - Documentation

Original documentation in Russian - `README_RU`
The documentation was translated using AI.

## Table of Contents
- [PyBridge - Module Overview](#pybridge---module-overview)
- [Brief Description](#brief-description)
- [Compatibility and requirements](#compatibility-and-requirements)
- [Quick Start](#quick-start)
- [Core Concepts and Terminology](#core-concepts-and-terminology)
- [Code Execution and Result Return Mechanism](#code-execution-and-Result-Return-Mechanism)
- [Usage Examples](#usage-examples)
- [Detailed API](#detailed-api)
- [Auxiliary and Private Elements](#auxiliary-and-private-elements)
- [Module File Structure](#module-file-structure)
- [Logging and Diagnostics](#logging-and-diagnostics)
- [Server Lifecycle / Code Execution](#server-lifecycle--code-execution)
- [Security Recommendations and Limitations](#security-recommendations-and-limitations)
- [Performance and benchmarks](#performance-and-benchmarks)
- [Nuances and Tips](#nuances-and-tips)
- [Common Errors and Troubleshooting](#common-errors-and-troubleshooting)
- [Contacts / Author / License](#contacts--author--license)
- [Appendices](#appendices)

## PyBridge - Module Overview

PyBridge is a module for executing Python code in isolated environments within Ren'Py applications. The module allows running code on different Python versions, managing processes, and safely executing user scripts.

## Brief Description

PyBridge provides a mechanism for executing Python code in separate processes with controlled interpreter versions. Key capabilities:
- Running code on different Python versions (3.13.7 by default)
- Process pool for efficient execution
- Caching and temporary file management
- Asynchronous execution with callback functions
- Logging and error handling

**Compatibility:**
- ✅ Ren'Py 7.x and above
- ✅ Standard Python (with automatic plugins)
- ✅ Support for Unicode and various encodings

The module is particularly useful for game modifications that require executing modern Python code in Ren'Py environments.

## Compatibility and requirements

### Supported platforms
- **Windows**: Python 3.13.7 (included in the module)
- **Linux**: Python 3.13.7 (included in the module)  
- **macOS**: Python 3.13.7 (included in the module)

### Compatibility with regular Python
The module automatically detects the runtime environment and creates the necessary placeholders:

```python
# For compatibility with regular Python:
if sys.version_info[0] >= 3:
    import types
    # Create minimal placeholders for renpy and config
    renpy = types.SimpleNamespace(
        log=print,
        invoke_in_main_thread=lambda cb, *a, **k: cb(*a, **k),
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
```

### Limitations
- Maximum Python interpreter size: 60 MB
- Automatic file integrity checks
- Support for trusted Python versions only

## Quick Start

```python
# Initialization in Ren'Py code happens automatically
init python:
    # Simple code execution
    result = pybridge.python(code="print('Hello World')")
    print(result)  # Output: Hello World

    # Creating a custom Python version
    pybridge.add_python("my_project", "default")
    
    # Asynchronous execution
    def callback(result, error=None):
        if error:
            print(f"Error: {error}")
        else:
            print(f"Result: {result}")
    
    pybridge.python_async(code="2 + 2", callback=callback)
```

## Core Concepts and Terminology

- **PyBridge** - Main class for managing code execution
- **PyServer** - Class representing a Python server process
- **LogSystem** - Module logging system
- **Python Version** - Specific interpreter version (e.g., "3.13.7")
- **Process Pool** - Set of pre-launched servers for fast execution
- **Temporary Python Copy** - Isolated interpreter copy for safe execution

## Code Execution and Result Return Mechanism

### Secure code execution

#### Base64 encoding mechanism

PyBridge uses secure code execution via Base64 encoding:

```python
# Internal execution process:
1. User code → UTF-8 bytes
2. Base64 encoding → secure string
3. Transfer to Python process
4. Base64 decoding → source code
5. Secure execution via exec()
```

This provides protection against escaping and encoding issues for any characters.

### Advanced initialization parameters

#### Full list of PyBridge parameters:

```python
pybridge = PyBridge(
    version="3.13.7",           # Default Python version
    path=None,                  # Path to interpreter (autodetect)
    server_default=None,        # Default server file
    max_age=3600,               # Cache lifetime (seconds)
    pool_size=2,                # Server pool size
    safe_mode=False,            # Safe execution mode
    debug=True,                 # Enable debug output
    decoder=None                # Custom decoding function)
)
```

### Process pool system

#### Automatic server recovery

```python
# PyBridge automatically monitors the status of servers:
- Health check with every request
- Automatic replacement of dead servers
- Fallback to direct execution in case of pool problems
- Load balancing between available servers
```

#### Server selection algorithm

```python
# Intelligent server selection:
1. Search for free servers (up to 50 attempts)
2. Random selection from available servers
3. Forced selection during long waits
4. Automatic recovery of problematic servers
```

### How print Replacement with _log Works

When code is executed through PyBridge, **all `print` calls are automatically replaced with the `_log` function**. This is important to understand as it affects the returned result.

### _log Function Implementation

```python
def _log(*args, **kwargs):
    end = kwargs.get('end', '\n')
    if not isinstance(end, str):
        end = '\n'
    sep = kwargs.get('sep', ' ')
    if not isinstance(sep, str):
        sep = ' '
    if 'result' not in globals_dict:
        globals_dict['result'] = ''
    res = sep.join(str(a) for a in args) + end
    globals_dict['result'] += res
```

### Behavior Examples

#### Example 1: Only print
```python
print("1")  # Replaced with _log("1") → result = "1\n"
print("2")  # Replaced with _log("2") → result = "1\n2\n"
# Final result: "1\n2\n"
```

#### Example 2: Print + explicit result assignment
```python
print("1")      # Replaced with _log("1") → result = "1\n"
print("2")      # Replaced with _log("2") → result = "1\n2\n"
result = "3"    # OVERWRITES result → result = "3"
# Final result: "3" (all previous output is lost)
```

#### Example 3: Explicit assignment + print
```python
result = "start"  # result = "start"
print("middle")   # Replaced with _log("middle") → result = "startmiddle\n"
# Final result: "startmiddle\n"
```

### Practical Recommendations

#### ✅ CORRECT - logic separation
```python
# Use separate variable for debug output
debug_output = []
debug_output.append("Step 1 completed")
debug_output.append(f"Processed {len(data)} elements")

# Use result for final result
result = {
    'data': processed_data,
    'debug': debug_output,  # Explicitly include debug info if needed
    'summary': "Processing completed"
}
```

#### ✅ CORRECT - only result for clean output
```python
# If only clean result is needed
data = [1, 2, 3, 4, 5]
result = {
    'sum': sum(data),
    'average': sum(data) / len(data)
}
# Returns: {'sum': 15, 'average': 3.0}
```

#### ❌ NOT RECOMMENDED - mixing print and result
```python
print("Starting processing")  # Will be added to result
data = load_data()
print(f"Loaded {len(data)} records")  # Will be added to result  
result = process_data()  # Will OVERWRITE all previous output!
# Unpredictable result!
```

#### ✅ ALTERNATIVE - accumulation in result
```python
result = ""  # Explicit initialization
result += "Starting processing\n"
data = load_data()
result += f"Loaded {len(data)} records\n"
processed = process_data()
result += f"Result: {processed}"
# Full control over output
```

### Technical Explanation

**Execution process:**
1. Your code is wrapped in a function with `print` replaced by `_log`
2. `_log` appends output to the existing `result` value
3. If you explicitly assign `result = ...`, it overwrites all accumulated content
4. The current `result` value is returned at the end

**Key rule:** The last assignment to the `result` variable determines the final returned result, overwriting all previous output through `print/_log`.

## Usage Examples

### Example 1: Basic Code Execution
```python
# Synchronous execution
result = pybridge.python(
    version="3.13.7",
    code="import math; result = math.sqrt(16)",
    timeout=5
)
print(result)  # Output: 4.0
```

### Example 2: Passing Variables to Code
```python
# Passing variables to executed code
variables = {
    "name": "Ivan",
    "age": 25
}

result = pybridge.python(
    code="""
greeting = f'Hello, {name}! You are {age} years old.'
result = greeting.upper()
""",
    variables=variables
)
print(result)  # Output: HELLO, IVAN! YOU ARE 25 YEARS OLD.
```

### Example 3: Asynchronous Execution with Callback
```python
def handle_result(result, error=None):
    if error:
        renpy.notify(f"Error: {error}")
    else:
        renpy.notify(f"Result: {result}")

# Asynchronous execution
pybridge.python_async(
    code="import time; time.sleep(2); result = 'Ready!'",
    callback=handle_result
)
```

### Example 4: Compatibility with standard Python
```python
# The module can be tested outside of Ren'Py.
if __name__ == "__main__":
    from PyBridge import pybridge
    
    result = pybridge.python(code="result = 'Hello from standalone Python'")
    print(result)
```

### Example 5: Using logging
```python
init python:
    # Setting up custom logging
    custom_log = LogSystem(
        filename="my_mod.log",
        max_size=2*1024*1024,  # 2 MB
        backup_count=2
    )
    
    def log_mod_activity(message):
        custom_log.info(f“[MyMod] {message}”)
    
    log_mod_activity(“Mod loaded”)
```

### Example 6: Secure transfer of more complex variables
```python
# Transfer of complex data structures
variables = {
    "player_data": {
        "name": "Alexey",
        "level": 5,
        "inventory": ["sword", "potion"]
    },
    "game_state": {
        "day": 3,
        "weather": "sunny"
    }
}

result = pybridge.python(
    code="""
# Variables are automatically serialized via JSON.
player_name = player_data['name']
weather = game_state['weather']
result = f"{player_name} is traveling on a {weather} day"
""",
    variables=variables
)
```

## Detailed API

### ProcessManager Class

**ProcessManager** - a system class for managing processes and ensuring reliable termination on timeouts.

```python
# Usage example
manager = ProcessManager()
proc = manager.create_process(["python", "-c", "print('Hello')"])
stdout, stderr, code = manager.wait_with_timeout(proc, timeout=5)
```

#### `ProcessManager.create_process(command, cwd=None)`
Creates a process with automatic registration for subsequent cleanup.

#### `ProcessManager.wait_with_timeout(proc, timeout, timeout_code=-9)`
Waits for process completion with timeout. If timeout is exceeded, the process is forcibly terminated.

#### `ProcessManager.cleanup_all()`
Terminates all active processes registered with the manager.

### PyBridge Class

Main class for managing Python code execution.

#### `PyBridge.__init__(version=None, path=None, server_default=None, max_age=3600, pool_size=2, safe_mode=True, debug=True, decoder=None)`

Initializes a PyBridge instance.

**Parameters:**

| Parameter      | Type     | Default | Description                     |
| -------------- | -------- | ------- | ------------------------------- |
| version        | str      | None    | Default Python version          |
| path           | str      | None    | Path to Python executable       |
| server_default | str      | None    | Path to server file             |
| max_age        | int      | 3600    | Cache lifetime in seconds       |
| pool_size      | int      | 2       | Process pool size               |
| safe_mode      | bool     | False   | Safe execution mode             |
| debug          | bool     | True    | Enable debugging                |
| decoder        | callable | None    | Output decoding function        |

**Exceptions:**
- `PyBridgeInitException`: when creating instance repeatedly

#### `PyBridge.add_python(version, path, server_file="default")`

Adds a Python version for use.

| Parameter   | Type | Default  | Description             |
| ----------- | ---- | -------- | ----------------------- |
| version     | str  | -        | Version identifier      |
| path        | str  | -        | Path to interpreter     |
| server_file | str  | "default" | Path to server file     |

**Parameters:**

```python
pybridge.add_python("my_version", "path/to/python", "path/to/server.py")
```

**Exceptions:**
- `PyBridgeFileException`: python cannot find the specified path or it exceeds 60MB.

#### `PyBridge.python(version="3.13.7", code="", timeout=5, args=None, variables=None, persist_variables=False, cwd=None, input_data=None, use_pool=True)`

Executes Python code synchronously.

**Parameters:**

| Parameter         | Type      | Default  | Description                                   |
| ----------------- | --------- | -------- | --------------------------------------------- |
| version           | str       | "3.13.7" | Python version                                |
| code              | str       | ""       | Code to execute                               |
| timeout           | int       | 5        | Execution timeout (in seconds)                |
| args              | list      | None     | Command-line arguments                        |
| variables         | dict      | None     | Variables to include in the execution context |
| persist_variables | bool      | False    | Whether to use persistent variables           |
| cwd               | str       | None     | Working directory                             |
| input_data        | str/bytes | None     | Input data for the process                    |
| use_pool          | bool      | True     | Whether to use a process pool                 |

**Returns:**
`str` — the execution result (`stdout`)

**Exceptions:**

* `PyBridgeExecException` — raised when an execution error occurs

```python
result = pybridge.python(
    version="3.13.7",
    code="x = 10; y = 20; result = x + y",
    timeout=10
)
```

### Persistent Variables

If `persist_variables = True`, a `persistent` class is automatically created in the code.
This class contains **all persistent variables** that have been defined.

Example:

```python
class persistent:
    bomb = False
    flag_olga_goodreal = False
    flag_olga_true = False
    ssg_1 = True
    cleaner_unsupported_renpy = False
    picture17 = "yes"
    rfg_sprite_time = "day"
    CardsDemo = True
    mt_7dl_bad = 1
    ...
    
# Example of using a persistent variable
if persistent.bomb:
    ...
```

#### `PyBridge.python_async(version="3.13.7", code="", callback=None, timeout=5, args=None, variables=None, persist_variables=False, cwd=None, input_data=None)`

Executes Python code asynchronously.

**Parameters:**
Same as `python()`, plus:

| Parameter | Type     | Default | Description        |
| --------- | -------- | ------- | ------------------ |
| callback  | callable | None    | Callback function  |

```python
def my_callback(result, error):
    if error:
        print(f"Error: {error}")
    else:
        print(f"Result: {result}")

pybridge.python_async(code="2 * 3", callback=my_callback)
```

#### `PyBridge.exec_temp_file(src_path, version="3.13.7", timeout=10, cache=False, related_files=None, cwd=None)`

Executes a Python script from a file with support for dependent files and custom working directory.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| src_path | str | - | Path to the main executable file |
| version | str | "3.13.7" | Python version |
| timeout | int | 10 | Execution timeout |
| cache | bool | False | Cache temporary file |
| related_files | list | None | List of dependent files |
| cwd | str | None | Execution working directory |

**Returns:** `str` - execution stdout

#### `PyBridge.create_server(version="3.13.7", port=5000)`

Creates a server process.

**Parameters:**

| Parameter    | Type | Default | Description                |
| ------------ | ---- | ------- | -------------------------- |
| version      | str  | "3.13.7" | Python version             |
| port         | int  | 5000    | Server port                |

**Returns:** `PyServer` - server object

#### `PyBridge.get_path(path)`
**Purpose:** Normalizes a path using Ren'Py's path transformation system
```python
# Usage example
normalized_path = pybridge.get_path("game/scripts/main.py")
```

#### `PyBridge.init_pool()`
**Purpose:** Explicitly initializes the server pool for preloading
```python
# Recommended for performance optimization
pybridge.init_pool()
```

#### `PyBridge.list_versions()`
**Purpose:** Returns a list of all available Python versions
```python
versions = pybridge.list_versions()
print(f"Available versions: {versions}")
```

#### `PyBridge.get_info(version)`
**Purpose:** Returns detailed information about the Python interpreter
```python
info = pybridge.get_info("3.13.7")
print(f"Python version: {info['version']}")
```

#### `PyBridge.remove_python(version)`
**Purpose:** Removes a Python version from the system and closes associated servers
```python
pybridge.remove_python("old_version")
```

#### `PyBridge.debug_info()`
**Purpose:** Outputs comprehensive debug information about the module state
```python
pybridge.debug_info()
```

### PyServer Class

Manages Python server process.

#### Server Protocol

##### Server Protocol Commands

PyBridge server supports an extended set of commands:

| Command | Purpose | Example |
|---------|---------|---------|
| **Python code** | Execution of arbitrary code | `print("Hello")` |
| **EXIT** | Server shutdown | `EXIT` |
| **IMPORT:module** | Import module into global namespace | `IMPORT:json` |
| **PING** | Server availability check | `PING` |

##### Server Response Formats

```python
# Successful execution
"RESULT:execution result"

# Execution error  
"ERROR:error message"

# Response to PING
"PONG"
```

#### `PyServer.__init__(version, pybridge, port, proc, python_path, random_id)`

Server constructor with additional control parameters.

**Parameters:**

| Name        | Type             | Default | Description                    |
| ----------- | ---------------- | ------- | ------------------------------ |
| version     | str              | -       | Python version                 |
| pybridge    | PyBridge         | -       | Parent PyBridge instance       |
| port        | int              | -       | Server port                    |
| proc        | subprocess.Popen | -       | Process object                 |
| python_path | str              | -       | Path to the Python interpreter |
| random_id   | int              | -       | Unique server identifier       |

#### `pyserver.is_busy()`

**Returns:** `bool` – True if the server is currently executing a task

**Example:**

```python
server = pybridge.create_server("3.13.7")
if not server.is_busy():
    result = server.send("print('Hello')")
```


#### `PyServer.send(code, timeout=5, buffer_size=65536)`

Sends code to server for execution.

**Parameters:**

| Parameter   | Type | Default | Description          |
| ----------- | ---- | ------- | -------------------- |
| code        | str  | -       | Code to execute      |
| timeout     | int  | 5       | Connection timeout   |
| buffer_size | int  | 65536   | Buffer size          |

**Returns:** str - execution result

#### `PyServer.safe_send(code, *a, **kw)`

Safely sends code to the server without causing errors in case of failures.

#### `PyServer.send_file(self, path)`

Reads code from a Python file and sends it to the server for execution.

#### `PyServer.send_async(data, timeout=15, callback=None)`

Asynchronously sends code to server.

#### `PyServer.is_alive(close=True, check_connection=False)`

Checks whether the server is alive.

**Parameters:**

| Name             | Type | Default | Description                                            |
| ---------------- | ---- | ------- | ------------------------------------------------------ |
| close            | bool | True    | Automatically close the server if it is not alive      |
| check_connection | bool | False   | Check the TCP connection instead of the process status |

```python
# Basic check (process status)
if server.is_alive():
    print(“Server is running”)

# TCP connection check  
if server.is_alive(check_connection=True):
    print(“Server is responding to requests”)
```

#### `PyServer.start_logging()`

Starts logging the server’s output in separate threads.

**Details:**

* Creates separate threads for stdout and stderr
* Stores references to the threads in `__logging_tread`
* Logs a message indicating the start of logging

#### `PyServer.get_status()`
**Purpose:** Returns complete diagnostic information about the server

```python
status = server.get_status()
print(f“Server {status[‘id’]} on port {status[‘port’]}”)
print(f“Version: {status[‘version’]}”)
print(f“Status: {‘active’ if status[‘alive’] else ‘inactive’}”)
print(f“Busy: {‘yes’ if status[‘busy’] else ‘no’}”)
```

### LogSystem Class

#### Reliable log rotation

```python
# Automatic size management:
- Rotation when max_size is exceeded (default 5 MB)
- Saving backup_count backup copies
- Backup logging via renpy.log in case of file system errors
```

#### `LogSystem.__init__(filename=“pybridge.log”, max_size=5242880, backup_count=3)`
Constructor with log rotation support.

| Parameter | Type | Default | Description |
|----------|---- -|--------------|----------|
| filename | str | pybridge.log | Log file |
| max_size | int | 5242880 | Maximum log file size |
| backup_count | int | 3 | Maximum number of log files remaining after rotation |

#### `LogSystem.log(message, no_lock=False, level="INFO")`

Writes a message to the log; the class uses `threading.Lock()`, `no_lock=True` disables it.

#### `LogSystem.info(message)`, `warning(message)`, `error(message)`, `debug(message)`
Methods for different logging levels.

#### `LogSystem.disable()`, `enable()`
Enable/disable logging.

#### `LogSystem.to_unicode(message)`
**Purpose:** Universal conversion to Unicode

```python
# Supports all data types:
log.to_unicode("string")           # Unicode strings
log.to_unicode(b"bytes")           # Byte strings  
log.to_unicode(123)                # Numbers
log.to_unicode({"key": "value"})   # Complex objects
```

## Auxiliary and Private Elements

The following elements are considered internal and not recommended for direct use unless you understand the consequences:

- All methods/fields with `__` prefix (e.g., `__temp_pythons`, `__create_temp_file`, `__get_hash`, `__cache_info`).
- `__wrapper`, `__popenen` — low-level helpers.
- Internal lock structures: `_lock`, `__tasks_lock`.

These elements are for internal logic and may change between versions.

### Internal PyBridge Methods (internal)

- `_get_temp_python(version)`: Creates and returns path to temporary Python copy for isolation
- `_exec(python_path, timeout, flags, cwd, input_data)`: Internal method for Python process execution
- `_decoder(stdout, stderr)`: Decodes process output considering system locale
- `_get_server_from_pool()`: Gets available server from process pool
- `_has_pip(python_path, timeout)`: Checks pip presence in interpreter
- `_log(message)`: Internal logging with PyBridge prefix
- `_find_free(used_set, start, end)`: Finds free number in range
- `__wrapper(code, variables)`: Creates wrapper for safe code execution
- `__clear_cache()`: Clears outdated cached files
- `__get_hash(code)`: Generates hash for caching
- `__get_file_hash(file_path)`: Generates file hash
- `__set_cache(path, key)`: Saves path to cache
- `__get_cache(key)`: Gets data from cache
- `__create_temp_file(file, cache)`: Creates temporary file copy
- `__popenen(python_path, flags, cwd)`: Starts Python process
- `__wait_for_server(port, timeout)`: Waits for server startup
- `__create_temp_file(file, cache, no_rename)`: Creates temporary copies of files and executes them

### Internal PyServer Methods (internal)

- `start_logging()`: Starts thread for server output logging
- `tasks_count()`: Returns count of active server tasks

### Internal LogSystem Methods (internal)

- `open()`: Opens log file
- `close()`: Closes log file

**Note**: Methods with double underscore (`__method`) are considered private and not intended for direct use.

## Module File Structure

```
game/
├── PyBridge/
│   ├── python/                    # Built-in Python interpreters
│   │   ├── win/
│   │   │   └── python.exe         # Python for Windows
│   │   ├── linux/
│   │   │   └── bin/python3        # Python for Linux
│   │   └── mac/
│   │       └── bin/python3        # Python for macOS
│   └── python_embed_server.py     # Standard server script
├── v1rus_team/
│   └── PyBridge/
│       └── logs/                  # Log directory
│           ├── pybridge.log       # Main module log
│           └── pybridge_server_*.log  # Individual server logs
└── [your_mod]/
    └── mod_assets/
        └── scripts/
            └── *.rpy              # Your custom scripts
```

## Logging and Diagnostics

### Improved logging system
LogSystem supports:
- **Log rotation** by size (5 MB by default)
- **Logging levels**: INFO, WARNING, ERROR, DEBUG
- **Backup copies** (up to 3 files)
- **Unicode processing** and different encodings

```python
# Using logging in RenPy
pylog.info("Informational message")
pylog.warning("Warning")  
pylog.error("Runtime error")
pylog.debug("Debug information")

# Creating your own logger
log_system = LogSystem(
    filename="custom.log",
    max_size=10*1024*1024,  # 10 MB
    backup_count=5)

```

### Logging System

PyBridge uses multi-level logging system:

1. **Main logging** - `v1rus_team/PyBridge/logs/pybridge.log`
2. **Server logs** - `v1rus_team/PyBridge/logs/pybridge_server_<port>.log`
3. **Backup logging** - via `renpy.log()` on filesystem errors

### Using log Function in Executed Code

When executing code, a `log` function is automatically created - a safe wrapper over `print`:

```python
result = pybridge.python(
    version="3.13.7",
    code="""
log("Starting complex calculations")
import time

# Long operation
start_time = time.time()
data = [i**2 for i in range(10000)]
end_time = time.time()

log(f"Calculations took: {end_time - start_time:.2f} seconds")
log(f"Created {len(data)} elements")
result = sum(data)
"""
)
```

### Diagnostics and Debugging

```python
init python:
    def debug_pybridge():
        """Comprehensive PyBridge diagnostics"""
        try:
            # Check available versions
            versions = pybridge.list_versions()
            print(f"Available Python versions: {versions}")
            
            # Check active servers
            active_servers = pybridge.get_active_servers()
            print(f"Active servers: {len(active_servers)}")
            
            # Detailed version information
            for version in versions:
                try:
                    info = pybridge.get_info(version)
                    print(f"Information about {version}: {info.get('version', 'N/A')}")
                except Exception as e:
                    print(f"Error getting information about {version}: {e}")
            
            # Debug information
            pybridge.debug_info()
            
            return "Diagnostics completed"
        except Exception as e:
            return f"Diagnostics error: {e}"

    # Run diagnostics
    debug_result = debug_pybridge()
    print(debug_result)
```

### Server Health Monitoring

```python
init python:
    def check_server_health():
        """Check health of all servers"""
        healthy_servers = []
        problematic_servers = []
        
        for server in pybridge.get_all_servers():
            if server.is_alive():
                healthy_servers.append(server)
            else:
                problematic_servers.append(server)
        
        print(f"Healthy servers: {len(healthy_servers)}")
        print(f"Problematic servers: {len(problematic_servers)}")
        
        # Restart problematic servers
        for server in problematic_servers:
            try:
                pybridge.close_server(server)
                new_server = pybridge.create_server(server.version())
                print(f"Restarted server {server.version()} on port {new_server.PORT}")
            except Exception as e:
                print(f"Error restarting server {server.version()}: {e}")
```

## Server Lifecycle / Code Execution

### Detailed Code Execution Process

1. **Environment Initialization**
   ```python
   # Temporary Python copy is created
   temp_python = pybridge._get_temp_python("3.13.7")
   ```

2. **Code Preparation**
   ```python
   # Code is wrapped for safe execution
   wrapped_code = pybridge.__wrapper("print('Hello')", {})
   ```

3. **Execution Method Selection**
   - Via process pool (use_pool=True)
   - Direct process launch (use_pool=False)

4. **Result Processing**
   - Output decoding
   - Error handling
   - Temporary resource cleanup

### Server Lifetime Management

```python
init python:
    class ServerManager:
        def __init__(self):
            self.last_activity = time.time()
            
        def keep_alive(self):
            """Keeps servers active"""
            current_time = time.time()
            if current_time - self.last_activity > 300:  # 5 minutes
                self._ping_servers()
                self.last_activity = current_time
        
        def _ping_servers(self):
            """Ping servers to maintain activity"""
            for version in pybridge.list_versions():
                try:
                    pybridge.python(
                        version=version,
                        code="result = 'ping'",
                        timeout=2,
                        use_pool=True
                    )
                except Exception as e:
                    print(f"Ping failed for server {version}: {e}")
    
    # Create server manager
    server_manager = ServerManager()
    
    # Regular call in game loop
    def periodic_keep_alive():
        server_manager.keep_alive()
    
    # Call every 2 minutes (example for Ren'Py)
    # config.periodic_callback = periodic_keep_alive
```

### Automatic Server Recovery

```python
init python:
    def execute_with_fallback(code, version="3.13.7", max_retries=2):
        """Execute code with automatic recovery on failures"""
        for attempt in range(max_retries + 1):
            try:
                result = pybridge.python(
                    version=version,
                    code=code,
                    timeout=10,
                    use_pool=True
                )
                return result
            except PyBridgeServerException as e:
                if attempt < max_retries:
                    print(f"Attempt {attempt + 1}: Restarting server...")
                    # Close problematic server
                    try:
                        pybridge.close_server(pybridge._get_server_from_pool())
                    except:
                        pass
                    # Create new one
                    pybridge.create_server(version=version)
                    time.sleep(1)  # Give time for startup
                else:
                    raise e
    
    # Usage
    try:
        result = execute_with_fallback("import os; result = os.cpu_count()")
        print(f"Core count: {result}")
    except Exception as e:
        print(f"All attempts failed: {e}")
```

## Security Recommendations and Limitations

### PyBridge automatically checks:
- Python interpreter size (no more than 60 MB)
- Existence of necessary files
- Integrity of temporary copies

### Secure serialization
- Variables are serialized via JSON
- Variable identifiers are checked
- System variables (with `__`) are excluded

### Creating Isolated Environments

```python
init python:
    # RECOMMENDED: Create separate versions for each mod
    pybridge.add_python("my_mod_v1", "default")
    pybridge.add_python("another_mod_v1", "default")
    
    # NOT RECOMMENDED: Using shared version
    # pybridge.python(version="3.13.7", code="...")  # May conflict!
```

### Access Rights Limitation

```python
init python:
    def safe_execute(code, timeout=5):
        """Safe execution of user code"""
        # Limit execution time
        result = pybridge.python(
            code=code,
            timeout=timeout,
            safe_mode=True,
            use_pool=True  # Isolation in process pool
        )
        return result
    
    # Example with untrusted code
    user_code = """
# Potentially dangerous operations blocked in safe_mode
import sys
try:
    # These operations may be restricted
    sys.exit(1)
except:
    result = "Safe execution"
"""
    
    safe_result = safe_execute(user_code, timeout=3)
```

### Large Data Processing

```python
init python:
    def process_large_data(data_chunks):
        """Large data processing with memory control"""
        results = []
        
        for i, chunk in enumerate(data_chunks):
            try:
                result = pybridge.python(
                    code=f"""
# Process data chunk
chunk = {chunk}
result = sum(x * 2 for x in chunk)
""",
                    timeout=30,  # Increased timeout
                    use_pool=True
                )
                results.append(result)
                
                # Memory cleanup between executions
                if i % 10 == 0:
                    pybridge.reset()
                    
            except PyBridgeExecException as e:
                print(f"Error processing chunk {i}: {e}")
                continue
        
        return results
```

## Performance and Benchmarks

### Performance Testing Results

Below are the results of performance tests for different execution methods in **PyBridge**.
The benchmark task was computing the sum of numbers from 0 to 1,000,000 (`sum(range(10**6))`).

#### Test Configuration

```python
import threading
from PyBridge.PyBridge import *

pybridge.POOL_SIZE = 2  # Process pool size
pybridge.init_python()
pybridge.init_pool()
pybridge.debug = False  # Disable debug output

test_range = 100  # Number of iterations
```

#### Execution Method Comparison

| Method                           | Iterations | Execution Time | Speedup   | Notes                                             |
| -------------------------------- | ---------- | -------------- | --------- | ------------------------------------------------- |
| **Direct execution** (case 4)    | 100        | 3.27 s         | 1x        | Baseline benchmark in the main process            |
| `use_pool=False` (case 1)        | 100        | 11.30 s        | 0.29x     | Worst result — spawns a new process for each call |
| `use_pool=True` (case 2, pool=2) | 100        | 5.38 s         | 0.61x     | Twice as fast as without a pool                   |
| `use_pool=True` (case 2, pool=4) | 100        | 5.12 s         | 0.64x     | Slight improvement with larger pool               |
| `python_async` (case 3)          | 100        | **1.29 s**     | **2.53x** | **Best result — asynchronous execution**          |
| Multithreading (case 5)          | 100        | Not measured   | –         | Slow due to GIL and thread creation overhead      |

---

### Detailed Test Analysis

#### Test 1: Synchronous Execution without Pool (`use_pool=False`)

```python
# Worst performance — spawns a new process for each request
start = time.time()
for i in range(test_range):
    res = pybridge.python(code="result = sum(range(10**6))", use_pool=False)
    print(f"iter: {i}")
print(f"Time: {time.time() - start:.2f} s")  # ~11.30 s
```

**Conclusion:** Avoid `use_pool=False` for batch operations.

---

#### Test 2: Synchronous Execution with Pool (`use_pool=True`)

```python
# Significant acceleration through process reuse
start = time.time()
for i in range(test_range):
    res = pybridge.python(code="result = sum(range(10**6))", use_pool=True)
    print(f"iter: {i}")
print(f"Time: {time.time() - start:.2f} s")  # ~5.12–5.38 s
```

**Conclusion:** Twice as fast as spawning new processes. Recommended for synchronous workloads.

---

#### Test 3: Asynchronous Execution (`python_async`)

```python
# Best performance — parallel execution
done = []
start = time.time()
for i in range(test_range):
    pybridge.python_async(
        code="result = sum(range(10**6))",
        callback=my_callback,  # Callback appends to the 'done' list
    )

while len(done) < test_range:
    time.sleep(0.01)
print(f"Time: {time.time() - start:.2f} s")  # ~1.29 s
```

**Conclusion:** 2.5× faster than direct execution. Ideal for background or parallel tasks.

---

#### Test 4: Direct Execution (Baseline)

```python
# Baseline benchmark without PyBridge
start = time.time()
for i in range(test_range):
    print(sum(range(10**6)))
print(f"Time: {time.time() - start:.2f} s")  # ~3.27 s
```

**Conclusion:** Surprisingly, `PyBridge` with asynchronous execution outperforms native direct execution.

---

#### Test 5: Native Multithreading

```python
# Performance issues due to thread creation and the GIL
def test_async(callback):
    def target():
        for i in range(test_range):
            sum(range(10**6))
        callback()
    t = threading.Thread(target=target)
    t.setDaemon(True)
    t.start()

# Not measured due to overhead in thread creation
```

**Conclusion:** PyBridge outperforms native Python threads for CPU-bound tasks.

---

### Practical Recommendations

#### For Maximum Performance:

```python
# ✅ Recommended: asynchronous execution with callback
def handle_result(result, error=None):
    if error:
        print(f"Error: {error}")
    else:
        # Process the result
        pass

pybridge.python_async(
    code="result = heavy_computation()",
    callback=handle_result,
    use_pool=True  # About 0.5 s faster in tests
)
```

#### For Synchronous Tasks:

```python
# ✅ Recommended for serial execution
result = pybridge.python(
    code="result = sync_computation()", 
    use_pool=True  # Always enable for repeated tasks
)
```

#### Avoid:

```python
# ❌ Not recommended — creating a process for each operation
for i in range(100):
    result = pybridge.python(code="...", use_pool=False)

# ❌ Inefficient — native threading for CPU-bound tasks
```

---

### Conclusions

1. **Asynchronous execution** with `python_async` and `use_pool=True` delivers the best performance.
2. **Process pooling** speeds up synchronous operations by roughly 2× compared to spawning separate processes.
3. **PyBridge outperforms native multithreading** for computational workloads.
4. **Optimal pool size**: 2–4 processes for most real-world use cases.

These results demonstrate that PyBridge not only provides isolation and safety but also achieves excellent performance when used effectively.

## Nuances and Tips

#### 1. For Maximum Performance:

```python
# 1. Pre-initialize Python
pybridge.init_python("my_version")

# 2. Pre-initialize pool
pybridge.init_pool()

# 3. Regular server status monitoring
def periodic_health_check():
    for server in pybridge.get_servers():
        if not server.is_alive(check_connection=True):
            print(f"Restarting problematic server {server.get_id()}")
            # Restart logic

# 4. Use caching for frequently executed scripts
result = pybridge.exec_temp_file("common_script.py", cache=True)
```

#### 2. For Debugging and Development:

```python
# Enable detailed logging
pylog.debug("Debug information")
pybridge.debug_info()

# Monitor specific server
server = pybridge.create_server()
status = server.get_status()
print(f"Server status: {status}")
```

### 3. Efficient Process Pool Usage

```python
init python:
    def optimized_batch_processing(tasks):
        """Batch processing with optimal pool usage"""
        results = []
        
        # Pre-warm pool
        if not pybridge.get_active_servers():
            pybridge.init_pool()
        
        for task in tasks:
            result = pybridge.python(
                code=task['code'],
                variables=task.get('variables', {}),
                use_pool=True,  # Key optimization
                timeout=task.get('timeout', 5)
            )
            results.append(result)
        
        return results
```

### 4. Caching Frequently Used Scripts

```python
init python:
    # Caching heavy scripts
    def get_cached_script_result(script_path, version="3.13.7"):
        """Script execution with caching"""
        return pybridge.exec_temp_file(
            src_path=script_path,
            version=version,
            cache=True,  # Caching enabled
            timeout=30
        )
    
    # First call - cache created
    result1 = get_cached_script_result("scripts/heavy_calculation.py")
    
    # Subsequent calls - cache used
    result2 = get_cached_script_result("scripts/heavy_calculation.py")
```

### 5. Proper Error Handling

```python
init python:
    def robust_python_execution(code, **kwargs):
        """Reliable code execution with comprehensive error handling"""
        try:
            return pybridge.python(code=code, **kwargs)
            
        except PyBridgeExecException as e:
            # Code execution errors
            print(f"Execution error: {e}")
            return None
            
        except PyBridgeServerException as e:
            # Server problems
            print(f"Server error: {e}")
            return None
            
        except PyBridgeCacheException as e:
            # Cache problems
            print(f"Cache error: {e}")
            # Continue without cache
            kwargs['use_pool'] = False
            return pybridge.python(code=code, **kwargs)
```

### 6. Asynchronous Operations for UI

```python
init python:
    def async_with_progress(code, callback, progress_callback=None):
        """Asynchronous execution with progress tracking"""
        progress = 0
        
        def update_progress():
            nonlocal progress
            progress += 25
            if progress_callback and progress <= 100:
                renpy.invoke_in_main_thread(progress_callback, progress)
        
        def execute():
            # Progress simulation
            for i in range(4):
                time.sleep(0.5)
                update_progress()
            
            # Main execution
            try:
                result = pybridge.python(code=code, timeout=30)
                renpy.invoke_in_main_thread(callback, result, None)
            except Exception as e:
                renpy.invoke_in_main_thread(callback, None, e)
        
        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()
    
    # Usage in interface
    def show_loading_screen(progress):
        renpy.show_screen("loading_screen", progress=progress)
    
    def on_calculation_done(result, error):
        if error:
            renpy.notify(f"Error: {error}")
        else:
            renpy.notify(f"Result: {result}")
        renpy.hide_screen("loading_screen")
    
    # Launch
    async_with_progress(
        code="import time; time.sleep(2); result = 'Ready!'",
        callback=on_calculation_done,
        progress_callback=show_loading_screen
    )
```

### 7. Modular Projects
```python
dependencies = []
for root, dirs, files in os.walk("my_project"):
    for file in files:
        if file.endswith(".py"):
            dependencies.append(os.path.join(root, file))

result = pybridge.exec_temp_file(
    src_path="my_project/main.py",
    related_files=dependencies
)
```

#### Example 8: Comprehensive Server Monitoring

```python
def monitor_servers():
    """Extended monitoring of all servers' status"""
    servers = pybridge.get_servers()
    
    for server in servers:
        status = server.get_status()
        print(f"Server {status['id']}:")
        print(f"  Port: {status['port']}")
        print(f"  Version: {status['version']}")
        print(f"  Status: {'🟢 Active' if status['alive'] else '🔴 Inactive'}")
        print(f"  Busy: {'🔒 Yes' if status['busy'] else '🔓 No'}")
        print(f"  History: {len(status['history'])} commands executed")
        
        # Detailed connection check
        if server.is_alive(check_connection=True):
            print("  Connection: ✅ Stable")
        else:
            print("  Connection: ❌ Issues")
```

## Common Errors and Troubleshooting

### Error: “Python version weighs more than 60 MB”
**Cause**: Python file is too large
**Solution**: Use official Python versions

### Unicode encoding error
**Cause**: Output encoding issues
**Solution**: PyBridge automatically uses utf-8 and fallback encodings

### Error: "PyBridge instance already created"

**Symptoms**: Exception when creating PyBridge
**Cause**: Global instance already created in `init -9999 python`
**Solution**: Use ready instance `pybridge`

```python
# Incorrect:
init python:
    my_bridge = PyBridge()  # Error!

# Correct:
init python:
    # Use existing instance
    result = pybridge.python(code="2+2")
```

### Error: "Default Python executable not found"

**Symptoms**: Module cannot find Python interpreter
**Cause**: Python files not copied to game/PyBridge/
**Solution**: Ensure structure exists:
```
game/PyBridge/python/win/python.exe
game/PyBridge/python/linux/bin/python3  
game/PyBridge/python/mac/bin/python3
```

### Error: "No free slots in range 5000-6000"

**Symptoms**: Cannot start server due to busy ports
**Cause**: Many active servers or port conflicts
**Solution**:

```python
init python:
    # Cleanup and restart
    pybridge.cleanup()
    pybridge.reset()
    
    # Manual port specification
    server = pybridge.create_server(port=6001)
```

### Error: "Python process timeout after X seconds"

**Symptoms**: Code execution exceeds allowed time
**Solution**:

```python
init python:
    # Increase timeout
    result = pybridge.python(
        code="import time; time.sleep(10); result = 'done'",
        timeout=15  # Increase timeout
    )
    
    # Or code optimization
    optimized_code = """
# Instead of time.sleep use efficient algorithms
result = sum(i for i in range(1000000))  # Faster than sleep
"""
```

### Error: "Failed to write to log file"

Error is not critical and may only appear in config.log
**Symptoms**: Problems writing logs
**Cause**: Missing write permissions or disk full
**Solution**:

```python
init python:
    # Check log directory availability
    import os
    log_dir = "v1rus_team/PyBridge/logs"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception as e:
            print(f"Failed to create log directory: {e}")
    
    # Use renpy.log as fallback
    renpy.log("PyBridge backup logging")
```

### Performance Errors

**Symptoms**: Slow code execution
**Solution**:

```python
init python:
    def optimize_performance():
        """PyBridge performance optimization"""
        
        # 1. Use process pool
        pybridge.init_pool()
        
        # 2. Cache frequently used scripts
        pybridge.exec_temp_file("common_scripts.py", cache=True)
        
        # 3. Preload modules
        # Only risk if multiple different processes from pool if pool size > 1
        for module in ["math", "json", "random"]:
            try:
                pybridge.python(code=f"import {module}", use_pool=True)
            except:
                pass
        
        # 4. Regular cache cleanup
        pybridge.reset()
```

### Network Issues Diagnostics

```python
init python:
    def diagnose_connection_issues():
        """Diagnose server connection problems"""
        import socket
        
        for server in pybridge.get_all_servers():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', server.PORT))
                sock.close()
                
                if result == 0:
                    print(f"Server on port {server.PORT} available")
                else:
                    print(f"Server on port {server.PORT} unavailable")
            except Exception as e:
                print(f"Error checking port {server.PORT}: {e}")
```

## Contacts / Author / License

**Developer**: v1rus team  
**License**: MIT License
**Module Version**: 10.10.2025
**Compatibility**: Ren'Py 7.x+  

**Support Channel**: [v1rus team Telegram](https://t.me/+VewEitmB66k0MmQy)  
**Bug Reports**: Via mod distribution platform or support channel

**Important**: When using PyBridge in your mods, specify authorship and comply with license terms.

## Appendices

### Complete Usage Example

```python
init python:
    class PyBridgeHelper:
        """Helper class for working with PyBridge"""
        
        def __init__(self, mod_name):
            self.mod_name = mod_name
            self.setup_environment()
        
        def setup_environment(self):
            """Setup execution environment for mod"""
            # Create isolated Python version
            pybridge.add_python(f"{self.mod_name}_python", "default")
            
            # Pre-initialize pool
            pybridge.init_pool()
            
            # Preload common modules
            self.preload_modules(["json", "math", "random", "time"])
        
        def preload_modules(self, modules):
            """Preload modules into process pool"""
            for module in modules:
                try:
                    pybridge.python(
                        code=f"import {module}",
                        use_pool=True,
                        timeout=2
                    )
                except Exception as e:
                    print(f"Failed to preload {module}: {e}")
        
        def safe_execute(self, code, timeout=10, variables=None):
            """Safe code execution with error handling"""
            try:
                return pybridge.python(
                    version=f"{self.mod_name}_python",
                    code=code,
                    timeout=timeout,
                    variables=variables or {},
                    use_pool=True
                )
            except PyBridgeException as e:
                print(f"Code execution error in {self.mod_name}: {e}")
                return None
    
    # Usage in mod
    mod_bridge = PyBridgeHelper("my_awesome_mod")
    
    # Code execution
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

### Server Protocol Example

```python
# Example of manual interaction with PyBridge server
import socket
import json

def send_to_pybridge_server(port, code):
    """Direct code sending to PyBridge server"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        client.connect(('127.0.0.1', port))
        
        # Send code
        client.send(code.encode('utf-8'))
        
        # Receive response
        response = client.recv(65536).decode('utf-8')
        client.close()
        
        return response
    except Exception as e:
        return f"ERROR: {e}"

# Usage
response = send_to_pybridge_server(5000, "print('Hello Server'); result = 42")
print(f"Server response: {response}")  # RESULT:42

```markdown
### PyServer Usage Example for Custom Functionality

```python
init python:
    class CustomPyBridgeClient:
        """Custom client for extended interaction with PyServer"""
        
        def __init__(self, version="3.13.7"):
            self.version = version
            self.server = None
            self.connect()
        
        def connect(self):
            """Establish connection with server"""
            try:
                self.server = pybridge.create_server(
                    version=self.version,
                    port=5000
                )
                print(f"Connected to Python {self.version} server on port {self.server.PORT}")
            except PyBridgeServerException as e:
                print(f"Connection error: {e}")
                self.server = None
        
        def execute_with_retry(self, code, max_retries=3, timeout=10):
            """Execute code with retry attempts"""
            for attempt in range(max_retries):
                try:
                    if not self.server or not self.server.is_alive():
                        self.connect()
                        if not self.server:
                            continue
                    
                    response = self.server.send(code, timeout=timeout)
                    
                    if response.startswith("RESULT:"):
                        return response[7:]  # Remove "RESULT:"
                    elif response.startswith("ERROR:"):
                        print(f"Execution error: {response[6:]}")
                        continue
                    else:
                        return response
                        
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        self.connect()
            
            raise PyBridgeExecException(f"Failed to execute code after {max_retries} attempts")
        
        def import_module(self, module_name):
            """Import module on server"""
            return self.execute_with_retry(f"IMPORT:{module_name}")
        
        def close(self):
            """Close connection"""
            if self.server:
                pybridge.close_server(self.server)
                self.server = None
    
    # Custom client usage example
    def example_custom_client():
        client = CustomPyBridgeClient("3.13.7")
        
        try:
            # Import required modules
            client.import_module("json")
            client.import_module("math")
            
            # Execute complex code
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
            
            print("Execution result:")
            print(result)
            
        finally:
            client.close()
    
    # Run example
    # example_custom_client()
```

### Asynchronous Work with PyServer Example

```python
init python:
    class AsyncPyBridgeManager:
        """Manager for asynchronous work with multiple servers"""
        
        def __init__(self, versions=None):
            self.versions = versions or ["3.13.7"]
            self.servers = {}
            self.setup_servers()
        
        def setup_servers(self):
            """Setup servers for each version"""
            for version in self.versions:
                try:
                    server = pybridge.create_server(version=version)
                    self.servers[version] = server
                    print(f"Server for {version} started on port {server.PORT}")
                except PyBridgeServerException as e:
                    print(f"Failed to start server for {version}: {e}")
        
        def execute_parallel(self, tasks):
            """Parallel task execution on different servers"""
            results = {}
            threads = []
            
            def worker(version, code, task_id):
                try:
                    if version in self.servers:
                        result = self.servers[version].send(code)
                        results[task_id] = result
                    else:
                        results[task_id] = f"ERROR: Server for {version} unavailable"
                except Exception as e:
                    results[task_id] = f"ERROR: {e}"
            
            # Start tasks in separate threads
            for task_id, task in enumerate(tasks):
                thread = threading.Thread(
                    target=worker,
                    args=(task.get('version', '3.13.7'), task['code'], task_id)
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=30)  # 30 second timeout
            
            return results
        
        def close_all(self):
            """Close all servers"""
            for version, server in list(self.servers.items()):
                try:
                    pybridge.close_server(server)
                    print(f"Server for {version} closed")
                except Exception as e:
                    print(f"Error closing server {version}: {e}")
            
            self.servers.clear()
    
    # Manager usage example
    def example_parallel_execution():
        manager = AsyncPyBridgeManager(["3.13.7"])
        
        try:
            tasks = [
                {
                    'version': '3.13.7',
                    'code': "import time; time.sleep(2); result = 'Task 1 completed'"
                },
                {
                    'version': '3.13.7', 
                    'code': "import time; time.sleep(1); result = 'Task 2 completed'"
                },
                {
                    'version': '3.13.7',
                    'code': "result = sum(i*i for i in range(1000))"
                }
            ]
            
            start_time = time.time()
            results = manager.execute_parallel(tasks)
            end_time = time.time()
            
            print(f"Parallel execution took: {end_time - start_time:.2f} seconds")
            
            for task_id, result in results.items():
                print(f"Task {task_id}: {result}")
                
        finally:
            manager.close_all()
    
    # Run example
    # example_parallel_execution()
```

### Custom Server Protocol Implementation Example

```python
init python:
    class CustomProtocolHandler:
        """Custom protocol handler on top of PyServer"""
        
        def __init__(self, server):
            self.server = server
            self.session_data = {}
        
        def send_command(self, command_type, data=None):
            """Send structured command to server"""
            if data is None:
                data = {}
            
            # Create command in JSON format
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
    # Process calculate command
    expression = command['data'].get('expression', '0')
    result = eval(expression)
elif command['type'] == 'store':
    # Process store command
    key = command['data'].get('key')
    value = command['data'].get('value')
    if key and value is not None:
        stored_data = globals().get('_custom_storage', {{}})
        stored_data[key] = value
        globals()['_custom_storage'] = stored_data
        result = f"Stored: {{key}} = {{value}}"
    else:
        result = "ERROR: Invalid parameters"
elif command['type'] == 'retrieve':
    # Process retrieve command
    key = command['data'].get('key')
    stored_data = globals().get('_custom_storage', {{}})
    result = stored_data.get(key, "Not found")
else:
    result = "ERROR: Unknown command"

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
            """Evaluate mathematical expression"""
            return self.send_command("calculate", {"expression": expression})
        
        def store_data(self, key, value):
            """Store data in server session"""
            return self.send_command("store", {"key": key, "value": value})
        
        def retrieve_data(self, key):
            """Retrieve data from server session"""
            return self.send_command("retrieve", {"key": key})
    
    # Custom protocol usage example
    def example_custom_protocol():
        server = pybridge.create_server(version="3.13.7")
        handler = CustomProtocolHandler(server)
        
        try:
            # Evaluate expressions
            result1 = handler.calculate("2 + 2 * 2")
            print(f"2 + 2 * 2 = {result1}")
            
            result2 = handler.calculate("math.sqrt(16)")  # Needs import math
            print(f"math.sqrt(16) = {result2}")
            
            # Data operations
            handler.store_data("player_name", "Alexey")
            handler.store_data("score", 100)
            
            name = handler.retrieve_data("player_name")
            score = handler.retrieve_data("score")
            print(f"Player: {name}, Score: {score}")
            
        finally:
            pybridge.close_server(server)
    
    # Run example
    # example_custom_protocol()
```

### Functionality Testing

```python
init python:
    def run_pybridge_tests():
        """Test suite for PyBridge functionality verification"""
        tests = [
            {
                "name": "Simple calculation",
                "code": "result = 2 + 2",
                "expected": "4"
            },
            {
                "name": "Module import", 
                "code": "import math; result = math.pi",
                "expected": "3.141592653589793"
            },
            {
                "name": "Variable operations",
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
                    timeout=5
                )
                
                if result == test["expected"]:
                    print(f"✓ {test['name']}: SUCCESS")
                else:
                    print(f"✗ {test['name']}: ERROR (expected: {test['expected']}, got: {result})")
                    
            except Exception as e:
                print(f"✗ {test['name']}: EXCEPTION ({e})")
    
    # Run tests on initialization
    # run_pybridge_tests()
```

### Game Mechanics Integration Example

```python
init python:
    class GameIntegrationExample:
        """PyBridge integration example with game mechanics"""
        
        def __init__(self):
            self.procedural_content = {}
            self.dynamic_variables = {}
        
        def generate_procedural_content(self, seed=None):
            """Procedural content generation via Python"""
            code = f"""
import random
{"random.seed(" + str(seed) + ")" if seed else ""}

# Random level generation
level_data = {{
    "rooms": [],
    "enemies": [],
    "items": []
}}

# Room generation
for i in range(random.randint(5, 10)):
    room = {{
        "id": i,
        "size": (random.randint(3, 8), random.randint(3, 8)),
        "connections": [],
        "type": random.choice(["normal", "treasure", "enemy"])
    }}
    level_data["rooms"].append(room)

# Enemy generation
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
                result_json = pybridge.python(code=code, timeout=10)
                # Parse JSON result
                self.procedural_content = json.loads(result_json)
                return self.procedural_content
            except Exception as e:
                print(f"Content generation error: {e}")
                return None
        
        def calculate_dynamic_difficulty(self, player_level, success_rate):
            """Dynamic difficulty calculation via ML-like algorithms"""
            code = f"""
# Simplified adaptive difficulty algorithm
player_level = {player_level}
success_rate = {success_rate}

# Base parameters
base_difficulty = player_level * 0.5

# Adjustment based on success rate
if success_rate > 0.8:
    # Player successful - increase difficulty
    adjustment = 1.2
elif success_rate < 0.4:
    # Player struggles - decrease difficulty
    adjustment = 0.8
else:
    adjustment = 1.0

final_difficulty = base_difficulty * adjustment

# Range limitation
final_difficulty = max(1, min(final_difficulty, 10))

result = {{
    "difficulty": round(final_difficulty, 1),
    "enemy_health_multiplier": final_difficulty * 0.8,
    "enemy_damage_multiplier": final_difficulty * 0.6,
    "reward_multiplier": final_difficulty * 0.3
}}
"""
            
            try:
                result_json = pybridge.python(code=code, timeout=5)
                return json.loads(result_json)
            except Exception as e:
                print(f"Difficulty calculation error: {e}")
                return {"difficulty": 1.0, "enemy_health_multiplier": 1.0, 
                       "enemy_damage_multiplier": 1.0, "reward_multiplier": 1.0}
    
    # Game usage
    game_integration = GameIntegrationExample()
    
    # Level generation on game start
    # generated_level = game_integration.generate_procedural_content(seed=12345)
    
    # Real-time difficulty calculation
    # difficulty_settings = game_integration.calculate_dynamic_difficulty(
    #     player_level=5, 
    #     success_rate=0.65
    # )
```

These examples demonstrate how to use `PyServer` to create custom functionality, extending PyBridge's basic capabilities for your mod's specific needs.

This documentation covers all major aspects of working with the PyBridge module and should help developers create reliable and efficient modifications for Ren'Py.