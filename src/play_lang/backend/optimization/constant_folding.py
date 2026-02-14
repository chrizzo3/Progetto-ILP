"""
Constant Folding Optimizer - Livello 1

Valuta espressioni costanti a compile-time.
"""

from ...frontend.ast_node import *


class ConstantFoldingOptimizer:
    """Ottimizzatore constant folding."""
    
    def __init__(self):
        self.optimizations_count = 0
    
    def optimize(self, ast):
        """Applica constant folding all'AST."""
        self.optimizations_count = 0
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
        return node
    
    def visit_BinOpNode(self, node):
        """Ottimizza operazioni binarie costanti."""
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        
        if not (isinstance(node.left, LiteralNode) and isinstance(node.right, LiteralNode)):
            return node
        
        l_val, r_val = node.left.value, node.right.value
        l_type, r_type = node.left.type_tag, node.right.type_tag
        
        # Aritmetici
        if node.op == '+':
            self.optimizations_count += 1
            if 'label' in [l_type, r_type]:
                return LiteralNode(str(l_val) + str(r_val), 'label')
            result_type = 'rate' if 'rate' in [l_type, r_type] else 'rank'
            return LiteralNode(l_val + r_val, result_type)
        elif node.op == '-':
            self.optimizations_count += 1
            result_type = 'rate' if 'rate' in [l_type, r_type] else 'rank'
            return LiteralNode(l_val - r_val, result_type)
        elif node.op == '*':
            self.optimizations_count += 1
            result_type = 'rate' if 'rate' in [l_type, r_type] else 'rank'
            return LiteralNode(l_val * r_val, result_type)
        elif node.op == '/':
            if r_val == 0:
                return node
            self.optimizations_count += 1
            result_type = 'rate' if 'rate' in [l_type, r_type] else 'rank'
            res = l_val / r_val
            return LiteralNode(int(res) if result_type == 'rank' else res, result_type)
        elif node.op == '%' and l_type == 'rank' and r_type == 'rank':
            if r_val == 0:
                return node
            self.optimizations_count += 1
            return LiteralNode(l_val % r_val, 'rank')
        
        # Confronto
        elif node.op in ['<', '<=', '>', '>=', '==', '<>']:
            self.optimizations_count += 1
            ops = {
                '<': lambda a, b: a < b,
                '<=': lambda a, b: a <= b,
                '>': lambda a, b: a > b,
                '>=': lambda a, b: a >= b,
                '==': lambda a, b: a == b,
                '<>': lambda a, b: a != b
            }
            result = ops[node.op](l_val, r_val)
            return LiteralNode(result, 'flag')
        
        # Logici
        elif node.op == '&&' and l_type == 'flag' and r_type == 'flag':
            self.optimizations_count += 1
            return LiteralNode(l_val and r_val, 'flag')
        elif node.op == '||' and l_type == 'flag' and r_type == 'flag':
            self.optimizations_count += 1
            return LiteralNode(l_val or r_val, 'flag')
        
        return node
    
    def visit_UnaryOpNode(self, node):
        """Ottimizza operazioni unarie costanti."""
        node.expr = self.visit(node.expr)
        
        if not isinstance(node.expr, LiteralNode):
            return node
        
        if node.op == '-':
            self.optimizations_count += 1
            return LiteralNode(-node.expr.value, node.expr.type_tag)
        elif node.op == '+':
            self.optimizations_count += 1
            return node.expr
        elif node.op == '!' and node.expr.type_tag == 'flag':
            self.optimizations_count += 1
            return LiteralNode(not node.expr.value, 'flag')
        
        return node
    
    def visit_ProgramNode(self, node):
        node.global_decls = [self.visit(d) for d in (node.global_decls or [])]
        node.functions = [self.visit(f) for f in (node.functions or [])]
        node.main_block = self.visit(node.main_block) if node.main_block else None
        return node
    
    def visit_BlockNode(self, node):
        node.statements = [self.visit(s) for s in (node.statements or [])]
        return node
    
    def visit_VarDeclNode(self, node):
        if node.var_list:
            for var_init in node.var_list:
                if var_init.expr:
                    var_init.expr = self.visit(var_init.expr)
        return node
    
    def visit_AssignNode(self, node):
        node.expr = self.visit(node.expr) if node.expr else None
        return node
    
    def visit_IfNode(self, node):
        node.condition = self.visit(node.condition) if node.condition else None
        node.then_block = self.visit(node.then_block) if node.then_block else None
        if node.elifs:
            for elif_node in node.elifs:
                elif_node.condition = self.visit(elif_node.condition)
                elif_node.block = self.visit(elif_node.block)
        node.else_block = self.visit(node.else_block) if node.else_block else None
        return node
    
    def visit_WhileNode(self, node):
        node.condition = self.visit(node.condition) if node.condition else None
        node.block = self.visit(node.block) if node.block else None
        return node
    
    def visit_ForNode(self, node):
        node.init = self.visit(node.init) if node.init else None
        node.condition = self.visit(node.condition) if node.condition else None
        node.update = self.visit(node.update) if node.update else None
        node.block = self.visit(node.block) if node.block else None
        return node
    
    def visit_FunNode(self, node):
        node.body = self.visit(node.body) if node.body else None
        return node
    
    def visit_ReturnNode(self, node):
        node.expr = self.visit(node.expr) if node.expr else None
        return node
    
    def visit_OutputNode(self, node):
        node.expr = self.visit(node.expr) if node.expr else None
        return node
    
    def visit_FunCallExprNode(self, node):
        node.args = [self.visit(arg) for arg in (node.args or [])]
        return node
