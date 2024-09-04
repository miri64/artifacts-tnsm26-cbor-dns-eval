BEGIN {
    FS=OFS=";"
    queries[0] = ""
    responses[0] = ""
}
{
    if (!$10 && !$11) {
        # use tcp.payload as payload (without leading length)
        $10 = substr($12,5)
    }
    else if (!$10) {
        # use tcp.reassembled.data as payload (without leading length)
        $10 = substr($11, 5)
    }
    # else use udp.payload as length
    # move the rest two columns to the left
    for (i = 11; i < (NF - 2); i++) {
        $i = $(i + 2)
    }
    # and remove the two tcp.payload/tcp.reassembled.data column
    NF -= 2
    # find dns.query_payloads:
    $(NF + 1) = ""
    $(NF + 1) = ""
	if ($5 == "True" || $5 == 1) { # is response
        if ($8) {  # dns.retransmit_response_in has a value
            if (responses[$8] && queries[responses[$8]]) {
                $(NF - 1) = queries[responses[$8]]
            }
            $NF = ($1 - $8) "|" ($1 - responses[$8])
        }
        if ($9) { # dns.response_to has a value
            # store dns.response_to under frame.number
            responses[$1] = $9
            if (queries[$9]) {
                $(NF - 1) = queries[$9]
            }
            $NF = $1 - $9
        }
        # Remove older responses to safe memory
        while (length(responses) > 500000) {
            min = 0;
            for (key in responses) {  # could use length here, but we need to search a minimum
                if (!min || (key < min)) {
                    min = key;
                }
            }
            delete responses[min];
        }
        $(NF + 1) = length(responses)
    }
    else { # is query
        # store query payload under frame.number
        queries[$1] = $10

        # Remove older queries to safe memory
        while (length(queries) > 500000) {
            min = 0;
            for (key in queries) {  # could use length here, but we need to search a minimum
                if (!min || (key < min)) {
                    min = key;
                }
            }
            delete queries[min];
        }
        $(NF + 1) = length(queries)
    }
    # add column for dns.query_payload
    print $0
}
