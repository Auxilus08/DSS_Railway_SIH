# Railway Traffic Management System - Frontend

## Overview
A production-ready React dashboard for railway traffic controllers with real-time WebSocket updates, comprehensive authentication, and modern UI components.

## Tech Stack
- **Framework**: React 18.3.1 with TypeScript
- **Build Tool**: Vite 5.4.20
- **Styling**: Tailwind CSS 3.4.14
- **Routing**: React Router DOM 7.1.1
- **HTTP Client**: Axios 1.7.7
- **State Management**: Context API

## Features

### Authentication System
- JWT-based authentication with token storage
- Role-based access control (OPERATOR, MANAGER, ADMIN)
- Protected routes with role hierarchy
- Auto-logout on token expiration
- Login form with employee ID and password

### Real-time Updates
- WebSocket connection with auto-reconnection
- Live position updates for trains
- Real-time conflict alerts
- System status notifications
- Automatic notification management

### Dashboard Pages

#### 1. Dashboard (`/dashboard`)
- Real-time statistics overview
- Active trains, conflicts, sections count
- System response time metrics
- Recent conflicts list with severity indicators
- Train type distribution charts
- Performance metrics grid
- Auto-refresh every 30 seconds

#### 2. Trains (`/trains`)
- Comprehensive train list with filtering
- Search by train number
- Filter by type (EXPRESS, LOCAL, FREIGHT) and status
- Speed and load monitoring
- Priority indicators
- Real-time position updates
- Auto-refresh every 30 seconds

#### 3. Conflicts (`/conflicts`)
- Conflict management interface
- Severity-based filtering (CRITICAL, HIGH, MEDIUM, LOW)
- Status tracking (ACTIVE, ACKNOWLEDGED, RESOLVING, RESOLVED)
- Visual severity indicators with icons
- Conflict resolution tracking
- Detailed conflict information
- Auto-refresh every 15 seconds

#### 4. Sections (`/sections`)
- Section status monitoring
- Occupancy visualization with progress bars
- Filter by section type (TRACK, JUNCTION, STATION, YARD)
- Real-time capacity tracking
- Train presence indicators
- Section details (length, speed limits, electrification)
- Auto-refresh every 30 seconds

### UI/UX Features
- Dark/Light mode toggle with persistence
- Responsive design for all screen sizes
- Accessibility features (ARIA labels, keyboard navigation)
- Toast notifications for user feedback
- Loading states for all async operations
- Error handling with user-friendly messages
- Professional railway operations theme
- Real-time WebSocket connection status

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx                    # Main app with routing
│   ├── main.tsx                   # App entry point
│   ├── types/
│   │   └── index.ts               # TypeScript definitions
│   ├── services/
│   │   ├── api.ts                 # Axios HTTP client
│   │   └── websocket.ts           # WebSocket manager
│   ├── context/
│   │   ├── AuthContext.tsx        # Authentication state
│   │   ├── ThemeContext.tsx       # Theme management
│   │   └── NotificationContext.tsx # Notification system
│   ├── hooks/
│   │   ├── useWebSocket.ts        # WebSocket hook
│   │   └── useApi.ts              # API hooks with loading states
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx      # Login page
│   │   │   └── PrivateRoute.tsx   # Route protection
│   │   └── layout/
│   │       ├── Header.tsx         # App header with notifications
│   │       ├── Sidebar.tsx        # Navigation sidebar
│   │       ├── Footer.tsx         # App footer with status
│   │       └── DashboardLayout.tsx # Main layout wrapper
│   └── pages/
│       ├── Dashboard.tsx          # Main dashboard
│       ├── Trains.tsx             # Train management
│       ├── Conflicts.tsx          # Conflict management
│       └── Sections.tsx           # Section monitoring
├── index.html                     # HTML entry point
├── package.json                   # Dependencies
├── tailwind.config.js             # Tailwind configuration
├── tsconfig.json                  # TypeScript config
└── vite.config.ts                 # Vite configuration
```

## Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173/`

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## API Integration

The frontend connects to the backend API at:
- HTTP API: `http://localhost:8000/api`
- WebSocket: `ws://localhost:8000/ws`

### API Endpoints Used
- `POST /api/auth/login` - User authentication
- `GET /api/trains` - Get all trains
- `GET /api/sections/status` - Get section statuses
- `GET /api/conflicts` - Get conflicts
- `GET /api/performance/metrics` - Get performance metrics
- `WS /ws` - WebSocket connection for real-time updates

## User Roles

1. **OPERATOR**
   - View dashboard
   - Monitor trains and sections
   - View conflicts

2. **MANAGER**
   - All OPERATOR permissions
   - Manage conflicts
   - Access performance metrics

3. **ADMIN**
   - All MANAGER permissions
   - User management
   - System configuration

## WebSocket Messages

### Subscription
```json
{
  "type": "SUBSCRIBE_ALL",
  "data": {},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Position Update
```json
{
  "type": "POSITION_UPDATE",
  "data": {
    "train_id": 1,
    "section_id": 5,
    "coordinates": { "latitude": 12.34, "longitude": 56.78 },
    "speed_kmh": 80
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Conflict Alert
```json
{
  "type": "CONFLICT_ALERT",
  "data": {
    "id": 1,
    "severity": "CRITICAL",
    "description": "Potential collision detected"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Testing

### Login Credentials
Use the default admin credentials from the backend:
- Employee ID: `EMP001`
- Password: (as configured in backend)

### Testing Checklist
- [x] Authentication flow (login/logout)
- [x] Protected route access control
- [x] Real-time WebSocket connection
- [x] Dashboard statistics display
- [x] Train list with filtering
- [x] Conflict management interface
- [x] Section monitoring
- [x] Theme toggle (dark/light mode)
- [x] Notification system
- [x] Responsive design
- [ ] End-to-end integration with backend

## Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance Optimizations
- Lazy loading of routes (ready to implement)
- Memoization of expensive calculations
- Auto-refresh intervals with cleanup
- Efficient WebSocket message handling
- Optimized re-renders with React hooks

## Future Enhancements
1. Real-time train position visualization on map
2. Conflict resolution workflow
3. User management interface
4. Settings page for preferences
5. Export functionality for reports
6. Advanced filtering and sorting
7. Historical data analysis
8. Mobile app version
9. Offline mode support
10. Multi-language support

## Troubleshooting

### Build Errors
If you encounter rollup errors, try:
```bash
rm -rf node_modules package-lock.json
npm install
```

### WebSocket Connection Issues
- Ensure backend is running
- Check CORS configuration
- Verify WebSocket URL in environment variables

### Authentication Issues
- Clear localStorage: `localStorage.clear()`
- Check token expiration
- Verify backend authentication endpoint

## License
MIT

## Contributors
Railway Traffic Management System Team
