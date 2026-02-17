import sys
import os
import subprocess
from lark import Lark
import llvmlite.binding as llvm_binding

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from play_lang.frontend.transformer import PlayTransformer
from play_lang.frontend.semantic_analysis import SemanticAnalyzer, SemanticError
from play_lang.backend.codegen import LLVMCodeGenerator
from play_lang.backend.optimization import (
    ConstantFoldingOptimizer,
    DeadCodeEliminationOptimizer,
    StrengthReductionOptimizer,
    CopyPropagationOptimizer,
    CSEOptimizer
)

def get_parser():
    """Carica la grammatica e restituisce il parser Lark."""
    grammar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'play_lang', 'frontend', 'grammar.lark')
    with open(grammar_path, 'r') as f:
        grammar_src = f.read()
    return Lark(grammar_src, start='program', parser='lalr', lexer='basic')

def optimize_ir(llvm_ir_string, speed_level=2, size_level=0):
    """
    Ottimizza il codice LLVM IR usando il Pass Manager di LLVM.
    
    Args:
        llvm_ir_string: Stringa contenente il codice LLVM IR
        speed_level: Livello di ottimizzazione per velocità (0-3, default 2)
        size_level: Livello di ottimizzazione per dimensione (0-2, default 0)
    
    Returns:
        Stringa contenente il codice LLVM IR ottimizzato
    """
    # Inizializza LLVM
    llvm_binding.initialize_native_target()
    llvm_binding.initialize_native_asmprinter()
    
    # Parsa l'IR generato
    mod = llvm_binding.parse_assembly(llvm_ir_string)
    mod.verify()
    
    # Crea target machine per il sistema corrente
    target = llvm_binding.Target.from_default_triple()
    target_machine = target.create_target_machine()
    
    # Configura le opzioni di ottimizzazione
    pto = llvm_binding.create_pipeline_tuning_options(
        speed_level=speed_level,
        size_level=size_level
    )
    pto.loop_unrolling = True
    pto.loop_vectorization = False 
    pto.slp_vectorization = False
    
    # Crea il pass builder e ottieni il pass manager popolato
    pass_builder = llvm_binding.create_pass_builder(target_machine, pto)
    
    # Ottimizzazione a livello di modulo
    mpm = pass_builder.getModulePassManager()
    mpm.run(mod, pass_builder)
    
    # Ottimizzazione a livello di funzione  
    fpm = pass_builder.getFunctionPassManager()
    for func in mod.functions:
        fpm.run(func, pass_builder)
    
    return str(mod)

def compile_source(source_code, output_filename="output.ll"):
    """
    Compila il codice sorgente Play in LLVM IR.
    """
    # 1. Parsing
    parser = get_parser()
    try:
        tree = parser.parse(source_code)
    except Exception as e:
        raise Exception(f"Syntax Error: {e}")

    # 2. Transformation
    try:
        transformer = PlayTransformer()
        ast = transformer.transform(tree)
    except Exception as e:
        raise Exception(f"AST Transformation Error: {e}")

    # 3. Semantic Analysis
    try:
        analyzer = SemanticAnalyzer()
        analyzer.visit(ast)
    except SemanticError as e:
        raise Exception(f"Semantic Error: {e}")
    except Exception as e:
        raise Exception(f"Unexpected Semantic Error: {e}")

    # 4. Optimizations
    print("Applying optimizations...")
    try:
        # Pass 1: Constant Folding
        cf_optimizer = ConstantFoldingOptimizer()
        ast = cf_optimizer.optimize(ast)
        cf_count = cf_optimizer.optimizations_count
        
        # Pass 2: Dead Code Elimination  
        dce_optimizer = DeadCodeEliminationOptimizer()
        ast = dce_optimizer.optimize(ast)
        dce_count = dce_optimizer.eliminations_count
        
        # Pass 3: Strength Reduction
        sr_optimizer = StrengthReductionOptimizer()
        ast = sr_optimizer.optimize(ast)
        sr_count = sr_optimizer.reductions_count
        
        # Pass 4: Copy Propagation (sinergia con CF)
        cp_optimizer = CopyPropagationOptimizer()
        ast = cp_optimizer.optimize(ast)
        cp_count = cp_optimizer.propagations_count
        
        # Pass 5: Constant Folding di nuovo (dopo copy propagation)
        cf2_optimizer = ConstantFoldingOptimizer()
        ast = cf2_optimizer.optimize(ast)
        cf2_count = cf2_optimizer.optimizations_count
        
        # Pass 6: CSE (dopo tutte le semplificazioni)
        cse_optimizer = CSEOptimizer()
        ast = cse_optimizer.optimize(ast)
        cse_count = cse_optimizer.eliminations_count
        
        # Report ottimizzazioni
        total_opts = cf_count + dce_count + sr_count + cp_count + cf2_count + cse_count
        if total_opts > 0:
            print(f"  - Constant Folding: {cf_count} optimizations")
            print(f"  - Dead Code Elimination: {dce_count} eliminations")
            print(f"  - Strength Reduction: {sr_count} reductions")
            print(f"  - Copy Propagation: {cp_count} propagations")
            print(f"  - Constant Folding (2nd pass): {cf2_count} optimizations")
            print(f"  - Common Subexpression Elimination: {cse_count} eliminations")
            print(f"  Total: {total_opts} optimizations applied")
        else:
            print("  No optimizations applicable")
    except Exception as e:
        raise Exception(f"Optimization Error: {e}")

    # 5. Code Generation
    print("Generating LLVM IR...")
    try:
        codegen = LLVMCodeGenerator()
        llvm_ir = codegen.generate(ast)
        
        # Salva su file
        with open(output_filename, 'w') as f:
            f.write(llvm_ir)
    except Exception as e:
        raise Exception(f"Code Generation Error: {e}")

    # 6. LLVM IR Optimization (Pass Manager)
    print("Applying LLVM IR optimizations...")
    try:
        optimized_ir = optimize_ir(llvm_ir)
        
        # Sovrascrivi il file con l'IR ottimizzato
        with open(output_filename, 'w') as f:
            f.write(optimized_ir)
        
        return optimized_ir
    except Exception as e:
        print(f"  [WARNING] LLVM optimization failed: {e}")
        print("  Using unoptimized IR.")
        return llvm_ir

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_compiler.py <path_to_play_file>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    try:
        with open(file_path, 'r') as f:
            code = f.read()
            
        print(f"Compiling '{file_path}'...")
        llvm_ir = compile_source(code, "output.ll")
        
        print("\n[OK] Compilation Successful!")
        print("Generated 'output.ll'.\n")
        
        # Compila in eseguibile con clang + gcc
        print("Creating executable...")
        exe_name = "program.exe"
        try:
            # Step 1: LLVM IR -> Object File (Clang)
            obj_file = "output.o"
            clang_args = ["clang", "-c", "output.ll", "-o", obj_file]
            
            if os.name == 'nt':  # Target specifico per Windows
                clang_args.extend(["-target", "x86_64-w64-mingw32"])

            print(f"  1. Compiling to object file ({' '.join(clang_args)})...")
            result_compile = subprocess.run(clang_args, capture_output=True, text=True)
            
            if result_compile.returncode != 0:
                print("[WARNING] Object compilation failed")
                print(f"Clang output: {result_compile.stderr}")
                raise Exception("Clang compilation failed")

            # Step 2: Object File -> Executable (GCC)
            gcc_args = ["gcc", obj_file, "-o", exe_name]

            print(f"  2. Linking executable ({' '.join(gcc_args)})...")
            result_link = subprocess.run(gcc_args, capture_output=True, text=True)

            # Controlla se l'eseguibile è stato creato
            if result_link.returncode == 0 and os.path.exists(exe_name):
                print(f"[OK] Created '{exe_name}'")
                print(f"\nRunning program...\n")
                print("="*60)
                
                # Esegui il programma
                try:
                    run_result = subprocess.run([f".\\{exe_name}"], shell=True)
                    print(f"\n[Program exited with code {run_result.returncode}]")
                except Exception as e:
                    print(f"[ERROR] Failed to run program: {e}")
                
                # Cleanup object file
                if os.path.exists(obj_file):
                    os.remove(obj_file)
            else:
                print("[WARNING] Linking failed")
                print(f"GCC output: {result_link.stderr}")

        except FileNotFoundError as e:
            print(f"[WARNING] Compilation tool not found: {e}. Ensure both 'clang' and 'gcc' are in PATH.")
        except Exception as e:
            print(f"[WARNING] Error creating executable: {e}")

    except FileNotFoundError:
        print(f"[ERROR] File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Compilation Failed:")
        print(e)
        import traceback
        traceback.print_exc()
        sys.exit(1)