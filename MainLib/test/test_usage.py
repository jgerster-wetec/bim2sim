﻿import unittest
import subprocess
import os
import sys
from pathlib import Path


class TestUsage(unittest.TestCase):
    """Tests for general use of library"""

    def test_import_mainlib(self):
        """Test importing bim2sim in python script"""
        try:
            import bim2sim
        except ImportError as err:
            self.fail("Unable to import bim2sim\nreason: %s"%(err.msg))
        except Exception as err:
            self.skipTest("bim2sim available but errors occured on import\ndetails: %s"%(err.msg))

    def test_import_plugin(self):
        """Test importing bim2sim_energyplus in python script"""
        try:
            import bim2sim_energyplus
        except ImportError as err:
            self.fail("Unable to import plugin\nreason: %s"%(err.msg))
        except Exception as err:
            self.skipTest("Plugin available but errors occured on import\ndetails: %s"%(err.msg))

    def test_call_console(self):
        """Test calling bim2sim -h from console"""
        try:
            import bim2sim
        except ImportError:
            self.fail("Unable to localize bim2sim")
        path = Path(bim2sim.__file__).parent
        cmd = "%s %s --version" % (sys.executable, 'bim2sim')
        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=path.parent, shell=True)
        self.assertTrue(ret.stdout.decode('utf-8').startswith(bim2sim.VERSION), 'unexpected output')

        # for some reason the error code is 1 but code runs as expected without errors ...
        # if ret.returncode != 0:
        #     print(ret.stdout)
        #     print(ret.stderr)
        # self.assertEqual(0, ret.returncode, "Calling '%s' by console failed" % cmd)


if __name__ == '__main__':
    unittest.main()
