from setuptools import setup

long_desc = """Minilanguage for documenting human corrections to automated 
vocalization labels.

Also includes a stack-styled undo/redo container to keep track of edits
generated on-the-fly.

Designed to work with Bark-formatted event data."""

setup(name='eventedit',
      version='0.3',
      description='Keep track of manual edits to event data',
      long_description=long_desc,
      url='http://github.com/gfetterman/eventedit',
      author='Graham Fetterman',
      author_email='graham.fetterman@gmail.com',
      license='GPL',
      packages=['eventedit'],
      install_requires=['pyyaml',],
      zip_safe=False)
