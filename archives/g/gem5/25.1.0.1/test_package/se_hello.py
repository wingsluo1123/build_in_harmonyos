"""Minimal gem5 SE (syscall emulation) configuration for the smoke test.

Runs one AArch64 binary on an ArmAtomicSimpleCPU with 512 MiB DDR3 and
prints the standard simulation begin/end banner.  Kept self-contained on
purpose: the test must exercise the packaged gem5.opt, not the source-tree
configs/ helpers.

Usage:
    gem5.opt -d <outdir> se_hello.py <aarch64-static-binary>
"""

import sys

import m5
from m5.objects import *

binary = sys.argv[1]

system = System()
system.voltage_domain = VoltageDomain()
system.clk_domain = SrcClockDomain(
    clock="1GHz", voltage_domain=system.voltage_domain
)
system.mem_mode = "atomic"
system.mem_ranges = [AddrRange("512MB")]

system.cpu = ArmAtomicSimpleCPU()
system.cpu.clk_domain = system.clk_domain

system.membus = SystemXBar()
system.system_port = system.membus.cpu_side_ports
system.cpu.createInterruptController()
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.workload = SEWorkload.init_compatible(binary)
process = Process()
process.cmd = [binary]
system.cpu.workload = process
system.cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()
print("Beginning simulation!")
exit_event = m5.simulate()
print("Exiting @ tick %i because %s" % (m5.curTick(), exit_event.getCause()))
