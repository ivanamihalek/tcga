#!/usr/bin/python

#
# This source code is part of tcga, a TCGA processing pipeline, written by Ivana Mihalek.
# Copyright (C) 2014-2016 Ivana Mihalek.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see<http://www.gnu.org/licenses/>.
# 
# Contact: ivana.mihalek@gmail.com
#

import sys, os
import MySQLdb
from   tcga_utils.mysql   import  *
from   tcga_utils.utils   import  *


#########################################
def main():

	if len(sys.argv) < 3:
		print  "usage: %s <gene symbol 1>  <gene symbol 2>" % sys.argv[0]
		exit(1)

	full_name = read_cancer_names ()

	# unbuffered output
	sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

	gene_symbol_1 = sys.argv[1].upper()
	gene_symbol_2 = sys.argv[2].upper()

	db     = connect_to_mysql()
	cursor = db.cursor()

	qry  = "select table_name from information_schema.tables "
	qry += "where table_schema='tcga' and table_name like '%_somatic_mutations'"
	tables = [field[0] for field in search_db(cursor,qry)]

	switch_to_db(cursor, "tcga")


	for table in tables:
		print "######################################"
		print table

		############################
		print "total number of entries:",
		qry = "select count(1) from " + table
		rows = search_db(cursor, qry)
		print  rows[0][0]

		if not rows[0][0]: continue

		############################
		print "number of patients:",
		qry  = "select distinct  sample_barcode_short from %s " % table
		rows = search_db(cursor, qry)
		number_of_patients =  len(rows)
		print number_of_patients

		############################
		qry = "select  variant_classification, aa_change, sample_barcode_short "
		qry += "from %s " % table
		qry += "where  hugo_symbol = '%s' " % gene_symbol_1
		rows = search_db (cursor, qry)
		if not rows:
			print 'no mutations found in ', gene_symbol_1
			continue
		print "%10s %15s  %10s  %20s  %15s" % ('sample id ', '#muts_in_sample', 'name1', 'variant1', 'aa_change1'),
		print "%10s  %20s  %15s" % ('name2', 'variant2', 'aa_change2')
		for row in rows:
			[variant_classification, aa_change, sample_barcode_short] = row
			# how many mutations in this particular sample?
			qry = "select count(1) from %s where sample_barcode_short = '%s'" % (table, sample_barcode_short)
			rows2 = search_db(cursor, qry)
			if not rows2:
				tot_number_of_mutations_in_sample = 0
			else:
				tot_number_of_mutations_in_sample = rows2[0][0]
			print sample_barcode_short,
			print " %15d  %10s  %20s  %15s  " % (tot_number_of_mutations_in_sample, gene_symbol_1,
												 variant_classification, aa_change),
			# do we have the second gene mutated in the same sample?
			qry = "select  variant_classification, aa_change"
			qry += " from %s " % table
			qry += " where  hugo_symbol = '%s' " % gene_symbol_2
			qry += " and  sample_barcode_short  = '%s' " % sample_barcode_short
			rows2 = search_db (cursor, qry)
			if not rows2:
				print "   %s  %20s " %  (gene_symbol_2, 'No mutations found')
			else:
				[variant_classification_2, aa_change_2] = rows2[0]
				print "   %s  %20s  %15s" % (gene_symbol_2, variant_classification_2, aa_change_2)
				for row2 in rows2[1:]:
					[variant_classification_2, aa_change_2] = row2
					print " "*80,
					print "   %s  %20s  %15s" % (gene_symbol_2, variant_classification_2, aa_change_2)

		print
		############################

	cursor.close()
	db.close()


#########################################
if __name__ == '__main__':
	main()

