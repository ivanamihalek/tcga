#! /usr/bin/python3
#
# This source code is part of icgc, an ICGC processing pipeline.
#
# Icgc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Icgc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see<http://www.gnu.org/licenses/>.
#
# Contact: ivana.mihalek@gmail.com
#

# some pathways do not have the associated genes listed, probably by mistake
# examples:
# R-HSA-1483171       | Synthesis of BMP
# R-HSA-2408499       | Formation of selenosugars for excretion

from icgc_utils.common_queries import quotify
from icgc_utils.mysql import  *
from config import Config
# https://networkx.github.io/documentation/stable/index.html
import networkx as nx

def count_successors(graph, pthwy_id):
	return len(list(graph.successors(pthwy_id)))

def genes_in_subgraph(cursor, graph, parent_id):
	genes = []
	# this is the whole subtree
	descendants = [pid for pid in nx.dfs_preorder_nodes(graph, parent_id) if count_successors(graph, pid) == 0]

	desc_id_string = ",".join([quotify(d) for d in descendants])
	qry = "select distinct(ensembl_gene_id) from  ensembl2reactome "
	qry += "where reactome_pathway_id in (%s)" % desc_id_string
	ret = error_intolerant_search(cursor,qry)
	if not ret:
		print("possible problem in Reactome: no associated genes found for ", desc_id_string)
		return []
	return [r[0] for r in ret]


##############
def print_genes(cursor, gene_ids, depth):
	if len(gene_ids)<1:
		print("\t"*depth, "no genes listed")
		return
	#print("\t"*depth, "print genes here")
	gene_id_string = ",".join([quotify(z) for z in gene_ids])
	qry = "select ensembl_gene_id, approved_name from hgnc  where ensembl_gene_id in (%s)" % gene_id_string
	gene_names = dict(hard_landing_search(cursor, qry))
	for gene in gene_ids:
		print("\t"*depth, gene, gene_names.get(gene,""))
	return


##############
def characterize_subtree(cursor, graph, pthwy_id, gene_groups, depth,  verbose=True):
	# this is the whole subtree
	# children = [node for node in nx.dfs_preorder_nodes(graph, pthwy_id)]
	# A successor of n is a node m such that there exists a directed edge from n to m.
	children = [node for node in graph.successors(pthwy_id)]
	if len(children)==0: return False
	node_id_string = ",".join([quotify(z) for z in children])
	qry_template = "select * from reactome_pathways where reactome_pathway_id in (%s)"
	children_names = hard_landing_search(cursor, qry_template % node_id_string)
	for child_id, child_name in children_names:
		# number_of_genes = genes related to nodes without descendants
		genes = genes_in_subgraph(cursor, graph, child_id)
		if verbose: print("\t"*depth, child_id, child_name, len(genes))
		if len(genes)<100:
			if verbose: print_genes(cursor, genes, depth+1)
			gene_groups[child_name] = genes
			continue
		if not characterize_subtree(cursor, graph, child_id, gene_groups, depth+1, verbose=verbose): # no further subdivisions
			if verbose: print_genes(cursor, genes, depth+1)
			gene_groups[child_name] = genes
			continue
	return True

#########################################
import numpy as np
from matplotlib import pyplot as plt

def hist_plot(gene_groups):
	data = [len(gene_list) for gene_list in list(gene_groups.values())]
	# fixed bin size
	bins = np.arange(0, 105, 5) # fixed bin size
	plt.xlim(0,101)
	plt.hist(data, bins=bins, alpha=0.5)
	# plt.title('Random Gaussian data (fixed bin size)')
	# plt.xlabel('variable X (bin size = 5)')
	# plt.ylabel('count')
	#
	plt.show()

####################################################
def main():

	verbose = False

	db     = connect_to_mysql(Config.mysql_conf_file)
	cursor = db.cursor()

	switch_to_db(cursor, 'icgc')

	# are there children with multiple parents? Yes. So I need some kind of
	# directed graph, rather tha a tree.
	qry = "select child, count(distinct parent) as ct from reactome_hierarchy "
	qry += "group by child having ct>1"
	ret = search_db(cursor, qry)
	print("number of children with multiple parents:", len(ret))

	# feed the parent/child pairs as edges into graph
	ret = hard_landing_search(cursor, 'select parent, child from reactome_hierarchy')
	graph = nx.DiGraph(ret) # directed graph
	print("graph is directed: ", graph.is_directed())
	print("number of edges:", len(graph.edges))
	print("graph is multigraph:", graph.is_multigraph())
	try:
		edges = nx.find_cycle(graph)
	except:
		print("hooray, no cycles found")

	# graph.in_degree is a list of pairs, rather than a method

	# candidate roots
	zero_in_degee_nodes = [name for name, indegree in graph.in_degree if indegree==0]

	node_id_string = ",".join([quotify(z) for z in zero_in_degee_nodes])
	qry_template = "select * from reactome_pathways where reactome_pathway_id in (%s)"
	root_names =  hard_landing_search(cursor, qry_template% node_id_string)
	gene_groups = {}
	for pthwy_id, name in root_names:
		if "disease" in name.lower(): continue
		if verbose: print(pthwy_id, name)
		characterize_subtree(cursor, graph, pthwy_id,  gene_groups,  1, verbose=verbose)
	cursor.close()
	db.close()

	# print("\n===========================")
	# for group, genes in gene_groups.items():
	# 	print (group, len(genes))
	hist_plot(gene_groups)


#########################################
if __name__ == '__main__':
	main()
