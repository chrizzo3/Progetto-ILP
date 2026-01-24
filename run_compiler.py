import sys
import os
from lark import Lark

# Add current directory to path so we can import modules
# Add 'src' directory to path so we can import 'play_lang'
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from play_lang.frontend.transformer import PlayTransformer
from play_lang.frontend.semantic_analysis import SemanticAnalyzer, SemanticError

def get_parser():
    """Loads the grammar and returns the Lark parser."""
    grammar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'play_lang', 'frontend', 'grammar.lark')
    with open(grammar_path, 'r') as f:
        grammar_src = f.read()
    return Lark(grammar_src, start='program', parser='lalr')

def compile_source(source_code):
    """
    Compiles the Play source code through the Frontend pipeline.
    
    1. Parsing (Lexical + Syntax Analysis) -> Concrete Syntax Tree (CST)
    2. Transformation -> Abstract Syntax Tree (AST)
    3. Semantic Analysis -> Verified AST
    
    Returns:
        ProgramNode: The root of the validated AST.
    
    Raises:
        Exception: If any stage fails (syntax error, semantic error, etc.)
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

    return ast

def print_ast(node, indent=""):
    """
    Recursively prints the AST node and its children.
    """
    if node is None:
        print(f"{indent}None")
        return

    if isinstance(node, list):
        for item in node:
            print_ast(item, indent)
        return

    if not hasattr(node, "__dict__"):
        print(f"{indent}{repr(node)}")
        return

    print(f"{indent}{type(node).__name__}")
    for key, value in node.__dict__.items():
        if isinstance(value, list):
            print(f"{indent}  {key}:")
            if not value:
                print(f"{indent}    []")
            for item in value:
                print_ast(item, indent + "    ")
        elif hasattr(value, "__dict__"):
            print(f"{indent}  {key}:")
            print_ast(value, indent + "    ")
        else:
            print(f"{indent}  {key}: {repr(value)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_frontend.py <path_to_play_file>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    try:
        with open(file_path, 'r') as f:
            code = f.read()
            
        print(f"Compiling '{file_path}'...")
        ast = compile_source(code)
        
        print("\n✅ Frontend Analysis Successful!")
        print(f"Generated AST Root: {type(ast).__name__} with {len(ast.functions)} functions and {len(ast.global_decls)} globals.")
        print("\n[AST Structure]")
        print_ast(ast)
        
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Compilation Failed:")
        print(e)
        sys.exit(1)
