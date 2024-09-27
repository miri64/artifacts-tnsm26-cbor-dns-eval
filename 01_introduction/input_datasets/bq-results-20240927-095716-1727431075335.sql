SELECT
  resp_content_encoding, mimeType, COUNT(0) AS count
FROM
  httparchive.summary_requests.2024_09_01_desktop
GROUP BY
  resp_content_encoding,
  mimeType
