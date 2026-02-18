#!/usr/bin/env python3
"""
Test Runner per il Compilatore Play
Esegue tutti i test nelle subdirectory e genera report.
"""

import os
import sys
import subprocess
import json
import unittest
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

# Colori ANSI per output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

@dataclass
class TestResult:
    """Risultato di un singolo test."""
    name: str
    category: str
    passed: bool
    message: str = ""
    
class TestRunner:
    """Runner principale per i test."""
    
    def __init__(self, tests_dir: Path):
        self.tests_dir = tests_dir
        self.project_root = tests_dir.parent
        self.results: List[TestResult] = []
        
    def run_all_tests(self):
        """Esegue tutti i test."""
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}  Play Compiler Test Suite{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        # Frontend unit tests
        self.run_frontend_tests()

        # Categorie di test basati su file .play
        categories = ['codegen', 'optimization', 'integration']
        
        for category in categories:
            category_dir = self.tests_dir / category
            if category_dir.exists():
                self.run_category_tests(category, category_dir)
        
        self.print_summary()
        
    def run_frontend_tests(self):
        """Esegue i test unittest nella cartella tests/frontend/."""
        frontend_dir = self.tests_dir / 'frontend'
        if not frontend_dir.exists():
            return

        print(f"\n{Colors.BOLD}{Colors.CYAN}[FRONTEND]{Colors.RESET}")
        print(f"{'-'*60}")

        src_path = str(self.project_root / 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        loader = unittest.TestLoader()
        suite = loader.discover(str(frontend_dir), pattern='test_*.py')

        # Raccoglie tutte le classi di test per eseguirle per classe
        # (necessario affinché setUpClass venga chiamato correttamente)
        test_classes = {}
        for group in suite:
            for subgroup in group:
                tests = list(subgroup) if isinstance(subgroup, unittest.TestSuite) else [subgroup]
                for test in tests:
                    cls = type(test)
                    test_classes.setdefault(cls, []).append(test)

        for cls, tests in test_classes.items():
            class_suite = unittest.TestSuite(tests)

            class _PerTestResult(unittest.TestResult):
                def __init__(self_inner):
                    super().__init__()
                    self_inner.per_test = {}

                def addSuccess(self_inner, test):
                    self_inner.per_test[test] = ('pass', '')

                def addFailure(self_inner, test, err):
                    msg = self_inner._exc_info_to_string(err, test).strip().splitlines()[-1]
                    self_inner.per_test[test] = ('fail', msg)

                def addError(self_inner, test, err):
                    msg = self_inner._exc_info_to_string(err, test).strip().splitlines()[-1]
                    self_inner.per_test[test] = ('error', msg)

            buf = _PerTestResult()
            class_suite.run(buf)

            for test in tests:
                display_name = f"{cls.__name__}.{test._testMethodName}"
                status, msg = buf.per_test.get(test, ('pass', ''))
                passed = (status == 'pass')
                label = 'OK' if passed else f"{'ERROR' if status == 'error' else 'FAIL'}: {msg}"
                result = TestResult(display_name, 'frontend', passed, label)
                self.results.append(result)
                self.print_result(result)

    def run_category_tests(self, category: str, category_dir: Path):
        """Esegue tutti i test in una categoria."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}[{category.upper()}]{Colors.RESET}")
        print(f"{'-'*60}")
        
        # Trova tutti i file .play
        test_files = list(category_dir.glob('**/*.play'))
        
        if not test_files:
            print(f"{Colors.YELLOW}  No tests found{Colors.RESET}")
            return
        
        for test_file in sorted(test_files):
            self.run_single_test(category, test_file)
    
    def run_single_test(self, category: str, test_file: Path):
        """Esegue un singolo test."""
        test_name = test_file.stem
        
        # Determina tipo di test dal nome o metadata
        if '_error' in test_name or test_file.parent.name == 'invalid':
            # Test che deve fallire
            result = self.run_error_test(test_file)
        elif '_output' in test_name or (test_file.parent / f"{test_name}.expected").exists():
            # Test con output atteso
            result = self.run_output_test(test_file)
        else:
            # Test che deve solo compilare
            result = self.run_compile_test(test_file)
        
        result.category = category
        self.results.append(result)
        self.print_result(result)
    
    def run_compile_test(self, test_file: Path) -> TestResult:
        """Test che deve compilare senza errori."""
        try:
            result = subprocess.run(
                ['python', 'run_compiler.py', str(test_file.resolve())],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return TestResult(test_file.stem, "", True, "Compiled successfully")
            else:
                return TestResult(test_file.stem, "", False, f"Compilation failed: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            return TestResult(test_file.stem, "", False, "Timeout")
        except Exception as e:
            return TestResult(test_file.stem, "", False, f"Error: {str(e)}")
    
    def run_error_test(self, test_file: Path) -> TestResult:
        """Test che deve fallire con errore."""
        try:
            result = subprocess.run(
                ['python', 'run_compiler.py', str(test_file.resolve())],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return TestResult(test_file.stem, "", True, "Failed as expected")
            else:
                return TestResult(test_file.stem, "", False, "Should have failed but compiled")
        except subprocess.TimeoutExpired:
            return TestResult(test_file.stem, "", False, "Timeout")
        except Exception as e:
            return TestResult(test_file.stem, "", False, f"Error: {str(e)}")
    
    def run_output_test(self, test_file: Path) -> TestResult:
        """Test con verifica output."""
        expected_file = test_file.parent / f"{test_file.stem}.expected"
        
        try:
            # Compila
            compile_result = subprocess.run(
                ['python', 'run_compiler.py', str(test_file.resolve())],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if compile_result.returncode != 0:
                return TestResult(test_file.stem, "", False, "Compilation failed")
            
            # Esegui il programma generato da run_compiler.py
            exe_name = 'program.exe' if os.name == 'nt' else 'program'
            exe_path = self.project_root / exe_name

            if not exe_path.exists():
                 return TestResult(test_file.stem, "", False, f"Executable '{exe_name}' not found")

            run_result = subprocess.run(
                [str(exe_path)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            actual_output = run_result.stdout.strip()
            
            # Confronta con expected
            if expected_file.exists():
                expected_output = expected_file.read_text(encoding='utf-8').strip()
                if actual_output == expected_output:
                    # Cleanup executable if test passes
                    try:
                        if exe_path.exists():
                            os.remove(exe_path)
                        if (self.project_root / "output.ll").exists():
                             os.remove(self.project_root / "output.ll")
                    except:
                        pass
                    return TestResult(test_file.stem, "", True, "Output matches")
                else:
                    return TestResult(test_file.stem, "", False, f"Output mismatch\nExpected:\n{expected_output}\nGot:\n{actual_output}")
            else:
                # Nessun file expected, solo verifica che runni
                try:
                    if exe_path.exists():
                        os.remove(exe_path)
                except:
                    pass
                return TestResult(test_file.stem, "", True, "Executed successfully")
                
        except subprocess.TimeoutExpired:
            return TestResult(test_file.stem, "", False, "Timeout")
        except Exception as e:
            return TestResult(test_file.stem, "", False, f"Error: {str(e)}")
    
    def print_result(self, result: TestResult):
        """Stampa risultato di un test."""
        status = f"{Colors.GREEN}+ PASS{Colors.RESET}" if result.passed else f"{Colors.RED}- FAIL{Colors.RESET}"
        print(f"  {status}  {result.name:40s} {Colors.YELLOW}{result.message}{Colors.RESET}")
    
    def print_summary(self):
        """Stampa statistiche finali."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}  Test Summary{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        # Per categoria
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {'passed': 0, 'failed': 0}
            if result.passed:
                categories[result.category]['passed'] += 1
            else:
                categories[result.category]['failed'] += 1
        
        for category, stats in sorted(categories.items()):
            total_cat = stats['passed'] + stats['failed']
            percentage = (stats['passed'] / total_cat * 100) if total_cat > 0 else 0
            print(f"  {category:15s}: {stats['passed']:3d}/{total_cat:3d} ({percentage:5.1f}%)")
        
        print()
        percentage = (passed / total * 100) if total > 0 else 0
        
        if percentage == 100:
            color = Colors.GREEN
        elif percentage >= 80:
            color = Colors.YELLOW
        else:
            color = Colors.RED
        
        print(f"  {Colors.BOLD}Total: {color}{passed}/{total} ({percentage:.1f}%){Colors.RESET}")
        
        if failed > 0:
            print(f"\n{Colors.RED}  Failed tests:{Colors.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"    - {result.category}/{result.name}: {result.message}")
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        # Exit code
        return 0 if failed == 0 else 1

def main():
    """Entry point."""
    tests_dir = Path(__file__).parent
    runner = TestRunner(tests_dir)
    if len(sys.argv) > 1:
        # Esegui test specifico
        test_path = Path(sys.argv[1])
        if not test_path.exists():
            print(f"{Colors.RED}File non trovato: {test_path}{Colors.RESET}")
            sys.exit(1)
            
        # Se è una directory, esegui tutti i test dentro
        if test_path.is_dir():
            print(f"{Colors.BOLD}{Colors.BLUE}Esecuzione test in: {test_path}{Colors.RESET}")
            # Se è la root dei test, usa run_all_tests
            if test_path.resolve() == tests_dir.resolve():
                exit_code = runner.run_all_tests()
            else:
                category = test_path.name
                runner.run_category_tests(category, test_path)
                runner.print_summary()
                exit_code = 0 if all(r.passed for r in runner.results) else 1
            sys.exit(exit_code)
            
        # Se è un file, esegui singolo test
        print(f"{Colors.BOLD}{Colors.BLUE}Esecuzione singolo test: {test_path.name}{Colors.RESET}")
        
        # Determina categoria dalla directory padre
        category = test_path.parent.name
        runner.run_single_test(category, test_path)
        
        # Stampa risultato
        result = runner.results[0]
        # runner.print_result(result) # Già stampato da run_single_test
        
        sys.exit(0 if result.passed else 1)
    else:
        # Esegui tutti i test
        exit_code = runner.run_all_tests()
        sys.exit(exit_code)

if __name__ == '__main__':
    main()
