import sys
import os

from .ast_node import *

class SemanticError(Exception):
    pass

class SymbolTable:
    def __init__(self):
        self.scopes = [{}]  # Stack of scopes (maps: name -> {'type': ..., 'kind': ...})

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
        else:
            raise Exception("Cannot exit global scope")

    def define(self, name, type_info, kind):
        """
        type_info: 'rank', 'rate', 'flag', 'label', or function signature
        kind: 'var' or 'func'
        """
        current_scope = self.scopes[-1]
        if name in current_scope:
            raise SemanticError(f"Symbol '{name}' already defined in current scope.")
        current_scope[name] = {'type': type_info, 'kind': kind}

    def lookup(self, name):
        # Search from innermost scope to outermost
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.in_output = False
        # Initialize embedded functions or constants if needed
    
    def visit(self, node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"No visit_{type(node).__name__} method")

    def visit_ProgramNode(self, node):
        # 1. Register global variables
        for var_decl in node.global_decls:
            self.visit(var_decl)
        
        # 2. Register function signatures first (to allow forward refs / recursion if supported, or just standard def)
        for fun_node in node.functions:
            self._register_function(fun_node)

        # 3. Analyze function bodies
        for fun_node in node.functions:
            self.visit(fun_node)

        # 4. Analyze main block
        self.visit(node.main_block)

    def _register_function(self, node):
        # Check if already defined
        if self.symbol_table.lookup(node.name):
             raise SemanticError(f"Function '{node.name}' already defined.")
        
        # Build signature: (param_types, return_type)
        param_types = [p.type_name for p in node.params]
        sig = {'params': param_types, 'ret': node.ret_type}
        
        # Define in GLOBAL scope (assumed to be current scope at this point or strictly scope[0])
        # Since we are in visit_ProgramNode, we should be in global scope.
        self.symbol_table.define(node.name, sig, 'func')

    # --- Declarations ---

    def visit_VarDeclNode(self, node):
        type_name = node.type_name
        for var_init in node.var_list:
            self._visit_VarInitNode(var_init, type_name)

    def _visit_VarInitNode(self, node, type_name):
        # Check init expr type if present
        if node.expr:
            expr_type = self.visit(node.expr)
            if not self._check_type_compatibility(type_name, expr_type):
                raise SemanticError(f"Type mismatchin declaration of '{node.name}': expected {type_name}, got {expr_type}")
        
        self.symbol_table.define(node.name, type_name, 'var')

    # --- Functions ---

    def visit_FunNode(self, node):
        # Function signature already registered in visit_ProgramNode
        self.symbol_table.enter_scope()
        
        # Define parameters
        for param in node.params:
            self.symbol_table.define(param.name, param.type_name, 'var')
            
        # Visit body
        # We need to pass expected return type to check returns inside block?
        # Or store it in instance var.
        self.current_function_ret_type = node.ret_type
        self.visit(node.body)
        self.current_function_ret_type = None
        
        self.symbol_table.exit_scope()

    # --- Statements ---

    def visit_BlockNode(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_AssignNode(self, node):
        target_name = node.target
        target_info = self.symbol_table.lookup(target_name)
        if not target_info:
            raise SemanticError(f"Variable '{target_name}' not declared.")
        if target_info['kind'] != 'var':
             raise SemanticError(f"Cannot assign to '{target_name}' which is a {target_info['kind']}")
        
        target_type = target_info['type']
        expr_type = self.visit(node.expr)
        
        if not self._check_type_compatibility(target_type, expr_type):
             raise SemanticError(f"Type mismatch in assignment to '{target_name}': expected {target_type}, got {expr_type}")

    def visit_IfNode(self, node):
        cond_type = self.visit(node.condition)
        if cond_type != 'flag':
             raise SemanticError(f"If condition must be 'flag', got {cond_type}")
        
        self.visit(node.then_block)
        
        if node.elifs:
            for elif_node in node.elifs:
                self.visit(elif_node)
        
        if node.else_block:
            self.visit(node.else_block)

    def visit_ElifNode(self, node):
        cond_type = self.visit(node.condition)
        if cond_type != 'flag':
             raise SemanticError(f"Elif condition must be 'flag', got {cond_type}")
        self.visit(node.block)

    def visit_WhileNode(self, node):
        cond_type = self.visit(node.condition)
        if cond_type != 'flag':
             raise SemanticError(f"While condition must be 'flag', got {cond_type}")
        self._enter_loop()
        self.visit(node.block)
        self._exit_loop()

    def visit_ForNode(self, node):
        # New scope for loop var? The specs don't explicitly say for-loop vars are local to loop,
        # but typically init is a statement. If it's a declaration, we might need a scope.
        # Our grammar: `for_stat: LOOP LPAR assign_stmt SEMI expr SEMI (assign_stmt | expr) ...`
        # `assign_stmt` uses existing vars. So no new scope needed for vars, 
        # but we need to verify the parts.
        
        self.visit(node.init)
        
        cond_type = self.visit(node.condition)
        if cond_type != 'flag':
             raise SemanticError(f"For condition must be 'flag', got {cond_type}")
             
        # Update can be Stmt (Assign) or Expr
        self.visit(node.update)
        
        self._enter_loop()
        self.visit(node.block)
        self._exit_loop()

    def visit_InputNode(self, node):
        # node.prompt_expr
        if node.prompt_expr:
            p_type = self.visit(node.prompt_expr)
            if p_type != 'label':
                raise SemanticError(f"Input prompt must be 'label', got {p_type}")
        
        # node.target_groups is list of lists.
        # "flattened" check as per spec
        for group in node.target_groups:
            for var_name in group:
                info = self.symbol_table.lookup(var_name)
                if not info:
                    raise SemanticError(f"Input target '{var_name}' not declared")

    def visit_OutputNode(self, node):
        self.in_output = True
        expr_type = self.visit(node.expr)
        self.in_output = False
        
        if expr_type != 'label':
             raise SemanticError(f"Output requires 'label', got {expr_type}")

    def visit_ReturnNode(self, node):
        if not hasattr(self, 'current_function_ret_type') or self.current_function_ret_type is None:
             raise SemanticError("Return statement outside function")
             
        ret_type = self.current_function_ret_type
        
        if node.expr:
            expr_type = self.visit(node.expr)
            if not self._check_type_compatibility(ret_type, expr_type):
                 raise SemanticError(f"Invalid return type: expected {ret_type}, got {expr_type}")
        else:
            if ret_type != 'void':
                 raise SemanticError(f"Return value expected for non-void function (expected {ret_type})")

    def visit_BreakNode(self, node):
        if not getattr(self, 'in_loop', False):
             raise SemanticError("Quit used outside loop")

    def visit_FuncCallStmtNode(self, node):
        self._check_func_call(node.name, node.args)

    # --- Expressions ---

    def visit_LiteralNode(self, node):
        # Mappings: 'int'->'rank', 'float'->'rate', 'string'->'label', 'bool'->'flag'
        # node.type_tag comes from transformer: 'rank', 'rate', 'label', 'flag'
        return node.type_tag

    def visit_VarAccessNode(self, node):
        info = self.symbol_table.lookup(node.name)
        if not info:
             raise SemanticError(f"Variable '{node.name}' not defined")
        return info['type']

    def visit_BinOpNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = node.op

        # Logic: &&, ||
        if op in ['&&', '||']:
            if left == 'flag' and right == 'flag':
                return 'flag'
            raise SemanticError(f"Logical op {op} requires flags, got {left}, {right}")

        # Comparison: ==, <>, <, <=, >, >=
        if op in ['==', '<>', '<', '<=', '>', '>=']:
            if self._check_type_compatibility(left, right) or self._check_type_compatibility(right, left):
                 # Loose check: strict check would be both numeric OR both string OR both flag
                 if self._is_numeric(left) and self._is_numeric(right): return 'flag'
                 if left == right: return 'flag' # e.g. label == label
                 # Allow cross-numeric comparison? Rule says 9: "compatible"
                 pass
            raise SemanticError(f"Comparison {op} types incompatible: {left}, {right}")
            return 'flag'

        # Arithmetic: +, -, *, /, %
        if op == '+':
            # Special case: String concat
            if left == 'label' or right == 'label':
                return 'label'
            # Numeric sum
            if self._is_numeric(left) and self._is_numeric(right):
                if left == 'rate' or right == 'rate': return 'rate'
                return 'rank'
            raise SemanticError(f"Operator + incompatible types: {left}, {right}")
            
        if op in ['-', '*', '/', '%']:
            if self._is_numeric(left) and self._is_numeric(right):
                if left == 'rate' or right == 'rate': return 'rate'
                return 'rank'
            raise SemanticError(f"Operator {op} requires numeric, got {left}, {right}")

    def visit_UnaryOpNode(self, node):
        op = node.op
        expr_type = self.visit(node.expr)
        
        if op == '!':
            if expr_type == 'flag': return 'flag'
            raise SemanticError(f"Not (!) requires flag, got {expr_type}")
        
        if op in ['-', '+']:
            if self._is_numeric(expr_type): return expr_type
            raise SemanticError(f"Unary {op} requires numeric, got {expr_type}")
            
        if op == '-->':
            # Rule 2: Operator --> can only be used in Output (Drop)
            if not getattr(self, 'in_output', False):
                 raise SemanticError("Operator '-->' can only be used in 'drop' statements")
            return expr_type

    def visit_FunCallExprNode(self, node):
        return self._check_func_call(node.name, node.args)

    # --- Helpers ---

    def _check_func_call(self, name, args):
        info = self.symbol_table.lookup(name)
        if not info:
             raise SemanticError(f"Function '{name}' not defined")
        if info['kind'] != 'func':
             raise SemanticError(f"'{name}' is not a function")
        
        sig = info['type'] # {params: [...], ret: ...}
        param_types = sig['params']
        
        if len(args) != len(param_types):
             raise SemanticError(f"Function '{name}' expects {len(param_types)} args, got {len(args)}")
             
        for i, arg_expr in enumerate(args):
            arg_type = self.visit(arg_expr)
            if not self._check_type_compatibility(param_types[i], arg_type):
                 raise SemanticError(f"Argument {i+1} of '{name}' type mismatch: expected {param_types[i]}, got {arg_type}")
                 
        return sig['ret']

    def _check_type_compatibility(self, expected, actual):
        if expected == actual:
            return True
        # Promotion: rank -> rate (assignment of rank to rate variable is ok?)
        # Usually: expected=rate, actual=rank is OK.
        if expected == 'rate' and actual == 'rank':
            return True
        return False

    def _is_numeric(self, t):
        return t in ['rank', 'rate']

    def _enter_loop(self):
        if not hasattr(self, 'loop_depth'): self.loop_depth = 0
        self.loop_depth += 1
        self.in_loop = True

    def _exit_loop(self):
        self.loop_depth -= 1
        if self.loop_depth == 0:
            self.in_loop = False
