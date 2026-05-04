# Face Recognition Attendance System - Frontend

A modern, responsive web interface for the Face Recognition Attendance System.

## Features

- ✅ **Real-time Statistics Dashboard** - View present, absent, late, and total students
- ✅ **Student Registration** - Register new students with face images
- ✅ **Model Training** - Train the face recognition model
- ✅ **Video Recognition** - Upload videos to automatically mark attendance
- ✅ **Manual Attendance** - Manually update student attendance status
- ✅ **Live Attendance Table** - View and refresh today's attendance records
- ✅ **CSV Export** - Export attendance data to CSV files
- ✅ **Auto-refresh** - Attendance data refreshes every 30 seconds
- ✅ **Responsive Design** - Works on desktop, tablet, and mobile devices

## Technologies Used

- **HTML5** - Semantic markup
- **CSS3** - Modern styling with gradients and animations
- **JavaScript (ES6+)** - Async/await, Fetch API
- **Bootstrap 5.3** - Responsive grid and components
- **Font Awesome 6.4** - Icons

## Setup

### 1. Configure Backend URL

Edit `app.js` and update the API base URL if needed:

```javascript
const API_BASE_URL = 'http://localhost:5080';
```

### 2. Serve the Frontend

You can use any static file server. Here are some options:

**Option 1: Python HTTP Server**
```bash
cd frontend
python3 -m http.server 8080
```

**Option 2: Node.js HTTP Server**
```bash
npm install -g http-server
cd frontend
http-server -p 8080
```

**Option 3: VS Code Live Server**
- Install "Live Server" extension
- Right-click `index.html` → "Open with Live Server"

### 3. Access the Application

Open your browser and navigate to:
```
http://localhost:8080
```

## File Structure

```
frontend/
├── index.html      # Main HTML page
├── app.js          # JavaScript logic and API calls
├── styles.css      # Custom CSS styles
└── README.md       # This file
```

## Usage Guide

### 1. Register Students

1. Navigate to the "Register New Face" card
2. Enter student's full name
3. Enter student's roll number/ID
4. Upload a clear, front-facing photo
5. Click "Register Face"

**Tips:**
- Use well-lit photos
- Ensure face is clearly visible
- Avoid sunglasses or face coverings
- One face per photo

### 2. Train the Model

1. After adding students, click "Train Model"
2. Wait for confirmation message
3. Model is now ready for recognition

### 3. Mark Attendance via Video

1. Navigate to "Recognize & Mark Attendance" card
2. Upload a video containing students' faces
3. Click "Recognize Faces"
4. System will automatically mark attendance
5. View results in the attendance table

**Video Requirements:**
- Supported formats: MP4, AVI, MOV, MKV
- Keep videos short (10-30 seconds)
- Ensure good lighting
- Students should face the camera

### 4. Manual Attendance Update

1. Navigate to "Update Attendance Manually" card
2. Select a student from the dropdown
3. Choose status (Present/Absent/Late)
4. Click "Update Attendance"

### 5. View Attendance Records

- Today's attendance is displayed in the table
- Click "Refresh" to update the data
- Status is color-coded:
  - **Green** = Present
  - **Red** = Absent
  - **Orange** = Late

### 6. Export Data

- Click "Export CSV" to download attendance records
- File is saved on the backend server
- Contains all historical attendance data

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check server status |
| `/add_student` | POST | Register new student |
| `/train_model` | POST | Train recognition model |
| `/recognize` | POST | Recognize faces from video |
| `/attendance` | GET | Get today's attendance |
| `/students` | GET | Get all students |
| `/update_attendance` | POST | Update attendance manually |
| `/export_csv` | GET | Export to CSV |
| `/stats` | GET | Get statistics |

## Keyboard Shortcuts

- **Ctrl/Cmd + R** - Refresh attendance table

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Troubleshooting

### Cannot connect to backend

**Error:** "Cannot connect to backend server"

**Solution:**
1. Ensure backend server is running on `http://localhost:5080`
2. Check `API_BASE_URL` in `app.js`
3. Verify CORS is enabled on backend

### Images not uploading

**Error:** "No face detected in the image"

**Solution:**
1. Use clear, front-facing photos
2. Ensure good lighting
3. Check file format (PNG, JPG, JPEG)
4. Try a different photo

### Video recognition fails

**Error:** "No students registered in the system"

**Solution:**
1. Register students first
2. Train the model
3. Try again with video

### Attendance table not loading

**Solution:**
1. Check browser console for errors
2. Verify backend is running
3. Click "Refresh" button
4. Check network tab in DevTools

## Customization

### Change Color Scheme

Edit `styles.css` and modify CSS variables:

```css
:root {
    --primary-color: #0d6efd;
    --success-color: #198754;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
}
```

### Modify Auto-refresh Interval

Edit `app.js`:

```javascript
// Change 30000 (30 seconds) to desired interval in milliseconds
setInterval(async () => {
    await fetchAttendance();
    await fetchStats();
}, 30000);
```

### Add Custom Features

The code is modular and well-commented. You can easily:
- Add new API endpoints
- Create additional UI components
- Implement new features

## Performance Tips

1. **Optimize Images** - Compress photos before uploading
2. **Short Videos** - Keep recognition videos under 30 seconds
3. **Regular Training** - Retrain model after adding multiple students
4. **Browser Cache** - Clear cache if experiencing issues

## Security Considerations

⚠️ **Important:** This is a development setup. For production:

1. Use HTTPS for both frontend and backend
2. Implement authentication and authorization
3. Validate all user inputs
4. Add rate limiting
5. Secure file uploads
6. Use environment variables for configuration

## License

MIT License

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review browser console for errors
3. Verify backend logs
4. Check network requests in DevTools
