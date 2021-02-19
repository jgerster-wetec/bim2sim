from bim2sim.task.base import Task, ITask
from bim2sim.decision import Decision, BoolDecision
from bim2sim.task.hvac import hvac_graph
from bim2sim.kernel.element import BasePort

class DeadEnds(ITask):
    """Analyses graph network for dead ends"""

    reads = ('graph', )
    touches = ('graph', )

    @Task.log
    def run(self, workflow, graph):
        self.logger.info("Inspecting for dead ends")
        dead_ends_fc = self.identify_deadends(graph)
        self.logger.info("Found %s possible dead ends in network." % len(dead_ends_fc))
        graph, n_removed = self.decide_deadends(graph, dead_ends_fc)
        self.logger.info("Removed %s ports due to found dead ends." % n_removed)
        return (graph, )

    @staticmethod
    def identify_deadends(graph: hvac_graph.HvacGraph):
        """Identify deadends in graph. Dead ends are all ports of elements which are not connected with another port."""

        uncoupled_graph = graph.copy()
        element_graph = uncoupled_graph.element_graph
        for node in element_graph.nodes:
            inner_edges = node.get_inner_connections()
            uncoupled_graph.remove_edges_from(inner_edges)
        # find first class dead ends (open ports)
        # dead_ends_fc = (port for port in BasePort.objects.values()
        #                      if not port.is_connected())
        dead_ends_fc = [v for v, d in uncoupled_graph.degree() if d == 0]
        return dead_ends_fc

    @staticmethod
    def decide_deadends(graph: hvac_graph.HvacGraph, dead_ends_fc):
        """Make Decisions for all dead ends, if they are consumer or dead end."""
        remove_ports = {}
        for dead_end in dead_ends_fc:
            if len(dead_end.parent.ports) > 2:
                # dead end at > 2 ports -> remove port but keep element
                remove_ports[dead_end] = ([dead_end], [dead_end.parent])
                continue
            else:
                # todo: how to handle devices where we might want to connect dead ends istead delete
                remove_ports_strand = []
                remove_elements_strand = []
                # find if there are more elements in strand to be removed
                strand_ports = hvac_graph.HvacGraph.get_path_without_junctions(graph, dead_end, include_edges=True)
                strand = graph.subgraph(strand_ports).element_graph
                for port in strand_ports:
                    remove_ports_strand.append(port)
                for element in strand:
                    remove_elements_strand.append(element)
                remove_ports[dead_end] = (remove_ports_strand, remove_elements_strand)

        answers = {}
        decisions = []
        for dead_end, (port_strand, element_strand) in remove_ports.items():
            cur_decision = BoolDecision(
                "Found possible dead end at port %s with guid %s in system, "
                "please check if it is a dead end:" % (dead_end, dead_end.guid),
                output=answers,
                output_key=dead_end,
                global_key="deadEnd.%s" % dead_end.guid,
                allow_skip=True, allow_load=True, allow_save=True,
                collect=True, quick_decide=False, related={dead_end.guid}, context=set(element.guid for element in element_strand))
            decisions.append(cur_decision)
        Decision.decide_collected(collection=decisions)
        n_removed = 0
        for element, answer in answers.items():
            if answer:
                remove = remove_ports[element][0]
                n_removed += len(set(remove))
                graph.remove_nodes_from([n for n in graph if n in set(remove)])
            else:
                # todo handle consumers
                # dead end identification with guid decision (see issue97 add_gui_decision)
                # build clusters with position for the rest of open ports
                # decision to to group thiese open ports to consumers
                # delete the rest of open ports afterwards
                pass

        return graph, n_removed
