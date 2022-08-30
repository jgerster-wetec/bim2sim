from bim2sim.task.base import ITask
from bim2sim.decision import BoolDecision, DecisionBunch
from bim2sim.task.hvac.hvac import hvac_graph
from bim2sim.workflow import Workflow


class DeadEnds(ITask):
    """Analyses graph network for dead ends and removes ports due to dead ends."""

    reads = ('graph', )
    touches = ('graph', )

    def run(self, workflow: Workflow, graph: hvac_graph) -> hvac_graph:
        self.logger.info("Inspecting for dead ends")
        pot_dead_ends = self.identify_dead_ends(graph)
        self.logger.info("Found %s possible dead ends in network." % len(pot_dead_ends))
        graph, n_removed = yield from self.decide_dead_ends(graph, pot_dead_ends, False)
        self.logger.info("Removed %s ports due to found dead ends." % n_removed)
        if __debug__:
            self.logger.info("Plotting graph ...")
            graph.plot(self.paths.export)
            graph.plot(self.paths.export, ports=True)
        return graph,

    @staticmethod
    def identify_dead_ends(graph: hvac_graph.HvacGraph) -> list:
        """Identify dead ends in graph. Dead ends are all ports of elements which
         are not connected with another port.

        Args:
            graph (hvac_graph.HvacGraph): HVAC graph being analysed

        Returns:
            pot_dead_ends (list): List of potential dead ends
        """

        uncoupled_graph = graph.copy()
        element_graph = uncoupled_graph.element_graph
        for node in element_graph.nodes:
            inner_edges = node.inner_connections
            uncoupled_graph.remove_edges_from(inner_edges)
        # find first class dead ends (open ports)
        pot_dead_ends = [v for v, d in uncoupled_graph.degree() if d == 0]
        return pot_dead_ends

    @staticmethod
    def decide_dead_ends(graph: hvac_graph.HvacGraph, pot_dead_ends: list,
                         force=False) -> [{hvac_graph.HvacGraph}, int]:
        """Decides for all dead ends whether they are consumers or dead ends.

        Args:
            graph (hvac_graph.HvacGraph): HVAC graph being analysed
            pot_dead_ends (list): List of potential dead ends
            force (bool): If True, then all potential dead ends are removed

        Returns:
            graph (hvac_graph.HvacGraph): HVAC graph where dead ends are removed
            n_removed (int): Number of removed ports due to dead ends
        """
        n_removed = 0
        remove_ports = {}
        for dead_end in pot_dead_ends:
            if len(dead_end.parent.ports) > 2:
                # dead end at > 2 ports -> remove port but keep element
                remove_ports[dead_end] = ([dead_end], [dead_end.parent])
                continue
            else:
                # TODO: how to handle devices where we might want to connect dead ends instead delete
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

        if force:
            for dead_end in pot_dead_ends:
                remove = remove_ports[dead_end][0]
                n_removed += len(set(remove))
                graph.remove_nodes_from([n for n in graph if n in set(remove)])
        else:
            decisions = DecisionBunch()
            for dead_end, (port_strand, element_strand) in remove_ports.items():
                cur_decision = BoolDecision(
                    "Found possible dead end at port %s with guid %s in system, "
                    "please check if it is a dead end:" % (dead_end, dead_end.guid),
                    key=dead_end,
                    global_key="deadEnd.%s" % dead_end.guid,
                    allow_skip=True,
                    related={dead_end.guid}, context=set(element.guid for element in element_strand))
                decisions.append(cur_decision)
            yield decisions
            answers = decisions.to_answer_dict()
            n_removed = 0
            for element, answer in answers.items():
                if answer:
                    remove = remove_ports[element][0]
                    n_removed += len(set(remove))
                    graph.remove_nodes_from([n for n in graph if n in set(remove)])
                else:
                    raise NotImplementedError()
                    # TODO: handle consumers
                    # dead end identification with guid decision (see issue97 add_gui_decision)
                    # build clusters with position for the rest of open ports
                    # decision to to group these open ports to consumers
                    # delete the rest of open ports afterwards
        return graph, n_removed
