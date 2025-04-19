-- Device Management System Database Schema
-- Version: 1.0
-- Last Updated: 2024-03-21

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Create Users Table
CREATE TABLE IF NOT EXISTS custom_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    department VARCHAR(50) NOT NULL,
    admin_state VARCHAR(3) NOT NULL CHECK (admin_state IN ('yes', 'no', '-')),
    state VARCHAR(10) NOT NULL CHECK (state IN ('enable', 'disable')),
    create_by INTEGER,
    disable_by VARCHAR(20),
    disable_datetime DATETIME,
    enable_by VARCHAR(20),
    enable_datetime DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (create_by) REFERENCES custom_user(id)
);

-- Create Device Table
CREATE TABLE IF NOT EXISTS device (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number VARCHAR(50) UNIQUE NOT NULL,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('available', 'assigned', 'maintenance', 'damaged')),
    department VARCHAR(50) NOT NULL,
    damage_by VARCHAR(20),
    damage_datetime DATETIME,
    created_by INTEGER NOT NULL,
    updated_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES custom_user(id),
    FOREIGN KEY (updated_by) REFERENCES custom_user(id)
);

-- Create Handover/Takeover Table
CREATE TABLE IF NOT EXISTS handover_takeover (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('handover', 'takeover')),
    condition VARCHAR(10) NOT NULL CHECK (condition IN ('working', 'damaged')),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at DATETIME,
    created_by INTEGER NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES device(id),
    FOREIGN KEY (from_user_id) REFERENCES custom_user(id),
    FOREIGN KEY (to_user_id) REFERENCES custom_user(id),
    FOREIGN KEY (created_by) REFERENCES custom_user(id)
);

-- Create Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_custom_user_employee_id ON custom_user(employee_id);
CREATE INDEX IF NOT EXISTS idx_custom_user_department ON custom_user(department);
CREATE INDEX IF NOT EXISTS idx_device_serial_number ON device(serial_number);
CREATE INDEX IF NOT EXISTS idx_device_department ON device(department);
CREATE INDEX IF NOT EXISTS idx_device_status ON device(status);
CREATE INDEX IF NOT EXISTS idx_handover_takeover_device ON handover_takeover(device_id);
CREATE INDEX IF NOT EXISTS idx_handover_takeover_from_user ON handover_takeover(from_user_id);
CREATE INDEX IF NOT EXISTS idx_handover_takeover_to_user ON handover_takeover(to_user_id);
CREATE INDEX IF NOT EXISTS idx_handover_takeover_date ON handover_takeover(transaction_date);

-- Create Triggers for automatic timestamp updates
CREATE TRIGGER IF NOT EXISTS update_custom_user_timestamp
    AFTER UPDATE ON custom_user
    FOR EACH ROW
    BEGIN
        UPDATE custom_user SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_device_timestamp
    AFTER UPDATE ON device
    FOR EACH ROW
    BEGIN
        UPDATE device SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Insert default admin user (password: admin123)
INSERT INTO custom_user (
    username, password, name, employee_id, department, admin_state, state, create_by
) VALUES (
    'admin',
    'pbkdf2_sha256$600000$your_hashed_password_here',
    'System Administrator',
    'ADMIN001',
    'IT',
    'yes',
    'enable',
    1
);

-- Comments on Tables
COMMENT ON TABLE custom_user IS 'Stores user information including admin and normal users';
COMMENT ON TABLE device IS 'Stores device inventory information';
COMMENT ON TABLE handover_takeover IS 'Stores device handover and takeover transactions';

-- Comments on Columns
COMMENT ON COLUMN custom_user.admin_state IS 'User admin status: yes=admin, no=limited admin, -=normal user';
COMMENT ON COLUMN custom_user.state IS 'User account status: enable or disable';
COMMENT ON COLUMN device.status IS 'Device status: available, assigned, maintenance, or damaged';
COMMENT ON COLUMN handover_takeover.transaction_type IS 'Type of transaction: handover or takeover';
COMMENT ON COLUMN handover_takeover.condition IS 'Device condition at time of transaction: working or damaged';

-- Database Requirements
/*
1. User Management:
   - Each user must have a unique employee ID
   - Admin users can manage all departments
   - Limited admins can only manage their department
   - Normal users can only view their assigned devices

2. Device Management:
   - Each device must have a unique serial number
   - Devices must belong to a department
   - Device status must be tracked (available, assigned, maintenance, damaged)
   - Device damage must be recorded with timestamp and responsible user

3. Handover/Takeover:
   - All transactions must be recorded with timestamps
   - Device condition must be recorded at each transaction
   - Transactions must be acknowledged by the receiving user
   - Only available devices can be handed over
   - Only assigned devices can be taken over

4. Security:
   - Passwords must be hashed
   - User sessions must be tracked
   - All actions must be logged with user information
   - Access control based on user roles and departments

5. Data Integrity:
   - Foreign key constraints must be enforced
   - Timestamps must be automatically updated
   - Status changes must be validated
   - Transaction history must be maintained

6. Performance:
   - Indexes must be created for frequently queried fields
   - Large tables must be partitioned if necessary
   - Query optimization must be implemented
   - Regular database maintenance must be performed
*/ 