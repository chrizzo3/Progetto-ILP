import unittest
import sys
import os

# Add parent directory to path
# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from lark import Lark
from play_lang.frontend.transformer import PlayTransformer
from play_lang.frontend.ast_node import *

class TestTransformer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        grammar_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'play_lang', 'frontend', 'grammar.lark')
        with open(grammar_path, 'r') as f:
            grammar_src = f.read()
        cls.parser = Lark(grammar_src, start='program', parser='lalr')
        cls.transformer = PlayTransformer()

    def transform(self, code):
        tree = self.parser.parse(code)
        return self.transformer.transform(tree)

    def test_program_structure(self):
        code = """
        rank: x
        play { } gameover
        """
        ast = self.transform(code)
        self.assertIsInstance(ast, ProgramNode)
        self.assertEqual(len(ast.global_decls), 1)
        self.assertIsInstance(ast.main_block, BlockNode)

    def test_assignment_chain(self):
        # Testing the specific rule: a, b <-- 10 -> Assign(b, 10), a is just declared (or ignored in this stmt)
        # Actually, in our transformer:
        # "a, b <-- 10" -> AssignNode(b, 10)
        # "a" stays as declaration from var_decl if present, but here we test the statement.
        code = """
        play {
            rank: a, b
            a, b <-- 10
        } gameover
        """
        ast = self.transform(code)
        block = ast.main_block
        # Stmts: 0=VarDecl(a,b), 1=AssignNode(b, 10)
        
        assign_node = block.statements[1]
        self.assertIsInstance(assign_node, AssignNode)
        self.assertEqual(assign_node.target, 'b')
        self.assertIsInstance(assign_node.expr, LiteralNode)
        self.assertEqual(assign_node.expr.value, 10)

    def test_binary_ops_precedence(self):
        # 1 + 2 * 3 -> 1 + (2 * 3)
        # Tree should be Sum(1, Prod(2, 3))
        code = """
        rank: x
        play {
            x <-- 1 + 2 * 3
        } gameover
        """
        ast = self.transform(code)
        # rank: x is global (outside play)
        # So main_block only contains the assignment
        assign = ast.main_block.statements[0]
        expr = assign.expr
        
        # Expr is BinOpNode(+)
        self.assertIsInstance(expr, BinOpNode)
        self.assertEqual(expr.op, '+')
        
        # Left is 1
        self.assertIsInstance(expr.left, LiteralNode)
        self.assertEqual(expr.left.value, 1)
        
        # Right is BinOpNode(*)
        self.assertIsInstance(expr.right, BinOpNode)
        self.assertEqual(expr.right.op, '*')
        
    def test_if_structure(self):
        code = """
        flag: f
        play {
            choice (f) -> {
                drop "then"
            } retry (f) -> {
                drop "elif"
            } fail -> {
                drop "else"
            }
        } gameover
        """
        ast = self.transform(code)
        # flag: f is global
        if_node = ast.main_block.statements[0]
        
        self.assertIsInstance(if_node, IfNode)
        self.assertIsNotNone(if_node.then_block)
        
        # Elifs
        self.assertEqual(len(if_node.elifs), 1)
        self.assertIsInstance(if_node.elifs[0], ElifNode)
        
        # Else
        self.assertIsNotNone(if_node.else_block)
        self.assertIsInstance(if_node.else_block, BlockNode)

    def test_loops(self):
        code = """
        flag: f
        play {
            stay (f) -> { }
        } gameover
        """
        ast = self.transform(code)
        # flag: f is global, so statements[0] is the loop
        while_node = ast.main_block.statements[0]
        self.assertIsInstance(while_node, WhileNode)
        self.assertIsInstance(while_node.condition, VarAccessNode)

    def test_function_def(self):
        code = """
        action foo(rank a) -> void { }
        play {} gameover
        """
        ast = self.transform(code)
        self.assertEqual(len(ast.functions), 1)
        func = ast.functions[0]
        self.assertIsInstance(func, FunNode)
        self.assertEqual(func.name, 'foo')
        self.assertEqual(len(func.params), 1)
        self.assertEqual(func.ret_type, 'void')

    def test_invalid_chain_exception(self):
        # Test the custom exception we added in transformer
        code = """
        play {
            rank: a = b
        } gameover
        """
        # Parsing succeeds, transforming fails
        tree = self.parser.parse(code)
        with self.assertRaisesRegex(Exception, "Invalid chain"):
            self.transformer.transform(tree)

if __name__ == '__main__':
    unittest.main()