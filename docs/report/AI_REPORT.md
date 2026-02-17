# Relazione sull'Utilizzo dell'Intelligenza Artificiale

## Introduzione

Lo sviluppo del compilatore per il linguaggio "Play" è stato realizzato con il supporto di assistenti di Intelligenza Artificiale generativa (AI), in particolare: Antigravity. Questo documento descrive in dettaglio come l'AI è stata utilizzata, i vantaggi ottenuti, le sfide incontrate e le lezioni apprese durante il processo di sviluppo.

## 1. Tipologia di Utilizzo dell'AI

L'interazione con l'AI è avvenuta principalmente attraverso una modalità di **"Pair Programming"**, dove l'assistente AI ha agito come un collaboratore tecnico esperto, supportando tutte le fasi del ciclo di sviluppo.

### 1.1 Generazione delle Specifiche

**Contesto**: Partendo da un'idea generale del linguaggio "Play", era necessario formalizzare le specifiche lessicali, sintattiche, semantiche e definire la struttura dell'AST.

**Utilizzo dell'AI**:

- **Definizione della Grammatica EBNF**: L'AI ha assistito nella scrittura delle regole grammaticali per la libreria Lark, garantendo:
  
  - Corretta **precedenza degli operatori** (gestione tramite annidamento delle regole: `logic_expr` → `comp_expr` → `sum_expr` → `prod_expr`)
  - Risoluzione delle **ambiguità** (es. dangling-else problem nei costrutti `choice`)
  - Utilizzo corretto dei **modificatori Lark** (`?` per flattening, terminali vs non-terminali)

**Documenti generati con supporto AI**:

- `docs/specifiche/specifiche_lessicali_e_sintattiche.md`
- `docs/specifiche/specifiche_ast.md`
- `docs/specifiche/analisi_semantica.md`

**Efficacia**: ⭐⭐⭐⭐⭐ (5/5)  
Le specifiche generate sono risultate coerenti e complete. L'AI ha identificato potenziali problemi (es. conflitti shift-reduce) già in fase di definizione, accelerando notevolmente il lavoro di specifica.

### 1.2 Sviluppo del Codice

**Sviluppo Core Manuale**:

Lo sviluppo del cuore del compilatore è stato condotto principalmente **manualmente**, per garantire il pieno controllo sulle logiche di dominio e sulle scelte architetturali. In particolare:

- **Classi AST** (`ast_node.py`): Definizione manuale della gerarchia per rispecchiare fedelmente le specifiche.
- **Analisi Semantica**: Implementazione manuale del **Visitor Pattern** e delle regole di type checking e scoping.
- **Transformer**: Scrittura manuale della logica di trasformazione CST-to-AST per gestire casi complessi di flattening.

**Ruolo dell'AI: Rifinitura e Edge Cases**:
L'AI è intervenuta in una seconda fase come "revisore intelligente", utile per:

- **Identificare Edge Cases**: Suggerire casi limite non gestiti (es. particolari combinazioni di promozione di tipo `rank` → `rate` o conversioni implicite).
- **Controllo errori**: Raffinare i messaggi di errore semantici per renderli più descrittivi.
- **Ottimizzazione**: Proporre miglioramenti stilistici e idiomatici Python su codice già funzionante.

**Esempio concreto**:
Dopo l'implementazione manuale del metodo `visit_BinOpNode` per la gestione degli operatori binari, l'AI ha suggerito di aggiungere controlli più robusti per la compatibilità dei tipi misti (`rank` e `rate`):

```python
def visit_BinOpNode(self, node):
    # Logica implementata manualmente...
    left_type = self.visit(node.left)
    right_type = self.visit(node.right)

    # altre operazioni...

    # Suggerimento AI per gestire edge case su tipi numerici misti
    if node.op in ['-', '*', '/', '%']:
       # ... raffinamento della logica di promozione che prima falliva in alcuni casi ...
```

**Refactoring del Progetto**:

- Creazione di `run_compiler.py` come entry point unificato per il frontend.

**Efficacia**: ⭐⭐⭐⭐ (4/5)
L'approccio "Human-First" ha garantito solidità architetturale, mentre l'AI ha accelerato il processo di rifinitura, hardening del codice e gestione delle eccezioni.

### 1.3 Generazione di Test

**Creazione Manuale della Test Suite**:

**Contesto**: Per garantire la correttezza del compilatore, è stata progettata **manualmente** una suite di test esaustiva, basata sulla conoscenza delle specifiche e delle criticità del linguaggio.

Ad esempio:
- **`test_parser.py`**: Scrittura manuale di test per verificare la struttura CST di ogni costrutto grammaticale.
- **`test_semantic.py`**: Definizione puntuale di casi di test per ogni regola semantica (es. type compatibility, scoping rules).

**Ruolo dell'AI: Review e Edge Cases**:
L'AI è stata incaricata di analizzare la suite di test esistente per proporre miglioramenti:

- **Espansione dei Casi Limite**: Suggerire input "malevoli" o combinazioni insolite che non erano state considerate (es. loop annidati con shadowing di variabili, overflow numerici).
- **Refactoring del Codice di Test**: Migliorare la leggibilità e ridurre la duplicazione nei metodi di setup/teardown.

**Coverage**: Grazie all'integrazione tra test manuali e casi limite suggeriti dall'AI, la coverage ha raggiunto circa l'**85-90%**.

**Efficacia**: ⭐⭐⭐⭐⭐ (5/5)
La creatività umana nel disegnare gli scenari di test, unita alla capacità dell'AI di scovare "corner cases", ha prodotto una suite molto robusta.

### 1.4 Spiegazioni e Apprendimento

**Comprensione di Concetti**:

- **Funzionamento di Lark**: L'AI ha spiegato la differenza tra parser `earley`, `lalr`, `cyk` e perché `lalr` è stato scelto (velocità vs espressività)

**Debugging**:

- L'AI ha aiutato a **interpretare errori** di Lark (es. `UnexpectedToken`) e a identificarne la causa
- Suggerimento di strategie di debugging (es. stampare il CST prima della trasformazione)

**Efficacia**: ⭐⭐⭐⭐⭐ (5/5)  
Le spiegazioni fornite hanno colmato lacune teoriche e accelerato la comprensione dei concetti di compilazione.

### 1.5 Documentazione

**Stesura Manuale e Formalizzazione**:

**Drafting Umano**:
La documentazione del progetto, inclusa la struttura del README e le spiegazioni tecniche nel report, è stata **scritta inizialmente da noi**. Questo ha garantito che:

- La narrazione riflettesse accuratamente le decisioni progettuali prese.
- Il tono fosse appropriato e coerente con gli obiettivi didattici del progetto.

**Ruolo dell'AI: Formalizzazione e Formatting**:
L'AI è intervenuta per "pulire" e professionalizzare i testi:

- **Miglioramento del Linguaggio**: Trasformare appunti grezzi in descrizioni tecniche formali.
- **Formattazione Markdown**: Organizzare i contenuti con tabelle, elenchi puntati e blocchi di codice ben formattati per massimizzare la leggibilità.
- **Generazione Docstrings**: Aggiungere commenti standard al codice Python per migliorare la manutenibilità.

**Efficacia**: ⭐⭐⭐⭐ (4/5)
L'AI ha agito come un ottimo "editor", permettendo all'autore di concentrarsi sui contenuti piuttosto che sulla forma.

---

## 2. Efficacia e Vantaggi

### 2.1 Velocità di Sviluppo

Le fasi più accelerate sono state:

1. Scaffolding del codice (classi AST, visitor pattern)
2. Espansione e rifinitura della suite di test
3. Debugging di errori sintattici nella grammatica

### 2.2 Qualità del Codice

**Pattern di Design**:
L'AI ha suggerito l'uso di pattern standard (Visitor, Transformer) rendendo il codice:

- **Modulare**: Ogni fase del frontend è isolata
- **Estendibile**: Aggiungere nuovi costrutti richiede modifiche localizzate
- **Manutenibile**: Codice pulito e ben documentato

### 2.3 Riduzione degli Errori

**Test-Driven Development**:
L'analisi AI della suite di test ha permesso di identificare **edge-cases critici**:

- Errore nella gestione di variabili globali modificate dentro funzioni
- Bug nella promozione di tipo per operatori logici
- Mancata validazione del tipo di ritorno in funzioni ricorsive

Questi errori sarebbero stati difficili da individuare con test manuali limitati.

---

## 3. Inconvenienti e Limitazioni

### 3.1 Necessità di Supervisione Critica

**Problema**: Il codice generato dall'AI non è sempre corretto al primo tentativo.

**Esempi Concreti**:

**Gestione dello Scope**: L'implementazione iniziale della Symbol Table non gestiva correttamente le variabili globali accessibili dentro le funzioni. è stata corretta manualmente la logica di `lookup()`.

**Lezione Appresa**: Il codice generato va **sempre revisionato** con occhio critico. L'AI eccelle nel boilerplate, ma le logiche di dominio richiedono supervisione umana.

### 3.2 Dipendenza dal Contesto

**Problema**: L'efficacia dell'AI dipende fortemente dalla **qualità del prompt**.

**Tempo per Iterazioni**:
In alcuni casi, sono state necessarie **3-4 iterazioni** di correzione del prompt prima di ottenere il risultato desiderato.

**Lezione Appresa**: Investire tempo nella **formulazione di prompt chiari e specifici** è cruciale. Fornire esempi concreti migliora drasticamente la qualità dell'output.

### 3.3 Limitazioni nella Comprensione del Contesto Globale

**Problema**: L'AI lavora meglio su compiti **localizzati**. Quando le richieste coinvolgono dipendenze tra più file, può perdere coerenza.

**Esempio**:
Durante la generazione del transformer, l'AI ha inizialmente creato nodi AST con nomi leggermente diversi da quelli definiti in `ast_node.py`, causando errori di `AttributeError` a runtime.

**Soluzione**: Fornire all'AI il **contesto completo** (es. contenuto di `ast_node.py`) quando si lavora su file correlati.

---

## 4. Riflessione Critica sul Processo

### 4.1 Cosa abbiamo Imparato grazie all'AI

**Competenze Tecniche**:

- Funzionamento interno di parser LALR
- Implementazione di un type system con promozione implicita
- Il Pattern Transformer

**Competenze nell'Uso dell'AI**:

- **Prompt Engineering**: Scrivere richieste precise e ben contestualizzate
- **Validazione Critica**: Non accettare l'output dell'AI senza verifica
- **Iterazione Efficace**: Raffinare progressivamente il prompt basandosi sui risultati parziali

### 4.2 Quando l'AI è Stata Più Utile

1. **Generazione di codice ripetitivo** (classi AST, test)
2. **Spiegazione di concetti teorici** (lark, tranformer)
3. **Debugging rapido** di errori

### 4.3 Quando l'AI è Stata Meno Utile

1. **Decisioni architetturali strategiche** (es. scelta tra visitor e interpreter pattern)
2. **Logiche di dominio complesse** (es. regole di scoping specifiche del linguaggio Play)
3. **Ottimizzazione delle prestazioni**

---

## 5. Conclusioni

### Sintesi dell'Esperienza

L'utilizzo dell'Intelligenza Artificiale nello sviluppo del compilatore per "Play" si è rivelato **estremamente vantaggioso**, permettendo di:

- **Dimezzare** il tempo di sviluppo (debugging e refactoring)
- Ottenere codice di **qualità professionale** grazie ai pattern suggeriti
- **Migliorare la robustezza** della suite di test manuale identificando corner cases nascosti

Tuttavia, l'AI **non è una soluzione autonoma**. Ha richiesto:

- Supervisione critica costante
- Competenze pregresse per validare l'output
- Capacità di formulare richieste precise

### Riflessione Finale
l'AI è un **amplificatore di produttività**, non un sostituto del programmatore. La combinazione di:

- **Creatività e Giudizio Umano** per decisioni strategiche
- **Potenza Computazionale dell'AI** per compiti meccanici

rappresenta il modello di sviluppo più efficace.

**Valutazione Complessiva Soggettiva dell'Utilizzo dell'AI**: ⭐⭐⭐⭐ (4/5)
