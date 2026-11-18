import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from library import ROOT,read,write


@unittest.skipUnless(os.name=='nt','Windows delete-sharing semantics')
class AtomicRegistryWriteTests(unittest.TestCase):
    def lock_reader(self,path):
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
        kernel.CreateFileW.restype=ctypes.c_void_p
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.CreateFileW(str(path),0x80000000,1,None,3,0,None)
        self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
        return kernel,handle

    def test_transient_real_reader_lock_preserves_old_data_then_commits(self):
        with tempfile.TemporaryDirectory(prefix='_atomic_test_',dir=ROOT/'runs') as temp:
            p=Path(temp)/'registry.json';write(p,dict(version='old'))
            kernel,handle=self.lock_reader(p);observed=[]
            def unlock():
                time.sleep(.09);observed.append(read(p));kernel.CloseHandle(handle)
            thread=threading.Thread(target=unlock);thread.start()
            try:write(p,dict(version='new',items=list(range(100))))
            finally:thread.join()
            self.assertEqual(observed,[dict(version='old')])
            self.assertEqual(read(p),dict(version='new',items=list(range(100))))

    def test_persistent_real_lock_fails_without_deleting_old_registry(self):
        with tempfile.TemporaryDirectory(prefix='_atomic_test_',dir=ROOT/'runs') as temp:
            p=Path(temp)/'registry.json';write(p,dict(version='old'))
            kernel,handle=self.lock_reader(p)
            try:
                with self.assertRaises(PermissionError):write(p,dict(version='new'))
                self.assertEqual(read(p),dict(version='old'))
            finally:kernel.CloseHandle(handle)


if __name__=='__main__':unittest.main()
