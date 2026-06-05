BEGIN {
    OFS=FS=","
    factor=10000
    start_col=9
}
NR == 1 {
    gsub(/[[:cntrl:][:space:]]+$/,"")
    for (c = start_col; c <= NF; c++) {
        names[c] = $c
    }
}
NR > 1 {
    gsub(/[[:cntrl:][:space:]]+$/,"")
    for (c = start_col; c <= NF; c++) {
        if (($c < 0) && (factor != 1)) {
            bin=int($c*factor)-1
        } else {
            bin=int($c*factor)
        }
        A[$1][$4][$5][$6][$7][$8][bin][c]++
    }
}
END {
    printf "dataset" OFS;
    printf "protocol" OFS;
    printf "msg" OFS;
    printf "qtype" OFS;
    printf "w_query" OFS; 
    printf "x" OFS;
    for (c = start_col; c < NF; c++) {
        printf names[c] OFS;
    }
    printf names[NF] "\n";
    for (dataset in A) {
        for (protocol in A[dataset]) {
            for (msg in A[dataset][protocol]) {
                for (qtype in A[dataset][protocol][msg]) {
                    for (w_query in A[dataset][protocol][msg][qtype]) {
                        for (i in A[dataset][protocol][msg][qtype][w_query]) {
                            for (bin in A[dataset][protocol][msg][qtype][w_query][i]) {
                                printf dataset OFS;
                                printf protocol OFS;
                                printf msg OFS;
                                printf qtype OFS;
                                printf w_query OFS;
                                printf (bin/factor)/i OFS;
                                for (c = start_col; c < NF; c++) {
                                    printf A[dataset][protocol][msg][qtype][w_query][i][bin][c] OFS; 
                                }
                                printf A[dataset][protocol][msg][qtype][w_query][i][bin][NF] "\n";
                            }
                        }
                    }
                }
            }
        }
    }
}
