from abc import ABC, abstractmethod


class Component(ABC):
    @property
    def parent(self):
        return self._parent
    
    @parent.setter
    def parent(self, parent):
        self._parent = parent

    @abstractmethod
    def operation(self):
        pass


class Leaf(Component):
    def operation(self):
        return "Leaf"
    

class Composite(Component):
    def __init__(self):
        self._children = []

    def add(self, component):
        self._children.append(component)
        component.parent = self

    def remove(self, component):
        self._children.remove(component)
        component.parent = None

    def operation(self):
        results = []
        for child in self._children:
            results.append(child.operation())
        return f"Branch({'+'.join(results)})"
    

def client_code(component):
    print(f"Result: {component.operation()}")
    

if __name__ == "__main__":
    simple = Leaf()
    client_code(simple)

    tree = Composite()
    branch1 = Composite()
    branch1.add(Leaf())
    branch1.add(Leaf())
    branch2 = Composite()
    branch2.add(Leaf())
    tree.add(branch1)
    tree.add(branch2)

    client_code(tree)
