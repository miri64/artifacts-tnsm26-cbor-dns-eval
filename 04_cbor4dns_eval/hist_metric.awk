BEGIN {
    OFS=FS=","
}
NR == 1 {
    col1_name=$col1
    gsub(/[[:cntrl:][:space:]]+$/,"")
    if (col2) {
        col2_name=$col2
    }
}
NR > 1 {
    gsub(/[[:cntrl:][:space:]]+$/,"")
    if (!match($col1, /^$/)) {
        if (($col1 < 0) && (factor != 1)) {
            bin=int($col1*factor)-1
        } else {
            bin=int($col1*factor)
        }
        A1[$1][$4][$5][$6][$7][bin]++
    }
    if (col2 && !match($col2, /^$/)) {
        if (($col2 < 0) && (factor != 1)) {
            bin=int($col2*factor)-1
        } else {
            bin=int($col2*factor)
        }
        A2[$1][$4][$5][$6][$7][bin]++
    }
}
END {
    printf "dataset" OFS;
    printf "protocol" OFS;
    printf "msg" OFS;
    printf "qtype" OFS;
    printf "w_query" OFS; 
    printf "x" OFS;
    printf col1_name " hist [bin_size = " 1/factor "]";
    printf OFS;
    if (col2_name) {
        printf col2_name " hist [bin_size = " 1/factor "]";
    }
    printf "\n";
    min=999999999999
    max=-999999999999
    for (dataset in A1) {
        for (protocol in A1[dataset]) {
            for (msg in A1[dataset][protocol]) {
                for (qtype in A1[dataset][protocol][msg]) {
                    for (w_query in A1[dataset][protocol][msg][qtype]) {
                        for (bin in A1[dataset][protocol][msg][qtype][w_query]) {
                            if (int(bin) < min) {
                                min=int(bin);
                            }
                            if (int(bin) > max) {
                                max=int(bin);
                            }
                        }
                        if (typeof(A2[dataset][protocol][msg][qtype][w_query]) == "array") { 
                            for (bin in A2[dataset][protocol][msg][qtype][w_query]) {
                                if (int(bin) < min) {
                                    min=int(bin);
                                }
                                if (int(bin) > max) {
                                    max=int(bin);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    for (dataset in A1) {
        for (protocol in A1[dataset]) {
            for (msg in A1[dataset][protocol]) {
                for (qtype in A1[dataset][protocol][msg]) {
                    for (w_query in A1[dataset][protocol][msg][qtype]) {
                        for (bin=min; bin<=max; bin++) {
                            if (bin in A1[dataset][protocol][msg][qtype][w_query] || 
                                ((typeof(A2[dataset][protocol][msg][qtype][w_query]) == "array")) && bin in A2[dataset][protocol][msg][qtype][w_query]) {
                                print dataset, protocol, msg, qtype, w_query, bin/factor,
                                      A1[dataset][protocol][msg][qtype][w_query][bin],
                                      (typeof(A2[dataset][protocol][msg][qtype][w_query]) == "array") ? A2[dataset][protocol][msg][qtype][w_query][bin] : "";
                            }
                        }
                    }
                }
            }
        }
    }
}
