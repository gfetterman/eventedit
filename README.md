# Label Corrections

Minilanguage for documenting human corrections to automated vocalization
labels.

Designed to work with [Bark](https://github.com/kylerbrown/bark)-formatted data.

## Minilanguage specification

The language describes a limited set of operations on interval labels:

1. Rename an interval
2. Adjust an interval's boundaries
3. Merge two consecutive intervals
4. Split an interval in two
5. Delete an interval
6. Create a new interval

## Minilanguage implementation and representation

Corrections stored in memory and on disk are structured in a Lisp-like prefix
notation. While the current language spec is extremely limited, this will
hopefully avoid restricting future extensions.

The choice of a Lisp-like representation also simplifies parsing. The
parser is a feature-sparse version of [Peter Norvig's `lispy`]
(http://norvig.com/lispy.html).