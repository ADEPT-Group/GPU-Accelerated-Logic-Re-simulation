# This is a manual translation, from perl to python, of :
# http://cpansearch.perl.org/src/GSULLIVAN/Verilog-VCD-0.03/lib/Verilog/VCD.pm 

import re

global timescale
global endtime


# our local exception for VCD parsing errors (inherited from Exception)
class VCDParseError(Exception):
    pass


def list_sigs(file):
    """Parse input VCD file into data structure, 
    then return just a list of the signal names."""

    vcd = parse_vcd(file, only_sigs=1)

    sigs = []
    for k in vcd.keys():
        v = vcd[k]
        nets = v['nets']
        sigs.extend( n['hier']+'.'+n['name'] for n in nets )
    
    return sigs


def parse_vcd(file, only_sigs=0, use_stdout=0, siglist=[], opt_timescale=''):
    """Parse input VCD file into data structure.
    Also, print t-v pairs to STDOUT, if requested."""

    global endtime

    usigs = {}
    for i in siglist:
        usigs[i] = 1

    if len(usigs):
        all_sigs = 0
    else:
        all_sigs = 1

    data = {}
    mult = 0
    num_sigs = 0
    hier = []
    time = 0

    with open(file, 'r') as fh:
        while True:
            line = fh.readline()
            if line == '': # EOF
                break

            # chomp
            # s/ ^ \s+ //x
            line = line.strip()

            # if nothing left after we strip whitespace, go to next line
            if line == '':
                continue

            # put most frequent lines encountered at start of if/elif, so other
            #   clauses usually don't need to be tested 
            if line[0] in ('b', 'B', 'r', 'R'):
                (value,code) = line[1:].split()
                if (code in data):
                    if (use_stdout):
                        print( time, value )
                    else:
                        if 'tv' not in data[code]:
                            data[code]['tv'] = []
                        data[code]['tv'].append( (time, value) )
        
            elif line[0] in ('0', '1', 'x', 'X', 'z', 'Z'):
                value = line[0]
                code = line[1:]
                if (code in data):
                    if (use_stdout):
                        print( time, value )
                    else:
                        if 'tv' not in data[code]:
                            data[code]['tv'] = []
                        data[code]['tv'].append( (time, value) )
        
            elif line[0]=='#':
                time = mult * int(line[1:])
                endtime = time

            elif "$enddefinitions" in line:
                num_sigs = len(data)
                if (num_sigs == 0):
                    if (all_sigs):
                        VCDParseError("Error: No signals were found in the "\
                                "VCD file "+file+". Check the VCD file for "\
                                "proper var syntax.")
                    
                    else:
                        VCDParseError("Error: No matching signals were found "\
                                "in the VCD file "+file+". Use list_sigs to "\
                                "view all signals in the VCD file.")
                
                if ((num_sigs>1) and use_stdout):
                    VCDParseError("Error: There are too many signals "\
                            "(num_sigs) for output to STDOUT.  Use list_sigs "\
                            "to select a single signal.")
                
                if only_sigs:
                    break

            elif "$timescale" in line:
                statement = line
                if not "$end" in line:
                    while fh:
                        line = fh.readline()
                        statement += line
                        if "$end" in line:
                            break
                
                mult = calc_mult(statement, opt_timescale)

            elif "$scope" in line:
                # assumes all on one line
                #   $scope module dff end
                hier.append( line.split()[2] ) # just keep scope name
            
            elif "$upscope" in line:
                hier.pop()
            
            elif "$var" in line:
                # assumes all on one line:
                #   $var reg 1 *@ data $end
                #   $var wire 4 ) addr [3:0] $end
                ls = line.split()
                type = ls[1]
                size = ls[2]
                code = ls[3]
                name = "".join(ls[4:-1])
                path = '.'.join(hier)
                full_name = path + '.' + name
                if (full_name in usigs) or all_sigs:
                  if code not in data:
                      data[code] = {}
                  if 'nets' not in data[code]:
                      data[code]['nets'] = []
                  var_struct = {
                      'type' : type,
                      'name' : name,
                      'size' : size,
                      'hier' : path,
                   } 
                  if var_struct not in data[code]['nets']:
                      data[code]['nets'].append( var_struct )

    fh.close()

    return data


def calc_mult (statement, opt_timescale=''):
    """ 
    Calculate a new multiplier for time values.
    Input statement is complete timescale, for example:
      timescale 10ns end
    Input new_units is one of s|ms|us|ns|ps|fs.
    Return numeric multiplier.
    Also sets the package timescale variable.
    """ 

    global timescale

    fields = statement.split()
    fields.pop()   # delete end from array
    fields.pop(0)  # delete timescale from array
    tscale = ''.join(fields)

    new_units = ''
    if (opt_timescale != ''):
        new_units = opt_timescale.lower()
        new_units = re.sub(r"\s", '', new_units)
        timescale = "1"+new_units
    
    else:
        timescale = tscale
        return 1


    mult = 0
    units = 0
    ts_match = re.match(r"(\d+)([a-z]+)", tscale)
    if ts_match:
        mult  = int(ts_match.group(1))
        units = ts_match.group(2).lower()
    
    else:
        VCDParseError("Error: Unsupported timescale found in VCD "\
                "file: "+tscale+".  Refer to the Verilog LRM.")
    

    mults = {
        'fs' : 1e-15,
        'ps' : 1e-12,
        'ns' : 1e-09,
        'us' : 1e-06,
        'ms' : 1e-03,
         's' : 1e-00,
    }
    mults_keys = mults.keys()
    mults_keys.sort(key=lambda x : mults[x])
    usage = '|'.join(mults_keys)

    scale = 0
    if units in mults:
        scale = mults[units]
    
    else:
        VCDParseError("Error: Unsupported timescale units found in VCD "\
                "file: "+units+".  Supported values are: "+usage)


    new_scale = 0
    if new_units in mults:
        new_scale = mults[new_units]
    
    else:
        VCDParseError("Error: Illegal user-supplied "\
                "timescale: "+new_units+".  Legal values are: "+usage)


    return ((mult * scale) / new_scale)


def get_timescale():
    return timescale


def get_endtime():
    return endtime

print(parse_vcd('NV_nvdla_rando_input.vcd',use_stdout=1))
