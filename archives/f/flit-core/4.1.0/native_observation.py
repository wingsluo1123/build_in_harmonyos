import json,os
from pathlib import Path
collected=[];reports=[];collection=[]
def pytest_collection_modifyitems(session,config,items):
 collected.extend(item.nodeid for item in items)
def pytest_collectreport(report):
 collection.append({'nodeid':report.nodeid,'outcome':report.outcome})
def pytest_runtest_logreport(report):
 reports.append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'wasxfail':getattr(report,'wasxfail',None),'skip_reason':report.longrepr[2].removeprefix('Skipped: ') if report.skipped and isinstance(report.longrepr,tuple) else None})
def pytest_sessionfinish(session,exitstatus):
 Path(os.environ['FLIT_NATIVE_OBSERVATION']).write_text(json.dumps({'collected_nodeids':collected,'reports':reports,'collection':collection,'exitstatus':int(exitstatus)}))
