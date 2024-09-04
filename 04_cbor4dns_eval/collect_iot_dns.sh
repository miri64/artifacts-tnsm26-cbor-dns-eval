#!/usr/bin/env bash
#
# collect_dns_hex.sh
# Copyright (C) 2023 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROCS=$(grep -c '^processor' /proc/cpuinfo)
FIELDS='-e frame.number -e frame.protocols -e _ws.col.Source -e _ws.col.Destination
    -e dns.flags.response -e dns.qry.type -e dns.resp.type -e dns.retransmit_response_in -e dns.response_to
    -e udp.payload -e tcp.reassembled.data -e tcp.payload
    -e dns.qry.name -e dns.resp.name
    -e dns.afsdb.hostname -e dns.cname -e dns.dname -e dns.mr -e dns.ns
    -e dns.nsec.next_domain_name -e dns.ptr.domain_name -e dns.rrsig.signers_name
    -e dns.rt.intermediate_host -e dns.soa.mname -e dns.soa.rname -e dns.srv.name
    -e dns.svcb.targetname -e dns.winsr.name_result_domain
    -e dns.a -e dns.aaaa -e dns.apl.afdpart.ipv4 -e dns.apl.afdpart.ipv6 -e dns.ilnp.l32
    -e dns.ipseckey.gateway_ipv4 -e dns.ipseckey.gateway_ipv6 -e dns.svcb.svcparam.ipv4hint.ip
    -e dns.svcb.svcparam.ipv6hint.ip -e dns.wins.wins_server -e dns.wks.address
    -e dns.xpf.destination_ipv4 -e dns.xpf.destination_ipv6 -e dns.xpf.source_ipv4
    -e dns.xpf.source_ipv6'
INPUT_DATASETS="${SCRIPT_DIR}/input_datasets"
OUTPUT_DATASETS="${SCRIPT_DIR}/output_datasets"

mkdir -p "${OUTPUT_DATASETS}"

parse_pcaps() {
    pcap="${1}"
    dataset_pcap="$(echo "${pcap}" | sed "s#${INPUT_DATASETS}/##")"
    dataset=$(echo "${dataset_pcap}" | cut -d'/' -f1)
    tshark -Y "dns.count.queries == 1 && !vlan" -r "${pcap}" -Tfields ${FIELDS} \
        -E aggregator='|' -E separator=';' | \
        gawk -f ${SCRIPT_DIR}/collect_dns.awk | sed "s#^#${dataset};${dataset_pcap};#"
}

export -f parse_pcaps
export FIELDS
export INPUT_DATASETS
export SCRIPT_DIR

HEADER=$(
    echo "${FIELDS}" | tr -d '\n' |
        sed -E -e 's/-e\s+//' -e 's/\s+-e\s+/;/g' -e 's/;tcp[^;]+//g' -e 's/udp.payload/payload/g' | \
        xargs printf "dataset;pcap;%s;dns.query_payload;qr-diff;stored\n"
)
find ${INPUT_DATASETS}/{yourthings,iotfinder,moniotr}/ \
    -name "*.pcap" -o -name "eth1-*" -o -name "*.pcapng" -o -name "*.pcapng.gz" | \
    parallel --line-buffer -j"${PROCS}" --progress --eta parse_pcaps > "${OUTPUT_DATASETS}/dns_data_iot.csv"
sed -i "1i\
${HEADER}
" "${OUTPUT_DATASETS}/dns_data_iot.csv"
