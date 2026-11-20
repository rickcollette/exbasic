# Third-Party Software and Derived Code

exBASIC contains tools and code from other projects.  This file says what
they are, where they came from and where their actual license notices live.
It is an attribution index, not a replacement license (because rewriting a
license in a friendlier format does not make it the license).

The original copyright notices, source headers and license files remain in
force.  If this file disagrees with one of them, use the original notice.
The exBASIC project license does not remove or replace any of those terms.

## FastBasic

exBASIC is a modified version of
[FastBasic](https://github.com/dmsc/fastbasic), written by Daniel Serpell.
The FastBasic-derived compiler, runtime, syntax definitions and related code
carry the FastBasic copyright and GNU General Public License notice found in
their source headers.

- **Copyright:** Copyright (C) 2017-2025 Daniel Serpell
- **License:** GNU General Public License, version 2 or later
- **Local notice:** [compiler/LICENSE](compiler/LICENSE)

The runtime notice includes an additional linking exception.  That exception
allows the compiled runtime to be linked into programs and the resulting
programs to be distributed without GPL restrictions arising from use of the
runtime.  Read [compiler/LICENSE](compiler/LICENSE) for the actual terms (the
short version here is only here to help you find the right bit).

## Bundled Tools

### CC65 tools

The `cc65/` directory contains the CA65 assembler, LD65 linker, AR65 archiver,
support code and assembly include files from the
[CC65 project](https://github.com/cc65/cc65).  The source files retain their
original notices, including the copyright of Ullrich von Bassewitz and other
CC65 contributors where applicable.

- **License:** zlib-style CC65 license
- **Local license:** [cc65/LICENSE](cc65/LICENSE)

### mkatrgo / atr

The `third_party/mkatrgo/` directory contains
[mkatrgo](https://github.com/rickcollette/mkatrgo), the Go `atr` tool used by
exBASIC to build and inspect Atari disk images.  Its SpartaDOS/BW-DOS code is
a Go port of Daniel Serpell's [mkatr](https://github.com/dmsc/mkatr).

- **Copyright:** Copyright (C) 2016-2026 Daniel Serpell and the mkatrgo
  contributors, with the applicable notices retained in the source files
- **License:** GNU General Public License, version 2 only
- **Local license:** [third_party/mkatrgo/LICENSE](third_party/mkatrgo/LICENSE)
- **Local notice:** [third_party/mkatrgo/NOTICE.md](third_party/mkatrgo/NOTICE.md)

### Mini65

The test suite contains Mini65, Daniel Serpell's small 6502 simulator with an
Atari 8-bit BIOS.  It lives under `testsuite/mini65/` and is used by the test
and profiling type stuff; it is not part of the compiler runtime installed in
an Atari program.

- **Copyright:** Copyright (C) 2017-2026 Daniel Serpell, with the applicable
  year ranges retained in individual source files
- **License:** GNU General Public License, version 2 or later, as stated in
  the source headers
- **Local license:** [testsuite/mini65/LICENSE](testsuite/mini65/LICENSE)

## Copied or Adapted Code

### Altirra BASIC floating-point routines

Two floating-point runtime routines identify Altirra BASIC as their source:

- `src/interp/atarifp/fp_sqrt.asm` says its square-root implementation was
  copied from Altirra BASIC and retains `Copyright (C) 2015 Avery Lee, All
  Rights Reserved.`
- `src/interp/atarifp/fp_rnd.asm` says its random-number implementation is
  based on Altirra BASIC and retains `(C) 2015 Avery Lee.`

[Altirra](https://www.virtualdub.org/altirra.html) and its source code are
published by Avery Lee.  The official project page identifies the Altirra
source distribution as GNU GPL version 2.  The comments in the two local
files are the notices carried with these particular adaptations; neither this
index nor the surrounding FastBasic header is meant to erase them.

### CCAN `likely.h`

`testsuite/mini65/ccan/likely.h` comes from the
[CCAN likely module](https://github.com/rustyrussell/ccan/tree/master/ccan/likely).
The retained header identifies it as CC0 (public domain).  CCAN's corresponding
license file is included at
[testsuite/mini65/ccan/LICENSE](testsuite/mini65/ccan/LICENSE).  The upstream
copy is also available from [CCAN](https://github.com/rustyrussell/ccan/blob/master/licenses/CC0).

### ATASCII to UTF-8 conversion table

The diagnostic character table in `testsuite/src/exbtest.c` is adapted from
Daniel Serpell's `conv-atascii-utf8.c`, originally posted with the
[AAC ASCII/ATASCII converter](https://forums.atariage.com/topic/245258-aac-ascii-atascii-converter-for-our-modern-computers/?do=findComment&comment=3359509).
The table is inside a FastBasic test source file carrying the GNU GPL version
2-or-later header.  No separate license notice for the table is included in
this source tree, so this entry records the derivation instead of inventing
one.

## Project License

Original exBASIC material is covered by [LICENSE](LICENSE).  That license
explicitly excludes separately licensed third-party material.  In other
words, read this file as a map to the notices above, then keep those notices
with the code they apply to.
