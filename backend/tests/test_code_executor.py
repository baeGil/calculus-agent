"""
Test cases for Code Executor tool.
Tests sandbox execution, SymPy integration, and correction loop.
"""
import pytest
from backend.tools.code_executor import execute_python_code


class TestCodeExecutor:
    """Test suite for code executor sandbox."""

    # ==================== BASIC EXECUTION TESTS ====================
    
    def test_simple_print(self):
        """TC-CE-001: Test basic print statement."""
        success, result = execute_python_code('print("Hello World")')
        assert success is True
        assert "Hello World" in result

    def test_arithmetic_calculation(self):
        """TC-CE-002: Test basic arithmetic."""
        success, result = execute_python_code('print(2 + 3 * 4)')
        assert success is True
        assert "14" in result

    def test_variable_assignment(self):
        """TC-CE-003: Test variable assignment and output."""
        code = """
x = 10
y = 20
print(x + y)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "30" in result

    # ==================== SYMPY ALGEBRA TESTS ====================

    def test_solve_quadratic(self):
        """TC-CE-004: Solve quadratic equation x² - 5x + 6 = 0."""
        code = 'x = symbols("x"); print(solve(x**2 - 5*x + 6, x))'
        success, result = execute_python_code(code)
        assert success is True
        assert "2" in result and "3" in result

    def test_solve_linear_system(self):
        """TC-CE-005: Solve system of linear equations."""
        code = """
x, y = symbols('x y')
eqs = [x + y - 5, x - y - 1]
solution = solve(eqs, [x, y])
print(solution)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "3" in result  # x = 3
        assert "2" in result  # y = 2

    def test_matrix_operations(self):
        """TC-CE-006: Test matrix operations."""
        code = """
A = Matrix([[1, 2], [3, 4]])
print("Determinant:", A.det())
print("Inverse exists:", A.inv() is not None)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "-2" in result  # det = 1*4 - 2*3 = -2

    def test_differentiation(self):
        """TC-CE-007: Test calculus - differentiation."""
        code = """
x = symbols('x')
f = x**3 + 2*x**2 - x + 1
derivative = diff(f, x)
print(derivative)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "3*x**2" in result or "3x²" in result.replace(" ", "")

    def test_integration(self):
        """TC-CE-008: Test calculus - integration."""
        code = """
x = symbols('x')
f = 2*x + 1
integral = integrate(f, x)
print(integral)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "x**2" in result or "x²" in result

    def test_simplify_expression(self):
        """TC-CE-009: Test expression simplification."""
        code = """
x = symbols('x')
expr = (x**2 - 1)/(x - 1)
simplified = simplify(expr)
print(simplified)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "x + 1" in result

    def test_factor_polynomial(self):
        """TC-CE-010: Test polynomial factorization."""
        code = """
x = symbols('x')
poly = x**2 - 4
factored = factor(poly)
print(factored)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "(x - 2)" in result and "(x + 2)" in result

    # ==================== IMPORT STRIPPING TESTS ====================

    def test_import_stripping(self):
        """TC-CE-011: Import statements should be stripped (pre-loaded)."""
        code = """
from sympy import symbols, solve
x = symbols('x')
print(solve(x - 5, x))
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "5" in result

    # ==================== ERROR HANDLING TESTS ====================

    def test_syntax_error(self):
        """TC-CE-012: Test syntax error handling."""
        success, result = execute_python_code('print("unclosed string')
        assert success is False
        assert "error" in result.lower() or "Error" in result

    def test_runtime_error(self):
        """TC-CE-013: Test runtime error handling."""
        success, result = execute_python_code('print(1/0)')
        assert success is False
        assert "ZeroDivision" in result or "error" in result.lower()

    def test_undefined_variable(self):
        """TC-CE-014: Test undefined variable error."""
        success, result = execute_python_code('print(undefined_var)')
        assert success is False
        assert "error" in result.lower()

    # ==================== SECURITY TESTS ====================

    def test_no_file_access(self):
        """TC-CE-015: File operations should be blocked."""
        success, result = execute_python_code('open("/etc/passwd")')
        assert success is False

    def test_no_os_module(self):
        """TC-CE-016: OS module should not be available for system commands."""
        # os.system is not available in sandbox (os not in safe_globals)
        success, result = execute_python_code('os.system("ls")')
        assert success is False
        assert "error" in result.lower() or "os" in result.lower()

    # ==================== LATEX OUTPUT TESTS ====================

    def test_latex_output(self):
        """TC-CE-017: Test LaTeX output generation."""
        code = """
x = symbols('x')
expr = x**2 + 2*x + 1
print(latex(expr))
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "x^{2}" in result or "x**2" in result


class TestCodeExecutorAdvanced:
    """Advanced algebra test cases."""

    def test_group_theory_cyclic(self):
        """TC-CE-018: Test group operations (mod arithmetic)."""
        code = """
# Check if Z_5 under addition is cyclic
# Generator test: 1 generates all elements
elements = [(1 * i) % 5 for i in range(5)]
print("Generated elements:", set(elements))
print("Is cyclic:", len(set(elements)) == 5)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "Is cyclic: True" in result

    def test_eigenvalues(self):
        """TC-CE-019: Test eigenvalue computation."""
        code = """
A = Matrix([[4, 1], [2, 3]])
eigenvals = A.eigenvals()
print("Eigenvalues:", eigenvals)
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "5" in result or "2" in result

    def test_gcd_lcm(self):
        """TC-CE-020: Test GCD and LCM functions."""
        code = """
print("GCD(12, 18):", gcd(12, 18))
print("LCM(4, 6):", lcm(4, 6))
"""
        success, result = execute_python_code(code)
        assert success is True
        assert "6" in result  # GCD = 6
        assert "12" in result  # LCM = 12
