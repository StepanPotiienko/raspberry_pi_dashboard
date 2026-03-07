# Raspberry Pi Dashboard

A modern, real-time system monitoring dashboard for Raspberry Pi built with Django.

## Features

- 📊 **Real-time Monitoring**: Live updates every 5 seconds
- 💻 **CPU Metrics**: Overall usage, per-core usage, temperature, and frequency
- 🧠 **Memory Monitoring**: RAM and Swap usage with visual indicators
- 💾 **Disk Usage**: Real-time disk space monitoring
- 🌐 **Network Statistics**: Bytes sent/received tracking
- 🌀 **Fan Speed**: Monitor cooling system (if available)
- 📈 **Historical Charts**: Interactive charts showing system trends
- ⚡ **Top Processes**: View resource-intensive processes
- 🎨 **Modern UI**: Clean, responsive design inspired by modern dashboards

## Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Run migrations**:

```bash
python manage.py makemigrations
python manage.py migrate
```

4. **Create a superuser** (optional, for admin access):

```bash
python manage.py createsuperuser
```

5. **Run the development server**:

```bash
python manage.py runserver 0.0.0.0:8000
```

6. **Access the dashboard**:

- Dashboard: http://your-pi-ip:8000/
- Admin panel: http://your-pi-ip:8000/admin/

## API Endpoints

- `/api/stats/` - Get current system statistics (JSON)
- `/api/processes/` - Get top processes (JSON)
- `/api/historical/?hours=1` - Get historical metrics (JSON)

## System Requirements

- Python 3.8+
- Django 6.0+
- psutil library
- Works on any Linux system, optimized for Raspberry Pi

## Features Breakdown

### Dashboard Cards

- **CPU Usage**: Real-time CPU percentage with progress bar
- **CPU Temperature**: Temperature monitoring with color-coded warnings
- **Memory (RAM)**: Current usage with total/used display
- **Swap Memory**: Swap space utilization
- **Disk Usage**: Storage capacity monitoring
- **Network**: Upload/download statistics
- **Fan Speed**: Cooling system RPM (if sensors available)
- **System Info**: OS, kernel, and architecture details

### Charts

- **CPU & Memory History**: Line chart showing trends over time
- **CPU Per Core**: Bar chart displaying individual core usage

### Process Table

- Live updating table of top CPU-consuming processes
- Shows PID, name, CPU%, memory%, and status

## Auto-Refresh

The dashboard automatically refreshes every 5 seconds to display the latest metrics. Historical data is stored in the database for trending analysis.

## Customization

### Changing Refresh Interval

Edit the `setInterval` value in `templates/dashboard/main.html` (default: 5000ms)

### Data Retention

The system automatically keeps the last 1000 metric records. Adjust this in `views.py` in the `api_system_stats` function.

## Production Deployment

For production use:

1. Set `DEBUG = False` in `settings.py`
2. Configure `ALLOWED_HOSTS` with your domain/IP
3. Set up a proper web server (nginx + gunicorn)
4. Use a production database (PostgreSQL recommended)
5. Serve static files properly
6. Enable HTTPS

## License

MIT License - feel free to modify and use as needed!

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.
