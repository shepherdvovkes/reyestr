# Reyestr Admin Panel

Modern admin panel for Reyestr download system built with React, TypeScript, and Material-UI.

## Features

- **WebAuthn/FIDO2 Authentication** - Secure login with YubiKey or phone
- **Real-time Client Monitoring** - Monitor client activity, download speeds, and errors
- **Task Map Navigation** - Navigate tasks by region, instance type, and date range
- **Telegram Notifications** - Receive critical error notifications via Telegram
- **User Profile Management** - Edit profile settings including Telegram chat ID

## Setup

1. Install dependencies:
```bash
cd admin
npm install
```

2. Configure environment variables (create `.env` file):
```
VITE_API_URL=http://localhost:8000/api/v1
```

3. Start development server:
```bash
npm run dev
```

The admin panel will be available at `http://localhost:3000`

## Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Backend Requirements

The backend server must be running and configured with:
- WebAuthn endpoints (`/api/v1/auth/webauthn/*`)
- User management endpoints (`/api/v1/users/*`)
- Client activity endpoints (`/api/v1/clients/{id}/activity`)
- Task indexes endpoints (`/api/v1/tasks/indexes`)

See the main project README for backend setup instructions.
