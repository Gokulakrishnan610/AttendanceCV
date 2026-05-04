# Face Recognition Attendance System - Backend

A Flask-based REST API for managing student attendance using face recognition technology with SQLite database.

## Features

- ✅ Student registration with face encoding
- ✅ Face recognition from video uploads
- ✅ Automatic attendance marking
- ✅ Manual attendance updates
- ✅ CSV export functionality
- ✅ Real-time attendance statistics
- ✅ SQLite database for data persistence

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- CMake (required for dlib installation)

### Installing CMake

**macOS:**
```bash
brew install cmake
```

**Linux:**
```bash
sudo apt-get install cmake
```

**Windows:**
Download from https://cmake.org/download/

## Installation

1. **Create a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python app.py
```

The server will start on `http://localhost:5080`

## API Endpoints

### Health Check
- **GET** `/health` - Check server status

### Student Management
- **POST** `/add_student` - Register new student with face image
  - Form data: `name`, `student_id`, `image` (file)
  
- **GET** `/students` - Get all registered students

### Face Recognition
- **POST** `/train_model` - Train/reload face recognition model

- **POST** `/recognize` - Upload video to recognize faces and mark attendance
  - Form data: `video` (file)

### Attendance Management
- **GET** `/attendance` - Get today's attendance records

- **POST** `/update_attendance` - Manually update attendance
  - JSON body: `{"student_id": "...", "status": "Present|Absent|Late"}`

- **GET** `/export_csv` - Export attendance to CSV file

- **GET** `/stats` - Get attendance statistics

## Database Schema

### Students Table
```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    student_id TEXT NOT NULL UNIQUE,
    face_encoding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Attendance Table
```sql
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    date DATE NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    UNIQUE(student_id, date)
)
```

## Directory Structure

```
backend/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── attendance.db      # SQLite database (created automatically)
├── uploads/           # Temporary upload folder (created automatically)
└── exports/           # CSV export folder (created automatically)
```

## Configuration

Edit the following constants in `app.py` if needed:

```python
UPLOAD_FOLDER = 'uploads'
EXPORT_FOLDER = 'exports'
DATABASE = 'attendance.db'
```

## Troubleshooting

### dlib installation fails
If dlib installation fails, try:
```bash
pip install dlib --no-cache-dir
```

Or install from conda:
```bash
conda install -c conda-forge dlib
```

### Face recognition is slow
- Reduce `max_frames` in the recognize endpoint
- Use smaller video files
- Ensure you're processing every 5th frame (already optimized)

### CORS errors
The backend has CORS enabled for all origins. If you still face issues, check your frontend URL configuration.

## Production Deployment

For production, consider:
1. Use a production WSGI server (gunicorn, uWSGI)
2. Set `debug=False` in app.run()
3. Use environment variables for configuration
4. Implement proper authentication
5. Add rate limiting
6. Use a more robust database (PostgreSQL, MySQL)

## License

MIT License
