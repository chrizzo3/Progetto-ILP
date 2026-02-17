# Play Language Compiler

## Panoramica

Questo progetto implementa un **compilatore completo** per il linguaggio di programmazione **"Play"**, un linguaggio imperativo progettato per scopi didattici.

Il sistema trasforma codice sorgente `.play` in un **Abstract Syntax Tree (AST)** validato e semanticamente corretto, che viene poi compilato in **codice LLVM IR** ottimizzato ed eseguibile.

### Componenti Implementati

#### Frontend

Il frontend è organizzato in tre fasi sequenziali:

1. **Analisi Lessicale e Sintattica (Lexer/Parser)**
   
   - Utilizza la libreria **Lark** con algoritmo **LALR(1)**
   - Grammatica definita in `src/play_lang/frontend/grammar.lark`
   - Produce un **Concrete Syntax Tree (CST)** dal codice sorgente

2. **Trasformazione AST (Transformer)**
   
   - Implementato in `src/play_lang/frontend/transformer.py`
   - Converte il CST in un **Abstract Syntax Tree (AST)** pulito e strutturato

3. **Analisi Semantica (Semantic Analyzer)**
   
   - Implementato in `src/play_lang/frontend/semantic_analysis.py`
   - Esegue **Type Checking** (verifica compatibilità tipi)
   - Gestisce **Symbol Table** e scoping (variabili locali/globali)
   - Valida coerenza di operazioni, assegnamenti, chiamate a funzione

#### Backend

Il backend trasforma l'AST validato in codice eseguibile:

1. **Generazione Codice LLVM (Code Generator)**
   
   - Implementato in `src/play_lang/backend/codegen.py`
   - Utilizza **llvmlite** per generare **LLVM IR** (Intermediate Representation)
   - Implementa **Visitor Pattern** per attraversare l'AST

2. **Ottimizzazioni (Optimization Passes)**
   
   Ottimizzazioni applicate all'AST
   
   - **Constant Folding**: Pre-calcola espressioni costanti a compile-time
   - **Copy Propagation**: Sostituisce copie di variabili con i valori originali
   - **Common Subexpression Elimination (CSE)**: Rimuove calcoli ridondanti
   - **Dead Code Elimination**: Elimina codice irraggiungibile
   - **Strength Reduction**: Ottimizza operazioni costose (es. moltiplicazioni per potenze di 2)
   
   In più, sono state utilizzate le ottimizzazioni attraverso il PassManager di LLVM

3. **Generazione Codice Macchina (Machine Code Generation)**
   
   - L'LLVM IR ottimizzato viene compilato in **codice macchina nativo** utilizzando la toolchain LLVM e GCC
   - Il processo di compilazione:
     1. Compilazione del codice IR (`output.ll`) in codice oggetto (`output.o`) tramite **Clang**
     2. Linking del codice oggetto con le librerie di sistema tramite **GCC** per produrre l'eseguibile finale

### Caratteristiche del Linguaggio Play

- **Tipi di dato**: `rank` (int), `rate` (double), `flag` (bool), `label` (string)
- **Strutture di controllo**: `choice` (if-else), `stay` (while), `loop` (for)
- **Funzioni**: Definizione con `action`, ritorno con `reward`
- **I/O**: Input con `grab`, output con `drop`
- **Operatori**: Aritmetici (`+`, `-`, `*`, `/`,`%`), logici (`&&`, `||`, `!`), comparazione (`<`, `>`, `>=`, `<=`, `==`, `<>`)
- **Operatore di conversione**: `-->` per convertire variabili/espressioni in stringhe all'interno di `drop`

## Struttura del Progetto

```
Progetto-ILP/
│
├── src/
│   └── play_lang/
│       ├── __init__.py
│       ├── frontend/                        # Pipeline di analisi frontend
│       │   ├── __init__.py
│       │   ├── grammar.lark                 # Grammatica Lark (EBNF)
│       │   ├── ast_node.py                  # Definizione classi AST
│       │   ├── transformer.py               # CST -> AST
│       │   └── semantic_analysis.py         # Type Checking & Symbol Table
│       │
│       └── backend/               # Generazione codice e ottimizzazioni
│           ├── codegen.py                   # Generatore LLVM IR
│           │
│           └── optimization/                # Pass di ottimizzazione
│               ├── constant_folding.py      # Calcolo espressioni costanti
│               ├── copy_propagation.py      # Propagazione copie
│               ├── cse.py                   # Eliminazione sottoespressioni comuni
│               ├── dead_code.py             # Rimozione codice morto
│               └── strength_reduction.py    # Riduzione forza operazioni
│
├── tests/                                   # Suite completa di test   
│   ├── __init__.py
│   ├── run_tests.py                         # Runner per tutti i test
│   │
│   ├── frontend/
│   │   ├── test_parser.py                       # Test analisi lessicale e sintattica
│   │   ├── test_transformer.py                  # Test trasformazione AST
│   │   └── test_semantic.py                     # Test analisi semantica
│   │
│   ├── codegen/                             # Test generazione codice
│   │   ├── test_math_output.play
│   │   └── test_math_output.expected
│   │
│   ├── optimization/                        # Test ottimizzazioni
│   │   ├── test_constant_folding_output.play
│   │   ├── test_constant_folding_output.expected
│   │   ├── test_cp_cse_output.play
│   │   └── test_cp_cse_output.expected
│   │   ├── test_dead_code_output.play
│   │   └── test_dead_code_output.expected
│   │   ├── test_strength_reduction_output.play
│   │   └── test_strength_reduction_output.expected
│   │
│   └── integration/                         # Test end-to-end
│       ├── test_fibonacci_output.play
│       ├── test_fibonacci_output.expected
│       ├── test_primes_output.play
│       └── test_primes_output.expected
│
├── docs/   
│   ├── specifiche/                        # Specifiche del Linguaggio Play
│   │   ├── specifiche_lessicali_e_sintattiche.md
│   │   ├── descrizione_sintassi.md
│   │   ├── specifiche_ast.md
│   │   └── analisi_semantica.md
│   │
│   └── reports/
│       ├── AI_REPORT.md                         # Relazione utilizzo AI
│       └── TECHNICAL_REPORT.md                  # Documentazione tecnica dettagliata
│
├── examples/                   # Esempi in file.play
│   ├── codice.play                          # Calcolatrice richiesta
│   ├── drop.play                            # Tutte le tipologie di stampe
│   └── test_completo.play                   # Tutto ciò che si può usare nel linguaggio Play
│
├── run_compiler.py                          # Entry point per compilazione ed esecuzione
├── requirements.txt                         # Dipendenze da installare
└── README.md                                # Questo file
```

## Requisiti

- **Python**: Versione 3.8 o superiore
- **Dipendenze Python**:
  - `lark` - Lexer e parser
  - `llvmlite` - Generazione codice LLVM IR
- **Dipendenze di sistema**:
  - **LLVM**: Versione 10 o superiore (per compilazione ed esecuzione del codice generato)
  - **Clang**: Per compilare l'IR e le librerie di runtime
  - **GCC**: Per il linking dell'eseguibile finale

## Installazione

### 1. Clona il repository

```bash
git clone https://github.com/chrizzo3/Progetto-ILP.git
cd Progetto-ILP
```

### 2. Installa LLVM, Clang e GCC

#### Windows

1. **LLVM & Clang**:
   
   - Scarica l'installer da [https://releases.llvm.org/](https://releases.llvm.org/) (versione 10+).
   - Seleziona **"Add LLVM to the system PATH"** durante l'installazione.

2. **GCC (MinGW)**:
   
   - Scarica **MinGW-w64** (consigliato tramite [MSYS2](https://www.msys2.org/) o [WinLibs](https://winlibs.com/)).
   - Aggiungi la cartella `bin` di MinGW al PATH di sistema.

3. Verifica:
   
   ```powershell
   clang --version
   gcc --version
   ```

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install llvm clang build-essential
# build-essential include GCC
```

#### macOS

```bash
brew install llvm gcc
# Aggiungi LLVM al PATH (aggiungi al tuo ~/.zshrc o ~/.bashrc)
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
```

### 3. (Opzionale) Crea un ambiente virtuale

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 4. Installa le dipendenze Python

```bash
pip install -r requirements.txt
```

## Utilizzo

### Compilare ed eseguire un file sorgente Play

Il comando principale per compilare ed eseguire un programma Play è:

```bash
python run_compiler.py <percorso_file.play>
```

Questo eseguirà:

1. **Frontend**: Analisi lessicale, sintattica e semantica
2. **Backend**: Generazione LLVM IR e ottimizzazioni
3. **Esecuzione**: Compilazione del codice LLVM ed esecuzione del programma

**Esempio**:

```bash
python run_compiler.py examples/codice.play
```

### Output atteso

Se il codice è **sintatticamente e semanticamente corretto**, il programma verrà compilato ed eseguito:

```
[OK] Compilation Successful!
Generated 'output.ll'.
Creating executable...
[OK] Created 'program.exe'

Running program...
=====================================
[Output del programma Play]
```

In caso di **errori sintattici** o **semantici**, verrà mostrato un messaggio di errore dettagliato:

```
❌ Compilation Failed:
Semantic Error: Type mismatch in assignment: expected 'rank', got 'rate'
```

## Esecuzione dei Test

Il progetto include una **suite di test completa** per verificare tutte le fasi del compilatore, dal frontend al backend.

### Eseguire tutti i test

```bash
python -m unittest discover tests
```

### Eseguire test specifici

```bash
# Test frontend
python -m unittest tests.frontend.test_parser
python -m unittest tests.frontend.test_transformer
# ...

# Test compilazione codice richiesto
python tests/compila_programma.py
```

### Dettaglio dei Test

#### Frontend Tests

| File                                 | Descrizione                                                                                                                  |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `tests/frontend/test_parser.py`      | Verifica il corretto riconoscimento dei token e della struttura sintattica tramite la grammatica Lark                        |
| `tests/frontend/test_transformer.py` | Testa la corretta creazione dei nodi AST a partire dal CST generato dal parser                                               |
| `tests/frontend/test_semantic.py`    | Verifica le regole di tipo, lo scoping delle variabili, la compatibilità degli operandi e la gestione degli errori semantici |

#### Backend & Integration Tests

| Directory/File         | Descrizione                                                            |
| ---------------------- | ---------------------------------------------------------------------- |
| `tests/codegen/`       | Test di generazione codice LLVM IR per operazioni matematiche e output |
| `tests/optimization/`  | Test delle ottimizzazioni (constant folding, copy propagation, CSE)    |
| `tests/integration/`   | Test end-to-end su programmi completi (Fibonacci, numeri primi, etc.)  |
| `compila_programma.py` | Script per testare l'intera pipeline di compilazione ed esecuzione     |

#### Struttura Test Files

Ogni test nel backend include:

- **`.play`**: File sorgente Play
- **`.expected`**: Output atteso del programma compilato

**Esempio**:

```bash
tests/integration/test_fibonacci_output.play
tests/integration/test_fibonacci_output.expected
```

## Esempi di Codice Play

### Hello World

```play
play {
    drop "Hello, Play!"
} gameover
```

**Output**:

```
Hello, Play!
```

### Calcolo dell'area di un cerchio

```play
action calculate_area(rate radius) -> rate {
    reward radius * radius * 3.14
}

play {
    rate: rad, area
    rad <-- grab "Inserisci il raggio: "
    area <-- calculate_area(rad)
    drop "Area: " + -->area  // --> converte la variabile in stringa
} gameover
```

**Output** (con input `5`):

```
Inserisci il raggio: 5
Area: 78.500000
```

### Loop e condizionali

```play
play {
    rank: i
    loop (i <-- 1; i <= 10; i <-- i + 1) -> {
        choice (i % 2 == 0) -> {
            drop "Pari: " + -->i
        } fail -> {
            drop "Dispari: " + -->i
        }
    }
} gameover
```

**Output**:

```
Dispari: 1
Pari: 2
Dispari: 3
Pari: 4
Dispari: 5
Pari: 6
Dispari: 7
Pari: 8
Dispari: 9
Pari: 10
```

### Operatore di conversione (`-->`)

L'operatore `-->` converte variabili ed espressioni in stringhe per l'output:

```play
play {
    rank: x <-- 42
    rate: y <-- 3.14
    flag: bool_val <-- true

    // Variabili richiedono -->
    drop -->x
    drop "Numero: " + -->x

    // Espressioni richiedono -->
    drop -->(x + 10)
    drop -->(y > 3.0)

    // Letterali NON richiedono -->
    drop "Hello"
    drop 123

    // I booleani vengono stampati come "true" o "false"
    drop -->bool_val
    drop -->(5 > 3)
} gameover
```

**Output**:

```
42
Numero: 42
52
true
Hello
123
true
true
```

### Uscita anticipata da loop (`quit`)

La keyword `quit` permette di uscire anticipatamente da un loop:

```play
play {
    rank: i

    // Trova il primo numero divisibile per 7
    loop (i <-- 1; i <= 100; i <-- i + 1) -> {
        choice (i % 7 == 0) -> {
            drop "Primo numero divisibile per 7: " + -->i
            quit  // Esce dal loop
        }
    }

    drop "Loop terminato!"
} gameover
```

**Output**:

```
Primo numero divisibile per 7: 7
Loop terminato!
```

## Documentazione

- **[TECHNICAL_REPORT.md](docs/reports/TECHNICAL_REPORT.md)**: Analisi dettagliata dell'architettura, delle scelte progettuali e della pipeline di compilazione
- **[AI_REPORT.md](docs/reports/AI_REPORT.md)**: Relazione sull'utilizzo dell'Intelligenza Artificiale nello sviluppo del progetto
- **Specifiche del linguaggio** (cartella `docs/specifiche/`):
  - `specifiche_lessicali_e_sintattiche.md`: Token e regole grammaticali
  - `descrizione_sintassi.md`: Descrizione formale dei costrutti
  - `specifiche_ast.md`: Definizione dei nodi AST
  - `analisi_semantica.md`: Regole di tipo e inferenza

## Autori

**Gagliarde Stefano & Izzo Christian** - Studenti Magistrale in Cloud Computing  
Università degli Studi di Salerno - Corso di Ingegneria dei Linguaggi di Programmazione (ILP)

## Licenza

Questo progetto è stato sviluppato per scopi didattici nell'ambito del corso universitario di Ingegneria dei Linguaggi di Programamzione.
