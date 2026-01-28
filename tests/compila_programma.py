import unittest
import sys
import os

# Add src and root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'src'))

from run_compiler import compile_source

class TestCompilaProgramma(unittest.TestCase):
    def test_calcolatrice(self):
        """
        Test:
        Genera/compila un programma in grado di:
        - Mostrare un menu per la scelta di un’operazione aritmetica.
        - Gestire input utente (interi o double).
        - Calcolare e restituire il risultato e gestire un ciclo di continuazione
          alla prossima operazione o chiusura del programma.
        - Utilizza almeno due funzioni.
        """
        code = """
        rank: op_choice
        rate: n1, n2, res
        flag: running

        // Funzione per la somma
        action add(rate a, rate b) -> rate {
            reward a + b
        }

        // Funzione per la sottrazione
        action sub(rate a, rate b) -> rate {
            reward a - b
        }

        // Funzione per la moltiplicazione
        action mul(rate a, rate b) -> rate {
            reward a * b
        }
        
        // Funzione per la divisione
        action div(rate a, rate b) -> rate {
            reward a / b
        }

        play {
            running <-- true
            
            // Ciclo principale del programma
            stay (running) -> {
                drop "--- MENU CALCOLATRICE SEMPLICE---"
                drop "1. Addizione"
                drop "2. Sottrazione"
                drop "3. Moltiplicazione"
                drop "4. Divisione"
                drop "0. Esci"
                
                op_choice <-- grab "Seleziona operazione (0-4): "

                n1 <-- grab "Inserisci primo numero: "
                n2 <-- grab "Inserisci secondo numero: "
                
                choice (op_choice == 0) -> {
                    running <-- false
                    drop "Uscita dal programma."
                } retry (op_choice == 1) -> {
                    res <-- add(n1, n2)
                    drop "Risultato: " + res
                } retry (op_choice == 2) -> {
                    res <-- sub(n1, n2)
                    drop "Risultato: " + res
                } retry (op_choice == 3) -> {
                    res <-- mul(n1, n2)
                    drop "Risultato: " + res
                } retry (op_choice == 4) -> {
                    res <-- div(n1, n2)
                    drop "Risultato: " + res
                } fail -> {
                    drop "Scelta non valida, riprova."
                }
            }
        } gameover
        """
        
        print("\nCompilazione programma Calcolatrice...")
        try:
            ast = compile_source(code)
            print("Compilazione riuscita!")
        except Exception as e:
            self.fail(f"Compilazione fallita: {e}")
        
        # Verifica che l'AST sia stato generato
        self.assertIsNotNone(ast)

if __name__ == '__main__':
    unittest.main()
