#!/usr/bin/python
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

import MySQLdb

from config import Config
from icgc_utils.mysql   import  *

#########################################
#########################################
def main():


	db     = connect_to_mysql(Config.mysql_conf_file)
	cursor = db.cursor()

	switch_to_db(cursor,"icgc")

	# indices on simple somatic temp
	qry  = "select table_name from information_schema.tables "
	qry += "where table_schema='icgc' and table_name like 'mutations_chrom_%'"
	tables = [field[0] for field in  search_db(cursor,qry)]
	for table in tables:
		print(table)
		create_index(cursor, 'icgc', 'mut_idx', table, ['start_position', 'mutated_from_allele', 'mutated_to_allele'])


	cursor.close()
	db.close()

#########################################
if __name__ == '__main__':
	main()

