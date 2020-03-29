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

opts = {"placing": True, "reserved": True}

VERSION = "0.4.0"

# values taken from sysexit.h
EX_OK          = 0
EX_USAGE       = 64
EX_CONFIG      = 78

class Disk:
    """Contains everything needed to represent a disk textually."""

    def __init__(self, device, mount):
        """
        Collect the stats when the object is created, and store them for later,
        when a report is requested.
        """
        self.__getstats(mount)
        self.__device = device
        self.__mount = mount

    def report(self):
        """Generate a report, and return it as text."""
        percent = self.__percentage()
        total = self.__format(self.__total)
        used = self.__format(self.__used)
        free = self.__format(self.__free)

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
            percent = (1.0 - (1.0 * self.__free / self.__total)) * 100
        except ZeroDivisionError:
            percent = 0.0

        return percent

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

    def __getstats(self, mount):
        """Gather statistics about specified filesystem."""
        stats = os.statvfs(mount)
        blocksize = int(stats.f_frsize)
        self.__total = int(stats.f_blocks) * (blocksize / 1024.0)
        # if we have to take care of reserved space for root, then use
        # available blocks (but keep counting free space with all free
        # blocks)
        if opts["reserved"]:
            self.__free = int(stats.f_bavail) * (blocksize / 1024.0)
            self.__used = (self.__total - int(stats.f_bfree) *
                         (blocksize / 1024.0))
        else:
            self.__free = int(stats.f_bfree) * (blocksize / 1024.0)
            self.__used = (self.__total - int(stats.f_bfree) *
                         (blocksize / 1024.0))

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


def help(exit_status, text=""):
    """Print a help file."""
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
        options, args = getopt.getopt(sys.argv[1:], "p:tgmksdcrvh",
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
                help(EX_USAGE, "The -p option requires a number from 0 to 9.")

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
            help(EX_OK)

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
    def test_simple_mtab(self):
        opts["mtab"] = "tests/mtab.oneline"
        opts["skip_list"] = []
        devices, mounts = read_mounts()
        self.assertEqual(len(devices), 1, "one device should be detected")
        self.assertEqual(devices[0], "/dev/sda2")
        self.assertEqual(len(mounts), 1, "one mount point should be detected")
        self.assertEqual(mounts[0], "/")

    def test_bug_291276(self):
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

    # Create a disk object for each mount, and print a report.
    for count in range(0, len(devices)):
        disk = Disk(devices[count], mounts[count])
        print(disk.report())


if __name__ == "__main__":
    # Before starting, we need to load the configuration files which
    # contain global objects.  First the global /etc file, then the user's
    # file, if exists.
    try:
        exec(compile(open("/etc/discusrc", "rb").read(), "/etc/discusrc",
             'exec'))
    except IOError:
        help(EX_CONFIG, "/etc/discusrc must exist and be readable.")

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
