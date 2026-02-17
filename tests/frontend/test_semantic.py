import unittest
import sys
import os

# Add parent directory to path
# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from lark import Lark
from play_lang.frontend.transformer import PlayTransformer
from play_lang.frontend.semantic_analysis import SemanticAnalyzer, SemanticError


class TestSemanticAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        grammar_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'play_lang', 'frontend', 'grammar.lark')
        with open(grammar_path, 'r') as f:
            grammar_src = f.read()
        cls.parser = Lark(grammar_src, start='program', parser='lalr')
        cls.transformer = PlayTransformer()


    def analyze(self, code):
        tree = self.parser.parse(code)
        ast = self.transformer.transform(tree)
        analyzer = SemanticAnalyzer()
        analyzer.visit(ast)

    
    def test_invalid_chain(self):
        code = """
        play {
            rank: a = b // Invalid because no value assigned
        } gameover
        """
        # Expecting Exception from transformer (Invalid chain)
        with self.assertRaisesRegex(Exception, "Invalid chain"):
            self.analyze(code)

    def test_invalid_output_operator(self):
        code = """
        rank: x
        play {
            x <-- -->x // Invalid use of --> outside drop
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Operator '-->' can only be used in 'drop'"):
            self.analyze(code)

    def test_basic_declarations(self):
        code = """
        rank: x, y
        rate: z
        flag: f
        label: s
        play {
            x <-- 10
            z <-- 3.14
            f <-- true
            s <-- "hello"
        } gameover
        """
        self.analyze(code) # Should pass

    def test_var_not_declared(self):
        code = """
        play {
            x <-- 10
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Variable 'x' not declared"):
            self.analyze(code)

    def test_type_mismatch_assign(self):
        code = """
        rank: x
        play {
            x <-- "hello"
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Type mismatch"):
            self.analyze(code)

    def test_arithmetic_ops(self):
        code = """
        rank: x
        rate: y
        play {
            x <-- 1 + 2
            y <-- 1.5 + 2.5
            y <-- x + 1.0 // Promotion
        } gameover
        """
        self.analyze(code)

    def test_arithmetic_wrong_types(self):
        code = """
        rank: x
        play {
            x <-- 1 - "no"
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, r"Operator - requires numeric"):
            self.analyze(code)

    def test_concatenation(self):
        code = """
        label: s
        play {
            s <-- "Hello" + " World"
        } gameover
        """
        self.analyze(code)

    def test_logic_and_comparison(self):
        code = """
        flag: f
        rank: x
        play {
            x <-- 10
            f <-- (x > 5) && (x < 20)
            f <-- x == 10
        } gameover
        """
        self.analyze(code)

    def test_if_condition_flag(self):
        code = """
        rank: x
        play {
            x <-- 10
            choice (x) -> { } // Error: x is rank, needs flag
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "If condition must be 'flag'"):
            self.analyze(code)

    def test_loops(self):
        code = """
        flag: done
        rank: i
        play {
            stay (done) -> { }
            loop (i <-- 0; i < 10; i <-- i + 1) -> { }
        } gameover
        """
        self.analyze(code)

    def test_break_outside_loop(self):
        code = """
        play {
            quit
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Quit used outside loop"):
            self.analyze(code)

    def test_functions(self):
        code = """
        rank: res
        action sum(rank a, rank b) -> rank {
            reward a + b
        }
        play {
            res <-- sum(1, 2)
        } gameover
        """
        self.analyze(code)

    def test_function_scope(self):
        code = """
        action test() -> void {
            rank: local_var
            local_var <-- 1
        }
        play {
            local_var <-- 2 // Error: not visible here
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Variable 'local_var' not declared"):
            self.analyze(code)

    def test_function_arg_mismatch(self):
        code = """
        action foo(rank a) -> void {}
        play {
            foo("wrong")
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "type mismatch"):
            self.analyze(code)

    def test_return_checking(self):
        code = """
        action foo() -> rank {
            reward "string"
        }
        play {} gameover
        """
        with self.assertRaisesRegex(SemanticError, "Invalid return type"):
            self.analyze(code)

    def test_return_outside_func(self):
        code = """
        play {
            reward 1
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Return statement outside function"):
            self.analyze(code)

    def test_input_output(self):
        code = """
        rank: x
        label: msg
        play {
            msg, x <-- grab "Enter number > "
            drop "Done"
        } gameover
        """
        self.analyze(code)

    def test_input_invalid_prompt(self):
        code = """
        rank: x
        play {
            x <-- grab 123
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Input prompt must be 'label'"):
            self.analyze(code)

    # --- Scope Tests ---
    
    def test_global_variable_accessible_from_play(self):
        """Test that global variables are accessible from play{} block"""
        code = """
        rank: global_x <-- 100
        play {
            drop -->global_x
        } gameover
        """
        self.analyze(code)  # Should pass without error
    
    def test_global_variable_accessible_from_function(self):
        """Test that global variables are accessible from functions"""
        code = """
        rank: global_x <-- 100
        action test() -> rank {
            reward global_x
        }
        play {
            rank: result <-- test()
        } gameover
        """
        self.analyze(code)  # Should pass without error
    
    def test_local_play_variable_not_accessible_from_function(self):
        """Test that variables declared in play{} are NOT accessible from functions"""
        code = """
        action test() -> rank {
            reward local_main
        }
        play {
            rank: local_main <-- 10
            rank: x <-- test()
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Variable 'local_main' not declared"):
            self.analyze(code)
    
    def test_local_function_variable_not_accessible_from_play(self):
        """Test that variables declared in functions are NOT accessible from play{}"""
        code = """
        action test() -> void {
            rank: local_func <-- 42
            reward void
        }
        play {
            test()
            drop -->local_func
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Variable 'local_func' not declared"):
            self.analyze(code)
    
    def test_shadowing_global_in_play(self):
        """Test that local variables in play{} can shadow global variables"""
        code = """
        rank: x <-- 100
        play {
            rank: x <-- 50
            drop -->x
        } gameover
        """
        self.analyze(code)  # Should pass - shadowing is allowed
    
    def test_shadowing_global_in_function(self):
        """Test that local variables in functions can shadow global variables"""
        code = """
        rank: score <-- 100
        action reset() -> rank {
            rank: score <-- 0
            reward score
        }
        play {
            rank: result <-- reset()
            drop -->result
        } gameover
        """
        self.analyze(code)  # Should pass - shadowing is allowed
    
    def test_isolation_between_function_scopes(self):
        """Test that different functions have isolated scopes"""
        code = """
        action func1() -> rank {
            rank: x <-- 10
            reward x
        }
        action func2() -> rank {
            rank: x <-- 20
            reward x
        }
        play {
            rank: a <-- func1()
            rank: b <-- func2()
        } gameover
        """
        self.analyze(code)  # Should pass - each function has its own scope
    
    def test_function_parameter_local_scope(self):
        """Test that function parameters are local to the function"""
        code = """
        action test(rank param) -> rank {
            reward param
        }
        play {
            rank: x <-- test(10)
            drop -->param
        } gameover
        """
        with self.assertRaisesRegex(SemanticError, "Variable 'param' not declared"):
            self.analyze(code)
    
    def test_nested_scope_access(self):
        """Test that inner scopes can access outer scopes"""
        code = """
        rank: global_var <-- 100
        action test() -> rank {
            rank: local_var <-- 50
            reward global_var + local_var
        }
        play {
            rank: result <-- test()
            drop -->global_var
        } gameover
        """
        self.analyze(code)  # Should pass

if __name__ == '__main__':
    unittest.main()
