-- Deforestation Detection System Database Schema
-- MySQL Database Schema

-- Create database
CREATE DATABASE IF NOT EXISTS deforestation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE deforestation_db;

-- Monitored Areas Table
CREATE TABLE IF NOT EXISTS monitored_areas (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    coordinates JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_monitored TIMESTAMP NULL,
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    active_monitoring BOOLEAN DEFAULT FALSE,
    monitoring_started_date TIMESTAMP NULL,
    monitoring_interval_days INT DEFAULT 5,
    next_scheduled_detection TIMESTAMP NULL,
    detection_count INT DEFAULT 0,
    INDEX idx_active_monitoring (active_monitoring),
    INDEX idx_next_scheduled (next_scheduled_detection)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Detection History Table
CREATE TABLE IF NOT EXISTS detection_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    area_id VARCHAR(36) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    before_date DATE NOT NULL,
    after_date DATE NOT NULL,
    deforestation_detected BOOLEAN DEFAULT FALSE,
    forest_loss_percent DECIMAL(10, 4) DEFAULT 0,
    vegetation_trend VARCHAR(50),
    forest_cover_before DECIMAL(10, 4),
    forest_cover_after DECIMAL(10, 4),
    change_data JSON,
    FOREIGN KEY (area_id) REFERENCES monitored_areas(id) ON DELETE CASCADE,
    INDEX idx_area_id (area_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_deforestation (deforestation_detected)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ML Detection Results Table
CREATE TABLE IF NOT EXISTS ml_detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    detection_id VARCHAR(50) UNIQUE NOT NULL,
    area_id VARCHAR(36),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detection_data JSON NOT NULL,
    model_version VARCHAR(50),
    confidence_score DECIMAL(5, 4),
    INDEX idx_area_id (area_id),
    INDEX idx_timestamp (timestamp),
    FOREIGN KEY (area_id) REFERENCES monitored_areas(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- System Metadata Table
CREATE TABLE IF NOT EXISTS system_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_name VARCHAR(100) UNIQUE NOT NULL,
    value_data JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (key_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Deforestation Coordinates Table (for map visualization)
CREATE TABLE IF NOT EXISTS deforestation_coordinates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    area_id VARCHAR(36),
    coordinates JSON NOT NULL,
    severity VARCHAR(50),
    detection_date TIMESTAMP,
    forest_loss_percent DECIMAL(10, 4),
    FOREIGN KEY (area_id) REFERENCES monitored_areas(id) ON DELETE CASCADE,
    INDEX idx_area_id (area_id),
    INDEX idx_detection_date (detection_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Users Table (authentication)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'employee') NOT NULL DEFAULT 'employee',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_email (email),
    INDEX idx_role (role),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Sessions Table (JWT audit + revocation)
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token_hash TEXT NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at),
    INDEX idx_is_revoked (is_revoked)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Search History Table
CREATE TABLE IF NOT EXISTS search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    search_query VARCHAR(500) NOT NULL,
    search_type VARCHAR(50) DEFAULT 'location',
    country VARCHAR(100),
    results_count INT DEFAULT 0,
    user_ip VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    selected_result JSON,
    INDEX idx_timestamp (timestamp),
    INDEX idx_search_query (search_query),
    INDEX idx_search_type (search_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
