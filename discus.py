#!/usr/bin/python3

# Discus is a program that reports hard drive space usage.

# Copyright 2000 Stormy Henderson (stormy@futuresouth.com).
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
import getopt
import os
import sys
import re
import unittest
from collections import namedtuple

opts = {"placing": True, "reserved": True}

VERSION = "0.4.0"

# values taken from sysexit.h
EX_OK = 0
EX_USAGE = 64
EX_CONFIG = 78


class StatsFactory:
    """Factory class to get statistics about a mount point."""
    def __init__(self, reserved):
        """Constructor, initialize private fields."""
        self.__reserved = reserved
        self.__stats_class = namedtuple('Stats', ['total', 'free', 'used'])

    def getStats(self, mount):
        """Gather statistics about specified filesystem."""
        stats = os.statvfs(mount)
        total = stats.f_blocks * stats.f_frsize
        # if we have to take care of reserved space for root, then use
        # available blocks (but keep counting free space with all free blocks)
        if self.__reserved:
            free = stats.f_bavail * stats.f_frsize
            used = total - stats.f_bfree * stats.f_frsize
        else:
            free = stats.f_bfree * stats.f_frsize
            used = total - stats.f_bfree * stats.f_frsize

        return self.__stats_class(total=total, free=free, used=used)


class StatsFactoryTests(unittest.TestCase):
    """Unit tests for the StatsFactory class"""
    def test_getStatsReservedTrue(self):
        """Normal use case with reserved == True."""
        factory = StatsFactory(True)
        s = factory.getStats("/")
        self.assertNotEqual(s.total, 0, "a size of 0 for / is unlikely")
        self.assertNotEqual(s.free, 0, "0 bytes free for / is unlikely")
        self.assertNotEqual(s.used, 0, "0 bytes used for / is unlikely")

    def test_getStatsReservedFalse(self):
        """Normal use case with reserved == False."""
        factory = StatsFactory(False)
        s = factory.getStats("/")
        self.assertNotEqual(s.total, 0, "a size of 0 for / is unlikely")
        self.assertNotEqual(s.free, 0, "0 bytes free for / is unlikely")
        self.assertNotEqual(s.used, 0, "0 bytes used for / is unlikely")
        self.assertEqual(s.total, s.free + s.used, "total != free + used")

    def test_getStatsFailure(self):
        """Failure use case, non existent mount point."""
        factory = StatsFactory(False)
        raised = False
        try:
            factory.getStats("non existent mount point")
        except Exception:
            raised = True
        self.assertTrue(raised)


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
                                     "divisor"],
                         defaults=(True, True, DEFAULT_AKABYTES, 1, 1))

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
        labels = self.__akabytes

        size, divisor, places = self.__formatter(size)

        # And now actually format the result.
        if size == 0:
            result = "%d %s" % (size, labels[divisor])
        else:
            result = "%%0.%df %%s" % places
            result = result % (size, labels[divisor])

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


class SizeFormatterTests(unittest.TestCase):
    """Unit tests for the SizeFormatter class"""

    def test_manual_format(self):
        """Format sizes in manual format mode."""
        # kilo bytes
        opts = SizeFormatter.Options(smart=False, divisor=0)
        sf = SizeFormatter(*opts)
        # TODO, this is not correct, if the converted size is exact, then there
        # should be no .0 part, but to implement that, we have to manipulate
        # sizes internally in bytes, not in kilo bytes
        self.assertEqual(sf.format(124684), "124684.0 KB", "124684 in KB fail")
        # mega bytes
        opts = SizeFormatter.Options(smart=False, divisor=1)
        sf = SizeFormatter(*opts)
        self.assertEqual(sf.format(124684), "121.8 MB", "124684 in MB fail")
        # giga bytes
        opts = SizeFormatter.Options(smart=False, divisor=2)
        sf = SizeFormatter(*opts)
        self.assertEqual(sf.format(124684), "0.1 GB", "124684 in GB fail")
        # tera bytes
        opts = SizeFormatter.Options(smart=False, divisor=3)
        sf = SizeFormatter(*opts)
        self.assertEqual(sf.format(pow(1024, 3)), "1.0 TB", "1 TB in TB fail")
        self.assertEqual(sf.format(0), "0 TB", "0 TB in TB fail")

    def test_smart_format(self):
        """Format sizes in smart format mode."""
        opts = SizeFormatter.Options(smart=True)
        sf = SizeFormatter(*opts)
        self.assertEqual(sf.format(124684), "121.8 MB", "124684 fail")
        self.assertEqual(sf.format(1024), "1.0 MB", "1024 fail")
        self.assertEqual(sf.format(1), "1.0 KB", "1 fail")
        self.assertEqual(sf.format(999), "999.0 KB", "999 fail")
        self.assertEqual(sf.format(1000), "1.0 MB", "1000 fail")


class Disk:
    """Contains everything needed to represent a disk textually."""

    def __init__(self, device, mount, stats_factory):
        """
        Collect the stats when the object is created, and store them for later,
        when a report is requested.
        """
        self.__stats = stats_factory.getStats(mount)
        self.__device = device
        self.__mount = mount

    def report(self):
        """Generate a report, and return it as text."""
        percent = self.__percentage()
        total = self.__format(self.__stats.total / 1024)
        used = self.__format(self.__stats.used / 1024)
        free = self.__format(self.__stats.free / 1024)

        # Perform a swaparoo if the user wants the device names instead
        # of my pretty bar graph.
        if opts["graph"]:
            graph = self.__graph(percent)
            mount = self.__trim(self.__mount)
        else:
            graph = self.__trim(self.__mount)
            mount = self.__trim(self.__device)

        # Format the result, and return it.
        return color("normal") + "%-11s %12s %12s %12s   %5.1f%%   %s" % \
            (
                mount,
                total,
                used,
                free,
                percent,
                graph
            ) + color("clear")

    def __format(self, size):
        """Format the size for human use."""
        labels = opts["akabytes"]

        # Is smart display enabled?
        if opts["smart"]:
            size, divisor, places = self.__smart_format(size)
        else:
            size, divisor, places = self.__manual_format(size)

        # And now actually format the result.
        if size == 0:
            result = "%d %s" % (size, labels[divisor])
        else:
            result = "%%0.%df %%s" % places
            result = result % (size, labels[divisor])

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
        if not opts["placing"]:
            if count < 2:
                fudge = count
            else:
                fudge = 2
        else:
            # User specified how many decimal places were wanted.
            fudge = opts["places"]

        return size, count, fudge

    def __manual_format(self, size):
        """
        We're not using smart display, so figure things up on the specified
        KB/MB/GB/TB basis.
        """
        divisor = opts["divisor"]
        size = size / pow(1024.0, divisor)

        return size, divisor, opts["places"]

    def __percentage(self):
        """Compute the percentage of space used."""
        try:
            ratio = 1.0 - self.__stats.free / self.__stats.total
        except ZeroDivisionError:
            ratio = 0.0

        return 100 * ratio

    def __graph(self, percent):
        """Format a percentage as a bar graph."""
        # How many stars to place?
        percent = percent / 10
        percent = round(percent)
        percent = int(percent)
        percent = 10 - percent

        # Now generate the string, using the characters in the config file.
        result = color("safe")
        graph_char = opts["graph_char"]
        graph_fill = opts["graph_fill"]
        for counter in range(0, (10 - percent)):
            if counter < 6:
                result = result + graph_char
            elif counter == 6:
                result = result + color("warning") + graph_char
            elif counter == 7:
                result = result + "*"
            elif counter == 8:
                result = result + color("danger") + graph_char
            elif counter == 9:
                result = result + graph_char

        result = result + color("normal")
        return "[%s%s]" % \
            (
                result,
                graph_fill * percent
            )

    def __trim(self, text):
        """Don't let long names mess up the display: shorten them."""
        where = len(text)
        where = where - 10
        if where > 0:
            text = "+" + text[where:]

        return text


def version():
    """Print version."""
    print("Discus version {} by Nicolas Carrier "
          "(carrier.nicolas0@gmail.com).".format(VERSION))
    print("Home page: https://github.com/ncarrier/discus")
    sys.exit(0)


def usage(exit_status, text=""):
    """Print the help of the tool."""
    # Only print the general help if no specific message is provided.
    if text == "":
        print("""Discus version %s, to display disk usage.
Options are:
 -h, --help      display help
 -v, --version   display version
 -p number       number of digits to right of decimal place
 -s              do not use smart formatting
 -t, g, m, k     display sizes in tera/giga/mega/kilobytes, repectively.
                    assumes -s
 -d              show device instead of graph
 -c              disable color
 -r              count reserved space as used
""" % VERSION)

    else:
        print(text)

    sys.exit(exit_status)


def parse_options():
    """Read the user's options and integrate them with the defaults."""
    try:
        options, _ = getopt.getopt(sys.argv[1:], "p:tgmksdcrvh",
                                   ["help", "version"])
    except Exception:
        sys.exit(EX_USAGE)

    for option, value in options:
        # Display terabytes.
        if option == "-t":
            opts["divisor"] = 3
            opts["smart"] = 0
            opts["places"] = 3

        # Display gigabytes.
        if option == "-g":
            opts["divisor"] = 2
            opts["smart"] = 0
            opts["places"] = 2

        # Display megabytes.
        if option == "-m":
            opts["divisor"] = 1
            opts["smart"] = 0
            opts["places"] = 1

        # Display kilobytes.
        if option == "-k":
            opts["divisor"] = 0
            opts["smart"] = 0
            opts["places"] = 0

        # Display X decimal places.
        if option == "-p":
            opts["placing"] = True
            fail = False
            try:
                opts["places"] = int(value)
            except ValueError:
                fail = True

            if fail or opts["places"] < 0 or opts["places"] > 9:
                usage(EX_USAGE, "The -p option requires a number from 0 to 9.")

        # Disable smart display.
        if option == "-s":
            opts["smart"] = 0

        # Show device instead of graph.
        if option == "-d":
            opts["graph"] = 0

        # Turn off color.
        if option == "-c":
            opts["color"] = 0

        # Display version.
        if option in ["-v", "--version"]:
            version()

        # Display help.
        if option in ["-h", "--help"]:
            usage(EX_OK)

        if option == "-r":
            opts["reserved"] = 1


def read_mounts():
    """Read the mounts file."""
    mounts = []
    devices = []
    mtab = opts["mtab"]

    # If the first letter of the mtab file begins with a !, it is a
    # shell command to be executed, and not a file to be read.  Idea
    # provided by John Soward.
    if mtab[0] == "!":
        mtab = subprocess.getoutput(mtab[1:])
        mtab = str.split(mtab, "\n")
    else:
        fp = open(opts["mtab"])
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
        if mount in opts["skip_list"]:
            continue

        devices.append(device)
        mounts.append(mount)

    return devices, mounts


class ReadMountsTests(unittest.TestCase):
    """Tests for the read_mounts function."""
    def test_simple_mtab(self):
        """Test with a simple mtabe consisting of only one line."""
        opts["mtab"] = "tests/mtab.oneline"
        opts["skip_list"] = []
        devices, mounts = read_mounts()
        self.assertEqual(len(devices), 1, "one device should be detected")
        self.assertEqual(devices[0], "/dev/sda2")
        self.assertEqual(len(mounts), 1, "one mount point should be detected")
        self.assertEqual(mounts[0], "/")

    def test_bug_291276(self):
        """Test to reproduce the debian bug 291276."""
        opts["mtab"] = "tests/mtab.291276"
        opts["skip_list"] = []
        _, mounts = read_mounts()
        self.assertEqual(len(mounts), 1, "one mount point should be detected")
        self.assertEqual(mounts[0], "/media/ACER UFD")


def color(code):
    """Function that return color codes if color is enabled."""
    if opts["color"]:
        return opts["color_" + code]

    return ""


def format_header():
    """Generate a colored heading."""
    # Has the user requested to see device names instead of a graph?
    if opts["graph"]:
        mount = "Mount"
        graph = " Graph"
    else:
        mount = "Device"
        graph = "Mount"

    return color("header") + "%-16s%-14s%-13s%-11s%-10s%s" % \
        (
            mount,
            "Total",
            "Used",
            "Avail",
            "Prcnt",
            graph
        ) + color("clear")


def main():
    """Define main program."""
    parse_options()
    devices, mounts = read_mounts()
    print(format_header())
    stats_factory = StatsFactory(opts["reserved"])

    # Create a disk object for each mount, and print a report.
    for count in range(0, len(devices)):
        disk = Disk(devices[count], mounts[count], stats_factory)
        print(disk.report())


if __name__ == "__main__":
    # Before starting, we need to load the configuration files which
    # contain global objects.  First the global /etc file, then the user's
    # file, if exists.
    try:
        exec(compile(open("/etc/discusrc", "rb").read(), "/etc/discusrc",
             'exec'))
    except IOError:
        usage(EX_CONFIG, "/etc/discusrc must exist and be readable.")

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
