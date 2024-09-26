/* Based on https://discuss.httparchive.org/t/median-of-application-json-or-xml-requests-within-a-page/1643/2 */
SELECT 
t1.table_name as table_suffix,
total_requests,
total_json_requests,
total_json_requests/total_requests as percent_json_requests,
FROM (SELECT
  _TABLE_SUFFIX as table_name,
  COUNT(0) total_json_requests,
FROM
  `httparchive.summary_requests.20*`
WHERE
  LOWER(mimeType) LIKE "%json%" AND _TABLE_SUFFIX LIKE '%01_desktop' AND _TABLE_SUFFIX BETWEEN '18_00' AND '24_13'
GROUP BY table_name
) t1 
JOIN (SELECT
  _TABLE_SUFFIX as table_name,
  COUNT(0) total_requests,
FROM
  `httparchive.summary_requests.20*`
WHERE
  _TABLE_SUFFIX LIKE '%01_desktop' AND _TABLE_SUFFIX BETWEEN '18_00' AND '24_13'
GROUP BY table_name
) t2 ON t1.table_name = t2.table_name
ORDER BY table_suffix
