"""
Dead Code Elimination Optimizer - Livello 2

Rimuove codice irraggiungibile:
- Branch if con condizione costante falsa
- Loop con condizione costante falsa  
- Codice dopo return/quit
"""

from ...frontend.ast_node import *


class DeadCodeEliminationOptimizer:
    """Ottimizzatore che elimina codice irraggiungibile."""
    
    def __init__(self):
        self.eliminations_count = 0
    
    def optimize(self, ast):
        """Applica dead code elimination all'AST."""
        self.eliminations_count = 0
        return self.visit(ast)
    
    def visit(self, node):
        """Visita un nodo dell'AST."""
        if node is None:
            return None
        
        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        """Visita generica."""
        return node
    
    def visit_IfNode(self, node):
        """Ottimizza if con condizioni costanti."""
        # Prima visita ricorsivamente i blocchi
        node.then_block = self.visit(node.then_block) if node.then_block else None
        if node.elifs:
            for elif_node in node.elifs:
                elif_node.block = self.visit(elif_node.block)
        node.else_block = self.visit(node.else_block) if node.else_block else None
        
        # Se condizione è letterale booleano
        if isinstance(node.condition, LiteralNode) and node.condition.type_tag == 'bool':
            if node.condition.value:  # True
                # Condizione sempre vera: sostituisci con then_block
                self.eliminations_count += 1
                return node.then_block
            else:  # False
                # Condizione sempre falsa: valuta elif/else
                self.eliminations_count += 1
                
                # Prova elif
                if node.elifs:
                    for i, elif_node in enumerate(node.elifs):
                        if isinstance(elif_node.condition, LiteralNode) and elif_node.condition.type_tag == 'flag':
                            if elif_node.condition.value:  # Elif true
                                return elif_node.block
                        else:
                            # Elif con condizione non costante
                            remaining_elifs = node.elifs[i+1:]
                            return IfNode(elif_node.condition, elif_node.block, remaining_elifs, node.else_block)
                
                # Usa else_block
                if node.else_block:
                    return node.else_block
                else:
                    return BlockNode([])
        
        return node
    
    def visit_WhileNode(self, node):
        """Ottimizza while con condizione costante falsa."""
        node.block = self.visit(node.block) if node.block else None
        
        # Se condizione sempre falsa, elimina il while
        if isinstance(node.condition, LiteralNode) and node.condition.type_tag == 'bool':
            if not node.condition.value:  # False
                self.eliminations_count += 1
                return BlockNode([])
        
        return node
    
    def visit_ForNode(self, node):
        """Ottimizza for con condizione costante falsa."""
        node.block = self.visit(node.block) if node.block else None
        
        # Se condizione sempre falsa, mantieni solo init
        if isinstance(node.condition, LiteralNode) and node.condition.type_tag == 'bool':
            if not node.condition.value:  # False
                self.eliminations_count += 1
                if node.init:
                    return BlockNode([node.init])
                else:
                    return BlockNode([])
        
        return node
    
    def visit_BlockNode(self, node):
        """Visita blocco ed elimina statement dopo return/quit."""
        if not node.statements:
            return node
        
        new_statements = []
        for i, stmt in enumerate(node.statements):
            visited_stmt = self.visit(stmt)
            
            if visited_stmt is not None:
                # Se è BlockNode vuoto, salta
                if isinstance(visited_stmt, BlockNode) and not visited_stmt.statements:
                    continue
                new_statements.append(visited_stmt)
            
            # Se return o break, tutto dopo è dead code
            if isinstance(stmt, (ReturnNode, BreakNode)):
                if i < len(node.statements) - 1:
                    self.eliminations_count += len(node.statements) - i - 1
                break
        
        node.statements = new_statements
        return node
    
    def visit_ProgramNode(self, node):
        """Visita programma."""
        node.global_decls = [self.visit(d) for d in (node.global_decls or [])]
        node.functions = [self.visit(f) for f in (node.functions or [])]
        node.main_block = self.visit(node.main_block) if node.main_block else None
        return node
    
    def visit_FunNode(self, node):
        """Visita funzione."""
        node.body = self.visit(node.body) if node.body else None
        return node
