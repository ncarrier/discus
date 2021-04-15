import unittest
import argparse
from discus import StatsFactory, SizeFormatter, DiskData, Mount, parse_options
from discus import read_mounts


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
        self.assertEqual(sf.format(0), "0 KB", "0 fail")
        self.assertEqual(sf.format(999), "999.0 KB", "999 fail")
        self.assertEqual(sf.format(1000), "1.0 MB", "1000 fail")


class DiskDataTests(unittest.TestCase):
    """Unit tests for the DiskData class"""

    def test_get(self):
        """Tests for the get method."""
        sf = SizeFormatter(*SizeFormatter.Options())
        mount = Mount("/", "/dev/sda1")
        d = DiskData.get(StatsFactory.Stats(1000000, 1000000 - 50000, 50000),
                         5.0,
                         mount,
                         sf)
        self.assertEqual(d.percent, "5.0%", "percent doesn't match")
        self.assertEqual(d.total, "976.6 KB", "total doesn't match")
        self.assertEqual(d.used, "48.8 KB", "used doesn't match")
        self.assertEqual(d.free, "927.7 KB", "free doesn't match")
        self.assertEqual(d.mount, mount.mount, "mount doesn't match")
        self.assertEqual(d.device, mount.device, "device doesn't match")


class ParseOptionsTests(unittest.TestCase):
    """Tests for the parse_options function."""
    def test_device(self):
        """Test for the --device option."""
        options = parse_options([])
        self.assertFalse(options.device)
        options = parse_options(["-d"])
        self.assertTrue(options.device)
        options = parse_options(["--device"])
        self.assertTrue(options.device)

    def test_color(self):
        """Test for the --color option."""
        options = parse_options([])
        self.assertTrue(options.color)
        options = parse_options(["-c"])
        self.assertFalse(options.color)
        options = parse_options(["--color"])
        self.assertFalse(options.color)

    def test_gigabytes(self):
        """Test for the --gigabytes option."""
        options = parse_options([])
        self.assertEqual(options.divisor, None)
        options = parse_options(["-g"])
        self.assertEqual(options.divisor, 2)
        options = parse_options(["--gigabytes"])
        self.assertEqual(options.divisor, 2)

    def test_kilobytes(self):
        """Test for the --kilobytes option."""
        options = parse_options([])
        self.assertEqual(options.divisor, None)
        options = parse_options(["-k"])
        self.assertEqual(options.divisor, 0)
        options = parse_options(["--kilobytes"])
        self.assertEqual(options.divisor, 0)

    def test_megabytes(self):
        """Test for the --megabytes option."""
        options = parse_options([])
        self.assertEqual(options.divisor, None)
        options = parse_options(["-m"])
        self.assertEqual(options.divisor, 1)
        options = parse_options(["--megabytes"])
        self.assertEqual(options.divisor, 1)

    def test_places(self):
        options = parse_options([])
        self.assertEqual(options.places, None)
        options = parse_options(["-p", "0"])
        self.assertEqual(options.places, 0)
        options = parse_options(["-p", "9"])
        self.assertEqual(options.places, 9)
        with self.assertRaises((SystemExit, argparse.ArgumentError)):
            parse_options(["-p", "10"])
        with self.assertRaises((SystemExit, argparse.ArgumentError)):
            parse_options(["-p", "-1"])

    def test_reserved(self):
        """ Test for the --reserved option."""
        options = parse_options([])
        self.assertFalse(options.reserved)
        options = parse_options(["-r"])
        self.assertTrue(options.reserved)
        options = parse_options(["--reserved"])
        self.assertTrue(options.reserved)

    def test_smart(self):
        options = parse_options([])
        self.assertTrue(options.smart)
        options = parse_options(["-s"])
        self.assertFalse(options.smart)
        options = parse_options(["--smart"])
        self.assertFalse(options.smart)

    def test_terabytes(self):
        """Test for the --terabytes option."""
        options = parse_options([])
        self.assertEqual(options.divisor, None)
        options = parse_options(["-t"])
        self.assertEqual(options.divisor, 3)
        options = parse_options(["--terabytes"])
        self.assertEqual(options.divisor, 3)


class ReadMountsTests(unittest.TestCase):
    """Tests for the read_mounts function."""
    def test_simple_mtab(self):
        """Test with a simple mtabe consisting of only one line."""
        mounts = read_mounts("tests/mtab.oneline", [])
        self.assertEqual(len(mounts), 1, "one device should be detected")
        self.assertEqual(mounts[0].device, "/dev/sda2")
        self.assertEqual(mounts[0].mount, "/")

    def test_bug_291276(self):
        """Test to reproduce the debian bug 291276."""
        mounts = read_mounts("tests/mtab.291276", [])
        self.assertEqual(len(mounts), 1, "one mount point should be detected")
        self.assertEqual(mounts[0].mount, "/media/ACER UFD")
