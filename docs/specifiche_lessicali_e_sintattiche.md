# Specifiche Lessicali e Sintattiche - Play

Questo documento definisce le specifiche lessicali e sintattiche del linguaggio.

```ebnf
Program ::= DeclList FunctionDefs MainBlock "gameover"

DeclList ::= VarDecl DeclList | /* empty */

FunctionDefs ::= FunctionDef FunctionDefs | /* empty */

MainBlock ::= "play" Block

Block ::= "{" Stmts "}"

Stmts ::= Stmt Stmts | /* empty */

Stmt ::= Assign
       | IfStat
       | WhileStat
       | ForStat
       | InputStat
       | OutputStat
       | BreakStat
       | FuncCallStmt (come statement)
       | ReturnStat
       | VarDecl

VarDecl ::= Type ":" VarList

VarList ::= VarItem "," VarList
          | VarItem

VarItem ::= ID
          | ID "<--" Expr              
          | ID "=" VarItem       

Type ::= "rank"   /* int */
       | "rate"   /* double */
       | "flag"   /* bool */
       | "label"  /* string */

Assign ::= AssignDest "<--" Expr

AssignDest ::= ID
             | ID "=" AssignDest

```

```ebnf
FunctionDef ::= "action" ID "(" ParamList ")" "->" ReturnType Block

ReturnType ::= Type | "void"

ParamList ::= Param "," ParamList
            | Param
            | /* empty */

Param ::= Type ID

ReturnStat ::= "reward" Expr
             | "reward" "void"

InputStat ::= InputDestList "<--" "grab" Expr

InputDestList ::= InputDest "," InputDestList | InputDest

InputDest ::= ID "=" InputDest | ID

OutputStat ::= "drop" Expr

IfStat ::= "choice" "(" Expr ")" "->" Block ElifStat ElseStat

ElifStat ::= "retry" "(" Expr ")" "->" Block ElifStat
           | /* empty */

ElseStat ::= "fail" "->" Block
           | /* empty */

WhileStat ::= "stay" "(" Expr ")" "->" Block

ForStat ::= "loop" "(" Assign ";" Expr ";" (Assign | Expr) ")" "->" Block

BreakStat ::= "quit"

FuncCallStmt ::= ID "(" ArgList ")"

ArgList ::= Expr "," ArgList | Expr | /* empty */

Expr ::= LogicExpr

LogicExpr ::= CompExpr LogicOp LogicExpr | CompExpr
CompExpr  ::= SumExpr CompOp SumExpr | SumExpr
SumExpr   ::= ProdExpr SumOp SumExpr | ProdExpr
ProdExpr  ::= UnaryExpr ProdOp ProdExpr | UnaryExpr

UnaryExpr ::= UnaryOp UnaryExpr | BaseExpr

BaseExpr ::= "(" Expr ")"
           | INTEGER_CONST
           | REAL_CONST
           | STRING_CONST
           | BOOL_CONST
           | ID
           | FuncCallExpr
           | "-->" ID

LogicOp ::= "&&" | "||"
CompOp  ::= "==" | "<>" | "<" | "<=" | ">" | ">="
SumOp   ::= "+" | "-"
ProdOp  ::= "*" | "/" | "%"
UnaryOp ::= "!" | "-" | "+" | "-->"
```

## Specifiche Lessicali

PLAY "play"

GAMEOVER "gameover"

ACTION "action"

REWARD "reward"

VOID "void"

RANK "rank"

RATE "rate"

FLAG "flag"

LABEL "label"

TRUE "true"

FALSE "false"

GRAB "grab"

DROP "drop"

ASSIGN "<--"

EQUALS "="

CHOICE "choice"

RETRY "retry"

FAIL "fail"

STAY "stay"

LOOP "loop"

QUIT "quit"

PLUS "+"

MINUS "-"

MUL "*"

DIV "/"

MOD "%"

EQ "=="

NE "<>"

LT "<"

LE "<="

GT ">"

GE ">="

AND "&&"

OR "||"

NOT "!"

OUT_VAL "-->"

LBRACE "{"

RBRACE "}"

LPAR "("

RPAR ")"

COMMA ","

SEMI ";"

COLON ":"

ARROW "->"

ID espressione per identificatore

INTEGER_CONST espressione per numero intero

REAL_CONST espressione per numero reale

STRING_CONST espressione per stringa costante

i commenti vengono iniziati con // e terminano alla fine della riga
