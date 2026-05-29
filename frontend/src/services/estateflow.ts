import { api } from '../lib/api';
import {
  agentLogsFromResponse,
  mapInspection,
  mapMaintenanceRequest,
  mapPredictive,
  mapProperty,
  mapVendor,
  normalizePipeline,
  unwrapData,
} from '../lib/mappers';
import {
  AgentLog,
  AppNotification,
  ChatResponse,
  Inspection,
  MaintenanceRequest,
  PipelineResult,
  PredictiveMaintenance,
  Property,
  UserProfile,
  Vendor,
  VendorReview,
} from '../types';

function asString(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function normalizeSpecialties(value: unknown): string[] | undefined {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return undefined;
}

export async function fetchProfile(): Promise<UserProfile> {
  const row = unwrapData<Record<string, unknown>>(await api.get('/api/profile/me'));
  return {
    id: String(row.id),
    email: asString(row.email ?? ''),
    role: row.role as UserProfile['role'],
    full_name: row.full_name as string | undefined,
    phone: row.phone as string | undefined,
    whatsapp_phone: row.whatsapp_phone as string | undefined,
    area: row.area as string | undefined,
    city: row.city as string | undefined,
    latitude: typeof row.latitude === 'number' ? row.latitude : undefined,
    longitude: typeof row.longitude === 'number' ? row.longitude : undefined,
    specialties: normalizeSpecialties(row.specialties ?? row.specialty),
  };
}

export async function updateProfile(body: {
  full_name?: string;
  phone?: string;
  whatsapp_phone?: string;
  area?: string;
  city?: string;
  latitude?: number;
  longitude?: number;
  specialties?: string[];
}): Promise<UserProfile> {
  const row = unwrapData<Record<string, unknown>>(await api.put('/api/profile/me', body));
  return {
    id: String(row.id),
    email: asString(row.email ?? ''),
    role: row.role as UserProfile['role'],
    full_name: row.full_name as string | undefined,
    phone: row.phone as string | undefined,
    whatsapp_phone: row.whatsapp_phone as string | undefined,
    area: row.area as string | undefined,
    city: row.city as string | undefined,
    latitude: typeof row.latitude === 'number' ? row.latitude : undefined,
    longitude: typeof row.longitude === 'number' ? row.longitude : undefined,
    specialties: normalizeSpecialties(row.specialties ?? row.specialty),
  };
}

export async function fetchMaintenanceRequests(): Promise<MaintenanceRequest[]> {
  const rows = unwrapData<Record<string, unknown>[]>(await api.get('/api/maintenance'));
  return (rows ?? []).map(mapMaintenanceRequest);
}

export async function fetchMaintenanceRequest(id: string): Promise<MaintenanceRequest> {
  const row = unwrapData<Record<string, unknown>>(await api.get(`/api/maintenance/${id}`));
  return mapMaintenanceRequest(row);
}

export async function fetchPendingApprovals(): Promise<MaintenanceRequest[]> {
  const rows = unwrapData<Record<string, unknown>[]>(
    await api.get('/api/maintenance/pending-approvals')
  );
  return (rows ?? []).map(mapMaintenanceRequest);
}

export async function approveMaintenanceRequest(id: string): Promise<void> {
  await api.post(`/api/maintenance/${id}/approve`, { approved: true });
}

export async function resolveMaintenanceRequest(id: string): Promise<void> {
  await api.post(`/api/maintenance/${id}/resolve`);
}

export async function submitFeedback(
  id: string,
  body: { confirmed_resolved: boolean; comment?: string }
): Promise<void> {
  await api.post(`/api/maintenance/${id}/feedback`, body);
}

export async function fetchPipelineLive(id: string): Promise<{
  request: MaintenanceRequest;
  pipeline: PipelineResult | undefined;
  agentLogs: AgentLog[];
}> {
  const [reqRow, pipeRes] = await Promise.all([
    unwrapData<Record<string, unknown>>(api.get(`/api/maintenance/${id}`)),
    api.get<{ pipeline: Record<string, unknown> | null; agent_logs: unknown[] }>(
      `/api/maintenance/${id}/pipeline`
    ),
  ]);

  const agentLogs = agentLogsFromResponse(pipeRes.agent_logs);
  const pipeline = normalizePipeline(pipeRes.pipeline ?? undefined, agentLogs);
  const request = mapMaintenanceRequest(reqRow);
  if (pipeline) request.maintenance_pipeline_results = pipeline;

  return { request, pipeline, agentLogs };
}

export async function submitMaintenanceJson(body: {
  property_id: string;
  property_name: string;
  unit: string;
  original_issue: string;
  latitude?: number;
  longitude?: number;
}): Promise<string> {
  const res = await api.post<{ data: { id: string }; request_id: string }>(
    '/api/maintenance',
    body
  );
  const payload = res as { data?: { id: string }; request_id?: string };
  return payload.data?.id ?? payload.request_id ?? '';
}

export async function submitMaintenanceWithMedia(form: FormData): Promise<string> {
  const res = await api.postForm<{ data: { id: string }; request_id: string }>(
    '/api/maintenance/submit-with-media',
    form
  );
  const payload = res as { data?: { id: string }; request_id?: string };
  return payload.data?.id ?? payload.request_id ?? '';
}

export async function fetchProperties(): Promise<Property[]> {
  const rows = unwrapData<Record<string, unknown>[]>(await api.get('/api/properties'));
  return (rows ?? []).map(mapProperty);
}

export async function createProperty(body: {
  name: string;
  city: string;
  address: string;
  unit_numbers: string[];
  latitude?: number;
  longitude?: number;
}): Promise<void> {
  await api.post('/api/properties', body);
}

export async function fetchVendors(): Promise<Vendor[]> {
  const rows = unwrapData<Record<string, unknown>[]>(await api.get('/api/vendors'));
  return (rows ?? []).map(mapVendor);
}

export async function rateVendor(
  vendorId: string,
  body: { rating: number; comment?: string; request_id?: string }
): Promise<void> {
  await api.post(`/api/vendors/${vendorId}/rate`, body);
}

export async function fetchInspections(): Promise<Inspection[]> {
  const rows = unwrapData<Record<string, unknown>[]>(await api.get('/api/inspections'));
  return (rows ?? []).map(mapInspection);
}

export async function createInspection(body: {
  property_id: string;
  property_name: string;
  inspection_type: string;
  items: { item_name: string; result: string; note?: string }[];
  notes?: Record<string, unknown>;
}): Promise<void> {
  await api.post('/api/inspections', body);
}

export async function fetchPredictiveMaintenance(): Promise<PredictiveMaintenance[]> {
  const rows = unwrapData<Record<string, unknown>[]>(
    await api.get('/api/predictive-maintenance')
  );
  return (rows ?? []).map(mapPredictive);
}

export async function runPredictiveMaintenance(): Promise<void> {
  await api.post('/api/predictive-maintenance/run');
}

export async function chatManager(body: {
  message: string;
  property_id?: string;
  history?: { role: 'user' | 'assistant'; content: string }[];
}): Promise<ChatResponse> {
  return unwrapData<ChatResponse>(await api.post('/api/knowledge/chat/manager', body));
}

export async function chatTenant(body: {
  message: string;
  history?: { role: 'user' | 'assistant'; content: string }[];
}): Promise<ChatResponse> {
  return unwrapData<ChatResponse>(await api.post('/api/knowledge/chat/tenant', body));
}

// ─── Notifications ────────────────────────────────────────────────────────────

export async function fetchNotifications(): Promise<{
  notifications: AppNotification[];
  unread_count: number;
}> {
  const res = await api.get<{ data: AppNotification[]; unread_count: number }>(
    '/api/notifications'
  );
  return { notifications: res.data ?? [], unread_count: res.unread_count ?? 0 };
}

export async function markNotificationRead(id: string): Promise<void> {
  await api.patch(`/api/notifications/${id}/read`, {});
}

export async function markAllNotificationsRead(): Promise<void> {
  await api.patch('/api/notifications/read-all', {});
}

export async function vendorReply(requestId: string): Promise<void> {
  await api.post(`/api/vendors/requests/${requestId}/vendor-reply`, {});
}

export async function fetchCalendarStatus(): Promise<{
  connected: boolean;
  provider: string;
  calendar_id: string;
  connected_at?: string;
}> {
  const row = unwrapData<Record<string, unknown>>(await api.get('/api/calendar/status'));
  return {
    connected: Boolean(row.connected),
    provider: String(row.provider ?? 'google'),
    calendar_id: String(row.calendar_id ?? 'primary'),
    connected_at: typeof row.connected_at === 'string' ? row.connected_at : undefined,
  };
}

export async function getCalendarConnectUrl(): Promise<{ auth_url: string }> {
  const row = unwrapData<Record<string, unknown>>(await api.get('/api/calendar/connect-url'));
  return { auth_url: String(row.auth_url ?? '') };
}

export async function completeCalendarConnect(code: string): Promise<void> {
  await api.post('/api/calendar/connect', { code, calendar_id: 'primary' });
}

export async function fetchVendorActiveJobs(): Promise<{
  id: string;
  ticket_id: string;
  original_issue: string;
  status: string;
  vendor_replied: boolean;
  created_at: string;
}[]> {
  const res = await api.get<{ data: unknown[] }>('/api/vendors/my-active-jobs');
  return (res.data ?? []) as {
    id: string;
    ticket_id: string;
    original_issue: string;
    status: string;
    vendor_replied: boolean;
    created_at: string;
  }[];
}

export async function fetchVendorReviews(): Promise<VendorReview[]> {
  const rows = unwrapData<Record<string, unknown>[]>(await api.get('/api/vendors/my-reviews'));
  return (rows ?? []).map((row) => ({
    id: String(row.id),
    request_id: String(row.request_id),
    ticket_id: row.ticket_id as string | undefined,
    property_name: row.property_name as string | undefined,
    unit: row.unit as string | undefined,
    rating: Number(row.rating ?? 0),
    comment: row.comment as string | undefined,
    created_at: String(row.created_at ?? ''),
  }));
}

