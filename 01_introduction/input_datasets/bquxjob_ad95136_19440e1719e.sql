SELECT 
t1.table_name as table_suffix,
total_requests,
total_json_requests,
total_json_requests/total_requests as percent_json_requests,
FROM (SELECT
  _TABLE_SUFFIX as table_name,
  SUM(respSize) total_json_requests,
FROM
  `httparchive.summary_requests.2024*`
WHERE
  LOWER(mimeType) LIKE "%json%" AND _TABLE_SUFFIX LIKE '%01_desktop' AND _TABLE_SUFFIX BETWEEN '_00' AND '_10'
GROUP BY table_name
) t1 
JOIN (SELECT
  _TABLE_SUFFIX as table_name,
  SUM(respSize) total_requests,
FROM
  `httparchive.summary_requests.2024*`
WHERE
  _TABLE_SUFFIX LIKE '%01_desktop' AND _TABLE_SUFFIX BETWEEN '_00' AND '_10'
GROUP BY table_name
) t2 ON t1.table_name = t2.table_name
ORDER BY table_suffix