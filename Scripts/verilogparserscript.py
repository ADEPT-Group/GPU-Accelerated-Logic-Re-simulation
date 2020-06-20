import pprint
import sys
from verilogparser import parse_verilog # should change relative path 
verilog_file = sys.argv[-1]
#verilog_file = os.path.join(os.path.dirname(__file__), 'simple_nl_ys.v')
with open(verilog_file) as f:
        data = f.read()
    
netlist = parse_verilog(data)
print(netlist)
pprint.pprint(netlist)
    
