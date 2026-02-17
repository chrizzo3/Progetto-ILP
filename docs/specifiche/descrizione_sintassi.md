# Manuale ed Esempi - Play

## Descrizione del Linguaggio

**Play** è un linguaggio imperativo tipizzato con una sintassi ispirata ai videogiochi.

### Struttura Generale

Il programma deve avere necessariamente il blocco principale di esecuzione `play` e termina con la fine del file con la keyword `gameover`.
Tutte le variabili hanno uno scope globale.

```javascript
// Dichiarazioni Variabili e/o Definizioni di Funzioni ...


play{ // Blocco principale

    // Codice...

}

gameover //EOF
```

### Tipi di Dati

- **rank**: Interi (`int`).
- **rate**: Numeri reali (`double`).
- **flag**: Booleani (`bool`).
- **label**: Stringhe (`string`).
- **void**: Tipo nullo.

### Variabili (Scope Globale)

Tutte le variabili sono visibili ovunque.

#### Dichiarazioni e Assegnazioni di Variabili

Le variabili possono essere dichiarate accorpandole sotto lo stesso tipo separate da virgole:

```javascript
rank: a, b,c
```

Possono essere inizializzate e/o assegnate con valori o variabili utilizzando `<--`:

```javascript
// a e b inizializzate allo stesso valore 4.5
// c inizializzata a 7
rate : a = b <-- 4.5, c <-- 7

// OPPURE

// a solo dichiarato, b e c inizializzate
rate : a,b <-- 4.5, c <-- 7

// OPPURE


label : a <-- "Hello", c <-- "World"
    // codice...
label : b <-- a // b avrà valore "Hello"
b <-- c // b avrà valore "World"


// ERRORE. Quando si inizializzano due variabili e si cerca di copiare 
// il valore dell'ultima nella precedente nella stessa riga
rate : b <-- 4.5 = c <-- 7
```

### Funzioni

Le funzioni possono avere zero o più parametri in input ed un solo un valore di ritorno (obbligatorio).
Vengono definite con `action`. Per ritornare un valore si usa `reward`. Se la funzione è void, si usa `reward void`.

Esempio di dichiarazione di una funzione:

```javascript
action FunzioneRitornaRank() -> rank {
    rank: n
    n <-- 5

    reward n // ritorna il valore 5
}



action FunzioneVoid(rank points) -> void {
    score <-- score + points
    reward void
}
```

### Controllo di Flusso

- **If - elseif - else**
  
  Sintassi: 
  
  ```javascript
  choice (cond) -> { 
      // if
  } retry (cond2) -> {
      // else if
  } fail -> {
      // else
  }
  ```

- **While**
  
  Sintassi:
  
  ```javascript
  stay (cond) -> {
      // corpo
  }
  ```

- **For**
  
  Sintassi:
  
  ```javascript
  rank: a
  loop (a <-- 0; a < 6; a+1) -> {
      // corpo
  
      quit //break
  
      // corpo (continua)
  } 
  ```

`quit` viene utilizzato per uscire dal corpo.

### Input

L'input si esprime con l'operatore `grab`.

```javascript
rank: d
label: a
// d e a prendono rispettivamente un intero e una stringa
d,a <-- grab "Inserisci " + " un numero intero e una stringa" 

rank: a,d
// sia a che d prendono lo stesso intero
a = d <-- grab "Inserisci un numero intero: " 
```

#### Nota

L'operatore `+` viene utilizzato per concatenare

### Output

L'output si esprime con l'operatore `drop`. Per stampare un valore di una variabile si utilizza `-->`

```javascript
rank: d <-- 5
drop "Questa è una stampa del valore della variabile d: " + -->d
// Stampa in output attesa: 
// Questa è una stampa del valore della variabile d: 5


rank: c <-- 2
label: a <-- "Ciao"
drop "La somma è " + -->(d+c) + " " + --> a
// Stampa in output attesa: 
// La somma è 7 Ciao
```

---

## Esempi di Codice

### Esempio 1: Gameplay Loop

```javascript
// Variabili
rank : score <-- 0
rank : level <-- 1
flag : isRunning <-- true

// Dichiarazione Funzione (deve usare reward)
action UpdateScore(rank points) -> void {
    score <-- score + points
    reward void
}

// Blocco Principale
play {
    drop "Gioco Iniziato!"

    stay (isRunning) -> {
        rank : inputVal // sarà comunque accessibile da ovunque       
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
```
