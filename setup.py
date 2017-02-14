from setuptools import setup

long_desc = """Minilanguage for documenting human corrections to automated 
vocalization labels.

Also includes a stack-styled undo/redo container to keep track of corrections
generated on-the-fly.

Designed to work with Bark-formatted event data."""

setup(name='labelcorrection',
      version='0.1',
      description='Keep track of manual label corrections',
      long_description=long_desc,
      url='http://github.com/gfetterman/labelcorrection',
      author='Graham Fetterman',
      author_email='graham.fetterman@gmail.com',
      license='GPL',
      packages=['labelcorrection'],
      install_requires=['pyyaml',],
      zip_safe=False)
