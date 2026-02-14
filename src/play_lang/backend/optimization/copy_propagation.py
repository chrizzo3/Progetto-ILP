"""
Copy Propagation Optimizer - Livello 4

Propaga copie di variabili per ridurre accessi e abilitare constant folding.

Esempio:
    rank: x <-- 5
    rank: y <-- x        # y è copia di x
    rank: z <-- y + 1    # z <-- x + 1, poi CF: z <-- 5 + 1 = 6
"""

from ...frontend.ast_node import *


class CopyPropagationOptimizer:
    """
    Ottimizzatore copy propagation.
    
    Traccia assegnamenti semplici (x <-- y) e sostituisce
    gli usi di x con y quando possibile.
    """
    
    def __init__(self):
        self.propagations_count = 0
        self.copies = {}  # var_name -> source_var_name
    
    def optimize(self, ast):
        """Applica copy propagation all'AST."""
        self.propagations_count = 0
        self.copies = {}
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
    
    def visit_ProgramNode(self, node):
        """Visita programma - scope globale."""
        # Reset copies per scope globale
        self.copies = {}
        node.global_decls = [self.visit(d) for d in (node.global_decls or [])]
        
        # Ogni funzione ha il suo scope
        if node.functions:
            for func in node.functions:
                saved_copies = self.copies.copy()
                self.copies = {}
                func.body = self.visit(func.body) if func.body else None
                self.copies = saved_copies
        
        # Main block
        node.main_block = self.visit(node.main_block) if node.main_block else None
        return node
    
    def visit_BlockNode(self, node):
        """Visita blocco sequenziale."""
        if not node.statements:
            return node
        
        new_statements = []
        for stmt in node.statements:
            # Processa statement
            visited = self.visit(stmt)
            
            # Se è assegnamento semplice, traccia la copia
            if isinstance(visited, AssignNode):
                if isinstance(visited.expr, VarAccessNode):
                    # x <-- y: traccia che x è copia di y
                    source = visited.expr.name
                    target = visited.target
                    
                    # Propaga transitivamente: se y è copia di z, x diventa copia di z
                    while source in self.copies:
                        source = self.copies[source]
                    
                    self.copies[target] = source
                else:
                    # x <-- expr: x non è più una copia
                    if visited.target in self.copies:
                        del self.copies[visited.target]
            
            # Se modifica una variabile, invalida copie che la usano
            self._invalidate_copies_using(visited)
            
            new_statements.append(visited)
        
        node.statements = new_statements
        return node
    
    def _invalidate_copies_using(self, node):
        """Invalida copie che dipendono da variabili modificate."""
        # Trova variabili modificate
        modified_vars = set()
        if isinstance(node, AssignNode):
            modified_vars.add(node.target)
        elif isinstance(node, VarDeclNode):
            for var_init in (node.var_list or []):
                modified_vars.add(var_init.name)
        
        # Rimuovi copie che usano variabili modificate
        if modified_vars:
            to_remove = []
            for copy_var, source_var in self.copies.items():
                if source_var in modified_vars:
                    to_remove.append(copy_var)
            for var in to_remove:
                del self.copies[var]
    
    def visit_VarDeclNode(self, node):
        """Visita dichiarazione variabile."""
        if node.var_list:
            for var_init in node.var_list:
                if var_init.expr:
                    var_init.expr = self.visit(var_init.expr)
                    
                    # Traccia copia se dichiarazione con copia
                    if isinstance(var_init.expr, VarAccessNode):
                        source = var_init.expr.name
                        while source in self.copies:
                            source = self.copies[source]
                        self.copies[var_init.name] = source
        return node
    
    def visit_AssignNode(self, node):
        """Visita assegnamento."""
        node.expr = self.visit(node.expr) if node.expr else None
        return node
    
    def visit_VarAccessNode(self, node):
        """Visita accesso variabile - applica propagazione."""
        # Se la variabile è una copia, sostituisci con la sorgente
        if node.name in self.copies:
            self.propagations_count += 1
            return VarAccessNode(self.copies[node.name])
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
        """Visita if - gestisce scope separati per branch."""
        node.condition = self.visit(node.condition) if node.condition else None
        
        # Salva stato copie prima dei branch
        saved_copies = self.copies.copy()
        
        # Then block con scope proprio
        if node.then_block:
            self.copies = saved_copies.copy()
            node.then_block = self.visit(node.then_block)
        
        # Elif blocks
        if node.elifs:
            for elif_node in node.elifs:
                self.copies = saved_copies.copy()
                elif_node.condition = self.visit(elif_node.condition)
                elif_node.block = self.visit(elif_node.block)
        
        # Else block
        if node.else_block:
            self.copies = saved_copies.copy()
            node.else_block = self.visit(node.else_block)
        
        # Dopo if, copie non più valide (potrebbero essere state modificate)
        self.copies = {}
        
        return node
    
    def visit_WhileNode(self, node):
        """Visita while."""
        node.condition = self.visit(node.condition) if node.condition else None
        
        # Loop invalida tutte le copie (iterazioni multiple)
        saved_copies = self.copies.copy()
        self.copies = {}
        node.block = self.visit(node.block) if node.block else None
        self.copies = {}
        
        return node
    
    def visit_ForNode(self, node):
        """Visita for."""
        node.init = self.visit(node.init) if node.init else None
        node.condition = self.visit(node.condition) if node.condition else None
        node.update = self.visit(node.update) if node.update else None
        
        # Loop invalida copie
        self.copies = {}
        node.block = self.visit(node.block) if node.block else None
        self.copies = {}
        
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
