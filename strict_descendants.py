"""Strict descendant reachability for an explicitly supplied directed graph."""
from collections import defaultdict, deque


def child_adjacency(pairs, nodes):
    nodes=set(nodes)
    result=defaultdict(set)
    for child,parent in pairs:
        if child not in nodes or parent not in nodes:
            raise ValueError('Graph endpoint outside declared population')
        result[parent].add(child)
    return result


def strict_descendants(children, root):
    distances={root:0}
    queue=deque([root])
    while queue:
        node=queue.popleft()
        for child in children.get(node,()):
            if child not in distances:
                distances[child]=distances[node]+1
                queue.append(child)
    return len(distances)-1,max(distances.values())
