from typing import Dict, List


class Vertex:

    def __init__(self):
        self.dependents = []
        self.dependencies = []


class DependencyGraph:

    def __init__(self):
        self.vertices: Dict[str, Vertex] = {}

    def add_node(self, name: str) -> None:
        if name in self.vertices:
            return
        self.vertices[name] = Vertex()

    def add_dependency(self, dependent: str, dependency: str) -> None:
        self.add_node(dependent)
        self.add_node(dependency)
        self.vertices[dependent].dependencies.append(dependency)
        self.vertices[dependency].dependents.append(dependent)

    def in_degree(self, name: str) -> int:
        vertex = self.vertices[name]
        return 0 if vertex is None else len(vertex.dependents)

    def out_degree(self, name: str) -> int:
        vertex = self.vertices[name]
        return 0 if vertex is None else len(vertex.dependencies)
