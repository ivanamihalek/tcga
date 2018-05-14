
from icgc_utils.mysql   import  *
########################################
def find_chromosome(cursor, gene):
	qry = "select chromosome from hgnc where approved_symbol = '%s'" % gene
	ret = search_db(cursor,qry)
	if not ret or ret ==[]:
		print "chromosome not found for %s (?)"%gene
		search_db(cursor,qry,verbose=True)
		exit()
	return ret[0][0]

########################################
def get_donors(cursor, table):
	qry  = "select distinct(icgc_donor_id) from %s " % table
	return [ret[0] for ret in search_db(cursor,qry)]

def get_mutations(cursor, table):
	qry = "select  distinct(icgc_mutation_id)  from %s " % table
	return [ret[0] for ret in search_db(cursor,qry)]

def get_specimens_from_donor(cursor, table, icgc_donor_id):
	qry = "select  distinct(icgc_specimen_id)  from %s " % table
	qry += "where icgc_donor_id = '%s'" % icgc_donor_id
	return [r[0] for r in search_db(cursor,qry)]

def get_specimen_type(cursor, table, spec_ids):
	specimen_type = {}
	for spec_id in spec_ids:
		qry = " select specimen_type from %s " % table.replace("simple_somatic","specimen")
		qry += "where icgc_specimen_id = '%s'" % spec_id
		specimen_type[spec_id] = search_db(cursor,qry)[0][0]
	return specimen_type

def get_mutations_from_donor(cursor, table, icgc_donor_id):
	qry = "select  distinct(icgc_mutation_id)  from %s " % table
	qry += "where icgc_donor_id = '%s'" % icgc_donor_id
	return [r[0] for r in search_db(cursor,qry)]

def mutation_provenance(cursor, table, icgc_donor_id, icgc_mutation_id):
	qry = "select  distinct(icgc_specimen_id)  from %s " % table
	qry += "where icgc_donor_id='%s' and icgc_mutation_id='%s'" % (icgc_donor_id, icgc_mutation_id)
	return [r[0] for r in search_db(cursor,qry)]

#########################################
def mutations_in_gene_old(cursor, approved_symbol):
	qry  = "select ensembl_gene_id_by_hgnc, ensembl_gene_id, chromosome from hgnc "
	qry += "where approved_symbol = '%s'" % approved_symbol
	ensembl_gene_id_by_hgnc, ensembl_gene_id, chromosome = search_db(cursor,qry)[0]
	if ensembl_gene_id_by_hgnc != ensembl_gene_id:
		print "Ensembl id mismatch: (ensembl_gene_id_by_hgnc, ensembl_gene_id)"
		print approved_symbol, ensembl_gene_id_by_hgnc, ensembl_gene_id
		exit()

	qry  = "select m.icgc_mutation_id from mutations_chrom_%s m, locations_chrom_%s l "  % (chromosome, chromosome)
	qry += "where m.pathogenic_estimate=1 and m.start_position=l.position "
	qry += "and l.gene_relative like '%%%s%%' " % ensembl_gene_id
	ret = search_db(cursor,qry, verbose=True)
	if not ret: return []
	return [r[0] for r in ret]

#########################################
def mutations_in_gene(cursor, approved_symbol):
	qry  = "select icgc_mutation_id from mutation2gene "
	qry += "where gene_symbol='%s'" % approved_symbol
	ret = search_db(cursor,qry, verbose=True)
	if not ret: return []
	return [r[0] for r in ret]

#########################################
def pathogenic_mutations_in_gene(cursor, approved_symbol, chromosome, use_reliability=True):
	qry  = "select map.icgc_mutation_id from mutation2gene map, mutations_chrom_%s mut " % chromosome
	qry += "where map.gene_symbol='%s' " % approved_symbol
	qry += "and map.icgc_mutation_id=mut.icgc_mutation_id "
	qry += "and mut.pathogenic_estimate=1 "
	if use_reliability: qry += "and mut.reliability_estimate=1 "
	ret = search_db(cursor,qry, verbose=True)
	if not ret: return []
	return [r[0] for r in ret]

#########################################
def try_to_resolve(cursor, old_ensembl_gene_id):
	# not sure how stable or reliable this is, but if there is no common transcript,
	# something iss seriously foul with the old_ensembl_gene_id
	switch_to_db(cursor,"homo_sapiens_core_91_38")
	qry = "select distinct(gene_stable_id) from gene_archive "
	qry += "where transcript_stable_id in  "
	qry +="(select transcript_stable_id from gene_archive where gene_stable_id = '%s')" % old_ensembl_gene_id
	ret = search_db(cursor,qry)
	if not ret: return None

	candidate_ids = [r[0] for r in ret if r[0]!=old_ensembl_gene_id]
	if len(candidate_ids)==0: return None  # there should be another identifier, besides the one we started from

	latest_ensembl_entries = []
	for  candidate in candidate_ids:
		qry = "select * from gene  where stable_id = '%s'" % candidate
		if not search_db(cursor,qry): continue  # this is another old identifier
		latest_ensembl_entries.append(candidate)
	#I'm not sure what to make of this if there are two live identifiers
	# that the old one maps to
	if len(latest_ensembl_entries) != 1: return None

	new_ensembl_gene_id = latest_ensembl_entries[0]

	qry = "select approved_symbol from icgc.hgnc where ensembl_gene_id='%s'"% new_ensembl_gene_id
	ret = search_db(cursor,qry)
	if not ret: return None
	return ret[0][0]


def get_approved_symbol(cursor, ensembl_gene_id):
	qry = "select approved_symbol from hgnc where ensembl_gene_id='%s'"% ensembl_gene_id
	ret = search_db(cursor,qry)
	if not ret:
		symbol = try_to_resolve(cursor, ensembl_gene_id)
		# if it cannot be resolved, just use the ensembl_id_itself
		if not symbol: symbol=ensembl_gene_id
		switch_to_db(cursor,"icgc")

	else:
		symbol = ret[0][0]
	return symbol