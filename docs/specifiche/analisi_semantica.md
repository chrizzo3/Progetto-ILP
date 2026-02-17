# Regole di Semantica Statica - Play

In questo documento vengono descritte le regole di semantica statica del linguaggio Play, formulate utilizzando la struttura logica **IF-THEN-ELSE** e facendo riferimento esplicito ai nodi dell'AST definiti in `specifiche_ast.md`.

Assumiamo un **singolo scope globale** e un ambiente (Environment/Tabella dei Simboli) $T$ che mantiene le associazioni tra i nomi delle variabili e i loro tipi.

---

## 1. Assegnamento (Var Assign)

**Costrutto Assegnamento, nodo `AssignNode`**:

- **IF** L'identificatore `target` è dichiarato nell'ambiente T
  - **AND** Il tipo dell'espressione `expr` è compatibile (uguale o promuovibile in modo sicuro) con il tipo dichiarato di `target` in T
  - **THEN** L'assegnamento è valido (`NOTYPE`).
- **ELSE**
  - **Errore**: Variabile non dichiarata o incompatibilità di tipo (`type mismatch`). 

## 2. Input (Grab)

**Costrutto Grab, nodo `InputNode`**:

- **IF** `prompt_expr` è presente **IMPLIES** (`prompt_expr` è di tipo `label`)
  - **AND** Per ogni variabile `x` nella lista (flattata) di `target_groups`:
    - `x` è dichiarata nell'ambiente $T$
  - **THEN** L'istruzione `grab` è valida.
- **ELSE**
  - **Errore**: Prompt non valido o variabile di destinazione non dichiarata.

## 3. Output (Drop)

**Costrutto Drop, nodo `OutputNode`**:

- **IF** Il tipo dell'espressione `expr` è `label`
  - **THEN** L'istruzione `drop` è valida.
- **ELSE**
  - **Errore**: `drop` richiede una stringa (usare concatenazione per stampare altri tipi).

## 4. Operatore di Valore (-->)

**Costrutto Output Value, nodo `UnaryOpNode` (con `op='-->'`)**:

- **IF** Il nodo è utilizzato come espressione diretta all'interno di un `OutputNode` (o contesto verificato simile)
  - **THEN** L'operazione è valida e ha lo stesso tipo dell'espressione interna.
    - **Nota**: Questo operatore è limitato esclusivamente all'uso all'interno di un'istruzione `drop` (output). Serve a estrarre esplicitamente il valore di una variabile per la stampa e non può essere utilizzato in altri contesti (come espressioni aritmetiche o assegnamenti).
- **ELSE**
  - **Errore**: Uso improprio dell'operatore valore.

## 5. Espressione Somma (Sum)

**Costrutto Somma/Concatenazione, nodo `BinOpNode` (con `op='+'`)**:

* **IF** (`left` è di tipo numerico (`rank` o `rate`) in $T$) **AND** (`right` è di tipo numerico (`rank` o `rate`) in $T$)
  * **THEN** L'operazione è valida e il tipo risultante è numerico (promozione a `rate` se uno dei due è `rate`, altrimenti `rank`).
* **ELSE IF** (`left` è di tipo `label` in $T$) **OR** (`right` è di tipo `label` in $T$)
  * **THEN** L'operazione è una concatenazione valida e il tipo risultante è `label`.
* **ELSE**
  * **Errore di tipo**: Impossibile sommare tipi incompatibili (es. `flag` + `rank`)

## 6. Condizionale (Choice/If)

Costrutto Choice, nodo `IfNode`

- **IF** Il tipo dell'espressione `condition` è `flag`
  - **AND** Il blocco `then_block` è valido
  - **AND** Per ogni nodo in `elifs` (se presenti):
    - Il tipo della `condition` dell' `ElifNode` è `flag`
    - Il `block` associato è valido
  - **AND** Il blocco `else_block` (se presente) è valido
  - **THEN** Il costrutto `choice` è valido.
- **ELSE**
  - **Errore**: Le condizioni devono essere di tipo `flag` o errore nei blocchi.

## 7. Operatori

### Operatori Logici (`&&`, `||`, `!`)

**Nodi `BinOpNode` (op logic) / `UnaryOpNode` (op='!')**:

- **IF** Tutti gli operandi (`left`, `right` oppure `expr`) sono di tipo `flag`
  - **THEN** L'operazione è valida e il tipo risultante è `flag`.
- **ELSE**
  - **Errore di tipo**: Gli operatori logici richiedono operandi booleani.

### Operatori di Confronto (`==`, `<>`, `<`, `<=`, `>`, `>=`)

**Nodo `BinOpNode` (op confronto)**:

- **IF** Il tipo di `left` è compatibile con il tipo di `right` (es. entrambi numerici o entrambi stringhe)
  - **THEN** Il confronto è valido e il tipo risultante è `flag`.
- **ELSE**
  - **Errore di tipo**: Confronto tra tipi incompatibili.

### Operatori Aritmetici (`-`, `*`, `/`, `%`)

**Nodo `BinOpNode` (op aritmetici)**:

- **IF** Il tipo di `left` è numerico (`rank` o `rate`) **AND** il tipo di `right` è numerico (`rank` o `rate`)
  - **THEN** L'operazione è valida e il risultato segue la promozione (se uno è `rate` -> `rate`, altrimenti `rank`).
- **ELSE**
  - **Errore di tipo**: Operandi non numerici.

## 8. Ciclo While (Stay)

**Costrutto Stay, nodo `WhileNode`**:

* **IF** Il tipo dell'espressione `condition` è `flag` (booleano)
  * **AND** Il corpo `block` è semanticamente valido
  * **THEN** Il costrutto `stay` è valido.
* **ELSE**
  * **Errore**: La condizione deve essere di tipo `flag` o errore nel corpo.

## 9. Ciclo For (Loop)

**Costrutto Loop, nodo `ForNode`**:

- **IF** L'istruzione di inizializzazione `init` è valida (tipicamente un `AssignNode`)
  - **AND** Il tipo dell'espressione `condition` è `flag`
  - **AND** L'aggiornamento `update` è valido (istruzione o espressione)
  - **AND** Il corpo `block` è valido
  - **THEN** Il ciclo `loop` è valido.
- **ELSE**
  - **Errore**: Condizione non booleana o componenti del ciclo non validi.

## 10. Istruzione di Uscita (Quit)

**Costrutto Quit, nodo `BreakNode`**:

- **IF** Il nodo appare annidato all'interno di un `WhileNode` (Stay) o `ForNode` (Loop)
  - **THEN** L'istruzione `quit` è valida.
- **ELSE**
  - **Errore**: `quit` usato fuori da un ciclo.

## 11. Funzioni (Action)

### Definizione

**Nodo `FunNode`**:

* **IF** Il nome `name` non è già dichiarato nello scope corrente (se non è overload)
  * **AND** I nomi dei parametri in `params` sono unici
  * **AND** Il corpo `body` è valido
  * **AND** (Se `ret_type` != `void`) Ogni percorso di esecuzione nel `body` termina con un `ReturnNode` con espressione compatibile con `ret_type`
  * **THEN** La definizione della funzione è valida e viene aggiunta all'ambiente $T$.
* **ELSE**
  * **Errore**: Firma non valida, corpo invalido o return mancante/errato.

### Chiamata

**Nodo `FuncCallStmtNode` (statement) / `FunCallExprNode` (espressione)**:

* **IF** La funzione `name` è definita in $T$ con firma (parametri $P_1, ..., P_n$)
  * **AND** Il numero di argomenti `args` è uguale a $n$
  * **AND** Per ogni $i$, il tipo dell'argomento $A_i$ è compatibile con il tipo del parametro $P_i$
  * **THEN** La chiamata è valida. (Il tipo è `ret_type` della funzione se espressione, o `void`/ignorato se statement).
* **ELSE**
  * **Errore**: Funzione non definita, numero argomenti errato o tipi incompatibili. 

## 12. Return (Reward)

**Costrutto Reward, nodo `ReturnNode`**:

* **IF** Il nodo appare all'interno di un `FunNode`
  * **AND** ( (`expr` è presente) **AND** (tipo di `expr` compatibile con `ret_type` della funzione) )
    **OR** ( (`expr` è assente) **AND** (`ret_type` è `void`) )
  * **THEN** L'istruzione `reward` è valida.
* **ELSE**
  * **Errore**: Return fuori funzione o tipo di ritorno non corrispondente.

## 