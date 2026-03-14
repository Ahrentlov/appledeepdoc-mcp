"""
Sandboxed Python Execution Environment
======================================

Executes user-provided Python code in an isolated subprocess with:
- Resource limits (CPU time, memory)
- Restricted builtins
- Dynamic API calls via IPC (stdin/stdout)
- No file system access
- No network access (beyond API bridge)

Security Model:
- Subprocess isolation is the PRIMARY security boundary
- Static code validation is defense-in-depth
- Resource limits prevent DoS attacks

IPC Protocol:
- Sandbox writes API requests to stdout as JSON: {"__api_call__": {"func": "name", "args": [...]}}
- Parent reads request, executes API, writes response to stdin
- Sandbox reads response and continues execution
"""

import subprocess
import tempfile
import json
import os
import sys
import time
import threading
import queue
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

from .security import CodeValidator, ValidationResult


@dataclass
class ExecutionResult:
    """Result of sandbox code execution."""
    success: bool
    result: Any = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: int = 0
    validation_warnings: list = None
    api_calls_made: int = 0

    def __post_init__(self):
        if self.validation_warnings is None:
            self.validation_warnings = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for MCP response."""
        d = asdict(self)
        # Remove None values for cleaner output
        return {k: v for k, v in d.items() if v is not None and v != [] and v != ""}


class SandboxExecutor:
    """
    Executes Python code in an isolated subprocess with dynamic API access.

    The executor:
    1. Validates code statically (defense-in-depth)
    2. Spawns subprocess with IPC channel
    3. Handles API calls from sandbox via stdin/stdout
    4. Returns results
    """

    # Template for the sandbox script with IPC support
    SANDBOX_TEMPLATE = '''
import json
import sys
import resource

# Set resource limits (Unix only)
try:
    resource.setrlimit(resource.RLIMIT_CPU, ({timeout}, {timeout}))
    memory_bytes = {max_memory_mb} * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
except (ValueError, resource.error):
    pass

# Restricted builtins
ALLOWED_BUILTINS = {{
    'len': len, 'range': range, 'enumerate': enumerate, 'zip': zip,
    'map': map, 'filter': filter, 'reversed': reversed,
    'min': min, 'max': max, 'sum': sum, 'any': any, 'all': all, 'sorted': sorted,
    'abs': abs, 'round': round, 'pow': pow, 'divmod': divmod,
    'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
    'str': str, 'int': int, 'float': float, 'bool': bool, 'bytes': bytes,
    'isinstance': isinstance, 'type': type,
    'print': print, 'repr': repr,
    'True': True, 'False': False, 'None': None,
}}

# IPC functions - these call back to the parent process
def _make_api_call(func_name, *args):
    """Make an API call to parent process via IPC."""
    request = {{"__api_call__": {{"func": func_name, "args": list(args)}}}}
    # Write request to stdout (parent reads this)
    sys.stdout.write(json.dumps(request) + "\\n")
    sys.stdout.flush()
    # Read response from stdin (parent writes this)
    response_line = sys.stdin.readline()
    if not response_line:
        raise RuntimeError(f"No response from API for {{func_name}}")
    response = json.loads(response_line)
    if "error" in response:
        raise RuntimeError(f"API error: {{response['error']}}")
    return response.get("result")

def fetch_documentation(url):
    """Fetch Apple Developer documentation."""
    return _make_api_call("fetch_documentation", url)

def search_proposals(feature):
    """Search Swift Evolution proposals."""
    return _make_api_call("search_proposals", feature)

def get_proposal(se_number):
    """Get details of a specific Swift Evolution proposal."""
    return _make_api_call("get_proposal", se_number)

def search_docs(query, case_sensitive=False):
    """Search Xcode hidden documentation."""
    return _make_api_call("search_docs", query, case_sensitive)

def get_document(name, xcode_version=None):
    """Get full content of a documentation file."""
    return _make_api_call("get_document", name, xcode_version)

def list_documents(filter=None):
    """List all available Xcode documentation files."""
    return _make_api_call("list_documents", filter)

def get_xcode_versions():
    """Get list of installed Xcode versions."""
    return _make_api_call("get_xcode_versions")

def search_apple_online(query, platform=None):
    """Search Apple's online documentation."""
    return _make_api_call("search_apple_online", query, platform)

def get_framework_info(framework):
    """Get documentation URL for a framework."""
    return _make_api_call("get_framework_info", framework)

def search_swift_repos(query):
    """Search across all Swift repositories."""
    return _make_api_call("search_swift_repos", query)

def fetch_github_file(url):
    """Fetch source code from GitHub."""
    return _make_api_call("fetch_github_file", url)

def search_wwdc_notes(query):
    """Search WWDC session notes."""
    return _make_api_call("search_wwdc_notes", query)

def get_wwdc_session(session_id):
    """Get WWDC session URLs."""
    return _make_api_call("get_wwdc_session", session_id)

def search_hig(query, platform=None):
    """Search Human Interface Guidelines."""
    return _make_api_call("search_hig", query, platform)

def list_hig_platforms():
    """List all HIG platforms."""
    return _make_api_call("list_hig_platforms")

# Create namespace with allowed builtins and API functions
namespace = {{'__builtins__': ALLOWED_BUILTINS}}
namespace['fetch_documentation'] = fetch_documentation
namespace['search_proposals'] = search_proposals
namespace['get_proposal'] = get_proposal
namespace['search_docs'] = search_docs
namespace['get_document'] = get_document
namespace['list_documents'] = list_documents
namespace['get_xcode_versions'] = get_xcode_versions
namespace['search_apple_online'] = search_apple_online
namespace['get_framework_info'] = get_framework_info
namespace['search_swift_repos'] = search_swift_repos
namespace['fetch_github_file'] = fetch_github_file
namespace['search_wwdc_notes'] = search_wwdc_notes
namespace['get_wwdc_session'] = get_wwdc_session
namespace['search_hig'] = search_hig
namespace['list_hig_platforms'] = list_hig_platforms

# User code execution
user_output = []
original_print = print

def capturing_print(*args, **kwargs):
    """Capture print output."""
    import io
    output = io.StringIO()
    kwargs['file'] = output
    original_print(*args, **kwargs)
    user_output.append(output.getvalue())

namespace['print'] = capturing_print

try:
    exec("""{user_code}""", namespace)

    if 'result' in namespace:
        result = namespace['result']
        output = {{"success": True, "result": result, "stdout": "".join(user_output)}}
    else:
        output = {{"success": True, "result": None, "stdout": "".join(user_output), "warning": "No 'result' variable set"}}

except Exception as e:
    output = {{
        "success": False,
        "error": str(e),
        "error_type": type(e).__name__,
        "stdout": "".join(user_output)
    }}

# Final output marker
sys.stdout.write("__SANDBOX_COMPLETE__\\n")
sys.stdout.write(json.dumps(output, default=str) + "\\n")
sys.stdout.flush()
'''

    def __init__(
        self,
        timeout: int = 5,
        max_memory_mb: int = 50,
        max_output_bytes: int = 10 * 1024,
        python_path: Optional[str] = None,
        api_handlers: Optional[Dict[str, Callable]] = None
    ):
        """
        Initialize the sandbox executor.

        Args:
            timeout: Maximum execution time in seconds
            max_memory_mb: Maximum memory usage in MB
            max_output_bytes: Maximum output size in bytes
            python_path: Path to Python interpreter
            api_handlers: Dict mapping function names to handler callables
        """
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.max_output_bytes = max_output_bytes
        self.python_path = python_path or sys.executable
        self.validator = CodeValidator()
        self.api_handlers = api_handlers or {}

    def execute(self, code: str, api_handlers: Optional[Dict[str, Callable]] = None, skip_validation: bool = False) -> ExecutionResult:
        """
        Execute code in the sandbox with dynamic API access.

        Args:
            code: Python code to execute
            api_handlers: Dict mapping function names to handler callables
            skip_validation: If True, skip code validation

        Returns:
            ExecutionResult with success status, result, and any errors
        """
        start_time = time.time()
        validation_warnings = []
        handlers = api_handlers or self.api_handlers

        # Step 1: Validate code (unless pre-validated)
        if not skip_validation:
            validation = self.validator.validate(code)
            if not validation.is_safe:
                return ExecutionResult(
                    success=False,
                    error="; ".join(validation.errors),
                    error_type="ValidationError",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            validation_warnings = validation.warnings

        # Step 2: Create sandbox script
        try:
            script = self._create_sandbox_script(code)
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Failed to prepare sandbox: {str(e)}",
                error_type="PreparationError",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        # Step 3: Execute with IPC
        try:
            result = self._run_with_ipc(script, handlers)
            result.validation_warnings = validation_warnings
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"Execution timed out after {self.timeout} seconds",
                error_type="TimeoutError",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution failed: {str(e)}",
                error_type="ExecutionError",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def _create_sandbox_script(self, code: str) -> str:
        """Create the sandbox script."""
        # Escape user code for embedding
        escaped_code = code.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')

        return self.SANDBOX_TEMPLATE.format(
            timeout=self.timeout,
            max_memory_mb=self.max_memory_mb,
            user_code=escaped_code
        )

    def _handle_api_call(self, data: Dict, handlers: Dict[str, Callable]) -> Dict:
        """Execute an API call from the sandbox and return the IPC response."""
        call_info = data["__api_call__"]
        func_name = call_info["func"]
        args = call_info["args"]

        if func_name not in handlers:
            return {"error": f"Unknown API function: {func_name}"}

        try:
            return {"result": handlers[func_name](*args)}
        except Exception as e:
            return {"error": str(e)}

    def _run_with_ipc(self, script: str, handlers: Dict[str, Callable]) -> ExecutionResult:
        """
        Run sandbox with IPC for API calls.

        Args:
            script: Sandbox script to execute
            handlers: API handlers

        Returns:
            ExecutionResult
        """
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name

        api_calls_made = 0
        collected_output = []

        try:
            env = {
                'PATH': os.environ.get('PATH', ''),
                'PYTHONPATH': '',
                'HOME': os.environ.get('HOME', ''),
            }

            # Start subprocess with pipes for IPC
            proc = subprocess.Popen(
                [self.python_path, script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )

            # Process IPC until completion or timeout
            deadline = time.time() + self.timeout
            result_line = None

            while True:
                if time.time() > deadline:
                    proc.kill()
                    raise subprocess.TimeoutExpired(cmd=script_path, timeout=self.timeout)

                line = proc.stdout.readline()
                if not line:
                    break

                line = line.strip()

                if line == "__SANDBOX_COMPLETE__":
                    result_line = proc.stdout.readline()
                    break

                # Try to parse as API call
                api_call = None
                try:
                    data = json.loads(line)
                    if "__api_call__" in data:
                        api_call = data
                except json.JSONDecodeError:
                    pass

                if api_call:
                    api_calls_made += 1
                    response = self._handle_api_call(api_call, handlers)
                    proc.stdin.write(json.dumps(response) + "\n")
                    proc.stdin.flush()
                else:
                    collected_output.append(line)

            # Wait for process to finish
            proc.wait(timeout=1)
            stderr = proc.stderr.read()

            # Parse final result
            if result_line is None:
                return ExecutionResult(
                    success=False,
                    stdout="\n".join(collected_output),
                    stderr=stderr,
                    error="Sandbox process exited without completing (possible resource limit or crash)",
                    error_type="ProcessError",
                    api_calls_made=api_calls_made
                )

            try:
                output = json.loads(result_line)
                return ExecutionResult(
                    success=output.get("success", False),
                    result=output.get("result"),
                    stdout=output.get("stdout", ""),
                    stderr=stderr,
                    error=output.get("error"),
                    error_type=output.get("error_type"),
                    api_calls_made=api_calls_made
                )
            except json.JSONDecodeError:
                return ExecutionResult(
                    success=False,
                    stdout="\n".join(collected_output),
                    stderr=stderr,
                    error="Failed to parse sandbox output",
                    error_type="ParseError",
                    api_calls_made=api_calls_made
                )

        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass
