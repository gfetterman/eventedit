# Event Edit

Minilanguage for documenting human corrections to automated vocalization
labels.

Also includes a stack-styled undo/redo container to keep track of edits
generated on-the-fly.

Designed to work with [Bark](https://github.com/kylerbrown/bark)-formatted event data.

## The EditStack

The `EditStack` structure mediates the user's interactions with the event data.
It can be used like a regular object, or placed within a context-managing `with`
statement.

The user calls `EditStack` methods representing the allowed operations on the
event data, and the edits are enacted and also stored, allowing easy undo and
redo.

When the user is finished editing the event data, they either leave the context
manager's scope, triggering a write of the operations representing the 
currently-enacted changes to a file, or (if the EditStack is being used without
the context manager) trigger the write to file manually.

The EditStack itself will only write operations representing the user's edits to
a file. The user is responsible for writing the (modified) label data to file
themselves.

When writing operations to disk, the EditStack creates two files: a textual
representation of the operations in a Lisp-like format, and a handful of
metadata that ensure corrections are only applied to the right labels. These
metadata include SHA-1 hashes of the labels before and after the operations in
the operations file are carried out. The metadata filename is that of the
operations file plus `.yaml`; it is, unsurprisingly, written in YAML syntax.

## Supported operations

The language describes a limited set of operations on interval labels:

1. Rename an interval: `EditStack.rename(index, new_name)`
2. Adjust an interval's boundaries: `EditStack.set_start(index, new_start)`
                                    `EditStack.set_stop(index, new_stop)`
3. Merge two consecutive intervals: `EditStack.merge(index)`
4. Split an interval in two: `EditStack.split(index, split_pt)`
5. Delete an interval: `EditStack.delete(index)`
6. Create a new interval: `EditStack.create(index, name, start, stop, **kwargs)`

Pseudo-Racket representations of the supported operations may be found in the
`examples.rkt` file above.

## Interaction with Bark

Corrections are assumed to operate on Bark-style event data - specifically,
interval data, having at least `start`, `stop`, and `name` columns. Any other
columns are ignored but preserved by the operations.

These event data are assumed to be represented in memory in the form of a list
of dictionaries.

Other than these assumptions, this tool relies on no knowledge of Bark,
including Bark metadata. The user is responsible for feeding event data to the
correction structure, and for writing any corrected event data to disk.

## Installation

The interface has been tested against both Python 2.7 and Python 3.5.

    git clone https://github.com/gfetterman/eventedit
    cd eventedit
    pip install .
    
    # optional tests
    pytest -v

## Usage

The pattern for usage of this tool is:

+ Create an `EditStack` object
+ Execute operations on the label data by applying stack operations.
+ Write the corrected label data back to Bark-formatted files.
+ Write the record of the corrections carried out by calling the stack's
  `write_to_file()` method, or rely on the context manager to do so.

## Python interface

The following is an example of use with already-loaded Bark event data.

    import eventedit as eved
    
    # bark event data: voc_labels
    
    with eved.EditStack(labels=voc_labels.data,
                        ops_file=(voc_labels.name + '.corr'),
                        load=False) as cs:
        cs.labels[55]['name']
        # 'a'
        cs.rename(index=55, new_name='b')
        cs.labels[55]['name']
        # 'b'
        
        cs.labels[56]['stop']
        # 77.5600
        cs.set_stop(index=56, new_stop=78.19988)
        cs.labels[56]['stop']
        # 78.19988
        
        cs.undo()
        cs.labels[56]['stop']
        # 77.5600
    # passing out of the context manager's scope triggers write of operations
    # to file - but not the modified label data themselves
    
    # EditStack doesn't write label data back to file
    # user is responsible for writing label data
    voc_labels.write()

## Minilanguage implementation and representation

Corrections stored in memory and on disk are structured in a Lisp-like prefix
notation. While the current language spec is extremely limited, this will
hopefully avoid restricting future extensions.

The choice of a Lisp-like representation also simplifies parsing. The
parser is a feature-sparse version of [Peter Norvig's `lispy`]
(http://norvig.com/lispy.html).
