"""
Modulo di ottimizzazioni per il compilatore Play.
Implementa vari pass di ottimizzazione sull'AST.
"""

from .constant_folding import ConstantFoldingOptimizer
from .dead_code import DeadCodeEliminationOptimizer
from .strength_reduction import StrengthReductionOptimizer
from .copy_propagation import CopyPropagationOptimizer
from .cse import CSEOptimizer

__all__ = [
    'ConstantFoldingOptimizer',
    'DeadCodeEliminationOptimizer', 
    'StrengthReductionOptimizer',
    'CopyPropagationOptimizer',
    'CSEOptimizer'
]
