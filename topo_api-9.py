import networkx as nx
from bluefog.common import topology_util
G = topology_util.InnerOuterExp2Graph(12, 3)
nx.draw_circular(G)