# MySQL Database Setup Guide

## Overview
The deforestation detection system now uses **MySQL** to store all monitoring data, detection history, and system metadata.

## Prerequisites

1. **Install MySQL Server** (version 5.7 or higher)
   - Windows: Download from https://dev.mysql.com/downloads/mysql/
   - During installation, set a root password and remember it

2. **Verify MySQL is Running**
   ```powershell
   # Check if MySQL service is running
   Get-Service -Name MySQL*
   ```

## Database Configuration

### 1. Update Database Credentials

Edit `backend/config/config.yaml`:

```yaml
database:
  type: "mysql"
  host: "localhost"
  port: 3306
  database: "deforestation_db"
  username: "root"
  password: "YOUR_MYSQL_PASSWORD"  # ⚠️ SET YOUR PASSWORD HERE
  charset: "utf8mb4"
```

### 2. Install Python MySQL Connector

```powershell
cd backend
pip install pymysql
```

Or install all requirements:
```powershell
pip install -r requirements.txt
```

### 3. Initialize Database Schema

The database schema is automatically initialized when you start the API server.

**Manual initialization** (optional):
```powershell
mysql -u root -p < backend/database/schema.sql
```

## Database Schema

### Tables Created

1. **monitored_areas** - Stores area information
   - id (UUID), name, description, coordinates (JSON)
   - Monitoring settings and schedule
   - Created timestamp and metadata

2. **detection_history** - Stores detection results
   - Links to monitored areas (foreign key)
   - Before/after dates, deforestation status
   - Forest loss percentages, vegetation trends
   - Automatic timestamps

3. **ml_detections** - ML model detection results
   - Detection data in JSON format
   - Model version and confidence scores

4. **system_metadata** - System configuration
   - Key-value pairs for system state

5. **deforestation_coordinates** - Map visualization data
   - Coordinates for detected deforestation areas
   - Severity and loss percentages

## Starting the System

1. **Start MySQL Service** (if not running):
   ```powershell
   net start MySQL80  # Or your MySQL service name
   ```

2. **Start Backend API**:
   ```powershell
   cd backend
   python start_api.py
   ```

3. **Check Logs** for database initialization:
   ```
   INFO: Initializing database connection...
   INFO: ✓ Database connection successful
   INFO: ✓ Database schema initialized
   ```

## Migration from JSON Files

If you have existing data in JSON files (`backend/data/monitored_areas.json`), the system will automatically continue to work. To migrate to MySQL:

1. The old JSON file is no longer used
2. All new areas and detections are stored in MySQL
3. Old data remains in JSON files for reference

## Troubleshooting

### Connection Failed
```
ERROR: Database connection failed - check config.yaml settings
```
**Solutions:**
- Verify MySQL service is running
- Check username/password in `config.yaml`
- Test connection: `mysql -u root -p`

### Access Denied
```
pymysql.err.OperationalError: (1045, "Access denied for user 'root'@'localhost'")
```
**Solutions:**
- Update password in `config.yaml`
- Reset MySQL root password if forgotten

### Database Does Not Exist
```
pymysql.err.OperationalError: (1049, "Unknown database 'deforestation_db'")
```
**Solutions:**
- Run schema initialization: `mysql -u root -p < backend/database/schema.sql`
- Or restart API server - it will auto-create the database

## Database Management

### View All Monitored Areas
```sql
SELECT * FROM monitored_areas;
```

### View Recent Detections
```sql
SELECT a.name, d.timestamp, d.deforestation_detected, d.forest_loss_percent
FROM detection_history d
JOIN monitored_areas a ON d.area_id = a.id
ORDER BY d.timestamp DESC
LIMIT 10;
```

### Check Active Monitoring
```sql
SELECT name, active_monitoring, next_scheduled_detection
FROM monitored_areas
WHERE active_monitoring = TRUE;
```

### Clear All Data (⚠️ Destructive)
```sql
TRUNCATE TABLE detection_history;
TRUNCATE TABLE monitored_areas;
```

## Benefits of MySQL

✅ **Reliability**: ACID compliance, transaction support  
✅ **Performance**: Indexed queries, connection pooling  
✅ **Scalability**: Handle thousands of detections  
✅ **Queries**: Complex joins and aggregations  
✅ **Backup**: Standard database backup tools  
✅ **Concurrent Access**: Multiple processes can read/write safely

## Production Recommendations

For production deployment:

1. **Create dedicated database user** (don't use root):
   ```sql
   CREATE USER 'deforestation_user'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON deforestation_db.* TO 'deforestation_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. **Enable connection pooling** (already configured in `db_manager.py`)

3. **Set up automated backups**:
   ```powershell
   mysqldump -u root -p deforestation_db > backup.sql
   ```

4. **Monitor database size**:
   ```sql
   SELECT table_name, 
          ROUND(((data_length + index_length) / 1024 / 1024), 2) AS "Size (MB)"
   FROM information_schema.TABLES
   WHERE table_schema = "deforestation_db";
   ```

## Support

For issues:
1. Check MySQL service status
2. Verify credentials in `config.yaml`
3. Review API server logs
4. Test direct MySQL connection
