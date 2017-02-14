# Label Corrections

Minilanguage for documenting human corrections to automated vocalization
labels.

Also includes a stack-styled undo/redo container to keep track of corrections
generated on-the-fly.

Designed to work with [Bark](https://github.com/kylerbrown/bark)-formatted event data.

## Supported operations

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

The stack container allows writing accumulated corrections to disk. Corrections
files are written in [YAML](http://yaml.org/). A stack can also be populated
from an already-existing corrections file.

## Interaction with Bark

Corrections are assumed to operate on Bark-style event data - specifically,
interval data, having at least `start`, `stop`, and `name` columns. Any other
columns are ignored but preserved by the operations.

These event data are assumed to be represented in memory in the form of a list
of dictionaries.

Other than these assumptions, this tool relies on no knowledge of Bark. This
includes Bark metadata. The user is responsible for feeding label data to the
correction structure, and for writing any corrected event data to disk.