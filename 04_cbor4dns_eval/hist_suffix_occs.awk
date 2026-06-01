BEGIN {FS=OFS=","}

NR > 1 && $12 > 0 {
    suffix=substr($9,length($9)-$13+1,$13);
    if (suffix ~ /^\./) {
        gsub(/^\.+/, "", suffix)
    }
    # count suffixes per message
    names[$1][$2][$3][$4][$5][$6][suffix]++;
}

END {
    for (d in names) {
        for (f in names[d]) {
            for (n in names[d][f]) {
                for (p in names[d][f][n]) {
                    for (m in names[d][f][n][p]) {
                        for (q in names[d][f][n][p][m]) {
                            for (s in names[d][f][n][p][m][q]) {
                                # create histogram of occurrences per message
                                suffix_occs[d][p][m][q][names[d][f][n][p][m][q][s]]++
                            }
                        }
                    }
                }
            }
        }
    }
    # print histogram
    print "dataset", "protocol", "msg", "qtype", "occurrences", "count";
    for (d in suffix_occs) {
        for (p in suffix_occs[d]) {
            for (m in suffix_occs[d][p]) {
                for (q in suffix_occs[d][p][m]) {
                    for (o in suffix_occs[d][p][m][q]) {
                        print d,p,m,q,o,suffix_occs[d][p][m][q][o];
                    }
                }
            }
        }
    }
}
