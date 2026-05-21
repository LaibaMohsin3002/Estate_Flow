import { MaintenanceRequest } from '../types';

/** True when a manager must approve / sign before dispatch completes. */
export function needsManagerApproval(row: MaintenanceRequest): boolean {
  if (row.status === 'Pending Approval') return true;

  const pl = row.maintenance_pipeline_results;
  if (!pl) return false;

  if (pl.report_pending_signature && !pl.report_signed) return true;

  const logs = pl.agents_run ?? [];
  const agentNames = logs.map((a) => a.agent_name);
  if (
    agentNames.includes('report_agent') &&
    !agentNames.includes('performance_agent')
  ) {
    return true;
  }

  if (
    (pl.urgency === 'Critical' || pl.urgency === 'High') &&
    !pl.human_approved
  ) {
    return true;
  }

  return false;
}
