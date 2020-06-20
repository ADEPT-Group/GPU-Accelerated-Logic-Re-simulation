#from kyupy import sdf, verilog
#from kyupy.saed import pin_index
import sdfparser
import pprint
test = '''
    (DELAYFILE
    (SDFVERSION "OVI 2.1")
    (DESIGN "test")
    (DATE "Wed May 31 14:46:06 2017")
    (VENDOR "saed90nm_max")
    (PROGRAM "Synopsys Design Compiler cmos-annotated")
    (VERSION "I-2013.12-ICC-SP3")
    (DIVIDER /)
    (VOLTAGE 1.20:1.20:1.20)
    (PROCESS "TYPICAL")
    (TEMPERATURE 25.00:25.00:25.00)
    (TIMESCALE 1ns)
    (CELL
      (CELLTYPE "b14")
      (INSTANCE)
      (DELAY
        (ABSOLUTE
        (INTERCONNECT U621/ZN U19246/IN1 (0.000:0.000:0.000))
        (INTERCONNECT U13292/QN U19246/IN2 (0.001:0.001:0.001))
        (INTERCONNECT U15050/QN U19247/IN1 (0.000:0.000:0.000))
        (INTERCONNECT U13293/QN U19247/IN2 (0.000:0.000:0.000) (0.000:0.000:0.000))
        )
      )
    )
    (CELL
      (CELLTYPE "INVX2")
      (INSTANCE U78)
      (DELAY
        (ABSOLUTE
        (IOPATH INP ZN (0.201:0.227:0.227) (0.250:0.271:0.271))
        )
      )
    )
    (CELL
      (CELLTYPE "SDFFARX1")
      (INSTANCE reg3_reg_1_0)
      (DELAY
        (ABSOLUTE
        (IOPATH (posedge CLK) Q (0.707:0.710:0.710) (0.737:0.740:0.740))
        (IOPATH (negedge RSTB) Q () (0.909:0.948:0.948))
        (IOPATH (posedge CLK) QN (0.585:0.589:0.589) (0.545:0.550:0.550))
        (IOPATH (negedge RSTB) QN (1.546:1.593:1.593) ())
        )
      )
      (TIMINGCHECK
        (WIDTH (posedge CLK) (0.284:0.284:0.284))
        (WIDTH (negedge CLK) (0.642:0.642:0.642))
        (SETUP (posedge D) (posedge CLK) (0.544:0.553:0.553))
        (SETUP (negedge D) (posedge CLK) (0.620:0.643:0.643))
        (HOLD (posedge D) (posedge CLK) (-0.321:-0.331:-0.331))
        (HOLD (negedge D) (posedge CLK) (-0.196:-0.219:-0.219))
        (RECOVERY (posedge RSTB) (posedge CLK) (-1.390:-1.455:-1.455))
        (HOLD (posedge RSTB) (posedge CLK) (1.448:1.509:1.509))
        (SETUP (posedge SE) (posedge CLK) (0.662:0.670:0.670))
        (SETUP (negedge SE) (posedge CLK) (0.698:0.702:0.702))
        (HOLD (posedge SE) (posedge CLK) (-0.435:-0.444:-0.444))
        (HOLD (negedge SE) (posedge CLK) (-0.291:-0.295:-0.295))
        (SETUP (posedge SI) (posedge CLK) (0.544:0.544:0.544))
        (SETUP (negedge SI) (posedge CLK) (0.634:0.688:0.688))
        (HOLD (posedge SI) (posedge CLK) (-0.317:-0.318:-0.318))
        (HOLD (negedge SI) (posedge CLK) (-0.198:-0.247:-0.247))
        (WIDTH (negedge RSTB) (0.345:0.345:0.345))
    )))
    '''
df = sdfparser.parse(test)
assert df.name == 'test'
print(f'DelayFile(name={df.name}')
#print(df)
pprint.pprint(df)

import sys
#from verilogparser import parse_verilog # should change relative path 
#verilog_file = sys.argv[-1]
#verilog_file = os.path.join(os.path.dirname(__file__), 'simple_nl_ys.v')
#with open(verilog_file) as f:
      #  data = f.read()
    
#netlist = parse_verilog(data)
#print(netlist)
#pprint.pprint(netlist)


