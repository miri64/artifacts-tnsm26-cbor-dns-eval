BEGIN {
    FS=OFS=",";
    # csb = common suffix bytes
    # ccsb = common component suffix bytes
    print "dataset", "prot", "msg", "qtype", "bytes", "same_names", "csb", "ccsb";
}
$NF ~ /^[0-9]+\s*$/ && $(NF - 1) ~ /^[0-9]+\s*$/ && $(NF - 2) ~ /^[0-9]+\s*$/ {
    gsub(/\s+/, "", $(NF - 2));
    gsub(/\s+/, "", $(NF - 1));
    gsub(/\s+/, "", $(NF));
    aggr[$1][$4][$5][$6][$(NF - 1)][0] += $(NF - 2);
    aggr[$1][$4][$5][$6][$(NF - 1)][1]++;
    aggr[$1][$4][$5][$6][$(NF)][2]++;
}
END {
    for (dataset in aggr) {
        for (prot in aggr[dataset]) {
            for (msg in aggr[dataset][prot]) {
                for (qtype in aggr[dataset][prot][msg]) {
                    for (bytes in aggr[dataset][prot][msg][qtype]) {
                        print dataset dataset_marker, prot, msg, qtype, bytes,
                              aggr[dataset][prot][msg][qtype][bytes][0],
                              aggr[dataset][prot][msg][qtype][bytes][1],
                              aggr[dataset][prot][msg][qtype][bytes][2];
                    }
                }
            }
        }
    }
}
