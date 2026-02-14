"""
Strength Reduction Optimizer - Livello 3

Sostituisce operazioni costose con equivalenti più efficienti:
- x * 0 -> 0
- x * 1 -> x  
- x * 2 -> x + x
- x + 0 -> x
- x - 0 -> x
- x / 1 -> x
- true && x -> x
- false || x -> x
"""

from ...frontend.ast_node import *


class StrengthReductionOptimizer:
    """Ottimizzatore strength reduction."""
    
    def __init__(self):
        self.reductions_count = 0
    
    def optimize(self, ast):
        """Applica strength reduction all'AST."""
        self.reductions_count = 0
        return self.visit(ast)
    
    def visit(self, node):
        """Visita un nodo dell'AST."""
        if node is None:
            return None
        
        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        """Visita generica che attraversa tutti i figli."""
        # Attraversa ricorsivamente
        for attr_name in ['left', 'right', 'expr', 'condition', 'block', 'then_block', 
                          'else_block', 'init', 'update', 'body', 'statements', 'args',
                          'global_decls', 'functions', 'main_block']:
            if hasattr(node, attr_name):
                attr = getattr(node, attr_name)
                if isinstance(attr, AstNode):
                    setattr(node, attr_name, self.visit(attr))
                elif isinstance(attr, list):
                    setattr(node, attr_name, [self.visit(item) if isinstance(item, AstNode) else item for item in attr])
        
        # Gestisce elifs e var_list
        if hasattr(node, 'elifs') and node.elifs:
            for elif_node in node.elifs:
                elif_node.condition = self.visit(elif_node.condition)
                elif_node.block = self.visit(elif_node.block)
        
        if hasattr(node, 'var_list') and node.var_list:
            for var_init in node.var_list:
                if var_init.expr:
                    var_init.expr = self.visit(var_init.expr)
        
        return node
    
    def _is_literal_zero(self, node):
        """Verifica se è letterale 0."""
        return (isinstance(node, LiteralNode) and 
                node.value == 0 and 
                node.type_tag in ['int', 'float'])
    
    def _is_literal_one(self, node):
        """Verifica se è letterale 1."""
        return (isinstance(node, LiteralNode) and 
                node.value == 1 and 
                node.type_tag in ['int', 'float'])
    
    def _is_literal_two(self, node):
        """Verifica se è letterale 2."""
        return (isinstance(node, LiteralNode) and 
                node.value == 2 and 
                node.type_tag == 'int')
    
    def visit_BinOpNode(self, node):
        """Applica strength reduction su operazioni binarie."""
        # Prima visita ricorsivamente
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        
        # Moltiplicazione
        if node.op == '*':
            # x * 0 -> 0
            if self._is_literal_zero(node.right):
                self.reductions_count += 1
                return LiteralNode(0, 'int')
            if self._is_literal_zero(node.left):
                self.reductions_count += 1
                return LiteralNode(0, 'int')
            
            # x * 1 -> x
            if self._is_literal_one(node.right):
                self.reductions_count += 1
                return node.left
            if self._is_literal_one(node.left):
                self.reductions_count += 1
                return node.right
            
            # x * 2 -> x + x (solo se non letterale)
            if self._is_literal_two(node.right) and not isinstance(node.left, LiteralNode):
                self.reductions_count += 1
                return BinOpNode(node.left, '+', node.left)
            if self._is_literal_two(node.left) and not isinstance(node.right, LiteralNode):
                self.reductions_count += 1
                return BinOpNode(node.right, '+', node.right)
        
        # Addizione
        elif node.op == '+':
            # x + 0 -> x
            if self._is_literal_zero(node.right):
                self.reductions_count += 1
                return node.left
            if self._is_literal_zero(node.left):
                self.reductions_count += 1
                return node.right
        
        # Sottrazione
        elif node.op == '-':
            # x - 0 -> x
            if self._is_literal_zero(node.right):
                self.reductions_count += 1
                return node.left
            
            # 0 - x -> -x
            if self._is_literal_zero(node.left):
                self.reductions_count += 1
                return UnaryOpNode('-', node.right)
        
        # Divisione
        elif node.op == '/':
            # x / 1 -> x
            if self._is_literal_one(node.right):
                self.reductions_count += 1
                return node.left
        
        # Operatori logici
        elif node.op == '&&':
            # true && x -> x
            if isinstance(node.left, LiteralNode) and node.left.type_tag == 'bool' and node.left.value:
                self.reductions_count += 1
                return node.right
            # x && true -> x  
            if isinstance(node.right, LiteralNode) and node.right.type_tag == 'bool' and node.right.value:
                self.reductions_count += 1
                return node.left
            # false && x -> false
            if isinstance(node.left, LiteralNode) and node.left.type_tag == 'bool' and not node.left.value:
                self.reductions_count += 1
                return LiteralNode(False, 'bool')
            # x && false -> false
            if isinstance(node.right, LiteralNode) and node.right.type_tag == 'bool' and not node.right.value:
                self.reductions_count += 1
                return LiteralNode(False, 'bool')
        
        elif node.op == '||':
            # true || x -> true
            if isinstance(node.left, LiteralNode) and node.left.type_tag == 'bool' and node.left.value:
                self.reductions_count += 1
                return LiteralNode(True, 'bool')
            # x || true -> true
            if isinstance(node.right, LiteralNode) and node.right.type_tag == 'bool' and node.right.value:
                self.reductions_count += 1
                return LiteralNode(True, 'bool')
            # false || x -> x
            if isinstance(node.left, LiteralNode) and node.left.type_tag == 'bool' and not node.left.value:
                self.reductions_count += 1
                return node.right
            # x || false -> x
            if isinstance(node.right, LiteralNode) and node.right.type_tag == 'bool' and not node.right.value:
                self.reductions_count += 1
                return node.left
        
        return node
