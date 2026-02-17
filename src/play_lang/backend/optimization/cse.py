"""
Common Subexpression Elimination (CSE) - Livello 5

Elimina calcoli ripetuti riusando risultati già calcolati.

Esempio:
    rank: a <-- x + y
    rank: b <-- x + y    # Riusa il calcolo di a
    # Diventa: b <-- a
"""

from ...frontend.ast_node import *


class CSEOptimizer:
    """
    Ottimizzatore Common Subexpression Elimination.
    
    Traccia espressioni già calcolate e sostituisce
    ricalcoli con accessi al risultato precedente.
    """
    
    def __init__(self):
        self.eliminations_count = 0
        self.expressions = {}  # expr_hash -> var_name
    
    def optimize(self, ast):
        """Applica CSE all'AST."""
        self.eliminations_count = 0
        self.expressions = {}
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
    
    def _expr_to_hash(self, expr):
        """
        Genera hash per un'espressione.
        Ritorna None se l'espressione non è hashabile (contiene chiamate, etc).
        """
        if isinstance(expr, LiteralNode):
            return ('lit', expr.type_tag, expr.value)
        
        elif isinstance(expr, VarAccessNode):
            return ('var', expr.name)
        
        elif isinstance(expr, BinOpNode):
            left_hash = self._expr_to_hash(expr.left)
            right_hash = self._expr_to_hash(expr.right)
            if left_hash is None or right_hash is None:
                return None
            return ('binop', expr.op, left_hash, right_hash)
        
        elif isinstance(expr, UnaryOpNode):
            expr_hash = self._expr_to_hash(expr.expr)
            if expr_hash is None:
                return None
            return ('unop', expr.op, expr_hash)
        
        else:
            # Espressioni complesse (chiamate funzioni, etc) non hashate
            return None
    
    def visit_ProgramNode(self, node):
        """Visita programma."""
        self.expressions = {}
        node.global_decls = [self.visit(d) for d in (node.global_decls or [])]
        
        # Ogni funzione ha scope separato
        if node.functions:
            for func in node.functions:
                saved_expr = self.expressions.copy()
                self.expressions = {}
                func.body = self.visit(func.body) if func.body else None
                self.expressions = saved_expr
        
        node.main_block = self.visit(node.main_block) if node.main_block else None
        return node
    
    def visit_BlockNode(self, node):
        """Visita blocco."""
        if not node.statements:
            return node
        
        new_statements = []
        for stmt in node.statements:
            visited = self.visit(stmt)
            
            # Se è assegnamento con espressione, traccia
            if isinstance(visited, AssignNode) and visited.expr:
                expr_hash = self._expr_to_hash(visited.expr)
                
                if expr_hash:
                    # Controlla se espressione già calcolata
                    if expr_hash in self.expressions:
                        # CSE: sostituisci con variabile esistente
                        prev_var = self.expressions[expr_hash]
                        visited.expr = VarAccessNode(prev_var)
                        self.eliminations_count += 1
                    else:
                        # Traccia nuova espressione
                        self.expressions[expr_hash] = visited.target
                
                # Invalida espressioni che usano la variabile assegnata
                self._invalidate_expressions_using(visited.target)
            
            # Se modifica variabile, invalida espressioni
            if isinstance(visited, (AssignNode, VarDeclNode)):
                modified_vars = set()
                if isinstance(visited, AssignNode):
                    modified_vars.add(visited.target)
                elif isinstance(visited, VarDeclNode):
                    for var_init in (visited.var_list or []):
                        modified_vars.add(var_init.name)
                
                for var in modified_vars:
                    self._invalidate_expressions_using(var)
            
            new_statements.append(visited)
        
        node.statements = new_statements
        return node
    
    def _invalidate_expressions_using(self, var_name):
        """Invalida espressioni che dipendono O usano come cache una variabile."""
        to_remove = []
        for expr_hash, cached_var in self.expressions.items():
            # Se l'espressione usa la variabile, OPPURE se la variabile salvata
            # come cache è proprio quella modificata, dobbiamo invalidare.
            if cached_var == var_name or self._expr_uses_var(expr_hash, var_name):
                to_remove.append(expr_hash)
        
        for expr_hash in to_remove:
            del self.expressions[expr_hash]
    
    def _expr_uses_var(self, expr_hash, var_name):
        """Verifica se un'espressione usa una variabile."""
        if not isinstance(expr_hash, tuple):
            return False
        
        if expr_hash[0] == 'var':
            return expr_hash[1] == var_name
        
        elif expr_hash[0] == 'binop':
            return (self._expr_uses_var(expr_hash[2], var_name) or 
                    self._expr_uses_var(expr_hash[3], var_name))
        
        elif expr_hash[0] == 'unop':
            return self._expr_uses_var(expr_hash[2], var_name)
        
        return False
    
    def visit_VarDeclNode(self, node):
        """Visita dichiarazione variabile."""
        if node.var_list:
            for var_init in node.var_list:
                if var_init.expr:
                    var_init.expr = self.visit(var_init.expr)
                    
                    # Traccia espressione
                    expr_hash = self._expr_to_hash(var_init.expr)
                    if expr_hash:
                        if expr_hash in self.expressions:
                            # CSE
                            prev_var = self.expressions[expr_hash]
                            var_init.expr = VarAccessNode(prev_var)
                            self.eliminations_count += 1
                        else:
                            self.expressions[expr_hash] = var_init.name
        return node
    
    def visit_AssignNode(self, node):
        """Visita assegnamento."""
        node.expr = self.visit(node.expr) if node.expr else None
        return node
    
    def visit_BinOpNode(self, node):
        """Visita operazione binaria."""
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        return node
    
    def visit_UnaryOpNode(self, node):
        """Visita operazione unaria."""
        node.expr = self.visit(node.expr)
        return node
    
    def visit_IfNode(self, node):
        """Visita if - invalida espressioni nei branch."""
        node.condition = self.visit(node.condition) if node.condition else None
        
        saved_expr = self.expressions.copy()
        
        if node.then_block:
            self.expressions = saved_expr.copy()
            node.then_block = self.visit(node.then_block)
        
        if node.elifs:
            for elif_node in node.elifs:
                self.expressions = saved_expr.copy()
                elif_node.condition = self.visit(elif_node.condition)
                elif_node.block = self.visit(elif_node.block)
        
        if node.else_block:
            self.expressions = saved_expr.copy()
            node.else_block = self.visit(node.else_block)
        
        # Dopo if, invalida tutto (branch potrebbero aver modificato)
        self.expressions = {}
        
        return node
    
    def visit_WhileNode(self, node):
        """Visita while."""
        node.condition = self.visit(node.condition) if node.condition else None
        
        # Loop invalida espressioni
        self.expressions = {}
        node.block = self.visit(node.block) if node.block else None
        self.expressions = {}
        
        return node
    
    def visit_ForNode(self, node):
        """Visita for."""
        node.init = self.visit(node.init) if node.init else None
        node.condition = self.visit(node.condition) if node.condition else None
        node.update = self.visit(node.update) if node.update else None
        
        self.expressions = {}
        node.block = self.visit(node.block) if node.block else None
        self.expressions = {}
        
        return node
    
    def visit_OutputNode(self, node):
        """Visita output."""
        node.expr = self.visit(node.expr) if node.expr else None
        return node
    
    def visit_ReturnNode(self, node):
        """Visita return."""
        node.expr = self.visit(node.expr) if node.expr else None
        return node
    
    def visit_FunCallExprNode(self, node):
        """Visita chiamata funzione."""
        node.args = [self.visit(arg) for arg in (node.args or [])]
        return node
