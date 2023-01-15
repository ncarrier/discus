#!/usr/bin/python3

# Discus is a program that reports hard drive space usage.

# Copyright 2000 Stormy Henderson (stormy@futuresouth.com).
# Copyright 2019-2021 Nicolas Carrier (carrier.nicolas0@gmail.com).
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307
# USA.
import subprocess
import os
import sys
import re
import copy
import shutil
from collections import namedtuple
import argparse
from argparse import RawTextHelpFormatter


# These colors should work on VT100-type displays and can be overridden by the
# user.
black = "\033[30m"
red = "\033[31m"
green = "\033[32m"
yellow = "\033[33m"
blue = "\033[34m"
magenta = "\033[35m"
cyan = "\033[36m"
white = "\033[37m"

on_black = "\033[40m"
on_red = "\033[41m"
on_green = "\033[42m"
on_yellow = "\033[43m"
on_blue = "\033[44m"
on_magenta = "\033[45m"
on_cyan = "\033[46m"
on_white = "\033[47m"

normal = "\033[0m"
bold = "\033[1m"
underline = "\033[4m"
blink = "\033[5m"
reverse = "\033[7m"
dim = "\033[8m"

opts = {
    "placing": True,
    "reserved": True,
    # Labels to display next to numbers.
    "akabytes": ["KB", "MB", "GB", "TB", "PB", "EB"],
    "color": 1,
    # Power of 1024, smallest value is 0, for KB, used only when smart
    # formatting is disabled, overridden by -t, -g, -m and -k options
    "divisor": 1,
    "graph": 1,
    "graph_char": "*",
    "graph_fill": "-",
    # Example mtab entry that uses a shell command (always use a ! as
    # first character) rather than a file:
    #        !/bin/mount |awk '{print $1, $3}'"
    "mtab": "/etc/mtab",
    #  Number of decimal places to display, same as -p
    "places": 1,
    # Filesystems to ignore.
    "skip_list": ["/dev/pts", "/proc", "/dev", "/proc/usb", "/sys"],
    #  Use smart formatting of numbers.
    "smart": 1,
    "color_header": blue,
    "color_normal": normal,
    "color_safe": normal,             # 0%- 70% full
    "color_warning": bold + yellow,   # 70%- 85% full
    "color_danger": bold + red        # 85%-100% full
}

HOMEPAGE = "https://github.com/ncarrier/discus"
VERSION = "0.5.0"
MINIMUM_WIDTH = 68

# values taken from sysexit.h
EX_OK = 0
EX_USAGE = 64
EX_CONFIG = 78


class StatsFactory:
    """Factory class to get statistics about a mount point."""
    Stats = namedtuple('Stats', ['total', 'free', 'used'])

    def __init__(self, reserved):
        """Constructor, initialize private fields."""
        self.__reserved = reserved

    def getStats(self, mount):
        """Gather statistics about specified filesystem."""
        try:
            stats = os.statvfs(mount)
        except PermissionError:
            return StatsFactory.Stats(total="-", free="-", used="-")

        total = stats.f_blocks * stats.f_frsize
        # if we have to take care of reserved space for root, then use
        # available blocks (but keep counting free space with all free blocks)
        if self.__reserved:
            free = stats.f_bavail * stats.f_frsize
        else:
            free = stats.f_bfree * stats.f_frsize
        used = total - stats.f_bfree * stats.f_frsize

        return StatsFactory.Stats(total=total, free=free, used=used)


class SizeFormatter:
    """
    Class responsible of formatting sizes, smartly or not.
    if opts["smart"] is false, divisor will be used to divide the size to the
    corresponding unit, that is 0 -> KB, 1 -> MB... Supposing that the size is
    fed in kilo bytes.
    """
    DEFAULT_AKABYTES = ["KB", "MB", "GB", "TB", "PB", "EB"]
    # helper class for manipulating options
    Options = namedtuple("Options", ["smart", "placing", "akabytes", "places",
                                     "divisor"])
    Options.__new__.__defaults__ = (True, True, DEFAULT_AKABYTES, 1, 1)

    def __init__(self, smart, placing, akabytes, places, divisor):
        """Constructor, initialize private fields."""
        self.__smart = smart
        self.__placing = placing
        self.__akabytes = akabytes.copy()
        self.__places = places
        self.__divisor = divisor
        # Is smart display enabled?
        self.__formatter = (self.__smart_format if self.__smart
                            else self.__manual_format)

    def format(self, size):
        """
        Format the size for human use.
        size: size in kilobytes.
        """
        size, divisor, places = self.__formatter(size)
        if size == 0:
            places = 0
        unit = self.__akabytes[divisor]

        # And now actually format the result.
        result = f"{size:0.{places}f} {unit}"

        return result

    def __smart_format(self, size):
        """
        Use smart formatting, which increases the divisor until size is 3 or
        less digits in size.
        """
        # Keep reducing digits until there are 3 or less.
        count = 0
        while size > (0.9999999999 * pow(10, 3)):
            # But don't let it get too small, either.
            if (size / 1024.0) < 0.05:
                break
            size = size / 1024.0
            count = count + 1

        # Display a proportionate number of decimal places to the number of
        # main digits.
        if not self.__placing:
            if count < 2:
                fudge = count
            else:
                fudge = 2
        else:
            # User specified how many decimal places were wanted.
            fudge = self.__places

        return size, count, fudge

    def __manual_format(self, size):
        """
        We're not using smart display, so figure things up on the specified
        KB/MB/GB/TB basis.
        """
        divisor = self.__divisor
        size = size / pow(1024.0, divisor)

        return size, divisor, self.__places


Mount = namedtuple('Mount', ['mount', 'device'])


class DiskData:
    """
    Class representing a disk's data, formatted for output, in string form.
    """
    Base = namedtuple('BaseDiskData',
                      ['percent', 'total', 'used', 'free', 'mount', 'device'])

    @staticmethod
    def get(stats, percent, mount, size_formatter):
        """Factory method returning a BaseDiskData instance."""
        sf = size_formatter
        if not isinstance(percent, str):
            percent = f"{percent:.1f}%"
            total = sf.format(stats.total / 1024)
            used = sf.format(stats.used / 1024)
            free = sf.format(stats.free / 1024)
        else:
            total = stats.total
            used = stats.used
            free = stats.free
        return DiskData.Base(percent,
                             total,
                             used,
                             free,
                             mount.mount,
                             mount.device)


class Disk:
    """Contains everything needed to represent a disk textually."""

    def __init__(self, mount, stats_factory, size_formatter):
        """
        Collect the stats when the object is created, and store them for later,
        when a report is requested.
        """
        stats = stats_factory.getStats(mount.mount)
        if isinstance(stats.free, str):
            self.__percent = "-"
        else:
            self.__percent = self.__percentage(stats.free, stats.total)
        self.__data = DiskData.get(stats, self.__percent, mount,
                                   size_formatter)

    def report(self):
        """Generate a report, and return it as text."""
        d = self.__data
        return [d.mount if opts["graph"] else d.device, d.total, d.used,
                d.free, d.percent,
                self.__percent if opts["graph"] else d.mount]

    @staticmethod
    def graph(percent, width):
        """Format a percentage as a bar graph."""
        # How many stars to place?
        # -4 accounts for the [] and the starting space
        width = width - 3
        if isinstance(percent, str):
            bar_width = 0
        else:
            bar_width = int(round(percent * width / 100))

        # Now generate the string, using the characters in the config file.
        result = color("safe")
        graph_char = opts["graph_char"]
        graph_fill = opts["graph_fill"]
        for counter in range(1, width + 1):
            if counter > bar_width:
                break

            if counter >= 0.7 * width and counter < 0.85 * width:
                result = result + color("warning")
            elif counter >= 0.85 * width:
                result = result + color("danger")

            result = result + graph_char

        result = result + (width - counter) * graph_fill

        return "  [" + color("safe") + result + color("normal") + "]"

    @staticmethod
    def __percentage(free, total):
        """Compute the percentage of space used."""
        if total == 0:
            return 0.0

        return 100 * (1.0 - free / total)

    @staticmethod
    def trim(text, width):
        """Don't let long names mess up the display: shorten them."""
        where = len(text)
        where = where - width
        if where > 0:
            text = "+" + text[where:]

        return text


def parse_options(args=sys.argv[1:]):
    """"""
    parser = argparse.ArgumentParser(description=f"Discus version {VERSION}, "
                                     "to display disk usage.",
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument("-d", "--device", action="store_true",
                        default=False, help="show device instead of graph")
    parser.add_argument("-c", "--color", action="store_false", default=True,
                        help="disable color")
    parser.add_argument("-g", "--gigabytes", action="store_const", const=2,
                        dest="divisor", help="display sizes in gigabytes")
    parser.add_argument("-k", "--kilobytes", action="store_const", const=0,
                        dest="divisor", help="display sizes in kilobytes")
    parser.add_argument("-m", "--megabytes", action="store_const", const=1,
                        dest="divisor", help="display sizes in megabytes")
    parser.add_argument("-p", "--places", type=int, choices=range(0, 10),
                        help="number of digits to right of decimal place")
    parser.add_argument("-r", "--reserved", action="store_true",
                        default=False, help="count reserved space as used")
    parser.add_argument("-s", "--smart", action="store_false", default=True,
                        help="do not use smart formatting")
    parser.add_argument("-t", "--terabytes", action="store_const", const=3,
                        dest="divisor", help="display sizes in terabytes")
    parser.add_argument("-v", "--version", action="version",
                        version=(f"Discus version {VERSION} by Nicolas "
                                 "Carrier (carrier.nicolas0@gmail.com)\n"
                                 f"Home page: {HOMEPAGE}"))

    return parser.parse_args(args)


def interpret_options(o):
    opts["smart"] = 1 if o.smart else 0
    if o.divisor is not None:
        if o.places is None:
            opts["places"] = o.divisor
        opts["divisor"] = o.divisor
        opts["smart"] = 0
    if o.places is not None:
        opts["placing"] = True
        opts["places"] = o.places
    opts["graph"] = 0 if o.device else 1
    opts["color"] = 1 if o.color else 0
    opts["reserved"] = 1 if o.reserved else 0


def read_mounts(mtab, skip_list):
    """Read the mounts file."""
    mounts = []

    # If the first letter of the mtab file begins with a !, it is a
    # shell command to be executed, and not a file to be read.  Idea
    # provided by John Soward.
    if mtab[0] == "!":
        mtab = subprocess.getoutput(mtab[1:])
        mtab = str.split(mtab, "\n")
    else:
        fp = open(mtab)
        mtab = fp.readlines()
        fp.close()

    # Extract the mounted filesystems from the read file.
    for entry in mtab:
        entry = str.split(entry)
        device = entry[0]
        mount = entry[1]

        # Sandro Tosi - to fix Debian bug 291276, convert escaped octal values
        # from /etc/mtab (or /proc/mounts) to real characters
        for octc in re.findall(r'\\(\d{3})', mount):
            mount = mount.replace(r'\%s' % octc, chr(int(octc, 8)))

        # Skip entries we aren't interested in.
        if mount in skip_list:
            continue

        mounts.append(Mount(mount, device))

    return mounts


def color(code):
    """Function that return color codes if color is enabled."""
    if opts["color"]:
        return opts["color_" + code]

    return ""


def get_header(graph):
    """Generate a list of headers."""
    # Has the user requested to see device names instead of a graph?
    if graph:
        return ["Mount", "Total", "Used", "Avail", "Prcnt", "  Graph"]
    else:
        return ["Device", "Total", "Used", "Avail", "Prcnt", "  Mount"]


def format_fields(f, w):
    """
    Format a list of fields into one string, given a list of corresponding
    widths.
    """
    a = ["", ">", ">", ">", ">", ""]
    return " ".join([f"{f[i]:{a[i]}{w[i]}}" for i in range(0, len(w))])


def get_layout(headers, reports):
    graph_column_width = 14
    widths = [11, 11, 12, 12, 8, graph_column_width]
    data = [copy.deepcopy(headers)] + copy.deepcopy(reports)

    size = shutil.get_terminal_size((MINIMUM_WIDTH, 20))
    # limit the width to a minimum and account to the inter-column gap
    columns = max(MINIMUM_WIDTH, size.columns - len(widths))
    for datum in data:
        for i, v in enumerate(datum[:-1]):
            if len(v) > widths[i]:
                widths[i] = len(v)

    widths[-1] = columns - sum(widths[:-1]) - 10
    if widths[-1] < graph_column_width:
        widths[-1] = graph_column_width
    widths[0] = columns - sum(widths[1:])

    return widths


def main():
    """Define main program."""
    options = parse_options()
    interpret_options(options)
    mounts = read_mounts(opts["mtab"], opts["skip_list"])
    headers = get_header(opts["graph"])
    stats_factory = StatsFactory(opts["reserved"])
    size_formatter = SizeFormatter(opts["smart"], opts["placing"],
                                   opts["akabytes"], opts["places"],
                                   opts["divisor"])

    # Create a disk object for each mount, store its report.
    reports = [Disk(m, stats_factory, size_formatter).report() for m in mounts]

    widths = get_layout(headers, reports)
    print(color("header") + format_fields(headers, widths))
    for report in reports:
        if opts["graph"]:
            r = report[:-1] + [Disk.graph(report[-1], widths[-1])]
        else:
            r = report[:-1] + ["  " + Disk.trim(report[-1], widths[-1] - 2)]
        # trim mount field if it exceeds its alloted width
        if len(r[0]) >= widths[0]:
            r[0] = Disk.trim(r[0], widths[0] - 1)
        print(color("normal") + format_fields(r, widths) + color("clear"))


if __name__ == "__main__":
    # Before starting, we try to load the configuration files which may
    # override global objects' values.
    # First the global /etc file, then the user's file, if it exists.
    try:
        exec(compile(open("/etc/discusrc", "rb").read(), "/etc/discusrc",
             'exec'))
    except IOError:
        pass

    try:
        exec(compile(open(os.environ['HOME'] + "/.discusrc", "rb").read(),
             os.environ['HOME'] + "/.discusrc", 'exec'))
    except IOError:
        pass

    # Add internal color setting.
    opts["color_clear"] = normal

    if "stat_prog" in opts:
        print("support for stat_prog option has been removed in 0.3.0",
              file=sys.stderr)

    main()
