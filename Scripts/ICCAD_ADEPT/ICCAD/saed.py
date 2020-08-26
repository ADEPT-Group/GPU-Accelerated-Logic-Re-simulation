from kyupy.circuit import Node, Line


def pin_index(cell_type, pin):
    if cell_type.startswith('SDFF') and pin == 'QN': return 1
    if cell_type.startswith('DFF') and pin == 'QN': return 1
    if cell_type.startswith('DFF') and pin == 'CLK': return 1
    if pin == 'A2' or pin == 'IN2' or pin == 'SE': return 1
    if pin == 'A3' or pin == 'IN3' or pin == 'SI': return 2
    if pin == 'A4' or pin == 'IN4' or pin == 'CLK': return 3  # CLK for scan cells SDFF
    if pin == 'A5' or pin == 'IN5' or pin == 'RSTB': return 4
    if pin == 'A6' or pin == 'IN6' or pin == 'SETB': return 5
    return 0


def add_and_connect(circuit, name, kind, in1, in2, out):
    n = Node(circuit, name, kind)
    if in1 is not None:
        n.i_lines[0] = in1
        in1.reader = n
        in1.reader_pin = 0
    if in2 is not None:
        n.i_lines[1] = in2
        in2.reader = n
        in2.reader_pin = 1
    if out is not None:
        n.o_lines[0] = out
        out.driver = n
        out.driver_pin = 0
    return n


def split_complex_gates(circuit):
    node_list = circuit.nodes
    for n in node_list:
        name = n.name
        ins = n.i_lines
        outs = n.o_lines
        if n.kind.startswith('AO21X'):
            n.remove()
            n_and = add_and_connect(circuit, name+'~and', 'AND2', ins[0], ins[1], None)
            n_or = add_and_connect(circuit, name+'~or', 'OR2', None, ins[2], outs[0])
            Line(circuit, n_and, n_or)
        elif n.kind.startswith('OA21X'):
            n.remove()
            n_or = add_and_connect(circuit, name+'~or', 'OR2', ins[0], ins[1], None)
            n_and = add_and_connect(circuit, name+'~and', 'AND2', None, ins[2], outs[0])
            Line(circuit, n_or, n_and)
        elif n.kind.startswith('OA22X'):
            n.remove()
            n_or0 = add_and_connect(circuit, name+'~or0', 'OR2', ins[0], ins[1], None)
            n_or1 = add_and_connect(circuit, name+'~or1', 'OR2', ins[2], ins[3], None)
            n_and = add_and_connect(circuit, name+'~and', 'AND2', None, None, outs[0])
            Line(circuit, n_or0, n_and)
            Line(circuit, n_or1, n_and)
        elif n.kind.startswith('AO22X'):
            n.remove()
            n_and0 = add_and_connect(circuit, name+'~and0', 'AND2', ins[0], ins[1], None)
            n_and1 = add_and_connect(circuit, name+'~and1', 'AND2', ins[2], ins[3], None)
            n_or = add_and_connect(circuit, name+'~or', 'OR2', None, None, outs[0])
            Line(circuit, n_and0, n_or)
            Line(circuit, n_and1, n_or)
        elif n.kind.startswith('AO221X'):
            n.remove()
            n_and0 = add_and_connect(circuit, name+'~and0', 'AND2', ins[0], ins[1], None)
            n_and1 = add_and_connect(circuit, name+'~and1', 'AND2', ins[2], ins[3], None)
            n_or0 = add_and_connect(circuit, name+'~or0', 'OR2', None, None, None)
            n_or1 = add_and_connect(circuit, name+'~or1', 'OR2', None, ins[4], outs[0])
            Line(circuit, n_and0, n_or0)
            Line(circuit, n_and1, n_or0)
            Line(circuit, n_or0, n_or1)     
        elif n.kind.startswith('AOI221X'):
            n.remove()
            n_and0 = add_and_connect(circuit, name+'~and0', 'AND2', ins[0], ins[1], None)
            n_and1 = add_and_connect(circuit, name+'~and1', 'AND2', ins[2], ins[3], None)
            n_or = add_and_connect(circuit, name+'~or', 'OR2', None, None, None)
            n_nor = add_and_connect(circuit, name+'~nor', 'NOR2', None, ins[4], outs[0])
            Line(circuit, n_and0, n_or)
            Line(circuit, n_and1, n_or)
            Line(circuit, n_or, n_nor)     
        elif n.kind.startswith('OA221X'):
            n.remove()
            n_or0 = add_and_connect(circuit, name+'~or0', 'OR2', ins[0], ins[1], None)
            n_or1 = add_and_connect(circuit, name+'~or1', 'OR2', ins[2], ins[3], None)
            n_and0 = add_and_connect(circuit, name+'~and0', 'AND2', None, None, None)
            n_and1 = add_and_connect(circuit, name+'~and1', 'AND2', None, ins[4], outs[0])
            Line(circuit, n_or0, n_and0)
            Line(circuit, n_or1, n_and0)
            Line(circuit, n_and0, n_and1)    
        elif n.kind.startswith('AO222X'):
            n.remove()
            n_and0 = add_and_connect(circuit, name+'~and0', 'AND2', ins[0], ins[1], None)
            n_and1 = add_and_connect(circuit, name+'~and1', 'AND2', ins[2], ins[3], None)
            n_and2 = add_and_connect(circuit, name+'~and2', 'AND2', ins[4], ins[5], None)
            n_or0 = add_and_connect(circuit, name+'~or0', 'OR2', None, None, None)
            n_or1 = add_and_connect(circuit, name+'~or1', 'OR2', None, None, outs[0])
            Line(circuit, n_and0, n_or0)
            Line(circuit, n_and1, n_or0)
            Line(circuit, n_and2, n_or1)
            Line(circuit, n_or0, n_or1)
        elif n.kind.startswith('OA222X'):
            n.remove()
            n_or0 = add_and_connect(circuit, name+'~or0', 'OR2', ins[0], ins[1], None)
            n_or1 = add_and_connect(circuit, name+'~or1', 'OR2', ins[2], ins[3], None)
            n_or2 = add_and_connect(circuit, name+'~or2', 'OR2', ins[4], ins[5], None)
            n_and0 = add_and_connect(circuit, name+'~and0', 'AND2', None, None, None)
            n_and1 = add_and_connect(circuit, name+'~and1', 'AND2', None, None, outs[0])
            Line(circuit, n_or0, n_and0)
            Line(circuit, n_or1, n_and0)
            Line(circuit, n_or2, n_and1)
            Line(circuit, n_and0, n_and1)
        elif n.kind.startswith('NOR3X'):
            n.remove()
            n_or = add_and_connect(circuit, name+'~or', 'OR2', ins[0], ins[1], None)
            n_nor = add_and_connect(circuit, name+'~nor', 'NOR2', None, ins[2], outs[0])
            Line(circuit, n_or, n_nor)

