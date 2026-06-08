SELECT
  resp_content_type, url
FROM `httparchive.summary_requests.2024_09_01_desktop`
WHERE 
  LOWER(resp_content_type) LIKE "%json%" OR
  LOWER(resp_content_type) LIKE "%text/html%" OR
  LOWER(resp_content_type) LIKE "%text/css%"
LIMIT 1000000;
