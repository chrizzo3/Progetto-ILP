import unittest
import sys
import os
# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from lark import Lark
from lark.exceptions import UnexpectedToken, UnexpectedCharacters

class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load grammar from file
        grammar_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'play_lang', 'frontend', 'grammar.lark')
        with open(grammar_path, 'r') as f:
            grammar_src = f.read()
        cls.parser = Lark(grammar_src, start='program', parser='lalr')

    def parse(self, code):
        return self.parser.parse(code)

    def test_valid_declarations(self):
        code = """
        rank: x
        rate: y
        flag: f
        label: s
        play {
            x <-- 10
            y <-- 3.14
            f <-- true
            s <-- "test"
        } gameover
        """
        self.parse(code)

    def test_valid_functions(self):
        code = """
        action myFunc(rank a, rate b) -> void {
            reward void
        }
        play {} gameover
        """
        self.parse(code)

    def test_control_flow(self):
        code = """
        play {
            flag: f
            rank: i
            
            choice (f) -> {
            } retry (f) -> {
            } fail -> {
            }
            
            stay (f) -> { }
            
            loop (i <-- 0; i < 10; i <-- i + 1) -> { }
        } gameover
        """
        self.parse(code)

    def test_input_output(self):
        code = """
        rank: x
        play {
            x <-- grab "Prompt"
            drop "Output"
        } gameover
        """
        self.parse(code)

    def test_complex_expressions(self):
        code = """
        rank: x
        play {
            x <-- (1 + 2) * 3 / 4 % 5
            flag: b <-- (1 < 2) && (3 >= 3) || !false
        } gameover
        """
        self.parse(code)

    def test_invalid_keyword(self):
        code = """
        play {
            print "hello" // Invalid keyword, should be drop
        } gameover
        """
        with self.assertRaises(UnexpectedToken):
            self.parse(code)

    def test_missing_brace(self):
        code = """
        play {
            rank: x
        gameover // Missing closing brace
        """
        with self.assertRaises(UnexpectedToken):
            self.parse(code)

    def test_missing_semicolon_in_loop(self):
        code = """
        rank: i
        play {
            loop (i <-- 0 i < 10; i <-- i + 1) -> { } // Missing first semicolon in for loop
        } gameover
        """
        with self.assertRaises(UnexpectedToken):
            self.parse(code)
            
    def test_lexical_error(self):
        code = """
        play {
            rank: x <-- $ // $ is valid? No, usually not in grammar
        } gameover
        """
        with self.assertRaises(UnexpectedCharacters):
            self.parse(code)

if __name__ == '__main__':
    unittest.main()
