---
title: "exBASIC Compiler - BASIC compiler for the Atari 8-bit computers"
---

exBASIC Compiler
================

exBASIC is a cross compiler based on FastBasic by Daniel Serpell.  It turns one
BASIC source file into 6502 assembly, runs the CA65 assembler, and uses the
LD65 linker to build an Atari executable or cartridge image.


Installation
------------

Extract the exBASIC compiler into any folder.  The archive already contains
the CC65 tools it needs.


Basic Usage
===========

Pass a `.bas` file to `exbasic` to build an Atari executable (`.xex`):

- On Linux:

      /path/to/exbasic myprog.bas

- On Windows:

      C:\path\to\exbasic myprog.bas

Compiler targets
----------------
Select a target with `-t:`:

- `atari`: Builds an Atari 8-bit executable (`.xex`).  This is the default
  if no other target is selected.

- `atari-cart`: Builds an 8 KB Atari cartridge image (`.rom`).

Floating point support is included automatically, only when the program uses
floating point numbers.  In the same way, the compiled program includes only
the parts of the runtime used by the program.

This example produces a cartridge image:

     exbasic -t:atari-cart myprog.bas

Output files
------------

The final file is an `.xex` or `.rom`, depending on the target.  Its base name
comes from the BASIC source unless `-o` gives another name.

- `.xex`: Atari executable built by the `atari` target.

- `.rom`: Cartridge image built by the `atari-cart` target.

- `.lbl`: Linker labels, written when `-g` is used.

The compiler also creates intermediate files and normally removes them after
a successful build.  `-keep` preserves them:

- `.o`: Object files produced by CA65 and passed to the linker.

- `.asm`: Assembly generated from the BASIC source.

Advanced Usage
==============

Compilation has three steps:

- The compiler reads the BASIC source and produces an assembly file.

- The compiler calls the `CA65` assembler to produce an object file.

- The compiler calls the `LD65` linker to join the object file with the runtime
  library, generating the `XEX` or `ROM` depending on the target.

The compiler searches its installation folder and `EXBASIC_HOME` for target
files, syntax files, libraries and tools.

Passing options to the compiler
-------------------------------

Options with an argument accept either `:` or `=` as the separator.

- **-t**:*target*  
  Selects the compilation target.  The target definitions are searched in the
  compiler installation folder, with an `.tgt` extension.

  If this option is not given, the `default.tgt` file is loaded, currently this
  file simply includes the `atari.tgt` file.

- **-v**  
  Prints the compiler version and exits.

- **-n**  
  Disables the optimizer.  This is mainly useful when debugging an optimizer
  problem.

- **-no-ext**  
  Don't use the extended instructions.  By default the optimizer replaces
  common instruction sequences with faster combined instructions, for
  example a single
  instruction for `NEXT`, for array element addresses (`A(I)`), for storing
  a constant in an array element (`A(I)=1`) and for division by a constant
  power of two (`X/4`).  Inside `FOR` loops that do not use `PAUSE`, a
  division and a modulus with the same operands (`X/D` and `X MOD D`) only
  divide once.

  This makes loops and arithmetic substantially faster, but each extended
  instruction used adds its code (from 8 to about 120 bytes) to the runtime
  included in the program.  Use this option to get the smallest program.

  If a very big program would use more than the maximum of 127 different
  instructions, the compiler automatically retries without the extended
  instructions.

- **-no-native**, **-native:hot**, **-native:all**  
  Select the code compiled to 6502 machine code instead of bytecode.  The
  machine code covers the integer code: variables, constants, arithmetic,
  comparisons, `PEEK`/`POKE`, arrays, `INC`/`DEC`, multiplication and
  division, loop control and `FUNC` calls.  Statements without a machine code
  version (like `PRINT`, strings or floating point) stay as bytecode: the
  machine code switches to the interpreter for them and back.

  Machine code is several times faster than bytecode, but bigger.  Bytecode
  needs the interpreter routines of each instruction it uses, so a program
  that is all machine code can also be smaller than the same program as
  bytecode.

  - `-native:hot` compiles only the code that runs often: the compiler
    estimates how many times each statement runs from the loops around it
    (the number of iterations of `FOR` loops with constant limits, and the
    `FUNC` calls), and compiles the statements that run at least 64 times
    and at least 1/64 as often as the most frequent ones.
  - `-native:all` compiles all the code possible, for the fastest program.
  - `-no-native` compiles only to bytecode, for the smallest program when
    it is big.

  By default, the compiler builds the program with `-native:all`, with
  `-native:hot` and with a lean selection (the hot code without the loops
  where machine code saves little time, because they spend it in floating
  point, strings or I/O), each with and without the extended
  instructions, and keeps the smallest one: integer code typically runs
  2 to 6 times faster than bytecode, and small programs are often smaller
  than with bytecode only.

- **-I**:*path*  
  Adds a folder to search for files included with `INCLUDE`.  Files are
  searched first in the folder of the including file, then in the folders
  given with this option, then in an `include` folder inside the compiler
  folder, if you create one for your own libraries.

- **-prof**  
  Prints bytecode token and token-pair statistics.  To find where a running
  program spends its time, use the `exbprof` tool in the test suite.

- **-g**  
  Generates a label file (`.lbl`) and an assembly listing for each source
  (`BAS` or `ASM`).

- **-o** *file*  
  Sets the output name.  A space is optional, so `-o prog.xex` and
  `-oprog.xex` mean the same thing.

- **-d**  
  Enables parser diagnostics, including the parse tree and attempted rules.
  This is noisy and mainly useful when working on the parser.

- **-l**  / **-l**:*extension*
  In addition to compiling the file, also write a prettified version of the
  input program, with all abbreviations expanded, one statement per line and
  indented code.  This listing will be saved to a file with the same name as the
  input and given extension, or `.list` if no extension is supplied.
  This is useful for examining compiler errors in heavily abbreviated code.

- **-ls** / **-ls**:*num*
  Instead of writing an expanded version of the program to the listing file,
  writes a short, minimized and abbreviated version, joining statements until
  the line reaches *num* characters.  Without *num*, the limit is 120.  This
  is meant for size-coding experiments.

  **WARNING**: Compile and test the minimized version.  The minimizer doesn't
  run the full parser and can write invalid code.  It also doesn't remove
  redundant parentheses or join `DATA` statements, so those changes are still
  manual.

- **-h**  
  Prints the available compiler options and exits.

- **-C**:*linker-file.cfg*  
  Uses a different linker configuration file.  The default is `exbasic.cfg`.

- **-S**:*address*  
  Sets the start address of the compiled binary.  The default value is `$2000`,
  set in the configuration file `exbasic.cfg`.  You can specify a different
  address to allow for a bigger DOS, or to have more memory available if you
  don't use a DOS.  The address can be specified as decimal or hexadecimal with
  `0x` at front.  A program that would load over the DOS (start below MEMLO)
  or past MEMTOP is not loaded: it prints `ERROR- 19` and returns
  to DOS.  For cartridge images (`-t:atari-cart`), it sets the start of
  the RAM used for the variables and data instead.

- **-c**  
  Only compile: write the assembly file (`.asm`) and stop, without assembling
  or linking.  See section "Extending the language".  Without linking, the
  compiler can't compare program sizes, so the default machine code mode is
  `-native:hot`.

- **-X**:*ca65-option*  
  Passes the given option to the CA65 assembler.  See the CA65 documentation for
  valid options.  Some useful options are listed below:

  - **-X:-I***path*  
    Adds a path to search for assembly included files, used in your custom ASM
    sources.

  - **-X:-D***symbol*  
    Define an assembly symbol, used in custom ASM sources.

  When using `-X:` you can't use spaces between assembler options.  Use multiple
  `-X:` for each space separated argument.  For example, you can use
  `-X:-I -X:path ` as two options or `-X:-Ipath`, as both will pass the same
  option and value.

- **-s**:*segment_name*  
  Sets the name of the "section" where the compiler will place the generated
  code.  The default segment is `BYTECODE`.  If you change the segment you must
  ensure that there is a segment with that name in the linker configuration.

- **-DL:***symbol=value*  
  Defines the linker symbol with the given value.  This is used to pass options
  to the linker that alter the configuration.

  For example, passing `-DL:__CARTFLAGS__=4` when using a cartridge target
  changes the cartridge flags, so the cartridge does not boot the disk.

- **-target-path**:*path*  
  Sets the list of paths where the target definition files are searched, as a
  list of folder names separated by `:`.

  The default is to search in the same folder as the compiler executable, and
  in the path in the `EXBASIC_HOME` environment variable.

- **-syntax-path**:*path*  
  Sets the list of paths where the syntax grammar files are searched, as a list
  of folder names separated by `:`.

  The default path is the same as the target path with `syntax` folder at the
  end.

- **-keep**  
  Do not remove the intermediate files on compilation.

Linking other assembly files
----------------------------

The compiler supports linking to external assembly modules.  You can pass them
on the `exbasic` command line:

    exbasic myprog.bas myasm.asm

This will compile `myprog.bas` to `myprog.asm` and then assemble the two files
together using CA65 and LD65.  You can pass multiple `.asm` (or `.o`) files on
the command line.  All the files will be assembled and linked together.
Only one BASIC file can be in a program: add other BASIC files with
`INCLUDE`.

From the exBASIC source, you can reference any symbol via `@name`, for example:

    ' exBASIC code
    '
    ? "External USR sample:"
    ? USR( @Add_10, 25 )

The ASM file must export the `ADD_10` (always uppercase) symbol, for example:

```Assembler
    ; Assembly module
      .export ADD_10

    .proc ADD_10
      pla   ; Parameters are passed on the stack, in reverse order
      tax
      pla
      clc
      adc #10
      bcc no
      inx
    no:
      ; Return value in A/X registers
      rts
    .endproc
```

You can also export ZP symbols, to import them use `@@name`.


Extending the language
----------------------

The exBASIC compiler is extensible.  The syntax is read at compilation time
from various files with the grammar and compilation rules (the `.syn` files in
the `syntax` folder).

The following sections show how to add simple functions and statements to the
language.  You can look at the existing syntax files for more advanced usage.


### Adding new functions

Suppose you want to add new functions to the language, to check if a console
key is pressed:

- `CSTART()`  : Returns 1 if the *START* key is pressed,
- `CSELECT()` : Returns 1 if the *SELECT* key is pressed,
- `COPTION()` : Returns 1 if the *OPTION* key is pressed,

To implement the functions above, the following exBASIC code could be used:

|Function| Equivalent Code           |
| ------ | ------------------------- |
| CSTART | `NOT (PEEK(53279) & 1)` |
| CSELECT| `NOT (PEEK(53279) & 2)` |
| COPTION| `NOT (PEEK(53279) & 4)` |

#### 1. Create a new target

First, you need to create a new target, let's call it `atari-extra`.  Create a
file in the exBASIC compiler folder named `atari-extra.tgt`, with the
following contents:

    include atari
    syntax console.syn

The first line reads the `atari` target, so the new target will have
all the definitions already in the standard target.

The second line adds a new syntax from the file `console.syn`.  This will be
appended to the syntax in the standard `atari` target.

#### 2. Create a new syntax file

Now, create a `console.syn` file inside the syntax folder, with the following
content inside:

    INT_FUNCTIONS:
         "CSTART()"
         "CSELECT()"
         "COPTION()"

This defines three new functions, without parameters, and without any code
generated.  You could now compile a simple program, but the resulting executable
will not run because the code for the functions is missing.

To add the code, you need to inspect the code generated for our test examples
and then use the `emit` keyword in the `console.syn` file to generate bytecode
based on what you found.

#### 3. Adding code for the new functions

Compile a small BASIC expression to assembly:

    PRINT NOT (PEEK(53279) & 1)

Use `exbasic -c simple.bas` and examine the generated assembly file.  You
will see the following bytecode at the end:

    TOK_NUM
    53279
    TOK_PEEK
    TOK_PUSH_1
    TOK_BIT_AND
    TOK_COMP_0
    TOK_L_NOT
    TOK_INT_STR
    TOK_PRINT_STR

The bytecode follows the BASIC source fairly closely:

- Load number `53279`
- `PEEK` into that location
- Load number `1`
- Perform the `&` operation
- Compare the result with `0`
- Negate the result.
- Convert to string and `PRINT`.

We need to generate similar code for the `CSTART()` function.  To do that, edit
the `console.syn` file, and add the emitted code:

    INT_FUNCTIONS:
         "CSTART()"   emit { TOK_NUM, &53279, TOK_PEEK, TOK_PUSH_1, TOK_BIT_AND, TOK_COMP_0, TOK_L_NOT }
         "CSELECT()"  emit { TOK_NUM, &53279, TOK_PEEK, TOK_PUSH, TOK_BYTE, 2, TOK_BIT_AND, TOK_COMP_0, TOK_L_NOT }
         "COPTION()"  emit { TOK_NUM, &53279, TOK_PEEK, TOK_PUSH, TOK_BYTE, 4, TOK_BIT_AND, TOK_COMP_0, TOK_L_NOT }

Note that the `emit` code needs to be on one line.  The `&` symbol before
the `53279` indicates a 16-bit word value (two bytes) instead of a single byte.

#### 4. Testing the new language extensions

Now, you can compile this simple test program:

    ? "Press console keys,"
    ? "or any other key to exit:"
    REPEAT
     MSG$=""
     IF CSTART()  THEN MSG$=+"START "
     IF CSELECT() THEN MSG$=+"SELECT "
     IF COPTION() THEN MSG$=+"OPTION"
     IF MSG$ <> "" THEN ? MSG$
    UNTIL KEY()

Compile with:

    exbasic -t:atari-extra myprog.bas

#### 5. Refactoring the code

Instead of writing the full code for each function, you can rearrange the code
to make the syntax smaller, and use constants to make it more generic, by
defining a new syntax table:

    SYMBOLS {
        CONSOL = $D01F
    }

    READ_CONSOLE:
         "()" emit { TOK_PUSH, TOK_NUM, &CONSOL, TOK_PEEK, TOK_BIT_AND, TOK_COMP_0, TOK_L_NOT }

    INT_FUNCTIONS:
         "CSTART"   emit { TOK_1 }       READ_CONSOLE
         "CSELECT"  emit { TOK_BYTE, 2 } READ_CONSOLE
         "COPTION"  emit { TOK_BYTE, 4 } READ_CONSOLE

Note the use of the symbol `CONSOL` instead of the number, and the rearranging
of the code to be more concise. 

Read more about bytecode in "Understanding the syntax files".


### Adding new statements

To add new statements, instead of expanding the table `INT_FUNCTIONS`, you need
to expand the table `STATEMENT`, but the logic is the same.

Also, to interface the interpreter with new assembly functions, you can `emit`
code similar to an `USR()` call, and process the parameters in the assembly.

Let's implement a new statement, `WAIT` that can wait for a vertical line in
the screen.

The simple assembly version of this statement would be:

```Assembler
    .export DO_WAIT
    .include "atari.inc"

    DO_WAIT:
        ; Line number is in accumulator already
    loop:
        cmp VCOUNT
        bcc loop
        rts
```

Save this file as `wait.asm`.

Now, we can edit our `atari-extra.tgt` target file, and add a new syntax file
to it:

    include atari
    syntax console.syn wait.syn

As in the first example, add a `wait.syn` syntax file:

    SYMBOLS {
        DO_WAIT = import
    }

    STATEMENT:
        "WAit" emit { TOK_NUM, &DO_WAIT, TOK_USR_ADDR} EXPR emit { TOK_USR_CALL }

Now, you can compile this simple example:

    DO
      WAIT 40
      POKE $D018, $36
      WAIT 80
      POKE $D018, $C8
    LOOP

The command line to compile should be:

    exbasic -t:atari-extra testw.bas wait.asm

Testing the resulting file, you should see three color zones on the screen.

There are a few details worth explaining:

- The `"WAit"` string is specified with mixed case.  The lower-case characters
  denote "optional" part of the name, so you can abbreviate this new statement
  as "WA." or "WAI.".

- We are loading the `DO_WAIT` address into the `USR` calling address as the
  first step in the generated code.  This is needed to be able to call the
  assembly code without a parameter in the accumulator.

- To get the value of the symbol `DO_WAIT`, we need to specify `import` as the
  symbol value.  This means the value will be filled by the linker.

- The `EXPR` rule accepts an integer expression.  Its result is left in the
  `A` and `X` registers.


### Syntax of the Target files

The target files (with `.tgt` extension) allow us to change many aspects of the
compilation process.

The syntax of the files is line oriented, with one command per line.  The list
of commands is the following:

- `#`: A line that starts with a hash is a comment.  The rest of the
       line is ignored.

- `include`: Includes all the target definitions for the named file.  If the
             file name given does not have an extension, `.tgt` is added.

- `library`: Gives the name of the library to link with a compiled exBASIC
             program for this target. Only one library file is allowed. The
             last one read takes precedence.

- `config`: Gives the name of the linker configuration file used for this
            target.

- `extension`: Gives the extension of the compiled file for this target.

- `ca65`: Gives a list of options to pass to the `CA65` assembler.  Multiple
          options are appended after existing assembler options.

- `syntax`: Gives a list of syntax files to read, defining the syntax of all
            the language. Multiple files are read in the order given, and
            all definitions are merged together.


### Understanding the Syntax files

The syntax files (with `.syn` extension) define the full parsing rules of the
exBASIC language.  There are no predefined rules in the parser.  The whole
language is defined in the included `.syn` files.

In the top level, the syntax files are composed of *tokens*, *symbols*,
*external routines* and *rules*.

The *tokens* are a list of bytecode language instructions available to the
parser for the compiled code.  The exBASIC interpreter supports up to 128
tokens.  Most implement core functionality (like adding two numbers, or loading
the value of a variable, etc.).  The tokens are listed in a special `TOKENS`
section:

    TOKENS {
       token-1, token-2
       token-3
       ...
    }

The *external routines* are routines that can be called from the parser to
parse special constructs, or modify compiler state outside the parser.  Examples
are adding a variable to the list of variables, checking if a variable name is
already defined, parsing a number or string, etc.  The external routines are
listed in a special `EXTERN` section:

    EXTERN {
       name_1, name_2
       name-4
       ...
    }

There is an important external rule `E_EOL` that matches at the end of the
input line.

All external routines used in the parser need to be implemented in the
compiler in C++ (see `src/compiler/parser-actions.cc`), or the parser will
fail.

The *symbols* are a list of symbols available to the parser to use for the
compiled code.  This allows the parser to include names instead of numeric
constants for the compiled code, and allows using symbols from the library.

The named *rules* define a part of the syntax that the parser understands.  They
are defined using a name followed by a colon:

    NAME: rule description
        pattern-1
        pattern-2
        ...

The *NAME* of the rule must start with a letter, and can contain any number of
letters, numbers or underscores.  On the other hand the *rule description* is
one line of any text that is shown when the parser encounters a syntax error
when expecting this rule.

Each *pattern* defines a possible parse for this rule.  Each pattern is tried
from the first to the last, and the first pattern that matches allows the rule
to match.  If after trying all the patterns, the last one does not match, the
rule fails to match.

The patterns must be in one line, and must begin with at least one space to
differentiate from a rule definition.

The patterns can contain the following:

- Text enclosed in double quotes (`"`).  The rule matches if all the text in the
  quotes matches the input, ignoring case - the parser is case insensitive.

  The exBASIC parser also supports abbreviations: Any lower-case letter in the
  quoted text is optional, if in that place of the input is a dot, the rest of
  the quoted text is skipped.

  For example, the pattern `"HEllo!!"` matches the text `HELLO!!`, `HE.`,
  `HEL.` or `HELL.`.

- The name of a rule.  This matches if the rule matches here.

- The name of an external rule.  This matches if called code returns true.

- The word `emit` followed by a token, symbol or number.  This instructs the
  parser to output the given token, symbol or number to the compiler.  The
  symbols and numbers produce one byte in the output, except when the symbol
  is prepended with an ampersand (`&`) that produces two bytes (a `word`).

  You can also follow the `emit` with a list of symbols enclosed in curly
  braces ( `{` and `}` ).

The last pattern in a rule can also be the special word `pass`.  This makes the
parser accept the rule even if no other pattern matched, effectively making
the rule optional.

Finally, there is a special rule named `PARSE_START` that the parser calls for
each line in the input.

The parsing rules use a simplified form of PEG grammar syntax.  The following
patterns show the equivalent exBASIC syntax:

- An optional rule `RULE ?`:

      RULE_OPT:
        RULE
        pass

- An optional and repeatable rule `RULE *`:

      RULE_OPT_REP:
        RULE RULE_OPT_REP
        pass

- A repeatable rule `RULE +`:

      RULE_REP:
        RULE RULE_MORE

      RULE_MORE:
        RULE RULE_MORE
        pass


