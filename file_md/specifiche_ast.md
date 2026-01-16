# Definizione Nodi AST - Play

Scheletro delle classi Python per l'Abstract Syntax Tree.

```python
# --- Nodi Base ---
class AstNode:
    pass

class StmtNode(AstNode):
    pass

class ExprNode(AstNode):
    pass

# --- Struttura Generale ---

class ProgramNode(AstNode):
    def __init__(self, global_decls, functions, main_block):
        self.global_decls = global_decls # list of VarDeclNode
        self.functions = functions       # list of FunNode
        self.main_block = main_block     # BlockNode

class BlockNode(StmtNode):
    def __init__(self, statements):
        self.statements = statements # list of StmtNode

# --- Dichiarazioni ---

class VarDeclNode(StmtNode):
    def __init__(self, type_name, var_list):
        self.type_name = type_name # str ('rank', 'flag', etc.)
        self.var_list = var_list   # list of VarInitNode

class VarInitNode(AstNode):
    def __init__(self, name, expr=None):
        self.name = name     # str
        self.expr = expr     # ExprNode or None

class FunNode(AstNode):
    def __init__(self, name, params, ret_type, body):
        self.name = name
        self.params = params      # list of ParamNode
        self.ret_type = ret_type  # str
        self.body = body          # BlockNode
```

```python
class ParamNode(AstNode):
    def __init__(self, type_name, name):
        self.type_name = type_name
        self.name = name

# --- Statements ---

class AssignNode(StmtNode):
    def __init__(self, target, expr):
        self.target = target # str
        self.expr = expr     # ExprNode

class IfNode(StmtNode):
    def __init__(self, condition, then_block, elifs=None, else_block=None):
        self.condition = condition
        self.then_block = then_block
        self.elifs = elifs       # list of ElifNode
        self.else_block = else_block

class ElifNode(AstNode):
    def __init__(self, condition, block):
        self.condition = condition
        self.block = block

class WhileNode(StmtNode): # Stay
    def __init__(self, condition, block):
        self.condition = condition
        self.block = block

class ForNode(StmtNode): # Loop
    def __init__(self, init, condition, update, block):
        self.init = init         # StmtNode (Assign)
        self.condition = condition # ExprNode
        self.update = update     # StmtNode (Assign) or ExprNode
        self.block = block

class InputNode(StmtNode):
    def __init__(self, target_groups, prompt_expr):
        self.target_groups = target_groups # list of list of str (each inner list is a chain)
        self.prompt_expr = prompt_expr

class OutputNode(StmtNode):
    def __init__(self, expr):
        self.expr = expr

class ReturnNode(StmtNode): # Reward
    def __init__(self, expr=None):
        self.expr = expr

class BreakNode(StmtNode): # Quit
    pass

class FuncCallStmtNode(StmtNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args



# --- Espressioni ---

class BinOpNode(ExprNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class UnaryOpNode(ExprNode): 
    def __init__(self, op, expr):
        self.op = op # '!', '-', '+', '-->'
        self.expr = expr

class LiteralNode(ExprNode):
    def __init__(self, value, type_tag):
        self.value = value
        self.type_tag = type_tag # 'int', 'float', 'bool', 'string'

class VarAccessNode(ExprNode):
    def __init__(self, name):
        self.name = name

class FunCallExprNode(ExprNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args
```
