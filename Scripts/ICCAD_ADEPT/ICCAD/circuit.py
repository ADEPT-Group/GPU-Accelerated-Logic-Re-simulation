from collections import namedtuple, deque


class GrowingList(list):
    def __setitem__(self, index, value):
        if index >= len(self):
            self.extend([None] * (index + 1 - len(self)))
        super().__setitem__(index, value)


class IndexList(list):
    def __delitem__(self, index):
        if index == len(self) - 1:
            super().__delitem__(index)
        else:
            replacement = self.pop()
            replacement.index = index
            super().__setitem__(index, replacement)


PinDescriptor = namedtuple('PinDescriptor', ['node', 'pin', 'line'])


class PinIterator:
    def __init__(self, pa):
        self.pa = pa
        self.pin = 0

    def __next__(self):
        if self.pin >= len(self.pa.lines):
            raise StopIteration
        pd = PinDescriptor(self.pa.node, self.pin, self.pa.lines[self.pin])
        self.pin += 1
        return pd

    def __iter__(self): return self


class PinAccessor:
    def __init__(self, node, lines):
        self.node = node
        self.lines = lines

    def __getitem__(self, pin):
        if pin >= len(self.lines):
            return PinDescriptor(self.node, pin, None)
        return PinDescriptor(self.node, pin, self.lines[pin])

    def __len__(self):
        return len(self.lines)

    def first_unconnected(self):
        for pin, line in enumerate(self.lines):
            if line is None:
                return PinDescriptor(self.node, pin, None)
        return PinDescriptor(self.node, len(self.lines), None)

    def __iter__(self):
        return PinIterator(self)


class Node:
    def __init__(self, circuit, name, kind='__fork__'):
        if kind == '__fork__':
            if name in circuit.forks:
                raise ValueError(f'fork of name {name} already exists.')
            circuit.forks[name] = self
        else:
            if name in circuit.cells:
                raise ValueError(f'cell of name {name} already exists.')
            circuit.cells[name] = self
        self.index = len(circuit.nodes)
        circuit.nodes.append(self)
        self.circuit = circuit
        self.name = name
        self.kind = kind
        self.i_lines = GrowingList()
        self.o_lines = GrowingList()
        self.i = PinAccessor(self, self.i_lines)
        self.o = PinAccessor(self, self.o_lines)

    def __repr__(self):
        ins = ' '.join([f'<{p.line.driver.index}' if p.line is not None else '<None' for p in self.i])
        outs = ' '.join([f'>{p.line.reader.index}' if p.line is not None else '>None' for p in self.o])
        return f'{self.index}:{self.kind}"{self.name}" {ins} {outs}'

    def remove(self):
        self.__del__()

    def __del__(self):
        if self.circuit is None:
            return
        del self.circuit.nodes[self.index]
        if self.kind == '__fork__':
            del self.circuit.forks[self.name]
        else:
            del self.circuit.cells[self.name]
        self.circuit = None


class Line:
    def __init__(self, circuit, driver, reader):
        self.index = len(circuit.lines)
        circuit.lines.append(self)
        if driver.__class__ == Node:
            driver = driver.o.first_unconnected()
        if reader.__class__ == Node:
            reader = reader.i.first_unconnected()
        assert driver.__class__ == PinDescriptor
        assert reader.__class__ == PinDescriptor
        self.driver, self.driver_pin, _ = driver
        self.reader, self.reader_pin, _ = reader
        self.driver.o_lines[self.driver_pin] = self
        self.reader.i_lines[self.reader_pin] = self

    def __del__(self):
        pass

    def __repr__(self):
        return f'{self.index}'

    def __lt__(self, other):
        return self.index < other.index


class Circuit:
    def __init__(self, name=None):
        self.name = name
        self.nodes = IndexList()
        self.lines = IndexList()
        self.interface = GrowingList()
        self.cells = {}
        self.forks = {}

    def get_or_add_fork(self, name):
        if name in self.forks:
            return self.forks[name]
        else:
            return Node(self, name)

    def dump(self):
        header = f'{self.name}({",".join([str(n.index) for n in self.interface])})\n'
        return header + '\n'.join([str(n) for n in self.nodes])

    def __repr__(self):
        name = f" '{self.name}'" if self.name else ''
        return f'<Circuit{name} with {len(self.nodes)} nodes, {len(self.lines)} lines, {len(self.interface)} ports>'

    def topological_order(self):
        visit_count = [0] * len(self.nodes)
        queue = deque(n for n in self.nodes if len(n.i) == 0 or 'DFF' in n.kind)
        while len(queue) > 0:
            n = queue.popleft()
            for line in n.o_lines:
                if line is None: continue
                succ = line.reader
                visit_count[succ.index] += 1
                if visit_count[succ.index] == len(succ.i) and 'DFF' not in succ.kind:
                    queue.append(succ)
            yield n

    def topological_line_order(self):
        for n in self.topological_order():
            for line in n.o_lines:
                if line is not None:
                    yield line

    def reversed_topological_order(self):
        visit_count = [0] * len(self.nodes)
        queue = deque(n for n in self.nodes if len(n.o) == 0 or 'DFF' in n.kind)
        while len(queue) > 0:
            n = queue.popleft()
            for line in n.i_lines:
                pred = line.driver
                visit_count[pred.index] += 1
                if visit_count[pred.index] == len(pred.o) and 'DFF' not in pred.kind:
                    queue.append(pred)
            yield n

    def fanin(self, origin_nodes):
        marks = [False] * len(self.nodes)
        for n in origin_nodes:
            marks[n.index] = True
        for n in self.reversed_topological_order():
            if not marks[n.index]:
                for line in n.o_lines:
                    if line is not None:
                        marks[n.index] |= marks[line.reader.index]
            if marks[n.index]:
                yield n

    def fanout_free_regions(self):
        for stem in self.reversed_topological_order():
            if len(stem.o) == 1 and 'DFF' not in stem.kind: continue
            region = []
            if 'DFF' in stem.kind:
                n = stem.i_lines[0]
                if len(n.driver.o) == 1 and 'DFF' not in n.driver.kind:
                    queue = deque([n.driver])
                else:
                    queue = deque()
            else:
                queue = deque(n.driver for n in stem.i_lines if len(n.driver.o) == 1 and 'DFF' not in n.driver.kind)
            while len(queue) > 0:
                n = queue.popleft()
                preds = [pred.driver for pred in n.i_lines if len(pred.driver.o) == 1 and 'DFF' not in pred.driver.kind]
                queue.extend(preds)
                region.append(n)
            yield stem, region
