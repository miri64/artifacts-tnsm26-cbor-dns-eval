BEGIN {
    FS=OFS=",";
    # cpb = common prefix bytes
    print "dataset", "prot", "msg", "qtype", "ip", "bytes", "cpb";
}
$NF ~ /^[0-9]+\s*$/ {
    gsub(/\s+/, "", $(NF));
    if (length($(NF - 1)) == 8) {
        aggr[$1][$4][$5][$6]["ipv4"][$(NF)]++;
    }
    if (length($(NF - 1)) == 32) {
        aggr[$1][$4][$5][$6]["ipv6"][$(NF)]++;
    }
}
END {
    for (dataset in aggr) {
        for (prot in aggr[dataset]) {
            for (msg in aggr[dataset][prot]) {
                for (qtype in aggr[dataset][prot][msg]) {
                    for (ip in aggr[dataset][prot][msg][qtype]) {
                        for (bytes in aggr[dataset][prot][msg][qtype][ip]) {
                            print dataset dataset_marker, prot, msg, qtype, ip, bytes,
                                  aggr[dataset][prot][msg][qtype][ip][bytes];
                        }
                    }
                }
            }
        }
    }
}
