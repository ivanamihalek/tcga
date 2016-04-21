#!/usr/bin/python -u

from   tcga_utils.utils   import  *
from   tcga_utils.ensembl   import  *
import matplotlib.pyplot as plt
from time import time
drop_silent = True
special = None

#########################################
def rank_message ( gene_name, freq_gene):
    rank_msg = ""
    if gene_name in freq_gene.keys():
        less_mutated = len( [y for y in  freq_gene.values() if y<freq_gene[gene_name]])
        more_mutated = len( [y for y in  freq_gene.values() if y>freq_gene[gene_name]])
        rank_msg = "%7s  mutated in %.1f%% patients   (rank: %d-%d)  " % (gene_name, freq_gene[gene_name], more_mutated, len(freq_gene)-less_mutated)
        middle_range = float(more_mutated + len(freq_gene)-less_mutated)/2.0
    else:
        rank_msg = "%7s   rank: %d  (no patients)" %  (gene_name, len(freq_gene))
        middle_range = -1
    return [rank_msg, middle_range]

#########################################
def  live_plot ( title, freq_gene, sorted_genes, filename):


    fig, ax1 = plt.subplots(1, 1)
    ax1.set_title (title, fontsize=24)
    ax1.set_xlabel('genes, listed by their rank', fontsize = 20)
    ax1.set_ylabel('% of patients', fontsize = 24)
    if special:
        [rank_msg, middle_range] = rank_message(special, freq_gene)
    bg_color = (0, 102./255, 204./255)
    ax1.set_axis_bgcolor(bg_color)
    x = range(1,len(sorted_genes)+1)
    y = [freq_gene[gene] for gene in sorted_genes]
    ylim = min(max(y),10)
    xlim = len(sorted_genes)
    if special:

        bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.8)
        ax1.text(xlim*0.9, ylim*0.9, rank_msg, ha="right", va="top", size=14, bbox=bbox_props)
        if middle_range < 0: middle_range = xlim
        ax1.annotate ('',  xy=(middle_range, 0),  # use the axes data coordinate system
                xytext=(middle_range, ylim/2),    # fraction, fraction
                arrowprops=dict(facecolor='red', shrink=0.05),
                horizontalalignment='left',
                verticalalignment='bottom')

    ax1.fill_between(x, y,  interpolate=True, color=(255./255,153./255,51./255))

    plt.ylim(0,ylim)
    plt.xlim(0,xlim)

    if filename:
        plt.savefig(filename)
    else:
        plt.show()



#########################################
def main():
    
    db     = connect_to_mysql()
    cursor = db.cursor()

    db_names  = ["ACC", "BLCA", "BRCA", "CESC", "CHOL", "COAD","ESCA",  "GBM", "HNSC", "KICH" ,"KIRC",
                 "KIRP","LAML", "LGG", "LIHC", "LUAD", "LUSC", "OV", "PAAD", "PCPG", "PRAD", "REA",
                 "SARC", "SKCM", "STAD", "TGCT", "THCA", "THYM", "UCEC", "UCS", "UVM"]
    #db_names = ["COAD"]

    full_name = read_cancer_names ()
    pancan_freq = {}
    pancan_silent = {}
    pancan_non_silent = {}
    grand_total_patients = 0
    for db_name in db_names:
        print "######################################"
        print db_name
        switch_to_db (cursor, db_name)

        ############################
        print db_name, "number of somatic_mutations:"
        qry = "select count(1)from somatic_mutations"
        rows = search_db(cursor, qry)
        print "\t", rows[0][0]
        print

        ############################
        print "number of different genes:"
        qry = "select distinct(hugo_symbol) from somatic_mutations"
        rows  = search_db(cursor, qry)
        genes = [row[0] for row in  rows]
        print "\t", len(genes)

        ############################
        print "number of different patients:"
        qry = "select distinct(sample_barcode_short) from somatic_mutations"
        rows = search_db(cursor, qry)
        patients = [row[0] for row in  rows]
        total_patients = len(patients)
        print "\t", total_patients

        grand_total_patients += total_patients

        ############################
        print "frequencies reported per gene"
        freq_gene = {}
        special_dropped = False
        silent_ct = 0
        non_silent_ct = 1
        prev_time = time()

        ct = 0
        genes = ['RPL5', 'RPL11', 'TP53', 'APC']
        for gene in genes:
            ct += 1
            if not ct%1000:
                print "%4d out of %4d, time for the last 1000: %8.3f s" % (ct, len(genes), time()-prev_time)
                prev_time = time()


            [silent_ct, non_silent_ct] = silent_proportion(cursor, gene)
            print gene, silent_ct, non_silent_ct
            if drop_silent and  (non_silent_ct==0 or float(silent_ct)/non_silent_ct>0.15):
                if non_silent_ct==0:
                    print gene, 'non_silent_ct == 0', '  dropping'
                else:
                    print gene, " %6.4f " % (float(silent_ct)/non_silent_ct), '  dropping'
                continue

            qry  = "select sample_barcode_short, count(sample_barcode_short) from somatic_mutations "
            qry += "where hugo_symbol='%s' " % gene
            qry += "and variant_classification!='silent' and variant_classification!='RNA' "
            qry += "group by sample_barcode_short"
            rows = search_db(cursor, qry)
            if rows:
                no_patients = len(rows)
            else:
                no_patients = 0
            if no_patients==0: continue


            if not pancan_freq.has_key(gene):
                pancan_freq[gene]   = 0
                pancan_silent[gene] = 0
                pancan_non_silent[gene] = 0
            pancan_freq[gene]       += no_patients
            pancan_silent[gene]     += silent_ct
            pancan_non_silent[gene] += non_silent_ct
            freq_gene[gene] = float(no_patients)/total_patients*100
            print gene, silent_ct, non_silent_ct
            print gene, pancan_silent[gene], pancan_non_silent[gene]
            print '-'*20

        if special and special_dropped: continue
        ###################################
        # in individual tumor types:
        if False:
            filename = db_name+"_somatic_freq.png"
            title = full_name[db_name]
            sorted_genes =  sorted(freq_gene.keys(), key= lambda x: -freq_gene[x])
            live_plot (title, freq_gene, sorted_genes, filename)

    for gene in pancan_freq.keys():
        pancan_freq[gene] /= float(grand_total_patients)
        pancan_freq[gene] *= 100

    sorted_genes =  sorted(pancan_freq.keys(), key= lambda x: -pancan_freq[x])
    for gene in sorted_genes:
        print " %10s   %6d%%    %6.4f    %4d   %4d " % (gene,  round(pancan_freq[gene]),
                                                        float(pancan_silent[gene])/pancan_non_silent[gene],
                                                        pancan_silent[gene], pancan_non_silent[gene])
    # special interest:
    if special:
        gene = special
        print " %10s   %6d%%    %6.4f   %3d  %3d  %5d " % (gene,  round(pancan_freq[gene]),
                                                          float(pancan_silent[gene])/pancan_non_silent[gene],
                                                          pancan_silent[gene], pancan_non_silent[gene],
                                                          sorted_genes.index(gene))

    filename = "pancan_somatic_freq.filtered_for_silent_proportion.png"
    #live_plot ("Pan-cancer statistics", pancan_freq, sorted_genes, filename)

    cursor.close()
    db.close()


#########################################
if __name__ == '__main__':
    main()
