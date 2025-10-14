/**
 * Railway Network Visualization Data Structures
 * Comprehensive TypeScript interfaces for the interactive dashboard
 */

// ==================== Core Network Entities ====================

export interface Position {
  latitude: number;
  longitude: number;
  x?: number; // SVG coordinate
  y?: number; // SVG coordinate
}

export interface Station {
  id: string;
  name: string;
  code: string;
  position: Position;
  type: 'TERMINAL' | 'JUNCTION' | 'INTERMEDIATE';
  platforms: number;
  capacity: number;
}

export interface Section {
  id: string;
  name: string;
  startStation: string;
  endStation: string;
  length: number; // in kilometers
  maxSpeed: number; // km/h
  status: SectionStatus;
  occupiedBy?: string[]; // train IDs
  coordinates: Position[];
  tracks: number;
  signalSystem: 'AUTOMATIC' | 'MANUAL' | 'SEMI_AUTOMATIC';
}

export type SectionStatus = 'CLEAR' | 'OCCUPIED' | 'CONFLICT' | 'MAINTENANCE' | 'BLOCKED';

export interface Junction {
  id: string;
  name: string;
  position: Position;
  connectedSections: string[];
  switchStates: SwitchState[];
  status: 'OPERATIONAL' | 'MAINTENANCE' | 'FAULT';
}

export interface SwitchState {
  id: string;
  position: 'STRAIGHT' | 'DIVERGING';
  locked: boolean;
}

// ==================== Train Data ====================

export interface Train {
  id: string;
  trainNumber: string;
  name: string;
  type: 'EXPRESS' | 'PASSENGER' | 'FREIGHT' | 'SUBURBAN';
  position: Position;
  currentSection: string;
  currentSpeed: number; // km/h
  maxSpeed: number;
  heading: number; // degrees, 0 = North
  status: TrainStatus;
  destination: string;
  origin: string;
  passengerCount?: number;
  priority: number; // 1-10, higher = more important
  scheduledRoute: string[]; // section IDs
  actualRoute: string[];
  delays: number; // minutes
  lastUpdate: Date;
  nextStation: string;
  eta: Date;
  distanceToNext: number; // km
}

export type TrainStatus = 'RUNNING' | 'STOPPED' | 'DELAYED' | 'EMERGENCY' | 'MAINTENANCE';

export interface TrainHistory {
  trainId: string;
  positions: TimestampedPosition[];
  speedProfile: SpeedReading[];
  events: TrainEvent[];
  delays: DelayRecord[];
}

export interface TimestampedPosition extends Position {
  timestamp: Date;
  section: string;
}

export interface SpeedReading {
  timestamp: Date;
  speed: number;
  acceleration: number;
}

export interface TrainEvent {
  id: string;
  trainId: string;
  type: 'DEPARTURE' | 'ARRIVAL' | 'STOP' | 'DELAY' | 'EMERGENCY' | 'CONFLICT';
  timestamp: Date;
  location: string;
  description: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
}

export interface DelayRecord {
  startTime: Date;
  endTime?: Date;
  duration: number; // minutes
  reason: string;
  location: string;
}

// ==================== Conflict Detection ====================

export interface Conflict {
  id: string;
  type: ConflictType;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  trains: string[]; // train IDs involved
  sections: string[]; // section IDs affected
  detectedAt: Date;
  estimatedImpact: Date;
  timeToImpact: number; // seconds
  description: string;
  status: ConflictStatus;
  aiRecommendation?: AIRecommendation;
  resolution?: ConflictResolution;
}

export type ConflictType = 
  | 'HEAD_ON'
  | 'REAR_END'
  | 'JUNCTION_COLLISION'
  | 'SPEED_VIOLATION'
  | 'ROUTE_OVERLAP'
  | 'SIGNAL_VIOLATION'
  | 'CAPACITY_EXCEEDED';

export type ConflictStatus = 
  | 'DETECTED'
  | 'ACKNOWLEDGED'
  | 'RESOLVING'
  | 'RESOLVED'
  | 'ESCALATED';

export interface ConflictResolution {
  id: string;
  conflictId: string;
  timestamp: Date;
  resolvedBy: string; // controller ID
  method: 'AI_RECOMMENDATION' | 'MANUAL' | 'AUTOMATIC';
  actions: ControllerAction[];
  effectiveness: number; // 0-1
}

// ==================== AI Recommendations ====================

export interface AIRecommendation {
  id: string;
  conflictId: string;
  timestamp: Date;
  type: RecommendationType;
  confidence: number; // 0-1
  priority: number; // 1-10
  actions: RecommendedAction[];
  alternativeRoutes?: AlternativeRoute[];
  estimatedResolutionTime: number; // seconds
  impactAnalysis: ImpactAnalysis;
  explanation: string;
  status: 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'MODIFIED';
}

export type RecommendationType = 
  | 'ROUTE_CHANGE'
  | 'SPEED_ADJUSTMENT'
  | 'STOP_TRAIN'
  | 'PRIORITY_CHANGE'
  | 'SECTION_CLEAR'
  | 'EMERGENCY_PROTOCOL';

export interface RecommendedAction {
  id: string;
  trainId: string;
  action: string;
  parameters: Record<string, any>;
  sequence: number;
  duration: number; // seconds
  mandatory: boolean;
}

export interface AlternativeRoute {
  id: string;
  sections: string[];
  distance: number; // km
  estimatedTime: number; // minutes
  delay: number; // minutes compared to original
  conflictFree: boolean;
  resourcesRequired: string[];
  coordinates: Position[];
}

export interface ImpactAnalysis {
  affectedTrains: string[];
  delayMinutes: Record<string, number>; // trainId -> delay
  passengerImpact: number;
  costEstimate: number;
  safetyScore: number; // 0-100
  efficiencyScore: number; // 0-100
}

// ==================== Controller Actions ====================

export interface ControllerAction {
  id: string;
  controllerId: string;
  timestamp: Date;
  type: ActionType;
  target: string; // train or section ID
  parameters: Record<string, any>;
  status: ActionStatus;
  result?: ActionResult;
  basedOnRecommendation?: string; // AI recommendation ID
}

export type ActionType =
  | 'SPEED_CHANGE'
  | 'ROUTE_CHANGE'
  | 'STOP_TRAIN'
  | 'CLEAR_SECTION'
  | 'EMERGENCY_STOP'
  | 'PRIORITY_OVERRIDE'
  | 'MANUAL_CONTROL';

export type ActionStatus = 
  | 'INITIATED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface ActionResult {
  success: boolean;
  timestamp: Date;
  message: string;
  impactedEntities: string[];
}

// ==================== System Status ====================

export interface SystemStatus {
  timestamp: Date;
  operational: boolean;
  trainCount: number;
  activeConflicts: number;
  sectionsStatus: Record<SectionStatus, number>;
  averageDelay: number; // minutes
  systemLoad: number; // 0-100
  performance: PerformanceMetrics;
  alerts: SystemAlert[];
}

export interface PerformanceMetrics {
  fps: number;
  latency: number; // ms
  updateFrequency: number; // Hz
  dataPoints: number;
  memoryUsage: number; // MB
}

export interface SystemAlert {
  id: string;
  type: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  message: string;
  timestamp: Date;
  acknowledged: boolean;
  source: string;
}

// ==================== WebSocket Messages ====================

export interface WSMessage {
  type: WSMessageType;
  payload: any;
  timestamp: Date;
}

export type WSMessageType =
  | 'TRAIN_UPDATE'
  | 'CONFLICT_DETECTED'
  | 'CONFLICT_RESOLVED'
  | 'SECTION_STATUS'
  | 'AI_RECOMMENDATION'
  | 'ACTION_RESULT'
  | 'SYSTEM_STATUS'
  | 'EMERGENCY';

export interface TrainUpdateMessage extends WSMessage {
  type: 'TRAIN_UPDATE';
  payload: {
    train: Train;
    previousPosition?: Position;
  };
}

export interface ConflictMessage extends WSMessage {
  type: 'CONFLICT_DETECTED' | 'CONFLICT_RESOLVED';
  payload: {
    conflict: Conflict;
  };
}

export interface SectionStatusMessage extends WSMessage {
  type: 'SECTION_STATUS';
  payload: {
    section: Section;
  };
}

export interface AIRecommendationMessage extends WSMessage {
  type: 'AI_RECOMMENDATION';
  payload: {
    recommendation: AIRecommendation;
  };
}

// ==================== Network Graph Data ====================

export interface NetworkGraph {
  stations: Station[];
  sections: Section[];
  junctions: Junction[];
  trains: Train[];
  bounds: GeoBounds;
}

export interface GeoBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

// ==================== Interaction Events ====================

export interface InteractionEvent {
  type: 'CLICK' | 'HOVER' | 'DRAG' | 'ZOOM' | 'PAN';
  target: InteractionTarget;
  position: Position;
  timestamp: Date;
}

export interface InteractionTarget {
  type: 'TRAIN' | 'SECTION' | 'STATION' | 'JUNCTION' | 'CONFLICT';
  id: string;
  data: any;
}

// ==================== Visualization Config ====================

export interface VisualizationConfig {
  width: number;
  height: number;
  zoom: {
    min: number;
    max: number;
    initial: number;
  };
  animation: {
    duration: number; // ms
    enabled: boolean;
    fps: number;
  };
  colors: {
    sections: Record<SectionStatus, string>;
    trains: Record<TrainStatus, string>;
    conflicts: Record<Conflict['severity'], string>;
    recommendations: string;
  };
  layers: {
    network: boolean;
    trains: boolean;
    conflicts: boolean;
    recommendations: boolean;
    labels: boolean;
  };
}

// ==================== Component Props ====================

export interface NetworkMapProps {
  network: NetworkGraph;
  config: VisualizationConfig;
  onTrainClick?: (train: Train) => void;
  onSectionClick?: (section: Section) => void;
  onStationClick?: (station: Station) => void;
  selectedTrain?: string;
  selectedSection?: string;
}

export interface ConflictPanelProps {
  conflicts: Conflict[];
  onConflictSelect?: (conflict: Conflict) => void;
  onAcceptRecommendation?: (recommendationId: string) => void;
  onRejectRecommendation?: (recommendationId: string) => void;
  selectedConflict?: string;
}

export interface TrainDetailsModalProps {
  train: Train | null;
  history?: TrainHistory;
  onClose: () => void;
  onControlAction?: (action: ControllerAction) => void;
}

export interface ControlPanelProps {
  systemStatus: SystemStatus;
  onEmergencyStop: () => void;
  onTestScenario: (scenario: Scenario) => void;
  onCommunication: (message: CommunicationMessage) => void;
}

// ==================== Control Room Features ====================

export interface Scenario {
  id: string;
  name: string;
  description: string;
  type: 'CONFLICT' | 'EMERGENCY' | 'CAPACITY_TEST' | 'CUSTOM';
  parameters: Record<string, any>;
}

export interface CommunicationMessage {
  id: string;
  from: string;
  to: string;
  channel: 'VOICE' | 'TEXT' | 'EMERGENCY';
  content: string;
  timestamp: Date;
  priority: 'NORMAL' | 'HIGH' | 'URGENT';
}

// ==================== Animation Data ====================

export interface AnimationFrame {
  timestamp: number;
  positions: Record<string, Position>; // trainId -> position
  interpolation: number; // 0-1
}

export interface TransitionState<T> {
  from: T;
  to: T;
  progress: number; // 0-1
  duration: number; // ms
  startTime: number;
}
