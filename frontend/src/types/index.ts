// Type definitions for Railway Traffic Management System

export interface User {
  id: number;
  name: string;
  employee_id: string;
  auth_level: 'OPERATOR' | 'MANAGER' | 'ADMIN';
  section_responsibility: number[];
  active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  controller: User;
}

export interface LoginCredentials {
  employee_id: string;
  password: string;
}

export interface Train {
  id: number;
  train_number: string;
  type: 'EXPRESS' | 'LOCAL' | 'FREIGHT' | 'MAINTENANCE';
  max_speed_kmh: number;
  capacity: number;
  priority: number;
  length_meters: number;
  weight_tons: number;
  current_section_id?: number;
  speed_kmh: number;
  current_load: number;
  operational_status: 'ACTIVE' | 'MAINTENANCE' | 'OUT_OF_SERVICE' | 'EMERGENCY';
  created_at: string;
  updated_at: string;
}

export interface Section {
  id: number;
  name: string;
  section_code: string;
  section_type: 'TRACK' | 'JUNCTION' | 'STATION' | 'YARD';
  length_meters: number;
  max_speed_kmh: number;
  capacity: number;
  electrified: boolean;
  signaling_system?: string;
  active: boolean;
  created_at: string;
}

export interface SectionStatus {
  section: Section;
  current_occupancy: number;
  utilization_percentage: number;
  trains_present: Train[];
  status: 'AVAILABLE' | 'BUSY' | 'FULL' | 'MAINTENANCE';
}

export interface Position {
  train_id: number;
  section_id: number;
  section_code: string;
  section_name: string;
  coordinates: {
    latitude: number;
    longitude: number;
    altitude?: number;
  };
  speed_kmh: number;
  heading: number;
  timestamp: string;
  distance_from_start?: number;
  signal_strength?: number;
  gps_accuracy?: number;
}

export interface Conflict {
  id: number;
  conflict_type: 'SPATIAL_COLLISION' | 'TEMPORAL_CONFLICT' | 'PRIORITY_CONFLICT' | 'JUNCTION_CONFLICT';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVING' | 'RESOLVED';
  trains_involved: number[];
  sections_involved: number[];
  section_id?: number;
  detected_at: string;
  detection_time: string;
  resolved_at?: string;
  resolution_time?: number;
  description: string;
  auto_resolved: boolean;
}

export interface WebSocketMessage {
  type: 'POSITION_UPDATE' | 'CONFLICT_ALERT' | 'SYSTEM_STATUS' | 'NOTIFICATION' | 'SUBSCRIBE_ALL' | 'UNSUBSCRIBE';
  data: any;
  timestamp: string;
}

export interface Notification {
  id: string;
  type: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface ApiError {
  success: boolean;
  error: string;
  details?: any;
  timestamp: string;
}

export interface PerformanceMetrics {
  total_trains: number;
  active_trains: number;
  position_updates_per_minute: number;
  average_response_time_ms: number;
  active_websocket_connections: number;
  cache_hit_rate: number;
  database_connections: number;
}
