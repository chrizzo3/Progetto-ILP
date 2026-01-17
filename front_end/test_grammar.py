from lark import Lark
from lark.exceptions import UnexpectedToken, UnexpectedCharacters, VisitError

# Mappa dei token tecnici -> Messaggi umani
# Basata sui nomi dei token definiti nel file grammar.lark
TOKEN_MAP = {
    'COLON': "i due punti ':'",
    'SEMICOLON': "il punto e virgola ';'",
    'LBRACE': "una parentesi graffa aperta '{'",
    'RBRACE': "una parentesi graffa chiusa '}'",
    'LPAR': "una parentesi tonda aperta '('",
    'RPAR': "una parentesi tonda chiusa ')'",
    'ARROW': "una freccia '->'",
    'ASSIGN': "l'operatore di assegnazione '<--'",
    'ID': "un identificatore (nome variabile o funzione)",
    'RANK': "il tipo 'rank'",
    'RATE': "il tipo 'rate'",
    'FLAG': "il tipo 'flag'",
    'LABEL': "il tipo 'label'",
}

def gestisci_errore(e, code):
    """Funzione universale per formattare gli errori"""
    
    print("\n" + "="*40)
    
    # 1. Errore Sintattico (Struttura sbagliata)
    if isinstance(e, UnexpectedToken):
        print(f"❌ ERRORE DI SINTASSI (Riga {e.line}, Colonna {e.column})")
        print(f"   Il compilatore si è bloccato su: '{e.token.value}'")
        
        # Cerchiamo di dare un suggerimento intelligente
        expected_tokens = [TOKEN_MAP.get(t, t) for t in e.expected]
        if expected_tokens:
            print(f"   💡 SUGGERIMENTO: Probabilmente ti sei dimenticato {expected_tokens[0]}")
            if len(expected_tokens) > 1:
                print(f"      (Oppure ci si aspettava: {', '.join(expected_tokens[1:])})")
        
        # Mostra il contesto (la riga di codice)
        lines = code.splitlines()
        print(f"\n   {lines[e.line-1]}")
        print(f"   {' ' * (e.column-1)}^")

    # 2. Errore Lessicale (Carattere sconosciuto)
    elif isinstance(e, UnexpectedCharacters):
        print(f"❌ ERRORE LESSICALE (Riga {e.line}, Colonna {e.column})")
        print(f"   Carattere non riconosciuto: '{code[e.pos_in_stream]}'")
        print("   Controlla di non aver inserito simboli strani o emoji.")
        
        lines = code.splitlines()
        print(f"\n   {lines[e.line-1]}")
        print(f"   {' ' * (e.column-1)}^")

    # 3. Errore Semantico (Logica errata - Lo useremo dopo col Transformer)
    elif isinstance(e, VisitError):
        # Lark avvolge l'errore originale (es. ValueError) dentro un VisitError
        print(f"❌ ERRORE SEMANTICO")
        print(f"   {e.orig_exc}") # Stampa il messaggio che scriveremo noi (es. "Tipo non compatibile")

    else:
        print(f"❌ ERRORE SCONOSCIUTO: {e}")
    
    print("="*40 + "\n")



# 1. Carica la grammatica
try:
    with open('grammar.lark', 'r') as f:
        grammar = f.read()
    
    # 'start' deve corrispondere alla tua regola iniziale (di solito 'program' o 'start')
    parser = Lark(grammar, start='program', parser='lalr')
    print("✅ Grammatica caricata correttamente (Sintassi .lark valida).")

except Exception as e:
    print(f"❌ Errore nel caricamento della grammatica:\n{e}")
    exit(1)

# 2. Codice di test (Esempio 1 dal Manuale Play)
test_code = """
rank: d
rank: score <-- 0
rank: level <-- 1
flag: isRunning <-- true

action UpdateScore(rank points) -> void {
    score <-- score + points
    reward void
}

play {
    drop "Gioco Iniziato!"
    stay (isRunning) -> {
        rank: inputVal
        inputVal <-- grab "Inserisci comando (1=Punti, 0=Esci)"
        
        choice (inputVal == 0) -> {
            isRunning <-- false
        } retry (inputVal == 1) -> {
            UpdateScore(100)
            drop "Punteggio: " + -->score
        } fail -> {
            drop "Comando non valido"
        }
    }
    drop "Score Finale: " + -->score
}
gameover
"""

# Prova di Parsing per Esempio 1
try:
    tree = parser.parse(test_code)
    print("\n✅ Parsing completato con successo!")
    
    # Visualizzazione Albero
    print("\nStruttura dell'albero:")
    print(tree.pretty())

except Exception as e:
    gestisci_errore(e, test_code)



# 3. Prova priorità Operatori (Esempio 2)
test_math = """
play {
    rank: x <-- 1 + 2 * 3
}
gameover
"""

# Prova di Parsing per Esempio 2
try:
    tree = parser.parse(test_math)
    print("\n✅ Parsing completato con successo!")
    
    # Visualizzazione Albero
    print("\nStruttura dell'albero:")
    print(tree.pretty())

except Exception as e:
    gestisci_errore(e, test_math)


# 4. Prova stress test
stress_code = """
play {
    // 1. Test precedenza logica mista
    flag: f <-- true || false && false   
    
    // 2. Test blocchi opzionali (niente else/retry)
    choice (f) -> {
        drop "Solo If"
    }

    // 3. Test annidamento profondo e vuoto
    rank: i
    stay (true) -> {
        loop (i <-- 0; i < 10; i + 1) -> {
            // Blocco vuoto
        }
    }

    // 4. Test assegnamenti multipli a catena (se supportati)
    rank: a, b, c
    a = b = c <-- 10

    // 5. Espressioni matematiche complesse con parentesi
    rank: x <-- ((1 + 2) * (3 + 4)) % 5
}
gameover
"""
# Esegui il parser su questo codice...
try:
    tree = parser.parse(stress_code)
    print("\n✅ Parsing completato con successo!")
    
    # Visualizzazione Albero
    print("\nStruttura dell'albero:")
    print(tree.pretty())

except Exception as e:
    gestisci_errore(e, stress_code)