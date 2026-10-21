import os,shlex
from pathlib import Path
from conan import ConanFile
from conan.tools.env import Environment,VirtualRunEnv
from conan.tools.files import copy
from conan.tools.layout import basic_layout
class FlitCoreConsumer(ConanFile):
    settings='os','arch','compiler','build_type'
    test_type='explicit'
    def requirements(self):self.requires(self.tested_reference_str,run=True)
    def layout(self):basic_layout(self)
    def generate(self):VirtualRunEnv(self).generate()
    def build(self):
        for n in ('test_flit_core.sh','consumer.py','backend_fixture.py'):copy(self,n,self.source_folder,self.build_folder)
        copy(self,'*',os.path.join(self.source_folder,'harmony_tests'),os.path.join(self.build_folder,'harmony_tests'))
        copy(self,'backend_fixture.py',self.source_folder,os.path.join(self.build_folder,'harmony_tests'))
    def test(self):
        python=Path(self.dependencies['python'].package_folder)/'bin/python3';root=self.dependencies['flit-core'].package_folder;e=Environment();e.define('PYTHONHOME',self.dependencies['python'].package_folder);e.define('PYTHONNOUSERSITE','1');e.define('PYTHONDONTWRITEBYTECODE','1')
        with VirtualRunEnv(self).vars().apply(),e.vars(self).apply():
            self.run(shlex.join(['/system/bin/sh',str(Path(self.build_folder)/'test_flit_core.sh'),str(python),root]),cwd=self.build_folder,env=None)
            if str(self.settings.os)=='OHOS':self.run(shlex.join([str(python),'-B',str(Path(self.build_folder)/'harmony_tests/hmdfs_backend.py'),root]),cwd=self.build_folder,env=None)
