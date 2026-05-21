-- Optional status for blocked requests
ALTER TABLE maintenance_requests DROP CONSTRAINT IF EXISTS maintenance_requests_status_check;
ALTER TABLE maintenance_requests ADD CONSTRAINT maintenance_requests_status_check
  CHECK (status IN ('Open', 'In Progress', 'Scheduled', 'Resolved', 'Pending Approval', 'Blocked'));
