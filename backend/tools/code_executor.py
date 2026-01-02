"""
Code execution tool with sandbox isolation.
Provides CodeTool class for safe Python code execution.
"""
import subprocess
import sys
import tempfile
import os
from typing import Dict, Any


class CodeTool:
    """
    Safe Python code executor using subprocess isolation.
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def execute(self, code: str) -> Dict[str, Any]:
        """
        Execute Python code in isolated subprocess.
        
        Args:
            code: Python code to execute
            
        Returns:
            Dict with keys: success, output, error
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Execute in subprocess
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=tempfile.gettempdir(),
                env={**os.environ, "PYTHONPATH": ""}
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout.strip() if result.stdout else None,
                    "error": result.stderr.strip() if result.stderr else "Unknown error"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": None,
                "error": f"Code execution timed out after {self.timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }
        finally:
            # Cleanup
            try:
                os.unlink(temp_path)
            except:
                pass


# Legacy function for backwards compatibility
def execute_python_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code (legacy wrapper)."""
    tool = CodeTool(timeout=timeout)
    return tool.execute(code)


async def execute_with_correction(
    code: str,
    correction_fn,
    max_corrections: int = 2,
    timeout: int = 30
) -> tuple:
    """
    Execute code with automatic correction on error.
    
    Args:
        code: Initial Python code
        correction_fn: Async function(code, error) -> corrected_code
        max_corrections: Maximum correction attempts
        timeout: Execution timeout
        
    Returns:
        Tuple of (success: bool, result: str, attempts: int)
    """
    tool = CodeTool(timeout=timeout)
    current_code = code
    attempts = 0
    
    while attempts <= max_corrections:
        result = tool.execute(current_code)
        
        if result["success"]:
            return True, result["output"], attempts
        
        if attempts >= max_corrections:
            break
            
        # Try to correct the code
        try:
            current_code = await correction_fn(current_code, result["error"])
            attempts += 1
        except Exception as e:
            return False, f"Correction failed: {str(e)}", attempts
    
    return False, result.get("error", "Max corrections reached"), attempts
