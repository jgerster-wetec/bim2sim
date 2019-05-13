﻿""" This module holds a HVACSystem object which is -represented by a graph
network
where each node represents a hvac-component
"""

import os
import logging

import networkx as nx
import matplotlib.pyplot as plt

#from bim2sim.ifc2python.aggregation import PipeStrand


class HvacGraph(object):
    def __init__(self, instances:list):
        self.logger = logging.getLogger(__name__)
        #self.instances = instances
        #self.parent = parent
        #self.instance_nodes = []
        #self.port_nodes = []
        #self.edges = []
        self.graph = self._create_hvac_network_by_ports(instances)
        #self.cycles = []
        #self.aggregated_instances = []
        #self.parent.representations.append(self)

    def _create_hvac_network_by_ports(self, instances):
        """
        This function creates a graph network of the raw instances. Each
        component and each port of the instances is represented by a node.
        """
        self.logger.info("Creating HVAC graph representation ...")
        graph = nx.DiGraph()
        #self.instance_nodes = list(self.instances.values())

        port_nodes = [port for instance in instances for port in
                       instance.ports]
        edges = [(port, connected_port) for port in port_nodes for
                      connected_port in port.connections]
        nodes = instances + port_nodes
        graph.update(nodes=nodes, edges=edges)

        hvac_graph = self._contract_ports_into_elements(graph, port_nodes)
        self.logger.info("HVAC graph building is completed")
        return hvac_graph

    def _contract_ports_into_elements(self, graph, port_nodes):
        """
        Contract the port nodes into the belonging instance nodes for better
        handling, the information about the ports is still accessible via the
        get_contractions function.
        :return:
        """

        self.logger.info("Contracting ports into elements ...")
        for port in port_nodes:
            graph = nx.contracted_nodes(graph, port.parent, port)
        self.logger.info("Contracted the ports into node instances, this"
                         " leads to %d nodes.",
                         graph.number_of_nodes())
        return graph

    

    #def _create_aggregations(self, aggregations, subgraph_aggregations,
    #                         hvac_graph):
    #    """
    #    Create aggregations for the reducible models. For now only pipestrand
    #    aggregation is integrated.

    #    :param aggregations: list of all aggregations
    #    :param subgraph_aggregations: subgraph that holds only the aggregatinos
    #    :param hvac_graph:
    #    :return:
    #    """

    #    def _get_start_and_end_ports(pipestrand, subgraph_aggregations):
    #        """
    #        Finds and sets the first and last port of the pipestrand.
    #        :param pipestrand:
    #        :param subgraph_aggregations:
    #        :return:
    #        """

    #        # todo: @dja direction sensitivity?
    #        inner_boundarys = [x for x in subgraph_aggregations.nodes() if
    #                           subgraph_aggregations.degree(x) == 1 and x in
    #                           pipestrand.models]
    #        for inner_boundary in inner_boundarys:
    #            for port in inner_boundary.ports:
    #                for connection in port.connections:
    #                    if not subgraph_aggregations.has_node(
    #                            connection.parent):
    #                        pipestrand.ports.append(port)

    #    def _update_network(graph, pipestrand):
    #        """
    #        Updates the network by:
    #         - deleting old nodes which are now represented by the aggregation
    #         - connecting the aggregation to the rest of the network
    #        :param graph:
    #        :param pipestrand:
    #        :return:
    #        """
    #        graph.add_node(pipestrand)
    #        outer_connections = [connection for port in pipestrand.ports
    #                             for
    #                             connection in port.connections]

    #        for element in pipestrand.elements:
    #            element.aggregation = pipestrand
    #            graph.remove_node(element)

    #        for port in outer_connections:
    #            other_port = port.connections[0]
    #            node = graph.node[port.parent]
    #            del node['contraction'][port]
    #            graph.add_edge(port, other_port)
    #            graph = nx.contracted_nodes(graph, port.parent, port)
    #            graph = nx.contracted_nodes(graph, pipestrand, other_port)
    #        return graph

    #    nr = 0
    #    for aggregation in aggregations:
    #        name = 'PipeStrand' + str(nr)
    #        pipestrand = PipeStrand(name, aggregation)
    #        self.aggregated_instances.append(pipestrand)
    #        _get_start_and_end_ports(pipestrand, subgraph_aggregations)
    #        hvac_graph = _update_network(hvac_graph, pipestrand)
    #        nr += 1

    #        self.graph = hvac_graph
    #    self.logger.info("Aggregation finished, reduced network to "
    #                     "%d nodes.", self.graph.number_of_nodes())

    #def find_aggregations(self, hvac_graph, aggregation_type):
    #    """
    #    This function reduces the network by searching for reducable
    #    elements.
    #    Pipes:
    #        All elements with a degree of 2 which are determined as
    #        reducible are put in a seperated, undirected subgraph. Then a
    #        list is created which holds all connected strangs of
    #        elements.
    #        For each of this strangs an aggregation element (pipestrand) is
    #        created.

    #    :param hvac_graph:
    #    :param aggregation_type:
    #    :return:
    #    """
    #    # todo do this later with factory method, for now only a test
    #    if aggregation_type == 'pipes':
    #        reducible_elements = PipeStrand.aggregatable_elements
    #        self.logger.info("Reducing the network by contracting pipes into "
    #                         "pipestrands ...")
    #        undirected_graph = nx.Graph(hvac_graph)
    #        nodes_degree2 = [v for v, d in undirected_graph.degree() if d ==
    #                         2 and v.ifc_type in reducible_elements]
    #        subgraph_aggregations = nx.subgraph(undirected_graph, nodes_degree2)
    #        aggregations = list([list(x) for x in list(nx.connected_components(
    #            subgraph_aggregations)) if len(x) > 1])

    #        self._create_aggregations(aggregations, subgraph_aggregations,
    #                              hvac_graph)

    def get_not_contracted_neighbors(self, graph, node):
        neighbors = list(
            set(nx.all_neighbors(graph, node)) -
            set(graph.node[node]['contracted_nodes']) -
            {node}
        )
        return neighbors

    def get_contractions(self, node):
        """
        Returns a list of contracted nodes for the passed node.
        :param node: node in whose connections you are interested
        :return:
        """
        node = self.graph.node[node]
        inner_nodes = []
        if 'contraction' in node:
            for contraction in node['contraction'].keys():
                inner_nodes.append(contraction)
        return inner_nodes

    def get_cycles(self):
        """
        Find cycles in the graph.
        :return cycles:
        """
        self.logger.info("Searching for cycles in hvac network ...")
        undirected_graph = nx.Graph(self.graph)
        cycles = nx.cycle_basis(undirected_graph)
        self.logger.info("Found %d cycles", len(cycles))
        return cycles

    def get_type_chains(self, types):
        """Returns lists of consecutive elements of the given types ordered as connected.
        
        :param types: iterable of ifcType names"""

        undirected_graph = nx.Graph(self.graph)
        nodes_degree2 = [v for v, d in undirected_graph.degree() if d ==
                            2 and v.ifc_type in types]
        subgraph_aggregations = nx.subgraph(undirected_graph, nodes_degree2)

        chain_lists = []
        # order elements as connected
        for subgraph in nx.connected_component_subgraphs(subgraph_aggregations):
            end_nodes = [v for v, d in subgraph.degree() if d == 1]
            if len(end_nodes) != 2:
                continue
            elements = nx.shortest_path(subgraph, *end_nodes) # TODO more efficient
            chain_lists.append(elements)

        return chain_lists

    def replace(self, elements, replacement=None):
        """Replaces elements in graph with replaement. If replacement is not given elements are deleted.

        Updates the network by:
            - deleting old nodes which are now represented by the aggregation
            - connecting the aggregation to the rest of the network
        :param elements:
        :param replacement:
        :return graph:
        """

        if replacement:
            self.graph.add_node(replacement)
    
            outer_connections = [connection for port in replacement.ports
                for connection in port.connections]

            for port in outer_connections:
                other_port = port.connections[0]
                node = self.graph.node[port.parent]
                del node['contraction'][port]
                self.graph.add_edge(port, other_port)
                self.graph = nx.contracted_nodes(self.graph, port.parent, port)
                self.graph = nx.contracted_nodes(self.graph, replacement, other_port)

        for element in elements:
            self.graph.remove_node(element)

        return self.graph

    def get_nodes(self):
        """Returns list of nodes represented by graph"""
        return list(self.graph.nodes)

    def plot(self, path=None):
        """Plot graph
        
        if path is provided plot is saved as pdf else it gets displayed"""
        nx.draw(self.graph, node_size=3, font_size=6,
                with_labels=True)
        plt.draw()
        if path:
            plt.savefig(
                os.path.join(path, 'graphnetwork.pdf'),
                bbox_inches='tight')
        else:
            plt.show()

