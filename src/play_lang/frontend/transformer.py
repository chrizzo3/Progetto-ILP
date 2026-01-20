import sys
import os
from lark import Transformer, Token


from .ast_node import *

class PlayTransformer(Transformer):
    """
    Trasforma l'albero di sintassi concreta (CST) di Lark 
    nell'Albero di Sintassi Astratta (AST) definito in ast_node.py.
    """

    # --- Struttura Generale ---

    def program(self, items):
        # items: [decl_list, function_defs, main_block, GAMEOVER]
        # global_decls è una lista di VarDeclNode
        # functions è una lista di FunNode
        # main_block è un BlockNode
        return ProgramNode(items[0], items[1], items[2])

    def decl_list(self, items):
        # items è già una lista di VarDeclNode grazie alla regola var_decl*
        return items

    def function_defs(self, items):
        # items è una lista di FunNode
        return items

    def main_block(self, items):
        # items: [PLAY, block] -> restituisce il nodo blocco
        return items[1]

    def block(self, items):
        # items: [LBRACE, stmts, RBRACE]
        return BlockNode(items[1])

    def stmts(self, items):
        # items è una lista di risultati dai singoli stmt.
        # Alcuni stmt (come assign) potrebbero restituire una LISTA di nodi.
        # Dobbiamo appiattire la lista (flatten).
        flat_list = []
        for i in items:
            if isinstance(i, list):
                flat_list.extend(i)
            elif i is not None:
                flat_list.append(i)
        return flat_list

    def stmt(self, items):
        # Pass-through: restituisce direttamente il figlio (es. AssignNode, IfNode...)
        return items[0]

    # --- Dichiarazioni ---

    def var_decl(self, items):
        # items: [type, COLON, var_list]
        return VarDeclNode(str(items[0]), items[2])

    def var_list(self, items):
        # items: [var_item, COMMA, var_item, ...]
        # Ogni var_item restituisce una LISTA di VarInitNode.
        # Dobbiamo unire tutte le liste e ignorare le virgole.
        full_list = []
        for item in items:
            if isinstance(item, list):
                full_list.extend(item)
        return full_list

    def var_item(self, items):
        # Gestisce: ID | ID ASSIGN expr | ID EQUALS var_item
        name = str(items[0])
        
        # Caso 1: ID (dichiarazione senza inizializzazione)
        if len(items) == 1:
            return [VarInitNode(name, None)]
        
        # Caso 2: ID <-- expr
        elif len(items) == 3 and items[1].type == 'ASSIGN':
            return [VarInitNode(name, items[2])]
        
        # Caso 3: ID = var_item (dichiarazione a catena: rank a = b <-- 10)
        elif len(items) == 3 and items[1].type == 'EQUALS':
            child_list = items[2] # Lista di VarInitNode del figlio
            # Prendiamo l'espressione dal primo nodo della lista figlia 
            # (che corrisponde alla variabile immediatamente a destra)
            first_child = child_list[0]
            
            # Rule 1: Chains must have an assigned value
            if first_child.expr is None:
                raise Exception(f"Invalid chain: '{name}' cannot be equated to '{first_child.name}' without a value assignment.")

            # Creiamo il nodo per la variabile corrente copiando l'espressione
            current_node = VarInitNode(name, first_child.expr)
            return [current_node] + child_list
        
        return []

    def type(self, items):
        return str(items[0]) # 'rank', 'rate', etc.

    # --- Statements ---

    def lvalue(self, items):
        # items: [ID] oppure [ID, EQUALS, lvalue]
        name = str(items[0])
        if len(items) == 1:
            return [name]
        else:
            # Ricorsione: aggiunge il nome corrente alla lista restituita dai figli
            return [name] + items[2]

    def lvalue_list(self, items):
        # items: [lvalue, COMMA, lvalue...]
        # Restituisce una LISTA DI LISTE per preservare i gruppi separati da virgola
        # Es: "a, b=c" -> [['a'], ['b', 'c']]
        groups = []
        for item in items:
            if isinstance(item, list): # Risultato di lvalue (che è una lista di nomi)
               groups.append(item)
        return groups

    # --- Statements ---

    def assign_stmt(self, items):
        # items: [lvalue_list, ASSIGN, expr]
        # lvalue_list è ora [['a'], ['b', 'c']]
        # Specifica utente: "a, b <-- 10" -> Solo b riceve 10.
        # "a = b <-- 10" -> a e b ricevono 10.
        
        groups = items[0]
        expr = items[2]
        
        # Prendiamo solo l'ULTIMO gruppo della lista (quello semanticamente legato all'espressione)
        # Gli altri gruppi vengono ignorati (o valutati ma non assegnati, in base alla semantica desiderata, 
        # ma qui costruiamo AST dichiarativo: generiamo nodi solo per ciò che avviene).
        if not groups:
            return []
            
        target_group = groups[-1] # Es. ['b', 'c'] in "a, b=c <-- 10"
        
        # Crea un AssignNode per ogni variabile nella catena target
        return [AssignNode(name, expr) for name in target_group]

    def input_stat(self, items):
        # items: [lvalue_list, ASSIGN, GRAB, expr]
        # Qui passiamo TUTTI i gruppi perché InputNode supporta la struttura (list of list)
        return InputNode(items[0], items[3])

    def output_stat(self, items):
        # items: [DROP, expr]
        return OutputNode(items[1])

    def return_stat(self, items):
        # items: [REWARD, expr] oppure [REWARD, VOID]
        if len(items) == 2 and isinstance(items[1], Token) and items[1].type == 'VOID':
            return ReturnNode(None)
        return ReturnNode(items[1])

    def break_stat(self, items):
        return BreakNode()

    # --- Control Flow ---

    def if_stat(self, items):
        # items: [CHOICE, LPAR, expr, RPAR, ARROW, block, elif_stat, else_stat]
        # Indici: 2=cond, 5=then, 6=elifs, 7=else
        return IfNode(items[2], items[5], items[6], items[7])

    def elif_stat(self, items):
        # Se vuoto restituisce None (o lista vuota nel transformer default, ma qui gestiamo i casi)
        if not items:
            return []
        # items: [RETRY, LPAR, expr, RPAR, ARROW, block, elif_stat]
        # Indici: 2=cond, 5=block, 6=recursive_elifs
        current_elif = ElifNode(items[2], items[5])
        return [current_elif] + items[6]

    def else_stat(self, items):
        # Se vuoto o assente
        if not items:
            return None
        # items: [FAIL, ARROW, block]
        return items[2]

    def while_stat(self, items):
        # items: [STAY, LPAR, expr, RPAR, ARROW, block]
        return WhileNode(items[2], items[5])

    def for_stat(self, items):
        # items: [LOOP, LPAR, assign_stmt, SEMI, expr, SEMI, update, RPAR, ARROW, block]
        # init (assign_stmt) restituisce una lista di AssignNode.
        # ForNode richiede un singolo StmtNode o BlockNode per init.
        init_nodes = items[2]
        if len(init_nodes) == 1:
            init = init_nodes[0]
        else:
            init = BlockNode(init_nodes) # Avvolgiamo in un blocco se multipli

        cond = items[4]
        
        # update è (assign_stmt | expr)
        update_item = items[6]
        if isinstance(update_item, list): # È un assign_stmt (lista di nodi)
            if len(update_item) == 1:
                update = update_item[0]
            else:
                update = BlockNode(update_item)
        else:
            update = update_item # È una espressione

        return ForNode(init, cond, update, items[9])

    # --- Funzioni ---

    def function_def(self, items):
        # items: [ACTION, ID, LPAR, param_list, RPAR, ARROW, return_type, block]
        return FunNode(str(items[1]), items[3], items[6], items[7])

    def param_list(self, items):
        # items: [param, COMMA, param...] o None
        if not items:
            return []
        params = []
        for item in items:
            if not isinstance(item, Token): # Ignora le virgole
                params.append(item)
        return params

    def param(self, items):
        # items: [type, ID]
        return ParamNode(str(items[0]), str(items[1]))

    def return_type(self, items):
        # items: [type] o [VOID]
        return str(items[0])

    def func_call_stmt(self, items):
        # items: [ID, LPAR, arg_list, RPAR]
        return FuncCallStmtNode(str(items[0]), items[2])

    def func_call_expr(self, items):
        return FunCallExprNode(str(items[0]), items[2])

    def arg_list(self, items):
        # items: [expr, COMMA, expr...] o None
        if not items:
            return []
        args = []
        for item in items:
            if not isinstance(item, Token):
                args.append(item)
        return args

    # --- Espressioni ---

    # Helper per gestire operazioni binarie (es. sum_expr, prod_expr)
    def _binary_op(self, items):
        if len(items) == 1:
            return items[0]
        
        left = items[0]
        # Itera a passi di 2: operatore, operando destro
        for i in range(1, len(items), 2):
            op = str(items[i])
            right = items[i+1]
            left = BinOpNode(left, op, right)
        return left

    def logic_expr(self, items): return self._binary_op(items)
    def comp_expr(self, items): return self._binary_op(items)
    def sum_expr(self, items): return self._binary_op(items)
    def prod_expr(self, items): return self._binary_op(items)

    def unary_expr(self, items):
        # items: [unary_op, unary_expr] oppure [base_expr]
        if len(items) == 1:
            return items[0]
        return UnaryOpNode(str(items[0]), items[1])

    def base_expr(self, items):
        first = items[0]
        # Gestione parentesi: LPAR expr RPAR
        if isinstance(first, Token) and first.type == 'LPAR':
            return items[1]
        
        # Gestione OUT_VAL ID (--> ID)
        if isinstance(first, Token) and first.type == 'OUT_VAL':
            return UnaryOpNode('-->', VarAccessNode(str(items[1])))

        # Gestione Literals e ID
        if isinstance(first, Token):
            if first.type == 'INTEGER_CONST':
                return LiteralNode(int(first.value), 'rank')
            elif first.type == 'REAL_CONST':
                return LiteralNode(float(first.value), 'rate')
            elif first.type == 'STRING_CONST':
                # Rimuove le virgolette "..."
                return LiteralNode(first.value[1:-1], 'label')
            elif first.type == 'ID':
                return VarAccessNode(str(first.value))
        
        # Altri casi (bool_const, func_call_expr) vengono restituiti direttamente
        return first

    def bool_const(self, items):
        # items: [TRUE] o [FALSE]
        val = (items[0].type == 'TRUE')
        return LiteralNode(val, 'flag')

    # Gestione operatori (ritornano la stringa del token)
    def logic_op(self, items): return str(items[0])
    def comp_op(self, items): return str(items[0])
    def sum_op(self, items): return str(items[0])
    def prod_op(self, items): return str(items[0])
    def unary_op(self, items): return str(items[0])