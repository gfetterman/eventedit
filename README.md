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

Pseudo-Racket representations of the supported operations may be found in the
`examples.rkt` file above.

The stack container allows writing accumulated corrections to disk. Corrections
files are written in [YAML](http://yaml.org/). A stack can also be populated
from an already-existing corrections file.

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

    git clone https://github.com/gfetterman/labelcorrection
    cd labelcorrection
    pip install .
    
    # optional tests
    pytest -v

## Usage

The pattern for usage of this tool is:

+ Create a `CorrectionStack` object
+ Execute operations on the label data by applying stack methods.
+ Write the corrected label data back to Bark-formatted files.
+ Write the record of the corrections carried out by calling the stack's
  `write_to_file()` method.

## Python interface

The following is an example of use with already-loaded Bark event data.

    import labelcorrection as lc
    
    # bark event data: voc_labels
    
    with lc.CorrectionStack(labels=voc_labels.data,
                            event_file=voc_labels.path,
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
    
    # CorrectionStack doesn't write label data back to file
    # user is responsible for writing label data themselves
    voc_labels.write()