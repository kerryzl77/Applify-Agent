# Applify - Job Application Assistant

A modern React application for generating tailored job application materials using AI, including cover letters, emails, and resume optimization.

## Features

- **Modern UI/UX**: Clean, minimal interface inspired by Perplexity, ChatGPT, and Claude
- **Dark Mode**: Fully supports dark mode with smooth transitions
- **Content Generation**: AI-powered generation of:
  - Cover letters tailored to job descriptions
  - Professional emails
  - Resume optimization for specific roles
- **Resume Upload**: Drag-and-drop resume upload with progress tracking
- **Chat Interface**: Conversational UI for iterative content improvement
- **Profile Management**: Store and manage your professional profile
- **State Management**: Persistent state using Zustand
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile

## Tech Stack

- **React 19** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Zustand** - State management
- **React Router** - Navigation
- **Axios** - API client
- **React Hot Toast** - Notifications
- **React Markdown** - Markdown rendering
- **Lucide React** - Icons

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Flask backend running (see backend setup)

### Installation

1. Clone the repository and navigate to the client directory:
```bash
cd job-application-llm/client
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Update the `.env` file with your backend API URL:
```
VITE_API_BASE_URL=http://localhost:5000
```

### Development

Run the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
client/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── Sidebar.jsx      # Navigation sidebar
│   │   ├── ContentGenerator.jsx  # Main chat interface
│   │   ├── ProfileModal.jsx # Profile editing modal
│   │   ├── ResumeUploader.jsx  # Resume upload component
│   │   ├── LoadingSpinner.jsx  # Loading animations
│   │   └── Toast.jsx        # Toast notifications
│   ├── pages/               # Page components
│   │   ├── Login.jsx        # Login page
│   │   ├── Register.jsx     # Registration page
│   │   └── Dashboard.jsx    # Main dashboard
│   ├── services/            # API services
│   │   └── api.js           # API client and endpoints
│   ├── store/               # State management
│   │   └── useStore.js      # Zustand store
│   ├── utils/               # Utility functions
│   │   └── helpers.js       # Helper functions
│   ├── App.jsx              # Main app component
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── .env.example             # Environment variables template
├── package.json             # Dependencies
└── README.md                # This file
```

## API Integration

The application integrates with a Flask backend API. The following endpoints are used:

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/profile` - Get user profile
- `PUT /auth/profile` - Update user profile

### Resume Management
- `POST /resume/upload` - Upload resume
- `GET /resume` - Get uploaded resume
- `DELETE /resume` - Delete resume

### Content Generation
- `POST /generate/cover-letter` - Generate cover letter
- `POST /generate/email` - Generate email
- `POST /generate/resume` - Tailor resume
- `POST /generate/improve` - Improve content

### Profile Management
- `GET /profile` - Get profile data
- `PUT /profile` - Update profile data
- `DELETE /profile` - Delete profile

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:5000` |
| `VITE_ENABLE_ANALYTICS` | Enable analytics | `false` |
| `VITE_ENABLE_DEBUG` | Enable debug mode | `true` |

## Features in Detail

### State Management (Zustand)

The application uses Zustand for state management with the following stores:

- **Authentication**: User login state, token management
- **Theme**: Dark/light mode toggle
- **Conversations**: Chat history and current conversation
- **Profile**: User profile data
- **Resume**: Uploaded resume state

### Protected Routes

The application implements route protection:
- Public routes: `/login`, `/register`
- Protected routes: `/dashboard`
- Auto-redirect based on authentication status

### Toast Notifications

Uses `react-hot-toast` for user feedback:
- Success messages (green)
- Error messages (red)
- Loading states (blue)
- Custom styling for dark mode

### Dark Mode

Dark mode implementation:
- Persistent theme storage
- Smooth transitions
- System preference detection (optional)
- Manual toggle in sidebar

## Styling

The application uses Tailwind CSS with custom configurations:

### Custom Classes
- `.card` - Card container
- `.btn` - Button base
- `.btn-primary` - Primary button
- `.btn-secondary` - Secondary button
- `.btn-outline` - Outline button
- `.input` - Input field
- `.textarea` - Textarea field
- `.badge` - Badge component
- `.glass` - Glassmorphism effect

### Custom Scrollbar
- Styled scrollbar for better UX
- Dark mode support
- Smooth scrolling

## Development Guidelines

### Adding New Components

1. Create component in `src/components/`
2. Use Framer Motion for animations
3. Support dark mode with Tailwind dark: variant
4. Add proper prop validation
5. Export component

### Adding New Pages

1. Create page in `src/pages/`
2. Add route in `App.jsx`
3. Implement protected/public route logic
4. Add to navigation if needed

### API Integration

1. Add endpoint to `src/services/api.js`
2. Use try-catch for error handling
3. Show loading states
4. Display toast notifications
5. Update store state

### State Management

1. Add state to `src/store/useStore.js`
2. Create actions for state updates
3. Persist important state
4. Keep state normalized

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check if backend is running
   - Verify `VITE_API_BASE_URL` in `.env`
   - Check CORS settings on backend

2. **Dark Mode Not Working**
   - Clear browser cache
   - Check localStorage
   - Verify Tailwind dark mode config

3. **Authentication Issues**
   - Clear localStorage
   - Check token expiration
   - Verify backend auth endpoints

4. **Build Errors**
   - Delete `node_modules` and reinstall
   - Clear Vite cache: `rm -rf .vite`
   - Check for missing dependencies

## Performance Optimization

- Lazy loading of components
- Code splitting with React Router
- Optimized re-renders with Zustand
- Debounced API calls
- Image optimization
- CSS purging in production

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.
