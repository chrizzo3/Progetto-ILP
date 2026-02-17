"""
LLVM Code Generator per il linguaggio Play.
Utilizza llvmlite per generare codice LLVM IR dall'AST.
"""

from llvmlite import ir
from ..frontend.ast_node import *


class LLVMCodeGenerator:
    """
    Generatore di codice LLVM per il linguaggio Play.
    Implementa il pattern Visitor per attraversare l'AST.
    """
    
    def __init__(self, module_name="play_module"):
        """
        Inizializza il generatore di codice LLVM.
        
        Args:
            module_name: Nome del modulo LLVM da creare
        """
        # Inizializza il modulo LLVM
        self.module = ir.Module(name=module_name)
        self.builder = None  # Verrà inizializzato quando necessario
        
        # Funzione corrente in compilazione
        self.current_function = None
        
        # Stack per gestire scope annidati (il primo elemento è lo scope globale)
        self.scope_stack = [{}]
        
        # Stack per gestire i blocchi di uscita dei loop (per break/quit)
        self.loop_exit_stack = []
        
        # Dimensione del buffer per le stringhe (label)
        self.STRING_BUFFER_SIZE = 256
        
        # Flag per tracciare se siamo in un contesto drop (per validare operatore -->)
        self.in_drop_context = False
        
        # Definizione delle funzioni di libreria C esterne
        self._declare_external_functions()
    
    def _declare_external_functions(self):
        """
        Dichiara le funzioni di libreria C esterne necessarie per I/O.
        """
        # printf: int printf(char* format, ...)
        # Tipo: i32 (i8*, ...)
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")
        
        # scanf: int scanf(char* format, ...)
        # Tipo: i32 (i8*, ...)
        scanf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.scanf = ir.Function(self.module, scanf_ty, name="scanf")
        
        # sprintf: int sprintf(char* str, char* format, ...)
        # Tipo: i32 (i8*, i8*, ...)
        sprintf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty, voidptr_ty], var_arg=True)
        self.sprintf = ir.Function(self.module, sprintf_ty, name="sprintf")
    
    def _get_llvm_type(self, play_type):
        """
        Mappa i tipi di Play ai tipi LLVM.
        
        Args:
            play_type: Tipo del linguaggio Play ('rank', 'rate', 'flag', 'label', 'void')
        
        Returns:
            Tipo LLVM corrispondente
        """
        type_mapping = {
            'rank': ir.IntType(32),      # int32
            'rate': ir.DoubleType(),     # double
            'flag': ir.IntType(1),       # bool (i1)
            'label': ir.IntType(8).as_pointer(),  # char* (string)
            'void': ir.VoidType()        # void
        }
        
        if play_type not in type_mapping:
            raise ValueError(f"Tipo sconosciuto: {play_type}")
        
        return type_mapping[play_type]
    
    def _get_play_type_from_llvm(self, llvm_type):
        """
        Determina il tipo Play corrispondente a un tipo LLVM.
        
        Args:
            llvm_type: Tipo LLVM
        
        Returns:
            Nome del tipo Play corrispondente
        """
        if isinstance(llvm_type, ir.IntType):
            if llvm_type.width == 32:
                return 'rank'
            elif llvm_type.width == 1:
                return 'flag'
        elif isinstance(llvm_type, ir.DoubleType):
            return 'rate'
        elif isinstance(llvm_type, ir.PointerType):
            if isinstance(llvm_type.pointee, ir.IntType) and llvm_type.pointee.width == 8:
                return 'label'
        
        return None
    
    def _cast_value(self, value, from_type, to_type):
        """
        Effettua il cast automatico di un valore tra tipi diversi.
        
        Args:
            value: Valore LLVM da convertire
            from_type: Tipo Play di origine
            to_type: Tipo Play di destinazione
        
        Returns:
            Valore convertito al tipo di destinazione
        """
        if from_type == to_type:
            return value
        
        # rank -> rate (int to double)
        if from_type == 'rank' and to_type == 'rate':
            return self.builder.sitofp(value, ir.DoubleType(), name="rank_to_rate")
        
        # rate -> rank (double to int, con troncamento)
        if from_type == 'rate' and to_type == 'rank':
            return self.builder.fptosi(value, ir.IntType(32), name="rate_to_rank")
        
        # rank -> flag (int to bool: 0 = false, != 0 = true)
        if from_type == 'rank' and to_type == 'flag':
            zero = ir.Constant(ir.IntType(32), 0)
            return self.builder.icmp_signed('!=', value, zero, name="rank_to_flag")
        
        # flag -> rank (bool to int: false = 0, true = 1)
        if from_type == 'flag' and to_type == 'rank':
            return self.builder.zext(value, ir.IntType(32), name="flag_to_rank")
        
        # rate -> flag (double to bool: 0.0 = false, != 0.0 = true)
        if from_type == 'rate' and to_type == 'flag':
            zero = ir.Constant(ir.DoubleType(), 0.0)
            return self.builder.fcmp_ordered('!=', value, zero, name="rate_to_flag")
        
        # flag -> rate (bool to double: false = 0.0, true = 1.0)
        if from_type == 'flag' and to_type == 'rate':
            int_val = self.builder.zext(value, ir.IntType(32), name="flag_to_int")
            return self.builder.sitofp(int_val, ir.DoubleType(), name="flag_to_rate")
        
        raise ValueError(f"Cast non supportato: {from_type} -> {to_type}")
    
    def _get_variable(self, name):
        """
        Recupera il puntatore di una variabile dalla symbol table.
        Cerca partendo dallo scope locale (ultimo nello stack) fino al globale (primo).
        
        Args:
            name: Nome della variabile
        
        Returns:
            Tupla (puntatore, tipo_play) della variabile
        
        Raises:
            NameError: Se la variabile non è stata dichiarata
        """
        # Cerca la variabile partendo dall'ultimo scope (locale) andando a ritroso fino al primo (globale)
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        
        raise NameError(f"Variabile '{name}' non dichiarata")
    
    def _create_global_string(self, string_value):
        """
        Crea una stringa globale costante e restituisce un puntatore i8*.
        
        Args:
            string_value: Stringa da creare come costante globale
        
        Returns:
            Puntatore i8* alla stringa globale
        """
        # Aggiungi null terminator
        string_bytes = bytearray(string_value.encode('utf-8') + b'\0')
        
        # Crea la costante stringa
        string_const = ir.Constant(
            ir.ArrayType(ir.IntType(8), len(string_bytes)),
            string_bytes
        )
        
        # Crea variabile globale
        global_str = ir.GlobalVariable(
            self.module,
            string_const.type,
            name=f".str.{len(self.module.globals)}"
        )
        global_str.linkage = 'internal'
        global_str.global_constant = True
        global_str.initializer = string_const
        
        # Restituisci puntatore al primo elemento (i8*)
        return self.builder.bitcast(global_str, ir.IntType(8).as_pointer())
    
    def _copy_string_to_buffer(self, source_ptr, dest_buffer_ptr, max_size):
        """
        Copia una stringa da source_ptr a dest_buffer_ptr.
        Implementa una copia manuale carattere per carattere.
        
        Args:
            source_ptr: Puntatore i8* alla stringa sorgente
            dest_buffer_ptr: Puntatore i8* al buffer di destinazione
            max_size: Dimensione massima del buffer
        """
        # Ottieni la funzione corrente
        current_func = self.builder.block.function
        
        # Crea i blocchi per il loop di copia
        loop_cond = current_func.append_basic_block(name="strcpy.cond")
        loop_body = current_func.append_basic_block(name="strcpy.body")
        loop_end = current_func.append_basic_block(name="strcpy.end")
        
        # Alloca un contatore per l'indice
        index_ptr = self.builder.alloca(ir.IntType(32), name="strcpy.index")
        self.builder.store(ir.Constant(ir.IntType(32), 0), index_ptr)
        
        # Salta al blocco condizione
        self.builder.branch(loop_cond)
        
        # Blocco condizione: controlla se abbiamo raggiunto il null terminator o il limite
        self.builder.position_at_end(loop_cond)
        index = self.builder.load(index_ptr, name="index")
        
        # Controlla se abbiamo raggiunto il limite del buffer
        max_index = ir.Constant(ir.IntType(32), max_size - 1)
        at_limit = self.builder.icmp_signed('>=', index, max_index, name="at_limit")
        
        # Calcola il puntatore al carattere corrente nella sorgente
        src_char_ptr = self.builder.gep(source_ptr, [index], name="src.char.ptr")
        src_char = self.builder.load(src_char_ptr, name="src.char")
        
        # Controlla se abbiamo raggiunto il null terminator
        null_char = ir.Constant(ir.IntType(8), 0)
        is_null = self.builder.icmp_signed('==', src_char, null_char, name="is_null")
        
        # Condizione: continua se non siamo al limite E non abbiamo raggiunto il null
        should_stop = self.builder.or_(at_limit, is_null, name="should_stop")
        self.builder.cbranch(should_stop, loop_end, loop_body)
        
        # Blocco body: copia il carattere
        self.builder.position_at_end(loop_body)
        index_body = self.builder.load(index_ptr, name="index.body")
        
        # Carica il carattere dalla sorgente
        src_char_ptr_body = self.builder.gep(source_ptr, [index_body], name="src.char.ptr.body")
        char_to_copy = self.builder.load(src_char_ptr_body, name="char.to.copy")
        
        # Memorizza nel buffer di destinazione
        dest_char_ptr = self.builder.gep(dest_buffer_ptr, [index_body], name="dest.char.ptr")
        self.builder.store(char_to_copy, dest_char_ptr)
        
        # Incrementa l'indice
        next_index = self.builder.add(index_body, ir.Constant(ir.IntType(32), 1), name="next.index")
        self.builder.store(next_index, index_ptr)
        
        # Torna alla condizione
        self.builder.branch(loop_cond)
        
        # Blocco end: aggiungi null terminator
        self.builder.position_at_end(loop_end)
        final_index = self.builder.load(index_ptr, name="final.index")
        dest_null_ptr = self.builder.gep(dest_buffer_ptr, [final_index], name="dest.null.ptr")
        self.builder.store(null_char, dest_null_ptr)
    
    def _concatenate_strings(self, str1_ptr, str2_ptr):
        """
        Concatena due stringhe usando sprintf.
        
        Args:
            str1_ptr: Puntatore i8* alla prima stringa
            str2_ptr: Puntatore i8* alla seconda stringa
        
        Returns:
            Puntatore i8* al buffer contenente la stringa concatenata
        """
        # Alloca buffer per il risultato (256 byte)
        buffer_type = ir.ArrayType(ir.IntType(8), self.STRING_BUFFER_SIZE)
        buffer_ptr = self.builder.alloca(buffer_type, name="concat.buffer")
        
        # Bitcast a i8*
        result_ptr = self.builder.bitcast(
            buffer_ptr, 
            ir.IntType(8).as_pointer(), 
            name="concat.result"
        )
        
        # Crea format string "%s%s"
        fmt = self._create_global_string("%s%s")
        
        # Chiama sprintf(result, "%s%s", str1, str2)
        self.builder.call(self.sprintf, [result_ptr, fmt, str1_ptr, str2_ptr])
        
        return result_ptr
    
    def _convert_bool_to_string(self, bool_value):
        """
        Converte un valore booleano (i1) in stringa "true" o "false".
        Usa un if-else per selezionare la stringa corretta.
        
        Args:
            bool_value: Valore LLVM di tipo i1 (flag)
        
        Returns:
            Puntatore i8* alla stringa "true" o "false"
        """
        # Crea le stringhe globali per "true" e "false"
        true_str = self._create_global_string("true")
        false_str = self._create_global_string("false")
        
        # Crea i blocchi per if-then-else
        current_func = self.builder.block.function
        then_block = current_func.append_basic_block(name="bool.true")
        else_block = current_func.append_basic_block(name="bool.false")
        merge_block = current_func.append_basic_block(name="bool.merge")
        
        # Alloca spazio per memorizzare il risultato (puntatore alla stringa)
        result_ptr = self.builder.alloca(ir.IntType(8).as_pointer(), name="bool.result.ptr")
        
        # Branch condizionale
        self.builder.cbranch(bool_value, then_block, else_block)
        
        # Blocco then: memorizza puntatore a "true"
        self.builder.position_at_end(then_block)
        self.builder.store(true_str, result_ptr)
        self.builder.branch(merge_block)
        
        # Blocco else: memorizza puntatore a "false"
        self.builder.position_at_end(else_block)
        self.builder.store(false_str, result_ptr)
        self.builder.branch(merge_block)
        
        # Blocco merge: carica e restituisci il risultato
        self.builder.position_at_end(merge_block)
        return self.builder.load(result_ptr, name="bool.str")
    
    def visit(self, node):
        """
        Metodo principale del pattern Visitor.
        Effettua il dispatching dinamico al metodo visit_NomeNodo appropriato.
        
        Args:
            node: Nodo AST da visitare
        
        Returns:
            Risultato della visita (dipende dal tipo di nodo)
        """
        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        """
        Metodo di fallback per nodi non implementati.
        """
        raise NotImplementedError(
            f"Nessun metodo visit_{node.__class__.__name__} implementato"
        )
    
    def visit_ProgramNode(self, node):
        """
        Visita il nodo radice del programma.
        Crea una funzione main implicita e visita il blocco principale.
        
        Args:
            node: ProgramNode contenente dichiarazioni globali, funzioni e main_block
        """
        # Visita le dichiarazioni globali
        for global_decl in node.global_decls:
            self.visit(global_decl)
        
        # Visita le funzioni definite dall'utente
        for function in node.functions:
            self.visit(function)
        
        # Crea la funzione main implicita
        # Tipo: int main()
        main_type = ir.FunctionType(ir.IntType(32), [])
        main_func = ir.Function(self.module, main_type, name="main")
        
        # Crea il blocco d'ingresso della funzione main
        entry_block = main_func.append_basic_block(name="entry")
        
        # Inizializza il builder nel blocco d'ingresso
        self.builder = ir.IRBuilder(entry_block)
        
        # Imposta la funzione corrente
        self.current_function = main_func
        
        # Push di un nuovo scope locale per il main
        self.scope_stack.append({})
        
        # Visita il blocco principale del programma
        self.visit(node.main_block)
        
        # Pop dello scope del main
        self.scope_stack.pop()
        
        # Aggiungi return 0 alla fine del main se il blocco corrente non è terminato
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(ir.IntType(32), 0))
    
    def visit_BlockNode(self, node):
        """
        Visita un blocco di statement.
        Itera su tutti gli statement contenuti nel blocco.
        
        Args:
            node: BlockNode contenente una lista di statement
        """
        for statement in node.statements:
            self.visit(statement)
    
    def visit_VarDeclNode(self, node):
        """
        Visita una dichiarazione di variabile.
        Crea una GlobalVariable se siamo in scope globale, altrimenti alloca sullo stack.
        Per le variabili label (stringhe), alloca un buffer scrivibile.
        
        Args:
            node: VarDeclNode contenente tipo e lista di variabili da dichiarare
        """
        # Ottieni il tipo LLVM corrispondente
        llvm_type = self._get_llvm_type(node.type_name)
        
        # Determina se siamo in scope globale
        is_global_scope = (self.builder is None or self.current_function is None)
        
        # Per ogni variabile nella lista
        for var_init in node.var_list:
            var_name = var_init.name
            
            if is_global_scope:
                # Crea una variabile globale nel modulo
                # Determina il valore iniziale costante
                if var_init.expr is not None and isinstance(var_init.expr, LiteralNode):
                    # Per le variabili globali con literal, usa il valore dal literal
                    if var_init.expr.type_tag in ('int', 'rank'):
                        initializer = ir.Constant(ir.IntType(32), int(var_init.expr.value))
                    elif var_init.expr.type_tag in ('float', 'rate'):
                        initializer = ir.Constant(ir.DoubleType(), float(var_init.expr.value))
                    elif var_init.expr.type_tag in ('bool', 'flag'):
                        bool_val = 1 if var_init.expr.value in (True, 'true', 'True', 1) else 0
                        initializer = ir.Constant(ir.IntType(1), bool_val)
                    elif var_init.expr.type_tag in ('string', 'label'):
                        # Per le stringhe globali, crea un array inizializzato con il valore
                        string_val = str(var_init.expr.value)
                        buffer_bytes = bytearray(string_val.encode('utf-8') + b'\0')
                        # Pad to STRING_BUFFER_SIZE
                        buffer_bytes.extend(b'\0' * (self.STRING_BUFFER_SIZE - len(buffer_bytes)))
                        buffer_type = ir.ArrayType(ir.IntType(8), self.STRING_BUFFER_SIZE)
                        initializer = ir.Constant(buffer_type, buffer_bytes)
                        global_var = ir.GlobalVariable(self.module, buffer_type, name=var_name)
                        global_var.initializer = initializer
                        global_var.linkage = 'internal'
                        self.scope_stack[0][var_name] = (global_var, node.type_name)
                        continue
                    else:
                        # Non literal o tipo sconosciuto, usa default
                        initializer = None
                else:
                    initializer = None
                
                # Se non abbiamo un initializer, usa valori di default
                if initializer is None:
                    if node.type_name == 'rank':
                        initializer = ir.Constant(ir.IntType(32), 0)
                    elif node.type_name == 'rate':
                        initializer = ir.Constant(ir.DoubleType(), 0.0)
                    elif node.type_name == 'flag':
                        initializer = ir.Constant(ir.IntType(1), 0)
                    elif node.type_name == 'label':
                        # Per le stringhe globali, crea un array di char invece di un puntatore
                        buffer_type = ir.ArrayType(ir.IntType(8), self.STRING_BUFFER_SIZE)
                        initializer = ir.Constant(buffer_type, bytearray(self.STRING_BUFFER_SIZE))
                        global_var = ir.GlobalVariable(self.module, buffer_type, name=var_name)
                        global_var.initializer = initializer
                        global_var.linkage = 'internal'
                        self.scope_stack[0][var_name] = (global_var, node.type_name)
                        continue
                    else:
                        continue  # void non ha valore di default
                
                # Crea la variabile globale
                global_var = ir.GlobalVariable(self.module, llvm_type, name=var_name)
                global_var.initializer = initializer
                global_var.linkage = 'internal'  # Visibilità interna al modulo
                
                # Registra nella symbol table (scope globale = primo elemento dello stack)
                self.scope_stack[0][var_name] = (global_var, node.type_name)
            else:
                # Siamo in una funzione: alloca sullo stack
                # Per le variabili label, alloca un buffer di char invece di un semplice puntatore
                with self.builder.goto_entry_block():
                    if node.type_name == 'label':
                        # Alloca un array di char [256 x i8] per il buffer scrivibile
                        buffer_type = ir.ArrayType(ir.IntType(8), self.STRING_BUFFER_SIZE)
                        buffer_ptr = self.builder.alloca(buffer_type, name=f"{var_name}.buffer")
                        
                        # Bitcast dell'array a i8* per compatibilità con printf/scanf
                        var_ptr = self.builder.bitcast(buffer_ptr, ir.IntType(8).as_pointer(), name=var_name)
                    else:
                        var_ptr = self.builder.alloca(llvm_type, name=var_name)
                
                # Salva il puntatore e il tipo nello scope corrente (ultimo nello stack)
                self.scope_stack[-1][var_name] = (var_ptr, node.type_name)
                
                # Se c'è un'inizializzazione, visita l'espressione e assegna il valore
                if var_init.expr is not None:
                    # Visita l'espressione di inizializzazione
                    init_value = self.visit(var_init.expr)
                    
                    # Determina il tipo dell'espressione
                    expr_type = self._get_play_type_from_llvm(init_value.type)
                    
                    # Per le stringhe, usa la copia invece di store diretto
                    if node.type_name == 'label' and expr_type == 'label':
                        self._copy_string_to_buffer(init_value, var_ptr, self.STRING_BUFFER_SIZE)
                    else:
                        # Effettua il cast se necessario
                        if expr_type != node.type_name:
                            init_value = self._cast_value(init_value, expr_type, node.type_name)
                        
                        # Memorizza il valore nella variabile
                        self.builder.store(init_value, var_ptr)
                else:
                    # Inizializza con valore di default
                    if node.type_name == 'rank':
                        default_value = ir.Constant(ir.IntType(32), 0)
                        self.builder.store(default_value, var_ptr)
                    elif node.type_name == 'rate':
                        default_value = ir.Constant(ir.DoubleType(), 0.0)
                        self.builder.store(default_value, var_ptr)
                    elif node.type_name == 'flag':
                        default_value = ir.Constant(ir.IntType(1), 0)
                        self.builder.store(default_value, var_ptr)
                    elif node.type_name == 'label':
                        # Inizializza il buffer con una stringa vuota (solo null terminator)
                        null_char = ir.Constant(ir.IntType(8), 0)
                        first_char_ptr = self.builder.gep(var_ptr, [ir.Constant(ir.IntType(32), 0)], name="first.char")
                        self.builder.store(null_char, first_char_ptr)
    
    def visit_AssignNode(self, node):
        """
        Visita un'assegnazione.
        Valuta l'espressione e memorizza il risultato nella variabile target.
        Per le stringhe (label), copia il contenuto nel buffer invece di sovrascrivere il puntatore.
        
        Args:
            node: AssignNode contenente target (nome variabile) ed espressione
        """
        # Recupera il puntatore della variabile target
        var_ptr, var_type = self._get_variable(node.target)
        
        # Visita l'espressione da assegnare
        value = self.visit(node.expr)
        
        # Determina il tipo dell'espressione
        expr_type = self._get_play_type_from_llvm(value.type)
        
        # Per le stringhe, usa la copia nel buffer
        if var_type == 'label' and expr_type == 'label':
            # Gestisci il caso delle variabili globali (array) vs locali (puntatore)
            # Per le globali, potrebbe essere necessario un bitcast
            if isinstance(var_ptr.type.pointee, ir.ArrayType):
                # Variabile globale: bitcast dell'array a i8*
                buffer_ptr = self.builder.bitcast(var_ptr, ir.IntType(8).as_pointer(), name="global.str.ptr")
                self._copy_string_to_buffer(value, buffer_ptr, self.STRING_BUFFER_SIZE)
            else:
                # Variabile locale: già un i8*
                self._copy_string_to_buffer(value, var_ptr, self.STRING_BUFFER_SIZE)
        else:
            # Effettua il cast se necessario
            if expr_type != var_type:
                value = self._cast_value(value, expr_type, var_type)
            
            # Memorizza il valore nella variabile
            self.builder.store(value, var_ptr)
    
    def visit_VarAccessNode(self, node):
        """
        Visita un accesso a variabile.
        Carica il valore della variabile dalla memoria.
        Per le stringhe (label), restituisce il puntatore senza caricare.
        
        Args:
            node: VarAccessNode contenente il nome della variabile
        
        Returns:
            Valore LLVM caricato dalla variabile o puntatore per label
        """
        # Recupera il puntatore della variabile
        var_ptr, var_type = self._get_variable(node.name)
        
        # Per le label (stringhe), restituisci il puntatore senza caricare
        if var_type == 'label':
            # Per le stringhe globali (array), bitcast a i8*
            if isinstance(var_ptr.type.pointee, ir.ArrayType):
                return self.builder.bitcast(var_ptr, ir.IntType(8).as_pointer(), name=f"{node.name}.ptr")
            else:
                # Per le stringhe locali, var_ptr è già il risultato del bitcast (i8*)
                # Restituisci direttamente senza load
                return var_ptr
        
        # Carica il valore dalla memoria per tutti gli altri tipi
        return self.builder.load(var_ptr, name=node.name)
    
    def visit_LiteralNode(self, node):
        """
        Visita un nodo letterale.
        Restituisce una costante LLVM del tipo appropriato.
        
        Args:
            node: LiteralNode contenente valore e type_tag
        
        Returns:
            Costante LLVM
        """
        # Gestisci sia i tag letterali (int, float, bool, string) 
        # che i tipi Play (rank, rate, flag, label) per compatibilità
        if node.type_tag in ('int', 'rank'):
            return ir.Constant(ir.IntType(32), int(node.value))
        elif node.type_tag in ('float', 'rate'):
            return ir.Constant(ir.DoubleType(), float(node.value))
        elif node.type_tag in ('bool', 'flag'):
            # Converti true/false in 1/0
            bool_val = 1 if node.value in (True, 'true', 'True', 1) else 0
            return ir.Constant(ir.IntType(1), bool_val)
        elif node.type_tag in ('string', 'label'):
            # Per ora restituiamo un puntatore a stringa globale
            string_val = str(node.value)
            # Crea una costante stringa globale
            string_const = ir.Constant(ir.ArrayType(ir.IntType(8), len(string_val) + 1),
                                      bytearray(string_val.encode('utf-8') + b'\0'))
            global_str = ir.GlobalVariable(self.module, string_const.type, 
                                          name=f".str.{len(self.module.globals)}")
            global_str.linkage = 'internal'
            global_str.global_constant = True
            global_str.initializer = string_const
            # Restituisci puntatore al primo elemento
            return self.builder.bitcast(global_str, ir.IntType(8).as_pointer())
        else:
            raise ValueError(f"Tipo letterale sconosciuto: {node.type_tag}")
    
    def visit_BinOpNode(self, node):
        """
        Visita un'operazione binaria.
        Gestisce aritmetica, logica e confronti con promozione implicita dei tipi.
        
        Args:
            node: BinOpNode contenente left, op, right
        
        Returns:
            Risultato dell'operazione binaria
        """
        # Valuta gli operandi
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        # Determina i tipi degli operandi
        left_type = self._get_play_type_from_llvm(left.type)
        right_type = self._get_play_type_from_llvm(right.type)
        
        # Promozione implicita: se uno è float e l'altro int, converti int in float
        if left_type == 'rate' and right_type == 'rank':
            right = self._cast_value(right, 'rank', 'rate')
            right_type = 'rate'
        elif left_type == 'rank' and right_type == 'rate':
            left = self._cast_value(left, 'rank', 'rate')
            left_type = 'rate'
        
        # Determina se stiamo operando su float o int
        is_float = (left_type == 'rate' or right_type == 'rate')
        
        # Operazioni aritmetiche
        if node.op == '+':
            # Caso speciale: concatenazione stringhe
            if left_type == 'label' and right_type == 'label':
                return self._concatenate_strings(left, right)
            
            # Aritmetica
            if is_float:
                return self.builder.fadd(left, right, name="fadd_tmp")
            else:
                return self.builder.add(left, right, name="add_tmp")
        
        elif node.op == '-':
            if is_float:
                return self.builder.fsub(left, right, name="fsub_tmp")
            else:
                return self.builder.sub(left, right, name="sub_tmp")
        
        elif node.op == '*':
            if is_float:
                return self.builder.fmul(left, right, name="fmul_tmp")
            else:
                return self.builder.mul(left, right, name="mul_tmp")
        
        elif node.op == '/':
            if is_float:
                return self.builder.fdiv(left, right, name="fdiv_tmp")
            else:
                # Divisione intera con segno
                return self.builder.sdiv(left, right, name="sdiv_tmp")
        
        elif node.op == '%':
            if is_float:
                return self.builder.frem(left, right, name="frem_tmp")
            else:
                return self.builder.srem(left, right, name="srem_tmp")
        
        # Operazioni logiche (&&, ||)
        elif node.op == '&&':
            # Converti a bool se necessario
            if left_type != 'flag':
                left = self._cast_value(left, left_type, 'flag')
            if right_type != 'flag':
                right = self._cast_value(right, right_type, 'flag')
            return self.builder.and_(left, right, name="and_tmp")
        
        elif node.op == '||':
            # Converti a bool se necessario
            if left_type != 'flag':
                left = self._cast_value(left, left_type, 'flag')
            if right_type != 'flag':
                right = self._cast_value(right, right_type, 'flag')
            return self.builder.or_(left, right, name="or_tmp")
        
        # Operazioni di confronto
        elif node.op == '<':
            if is_float:
                return self.builder.fcmp_ordered('<', left, right, name="flt_tmp")
            else:
                return self.builder.icmp_signed('<', left, right, name="lt_tmp")
        
        elif node.op == '<=':
            if is_float:
                return self.builder.fcmp_ordered('<=', left, right, name="fle_tmp")
            else:
                return self.builder.icmp_signed('<=', left, right, name="le_tmp")
        
        elif node.op == '>':
            if is_float:
                return self.builder.fcmp_ordered('>', left, right, name="fgt_tmp")
            else:
                return self.builder.icmp_signed('>', left, right, name="gt_tmp")
        
        elif node.op == '>=':
            if is_float:
                return self.builder.fcmp_ordered('>=', left, right, name="fge_tmp")
            else:
                return self.builder.icmp_signed('>=', left, right, name="ge_tmp")
        
        elif node.op == '==':
            if is_float:
                return self.builder.fcmp_ordered('==', left, right, name="feq_tmp")
            else:
                return self.builder.icmp_signed('==', left, right, name="eq_tmp")
        
        elif node.op == '<>':
            if is_float:
                return self.builder.fcmp_ordered('!=', left, right, name="fne_tmp")
            else:
                return self.builder.icmp_signed('!=', left, right, name="ne_tmp")
        
        else:
            raise ValueError(f"Operatore binario non supportato: {node.op}")
    
    def visit_UnaryOpNode(self, node):
        """
        Visita un'operazione unaria.
        Gestisce negazione aritmetica e logica.
        
        Args:
            node: UnaryOpNode contenente op ed expr
        
        Returns:
            Risultato dell'operazione unaria
        """
        # Valuta l'operando
        expr = self.visit(node.expr)
        expr_type = self._get_play_type_from_llvm(expr.type)
        
        # Negazione aritmetica
        if node.op == '-':
            if expr_type == 'rate':
                return self.builder.fsub(
                    ir.Constant(ir.DoubleType(), 0.0),
                    expr,
                    name="fneg_tmp"
                )
            elif expr_type == 'rank':
                return self.builder.sub(
                    ir.Constant(ir.IntType(32), 0),
                    expr,
                    name="neg_tmp"
                )
            else:
                raise ValueError(f"Negazione non supportata per tipo {expr_type}")
        
        # Positivo unario (no-op)
        elif node.op == '+':
            return expr
        
        # Negazione logica
        elif node.op == '!':
            # Converti a bool se necessario
            if expr_type != 'flag':
                expr = self._cast_value(expr, expr_type, 'flag')
            # NOT logico: xor con 1
            return self.builder.xor(
                expr,
                ir.Constant(ir.IntType(1), 1),
                name="not_tmp"
            )
        
        # Operatore freccia (conversione a stringa)
        elif node.op == '-->':
            # VALIDAZIONE: --> può essere usato solo in drop
            if not self.in_drop_context:
                raise RuntimeError(
                    "L'operatore '-->' può essere usato solo all'interno di 'drop'. "
                    "Trovato in un contesto non valido."
                )
            
            # Converte un valore (rank, rate, flag, label) in stringa usando sprintf
            
            # Debug: verifica che expr_type non sia None
            if expr_type is None:
                raise ValueError(
                    f"Impossibile determinare il tipo dell'espressione per -->. "
                    f"Tipo LLVM: {expr.type}, Espressione: {type(node.expr).__name__}"
                )
            
            # Se è già una stringa, ritorna così com'è
            if expr_type == 'label':
                return expr
            
            # Alloca buffer per la stringa risultante
            buffer_type = ir.ArrayType(ir.IntType(8), self.STRING_BUFFER_SIZE)
            buffer_ptr = self.builder.alloca(buffer_type, name="value_to_string.buffer")
            
            # Bitcast dell'array a i8* per compatibilità con sprintf
            str_ptr = self.builder.bitcast(buffer_ptr, ir.IntType(8).as_pointer(), name="value_to_string")
            
            # Determina format string e chiama sprintf
            if expr_type == 'rank':
                # Converti intero a stringa
                fmt = self._create_global_string("%d")
                self.builder.call(self.sprintf, [str_ptr, fmt, expr])
            elif expr_type == 'rate':
                # Converti double a stringa
                fmt = self._create_global_string("%f")
                self.builder.call(self.sprintf, [str_ptr, fmt, expr])
            elif expr_type == 'flag':
                # Converti bool a stringa ("true" o "false")
                return self._convert_bool_to_string(expr)
            else:
                raise ValueError(f"Operatore --> non supportato per tipo {expr_type}")
            
            # Restituisci il puntatore alla stringa
            return str_ptr
        
        else:
            raise ValueError(f"Operatore unario non supportato: {node.op}")
    
    def visit_IfNode(self, node):
        """
        Visita un nodo if con supporto per elif ed else.
        Crea blocchi separati per then, elif, else e merge.
        
        Args:
            node: IfNode contenente condition, then_block, elifs, else_block
        """
        # Valuta la condizione
        condition = self.visit(node.condition)
        
        # Converti a bool se necessario
        cond_type = self._get_play_type_from_llvm(condition.type)
        if cond_type != 'flag':
            condition = self._cast_value(condition, cond_type, 'flag')
        
        # Ottieni la funzione corrente
        current_func = self.builder.block.function
        
        # Crea i blocchi
        then_block = current_func.append_basic_block(name="if.then")
        merge_block = current_func.append_basic_block(name="if.merge")
        
        # Se ci sono elif o else, creiamo il blocco else, altrimenti saltiamo al merge
        if node.elifs or node.else_block:
            else_block = current_func.append_basic_block(name="if.else")
            self.builder.cbranch(condition, then_block, else_block)
        else:
            self.builder.cbranch(condition, then_block, merge_block)
        
        # Genera codice per il blocco then
        self.builder.position_at_end(then_block)
        self.visit(node.then_block)
        # Salta al merge se il blocco non è già terminato
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
        
        # Gestisci elif ed else
        if node.elifs or node.else_block:
            self.builder.position_at_end(else_block)
            
            # Processa gli elif come una catena di if annidati
            if node.elifs:
                current_else = else_block
                for elif_node in node.elifs:
                    # Valuta la condizione elif
                    elif_cond = self.visit(elif_node.condition)
                    elif_cond_type = self._get_play_type_from_llvm(elif_cond.type)
                    if elif_cond_type != 'flag':
                        elif_cond = self._cast_value(elif_cond, elif_cond_type, 'flag')
                    
                    # Crea blocchi per questo elif
                    elif_then = current_func.append_basic_block(name="elif.then")
                    elif_else = current_func.append_basic_block(name="elif.else")
                    
                    self.builder.cbranch(elif_cond, elif_then, elif_else)
                    
                    # Genera codice per il blocco elif
                    self.builder.position_at_end(elif_then)
                    self.visit(elif_node.block)
                    if not self.builder.block.is_terminated:
                        self.builder.branch(merge_block)
                    
                    # Continua con il prossimo elif o else
                    self.builder.position_at_end(elif_else)
                    current_else = elif_else
            
            # Gestisci il blocco else finale
            if node.else_block:
                self.visit(node.else_block)
                if not self.builder.block.is_terminated:
                    self.builder.branch(merge_block)
            else:
                # Se non c'è else, salta al merge
                if not self.builder.block.is_terminated:
                    self.builder.branch(merge_block)
        
        # Posiziona il builder sul blocco merge
        self.builder.position_at_end(merge_block)
    
    def visit_WhileNode(self, node):
        """
        Visita un nodo while (Stay in Play).
        Crea blocchi per condizione, corpo e uscita.
        
        Args:
            node: WhileNode contenente condition e block
        """
        # Ottieni la funzione corrente
        current_func = self.builder.block.function
        
        # Crea i blocchi
        cond_block = current_func.append_basic_block(name="while.cond")
        body_block = current_func.append_basic_block(name="while.body")
        after_block = current_func.append_basic_block(name="while.after")
        
        # Aggiungi il blocco di uscita allo stack per gestire break
        self.loop_exit_stack.append(after_block)
        
        # Salta incondizionatamente al blocco condizione
        self.builder.branch(cond_block)
        
        # Genera codice per il blocco condizione
        self.builder.position_at_end(cond_block)
        condition = self.visit(node.condition)
        
        # Converti a bool se necessario
        cond_type = self._get_play_type_from_llvm(condition.type)
        if cond_type != 'flag':
            condition = self._cast_value(condition, cond_type, 'flag')
        
        # Branch condizionale: se true vai al body, altrimenti esci
        self.builder.cbranch(condition, body_block, after_block)
        
        # Genera codice per il corpo del loop
        self.builder.position_at_end(body_block)
        self.visit(node.block)
        
        # Torna alla condizione se il blocco non è già terminato
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        
        # Rimuovi il blocco di uscita dallo stack
        self.loop_exit_stack.pop()
        
        # Posiziona il builder sul blocco after
        self.builder.position_at_end(after_block)
    
    def visit_ForNode(self, node):
        """
        Visita un nodo for (Loop in Play).
        Crea blocchi per inizializzazione, condizione, corpo, update e uscita.
        
        Args:
            node: ForNode contenente init, condition, update, block
        """
        # Ottieni la funzione corrente
        current_func = self.builder.block.function
        
        # Esegui l'inizializzazione nel blocco corrente
        if node.init:
            self.visit(node.init)
        
        # Crea i blocchi
        cond_block = current_func.append_basic_block(name="for.cond")
        body_block = current_func.append_basic_block(name="for.body")
        update_block = current_func.append_basic_block(name="for.update")
        after_block = current_func.append_basic_block(name="for.after")
        
        # Aggiungi il blocco di uscita allo stack per gestire break
        self.loop_exit_stack.append(after_block)
        
        # Salta incondizionatamente al blocco condizione
        self.builder.branch(cond_block)
        
        # Genera codice per il blocco condizione
        self.builder.position_at_end(cond_block)
        if node.condition:
            condition = self.visit(node.condition)
            
            # Converti a bool se necessario
            cond_type = self._get_play_type_from_llvm(condition.type)
            if cond_type != 'flag':
                condition = self._cast_value(condition, cond_type, 'flag')
            
            # Branch condizionale
            self.builder.cbranch(condition, body_block, after_block)
        else:
            # Se non c'è condizione, loop infinito
            self.builder.branch(body_block)
        
        # Genera codice per il corpo del loop
        self.builder.position_at_end(body_block)
        self.visit(node.block)
        
        # Vai al blocco update se il blocco non è già terminato
        if not self.builder.block.is_terminated:
            self.builder.branch(update_block)
        
        # Genera codice per l'update
        self.builder.position_at_end(update_block)
        if node.update:
            self.visit(node.update)
        
        # Torna alla condizione
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        
        # Rimuovi il blocco di uscita dallo stack
        self.loop_exit_stack.pop()
        
        # Posiziona il builder sul blocco after
        self.builder.position_at_end(after_block)
    
    def visit_BreakNode(self, node):
        """
        Visita un nodo break (Quit in Play).
        Salta al blocco di uscita del loop più interno.
        
        Args:
            node: BreakNode
        """
        if not self.loop_exit_stack:
            raise RuntimeError("Break/Quit usato fuori da un loop")
        
        # Salta al blocco di uscita del loop più interno
        exit_block = self.loop_exit_stack[-1]
        self.builder.branch(exit_block)
    
    def visit_ReturnNode(self, node):
        """
        Visita un nodo return (Reward in Play).
        Genera istruzione di ritorno con valore opzionale.
        
        Args:
            node: ReturnNode contenente expr opzionale
        """
        if node.expr:
            # Valuta l'espressione di ritorno
            ret_value = self.visit(node.expr)
            self.builder.ret(ret_value)
        else:
            # Return void
            self.builder.ret_void()
    
    def visit_OutputNode(self, node):
        """
        Visita un nodo output (Drop in Play).
        Stampa l'espressione usando printf.
        I valori non-label vengono automaticamente convertiti in stringa.
        
        Args:
            node: OutputNode contenente expr da stampare
        """
        # ATTIVA CONTESTO DROP: l'operatore --> può essere usato qui
        old_drop_context = self.in_drop_context
        self.in_drop_context = True
        
        try:
            # Valuta l'espressione
            value = self.visit(node.expr)
            value_type = self._get_play_type_from_llvm(value.type)
            
            # Se non è già una stringa, converti automaticamente
            if value_type != 'label':
                # Converti in base al tipo
                if value_type == 'rank':
                    # Alloca buffer per la stringa risultante
                    buffer_type = ir.ArrayType(ir.IntType(8), self.STRING_BUFFER_SIZE)
                    buffer_ptr = self.builder.alloca(buffer_type, name="literal_to_string.buffer")
                    str_ptr = self.builder.bitcast(buffer_ptr, ir.IntType(8).as_pointer(), name="literal_to_string")
                    
                    fmt = self._create_global_string("%d")
                    self.builder.call(self.sprintf, [str_ptr, fmt, value])
                    value = str_ptr
                    
                elif value_type == 'rate':
                    # Alloca buffer per la stringa risultante
                    buffer_type = ir.ArrayType(ir.IntType(8), self.STRING_BUFFER_SIZE)
                    buffer_ptr = self.builder.alloca(buffer_type, name="literal_to_string.buffer")
                    str_ptr = self.builder.bitcast(buffer_ptr, ir.IntType(8).as_pointer(), name="literal_to_string")
                    
                    fmt = self._create_global_string("%f")
                    self.builder.call(self.sprintf, [str_ptr, fmt, value])
                    value = str_ptr
                    
                elif value_type == 'flag':
                    # Converti bool a stringa ("true" o "false")
                    # _convert_bool_to_string già restituisce il puntatore alla stringa
                    value = self._convert_bool_to_string(value)
                    
                else:
                    raise ValueError(f"Tipo non supportato per output: {value_type}")
            
            # Stampa la stringa (ora value è sempre di tipo label/i8*)
            fmt = self._create_global_string("%s\n")
            self.builder.call(self.printf, [fmt, value])
        finally:
            # RIPRISTINA CONTESTO: disattiva il contesto drop
            self.in_drop_context = old_drop_context
    
    
    
    
    def visit_InputNode(self, node):
        """
        Visita un nodo input (Grab in Play).
        Legge valori usando scanf e li memorizza nelle variabili target.
        
        Args:
            node: InputNode contenente target_groups e prompt_expr
        """
        # Se c'è un prompt, stampalo prima
        if node.prompt_expr:
            prompt_value = self.visit(node.prompt_expr)
            prompt_type = self._get_play_type_from_llvm(prompt_value.type)
            
            if prompt_type == 'label':
                fmt = self._create_global_string("%s")
                self.builder.call(self.printf, [fmt, prompt_value])
        
        # Per ogni gruppo di variabili (chain)
        for target_chain in node.target_groups:
            # In Play, ogni chain è una lista di nomi di variabili
            # Per semplicità, processiamo ogni variabile separatamente
            for var_name in target_chain:
                # Recupera il puntatore della variabile
                var_ptr, var_type = self._get_variable(var_name)
                
                # Crea format string appropriata per scanf
                if var_type == 'rank':
                    fmt = self._create_global_string("%d")
                elif var_type == 'rate':
                    fmt = self._create_global_string("%lf")  # scanf usa %lf per double
                elif var_type == 'flag':
                    fmt = self._create_global_string("%d")
                elif var_type == 'label':
                    # Per stringhe, usiamo %s ma dobbiamo gestire il buffer
                    # Per ora assumiamo che la variabile sia già un puntatore
                    fmt = self._create_global_string("%s")
                else:
                    raise ValueError(f"Tipo non supportato per input: {var_type}")
                
                # Chiama scanf passando il puntatore della variabile
                # IMPORTANTE: scanf richiede il puntatore, non il valore
                self.builder.call(self.scanf, [fmt, var_ptr])
    
    def visit_FunNode(self, node):
        """
        Visita una definizione di funzione.
        Crea la funzione LLVM con argomenti mutabili tramite alloca.
        Usa scope_stack per gestire la visibilità delle variabili globali.
        
        Args:
            node: FunNode contenente name, params, ret_type, body
        """
        # Determina il tipo di ritorno
        ret_llvm_type = self._get_llvm_type(node.ret_type)
        
        # Determina i tipi dei parametri
        param_types = [self._get_llvm_type(param.type_name) for param in node.params]
        
        # Crea il tipo della funzione
        func_type = ir.FunctionType(ret_llvm_type, param_types)
        
        # Crea la funzione nel modulo
        func = ir.Function(self.module, func_type, name=node.name)
        
        # Salva il builder e la funzione correnti
        old_builder = self.builder
        old_function = self.current_function
        
        # Imposta la funzione corrente
        self.current_function = func
        
        # Push di un nuovo scope locale nello stack (le variabili globali rimangono visibili)
        self.scope_stack.append({})
        
        # Crea il blocco di ingresso
        entry_block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)
        
        # Gestisci gli argomenti: crea alloca per renderli mutabili
        for i, (param, param_node) in enumerate(zip(func.args, node.params)):
            # Imposta il nome dell'argomento LLVM
            param.name = param_node.name
            
            # Alloca spazio sullo stack per l'argomento
            param_ptr = self.builder.alloca(param.type, name=f"{param_node.name}.addr")
            
            # Memorizza il valore dell'argomento nello spazio allocato
            self.builder.store(param, param_ptr)
            
            # Registra il puntatore nello scope locale (ultimo nello stack)
            self.scope_stack[-1][param_node.name] = (param_ptr, param_node.type_name)
        
        # Visita il corpo della funzione
        self.visit(node.body)
        
        # Assicurati che la funzione termini correttamente
        if not self.builder.block.is_terminated:
            if node.ret_type == 'void':
                self.builder.ret_void()
            else:
                # Aggiungi un valore di default per sicurezza
                if node.ret_type == 'rank':
                    self.builder.ret(ir.Constant(ir.IntType(32), 0))
                elif node.ret_type == 'rate':
                    self.builder.ret(ir.Constant(ir.DoubleType(), 0.0))
                elif node.ret_type == 'flag':
                    self.builder.ret(ir.Constant(ir.IntType(1), 0))
                elif node.ret_type == 'label':
                    # Restituisci puntatore null
                    self.builder.ret(ir.Constant(ir.IntType(8).as_pointer(), None))
        
        # Pop dello scope locale
        self.scope_stack.pop()
        
        # Ripristina il builder e la funzione precedenti
        self.builder = old_builder
        self.current_function = old_function
    
    def visit_FunCallExprNode(self, node):
        """
        Visita una chiamata di funzione come espressione.
        Restituisce il valore di ritorno della funzione.
        
        Args:
            node: FunCallExprNode contenente name e args
        
        Returns:
            Valore di ritorno della funzione chiamata
        """
        # Cerca la funzione nel modulo
        func = None
        for f in self.module.functions:
            if f.name == node.name:
                func = f
                break
        
        if func is None:
            raise NameError(f"Funzione '{node.name}' non definita")
        
        # Valuta gli argomenti
        args = [self.visit(arg) for arg in node.args]
        
        # Verifica il numero di argomenti
        if len(args) != len(func.args):
            raise TypeError(
                f"Funzione '{node.name}' richiede {len(func.args)} argomenti, "
                f"ma ne sono stati forniti {len(args)}"
            )
        
        # Effettua eventuali cast necessari per gli argomenti
        casted_args = []
        for i, (arg, param) in enumerate(zip(args, func.args)):
            arg_type = self._get_play_type_from_llvm(arg.type)
            param_type = self._get_play_type_from_llvm(param.type)
            
            if arg_type != param_type:
                arg = self._cast_value(arg, arg_type, param_type)
            
            casted_args.append(arg)
        
        # Chiama la funzione
        return self.builder.call(func, casted_args, name=f"{node.name}_result")
    
    def visit_FuncCallStmtNode(self, node):
        """
        Visita una chiamata di funzione come statement.
        Esegue la chiamata ma ignora il valore di ritorno.
        
        Args:
            node: FuncCallStmtNode contenente name e args
        """
        # Cerca la funzione nel modulo
        func = None
        for f in self.module.functions:
            if f.name == node.name:
                func = f
                break
        
        if func is None:
            raise NameError(f"Funzione '{node.name}' non definita")
        
        # Valuta gli argomenti
        args = [self.visit(arg) for arg in node.args]
        
        # Verifica il numero di argomenti
        if len(args) != len(func.args):
            raise TypeError(
                f"Funzione '{node.name}' richiede {len(func.args)} argomenti, "
                f"ma ne sono stati forniti {len(args)}"
            )
        
        # Effettua eventuali cast necessari per gli argomenti
        casted_args = []
        for i, (arg, param) in enumerate(zip(args, func.args)):
            arg_type = self._get_play_type_from_llvm(arg.type)
            param_type = self._get_play_type_from_llvm(param.type)
            
            if arg_type != param_type:
                arg = self._cast_value(arg, arg_type, param_type)
            
            casted_args.append(arg)
        
        # Chiama la funzione (ignora il valore di ritorno)
        self.builder.call(func, casted_args)
    
    def generate(self, ast_root):
        """
        Genera il codice LLVM a partire dalla radice dell'AST.
        
        Args:
            ast_root: Nodo radice dell'AST (ProgramNode)
        
        Returns:
            Stringa contenente il codice LLVM IR generato
        """
        self.visit(ast_root)
        return str(self.module)
