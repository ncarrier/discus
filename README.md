# Discus

## Overview

Discus is a program to display hard drive space usage, much like the standard
UN*X command df.

Discus aims to make df(1) prettier.
Features include color, bar graphs, and smart formatting of numbers
(automatically choosing the most suitable size from kilobytes, megabytes,
gigabytes, or terabytes). Or choose your own size, along with specifying the
number of decimal places you'd like to see.

To configure Discus on a system-wide basis, edit the **/etc/discusrc** file. 
But you should probably change things just for yourself, by copying
**/etc/discusrc** to **~/.discusrc** and editing that.

The source code is contained in the discus.py file itself, as it is a Python
code encapsulated in a shell script.

Stormy Henderson, the original author, said:

> Yes, I chose the name Discus because of the similarity to "disk use."
> And no, I didn't misspell discuss.
> A discus is a round thingie people throw.

Newest versions of Discus may be found at:
https://github.com/ncarrier/discus

## Dependencies

Python 3.6 or above.

## Usage

Usually:

```
./discus.py
```

should be sufficient.

Please do:

```
./discus.py --help
```

for more information.

## Installation

```
cp discus.py /usr/local/bin
chmod a+rx /usr/local/bin/discus
cp discusrc /etc
chmod a+r /etc/discusrc
gzip -9 discus.1
cp discus.1.gz /usr/local/man/man1
chmod a+r /usr/local/man/man1/discus.1.gz
```

## Test

### Unit tests

Only a few unit tests exist at the time of writing, but one has to start
somewhere :)

```
python3 -m unittest discus.py -v
```

### Pre-commit tests

The `tests/pre-commit.sh` script allows to perform tests prior of committing.
You can run it directly or even better, install it as a git hook script by
running:

```
ln -s ../../tests/pre-commit.sh .git/hooks/pre-commit
```

## Coding style

The source code follows the PEP8 coding style, which can be checked with, for
example, the `pep8` or the `flake8` command-line tools in debian.

## Known bugs

These problems remain unfixed as of this release:

 * RedHat 6.0 Commerce with RH 6.1 Python outputs all zeros (reported by
   Jerrad Pierce)
 * The known bugs list hasn't been checked :)

## To do

Simple things I'm considering adding to Discus:

 * Adapt the width to the terminal's display.
 * Choose your own column labels.
 * Compact option to squeeze in everything including device name.
 * A Makefile for non-Debian users, or rather, setuptools support.

Complicated things I'm considering adding to Discus:

 * Add du(1) functionality to combine both disk usage functions into
     one software package.

Want your wish added? Please open an issue.
