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

if __name__ == '__main__':
    unittest.main()
